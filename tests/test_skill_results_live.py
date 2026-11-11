"""止まる点 E-2（2026-11-06 河原さん）：架空の本人（displayCode あり）を一人ゲートで入れ、neo4j-support-db の照会 15 本を
読み取りの包み（mcp_guard.run_read）に通して、結果の中身が期待どおりかを確かめる。NEST_LIVE_DB=1 のときだけ。

    NEST_LIVE_DB=1 uv run pytest -q tests/test_skill_results_live.py

入れるのは架空のものだけ。資源の側には触れない。ほかの読み取りのスキルの照会も、この本人の仮名で包みを通す。
"""
import datetime as dt
import os
import re
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

from tests.test_gate_write_live import admin, driver  # noqa: E402,F401  フィクスチャ
from tests.test_read_skills_canon import LIVE_PARAMS, SKILLS, _queries  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
ORG = "ORG-01HZZZZZZZZZZZZZZZZZZZZZZZ"
TODAY = dt.date.today()


def _skill_queries():
    text = (REPO / "claude-skills" / "neo4j-support-db" / "SKILL.md").read_text(encoding="utf-8")
    found = {}
    for m in re.finditer(r"### (\d+)\.[^\n]*\n(?:[^`]*?)```cypher\n(.*?)```", text, re.S):
        found[int(m.group(1))] = m.group(2)
    return found


Q = _skill_queries()


def _rec(text, **more):
    return dict({"kind": "Interview", "text": text, "quote": text, "certainty": "Hearsay", "informantKind": "Family"}, **more)


