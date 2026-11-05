"""正典 v0.6（2026-11-05 河原さんの決定）：関わりの種類 Employment・Administrative の定義と、推定の根拠。DB を使わない。

- Employment・Administrative は nest-support の正典にだけ置く（tsunagu-net には足さない。台帳 G-40 のこの部分を閉じた）
- 関わりに推定の根拠（inferenceBasis）を決まった値で持つ。住所そのものは持たない。確度が Inference の関わりにだけ書ける
- 関わりの注記（note）：雇用契約が支援の上で大事なときなどに書く
"""
from pathlib import Path

import pytest

from nest import canon
from nest.gate import intake
from nest.gate import validate as gv

REPO = Path(__file__).resolve().parents[1]
C = canon.load(REPO / "docs" / "SCHEMA.md")
TEXT = (REPO / "docs" / "SCHEMA.md").read_text(encoding="utf-8")


def test_kinds_and_inference_basis_are_in_the_canon():
    assert {"Employment", "Administrative"} <= set(C["enums"]["involvementKind"])
    assert C["enums"]["inferenceBasis"] == ["ResidenceAreaAtTheTime", "CurrentResidenceArea"]
    inv = C["personal"]["nodes"]["Involvement"]
    assert {"inferenceBasis", "note"} <= set(inv["optional"])
    assert C["enumBindings"]["Involvement.inferenceBasis"] == "inferenceBasis"
    assert "address" not in inv["required"] + inv["optional"] and "areaCode" not in inv["required"] + inv["optional"]


def test_canon_defines_the_two_kinds_and_their_boundaries():
    for words in (("Employment", "特例子会社", "機関 ID の形"),
                  ("就労移行支援", "就労継続支援", "就労定着支援", "就労選択支援", "ServiceProvision"),
                  ("Administrative", "申請", "更新", "決定"),
                  ("相談", "Consultation", "二つ")):
        assert all(w in TEXT for w in words), words
    assert "tsunagu-net へ足す提案" not in TEXT.split("## 変更履歴")[0].split("`involvementKind`")[1][:300]


def _inv(**props):
    base = {"kind": "Consultation", "howEnded": "Unknown", "certainty": "Inference"}
    base.update(props)
    return {"requestId": "req-v6", "actorStaffId": "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ",
            "nodes": [{"ref": "i", "label": "Involvement", "origin": "AiExtracted", "properties": base}], "relationships": []}


@pytest.mark.parametrize("basis", ["ResidenceAreaAtTheTime", "CurrentResidenceArea"])
def test_inference_basis_passes_on_an_inferred_involvement(basis):
    rep = gv.validate(_inv(inferenceBasis=basis))
    assert rep["ok"], rep["errors"]


@pytest.mark.parametrize("certainty", ["Confirmed", "Hearsay", "SelfReport", "Unspecified"])
def test_inference_basis_only_on_inference(certainty):
    rep = gv.validate(_inv(certainty=certainty, inferenceBasis="ResidenceAreaAtTheTime"))
    assert not rep["ok"] and any("inferenceBasis" in e for e in rep["errors"])


@pytest.mark.parametrize("value", ["福岡県北九州市小倉北区", "401064", "AddressArea", "residenceareaatthetime_x"])
def test_inference_basis_is_a_fixed_value_not_an_address(value):
    assert not gv.validate(_inv(inferenceBasis=value))["ok"]


def test_employment_with_a_note_and_no_organization_passes():
    rep = gv.validate(_inv(kind="Employment", certainty="Hearsay", note="雇用契約あり（架空）"))
    assert rep["ok"], rep["errors"]


# ---- 取り込みの案：推定の根拠は道具が推定の結果から付ける ----

OWN = (REPO / "tests" / "fixtures" / "intake" / "own_record_desk.md").read_text(encoding="utf-8")
QUOTE = "母の話では、去年の春に区役所の相談コーナーで、本人の通所のことを相談した"
ORG = "ORG-01AAAAAAAAAAAAAAAAAAAAAAAA"


def _check(basis, org=ORG, extra=None):
    est = {"basis": basis, "notes": [], "window": None, "chosen": None, "truncated": False,
           "candidates": [{"orgId": ORG, "name": "架空", "kind": "DisabilityDivision", "servesBasis": "PresumedByLocation",
                           "partOfArea": False, "viaParent": False}]}
    inv = {"quote": QUOTE, "kind": "Consultation"}
    if org:
        inv["orgId"] = org
    inv.update(extra or {})
    p = {"documentKind": "OwnCaseRecord", "clientId": "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ",
         "facts": [{"quote": QUOTE, "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family"}],
         "involvements": [inv]}
    return intake.check(p, OWN, actor_staff_id="STF-01HZZZZZZZZZZZZZZZZZZZZZZZ", request_id="req-v6", estimate=est)


def _props(rep):
    return next(n for n in rep["request"]["nodes"] if n["label"] == "Involvement")["properties"]


@pytest.mark.parametrize("basis, value", [("AtTheTime", "ResidenceAreaAtTheTime"), ("CurrentFallback", "CurrentResidenceArea")])
def test_chosen_candidate_carries_the_inference_basis(basis, value):
    rep = _check(basis)
    assert rep["ok"], rep["errors"]
    assert _props(rep)["inferenceBasis"] == value
    assert gv.validate(rep["request"])["ok"]


def test_no_basis_when_the_organization_is_not_chosen():
    rep = _check("AtTheTime", org=None)
    assert rep["ok"] and "inferenceBasis" not in _props(rep)


def test_proposal_cannot_write_the_basis_or_a_note_itself():
    for extra in ({"inferenceBasis": "ResidenceAreaAtTheTime"}, {"note": "x"}):
        rep = _check("AtTheTime", extra=extra)
        assert not rep["ok"]
