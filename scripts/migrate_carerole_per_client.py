"""
CareRole の per-client 化マイグレーション（R2-C-4）

背景:
    旧コードは `MERGE (cr:CareRole {name})` でロール名だけをキーに CareRole を
    作っていたため、別クライアントの Relative が同名ロール（例「服薬管理」）を
    担うと、単一の CareRole ノードが複数クライアント間で共有されてしまう。
    共有ノードにクライアント固有の担い手（CAN_BE_PERFORMED_BY）が混ざると、
    「誰が誰のケアを代替できるか」の可視化が壊れる。

本スクリプト:
    複数クライアントから到達される共有 CareRole を検出し、クライアントごとに
    複製して PERFORMS / CAN_BE_PERFORMED_BY を貼り替え、元の共有ノードを外す。

    - 既定は dry-run（計画を表示するだけ・DB を変更しない）。
    - `--apply` で実行する。
    - 冪等: 分割済み（clientName 付き）の CareRole は対象外。

前提スキーマ:
    (:Relative)-[:PERFORMS]->(:CareRole)
    (:Relative)-[:IS_PARENT_OF|FAMILY_OF]->(:Client)
    (:CareRole)-[:CAN_BE_PERFORMED_BY]->(:ServiceProvider|:Supporter|:KeyPerson)

使い方:
    uv run python scripts/migrate_carerole_per_client.py            # dry-run
    uv run python scripts/migrate_carerole_per_client.py --apply    # 実行
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.db_operations import run_query, execute_write


# 複数クライアントから到達される共有 CareRole を検出する。
# clientName が既に付いているものは分割済みとみなし対象外。
_DETECT = """
MATCH (c:Client)<-[:IS_PARENT_OF|FAMILY_OF]-(:Relative)-[:PERFORMS]->(cr:CareRole)
WHERE cr.clientName IS NULL
WITH cr, collect(DISTINCT c.name) AS clients
WHERE size(clients) > 1
RETURN elementId(cr) AS crId, cr.name AS roleName, clients
ORDER BY roleName
"""

# 1 クライアント分の分割を行う。元 CareRole の props をコピーしつつ clientName で
# スコープした新ノードを作り、そのクライアント配下の Relative の PERFORMS と、
# 元ノードの CAN_BE_PERFORMED_BY を新ノードへ複製する。
# 元の共有ノード・元 PERFORMS は最後の cleanup で取り除く。
_SPLIT_FOR_CLIENT = """
MATCH (cr:CareRole) WHERE elementId(cr) = $crId
MATCH (client:Client {name: $clientName})<-[:IS_PARENT_OF|FAMILY_OF]-(rel:Relative)-[oldPerf:PERFORMS]->(cr)
WITH cr, client, collect(DISTINCT rel) AS rels
CREATE (nc:CareRole)
SET nc = properties(cr), nc.clientName = $clientName
WITH cr, nc, rels
FOREACH (r IN rels | CREATE (r)-[:PERFORMS]->(nc))
WITH cr, nc
OPTIONAL MATCH (cr)-[:CAN_BE_PERFORMED_BY]->(performer)
WITH nc, collect(DISTINCT performer) AS performers
FOREACH (p IN performers | CREATE (nc)-[:CAN_BE_PERFORMED_BY]->(p))
RETURN elementId(nc) AS newId
"""

# 分割元の共有 CareRole を切り離して削除する（全クライアント分割後に呼ぶ）。
_CLEANUP = """
MATCH (cr:CareRole) WHERE elementId(cr) = $crId
DETACH DELETE cr
"""


def detect_shared() -> list[dict]:
    return run_query(_DETECT)


def migrate(apply: bool) -> dict:
    shared = detect_shared()
    if not shared:
        print("共有 CareRole は見つかりませんでした。マイグレーション対象はありません。")
        return {"shared": 0, "split": 0, "applied": apply}

    split_count = 0
    for row in shared:
        cr_id = row["crId"]
        role = row["roleName"]
        clients = row["clients"]
        print(f"[{role}] {len(clients)} クライアントで共有: {', '.join(clients)}")
        for client_name in clients:
            print(f"    → '{client_name}' 用に複製")
            if apply:
                execute_write(_SPLIT_FOR_CLIENT, {"crId": cr_id, "clientName": client_name})
                split_count += 1
        if apply:
            execute_write(_CLEANUP, {"crId": cr_id})
            print(f"    ✓ 元の共有ノードを削除")

    if apply:
        print(f"\n完了: {len(shared)} 個の共有 CareRole を {split_count} 個の per-client ノードに分割しました。")
    else:
        print(f"\n[dry-run] {len(shared)} 個の共有 CareRole が対象です。実行するには --apply を付けてください。")
    return {"shared": len(shared), "split": split_count, "applied": apply}


def main() -> None:
    parser = argparse.ArgumentParser(description="CareRole の per-client 化マイグレーション")
    parser.add_argument("--apply", action="store_true", help="実際に DB を変更する（既定は dry-run）")
    args = parser.parse_args()
    migrate(apply=args.apply)


if __name__ == "__main__":
    main()
