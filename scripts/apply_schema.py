"""正典（docs/SCHEMA.md）から個人の側の制約・インデックスを DB に作る入口（N-19）。既定は流す文を出すだけ（--write で流す）。

使い方（Mac）:  uv run python scripts/apply_schema.py [--write]
接続先は新しい個人の側（127.0.0.1:37687）だけ。資源の側には当てない（資源の側の制約は書き出しに入っている。N-23）。
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest import canon, schema_apply  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    c = canon.load(REPO / "docs" / "SCHEMA.md")
    stmts = schema_apply.statements(c)
    for s in stmts:
        print(s)
    if not a.write:
        print("書き込んでいない（%d 文。--write で流す）" % len(stmts))
        return 0
    from nest import connections
    with connections.driver("personal") as d:
        schema_apply.apply(d, c)
    print("流した：%d 文（個人の側）" % len(stmts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
