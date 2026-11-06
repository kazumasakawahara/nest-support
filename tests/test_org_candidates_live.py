"""N-24：資源の側から、原文の名前で機関の候補を引く。NEST_LIVE_DB=1 のときだけ。資源の側は読むだけ。"""
import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")


@pytest.fixture(scope="module")
def resource():
    from nest import connections
    with connections.driver("resource") as d:
        yield d


def test_name_with_spaces_or_full_width_matches(resource):
    from nest import org_candidates
    a = org_candidates.by_name(resource, "門司区役所 保健福祉課")
    b = org_candidates.by_name(resource, "門司区役所　保健福祉課")
    assert a["candidates"] and a["candidates"] == b["candidates"]
    for c in a["candidates"]:
        assert set(c) == org_candidates.CANDIDATE_KEYS and c["orgId"].startswith("ORG-")
    assert a["chosen"] is None


def test_alias_names_are_searched(resource):
    from nest import org_candidates
    rows = org_candidates.by_name(resource, "みどり園")["candidates"]
    assert any("みどり園" in c["name"] for c in rows)


def test_many_matches_are_cut_and_said_so(resource):
    from nest import org_candidates
    out = org_candidates.by_name(resource, "事業所", limit=5)
    assert len(out["candidates"]) == 5 and out["truncated"] is True


def test_no_match_returns_empty_not_a_guess(resource):
    from nest import org_candidates
    out = org_candidates.by_name(resource, "架空の存在しない機関名XYZ")
    assert out["candidates"] == [] and out["chosen"] is None
