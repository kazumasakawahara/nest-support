"""
Hospital.doctor → Doctor ノード昇格マイグレーション（C-2 / P2 2026-07）

背景:
    かかりつけ医が Hospital.doctor の文字列プロパティに埋まっていた（例
    '中村先生'）。同一医師が複数病院に登場しても文字列では繋がらず、
    「この医師がどの病院・どの利用者に関わるか」をグラフで辿れない。

方針:
    Hospital.doctor を Doctor ノードへ昇格する:
        (:Hospital {doctor:'X'})  →  (:Hospital)-[:HAS_DOCTOR]->(:Doctor {name:'X'})
    Doctor は name で MERGE し、同名医師は 1 ノードに収斂させる（共有・クエリ性）。
    昇格後に Hospital.doctor プロパティを除去する。

    - 空文字/NULL の doctor は対象外。
    - 既定は dry-run（計画表示のみ・DB 変更なし）。
    - `--apply` で実行。冪等（doctor 除去済みの Hospital は再対象にならない）。
    - 実行前に scripts/backup.sh でのバックアップを推奨。

前提スキーマ（追加済み）:
    ノードラベル Doctor / リレーション HAS_DOCTOR（schema_validator に登録）。

使い方:
    uv run python scripts/migrate_hospital_doctor_to_node.py            # dry-run
    uv run python scripts/migrate_hospital_doctor_to_node.py --apply    # 実行
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.db_operations import run_query, execute_write

# doctor 文字列を持つ Hospital を列挙（空文字は除外）。
_DETECT = """
MATCH (h:Hospital)
WHERE h.doctor IS NOT NULL AND trim(h.doctor) <> ''
RETURN h.name AS hospital, h.doctor AS doctor
ORDER BY doctor, hospital
"""

# 1 病院分の昇格。捕捉済みの doctor 値をパラメータで渡し、Doctor を MERGE、
# HAS_DOCTOR を張り、Hospital.doctor を除去する。
_PROMOTE = """
MATCH (h:Hospital {name: $hospital})
WHERE h.doctor IS NOT NULL
MERGE (d:Doctor {name: $doctor})
MERGE (h)-[:HAS_DOCTOR]->(d)
REMOVE h.doctor
RETURN elementId(d) AS doctorId
"""


def migrate(apply: bool) -> dict:
    rows = run_query(_DETECT)
    if not rows:
        print("昇格対象の Hospital.doctor はありません。")
        return {"hospitals": 0, "doctors": 0, "applied": apply}

    distinct_doctors = sorted({r["doctor"] for r in rows})
    print(f"対象病院: {len(rows)} 件 / 医師（名寄せ後）: {len(distinct_doctors)} 名")
    for r in rows:
        print(f"  {r['hospital']!r}  -[:HAS_DOCTOR]->  Doctor {{name: {r['doctor']!r}}}")
        if apply:
            execute_write(_PROMOTE, {"hospital": r["hospital"], "doctor": r["doctor"]})

    if apply:
        print(f"\n完了: {len(rows)} 病院を昇格し、{len(distinct_doctors)} 名の Doctor に収斂、"
              f"Hospital.doctor を除去しました。")
    else:
        print(f"\n[dry-run] {len(rows)} 病院が対象です。実行するには --apply を付けてください。")
    return {"hospitals": len(rows), "doctors": len(distinct_doctors), "applied": apply}


def main() -> None:
    parser = argparse.ArgumentParser(description="Hospital.doctor を Doctor ノードへ昇格")
    parser.add_argument("--apply", action="store_true", help="実際に DB を変更する（既定は dry-run）")
    args = parser.parse_args()
    migrate(apply=args.apply)


if __name__ == "__main__":
    main()
