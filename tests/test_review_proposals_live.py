"""N-44：手順書（docs/OPERATIONS.md）の review_proposals のコマンドを、起動した個人の側でそのまま流す。NEST_LIVE_DB=1 のときだけ。

架空の本人と、AI 由来の未確定の記録を二つ（古い順に a・b）ゲートで入れて：
- list：a が b より先（古い順）。仮名が出る
- show：根拠の引用が出る
- approve：a が Active。AuditLog（Approve）が職員に結ばれる。自分で登録したものなので selfApproval
- reject：b が Inactive。AuditLog（Reject）
"""
import importlib.util
import os
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("doc_commands", REPO / "tests" / "doc_commands.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


def _q(d, query, **params):
    records, _, _ = d.execute_query(query, params, database_="neo4j")
    return [r.data() for r in records]


@pytest.fixture
def driver():
    from nest import connections
    with connections.driver("personal") as d:
        yield d


@pytest.fixture
def setup(driver):
    from nest.gate import write as gw
    admin = _q(driver, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")[0]["id"]
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                     "nodes": [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空"}}],
                     "relationships": []}, driver)
    assert out["ok"], out["errors"]
    client = out["ids"]["c"]
    made = []
    for word in ("一つ目", "二つ目"):
        text = "架空の話 %s %s：お茶が好き" % (word, uuid.uuid4().hex[:6])
        o = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                       "nodes": [{"ref": "r", "label": "Record", "origin": "AiExtracted",
                                  "properties": {"kind": "Interview", "text": text, "quote": text,
                                                 "certainty": "Hearsay", "informantKind": "Family"}}],
                       "relationships": [{"type": "ABOUT", "from": "r", "to": {"label": "Client", "id": client}},
                                         {"type": "AUTHORED_BY", "from": "r", "to": {"label": "Staff", "id": admin}}]}, driver)
        assert o["ok"], o["errors"]
        made.append((o["ids"]["r"], text))
    code = _q(driver, "MATCH (c:Client {clientId: $id}) RETURN c.displayCode AS code", id=client)[0]["code"]
    return {"admin": admin, "a": made[0], "b": made[1], "code": code}


def _line(sub):
    return next(l for l in dc.lines("review_proposals.py") if (" %s" % sub) in l)


def _run(sub, fill, driver):
    return dc.load("review_proposals.py").main(dc.argv(_line(sub), fill), driver=driver)


def test_list_is_oldest_first_with_the_code(driver, setup, capsys):
    assert _run("list", {}, driver) == 0
    out = capsys.readouterr().out
    a, b = setup["a"][0], setup["b"][0]
    assert a in out and b in out and out.index(a) < out.index(b)
    assert setup["code"] in out


def test_show_has_the_quote(driver, setup, capsys):
    rid, text = setup["a"]
    assert _run("show", {"REC-…": rid}, driver) == 0
    assert text in capsys.readouterr().out


def test_approve_one_with_self_approval(driver, setup, capsys):
    rid = setup["a"][0]
    assert _run("approve", {"REC-…": rid, "STF-…": setup["admin"]}, driver) == 0
    assert "自己承認" in capsys.readouterr().out
    rows = _q(driver, """MATCH (r:Record {recordId: $id})
                         OPTIONAL MATCH (r)<-[:AUDIT_FOR]-(a:AuditLog {action: 'Approve'})-[:ACTED_BY]->(s:Staff)
                         OPTIONAL MATCH (r)<-[ap:APPROVED]-(:Staff)
                         RETURN r.status AS status, s.staffId AS by, a.selfApproval AS selfAudit, ap.selfApproval AS selfRel""", id=rid)
    assert rows == [{"status": "Active", "by": setup["admin"], "selfAudit": True, "selfRel": True}], rows


def test_reject_one_with_a_reason_seen_in_show_and_list(driver, setup, capsys):
    """G-91：差し戻しの理由は AuditLog の reason に残り、show と list --rejected で見える"""
    rid = setup["b"][0]
    reason = "引用と中身が合わない（架空 %s）" % uuid.uuid4().hex[:6]
    assert _run("reject", {"REC-…": rid, "STF-…": setup["admin"], "…": reason}, driver) == 0
    capsys.readouterr()
    rows = _q(driver, """MATCH (r:Record {recordId: $id})
                         OPTIONAL MATCH (r)<-[:AUDIT_FOR]-(a:AuditLog {action: 'Reject'})-[:ACTED_BY]->(s:Staff)
                         RETURN r.status AS status, s.staffId AS by, a.reason AS reason""", id=rid)
    assert rows == [{"status": "Inactive", "by": setup["admin"], "reason": reason}], rows
    assert _run("show", {"REC-…": rid}, driver) == 0
    assert reason in capsys.readouterr().out
    assert _run("list --rejected", {}, driver) == 0
    out = capsys.readouterr().out
    assert rid in out and reason in out
