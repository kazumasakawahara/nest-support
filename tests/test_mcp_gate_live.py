"""書き込み受付の MCP（nest/mcp_gate.py）を、起動した個人の側（架空の印のある DB）で流す。NEST_LIVE_DB=1 のときだけ。

- 面接記録の案（確認点 L-0。supportLog と見立ての一文）が、未確定（Pending）の SupportLog・Record として入る
- SupportLog は本人に ABOUT、職員に AUTHORED_BY、接触の一文の記録に EVIDENCED_BY で結ばれる
- 入口で止まる案（使われない新しい人）は何も入れない
- 職員の ID は道具の引数でなく設定（ここでは環境変数）から読まれ、AUTHORED_BY の先になる
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")


def _q(d, query, **params):
    records, _, _ = d.execute_query(query, params, database_="neo4j")
    return [r.data() for r in records]


@pytest.fixture
def driver():
    from nest import connections
    with connections.driver("personal") as d:
        yield d


@pytest.fixture
def setup(driver, monkeypatch):
    from nest.gate import write as gw
    admin = _q(driver, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")[0]["id"]
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                     "nodes": [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空"}}],
                     "relationships": []}, driver)
    assert out["ok"], out["errors"]
    monkeypatch.setenv("NEST_GATE_STAFF_ID", admin)
    code = _q(driver, "MATCH (c:Client {clientId: $id}) RETURN c.displayCode AS code", id=out["ids"]["c"])[0]["code"]
    word = uuid.uuid4().hex[:6]
    visit = "自宅を訪問 %s。母と本人に会う。" % word
    view = "予定が変わると落ち着かないのだろうと、私は受け取りました %s。" % word
    original = "架空の面接記録\n2026-11-01 訪問\n%s\n%s【推測】\n" % (visit, view)
    return {"admin": admin, "client": out["ids"]["c"], "code": code, "visit": visit, "view": view, "original": original}


def _proposal(s, **over):
    p = {"documentKind": "OwnCaseRecord",
         "facts": [{"quote": s["visit"], "recordKind": "Observation", "certainty": "Unspecified", "informantKind": "Agency"},
                   {"quote": s["view"], "recordKind": "Interview", "certainty": "Inference", "informantKind": "Self"}],
         "supportLog": {"quote": s["visit"], "date": "2026-11-01", "contactKind": "Visit", "situation": "自宅。母と本人",
                        "action": "母と本人に会い、話を聞いた"}}
    p.update(over)
    return p


def _pending(driver):
    return _q(driver, "MATCH (n {status: 'Pending'}) RETURN count(n) AS n")[0]["n"]


def test_an_interview_record_goes_in_as_pending(driver, setup):
    from nest import mcp_gate
    out = mcp_gate._submit(driver, setup["code"], setup["original"], _proposal(setup))
    assert out["ok"], out
    assert out["counts"] == {"Record": 2, "SupportLog": 1}
    rows = _q(driver, """MATCH (l:SupportLog)-[:EVIDENCED_BY]->(r:Record {quote: $q})
                         MATCH (l)-[:ABOUT]->(c:Client), (l)-[:AUTHORED_BY]->(s:Staff)
                         RETURN l.status AS st, l.contactKind AS kind, c.clientId AS c, s.staffId AS s""", q=setup["visit"])
    assert rows == [{"st": "Pending", "kind": "Visit", "c": setup["client"], "s": setup["admin"]}]
    view = _q(driver, "MATCH (r:Record {quote: $q}) OPTIONAL MATCH (r)-[t:TOLD_BY]->() "
                      "RETURN r.certainty AS c, r.informantKind AS i, count(t) AS told", q=setup["view"])
    assert view == [{"c": "Inference", "i": "Self", "told": 0}]


def test_a_stopped_proposal_adds_nothing(driver, setup):
    from nest import mcp_gate
    before = _pending(driver)
    out = mcp_gate._submit(driver, setup["code"], setup["original"], _proposal(setup, newPeople=[{"ref": "neighbor"}]))
    assert not out["ok"] and out["stage"] == "intake"
    assert _pending(driver) == before
