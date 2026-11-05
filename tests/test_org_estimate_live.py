"""N-24a：担当機関の推定を、起動した二つの DB で確かめる。NEST_LIVE_DB=1 のときだけ。

個人の側には架空の本人と架空の住所だけを書く。資源の側は読むだけ（tsunagu-net の配布の一式を読み込んだもの。N-23）。
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

from tests.test_gate_write_live import admin, driver  # noqa: E402,F401  フィクスチャ（個人の側）

KOKURAKITA, YAHATANISHI = "401064", "401099"


@pytest.fixture(scope="module")
def resource():
    from nest import connections
    with connections.driver("resource") as d:
        yield d


def _client(driver, admin, residences):
    from nest.gate import write as gw
    nodes = [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空", "givenName": "推定"}}]
    rels = []
    for n, (address, since, until) in enumerate(residences):
        props = {"address": address, "certainty": "Confirmed", "since": since}
        if until:
            props["until"] = until
        nodes.append({"ref": "r%d" % n, "label": "Residence", "origin": "Human", "properties": props})
        rels.append({"type": "RESIDES_AT", "from": "c", "to": "r%d" % n, "properties": {}})
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin, "nodes": nodes, "relationships": rels}, driver)
    assert out["ok"], out["errors"]
    return out["ids"]["c"]


def test_gate_stores_the_area_code_it_derived(driver, admin):
    cid = _client(driver, admin, [("福岡県北九州市小倉北区架空町1-2-3", "2023-04-01", None)])
    rows = driver.execute_query("MATCH (:Client {clientId: $id})-[:RESIDES_AT]->(r:Residence) RETURN r.areaCode AS a", {"id": cid}).records
    assert [r["a"] for r in rows] == [KOKURAKITA]


def test_candidates_are_consultation_desks_serving_the_ward(resource):
    from nest import org_estimate as oe
    got = oe.by_area(resource, KOKURAKITA)["candidates"]
    names = {c["name"] for c in got}
    assert "小倉北区高齢者・障害者相談コーナー" in names
    assert all(c["kind"] in oe.CONSULTATION_KINDS for c in got)
    assert all(c["servesBasis"] in ("Designated", "PresumedByLocation") for c in got)
    other = {c["orgId"] for c in oe.by_area(resource, YAHATANISHI)["candidates"] if not c["viaParent"]}
    assert not other & {c["orgId"] for c in got if not c["viaParent"]}  # 他の区だけの担当は出ない


def test_unknown_area_gives_no_candidates(resource):
    from nest import org_estimate as oe
    assert oe.by_area(resource, "999999")["candidates"] == []


def test_past_mention_uses_the_old_ward(driver, admin, resource):
    from nest import org_estimate as oe
    cid = _client(driver, admin, [("福岡県北九州市小倉北区架空町1-2-3", "2023-04-01", None),
                                  ("福岡県北九州市八幡西区架空台4-5", "2015-04-01", "2023-04-01")])
    past = oe.estimate(driver, resource, cid, "2020-06-01")
    assert past["basis"] == "AtTheTime" and past["notes"] == []
    assert {c["orgId"] for c in past["candidates"]} == {c["orgId"] for c in oe.by_area(resource, YAHATANISHI)["candidates"]}
    text = repr(past)
    assert YAHATANISHI not in text and "架空台" not in text
    fallback = oe.estimate(driver, resource, _client(driver, admin, [("福岡県北九州市小倉北区架空町9", "2023-04-01", None)]), "2019-01-01")
    assert fallback["basis"] == "CurrentFallback" and fallback["notes"]


def test_address_outside_the_table_leaves_the_organization_undecided(driver, admin, resource):
    from nest import org_estimate as oe
    cid = _client(driver, admin, [("架空県架空市1-2-3", "2023-04-01", None)])
    est = oe.estimate(driver, resource, cid, "2024-01-01")
    assert est["candidates"] == [] and est["notes"]
