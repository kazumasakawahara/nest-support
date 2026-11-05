"""N-20：ゲートの書き込み（DB を使わない部分）。ADR-001 D5・D6・D8。

- 書く予定（plan）は、ID・registeredAt・origin・status（AI 由来は Pending）をゲートが付ける
- Client の displayCode はゲートが付ける。名前から作らない（D8）
- Record の sourceHash は内容と、ID が決まった相手から作る。依頼の中の二重は止める
- EVIDENCED_BY の linkedBy・at、CONTRADICTS の raisedAt はゲートが付ける
- 既にある事実（禁忌など）に根拠を結ぶのは人の指定だけ（link_evidence）。依頼の中では結べない（D5）
- 職員は人が登録する。書くたびに AuditLog を作る予定を持つ
- 問い合わせは CREATE だけ。MERGE しない（自動でまとめない）
DB に書く試験は tests/test_gate_write_live.py（NEST_LIVE_DB=1 のときだけ）。
"""
import datetime as dt
import re
from pathlib import Path

import pytest

from nest import ids
from nest.gate import intake
from nest.gate import validate as gv
from nest.gate import write as gw

NOW = dt.datetime(2026, 11, 5, 9, 0, tzinfo=dt.timezone.utc)
STAFF = "STF-" + "0" * 26
CLIENT = "CLI-" + "1" * 26
NGA = "NGA-" + "2" * 26
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "intake"


def _counter():
    n = {"i": 0}

    def new_id(prefix):
        n["i"] += 1
        return "%s-%s" % (prefix, ("%026d" % n["i"]).replace("0", "A"))
    return new_id


def _record_props(text="架空の記録"):
    return {"kind": "Interview", "text": text, "quote": text, "certainty": "Hearsay", "informantKind": "Family"}


def _plan(req):
    rep = gv.validate(req)
    assert rep["ok"], rep["errors"]
    return gw.build_plan(rep, req, NOW, _counter(), lambda: "C-ABCDEF")


def _req(nodes, rels=(), actor=STAFF):
    return {"requestId": "req-1", "actorStaffId": actor, "nodes": list(nodes), "relationships": list(rels)}


def test_gate_sets_ids_and_common_properties():
    plan = _plan(_req([
        {"ref": "r1", "label": "Record", "origin": "AiExtracted", "properties": _record_props()},
        {"ref": "p1", "label": "Person", "origin": "Human", "properties": {"familyName": "架空"}},
    ]))
    assert plan["errors"] == []
    by_ref = {n["ref"]: n for n in plan["nodes"]}
    assert ids.is_valid_id(by_ref["r1"]["props"]["recordId"], "REC") or by_ref["r1"]["props"]["recordId"].startswith("REC-")
    assert by_ref["r1"]["props"]["status"] == "Pending" and by_ref["r1"]["props"]["origin"] == "AiExtracted"
    assert by_ref["p1"]["props"]["status"] == "Active"
    for n in plan["nodes"]:
        assert n["props"]["registeredAt"] == NOW


