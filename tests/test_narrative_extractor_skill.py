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


def test_the_skill_states_the_ref_rule_with_an_example():
    """段階 L の確かめ（2026-11-11）の詰まり 3：名札の決まりを入口の点検と同じ言い方で一行。"""
    from nest.gate import intake
    text = SKILL
    assert "英小文字で始め、英字・数字・ハイフンだけ" in text and "`supportWorker`" in text
    for ref in ("mother", "supportWorker", "sister-2"):
        assert intake.REF.match(ref) and not intake.RESERVED_REF.match(ref)


# ---- 2026-11-11：関わりを資源の側の機関に結ぶ一往復 ----

def test_the_proposal_shape_has_org_name_and_service_type():
    shape = _skill_section("案の形")
    assert '"orgName"' in shape and '"serviceTypeName"' in shape


def test_the_skill_writes_the_org_name_only_as_in_the_quote_and_no_org_id():
    rules = _skill_section("守ること")
    assert "orgName" in rules and "引用" in rules and "serviceTypeName" in rules


def test_the_skill_asks_the_staff_to_choose_and_never_chooses_itself():
    steps = _skill_section("手順")
    for words in ("orgChoices", "番号", "自分で選ばない", "一件でも", "「無い」", "link_organization", "所在地", "サービスの種類"):
        assert words in steps, words
    assert steps.index("submit_proposal を呼ぶ") < steps.index("link_organization")



def test_the_skill_writes_ongoing_only_when_the_original_says_so():
    """2026-11-12（案 A）：名前のある関わりに howEnded は Ongoing だけ。推し量って書かない。終わった関わりは事実だけ残す"""
    shape = _skill_section("案の形")
    assert '"howEnded"' in shape
    rules = _skill_section("守ること")
    for words in ("howEnded", "`Ongoing`", "推し量", "終わった関わり", "事実"):
        assert words in rules, words


def test_the_skill_says_which_record_kind_a_contact_sentence_takes():
    """2026-11-12 河原さん：接触そのものを述べる一文（記録者がしたこと・見たこと）は Observation、相手が語った中身は Interview。
    昨日「ぶれ」と書いたが、Claude は一貫して分けていた。決まりが書かれていなかった"""
    rules = _skill_section("守ること")
    for words in ("接触そのもの", "電話で聞き取りました", "`Observation`", "語った中身", "とのこと", "`Interview`"):
        assert words in rules, words
    proposal = json.loads(_block("example-proposal", "json"))
    contact = proposal["supportLog"]["quote"]
    (fact,) = [f for f in proposal["facts"] if f["quote"] == contact]
    assert fact["recordKind"] == "Observation"  # 例の接触の一文も同じ決まり


VIEW_KIND = {"Self": "Interview", "Family": "Interview", "Neighbor": "Interview", "Agency": "Observation",
             "DocumentOnly": "Document"}


def test_the_view_takes_the_record_kind_of_its_source():
    """2026-11-12 河原さん（台帳 G-100。L-0 の案 2-B の一文を正典に写した）：見立ての記録の種類は、もとになった情報に合わせる。
    Self・Family なら Interview、Agency（記録者の観察）なら Observation、書面だけなら Document"""
    rules = _skill_section("守ること")
    for words in ("見立て", "もとになった情報", "`Self`・`Family`・`Neighbor` なら `Interview`", "`Agency`", "`Observation`",
                  "`DocumentOnly`", "`Document`", "記録の種類に見立ての意味を持たせない"):
        assert words in rules, words
    proposal = json.loads(_block("example-proposal", "json"))
    (view,) = [f for f in proposal["facts"] if f["certainty"] == "Inference"]
    assert view["recordKind"] == VIEW_KIND[view["informantKind"]]
