"""N-25：narrative-extractor の書き直し。書き込みの案（JSON）を出すだけ。DB を使わない。

- スキルの本文に、Cypher の書き込み（CREATE・MERGE・SET・DELETE）と、名前で既にいる人に結び付ける指示が無い
- スキルの本文の例（架空の原文と案）が、入口の点検（nest/gate/intake.py）とゲートの検証（validate.py）を通る
- 語りの中の人は役割の名前で書く（SEMANTICS SEM-REC-01）。案に実名を書かない
2026-11-10（段階 L の L-1。確認点 L-0）：書き込み受付の MCP（nest-gate の submit_proposal）を呼ぶ形に直した。
- 呼ぶ前に対象の仮名を職員に復唱して確かめる（L-0 の論点 7 (b)）。clientId は書かない（道具が仮名から入れる）
- 止まったら理由を職員に示し、理由のとおりに案を作り直して出し直す
- 面接記録は supportLog、見立ては certainty Inference と情報源（SEM-REC-04）。例にも入れる
"""
import json
import re
from pathlib import Path

from nest.gate import intake
from nest.gate import validate as gv

REPO = Path(__file__).resolve().parents[1]
SKILL = (REPO / "claude-skills" / "narrative-extractor" / "SKILL.md").read_text(encoding="utf-8")
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"


def _example():
    """例の案には clientId が無い（道具が仮名から入れる）。点検に掛けるときは道具と同じく入れる。"""
    proposal = json.loads(_block("example-proposal", "json"))
    assert "clientId" not in proposal
    return _block("example-original", "text"), dict(proposal, clientId=CLIENT)


def _block(marker, lang):
    m = re.search(r"<!-- %s -->\s*```%s\n(.*?)```" % (re.escape(marker), lang), SKILL, re.S)
    assert m, marker
    return m.group(1)


def test_no_cypher_writes_and_no_name_merging():
    assert "```cypher" not in SKILL.lower()
    for word in ("CREATE (", "MERGE (", "DETACH DELETE", "execute_query"):
        assert word not in SKILL, word
    for phrase in ("同一エンティティに統合", "Neo4j を検索して既存ノードと突合"):
        assert phrase not in SKILL, phrase


def test_skill_states_the_rules():
    for words in (("案", "JSON", "だけ"), ("役割の名前", "SEM-REC-01"), ("原文", "quote"), ("【", "確度"),
                  ("ゲート", "Pending"), ("架空",)):
        assert all(w in SKILL for w in words), words


def test_example_passes_intake_and_the_gate():
    original, proposal = _example()
    assert "架空" in original
    rep = intake.check(proposal, original, actor_staff_id=ACTOR, request_id="req-n25")
    assert rep["ok"], rep["errors"]
    out = gv.validate(rep["request"])
    assert out["ok"], out["errors"]
    assert {n["status"] for n in out["nodes"]} == {"Pending"}


def test_example_has_an_ngaction_candidate_that_enters_pending():
    """G-63：架空の例に禁忌の候補を一つ。入口の点検とゲートを通って Pending。"""
    original, proposal = _example()
    assert len(proposal.get("ngActions") or []) == 1
    rep = intake.check(proposal, original, actor_staff_id=ACTOR, request_id="req-n25")
    out = gv.validate(rep["request"])
    assert [n["status"] for n in out["nodes"] if n["label"] == "NgAction"] == ["Pending"]


def test_skill_states_the_two_stages():
    for words in (("ngActions", "carePreferences"), ("同じ案", "根拠"), ("禁忌の候補", "事実として残")):
        assert all(w in SKILL for w in words), words


def test_example_has_no_real_names():
    proposal = json.loads(_block("example-proposal", "json"))
    for person in proposal.get("newPeople") or []:
        assert set(person) == {"ref"}, person


def _skill_section(title):
    start = SKILL.index("## " + title)
    end = SKILL.find("\n## ", start + 1)
    return SKILL[start:end]


def test_the_skill_calls_the_write_intake_tool():
    steps = _skill_section("手順")
    assert "submit_proposal" in steps and "nest-gate" in steps
    assert "DB には書かない" in SKILL or "Claude は DB に書かない" in SKILL


def test_the_skill_repeats_the_pseudonym_before_calling():
    steps = _skill_section("手順")
    assert "仮名" in steps and "復唱" in steps and "はい" in steps
    assert steps.index("復唱") < steps.index("submit_proposal を呼ぶ")


def test_the_skill_remakes_the_proposal_with_the_reasons_when_stopped():
    steps = _skill_section("手順")
    for words in ("止まった", "理由", "そのまま", "作り直", "出し直"):
        assert words in steps, words
    assert "読み替えない" in steps


def test_the_skill_does_not_ask_for_a_client_id():
    assert "clientId は書かない" in SKILL


def test_the_example_has_an_interview_record_and_a_view():
    original, proposal = _example()
    log = proposal["supportLog"]
    assert log["contactKind"] in ("Visit", "OfficeVisit", "Phone", "Accompaniment", "Meeting", "Correspondence")
    views = [f for f in proposal["facts"] if f["certainty"] == "Inference"]
    assert len(views) == 1 and views[0]["informantKind"] and "toldBy" not in views[0]
    rep = intake.check(proposal, original, actor_staff_id=ACTOR, request_id="req-l1")
    out = gv.validate(rep["request"])
    assert [n["status"] for n in out["nodes"] if n["label"] == "SupportLog"] == ["Pending"]


def test_the_skill_states_the_l0_rules():
    for words in (("supportLog", "面接 1 回"), ("見立て", "Inference", "もとになった"), ("effectiveness", "書かない"),
                  ("SEM-REC-04",), ("toldBy", "concerns", "新しい人")):
        assert all(w in SKILL for w in words), words


def test_the_skill_tells_the_pseudonym_and_count_from_the_reply():
    steps = _skill_section("手順")
    assert "summary" in steps and "仮名と件数" in steps