def test_display_code_is_issued_by_the_gate_not_from_the_name():
    plan = _plan(_req([{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空", "givenName": "太郎"}}]))
    props = plan["nodes"][0]["props"]
    assert props["displayCode"] == "C-ABCDEF"
    assert ids.is_valid_id(props["clientId"], "CLI") or props["clientId"].startswith("CLI-")


def test_display_code_shape():
    codes = {gw.new_display_code() for _ in range(50)}
    assert len(codes) == 50
    for c in codes:
        assert re.fullmatch(r"C-[0-9A-HJKMNP-TV-Z]{6}", c), c


def test_record_gets_source_hash_and_duplicates_in_one_request_stop():
    rels = [{"type": "ABOUT", "from": "r1", "to": {"label": "Client", "id": CLIENT}},
            {"type": "ABOUT", "from": "r2", "to": {"label": "Client", "id": CLIENT}}]
    plan = _plan(_req([
        {"ref": "r1", "label": "Record", "origin": "AiExtracted", "properties": _record_props()},
        {"ref": "r2", "label": "Record", "origin": "AiExtracted", "properties": _record_props()},
    ], rels))
    assert any("二重登録" in e for e in plan["errors"])
    h = [n["props"]["sourceHash"] for n in plan["nodes"]]
    assert h[0] == h[1] and re.fullmatch(r"[0-9a-f]{64}", h[0])


def test_same_text_about_different_clients_is_not_a_duplicate():
    other = "CLI-" + "3" * 26
    plan = _plan(_req([
        {"ref": "r1", "label": "Record", "origin": "AiExtracted", "properties": _record_props()},
        {"ref": "r2", "label": "Record", "origin": "AiExtracted", "properties": _record_props()},
    ], [{"type": "ABOUT", "from": "r1", "to": {"label": "Client", "id": CLIENT}},
        {"type": "ABOUT", "from": "r2", "to": {"label": "Client", "id": other}}]))
    assert plan["errors"] == []


def test_evidence_and_contradiction_stamps_are_set_by_the_gate():
    plan = _plan(_req([
        {"ref": "ng", "label": "NgAction", "origin": "AiExtracted", "properties": {"action": "大きな音", "riskLevel": "Panic"}},
        {"ref": "r1", "label": "Record", "origin": "AiExtracted", "properties": _record_props("大きな音が苦手")},
        {"ref": "r2", "label": "Record", "origin": "AiExtracted", "properties": _record_props("大きな音は平気になった")},
    ], [{"type": "EVIDENCED_BY", "from": "ng", "to": "r1", "properties": {}},
        {"type": "CONTRADICTS", "from": "r2", "to": {"label": "NgAction", "id": NGA}, "properties": {"claim": "平気になったと聞いた"}}]))
    assert plan["errors"] == []
    ev = next(r for r in plan["relationships"] if r["type"] == "EVIDENCED_BY")
    assert ev["props"] == {"linkedBy": STAFF, "at": NOW}
    con = next(r for r in plan["relationships"] if r["type"] == "CONTRADICTS")
    assert con["props"]["raisedAt"] == NOW and con["props"]["claim"] == "平気になったと聞いた"


def test_linking_to_an_existing_fact_is_not_done_inside_a_request():
    """既にある禁忌に結ぶのは人の指定だけ。依頼の中では結ばない（D5）。結ぶのは link_evidence。"""
    plan = _plan(_req([{"ref": "r1", "label": "Record", "origin": "AiExtracted", "properties": _record_props()}],
                      [{"type": "EVIDENCED_BY", "from": {"label": "NgAction", "id": NGA}, "to": "r1", "properties": {}}]))
    assert any("link_evidence" in e for e in plan["errors"])


def test_staff_must_be_registered_by_a_person():
    plan = _plan(_req([{"ref": "s", "label": "Staff", "origin": "AiExtracted", "properties": {"displayName": "架空", "role": "Staff"}}]))
    assert any("職員は人が登録する" in e for e in plan["errors"])


@pytest.mark.parametrize("actor", [None, "", "staff-1", "PER-" + "0" * 26])
def test_actor_must_be_a_staff_id(actor):
    plan = _plan(_req([{"ref": "p1", "label": "Person", "origin": "Human", "properties": {}}], actor=actor))
    assert any("actorStaffId" in e for e in plan["errors"])


def test_an_audit_row_for_every_node_and_relationship():
    plan = _plan(_req([
        {"ref": "ng", "label": "NgAction", "origin": "AiExtracted", "properties": {"action": "大きな音", "riskLevel": "Panic"}},
        {"ref": "r1", "label": "Record", "origin": "AiExtracted", "properties": _record_props()},
    ], [{"type": "EVIDENCED_BY", "from": "ng", "to": "r1", "properties": {}},
        {"type": "ABOUT", "from": "r1", "to": {"label": "Client", "id": CLIENT}}]))
    actions = sorted((a["props"]["targetLabel"], a["props"]["action"]) for a in plan["audits"])
    assert actions == [("ABOUT", "Create"), ("EVIDENCED_BY", "LinkEvidence"), ("NgAction", "Create"), ("Record", "Create")]
    for a in plan["audits"]:
        assert a["props"]["requestId"] == "req-1" and a["actor"] == STAFF and a["props"]["at"] == NOW


def test_intake_request_can_be_planned():
    original = (FIXTURES / "own_record.md").read_text(encoding="utf-8")
    proposal = {"documentKind": "OwnCaseRecord", "clientId": CLIENT,
                "facts": [{"quote": "児童扶養手当の申請を、離婚後まだしていない", "recordKind": "Interview",
                           "certainty": "Confirmed", "informantKind": "Self"}]}
    got = intake.check(proposal, original, STAFF, "req-intake")
    assert got["ok"], got["errors"]
    plan = _plan(got["request"])
    assert plan["errors"] == []
    assert all(n["props"]["status"] == "Pending" for n in plan["nodes"] if n["label"] == "Record")


def test_validation_errors_do_not_touch_the_driver():
    out = gw.submit(_req([{"ref": "x", "label": "Patient", "origin": "Human", "properties": {}}]), driver=None)
    assert out["ok"] is False and out["errors"]


def test_writes_only_create():
    src = (Path(gw.__file__)).read_text(encoding="utf-8")
    assert "MERGE" not in src
    assert not re.search(r"SET\s+\w+\s*\+=", src)  # 既にあるノードに項目を足し書きしない
    assert not re.search(r"MATCH[^\n]*SET\s+\w+\.", src)  # MATCH したノードの項目を書き換えない


# ---- N-24a：Residence の areaCode はゲートが住所から出す ----

def _residence(**props):
    base = {"address": "福岡県北九州市小倉北区架空町1-2-3", "certainty": "Confirmed", "since": "2023-04-01"}
    base.update(props)
    return _req([{"ref": "r", "label": "Residence", "origin": "Human", "properties": base}],
                [{"type": "RESIDES_AT", "from": {"label": "Client", "id": CLIENT}, "to": "r", "properties": {}}])


def test_gate_derives_area_code_from_the_address():
    plan = _plan(_residence())
    assert plan["errors"] == []
    assert plan["nodes"][0]["props"]["areaCode"] == "401064"


def test_gate_accepts_a_matching_area_code():
    assert _plan(_residence(areaCode="401064"))["errors"] == []


def test_gate_refuses_an_area_code_that_disagrees_with_the_address():
    plan = _plan(_residence(areaCode="401099"))
    assert any("areaCode" in e for e in plan["errors"])


def test_unmatched_address_leaves_area_code_empty():
    plan = _plan(_residence(address="架空県架空市1-2-3"))
    assert plan["errors"] == [] and "areaCode" not in plan["nodes"][0]["props"]


def test_unmatched_address_with_a_given_area_code_is_refused():
    plan = _plan(_residence(address="架空県架空市1-2-3", areaCode="401064"))
    assert any("areaCode" in e for e in plan["errors"])
