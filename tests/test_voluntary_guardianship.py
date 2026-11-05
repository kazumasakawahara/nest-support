"""正典 v0.8（2026-11-06 河原さんの決定。台帳 G-62）：任意後見と任意代理を tsunagu-net の BRS-49（SEMANTICS v0.32）に合わせる。DB を使わない。

- 後見の類型：VoluntaryGuardianship（効力が生じた後）と VoluntaryGuardianshipContracted（任意後見受任者。効力の前、代理権は無い）
- 関わりの種類 AgencyContract（委任契約による任意代理）。社協の日常生活自立支援事業は ServiceProvision のまま
- 終わり方 Transitioned：受任者の段階と任意代理の関わりにだけ書ける
- 令和 8 年法律第 45 号の施行の前なので、後見・保佐はまだ止めない（止めるのは政令の後）
"""
from pathlib import Path

import pytest

from nest import canon
from nest.gate import validate as gv

REPO = Path(__file__).resolve().parents[1]
C = canon.load(REPO / "docs" / "SCHEMA.md")
TEXT = (REPO / "docs" / "SCHEMA.md").read_text(encoding="utf-8")
SEM = (REPO / "docs" / "SEMANTICS.md").read_text(encoding="utf-8")


def test_enums_follow_tsunagu_net():
    assert C["enums"]["guardianshipType"] == ["Guardianship", "Curatorship", "Assistance",
                                              "VoluntaryGuardianship", "VoluntaryGuardianshipContracted"]
    assert "AgencyContract" in C["enums"]["involvementKind"]
    assert C["enums"]["howEnded"] == ["Ongoing", "Lapsed", "DeclinedByPerson", "EndedByAgency", "Unknown", "Transitioned"]


def test_canon_and_semantics_define_the_values():
    for words in (("VoluntaryGuardianshipContracted", "代理権は無い"),
                  ("VoluntaryGuardianship", "任意後見監督人の選任", "任意後見開始の審判"),
                  ("AgencyContract", "日常生活自立支援事業", "ServiceProvision"),
                  ("Transitioned",)):
        assert all(w in TEXT for w in words), words
    for words in (("任意後見契約に関する法律", "第2条第1号", "後見登記等に関する法律", "第5条第3号"),
                  ("令和 8 年法律第 45 号", "政令", "【未照合"),
                  ("民法", "第643条", "第99条第1項"),
                  ("委任者は本人", "第2条第2号")):
        assert all(w in SEM for w in words), words


def _inv(**props):
    base = {"kind": "Guardianship", "howEnded": "Ongoing", "certainty": "Confirmed"}
    base.update(props)
    return {"requestId": "req-vg", "actorStaffId": "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ",
            "nodes": [{"ref": "i", "label": "Involvement", "origin": "Human", "properties": base}], "relationships": []}


@pytest.mark.parametrize("gtype", ["Guardianship", "Curatorship", "Assistance", "VoluntaryGuardianship", "VoluntaryGuardianshipContracted"])
def test_every_guardianship_type_still_passes(gtype):
    rep = gv.validate(_inv(guardianshipType=gtype))
    assert rep["ok"], rep["errors"]


def test_agency_contract_passes_without_guardianship_type():
    rep = gv.validate(_inv(kind="AgencyContract"))
    assert rep["ok"], rep["errors"]


def test_agency_contract_takes_no_guardianship_type():
    rep = gv.validate(_inv(kind="AgencyContract", guardianshipType="VoluntaryGuardianship"))
    assert not rep["ok"] and any("guardianshipType" in e for e in rep["errors"])


@pytest.mark.parametrize("props", [{"guardianshipType": "VoluntaryGuardianshipContracted"}, {"kind": "AgencyContract"}])
def test_transitioned_passes_on_the_two_involvements(props):
    rep = gv.validate(_inv(howEnded="Transitioned", endDate="2026-10-01", **props))
    assert rep["ok"], rep["errors"]


@pytest.mark.parametrize("props", [{"guardianshipType": "VoluntaryGuardianship"}, {"guardianshipType": "Assistance"},
                                   {"guardianshipType": "Guardianship"}, {"kind": "Consultation"}, {"kind": "ServiceProvision"}])
def test_transitioned_is_refused_elsewhere(props):
    rep = gv.validate(_inv(howEnded="Transitioned", **props))
    assert not rep["ok"] and any("Transitioned" in e for e in rep["errors"])
