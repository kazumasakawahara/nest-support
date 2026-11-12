"""新しい人の続柄を、起動した個人の側で確かめる（2026-11-12 河原さんの承認。正典 v0.14 §7。台帳 G-102）。NEST_LIVE_DB=1 のときだけ。

- 案（続柄つき）→ 入口の点検 → ゲート：RELATED_TO が Pending、evidenceRecordIds は発番した記録の ID
- 人の承認は、続柄の根拠の記録が未確定なら止まり、その記録を名指す。記録を承認した後に人を承認すると、続柄も一緒に Active。
  関係ごとに AuditLog（targetLabel RELATED_TO）が残る
- 人の差し戻しで、続柄も一緒に Inactive（根拠が未確定でも差し戻しは止めない）
- 照会口（読み取りの包み）で続柄が読める
- 未確定の一覧（review_proposals.py list）の人の行は、仮名を一度だけ出し、続柄を添える（2026-11-12 河原さん）
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

from tests.test_gate_write_live import _count, _one, admin, client, driver  # noqa: E402,F401  フィクスチャ


def _submit(driver, admin, client):
    from nest.gate import intake
    from nest.gate import write as gw
    quote = "母が電話で話した %s。" % uuid.uuid4().hex[:8]
    p = {"documentKind": "OwnCaseRecord", "clientId": client, "newPeople": [{"ref": "mother", "relation": {"kind": "Parent", "quote": quote}}],
         "facts": [{"quote": quote, "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family", "toldBy": "mother"}]}
    rep = intake.check(p, "架空の面接記録\n2026-11-12 電話\n%s【伝聞】\n" % quote, admin, "req-" + uuid.uuid4().hex)
    assert rep["ok"], rep["errors"]
    out = gw.submit(rep["request"], driver)
    assert out["ok"], out["errors"]
    return out["ids"]["mother"], out["ids"]["fact-1"]


def _relation(driver, person):
    return _one(driver, "MATCH (:Person {personId: $p})-[r:RELATED_TO]->(:Client) "
                        "RETURN r.kind AS kind, r.status AS status, r.certainty AS c, r.evidenceRecordIds AS ev", p=person)


def test_the_relation_enters_pending_with_the_issued_record_id(driver, admin, client):
    person, record = _submit(driver, admin, client)
    assert _relation(driver, person) == [{"kind": "Parent", "status": "Pending", "c": "Hearsay", "ev": [record]}]


def test_approving_the_person_waits_for_the_record_then_activates_the_relation(driver, admin, client):
    from nest.gate import approve as ga
    person, record = _submit(driver, admin, client)
    first = ga.approve(driver, admin, {"label": "Person", "id": person}, "req-" + uuid.uuid4().hex)
    assert not first["ok"] and any(record in e and "未確定" in e for e in first["errors"]), first["errors"]
    assert _relation(driver, person)[0]["status"] == "Pending"
    assert ga.approve(driver, admin, {"label": "Record", "id": record}, "req-" + uuid.uuid4().hex)["ok"]
    out = ga.approve(driver, admin, {"label": "Person", "id": person}, "req-" + uuid.uuid4().hex)
    assert out["ok"], out["errors"]
    assert _relation(driver, person)[0]["status"] == "Active"
    assert [(r["kind"], r["status"]) for r in out["relations"]] == [("Parent", "Active")]
    assert _count(driver, "MATCH (a:AuditLog {action: 'Approve', targetLabel: 'RELATED_TO', targetId: $p, requestId: $q}) "
                          "RETURN count(a) AS n", p=person, q=out["requestId"]) == 1


def test_rejecting_the_person_inactivates_the_relation(driver, admin, client):
    from nest.gate import approve as ga
    person, _ = _submit(driver, admin, client)
    out = ga.reject(driver, admin, {"label": "Person", "id": person}, "req-" + uuid.uuid4().hex)
    assert out["ok"], out["errors"]
    assert _relation(driver, person)[0]["status"] == "Inactive"
    assert _count(driver, "MATCH (a:AuditLog {action: 'Reject', targetLabel: 'RELATED_TO', targetId: $p}) RETURN count(a) AS n",
                  p=person) == 1


def test_the_read_wrapper_returns_the_relation(driver, admin, client):
    from nest import mcp_guard
    person, _ = _submit(driver, admin, client)
    rows = mcp_guard.run_read(driver, "MATCH (p:Person {personId: $p})-[r:RELATED_TO]->(c:Client) "
                                      "RETURN p.personId AS person, r.kind AS kind, r.status AS status", {"p": person}, personal=True)
    assert rows == [{"person": person, "kind": "Parent", "status": "Pending"}]


def test_the_list_names_the_client_once_with_the_relation(driver, admin, client, capsys):
    from tests import doc_commands
    person, _ = _submit(driver, admin, client)
    code = _one(driver, "MATCH (c:Client {clientId: $c}) RETURN c.displayCode AS code", c=client)[0]["code"]
    assert doc_commands.load("review_proposals.py").main(["list", "--code", code], driver=driver) == 0
    (line,) = [l for l in capsys.readouterr().out.splitlines() if l.startswith(person)]
    assert line.count(code) == 1 and "本人 %s  続柄 " % code in line and "（Parent）・Pending" in line, line
    assert "「母が電話で話した " in line, line  # 2026-11-12：続柄の根拠の引用の冒頭を添える（本物の DB の問い合わせで確かめる）


def test_the_list_shows_the_start_of_the_record_quote(driver, admin, client, capsys):
    from tests import doc_commands
    _, record = _submit(driver, admin, client)
    code = _one(driver, "MATCH (c:Client {clientId: $c}) RETURN c.displayCode AS code", c=client)[0]["code"]
    assert doc_commands.load("review_proposals.py").main(["list", "--code", code], driver=driver) == 0
    (line,) = [l for l in capsys.readouterr().out.splitlines() if l.startswith(record)]
    assert "「母が電話で話した " in line, line
