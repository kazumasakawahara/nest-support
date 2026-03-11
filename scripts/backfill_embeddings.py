"""
既存ノードへの Embedding 一括付与（バックフィル）スクリプト

Gemini Embedding 2 を使って SupportLog, NgAction, CarePreference の
既存ノードに embedding を付与する。

使用例:
    uv run python scripts/backfill_embeddings.py --all
    uv run python scripts/backfill_embeddings.py --label SupportLog
    uv run python scripts/backfill_embeddings.py --label SupportLog --client "山田健太"
    uv run python scripts/backfill_embeddings.py --dry-run
    uv run python scripts/backfill_embeddings.py --stats
"""

import argparse
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加（scripts/ から実行する場合）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()


def log(message: str, level: str = "INFO"):
    prefix = {"INFO": "  ", "OK": "  ✅", "WARN": "  ⚠️", "ERROR": "  ❌"}
    sys.stderr.write(f"{prefix.get(level, '  ')} {message}\n")
    sys.stderr.flush()


def get_stats():
    """embedding 付与状況を表示"""
    from lib.embedding import get_embedding_stats

    stats = get_embedding_stats()
    print("\n📊 Embedding 統計:")
    print(f"  {'ラベル':<20} {'付与済み':>8} / {'全体':>8}  {'率':>7}")
    print(f"  {'─' * 50}")
    for label, s in stats.items():
        total = s["total"]
        embedded = s["embedded"]
        pct = (embedded / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {label:<20} {embedded:>8} / {total:>8}  {pct:>6.1f}% {bar}")
    print()


def backfill_label(label: str, client_name: str | None, batch_size: int, dry_run: bool):
    """指定ラベルのノードにembeddingをバックフィル"""
    from lib.embedding import backfill_support_log_embeddings, backfill_ng_action_embeddings
    from lib.db_new_operations import run_query
    from lib.embedding import embed_texts_batch, _run_query

    if label == "SupportLog":
        return _backfill_loop(
            label="SupportLog",
            fetch_fn=lambda bs: _fetch_support_logs(client_name, bs),
            text_fn=_support_log_text,
            batch_size=batch_size,
            dry_run=dry_run,
        )
    elif label == "NgAction":
        return _backfill_loop(
            label="NgAction",
            fetch_fn=lambda bs: _fetch_ng_actions(bs),
            text_fn=_ng_action_text,
            batch_size=batch_size,
            dry_run=dry_run,
        )
    elif label == "CarePreference":
        return _backfill_loop(
            label="CarePreference",
            fetch_fn=lambda bs: _fetch_care_preferences(bs),
            text_fn=_care_preference_text,
            batch_size=batch_size,
            dry_run=dry_run,
        )
    else:
        log(f"未対応のラベル: {label}", "ERROR")
        return {"processed": 0, "success": 0, "failed": 0}


# --- Fetch 関数 ---

def _fetch_support_logs(client_name: str | None, batch_size: int) -> list:
    from lib.db_new_operations import run_query

    if client_name:
        return run_query(
            """
            MATCH (log:SupportLog)-[:ABOUT]->(c:Client)
            WHERE c.name CONTAINS $client_name AND log.embedding IS NULL
            RETURN elementId(log) AS id,
                   log.situation AS situation, log.action AS action,
                   log.note AS note, log.effectiveness AS effectiveness
            LIMIT $batch_size
            """,
            {"client_name": client_name, "batch_size": batch_size},
        )
    return run_query(
        """
        MATCH (log:SupportLog)
        WHERE log.embedding IS NULL
        RETURN elementId(log) AS id,
               log.situation AS situation, log.action AS action,
               log.note AS note, log.effectiveness AS effectiveness
        LIMIT $batch_size
        """,
        {"batch_size": batch_size},
    )


def _fetch_ng_actions(batch_size: int) -> list:
    from lib.db_new_operations import run_query

    return run_query(
        """
        MATCH (ng:NgAction)
        WHERE ng.embedding IS NULL
        RETURN elementId(ng) AS id,
               ng.action AS action, ng.reason AS reason, ng.riskLevel AS riskLevel
        LIMIT $batch_size
        """,
        {"batch_size": batch_size},
    )


def _fetch_care_preferences(batch_size: int) -> list:
    from lib.db_new_operations import run_query

    return run_query(
        """
        MATCH (cp:CarePreference)
        WHERE cp.embedding IS NULL
        RETURN elementId(cp) AS id,
               cp.category AS category, cp.instruction AS instruction
        LIMIT $batch_size
        """,
        {"batch_size": batch_size},
    )


# --- テキスト構築関数 ---

def _support_log_text(node: dict) -> str:
    parts = []
    if node.get("situation"):
        parts.append(f"状況: {node['situation']}")
    if node.get("action"):
        parts.append(f"対応: {node['action']}")
    if node.get("note"):
        parts.append(f"メモ: {node['note']}")
    if node.get("effectiveness"):
        parts.append(f"効果: {node['effectiveness']}")
    return "。".join(parts) if parts else ""


def _ng_action_text(node: dict) -> str:
    parts = [f"禁忌: {node.get('action', '')}"]
    if node.get("reason"):
        parts.append(f"理由: {node['reason']}")
    if node.get("riskLevel"):
        parts.append(f"リスク: {node['riskLevel']}")
    return "。".join(parts)


def _care_preference_text(node: dict) -> str:
    parts = []
    if node.get("category"):
        parts.append(f"カテゴリ: {node['category']}")
    if node.get("instruction"):
        parts.append(f"指示: {node['instruction']}")
    return "。".join(parts) if parts else ""


# --- バックフィルループ ---

def _backfill_loop(
    label: str,
    fetch_fn,
    text_fn,
    batch_size: int,
    dry_run: bool,
) -> dict:
    """バッチ単位でembeddingを付与するループ"""
    from lib.embedding import embed_texts_batch
    from lib.db_new_operations import run_query

    total_processed = 0
    total_success = 0
    total_failed = 0

    while True:
        nodes = fetch_fn(batch_size)
        if not nodes:
            break

        if dry_run:
            total_processed += len(nodes)
            log(f"[dry-run] {label}: {len(nodes)} 件見つかりました")
            break  # dry-run では1バッチだけカウントして終了

        texts = [text_fn(n) for n in nodes]
        # 空テキストのノードをスキップ
        valid = [(n, t) for n, t in zip(nodes, texts) if t]
        if not valid:
            break

        valid_nodes, valid_texts = zip(*valid)
        embeddings = embed_texts_batch(list(valid_texts))

        batch_success = 0
        for node, emb in zip(valid_nodes, embeddings):
            if emb is None:
                total_failed += 1
                continue
            try:
                run_query(
                    """
                    MATCH (n) WHERE elementId(n) = $id
                    CALL db.create.setNodeVectorProperty(n, 'embedding', $embedding)
                    """,
                    {"id": node["id"], "embedding": emb},
                )
                batch_success += 1
            except Exception as e:
                log(f"付与失敗 ({node['id']}): {e}", "WARN")
                total_failed += 1

        total_processed += len(valid_nodes)
        total_success += batch_success
        log(f"{label}: バッチ {batch_success}/{len(valid_nodes)} 件付与", "OK")

        # 全件処理済みならループを抜ける
        if len(nodes) < batch_size:
            break

        # レートリミット対策
        time.sleep(0.5)

    return {"processed": total_processed, "success": total_success, "failed": total_failed}


def main():
    parser = argparse.ArgumentParser(
        description="既存ノードに Gemini Embedding 2 ベクトルを一括付与する"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="SupportLog, NgAction, CarePreference の全てを処理",
    )
    parser.add_argument(
        "--label", choices=["SupportLog", "NgAction", "CarePreference"],
        help="特定のラベルのみ処理",
    )
    parser.add_argument(
        "--client", type=str, default=None,
        help="特定クライアント名でフィルタ（SupportLogのみ有効）",
    )
    parser.add_argument(
        "--batch-size", type=int, default=20,
        help="一度に処理するノード数（デフォルト: 20）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="実際には付与せず、対象件数のみ表示",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="embedding付与状況の統計のみ表示",
    )
    args = parser.parse_args()

    # ベクトルインデックスの確保
    from lib.embedding import ensure_vector_indexes
    ensure_vector_indexes()

    if args.stats:
        get_stats()
        return

    if not args.all and not args.label:
        parser.print_help()
        print("\n--all または --label を指定してください。")
        return

    labels = ["SupportLog", "NgAction", "CarePreference"] if args.all else [args.label]

    if args.dry_run:
        print("\n🔍 Dry-run モード（実際の付与は行いません）")

    print(f"\n🚀 バックフィル開始: {', '.join(labels)}")
    if args.client:
        print(f"   フィルタ: client={args.client}")

    results = {}
    for label in labels:
        print(f"\n--- {label} ---")
        result = backfill_label(
            label=label,
            client_name=args.client if label == "SupportLog" else None,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
        results[label] = result

    # サマリ
    print("\n" + "=" * 50)
    print("📋 バックフィル結果サマリ:")
    for label, r in results.items():
        if args.dry_run:
            print(f"  {label}: {r['processed']} 件が未付与")
        else:
            print(f"  {label}: {r['success']}/{r['processed']} 成功, {r['failed']} 失敗")
    print()

    # 最終統計
    get_stats()


if __name__ == "__main__":
    main()