@pytest.fixture(scope="module")
def fictional(driver, admin):
    """架空の本人と、15 本の照会がそれぞれ何かを返すだけの記録。返り値は ID と仮名"""
    from nest.gate import write as gw
    mark = uuid.uuid4().hex[:8]
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                     "nodes": [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空"}}],
                     "relationships": []}, driver)
    assert out["ok"], out["errors"]
    client = {"label": "Client", "id": out["ids"]["c"]}
    staff = {"label": "Staff", "id": admin}
    h = lambda ref, label, props: {"ref": ref, "label": label, "origin": "Human", "properties": props}  # noqa: E731
    nodes = [
        h("r0", "Record", _rec("架空の話 %s：母によると、エビを食べると息が苦しくなる" % mark, heardOn=str(TODAY))),
        h("r1", "Record", _rec("架空の話 %s：父によると、エビは平気だった" % mark)),
        h("cd", "Condition", {"name": "架空の特性 %s" % mark}),
        h("ng", "NgAction", {"action": "エビを食べさせる", "riskLevel": "LifeThreatening", "reason": "息が苦しくなる"}),
        h("ng2", "NgAction", {"action": "大きな音を立てる", "riskLevel": "Panic"}),
        h("cp", "CarePreference", {"category": "食事", "instruction": "献立を先に見せる", "priority": "High"}),
        h("w", "Wish", {"content": "架空の願い：海を見に行きたい"}),
        h("hi", "LifeHistory", {"episode": "架空の出来事：引っ越し", "era": "学齢期"}),
        h("ct", "Certificate", {"type": "IntellectualDisabilityHandbook", "grade": "B",
                                "nextRenewalDate": str(TODAY + dt.timedelta(days=30))}),
        h("pa", "PublicAssistance", {"type": "DisabilityBasicPension"}),
        h("s1", "SupportLog", {"date": str(TODAY - dt.timedelta(days=1)), "situation": "食事", "action": "献立を先に見せた",
                               "effectiveness": "Effective"}),
        h("s2", "SupportLog", {"date": str(TODAY - dt.timedelta(days=2)), "situation": "食事", "action": "献立を先に見せた",
                               "effectiveness": "Effective"}),
        h("p", "Person", {}),
        h("i", "Involvement", {"kind": "ServiceProvision", "howEnded": "Ongoing", "certainty": "Hearsay",
                               "serviceTypeName": "生活介護"}),
        h("org", "Organization", {"orgId": ORG}),
    ]
    rels = [{"type": "ABOUT", "from": r, "to": client} for r in ("r0", "r1", "s1", "s2")]
    rels += [{"type": "AUTHORED_BY", "from": r, "to": staff} for r in ("r0", "r1", "s1", "s2")]
    rels += [{"type": "TOLD_BY", "from": "r0", "to": "p"},
             {"type": "HAS_CONDITION", "from": client, "to": "cd"},
             {"type": "MUST_AVOID", "from": client, "to": "ng"}, {"type": "MUST_AVOID", "from": client, "to": "ng2"},
             {"type": "IN_CONTEXT", "from": "ng", "to": "cd"},
             {"type": "EVIDENCED_BY", "from": "ng", "to": "r0"}, {"type": "EVIDENCED_BY", "from": "ng2", "to": "r0"},
             {"type": "REQUIRES", "from": client, "to": "cp"}, {"type": "RESPONDS_TO", "from": "cp", "to": "cd"},
             {"type": "EVIDENCED_BY", "from": "cp", "to": "r0"},
             {"type": "HAS_WISH", "from": client, "to": "w"}, {"type": "HAS_HISTORY", "from": client, "to": "hi"},
             {"type": "HAS_CERTIFICATE", "from": client, "to": "ct"}, {"type": "RECEIVES", "from": client, "to": "pa"},
             {"type": "CONCERNS", "from": "i", "to": client}, {"type": "HAS_INVOLVEMENT", "from": "org", "to": "i"},
             {"type": "CONTRADICTS", "from": "r1", "to": "ng", "properties": {"claim": "エビは平気だったという話がある"}}]
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin, "nodes": nodes, "relationships": rels},
                    driver)
    assert out["ok"], out["errors"]
    ids = dict(out["ids"], client=client["id"])
    # キーパーソン（根拠の記録の ID が要るので二つ目の依頼）・承認待ちの AI 由来の記録・確認の記録。
    # 2026-11-12 河原さん（案 B）：AI 由来の記録と職員が作る続柄は別の依頼に分ける（混ぜると止まる。正典 v0.14 §7。台帳 G-102）
    out2 = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin, "nodes": [],
                      "relationships": [{"type": "RELATED_TO", "from": {"label": "Person", "id": ids["p"]}, "to": client,
                                         "properties": {"kind": "KeyPerson", "certainty": "Hearsay", "rank": 1,
                                                        "evidenceRecordIds": [ids["r0"]], "status": "Active"}}]},
                     driver)
    assert out2["ok"], out2["errors"]
    out3 = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                      "nodes": [{"ref": "ai", "label": "Record", "origin": "AiExtracted",
                                 "properties": _rec("架空の話 %s：未確定の話" % mark)}],
                      "relationships": [{"type": "ABOUT", "from": "ai", "to": client},
                                        {"type": "AUTHORED_BY", "from": "ai", "to": staff}]},
                     driver)
    assert out3["ok"], out3["errors"]
    ids["ai"] = out3["ids"]["ai"]
    rv = gw.record_review(driver, admin, client["id"], "Guardianship", dt.datetime.now(dt.timezone.utc).isoformat(),
                          "Family", [ids["r0"]], "req-" + uuid.uuid4().hex)
    assert rv["ok"], rv["errors"]
    from nest import mcp_guard
    rows = mcp_guard.run_read(driver, "MATCH (c:Client {clientId: $id}) RETURN c.displayCode AS code",
                              {"id": client["id"]}, personal=True)
    ids["code"] = rows[0]["code"]
    return ids


def _run(driver, n, **params):
    from nest import mcp_guard
    q = Q[n]
    return mcp_guard.run_read(driver, q, {k: v for k, v in params.items() if "$" + k in q}, personal=True)


def test_there_are_fifteen_queries():
    assert sorted(Q) == list(range(1, 16))


def test_q01_list_has_the_code(driver, fictional):
    assert {"code": fictional["code"], "status": "Active"} in _run(driver, 1)


def test_q02_ngactions_lifethreatening_first_with_evidence_and_contradiction(driver, fictional):
    rows = _run(driver, 2, code=fictional["code"])
    assert [r["riskLevel"] for r in rows] == ["LifeThreatening", "Panic"]
    top = rows[0]
    assert top["action"] == "エビを食べさせる" and top["status"] == "Active"
    assert [e["recordId"] for e in top["evidence"]] == [fictional["r0"]] and top["evidence"][0]["certainty"] == "Hearsay"
    assert top["openContradictions"] == 1 and len(top["conditions"]) == 1
    assert rows[1]["openContradictions"] == 0


