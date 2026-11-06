"""field-ui の職員ごとのトークンの表を作る（計画 N-37。決まりは nest/auth.py の先頭）。

表は ~/.config/nest/field-ui-staff.json（権限 600）。職員 ID とトークンの sha256 だけを書く。
トークンは add のときに一度だけ画面に出す。表にもリポジトリにもチャットにも残さない。職員に手で渡す。

使い方:
  uv run python scripts/staff_token.py add STF-…      # 新しいトークン（同じ職員なら作り直し。前のものは使えなくなる）
  uv run python scripts/staff_token.py remove STF-…
  uv run python scripts/staff_token.py list           # 職員 ID だけ
"""
import argparse
import json
import os
import secrets
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest import auth, ids  # noqa: E402


def _read(table):
    return auth.load_staff_table(table) if table.exists() else {}


def _write(table, staff):
    table.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = table.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "staff": staff}, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, table)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "remove", "list"])
    ap.add_argument("staff_id", nargs="?")
    ap.add_argument("--table", default=str(auth.DEFAULT_STAFF_TOKENS))
    a = ap.parse_args(argv)
    table = Path(a.table)
    if a.cmd != "list" and not ids.is_valid_id(a.staff_id, "STF"):
        print("止めた：職員 ID（STF-…）を指定する")
        return 1
    staff = _read(table)
    if a.cmd == "list":
        for staff_id in sorted(staff):
            print(staff_id)
        return 0
    if a.cmd == "remove":
        if staff.pop(a.staff_id, None) is None:
            print("止めた：%s は表に無い" % a.staff_id)
            return 1
        _write(table, staff)
        print("消した：%s" % a.staff_id)
        return 0
    token = secrets.token_urlsafe(32)
    staff[a.staff_id] = auth.token_hash(token)
    _write(table, staff)
    print("作った：%s（表 %s）" % (a.staff_id, table))
    print("トークン：%s" % token)
    print("このトークンは二度と出ない。職員に手で渡す（チャット・メールに貼らない）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
