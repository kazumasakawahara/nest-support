"""N-46 詰まり #7（2026-11-09 河原さん。台帳 G-94）：書き込みの案を、職員が手元で入口の点検とゲートに通す道具
（scripts/submit_proposal.py）。DB を使わない部分（ゲートの書き込みは差し替えて、渡された依頼を見る）。

- つなぎの道具。段階 L の L-1 でゲート MCP ができたら外す（ファイルの頭と台帳に書く）
- 本人は仮名（--code）で指し、道具が個人の側から clientId を引いて案に入れる
- 点検で止まる案（原文に無い語を quote に含む）はゲートに渡らない（Pending に入らない）
- 通った案は、AI 由来（Pending）の依頼になってゲートに渡る。review_proposals.py list が数える種類に入る
- 原文（--original）は引用の照合と指紋にだけ使う。原文そのものは依頼に入れない（DB に入るのは text と quote）
- 今は自分の記録（OwnCaseRecord）だけ。書面（ProvisionDocument）は止める
DB を使う確かめ（入れたものが review_proposals.py list に並ぶ）は tests/test_submit_proposal_live.py。
"""
import json

import pytest

from doc_commands import REPO, argv, lines, load
from nest.gate import validate as gv

STAFF = "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"
CLIENT = "CLI-01BBBBBBBBBBBBBBBBBBBBBBBB"
CODE = "C-ZZZZZZ"
PRIVATE = "この行は案に引用しない、原文にだけある行（架空）"
ORIGINAL = "架空の面談記録\n本人は、音楽を聴くと落ち着くと話した【本人の話】\n%s\n" % PRIVATE


def _proposal(**over):
    p = {"documentKind": "OwnCaseRecord",
         "facts": [{"quote": "本人は、音楽を聴くと落ち着くと話した", "recordKind": "Interview",
                    "certainty": "SelfReport", "informantKind": "Self", "toldBy": "client"}]}
    p.update(over)
    return p


class FakeDriver:
    """仮名から clientId を引く照会だけに答える"""

    def __init__(self, known=True):
        self.known = known

    def execute_query(self, query, params=None, **kw):
        class R(dict):
            pass
        if "displayCode" in query and self.known and (params or {}).get("code") == CODE:
            return [R(id=CLIENT)], None, None
        return [], None, None


@pytest.fixture
def run(tmp_path, monkeypatch):
    from nest.gate import write as gw
    sent = []

    def fake_submit(req, driver, **kw):
        sent.append(req)
        return {"ok": True, "errors": [], "ids": {}}
    monkeypatch.setattr(gw, "submit", fake_submit)

    def _run(proposal, original=ORIGINAL, code=CODE, driver=None):
        o, p = tmp_path / "original.txt", tmp_path / "proposal.json"
        o.write_text(original, encoding="utf-8")
        p.write_text(json.dumps(proposal, ensure_ascii=False), encoding="utf-8")
        rc = load("submit_proposal.py").main(["--staff", STAFF, "--code", code, "--original", str(o),
                                              "--proposal", str(p)], driver=driver or FakeDriver())
        return rc, sent
    return _run


def test_rejected_proposal_does_not_reach_the_gate(run, capsys):
    """点検で止まる案（原文に無い語を quote に含む）は Pending に入らない"""
    bad = _proposal(facts=[{"quote": "本人は、ジャズを聴くと落ち着くと話した", "recordKind": "Interview",
                            "certainty": "SelfReport", "informantKind": "Self"}])
    rc, sent = run(bad)
    assert rc == 1 and sent == []
    assert "原文に無い" in capsys.readouterr().out


def test_passed_proposal_goes_to_the_gate_as_pending(run, capsys):
    """通った案は AI 由来の依頼でゲートに渡り、ゲートの検証で Pending になる。review_proposals が数える種類"""
    rc, sent = run(_proposal())
    assert rc == 0 and len(sent) == 1
    req = sent[0]
    rep = gv.validate(req)
    assert rep["ok"], rep["errors"]
    records = [n for n in rep["nodes"] if n["label"] == "Record"]
    assert records and all(n["status"] == "Pending" for n in records)
    assert {"label": "Client", "id": CLIENT} in [r["to"] for r in req["relationships"] if r["type"] == "ABOUT"]
    rp = load("review_proposals.py")
    assert "Record" in rp.ap.DECIDABLE
    assert "review_proposals.py list" in capsys.readouterr().out


