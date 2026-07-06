"""
Condition.status のケース正規化マイグレーション（C-1 / P2 2026-07）

背景:
    実DBの Condition.status に 'Active' と 'active' が混在していた。列挙値は
    英語 PascalCase が規約（SSOT）。大小文字ゆれは検索・集計・Guardian Layer の
    検証を壊すため、正規の列挙値へ揃える。

方針:
    status 値を大小文字を無視して正規の列挙値（schema_validator.ENUM_VALUES
    ["status"]）に照合し、一致すれば正規形へ補正する。照合できない未知の値は
    **変更せず報告のみ**（安全側。勝手に推測して上書きしない）。

    - 既定は dry-run（計画表示のみ・DB 変更なし）。
    - `--apply` で実行。冪等（既に正規形なら対象外）。
    - 実行前に scripts/backup.sh でのバックアップを推奨。

使い方:
    uv run python scripts/migrate_condition_status_case.py            # dry-run
    uv run python scripts/migrate_condition_status_case.py --apply    # 実行
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.db_operations import run_query, execute_write
from lib.schema_validator import ENUM_VALUES

_CANONICAL = ENUM_VALUES["status"]
_LOWER_TO_CANONICAL = {v.lower(): v for v in _CANONICAL}


def normalize_status_case(value):
    """status 値を大小文字無視で正規列挙値へ補正する。

    Returns:
        (canonical, changed): 照合できれば (正規形, 元と違うか)。
        照合できなければ (元値, False)。
    """
    if not isinstance(value, str):
        return value, False
    if value in _CANONICAL:
        return value, False
    canonical = _LOWER_TO_CANONICAL.get(value.strip().lower())
    if canonical is None:
        return value, False
    return canonical, True


def migrate(apply: bool) -> dict:
    rows = run_query(
        "MATCH (c:Condition) WHERE c.status IS NOT NULL "
        "RETURN c.status AS status, count(*) AS n ORDER BY n DESC"
    )
    fixed = 0
    unknown = []
    for row in rows:
        old = row["status"]
        n = row["n"]
        new, changed = normalize_status_case(old)
        if changed:
            print(f"  補正: {old!r} → {new!r}  （{n} 件）")
            if apply:
                execute_write(
                    "MATCH (c:Condition {status: $old}) SET c.status = $new",
                    {"old": old, "new": new},
                )
                fixed += n
        elif new not in _CANONICAL:
            unknown.append((old, n))

    if unknown:
        print("\n[警告] 正規列挙に照合できない未知の status（変更しません）:")
        for val, n in unknown:
            print(f"  {val!r}: {n} 件")

    if apply:
        print(f"\n完了: {fixed} 件の Condition.status を正規形へ補正しました。")
    else:
        total = sum(r["n"] for r in rows
                    if normalize_status_case(r["status"])[1])
        print(f"\n[dry-run] 補正対象 {total} 件。実行するには --apply を付けてください。")
    return {"fixed": fixed, "unknown": len(unknown), "applied": apply}


def main() -> None:
    parser = argparse.ArgumentParser(description="Condition.status のケース正規化")
    parser.add_argument("--apply", action="store_true", help="実際に DB を変更する（既定は dry-run）")
    args = parser.parse_args()
    migrate(apply=args.apply)


if __name__ == "__main__":
    main()
