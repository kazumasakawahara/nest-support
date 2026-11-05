"""住所からの推定で作れる関わりの種類（2026-11-05 河原さんの決定。台帳 G-62）。DB を使わない。

推定の根拠（inferenceBasis）を持つ関わりは Consultation（相談）と Administrative（手続き）だけ。
住所で分かるのは「この区の窓口が担当になりうる」ことだけで、契約や選任で決まる関わりは推し量れない（G-57 の成年後見センターと同じ考え方）。
"""
from pathlib import Path

import pytest

from nest import canon
from nest.gate import validate as gv

REPO = Path(__file__).resolve().parents[1]
KINDS = canon.load(REPO / "docs" / "SCHEMA.md")["enums"]["involvementKind"]
ALLOWED = ["Consultation", "Administrative"]


def _inv(kind, **extra):
    props = {"kind": kind, "howEnded": "Unknown", "certainty": "Inference", "inferenceBasis": "ResidenceAreaAtTheTime"}
    props.update(extra)
    return {"requestId": "req-ik", "actorStaffId": "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ",
            "nodes": [{"ref": "i", "label": "Involvement", "origin": "AiExtracted", "properties": props}], "relationships": []}


@pytest.mark.parametrize("kind", ALLOWED)
def test_consultation_and_administrative_pass(kind):
    rep = gv.validate(_inv(kind))
    assert rep["ok"], rep["errors"]


@pytest.mark.parametrize("kind", [k for k in KINDS if k not in ALLOWED])
def test_other_kinds_are_refused(kind):
    rep = gv.validate(_inv(kind))
    assert not rep["ok"] and any("住所からの推定" in e and kind in e for e in rep["errors"]), rep["errors"]


def test_refused_kinds_cover_contracts_and_appointments():
    assert {"AgencyContract", "Guardianship", "ServiceProvision"} <= set(KINDS) - set(ALLOWED)


@pytest.mark.parametrize("kind", [k for k in KINDS if k not in ALLOWED])
def test_without_inference_basis_other_kinds_still_pass(kind):
    req = _inv(kind)
    del req["nodes"][0]["properties"]["inferenceBasis"]
    rep = gv.validate(req)
    assert rep["ok"], rep["errors"]