def test_original_itself_is_not_in_the_request(run):
    """原文は照合と指紋にだけ使う。原文の引用していない行は依頼のどこにも無い。本文は text か quote"""
    rc, sent = run(_proposal())
    assert rc == 0
    dumped = json.dumps(sent[0], ensure_ascii=False)
    assert PRIVATE not in dumped and "架空の面談記録" not in dumped
    rec = next(n for n in sent[0]["nodes"] if n["label"] == "Record")["properties"]
    assert rec["text"] == rec["quote"] == "本人は、音楽を聴くと落ち着くと話した"


def test_provision_document_is_stopped_for_now(run):
    rc, sent = run(_proposal(documentKind="ProvisionDocument", providerName="架空の家ひだまり"))
    assert rc == 1 and sent == []


def test_unknown_code_is_stopped(run):
    rc, sent = run(_proposal(), driver=FakeDriver(known=False))
    assert rc == 1 and sent == []


def test_a_different_client_id_in_the_proposal_is_stopped(run):
    rc, sent = run(_proposal(clientId="CLI-01CCCCCCCCCCCCCCCCCCCCCCCC"))
    assert rc == 1 and sent == []


def test_placeholder_client_id_is_filled_from_the_code(run):
    rc, sent = run(_proposal(clientId="CLI-…"))
    assert rc == 0 and len(sent) == 1


def test_the_tool_says_it_is_a_bridge_until_l1():
    head = (REPO / "scripts" / "submit_proposal.py").read_text(encoding="utf-8").split('"""')[1]
    assert "つなぎ" in head and "L-1" in head and "G-94" in head
    ledger = (REPO / "docs" / "gray-decisions.md").read_text(encoding="utf-8")
    row = next(l for l in ledger.splitlines() if l.startswith("| G-94 "))
    assert "submit_proposal" in row and "つなぎ" in row and "L-1" in row


def test_doc_command_parses_with_the_tool():
    """手順書の submit_proposal の行を、そのまま道具の引数にできる"""
    line = lines("submit_proposal.py")
    assert line
    a = load("submit_proposal.py").parse(argv(line[0], {"STF-…": STAFF, "C-……": CODE}))
    assert a.staff == STAFF and a.code == CODE and a.original and a.proposal


