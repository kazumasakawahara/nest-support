"""二人目からの職員を登録する（計画 N-43。2026-11-06 河原さん）。管理者（Administrator）が手元で打つ。

- ゲート（nest.gate.write.submit）を通して職員（Staff）を一人作る。人が入れたもの（origin Human）。
  職員を作れるのは Active な管理者だけ（ゲートが確かめる）
- 役割は Staff（既定）か Administrator。表示名は呼び名でよい（実名でなくてよい）
- 作ったら職員 ID と、続けて打つ staff_token のコマンドを出す（field-ui を使う職員のトークン）

使い方:
  uv run python scripts/new_staff.py --admin STF-… --name "呼び名" [--role Staff|Administrator]
"""
import argparse
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest.gate import write as gw  # noqa: E402


def parse(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--admin", required=True, help="登録する管理者の職員 ID（STF-…）")
    ap.add_argument("--name", required=True, help="表示名（呼び名）")
    ap.add_argument("--role", choices=["Staff", "Administrator"], default="Staff")
    return ap.parse_args(argv)


def staff_request(a, request_id):
    return {"requestId": request_id, "actorStaffId": a.admin,
            "nodes": [{"ref": "s", "label": "Staff", "origin": "Human",
                       "properties": {"displayName": a.name, "role": a.role}}],
            "relationships": []}


def _run(d, a):
    out = gw.submit(staff_request(a, "req-new-staff-" + uuid.uuid4().hex), d)
    if not out["ok"]:
        print("作らなかった：" + "；".join(out["errors"]))
        return 1
    staff_id = out["ids"]["s"]
    print("作った：%s（役割 %s）" % (staff_id, a.role))
    print("field-ui を使うなら、続けて：uv run python scripts/staff_token.py add %s" % staff_id)
    return 0


def main(argv=None, driver=None):
    a = parse(argv)
    if driver is not None:
        return _run(driver, a)
    from nest import connections
    with connections.driver("personal") as d:
        return _run(d, a)


if __name__ == "__main__":
    sys.exit(main())
