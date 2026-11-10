"""書き込みの案（narrative-extractor が作った JSON）を、職員が手元で入口の点検とゲートに通す（N-46 詰まり #7。2026-11-09 河原さん）。

**つなぎの道具。段階 L の L-1 で書き込み受付（ゲート MCP）ができたら外す（台帳 G-94）。**

- 本人は仮名（--code）で指す。道具が個人の側から clientId を引いて案に入れる（案の clientId が空か「CLI-…」のままなら入れ、
  別の本人の ID が書いてあれば止める）
- 入口の点検（nest.gate.intake.check）→ ゲート（nest.gate.write.submit）の順に通す。点検で止まったら理由を出し、何も書かない
- 通った案は AI 由来なので、未確定（Pending）で入る。承認は review_proposals.py で一つずつ
- 原文（--original）は、引用（quote）の照合と原本の指紋（documentHash）にだけ使う。原文そのものは DB に入れない
  （入るのは、事実ごとの要約 text と引用 quote）
- 今は自分の記録（OwnCaseRecord）だけを受ける。情報提供の書面（ProvisionDocument）と、担当機関の推定は止める

使い方:
  uv run python scripts/submit_proposal.py --staff STF-… --code C-…… --original 原文.txt --proposal 案.json
"""
import argparse
import json
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest import ids  # noqa: E402
from nest.gate import intake  # noqa: E402
from nest.gate import write as gw  # noqa: E402

CLIENT_OF = "MATCH (c:Client {displayCode: $code}) RETURN c.clientId AS id"
AGAIN = "何も書いていない。JSON を手で直さず、止めた行をそのまま Claude Desktop に貼って案を作り直してもらう"


def parse(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--staff", required=True, help="通す職員の ID（STF-…）")
    ap.add_argument("--code", required=True, help="本人の仮名（C-……）")
    ap.add_argument("--original", required=True, help="原文のファイル（Claude に貼ったのと同じ文）")
    ap.add_argument("--proposal", required=True, help="案のファイル（JSON）")
    return ap.parse_args(argv)


def _run(d, a):
    proposal = json.loads(Path(a.proposal).read_text(encoding="utf-8"))
    original = Path(a.original).read_text(encoding="utf-8")
    if not isinstance(proposal, dict):
        print("止めた：案は JSON のオブジェクト")
        return 1
    if proposal.get("documentKind") != "OwnCaseRecord":
        print("止めた：今は自分の記録（OwnCaseRecord）だけを受ける（書面は段階 L で）")
        return 1
    records, _, _ = d.execute_query(CLIENT_OF, {"code": a.code}, database_="neo4j")
    if not records:
        print("止めた：仮名 %s の本人がいない" % a.code)
        return 1
    client_id = records[0]["id"]
    written = proposal.get("clientId")
    if ids.is_valid_id(written, "CLI") and written != client_id:
        print("止めた：案の clientId が仮名 %s の本人と違う" % a.code)
        return 1
    proposal["clientId"] = client_id
    checked = intake.check(proposal, original, a.staff, "req-proposal-" + uuid.uuid4().hex)
    for w in checked["warnings"]:
        print("注意：" + w)
    if not checked["ok"]:
        for e in checked["errors"]:
            print("止めた：" + e)
        print(AGAIN)
        return 1
    out = gw.submit(checked["request"], d)
    if not out["ok"]:
        print("止めた（ゲート）：" + "；".join(out["errors"]))
        print(AGAIN)
        return 1
    n = sum(1 for node in checked["request"]["nodes"] if node["origin"] == "AiExtracted")
    print("未確定（Pending）で入れた：%d 件。次に見る：uv run python scripts/review_proposals.py list" % n)
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
