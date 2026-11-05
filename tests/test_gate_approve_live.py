"""N-21：承認の操作を、起動した個人の側で確かめる。NEST_LIVE_DB=1 のときだけ。架空のものだけを入れる。

    NEST_LIVE_DB=1 uv run pytest -q tests/test_gate_approve_live.py
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

from tests.test_gate_write_live import _count, _one, _records_req, admin, client, driver  # noqa: E402,F401  フィクスチャ


def _rid():
    return "req-" + uuid.uuid4().hex


def _two_pending(driver, admin, client):
    from nest.gate import write as gw
    mark = uuid.uuid4().hex
    out = gw.submit(_records_req(admin, client, ["架空の話 A %s" % mark, "架空の話 B %s" % mark]), driver)
    assert out["ok"], out["errors"]
    return [{"label": "Record", "id": out["ids"]["r0"]}, {"label": "Record", "id": out["ids"]["r1"]}]


def test_single_approval_is_recorded_with_self_approval_and_quote(driver, admin, client):
    from nest.gate import approve as ga
    target = _two_pending(driver, admin, client)[0]
    out = ga.approve(driver, admin, target, _rid())
    assert out["ok"], out["errors"]
    assert out["selfApproval"] is True
    assert out["shown"][0]["quote"].startswith("架空の話 A ")
    row = _one(driver, "MATCH (s:Staff {staffId: $s})-[a:APPROVED]->(r:Record {recordId: $r}) "
                       "RETURN r.status AS status, a.selfApproval AS self, a.at IS NOT NULL AS at", s=admin, r=target["id"])
    assert row == [{"status": "Active", "self": True, "at": True}]
    assert _count(driver, "MATCH (a:AuditLog {action: 'Approve', targetId: $r, requestId: $q, selfApproval: true})"
                          "-[:ACTED_BY]->(:Staff {staffId: $s}) RETURN count(a) AS n", r=target["id"], q=out["requestId"], s=admin) == 1


def test_approving_twice_fails(driver, admin, client):
    from nest.gate import approve as ga
    target = _two_pending(driver, admin, client)[0]
    assert ga.approve(driver, admin, target, _rid())["ok"]
    again = ga.approve(driver, admin, target, _rid())
    assert again["ok"] is False and any("Pending でない" in e for e in again["errors"])


def test_bulk_approval_of_ai_derived_items_fails_and_changes_nothing(driver, admin, client):
    from nest.gate import approve as ga
    targets = _two_pending(driver, admin, client)
    out = ga.approve_many(driver, admin, targets, _rid())
    assert out["ok"] is False and any("まとめて" in e for e in out["errors"])
    for t in targets:
        assert _one(driver, "MATCH (r:Record {recordId: $r}) RETURN r.status AS s", r=t["id"]) == [{"s": "Pending"}]
    assert _count(driver, "MATCH (a:AuditLog {requestId: $q}) RETURN count(a) AS n", q=out["requestId"]) == 0


def test_reject_makes_inactive_with_audit(driver, admin, client):
    from nest.gate import approve as ga
    target = _two_pending(driver, admin, client)[1]
    out = ga.reject(driver, admin, target, _rid())
    assert out["ok"], out["errors"]
    assert _one(driver, "MATCH (r:Record {recordId: $r}) RETURN r.status AS s", r=target["id"]) == [{"s": "Inactive"}]
    assert _count(driver, "MATCH (a:AuditLog {action: 'Reject', targetId: $r}) RETURN count(a) AS n", r=target["id"]) == 1


def test_review_lists_each_pending_fact_with_its_quotes(driver, admin, client):
    from nest.gate import approve as ga
    from nest.gate import write as gw
    mark = uuid.uuid4().hex
    out = gw.submit({"requestId": _rid(), "actorStaffId": admin,
                     "nodes": [{"ref": "ng", "label": "NgAction", "origin": "AiExtracted",
                                "properties": {"action": "架空の禁忌 %s" % mark, "riskLevel": "Panic"}},
                               {"ref": "r0", "label": "Record", "origin": "AiExtracted",
                                "properties": {"kind": "Interview", "text": "根拠 %s" % mark, "quote": "根拠 %s" % mark,
                                               "certainty": "Hearsay", "informantKind": "Family"}}],
                     "relationships": [{"type": "MUST_AVOID", "from": {"label": "Client", "id": client}, "to": "ng", "properties": {}},
                                       {"type": "EVIDENCED_BY", "from": "ng", "to": "r0", "properties": {}}]}, driver)
    assert out["ok"], out["errors"]
    items = {i["id"]: i for i in ga.review_items(driver, client)}
    ng = items[out["ids"]["ng"]]
    assert ng["label"] == "NgAction" and ng["origin"] == "AiExtracted"
    assert [q["quote"] for q in ng["quotes"]] == ["根拠 %s" % mark]
    assert ng["quotes"][0]["certainty"] == "Hearsay"
    rec = items[out["ids"]["r0"]]
    assert [q["quote"] for q in rec["quotes"]] == ["根拠 %s" % mark]
