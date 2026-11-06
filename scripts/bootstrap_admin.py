"""最初の職員（Administrator）を登録する（計画 N-38。登録そのものは nest/gate/bootstrap.py。N-20）。

個人の側に職員が一人もいないときだけ使える。2 人目からは Administrator がゲートで登録する。
表示名は呼び名でよい（実名でなくてよい）。DB を起動してから使う。

使い方:
  uv run python scripts/bootstrap_admin.py --name "事務局"
"""
import argparse
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest.gate import bootstrap  # noqa: E402


def main(argv=None, driver=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="表示名（呼び名）")
    a = ap.parse_args(argv)
    request_id = "req-bootstrap-" + uuid.uuid4().hex

    if driver is None:
        from nest import connections
        with connections.driver("personal") as d:
            out = bootstrap.bootstrap_admin(d, a.name, request_id)
    else:
        out = bootstrap.bootstrap_admin(driver, a.name, request_id)

    if not out["ok"]:
        for e in out["errors"]:
            print("登録しなかった：" + e)
        return 1
    print("最初の管理者を登録した：%s" % out["staffId"])
    print("field-ui を使うなら、次にトークンを作る：uv run python scripts/staff_token.py add %s" % out["staffId"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
