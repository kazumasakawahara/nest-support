"""止まる点 4 の決定（2026-11-05 河原さん。台帳 G-59）。DB を使わない部分。

- 推定で作った機関の写し（Organization。公開 ID への参照）は、AI 由来でも Active で作る。判断の中身は Pending の関わりの側で承認する
- 承認の前に、関わりの中身（種類・確度・終わり方・推定の根拠・機関）を見えるようにする
DB の試験は tests/test_gate_approve_live.py。
"""
from pathlib import Path

from nest.gate import approve as ga
from nest.gate import intake
from nest.gate import validate as gv

ORG = "ORG-01AAAAAAAAAAAAAAAAAAAAAAAA"
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"


def _req(nodes):
    return {"requestId": "req-s4", "actorStaffId": ACTOR, "nodes": nodes, "relationships": []}


def test_ai_made_organization_reference_is_active_but_the_involvement_stays_pending():
    rep = gv.validate(_req([
        {"ref": "o", "label": "Organization", "origin": "AiExtracted", "properties": {"orgId": ORG}},
        {"ref": "i", "label": "Involvement", "origin": "AiExtracted",
         "properties": {"kind": "Consultation", "howEnded": "Unknown", "certainty": "Inference"}}]))
    assert rep["ok"], rep["errors"]
    status = {n["ref"]: (n["origin"], n["status"]) for n in rep["nodes"]}
    assert status["o"] == ("AiExtracted", "Active")       # 由来は偽らない。状態だけ Active
    assert status["i"] == ("AiExtracted", "Pending")


def test_estimated_organization_from_intake_is_active():
    own = (Path(__file__).resolve().parent / "fixtures" / "intake" / "own_record_desk.md").read_text(encoding="utf-8")
    quote = "母の話では、去年の春に区役所の相談コーナーで、本人の通所のことを相談した"
    est = {"basis": "AtTheTime", "notes": [], "window": None, "chosen": None, "truncated": False,
           "candidates": [{"orgId": ORG, "name": "架空", "kind": "DisabilityDivision", "servesBasis": "PresumedByLocation",
                           "partOfArea": False, "viaParent": False}]}
    p = {"documentKind": "OwnCaseRecord", "clientId": "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ",
         "facts": [{"quote": quote, "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family"}],
         "involvements": [{"quote": quote, "kind": "Consultation", "orgId": ORG}]}
    rep = intake.check(p, own, actor_staff_id=ACTOR, request_id="req-s4", estimate=est)
    v = gv.validate(rep["request"])
    by_label = {n["label"]: n["status"] for n in v["nodes"]}
    assert by_label["Organization"] == "Active" and by_label["Involvement"] == "Pending" and by_label["Record"] == "Pending"


def test_involvement_content_shows_kind_certainty_basis_and_organization():
    props = {"involvementId": "INV-1", "kind": "Consultation", "certainty": "Inference", "howEnded": "Unknown",
             "inferenceBasis": "CurrentResidenceArea", "status": "Pending", "origin": "AiExtracted"}
    out = ga.involvement_content(props, [ORG], {ORG: "架空区相談コーナー"})
    assert out == {"kind": "Consultation", "certainty": "Inference", "howEnded": "Unknown",
                   "inferenceBasis": "CurrentResidenceArea", "note": None,
                   "organizations": [{"orgId": ORG, "name": "架空区相談コーナー"}], "organizationUndecided": False}


def test_involvement_content_without_organization_says_undecided():
    out = ga.involvement_content({"kind": "Employment", "certainty": "Hearsay", "howEnded": "Ongoing", "note": "雇用契約あり（架空）"}, [], {})
    assert out["organizations"] == [] and out["organizationUndecided"] is True
    assert out["inferenceBasis"] is None and out["note"] == "雇用契約あり（架空）"


def test_involvement_content_without_resource_names_keeps_the_id():
    out = ga.involvement_content({"kind": "Consultation", "certainty": "Inference", "howEnded": "Unknown"}, [ORG], None)
    assert out["organizations"] == [{"orgId": ORG, "name": None}]
