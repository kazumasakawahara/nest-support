"""N-25：narrative-extractor の書き直し。書き込みの案（JSON）を出すだけ。DB を使わない。

- スキルの本文に、Cypher の書き込み（CREATE・MERGE・SET・DELETE）と、名前で既にいる人に結び付ける指示が無い
- スキルの本文の例（架空の原文と案）が、入口の点検（nest/gate/intake.py）とゲートの検証（validate.py）を通る
- 語りの中の人は役割の名前で書く（SEMANTICS SEM-REC-01）。案に実名を書かない
"""
import json
import re
from pathlib import Path

from nest.gate import intake
from nest.gate import validate as gv

REPO = Path(__file__).resolve().parents[1]
SKILL = (REPO / "claude-skills" / "narrative-extractor" / "SKILL.md").read_text(encoding="utf-8")
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"


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
    original = _block("example-original", "text")
    proposal = json.loads(_block("example-proposal", "json"))
    assert "架空" in original
    rep = intake.check(proposal, original, actor_staff_id=ACTOR, request_id="req-n25")
    assert rep["ok"], rep["errors"]
    out = gv.validate(rep["request"])
    assert out["ok"], out["errors"]
    assert {n["status"] for n in out["nodes"]} == {"Pending"}


def test_example_has_an_ngaction_candidate_that_enters_pending():
    """G-63：架空の例に禁忌の候補を一つ。入口の点検とゲートを通って Pending。"""
    original = _block("example-original", "text")
    proposal = json.loads(_block("example-proposal", "json"))
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
