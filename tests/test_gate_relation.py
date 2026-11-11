"""続柄（RELATED_TO）の受付の検証と書き込み（2026-11-12 河原さんの承認。正典 v0.14 §7・§4.3。台帳 G-102）。DB を使わない。

- AI 由来の RELATED_TO は、同じ依頼の AI 由来の新しい Person からだけ張れる。status はゲートが Pending にする
  （依頼が Pending 以外を書いていたら止める。自動で直さない）
- evidenceRecordIds は、同じ依頼の Record の名札か、既にある REC-…。名札は書くときに発番した ID に置き換える
- 人が作る（Human）RELATED_TO は今のまま
"""
import datetime as dt

from nest.gate import validate as gv
from nest.gate import write as gw

NOW = dt.datetime(2026, 11, 12, 9, 0, tzinfo=dt.timezone.utc)
STAFF = "STF-" + "0" * 26
CLIENT = {"label": "Client", "id": "CLI-" + "1" * 26}
PER = {"label": "Person", "id": "PER-" + "2" * 26}
REC = "REC-" + "3" * 26


def _record(ref="fact-1"):
    return {"ref": ref, "label": "Record", "origin": "AiExtracted",
            "properties": {"kind": "Interview", "text": "母が話した。", "quote": "母が話した。", "certainty": "Hearsay",
                           "informantKind": "Family"}}


def _req(rel_props, person_origin="AiExtracted", frm="mother", extra_nodes=()):
    nodes = [_record()] + list(extra_nodes)
    if person_origin:
        nodes.append({"ref": "mother", "label": "Person", "origin": person_origin, "properties": {}})
    rels = [{"type": "ABOUT", "from": "fact-1", "to": CLIENT, "properties": {}},
            {"type": "TOLD_BY", "from": "fact-1", "to": "mother" if person_origin else PER, "properties": {}},
            {"type": "RELATED_TO", "from": frm, "to": CLIENT, "properties": rel_props}]
    return {"requestId": "req-1", "actorStaffId": STAFF, "nodes": nodes, "relationships": rels}


BASE = {"kind": "Parent", "certainty": "Hearsay", "evidenceRecordIds": ["fact-1"]}


def _rel(rep):
    (rel,) = [r for r in rep["relationships"] if r["type"] == "RELATED_TO"]
    return rel


def test_an_ai_relation_from_a_new_ai_person_enters_pending():
    rep = gv.validate(_req(dict(BASE)))
    assert rep["ok"], rep["errors"]
    assert _rel(rep)["properties"]["status"] == "Pending"


def test_an_ai_relation_written_as_active_stops():
    rep = gv.validate(_req(dict(BASE, status="Active")))
    assert not rep["ok"] and any("RELATED_TO" in e and "Pending" in e for e in rep["errors"]), rep["errors"]


def test_an_ai_relation_written_as_pending_is_accepted():
    rep = gv.validate(_req(dict(BASE, status="Pending")))
    assert rep["ok"], rep["errors"]


def test_an_ai_request_cannot_add_a_relation_to_an_existing_person():
    """既にいる人から、AI 由来の依頼（新しい AI の記録を含む）で続柄を張ると止まる"""
    rep = gv.validate(_req(dict(BASE), person_origin=None, frm=PER))
    assert not rep["ok"] and any("RELATED_TO" in e and "新しい" in e for e in rep["errors"]), rep["errors"]


def test_an_evidence_ref_must_be_a_record_in_the_request():
    rep = gv.validate(_req(dict(BASE, evidenceRecordIds=["fact-9"])))
    assert not rep["ok"] and any("evidenceRecordIds" in e and "fact-9" in e for e in rep["errors"]), rep["errors"]


def test_an_existing_record_id_is_accepted_as_evidence():
    rep = gv.validate(_req(dict(BASE, evidenceRecordIds=[REC])))
    assert rep["ok"], rep["errors"]


def test_a_human_relation_stays_as_it_was():
    req = {"requestId": "req-1", "actorStaffId": STAFF, "nodes": [],
           "relationships": [{"type": "RELATED_TO", "from": PER, "to": CLIENT,
                              "properties": dict(BASE, evidenceRecordIds=[REC], status="Active")}]}
    rep = gv.validate(req)
    assert rep["ok"], rep["errors"]
    assert _rel(rep)["properties"]["status"] == "Active"


def test_write_replaces_the_evidence_ref_with_the_issued_record_id():
    req = _req(dict(BASE))
    rep = gv.validate(req)
    plan = gw.build_plan(rep, req, NOW, lambda prefix: "%s-%s" % (prefix, "A" * 26), lambda: "C-ABCDEF")
    assert plan["errors"] == []
    (rel,) = [r for r in plan["relationships"] if r["type"] == "RELATED_TO"]
    assert rel["props"]["evidenceRecordIds"] == [plan["ids"]["fact-1"]]
    assert rel["props"]["status"] == "Pending"
    assert any(a["props"]["targetLabel"] == "RELATED_TO" for a in plan["audits"])
