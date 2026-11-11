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


def test_estimated_org_reference_is_active_and_review_shows_the_involvement(driver, admin, client):
    """止まる点 4 の決定（台帳 G-59）。機関は資源の側（読むだけ）から架空でない公開の ID を一つ借りる。"""
    from nest import connections, org_estimate as oe
    from nest.gate import approve as ga
    from nest.gate import write as gw
    with connections.driver("resource") as resource:
        cands = oe.by_area(resource, "401099")["candidates"]
        have = {r["id"] for r in _one(driver, "MATCH (o:Organization) RETURN o.orgId AS id")}
        fresh = [c for c in cands if c["orgId"] not in have]
        org = (fresh or cands)[0]
        mark = uuid.uuid4().hex
        out = gw.submit({"requestId": _rid(), "actorStaffId": admin,
                         "nodes": [{"ref": "o", "label": "Organization", "origin": "AiExtracted", "properties": {"orgId": org["orgId"]}},
                                   {"ref": "i", "label": "Involvement", "origin": "AiExtracted",
                                    "properties": {"kind": "Consultation", "howEnded": "Unknown", "certainty": "Inference",
                                                   "inferenceBasis": "CurrentResidenceArea"}},
                                   {"ref": "r0", "label": "Record", "origin": "AiExtracted",
                                    "properties": {"kind": "Interview", "text": "架空の相談 %s" % mark, "quote": "架空の相談 %s" % mark,
                                                   "certainty": "Hearsay", "informantKind": "Family"}}],
                         "relationships": [{"type": "HAS_INVOLVEMENT", "from": "o", "to": "i", "properties": {}},
                                           {"type": "CONCERNS", "from": "i", "to": {"label": "Client", "id": client}, "properties": {}},
                                           {"type": "EVIDENCED_BY", "from": "i", "to": "r0", "properties": {}}]}, driver)
        assert out["ok"], out["errors"]
        if fresh:
            st = _one(driver, "MATCH (o:Organization {orgId: $id}) RETURN o.status AS s, o.origin AS o", id=org["orgId"])
            assert st == [{"s": "Active", "o": "AiExtracted"}]
        items = {i["id"]: i for i in ga.review_items(driver, client, resource_driver=resource)}
    assert org["orgId"] not in items                                     # 機関の写しは承認の対象に出ない
    inv = items[out["ids"]["i"]]
    assert inv["content"] == {"kind": "Consultation", "certainty": "Inference", "howEnded": "Unknown",
                              "inferenceBasis": "CurrentResidenceArea", "note": None,
                              "organizations": [{"orgId": org["orgId"], "name": org["name"]}], "organizationUndecided": False}
    assert [q["quote"] for q in inv["quotes"]] == ["架空の相談 %s" % mark]


def test_involvement_of_a_parent_shows_up_for_review_with_its_quote(driver, admin, client):
    """正典 v0.7（台帳 G-60）。親（新しい人）に向けた関わりも、本人の承認待ちに引用つきで出る。"""
    from nest.gate import approve as ga
    from nest.gate import write as gw
    mark = uuid.uuid4().hex
    out = gw.submit({"requestId": _rid(), "actorStaffId": admin,
                     "nodes": [{"ref": "mother", "label": "Person", "origin": "AiExtracted", "properties": {}},
                               {"ref": "i", "label": "Involvement", "origin": "Human",
                                "properties": {"kind": "Consultation", "howEnded": "Unknown", "certainty": "SelfReport"}},
                               {"ref": "r0", "label": "Record", "origin": "AiExtracted",
                                "properties": {"kind": "Interview", "text": "母が相談した %s" % mark, "quote": "母が相談した %s" % mark,
                                               "certainty": "SelfReport", "informantKind": "Family"}}],
                     "relationships": [{"type": "CONCERNS", "from": "i", "to": "mother", "properties": {}},
                                       {"type": "EVIDENCED_BY", "from": "i", "to": "r0", "properties": {}},
                                       {"type": "ABOUT", "from": "r0", "to": {"label": "Client", "id": client}, "properties": {}}]}, driver)
    assert out["ok"], out["errors"]
    assert _one(driver, "MATCH (i:Involvement {involvementId: $id}) RETURN i.status AS s", id=out["ids"]["i"]) == [{"s": "Pending"}]
    items = {i["id"]: i for i in ga.review_items(driver, client)}
    inv = items[out["ids"]["i"]]
    assert [q["quote"] for q in inv["quotes"]] == ["母が相談した %s" % mark]
    assert inv["content"]["kind"] == "Consultation"


def test_reject_keeps_the_reason_on_the_audit_log(driver, admin, client):
    """G-91：理由は AuditLog の reason に一行で残る。理由が無ければ項目を置かない"""
    from nest.gate import approve as ga
    with_reason, without = _two_pending(driver, admin, client)
    assert ga.reject(driver, admin, with_reason, _rid(), reason="引用と中身が合わない（架空）")["ok"]
    assert ga.reject(driver, admin, without, _rid())["ok"]
    q = "MATCH (a:AuditLog {action: 'Reject', targetId: $r}) RETURN a.reason AS reason, 'reason' IN keys(a) AS has"
    assert _one(driver, q, r=with_reason["id"]) == [{"reason": "引用と中身が合わない（架空）", "has": True}]
    assert _one(driver, q, r=without["id"]) == [{"reason": None, "has": False}]


def test_a_fact_waits_until_its_evidence_is_approved(driver, admin, client):
    """2026-11-11 河原さん：根拠の記録が未確定のまま禁忌が有効になった。根拠を先に一件ずつ承認する（正典 §7）"""
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
    ng, rec = {"label": "NgAction", "id": out["ids"]["ng"]}, {"label": "Record", "id": out["ids"]["r0"]}
    early = ga.approve(driver, admin, ng, _rid())
    assert early["ok"] is False and any(rec["id"] in e and "先に" in e for e in early["errors"])
    assert _one(driver, "MATCH (n:NgAction {ngActionId: $id}) RETURN n.status AS s", id=ng["id"]) == [{"s": "Pending"}]
    assert _count(driver, "MATCH (a:AuditLog {requestId: $q}) RETURN count(a) AS n", q=early["requestId"]) == 0
    assert ga.approve(driver, admin, rec, _rid())["ok"]
    assert ga.approve(driver, admin, ng, _rid())["ok"]
