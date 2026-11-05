"""N-20：ゲートの書き込みを、起動した個人の側（127.0.0.1:37687）で確かめる。NEST_LIVE_DB=1 のときだけ。

    NEST_LIVE_DB=1 uv run pytest -q tests/test_gate_write_live.py

入れるのは架空のものだけ。資源の側には触れない。試験ごとに印（uuid）を付けた文を使い、前の試験の残りと混ざらないようにする。
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")


@pytest.fixture(scope="module")
def driver():
    from nest import connections
    with connections.driver("personal") as d:
        d.verify_connectivity()
        yield d


def _one(driver, query, **params):
    records, _, _ = driver.execute_query(query, params, routing_="r", database_="neo4j")
    return [r.data() for r in records]


def _count(driver, query, **params):
    return _one(driver, query, **params)[0]["n"]


@pytest.fixture(scope="module")
def admin(driver):
    """最初の管理者。いなければ bootstrap で作る。いれば Active な Administrator を使う。"""
    from nest.gate import bootstrap
    rows = _one(driver, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")
    if rows:
        return rows[0]["id"]
    out = bootstrap.bootstrap_admin(driver, "架空の管理者", "req-bootstrap-" + uuid.uuid4().hex)
    assert out["ok"], out["errors"]
    return out["staffId"]


@pytest.fixture
def client(driver, admin):
    from nest.gate import write as gw
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                     "nodes": [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空"}}],
                     "relationships": []}, driver)
    assert out["ok"], out["errors"]
    return out["ids"]["c"]


def _record(text):
    return {"kind": "Interview", "text": text, "quote": text, "certainty": "Hearsay", "informantKind": "Family"}


def _records_req(admin, client, texts, request_id=None):
    nodes, rels = [], []
    for n, t in enumerate(texts):
        nodes.append({"ref": "r%d" % n, "label": "Record", "origin": "AiExtracted", "properties": _record(t)})
        rels.append({"type": "ABOUT", "from": "r%d" % n, "to": {"label": "Client", "id": client}, "properties": {}})
        rels.append({"type": "AUTHORED_BY", "from": "r%d" % n, "to": {"label": "Staff", "id": admin}, "properties": {}})
    return {"requestId": request_id or "req-" + uuid.uuid4().hex, "actorStaffId": admin, "nodes": nodes, "relationships": rels}


def test_bootstrap_refuses_once_staff_exist(driver, admin):
    from nest.gate import bootstrap
    out = bootstrap.bootstrap_admin(driver, "二人目", "req-" + uuid.uuid4().hex)
    assert out["ok"] is False and "既に職員" in out["errors"][0]


def test_client_gets_display_code_and_audit(driver, admin, client):
    row = _one(driver, "MATCH (c:Client {clientId: $id}) RETURN c.displayCode AS code, c.status AS status", id=client)[0]
    assert row["code"].startswith("C-") and row["status"] == "Active"
    assert _count(driver, "MATCH (a:AuditLog {targetId: $id, action: 'Create'})-[:AUDIT_FOR]->(:Client {clientId: $id}) "
                          "MATCH (a)-[:ACTED_BY]->(:Staff {staffId: $s}) RETURN count(a) AS n", id=client, s=admin) == 1


def test_ai_records_are_written_pending_with_audit(driver, admin, client):
    from nest.gate import write as gw
    mark = uuid.uuid4().hex
    out = gw.submit(_records_req(admin, client, ["架空の話 %s" % mark]), driver)
    assert out["ok"], out["errors"]
    rid = out["ids"]["r0"]
    row = _one(driver, "MATCH (r:Record {recordId: $id})-[:ABOUT]->(:Client {clientId: $c}) RETURN r.status AS s, r.sourceHash AS h",
               id=rid, c=client)[0]
    assert row["s"] == "Pending" and len(row["h"]) == 64
    assert _count(driver, "MATCH (a:AuditLog {requestId: $r}) RETURN count(a) AS n", r=out["requestId"]) == 3  # 記録 1・ABOUT・AUTHORED_BY


def test_same_record_twice_is_rejected_and_nothing_is_written(driver, admin, client):
    from nest.gate import write as gw
    text = "架空の二重 %s" % uuid.uuid4().hex
    assert gw.submit(_records_req(admin, client, [text]), driver)["ok"]
    again = _records_req(admin, client, [text, "架空の別の話 %s" % uuid.uuid4().hex])
    out = gw.submit(again, driver)
    assert out["ok"] is False and any("二重登録" in e for e in out["errors"])
    assert _count(driver, "MATCH (a:AuditLog {requestId: $r}) RETURN count(a) AS n", r=again["requestId"]) == 0
    assert _count(driver, "MATCH (r:Record) WHERE r.text STARTS WITH '架空の別の話 ' AND r.text = $t RETURN count(r) AS n",
                  t=again["nodes"][1]["properties"]["text"]) == 0


def test_same_ng_action_text_is_not_merged(driver, admin, client):
    from nest.gate import write as gw
    action = "架空の禁忌 %s" % uuid.uuid4().hex
    for n in range(2):  # 新しい禁忌には根拠の記録が要る（台帳 G-52 (7)）
        out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                         "nodes": [{"ref": "ng", "label": "NgAction", "origin": "AiExtracted",
                                    "properties": {"action": action, "riskLevel": "Panic"}},
                                   {"ref": "r0", "label": "Record", "origin": "AiExtracted",
                                    "properties": _record("根拠 %s %d" % (action, n))}],
                         "relationships": [{"type": "MUST_AVOID", "from": {"label": "Client", "id": client}, "to": "ng",
                                            "properties": {}},
                                           {"type": "ABOUT", "from": "r0", "to": {"label": "Client", "id": client}, "properties": {}},
                                           {"type": "EVIDENCED_BY", "from": "ng", "to": "r0", "properties": {}}]}, driver)
        assert out["ok"], out["errors"]
    assert _count(driver, "MATCH (n:NgAction {action: $a, status: 'Pending'}) RETURN count(n) AS n", a=action) == 2


def test_missing_existing_node_rejects_everything(driver, admin):
    from nest import ids
    from nest.gate import write as gw
    req = _records_req(admin, ids.new_id("CLI"), ["架空の宛先なし %s" % uuid.uuid4().hex])
    out = gw.submit(req, driver)
    assert out["ok"] is False and any("無い" in e for e in out["errors"])
    assert _count(driver, "MATCH (a:AuditLog {requestId: $r}) RETURN count(a) AS n", r=req["requestId"]) == 0


def test_unknown_or_inactive_staff_cannot_write(driver, client):
    from nest import ids
    from nest.gate import write as gw
    out = gw.submit(_records_req(ids.new_id("STF"), client, ["架空 %s" % uuid.uuid4().hex]), driver)
    assert out["ok"] is False and any("Active でない" in e for e in out["errors"])


def test_linking_an_existing_ng_action_is_a_separate_human_step(driver, admin, client):
    from nest.gate import write as gw
    mark = uuid.uuid4().hex
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                     "nodes": [{"ref": "ng", "label": "NgAction", "origin": "AiExtracted",
                                "properties": {"action": "架空の禁忌 %s" % mark, "riskLevel": "Panic"}},
                               {"ref": "r0", "label": "Record", "origin": "AiExtracted", "properties": _record("最初の話 %s" % mark)}],
                     "relationships": [{"type": "EVIDENCED_BY", "from": "ng", "to": "r0", "properties": {}}]}, driver)
    assert out["ok"], out["errors"]
    ng = out["ids"]["ng"]
    later = gw.submit(_records_req(admin, client, ["後で聞いた話 %s" % mark]), driver)
    assert later["ok"], later["errors"]
    rec = later["ids"]["r0"]
    linked = gw.link_evidence(driver, admin, {"label": "NgAction", "id": ng}, rec, "req-" + uuid.uuid4().hex)
    assert linked["ok"], linked["errors"]
    rows = _one(driver, "MATCH (:NgAction {ngActionId: $ng})-[e:EVIDENCED_BY]->(r:Record) RETURN r.recordId AS r, e.linkedBy AS by",
                ng=ng)
    assert sorted(r["r"] for r in rows) == sorted([out["ids"]["r0"], rec])
    assert all(r["by"] == admin for r in rows)
    assert _count(driver, "MATCH (a:AuditLog {action: 'LinkEvidence', requestId: $r}) RETURN count(a) AS n",
                  r=linked["requestId"]) == 1
    again = gw.link_evidence(driver, admin, {"label": "NgAction", "id": ng}, rec, "req-" + uuid.uuid4().hex)
    assert again["ok"] is False and any("既に" in e for e in again["errors"])


def test_contradiction_is_held_without_changing_the_ng_action(driver, admin, client):
    from nest.gate import write as gw
    mark = uuid.uuid4().hex
    first = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                       "nodes": [{"ref": "ng", "label": "NgAction", "origin": "Human",
                                  "properties": {"action": "架空の禁忌 %s" % mark, "riskLevel": "Panic"}},
                                 {"ref": "r0", "label": "Record", "origin": "Human", "properties": _record("職員が見た %s" % mark)}],
                       "relationships": [{"type": "ABOUT", "from": "r0", "to": {"label": "Client", "id": client}, "properties": {}},
                                         {"type": "EVIDENCED_BY", "from": "ng", "to": "r0", "properties": {}}]}, driver)
    ng = first["ids"]["ng"]
    before = _one(driver, "MATCH (n:NgAction {ngActionId: $id}) RETURN properties(n) AS p", id=ng)[0]["p"]
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                     "nodes": [{"ref": "r0", "label": "Record", "origin": "AiExtracted", "properties": _record("平気になった %s" % mark)}],
                     "relationships": [{"type": "CONTRADICTS", "from": "r0", "to": {"label": "NgAction", "id": ng},
                                        "properties": {"claim": "平気になったと聞いた"}}]}, driver)
    assert out["ok"], out["errors"]
    after = _one(driver, "MATCH (n:NgAction {ngActionId: $id}) RETURN properties(n) AS p", id=ng)[0]["p"]
    assert after == before
    row = _one(driver, "MATCH (:Record {recordId: $r})-[c:CONTRADICTS]->(:NgAction {ngActionId: $ng}) RETURN c.raisedAt IS NOT NULL AS ok",
               r=out["ids"]["r0"], ng=ng)
    assert row == [{"ok": True}]


def test_intake_care_candidates_are_written_pending_with_evidence(driver, admin, client):
    """G-63：入口の案の禁忌・推奨ケアの候補が、Pending で、根拠の記録（EVIDENCED_BY → Record）に結ばれて書かれる。"""
    from nest.gate import intake
    from nest.gate import write as gw
    mark = uuid.uuid4().hex
    quote = "架空の話 %s 後ろから急に声をかけるとパニックになる" % mark
    original = "架空の面談記録\n- %s【伝聞】\n" % quote
    proposal = {"documentKind": "OwnCaseRecord", "clientId": client,
                "facts": [{"quote": quote, "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family"}],
                "ngActions": [{"quote": quote, "action": "架空の禁忌 %s" % mark, "riskLevel": "Panic"}],
                "carePreferences": [{"quote": quote, "category": "声のかけ方", "instruction": "架空の推奨 %s" % mark}]}
    got = intake.check(proposal, original, admin, "req-" + uuid.uuid4().hex)
    assert got["ok"], got["errors"]
    out = gw.submit(got["request"], driver)
    assert out["ok"], out["errors"]
    rows = _one(driver, """
        MATCH (c:Client {clientId: $c})-[rel:MUST_AVOID|REQUIRES]->(n)-[:EVIDENCED_BY]->(r:Record {quote: $q})
        WHERE n.action = $a OR n.instruction = $i
        RETURN labels(n)[0] AS label, n.status AS status, n.certainty AS certainty, r.certainty AS evidence""",
                c=client, q=quote, a="架空の禁忌 %s" % mark, i="架空の推奨 %s" % mark)
    assert sorted((r["label"], r["status"], r["certainty"], r["evidence"]) for r in rows) == [
        ("CarePreference", "Pending", None, "Hearsay"), ("NgAction", "Pending", None, "Hearsay")]
