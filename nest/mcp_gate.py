"""書き込み受付の MCP（ADR-002 D1・D2・D6。段階 L の L-1 の最初の一つ）。新しい個人の側（127.0.0.1:37687）にだけつなぐ。

- 照会口（nest/mcp_personal.py）とは別のプロセス。照会口に書く道具を足さない
- 道具は submit_proposal だけ（承認・差し戻しは L-2 で足す。それまでは scripts/review_proposals.py）
- 職員の ID は道具の引数で受けない。環境変数 NEST_GATE_STAFF_ID か ~/.config/nest/nest-gate.env から読む（中身は Claude に読ませない）。
  Claude が別の人の名で案を出す余地を作らない
- 照会口と同じ歯止め（mcp_guard.require_personal_allowed）を通す：NEXT-02 がそろうか、架空の印のある DB のときだけ動く
- 書くのはゲート（nest/gate/）だけ。通った案は未確定（Pending）で入る。返すのは仮名・件数・新しい ID・理由だけで、実名も clientId も返さない。
  入れた先の仮名と件数は、通っても止まっても（0 件）必ず返す（summary・code・pending・counts。2026-11-10 河原さん）

起動：uv run --quiet python -m nest.mcp_gate
"""
import os
from pathlib import Path

from mcp.server import MCPServer

from nest import ids, mcp_guard
from nest.gate import proposal

CONFIG = Path.home() / ".config" / "nest" / "nest-gate.env"
KEY = "NEST_GATE_STAFF_ID"
AGAIN = ("何も書いていない。止めた理由のとおりに案を作り直し、もう一度 submit_proposal で出す"
         "（理由を読み替えて通さない。JSON を人が手で直さない）")
DONE = "未確定（Pending）で入れた。承認は職員が一件ずつ、引用を見てから行う（今は scripts/review_proposals.py）"

server = MCPServer("nest-gate")


def staff_id():
    """この Mac の専門職の Staff ID。環境変数、無ければ設定のファイルから読む。"""
    value = os.environ.get(KEY)
    if not value and CONFIG.is_file():
        from dotenv import dotenv_values
        value = dotenv_values(CONFIG).get(KEY)
    if not value:
        raise RuntimeError("%s が設定されていない（%s）。管理者が設定する" % (KEY, CONFIG))
    if not ids.is_valid_id(value, "STF"):
        raise RuntimeError("%s は職員の ID（STF-…）でなければならない（%s）。管理者が直す" % (KEY, CONFIG))
    return value


def _submit(driver, code, original, proposal_):
    mcp_guard.require_personal_allowed(driver)
    out = proposal.submit(driver, staff_id(), code, original, proposal_)
    if out["ok"]:
        parts = "・".join("%s %d" % (k, v) for k, v in sorted(out["counts"].items()))
        summary = "%s に未確定（Pending）で %d 件入れた（%s）" % (code, out["pending"], parts)
    else:
        out = dict(out, pending=0, counts={})
        summary = "%s には何も入れていない（0 件）" % code
    return dict(out, code=code, summary=summary, next=DONE if out["ok"] else AGAIN)


@server.tool()
def submit_proposal(code: str, original: str, proposal: dict) -> dict:
    """書き込みの案（narrative-extractor の JSON）を、入口の点検とゲートに通し、未確定（Pending）で入れる。

    呼ぶ前に、対象の本人の仮名（C-……）を職員に復唱して確かめ、「はい」を得てから呼ぶ（取り違えを防ぐ）。
    code は本人の仮名、original は職員が渡した原文（引用の照合と指紋にだけ使い、DB に入れない）、proposal は案。
    返り値の summary（入れた先の仮名と件数）は、通っても止まっても、そのまま職員に伝える。復唱した仮名と同じかを職員が確かめる。
    返り値の ok が偽なら何も書いていない。errors の理由を職員に示し、理由のとおりに案を作り直して出し直す。
    stage は止まった場所（input：案の形・本人の指定、intake：入口の点検、gate：ゲート）。"""
    from nest import connections
    with connections.driver("personal") as d:
        return _submit(d, code, original, proposal)


if __name__ == "__main__":
    server.run()
