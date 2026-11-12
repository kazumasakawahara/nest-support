"""書き込み受付（MCP nest-gate）の職員の ID を設定する・設定したか確かめる（台帳 G-96 (f)。2026-11-10 河原さん。ADR-002 D2）。

- set：~/.config/nest/nest-gate.env に NEST_GATE_STAFF_ID=STF-… を書く（置き換える）。権限は 600。
  形が STF-… でない ID と、個人の側に Active の職員としていない ID は、何も書かずに止める（DB を起こしてから打つ）
- check：ファイルが有る・権限 600・中の ID の形が正しいかを確かめる。ID そのものは出さない（中身は Claude に読ませない）

この Mac で Claude Desktop を使う専門職一人の ID を書く。書き込み受付は、道具の引数ではなくこのファイルから職員を読む。

使い方:
  uv run python scripts/gate_staff.py set --staff STF-…
  uv run python scripts/gate_staff.py check
"""
import argparse
import os
import stat
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest import ids  # noqa: E402

CONFIG = Path.home() / ".config" / "nest" / "nest-gate.env"
KEY = "NEST_GATE_STAFF_ID"
ACTIVE = "MATCH (s:Staff {staffId: $id, status: 'Active'}) RETURN s.staffId AS id"


def _set(staff, driver):
    if not ids.is_valid_id(staff, "STF"):
        print("止めた：職員の ID（STF-…）の形でない。何も書いていない")
        return 1
    records, _, _ = driver.execute_query(ACTIVE, {"id": staff}, database_="neo4j")
    if not records:
        print("止めた：個人の側に Active の職員としていない（%s）。何も書いていない" % staff)
        return 1
    CONFIG.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(CONFIG, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("%s=%s\n" % (KEY, staff))
    os.chmod(CONFIG, 0o600)
    print("設定した：%s（権限 600）。Claude Desktop を ⌘Q で終了して起動し直す" % CONFIG)
    return 0


def _check():
    if not CONFIG.is_file() or CONFIG.is_symlink():
        print("設定していない：%s が無い。uv run python scripts/gate_staff.py set --staff STF-… を打つ" % CONFIG)
        return 1
    mode = stat.S_IMODE(os.stat(CONFIG).st_mode)
    if mode != 0o600:
        print("直す：%s の権限が %o（600 にする。uv run python scripts/gate_staff.py set --staff STF-… を打ち直す）" % (CONFIG, mode))
        return 1
    from dotenv import dotenv_values
    if not ids.is_valid_id(dotenv_values(CONFIG).get(KEY), "STF"):
        print("直す：%s の %s が職員の ID（STF-…）の形でない。set を打ち直す" % (CONFIG, KEY))
        return 1
    print("設定してある：%s（権限 600、職員の ID の形は正しい）" % CONFIG)
    return 0


def main(argv=None, driver=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["set", "check"])
    ap.add_argument("--staff", help="この Mac の専門職の職員 ID（STF-…）。set のとき")
    a = ap.parse_args(argv)
    if a.action == "check":
        return _check()
    if not a.staff:
        print("止めた：set には --staff STF-… が要る")
        return 1
    if driver is not None:
        return _set(a.staff, driver)
    from nest import connections
    with connections.driver("personal") as d:
        return _set(a.staff, d)


if __name__ == "__main__":
    sys.exit(main())
