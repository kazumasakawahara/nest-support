"""N-32：本人のデータの廃棄（2026-11-06 河原さん。止まる点 F-1。台帳 G-74）。DB を使わない部分。

- 保存の判断（RetentionDecision）はゲートで書く。人の操作だけ（origin Human）、Administrator だけ、本人一人に DECIDES_ON 一本
- 消す道具（nest.gate.purge）：保存の判断（最後のものが Delete）が本人に結ばれていなければ、試しの実行でも動かない。
  Active な Administrator だけ。本当に消すには仮名の打ち返しが要る。監査ログは Purge を 1 件（件数だけ。名前・本文・理由を書かない）
- 消す範囲：その本人と、その本人にだけつながるもの。ほかの本人にもつながる人は残す
手本：tsunagu-net の tsunagu/gate/purge.py（読むだけ）。DB を使う確かめは tests/test_purge_live.py。
"""
import datetime as dt

from nest.gate import purge
from nest.gate import validate as gv
from nest.gate import write as gw

ADMIN = "STF-01KAAAAAAAAAAAAAAAAAAAAAAA"
CLIENT = "CLI-01KAAAAAAAAAAAAAAAAAAAAAAA"
OTHER = "CLI-01KBBBBBBBBBBBBBBBBBBBBBBB"


def _req(origin="Human", rels=None, props=None):
    p = {"decidedOn": "2026-11-06", "decision": "Delete", "reason": "架空：保存の期間を過ぎた"}
    p.update(props or {})
    return {"requestId": "req-test", "actorStaffId": ADMIN,
            "nodes": [{"ref": "rd", "label": "RetentionDecision", "origin": origin, "properties": p}],
            "relationships": rels if rels is not None else
            [{"type": "DECIDES_ON", "from": "rd", "to": {"label": "Client", "id": CLIENT}, "properties": {}}]}


# --- 保存の判断（ゲート） ---

def test_retention_request_is_human_and_points_at_one_client():
    req = gw.retention_request(ADMIN, CLIENT, "2026-11-06", "Delete", "架空の理由", "req-1")
    assert [n["label"] for n in req["nodes"]] == ["RetentionDecision"]
    assert req["nodes"][0]["origin"] == "Human"
    assert req["relationships"] == [{"type": "DECIDES_ON", "from": "rd", "to": {"label": "Client", "id": CLIENT}, "properties": {}}]
    assert gv.validate(req)["ok"], gv.validate(req)["errors"]


def test_retention_decision_from_ai_is_refused():
    rep = gv.validate(_req(origin="AiExtracted"))
    assert any("RetentionDecision" in e and "Human" in e for e in rep["errors"]), rep["errors"]


def test_retention_decision_needs_exactly_one_client():
    assert any("DECIDES_ON" in e for e in gv.validate(_req(rels=[]))["errors"])
    two = [{"type": "DECIDES_ON", "from": "rd", "to": {"label": "Client", "id": c}, "properties": {}} for c in (CLIENT, OTHER)]
    assert any("DECIDES_ON" in e for e in gv.validate(_req(rels=two))["errors"])


def test_retention_decision_value_must_be_keep_or_delete():
    assert not gv.validate(_req(props={"decision": "Archive"}))["ok"]


# --- 消す道具の決まり（DB を使わない部分） ---

def _k(label, n):
    return (label, "%s-%d" % (label, n))


def test_plan_deletes_only_what_hangs_on_this_client_and_keeps_shared_people():
    c, other = _k("Client", 1), _k("Client", 2)
    shared, own = _k("Person", 1), _k("Person", 2)
    rec, ng, rd, inv = _k("Record", 1), _k("NgAction", 1), _k("RetentionDecision", 1), _k("Involvement", 1)
    edges = [
        {"child": shared, "type": "RELATED_TO", "out": True, "parent": c},
        {"child": shared, "type": "RELATED_TO", "out": True, "parent": other},
        {"child": own, "type": "RELATED_TO", "out": True, "parent": c},
        {"child": rec, "type": "ABOUT", "out": True, "parent": c},
        {"child": ng, "type": "MUST_AVOID", "out": False, "parent": c},
        {"child": rd, "type": "DECIDES_ON", "out": True, "parent": c},
        {"child": inv, "type": "CONCERNS", "out": True, "parent": c},
        {"child": own, "type": "HAS_INVOLVEMENT", "out": True, "parent": inv},
    ]
    p = purge.plan(c, edges)
    assert p["delete"] == {c, own, rec, ng, rd, inv}
    assert p["kept"] == {shared}
    assert p["keptPersons"] == 1
    assert purge.counts(p["delete"]) == ["Client:1", "Involvement:1", "NgAction:1", "Person:1", "Record:1", "RetentionDecision:1"]


