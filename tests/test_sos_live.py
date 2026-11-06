"""N-36：sos の本人の確認（lookup_client）が、起動した個人の側（127.0.0.1:37687）を読み取りの包みで読めること。
NEST_LIVE_DB=1 のときだけ。

    NEST_LIVE_DB=1 uv run pytest -q tests/test_sos_live.py

架空の本人を一人ゲートで作り、その仮名で「いる」、無い仮名で「いない」を確かめる。
包みは NEXT-02 の歯止めがそろわないと読まないので、試験の間だけ架空の印（NestLiveProbe）を置き、終わったら外す。
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")
pytest.importorskip("fastapi")


def _q(d, query, **params):
    records, _, _ = d.execute_query(query, params, database_="neo4j")
    return [r.data() for r in records]


def test_lookup_finds_a_fictional_client_through_the_wrapper():
    import sos.api_server as sos
    from nest import connections
    from nest.gate import write as gw
    probe = "sos-" + uuid.uuid4().hex
    with connections.driver("personal") as d:
        admin = _q(d, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")
        if not admin:
            pytest.skip("Administrator がいない（ほかの DB つきの試験を先に流す）")
        out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin[0]["id"],
                         "nodes": [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空"}}],
                         "relationships": []}, d)
        assert out["ok"], out["errors"]
        code = _q(d, "MATCH (c:Client {clientId: $id}) RETURN c.displayCode AS code", id=out["ids"]["c"])[0]["code"]
        d.execute_query("CREATE (:NestLiveProbe {probe: $probe, _fictional: true})", {"probe": probe}, database_="neo4j")
    try:
        assert sos.lookup_client(code) is True
        missing = "C-" + ("Z" * 6 if code != "C-ZZZZZZ" else "Y" * 6)
        assert sos.lookup_client(missing) is False
    finally:
        with connections.driver("personal") as d:
            d.execute_query("MATCH (n:NestLiveProbe {probe: $probe}) DELETE n", {"probe": probe}, database_="neo4j")