def test_q03_carepreference_with_condition(driver, fictional):
    [row] = _run(driver, 3, code=fictional["code"])
    assert row["instruction"] == "献立を先に見せる" and row["priority"] == "High"
    assert len(row["conditions"]) == 1 and row["evidence"][0]["recordId"] == fictional["r0"]


def test_q04_conditions_wishes_history(driver, fictional):
    [row] = _run(driver, 4, code=fictional["code"])
    assert [w["content"] for w in row["wishes"]] == ["架空の願い：海を見に行きたい"]
    assert [h["era"] for h in row["history"]] == ["学齢期"] and row["conditions"][0]["status"] == "Active"


def test_q05_keyperson_rank_and_evidence(driver, fictional):
    [row] = _run(driver, 5, code=fictional["code"])
    assert row["personId"] == fictional["p"] and row["kind"] == "KeyPerson" and row["rank"] == 1
    assert row["evidenceRecordIds"] == [fictional["r0"]]


def test_q06_involvement_with_org(driver, fictional):
    [row] = _run(driver, 6, code=fictional["code"])
    assert row["kind"] == "ServiceProvision" and row["orgId"] == ORG and row["service"] == "生活介護"


def test_q07_certificate_and_assistance(driver, fictional):
    [row] = _run(driver, 7, code=fictional["code"])
    assert [c["type"] for c in row["certificates"]] == ["IntellectualDisabilityHandbook"]
    assert [a["type"] for a in row["assistance"]] == ["DisabilityBasicPension"]


def test_q08_renewal_within_days(driver, fictional):
    rows = _run(driver, 8, days=60)
    assert any(r["code"] == fictional["code"] for r in rows)
    assert not any(r["code"] == fictional["code"] for r in _run(driver, 8, days=10))


def test_q09_review_domain(driver, fictional):
    rows = _run(driver, 9, code=fictional["code"])
    assert [r["domain"] for r in rows] == ["Guardianship"] and rows[0]["informantKinds"] == ["Family"]


def test_q10_supportlogs_newest_first(driver, fictional):
    rows = _run(driver, 10, code=fictional["code"], limit=5)
    assert [r["id"] for r in rows] == [fictional["s1"], fictional["s2"]]


def test_q11_effective_pattern(driver, fictional):
    assert _run(driver, 11, code=fictional["code"]) == [
        {"situation": "食事", "action": "献立を先に見せた", "times": 2, "lastDate": str(TODAY - dt.timedelta(days=1))}]


def test_q12_evidence_and_told_by(driver, fictional):
    [row] = _run(driver, 12, code=fictional["code"], id=fictional["ng"])
    assert row["recordId"] == fictional["r0"] and row["toldBy"] == fictional["p"] and row["kind"] == "Interview"


def test_q13_pending_ai_record_listed(driver, fictional):
    rows = _run(driver, 13)
    assert {"label": "Record", "id": fictional["ai"]} in [{"label": r["label"], "id": r["id"]} for r in rows]


def test_q14_open_contradiction(driver, fictional):
    [row] = _run(driver, 14, code=fictional["code"])
    assert row["label"] == "NgAction" and row["recordId"] == fictional["r1"] and row["claim"]


def test_q15_audit_log(driver, fictional):
    rows = _run(driver, 15, code=fictional["code"], limit=100)
    assert rows and all(r["staffId"] for r in rows)
    # 操作の記録は対象のノードに結ばれる。本人そのものだけでなく、本人につながる禁忌・記録などの操作も出る
    assert {"Create", "RaiseContradiction", "LinkEvidence"} <= {r["action"] for r in rows}
    assert {"Client", "NgAction", "Record"} <= {r["targetLabel"] for r in rows}


@pytest.mark.parametrize("skill", SKILLS)
def test_other_skill_queries_run_with_the_fictional_code(driver, fictional, skill):
    from nest import mcp_guard
    params = dict(LIVE_PARAMS, code=fictional["code"], id=fictional["ng"], orgIds=[ORG])
    for where, side, q in _queries(skill):
        if side != "personal":
            continue
        mcp_guard.run_read(driver, q, {k: v for k, v in params.items() if "$" + k in q}, personal=True)
