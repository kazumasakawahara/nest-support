"""
重み横断一貫性チェッカー (cross-client weight consistency checker)

類似した NgAction / CarePreference の間で、riskLevel / priority が矛盾して
いないかを Gemini Embedding 2 の意味的類似度で検出する。

Usage:
    uv run python scripts/check_weight_consistency.py
    uv run python scripts/check_weight_consistency.py --threshold 0.75
    uv run python scripts/check_weight_consistency.py --only ng
    uv run python scripts/check_weight_consistency.py --only cp
    uv run python scripts/check_weight_consistency.py --client "テスト太郎"

前提:
    - Neo4j 起動中 (bolt://localhost:7687)
    - 対象ノードに embedding プロパティ (Gemini Embedding 2, 768次元) が付与済み
      未付与の場合:
          uv run python scripts/backfill_embeddings.py --label NgAction
          uv run python scripts/backfill_embeddings.py --label CarePreference
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.embedding import cosine_similarity

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")

# 列挙値の順序（段差計算用）
RISK_ORDER = {"LifeThreatening": 3, "Panic": 2, "Discomfort": 1}
PRIORITY_ORDER = {"High": 3, "Medium": 2, "Low": 1}


def fetch_nodes_with_embedding(
    session, label: str, weight_prop: str, client_filter: str | None
) -> list[dict]:
    """
    指定ラベルのノードのうち embedding を持つものを取得。
    client_filter が指定されたとき、そのクライアントに紐づくもののみ対象。
    """
    rel = "MUST_AVOID" if label == "NgAction" else "REQUIRES"
    if client_filter:
        query = f"""
        MATCH (c:Client)-[:{rel}]->(n:{label})
        WHERE n.embedding IS NOT NULL AND c.name CONTAINS $name
        RETURN elementId(n) AS id, n.embedding AS emb,
               n[$wp] AS weight,
               coalesce(n.action, n.instruction) AS text,
               c.name AS client
        """
    else:
        query = f"""
        MATCH (c:Client)-[:{rel}]->(n:{label})
        WHERE n.embedding IS NOT NULL
        RETURN elementId(n) AS id, n.embedding AS emb,
               n[$wp] AS weight,
               coalesce(n.action, n.instruction) AS text,
               c.name AS client
        """
    result = []
    for r in session.run(query, wp=weight_prop, name=client_filter or ""):
        result.append({
            "id": r["id"],
            "emb": r["emb"],
            "weight": r["weight"],
            "text": r["text"],
            "client": r["client"],
        })
    return result


def find_inconsistent_pairs(
    nodes: list[dict], threshold: float, weight_order: dict[str, int]
) -> list[tuple]:
    """
    ノード群から類似ペアを抽出し、weight が異なるものを返す。
    戻り値: (similarity, node_a, node_b, gap) のリスト。gap は順序段差。
    """
    pairs: list[tuple] = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            sim = cosine_similarity(a["emb"], b["emb"])
            if sim < threshold:
                continue
            wa, wb = a["weight"], b["weight"]
            if wa is None or wb is None:
                continue
            if wa == wb:
                continue
            gap = abs(weight_order.get(wa, 0) - weight_order.get(wb, 0))
            pairs.append((sim, a, b, gap))
    # 重大度順: gap 降順 → sim 降順
    pairs.sort(key=lambda x: (-x[3], -x[0]))
    return pairs


def print_report(
    label: str, weight_label: str, pairs: list[tuple], total_nodes: int
) -> None:
    bar = "━" * 70
    print()
    print(bar)
    print(f"【{label}】{weight_label} 横断一貫性チェック (対象 {total_nodes} 件)")
    print(bar)
    if not pairs:
        print("  ✅ 重みに不整合は検出されませんでした")
        return

    critical = [p for p in pairs if p[3] >= 2]
    warning = [p for p in pairs if p[3] == 1]

    if critical:
        print(f"\n  🔴 重大（段差 ≥ 2）: {len(critical)} 件")
        for sim, a, b, gap in critical:
            print(f"\n  類似度 {sim:.3f}  (段差 {gap})")
            print(f"    [{a['weight']:15s}] {a['text']}  ({a['client']})")
            print(f"    [{b['weight']:15s}] {b['text']}  ({b['client']})")

    if warning:
        print(f"\n  🟡 要確認（段差 1）: {len(warning)} 件")
        for sim, a, b, gap in warning:
            print(f"\n  類似度 {sim:.3f}")
            print(f"    [{a['weight']:15s}] {a['text']}  ({a['client']})")
            print(f"    [{b['weight']:15s}] {b['text']}  ({b['client']})")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="類似 NgAction / CarePreference 間の重み不整合を検出"
    )
    parser.add_argument("--threshold", type=float, default=0.85,
                        help="コサイン類似度の下限 (default: 0.85)")
    parser.add_argument("--only", choices=["ng", "cp"], default=None,
                        help="ng: NgAction のみ / cp: CarePreference のみ")
    parser.add_argument("--client", type=str, default=None,
                        help="特定クライアントに関連する重みだけをチェック")
    args = parser.parse_args()

    targets: list[tuple[str, str, str, dict]] = []
    if args.only in (None, "ng"):
        targets.append(("NgAction", "riskLevel", "riskLevel", RISK_ORDER))
    if args.only in (None, "cp"):
        targets.append(("CarePreference", "priority", "priority", PRIORITY_ORDER))

    print(f"\n重み横断一貫性チェック  threshold={args.threshold}"
          + (f"  client={args.client}" if args.client else ""))

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session() as s:
            for label, weight_prop, weight_label, order in targets:
                nodes = fetch_nodes_with_embedding(s, label, weight_prop, args.client)
                if not nodes:
                    print(f"\n{label}: 対象ノードなし（embedding 未付与の可能性あり）")
                    continue
                pairs = find_inconsistent_pairs(nodes, args.threshold, order)
                print_report(label, weight_label, pairs, len(nodes))
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