def _section(head):
    t = (REPO / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    i = t.index(head)
    return t[i:t.index("\n## ", i)]


def test_section_4_5_sits_between_4_and_5_and_covers_a_b_c():
    t = (REPO / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    assert t.index("## 4.") < t.index("## 4.5") < t.index("## 5.")
    s = _section("## 4.5")
    for word in ("configs/claude_desktop_config.json", "Library/Application Support/Claude/claude_desktop_config.json",
                 "起動し直", "[10]", "narrative-extractor", "submit_proposal.py", "review_proposals.py list",
                 "§2", "§1", "貼りません", "原文", "DB に入れません"):
        assert word in s, word


def test_section_0_points_to_4_5():
    assert "4.5" in _section("## 0.")


# N-46 #7 の続き（2026-11-09 河原さん）：架空の事例の確度の印を、各文の直後に置き、語彙を点検の印にそろえた。
# §2 の語りの各文を引用にした案を、文の直後の印から確度を決めて通すと、点検が止まらない。

MARK_AT_END = __import__("re").compile(r"【([^】]+)】$")


def _sentences(paragraph):
    """「。」で文に分ける。かぎかっこ・丸かっこの中の「。」では分けない。文の直後の【…】は前の文に付ける"""
    out, buf, depth = [], "", 0
    for ch in paragraph:
        if buf == "" and ch == "【" and out:
            out[-1] += ch
            buf = None
            continue
        if buf is None:
            out[-1] += ch
            if ch == "】":
                buf = ""
            continue
        buf += ch
        depth += ch in "「（" and 1 or 0
        depth -= ch in "」）" and 1 or 0
        if ch == "。" and depth == 0:
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out


def _fixture_section(n):
    t = (REPO / "fixture_kakuu_haruto.md").read_text(encoding="utf-8")
    i = t.index("## %d." % n)
    body = t[t.index("\n", i) + 1:t.index("\n## ", i)]
    return body


def test_fixture_section_2_passes_the_intake_check(run, capsys):
    from nest import semantics
    marks = dict(semantics.certainty_marks())
    body = _fixture_section(2)
    facts = []
    for para in [p.strip() for p in body.split("\n") if p.strip()]:
        for s in _sentences(para):
            m = MARK_AT_END.search(s)
            quote = MARK_AT_END.sub("", s)
            assert m is None or m.group(1) in marks, "知らない印：%s" % s
            facts.append({"quote": quote, "recordKind": "Interview", "informantKind": "Family",
                          "certainty": marks[m.group(1)] if m else "Unspecified"})
    assert len(facts) > 10
    rc, sent = run(_proposal(facts=facts), original=body)
    assert rc == 0, capsys.readouterr().out
    assert len(sent) == 1


@pytest.mark.parametrize("n", [2, 3])
def test_fixture_marks_follow_the_sentence(n):
    """印は文の直後に置く（文の前に置かない）。語彙は点検の印だけ"""
    from nest import semantics
    words = {w for w, _ in semantics.certainty_marks()}
    body = _fixture_section(n)
    for para in [p.strip() for p in body.split("\n") if p.strip()]:
        assert not para.startswith("【"), para[:20]
        for s in _sentences(para):
            assert "【" not in MARK_AT_END.sub("", s), "文の途中か前に印がある：%s" % s[:30]
    found = set(__import__("re").findall(r"【([^】]+)】", body))
    assert found and found <= words, found - words


def test_section_4_5_says_where_and_which_marks():
    """4.5 (b)：印は文の直後に、点検が読む 5 つのどれかを置く"""
    s = _section("## 4.5")
    assert "文の直後" in s
    for word in ("【本人の話】", "【伝聞】", "【確認済み】", "【未確認】", "【推測】"):
        assert word in s, word


def test_fixture_section_2_passes_even_if_quotes_drop_the_full_stop(run, capsys):
    """引用が文末の句点を落としても、点検は句点の後の印を読む（mark_of。2026-11-09 河原さん）"""
    from nest import semantics
    marks = dict(semantics.certainty_marks())
    body = _fixture_section(2)
    facts = []
    for para in [p.strip() for p in body.split("\n") if p.strip()]:
        for s in _sentences(para):
            m = MARK_AT_END.search(s)
            facts.append({"quote": MARK_AT_END.sub("", s).rstrip("。"), "recordKind": "Interview",
                          "informantKind": "Family", "certainty": marks[m.group(1)] if m else "Unspecified"})
    rc, sent = run(_proposal(facts=facts), original=body)
    assert rc == 0, capsys.readouterr().out


# N-46 詰まり #9（2026-11-09 河原さん）：ゲートで止まった（informantKind が無い事実）とき、どう直すかが
# 道具の出力にも手順書 4.5 (c) にも無かった。人は JSON を手で直さず、Claude Desktop に作り直しを頼む。

def test_gate_stop_tells_how_to_fix(tmp_path, monkeypatch, capsys):
    from nest.gate import write as gw

    def gate(req, driver, **kw):
        rep = gv.validate(req)
        return {"ok": rep["ok"], "errors": rep["errors"], "ids": {}}
    monkeypatch.setattr(gw, "submit", gate)
    o, p = tmp_path / "original.txt", tmp_path / "proposal.json"
    o.write_text(ORIGINAL, encoding="utf-8")
    p.write_text(json.dumps(_proposal(facts=[{"quote": "本人は、音楽を聴くと落ち着くと話した", "recordKind": "Interview",
                                              "certainty": "SelfReport"}]), ensure_ascii=False), encoding="utf-8")
    rc = load("submit_proposal.py").main(["--staff", STAFF, "--code", CODE, "--original", str(o), "--proposal", str(p)],
                                         driver=FakeDriver())
    out = capsys.readouterr().out
    assert rc == 1 and "止めた（ゲート）" in out and "informantKind" in out
    assert "何も書いていない" in out and "Claude" in out and "作り直" in out


def test_section_4_5_c_says_ask_claude_to_remake_not_edit_json():
    s = _section("## 4.5")
    c = s[s.index("### (c)"):]
    for word in ("止めた（ゲート）", "手で直さない", "作り直して", "打ち直します"):
        assert word in c, word