def test_plan_ignores_edges_that_are_not_parent_edges():
    """機関・職員・監査ログは親の辺にならない（消えない）。根拠の辺（EVIDENCED_BY）は記録を事実の子にしない"""
    c, rec, ng = _k("Client", 1), _k("Record", 1), _k("NgAction", 1)
    edges = [{"child": rec, "type": "EVIDENCED_BY", "out": False, "parent": ng},
             {"child": ng, "type": "MUST_AVOID", "out": False, "parent": c}]
    p = purge.plan(c, edges)
    assert rec not in p["delete"] and ng in p["delete"]
    assert not {"Staff", "Organization", "AuditLog"} & set(purge.PARENTS)


def test_latest_decision_is_by_date_then_registration():
    rows = [{"retentionId": "RTD-a", "decision": "Delete", "decidedOn": dt.date(2026, 1, 1), "registeredAt": dt.datetime(2026, 1, 1)},
            {"retentionId": "RTD-b", "decision": "Keep", "decidedOn": dt.date(2026, 6, 1), "registeredAt": dt.datetime(2026, 6, 1)}]
    assert purge.latest_decision(rows)["retentionId"] == "RTD-b"
    assert purge.latest_decision([]) is None


ADMIN_ROLE = {"status": "Active", "role": "Administrator"}
DELETE = {"retentionId": "RTD-x", "decision": "Delete"}


def test_check_refuses_without_a_delete_decision_even_for_a_dry_run():
    assert any("保存の判断" in e for e in purge.check(ADMIN_ROLE, True, None, "C-ZZZZZZ", False, None))
    keep = {"retentionId": "RTD-y", "decision": "Keep"}
    assert any("Delete" in e or "消す" in e for e in purge.check(ADMIN_ROLE, True, keep, "C-ZZZZZZ", False, None))
    assert purge.check(ADMIN_ROLE, True, DELETE, "C-ZZZZZZ", False, None) == []


def test_check_needs_an_active_administrator_and_an_existing_client():
    assert purge.check({"status": "Active", "role": "Staff"}, True, DELETE, "C-ZZZZZZ", False, None)
    assert purge.check({"status": "Inactive", "role": "Administrator"}, True, DELETE, "C-ZZZZZZ", False, None)
    assert purge.check(None, True, DELETE, "C-ZZZZZZ", False, None)
    assert purge.check(ADMIN_ROLE, False, None, "C-ZZZZZZ", False, None)


def test_check_needs_the_display_code_echoed_to_write():
    assert any("打ち返し" in e for e in purge.check(ADMIN_ROLE, True, DELETE, "C-ZZZZZZ", True, None))
    assert any("打ち返し" in e for e in purge.check(ADMIN_ROLE, True, DELETE, "C-ZZZZZZ", True, "C-YYYYYY"))
    assert purge.check(ADMIN_ROLE, True, DELETE, "C-ZZZZZZ", True, "C-ZZZZZZ") == []


def test_purge_audit_keeps_counts_only():
    now = dt.datetime(2026, 11, 6, tzinfo=dt.timezone.utc)
    a = purge.audit_props(lambda p: p + "-01KZZZZZZZZZZZZZZZZZZZZZZZ", now, CLIENT, "RTD-x", ["Record:2"], 1, "req-9")
    assert a["action"] == "Purge" and a["targetLabel"] == "Client" and a["targetId"] == CLIENT
    assert a["retentionId"] == "RTD-x" and a["purgedCounts"] == ["Record:2"] and a["keptPersons"] == 1
    assert a["origin"] == "Human" and a["status"] == "Active"
    assert not {"reason", "displayCode", "familyName", "givenName", "text", "quote"} & set(a)
