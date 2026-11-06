"""N-24：機関の候補（ADR-001 D3）。原文の名前から候補を出し、人が orgId を選ぶ。選ぶまでは機関未確定。

- 案（AI が作るもの）に機関 ID（providerOrgId）を書いたら止める。名前の一致だけで orgId を入れない
- 案には原文の提供元の名前（providerName）だけを書く。原文に無い名前は止める
- 職員が選んだ機関 ID を provider_org_id で渡すまでは、提供元は未確定。書き込みの依頼を作らずに、選ぶべき名前を返す
DB を使う候補の引き方は tests/test_org_candidates_live.py（NEST_LIVE_DB=1 のときだけ）。
"""
from pathlib import Path

import pytest

from nest.gate import intake

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "intake"
ORIGINAL = (FIXTURES / "provision_document.md").read_text(encoding="utf-8")
CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"
PROVIDER = "ORG-01HPPPPPPPPPPPPPPPPPPPPPPP"
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
QUOTE = "ハナの右上腕に、指の形に見えるあざ（2か所）を送迎時に確認し、写真を記録"


def _proposal(**over):
    p = {"documentKind": "ProvisionDocument", "providerName": "デイサービス事業所", "clientId": CLIENT,
         "facts": [{"quote": QUOTE, "recordKind": "Document", "certainty": "Hearsay", "providerCertainty": "Confirmed",
                    "informantKind": "Agency"}]}
    p.update(over)
    return p


def test_org_id_written_in_the_proposal_stops():
    rep = intake.check(_proposal(providerOrgId=PROVIDER), ORIGINAL, ACTOR, "req", provider_org_id=PROVIDER)
    assert not rep["ok"] and any("候補から" in e for e in rep["errors"])


def test_until_a_person_chooses_the_provider_is_unresolved():
    rep = intake.check(_proposal(), ORIGINAL, ACTOR, "req")
    assert not rep["ok"] and rep["request"] is None
    assert rep["needsProviderChoice"] == "デイサービス事業所"
    assert any("未確定" in e for e in rep["errors"])


def test_provider_name_must_be_in_the_original():
    rep = intake.check(_proposal(providerName="架空の別の事業所"), ORIGINAL, ACTOR, "req", provider_org_id=PROVIDER)
    assert not rep["ok"] and any("原文に無い" in e for e in rep["errors"])


def test_chosen_provider_goes_into_the_request():
    rep = intake.check(_proposal(), ORIGINAL, ACTOR, "req", provider_org_id=PROVIDER)
    assert rep["ok"], rep["errors"]
    org = [n for n in rep["request"]["nodes"] if n["label"] == "Organization"]
    assert org == [{"ref": "provider", "label": "Organization", "origin": "Human", "properties": {"orgId": PROVIDER}}]


@pytest.mark.parametrize("bad", ["", "ORG-x", "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ", "デイサービス事業所"])
def test_chosen_provider_must_be_an_org_id(bad):
    rep = intake.check(_proposal(), ORIGINAL, ACTOR, "req", provider_org_id=bad)
    assert not rep["ok"]


def test_own_record_takes_no_provider():
    own = {"documentKind": "OwnCaseRecord", "clientId": CLIENT, "facts": _proposal()["facts"]}
    assert not intake.check(dict(own, providerName="デイサービス事業所"), ORIGINAL, ACTOR, "req")["ok"]
    assert not intake.check(own, ORIGINAL, ACTOR, "req", provider_org_id=PROVIDER)["ok"]


@pytest.mark.parametrize("name", [None, "", "  ", "区"])
def test_too_short_or_empty_names_give_no_search(name):
    from nest import org_candidates
    with pytest.raises(ValueError):
        org_candidates.by_name(None, name)


def test_candidates_carry_no_score_and_are_marked_unchosen():
    from nest import org_candidates
    assert org_candidates.CANDIDATE_KEYS == {"orgId", "name", "kind", "matchedBy"}
    src = (Path(org_candidates.__file__)).read_text(encoding="utf-8")
    assert "score" not in src.lower()
