"""正典 v0.7（2026-11-05 河原さんの決定。台帳 G-60）：関わりを本人以外の人（Person。親など）にも向けられる。DB を使わない。

- 本人以外の人の関わりは、原文の引用（根拠の記録）を必ず付け、未確定（Pending）で入れる。人が承認する
- 住所からの推定（inferenceBasis）では、本人以外の人の関わりを作らない（ゲートで止める）
- 両方向（作れる例・止める例）
"""
import pytest

from nest import canon
from nest.gate import intake
from nest.gate import validate as gv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"
PER = "PER-01H11111111111111111111111"
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
ORG = "ORG-01AAAAAAAAAAAAAAAAAAAAAAAA"


def test_canon_lets_concerns_point_to_a_person():
    c = canon.load(REPO / "docs" / "SCHEMA.md")
    assert c["personal"]["relationships"]["CONCERNS"]["to"] == ["Client", "Person"]


def _inv(origin="AiExtracted", **props):
    base = {"kind": "Consultation", "howEnded": "Unknown", "certainty": "Hearsay"}
    base.update(props)
    return {"ref": "i", "label": "Involvement", "origin": origin, "properties": base}


REC = {"ref": "r", "label": "Record", "origin": "AiExtracted",
       "properties": {"kind": "Interview", "text": "母が地域包括支援センターに相談した", "quote": "母が地域包括支援センターに相談した",
                      "certainty": "Hearsay", "informantKind": "Family"}}


def _req(nodes, rels):
    return {"requestId": "req-p", "actorStaffId": ACTOR, "nodes": nodes, "relationships": rels}


def _concerns(to):
    return {"type": "CONCERNS", "from": "i", "to": to}


EVID = {"type": "EVIDENCED_BY", "from": "i", "to": "r"}
ABOUT = {"type": "ABOUT", "from": "r", "to": {"label": "Client", "id": CLIENT}}


# ---- 作れる例 ----

@pytest.mark.parametrize("origin", ["AiExtracted", "Human"])
def test_person_involvement_with_a_quote_passes_as_pending(origin):
    rep = gv.validate(_req([_inv(origin), REC], [_concerns({"label": "Person", "id": PER}), EVID, ABOUT]))
    assert rep["ok"], rep["errors"]
    assert {n["ref"]: n["status"] for n in rep["nodes"]}["i"] == "Pending"   # 人が入れても Pending（承認して確定）


def test_new_person_in_the_same_request_can_be_the_target():
    mother = {"ref": "mother", "label": "Person", "origin": "AiExtracted", "properties": {}}
    rep = gv.validate(_req([_inv(), REC, mother], [_concerns("mother"), EVID, ABOUT]))
    assert rep["ok"], rep["errors"]


def test_client_involvement_keeps_the_inference_basis():
    rep = gv.validate(_req([_inv(certainty="Inference", inferenceBasis="ResidenceAreaAtTheTime"), REC],
                           [_concerns({"label": "Client", "id": CLIENT}), EVID, ABOUT]))
    assert rep["ok"], rep["errors"]


# ---- 止める例 ----

def test_person_involvement_without_a_quote_is_refused():
    rep = gv.validate(_req([_inv()], [_concerns({"label": "Person", "id": PER})]))
    assert not rep["ok"] and any("根拠" in e for e in rep["errors"])


def test_person_involvement_from_the_address_estimate_is_refused():
    rep = gv.validate(_req([_inv(certainty="Inference", inferenceBasis="CurrentResidenceArea"), REC],
                           [_concerns({"label": "Person", "id": PER}), EVID, ABOUT]))
    assert not rep["ok"] and any("住所" in e for e in rep["errors"])


def test_staff_cannot_be_the_target():
    rep = gv.validate(_req([_inv(), REC], [_concerns({"label": "Staff", "id": ACTOR}), EVID, ABOUT]))
    assert not rep["ok"]


# ---- 取り込みの案 ----

OWN = "- 母は、先月、地域包括支援センターに自分の介護のことを相談したと話した【本人の話】\n"
QUOTE = "母は、先月、地域包括支援センターに自分の介護のことを相談したと話した"


def _proposal(inv, people=None):
    p = {"documentKind": "OwnCaseRecord", "clientId": CLIENT,
         "facts": [{"quote": QUOTE, "recordKind": "Interview", "certainty": "SelfReport", "informantKind": "Family"}],
         "involvements": [inv]}
    if people:
        p["newPeople"] = people
    return p


EST = {"basis": "AtTheTime", "notes": [], "window": None, "chosen": None, "truncated": False,
       "candidates": [{"orgId": ORG, "name": "架空", "kind": "CommunityGeneralSupportCenter", "servesBasis": "Designated",
                       "partOfArea": False, "viaParent": False}]}


def _check(p, estimate=None):
    return intake.check(p, OWN, actor_staff_id=ACTOR, request_id="req-p", estimate=estimate)


def _concerns_of(rep):
    return [r["to"] for r in rep["request"]["relationships"] if r["type"] == "CONCERNS"]


@pytest.mark.parametrize("target, expect", [(PER, {"label": "Person", "id": PER}), ("mother", "mother")])
def test_intake_can_point_an_involvement_to_a_person(target, expect):
    people = [{"ref": "mother"}] if target == "mother" else None
    rep = _check(_proposal({"quote": QUOTE, "kind": "Consultation", "concerns": target}, people))
    assert rep["ok"], rep["errors"]
    assert _concerns_of(rep) == [expect]
    assert gv.validate(rep["request"])["ok"]


def test_intake_default_target_is_the_client():
    rep = _check(_proposal({"quote": QUOTE, "kind": "Consultation"}))
    assert _concerns_of(rep) == [{"label": "Client", "id": CLIENT}]


def test_intake_refuses_a_person_involvement_with_an_estimated_org():
    rep = _check(_proposal({"quote": QUOTE, "kind": "Consultation", "concerns": PER, "orgId": ORG}), EST)
    assert not rep["ok"] and any("住所" in e for e in rep["errors"])


@pytest.mark.parametrize("target", ["母", "PER-x", "father", ""])
def test_intake_refuses_a_person_by_name_or_unknown_ref(target):
    rep = _check(_proposal({"quote": QUOTE, "kind": "Consultation", "concerns": target}))
    assert not rep["ok"] and any("concerns" in e for e in rep["errors"])
