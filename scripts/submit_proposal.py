"""書き込みの案（narrative-extractor が作った JSON）を、職員が手元で入口の点検とゲートに通す（N-46 詰まり #7。2026-11-09 河原さん）。

**つなぎの道具。段階 L の L-1 で書き込み受付（ゲート MCP）ができたら外す（台帳 G-94）。**
中身は nest/gate/proposal.py に移し、書き込み受付の MCP（nest/mcp_gate.py の submit_proposal）と同じものを呼ぶ（2026-11-10）。
外すまでは、Claude Desktop が使えないときの予備として残す。

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
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest.gate import proposal  # noqa: E402

AGAIN = "何も書いていない。JSON を手で直さず、止めた行をそのまま Claude Desktop に貼って案を作り直してもらう"


def parse(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--staff", required=True, help="通す職員の ID（STF-…）")
    ap.add_argument("--code", required=True, help="本人の仮名（C-……）")
    ap.add_argument("--original", required=True, help="原文のファイル（Claude に貼ったのと同じ文）")
    ap.add_argument("--proposal", required=True, help="案のファイル（JSON）")
    return ap.parse_args(argv)


def _run(d, a):
    data = json.loads(Path(a.proposal).read_text(encoding="utf-8"))
    original = Path(a.original).read_text(encoding="utf-8")
    out = proposal.submit(d, a.staff, a.code, original, data)
    for w in out["warnings"]:
        print("注意：" + w)
    if out["ok"]:
        print("未確定（Pending）で入れた：%d 件。次に見る：uv run python scripts/review_proposals.py list" % out["pending"])
        return 0
    if out["stage"] == "gate":
        print("止めた（ゲート）：" + "；".join(out["errors"]))
    else:
        for e in out["errors"]:
            print("止めた：" + e)
    if out["stage"] != "input":
        print(AGAIN)
    return 1


def main(argv=None, driver=None):
    a = parse(argv)
    if driver is not None:
        return _run(driver, a)
    from nest import connections
    with connections.driver("personal") as d:
        return _run(d, a)


if __name__ == "__main__":
    sys.exit(main())
