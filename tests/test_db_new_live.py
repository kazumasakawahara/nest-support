"""N-18：起動した新しい 2 つの Neo4j（個人の側・資源の側）への接続の試験。2026-11-05 河原さんの条件。

動かすのは NEST_LIVE_DB=1 のときだけ（ふだんの試験は DB を使わない）:
    NEST_LIVE_DB=1 uv run pytest -q tests/test_db_new_live.py

- 両方に接続でき、どちらも 5.26 の Community 版で、APOC が無い
- 互いのデータが見えない（個人の側に置いた架空の印が、資源の側から見えない）
- 個人の側の認証で資源の側に入れない（その逆も）
- file: の LOAD CSV が止まっている
認証情報は ~/.config/nest/neo4j-redesign.env から読む。値は表示しない。
資源の側には書かない（読み込みの道具 N-23 だけが書く）。個人の側に置く印は架空で、試験の終わりに消す。
"""
import os
import time
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

ENV_FILE = Path.home() / ".config" / "nest" / "neo4j-redesign.env"
SIDES = {
    "personal": ("bolt://127.0.0.1:37687", "NEST_PERSONAL_PASSWORD"),
    "resource": ("bolt://127.0.0.1:38687", "NEST_RESOURCE_PASSWORD"),
}


def _password(key):
    from dotenv import dotenv_values
    value = dotenv_values(ENV_FILE).get(key)
    assert value, "%s が %s に無い" % (key, ENV_FILE)
    return value


def _driver(side, password_of=None):
    from neo4j import GraphDatabase
    uri, key = SIDES[side]
    return GraphDatabase.driver(uri, auth=("neo4j", _password(SIDES[password_of or side][1])))


def _wait(driver, seconds=90):
    from neo4j.exceptions import ServiceUnavailable
    end = time.monotonic() + seconds
    while True:
        try:
            driver.verify_connectivity()
            return
        except ServiceUnavailable:
            if time.monotonic() > end:
                raise
            time.sleep(2)


@pytest.fixture(scope="module")
def drivers():
    ds = {side: _driver(side) for side in SIDES}
    try:
        for d in ds.values():
            _wait(d)
        yield ds
    finally:
        for d in ds.values():
            d.close()


def _read(driver, query, **params):
    records, _, _ = driver.execute_query(query, params, routing_="r", database_="neo4j")
    return [r.data() for r in records]


@pytest.mark.parametrize("side", sorted(SIDES))
def test_reachable_and_community_5_26(drivers, side):
    rows = _read(drivers[side], "CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition")
    kernel = [r for r in rows if r["name"] == "Neo4j Kernel"]
    assert kernel and kernel[0]["edition"] == "community"
    assert kernel[0]["versions"][0].startswith("5.26.")


@pytest.mark.parametrize("side", sorted(SIDES))
def test_no_apoc(drivers, side):
    rows = _read(drivers[side], "SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'apoc' RETURN count(*) AS n")
    assert rows == [{"n": 0}]


@pytest.mark.parametrize("side", sorted(SIDES))
def test_file_load_csv_is_off(drivers, side):
    rows = _read(drivers[side], "SHOW SETTINGS YIELD name, value "
                                "WHERE name = 'dbms.security.allow_csv_import_from_file_urls' RETURN value")
    assert rows == [{"value": "false"}]


def test_data_is_not_visible_across(drivers):
    probe = "probe-" + uuid.uuid4().hex
    personal, resource = drivers["personal"], drivers["resource"]
    personal.execute_query("CREATE (:NestLiveProbe {probe: $probe, _fictional: true})", {"probe": probe}, database_="neo4j")
    try:
        assert _read(personal, "MATCH (n:NestLiveProbe {probe: $probe}) RETURN count(n) AS n", probe=probe) == [{"n": 1}]
        assert _read(resource, "MATCH (n {probe: $probe}) RETURN count(n) AS n", probe=probe) == [{"n": 0}]
    finally:
        personal.execute_query("MATCH (n:NestLiveProbe {probe: $probe}) DELETE n", {"probe": probe}, database_="neo4j")
    assert _read(personal, "MATCH (n:NestLiveProbe) RETURN count(n) AS n") == [{"n": 0}]


@pytest.mark.parametrize("side,other", [("personal", "resource"), ("resource", "personal")])
def test_one_sides_password_does_not_open_the_other(side, other):
    from neo4j.exceptions import AuthError
    with _driver(side, password_of=other) as d:
        with pytest.raises(AuthError):
            d.verify_connectivity()


def test_schema_applied_to_personal_matches_canon():
    """N-19：個人の側に正典の制約とインデックスを当てる。2 回当てても失敗しない。制約の一覧が JSON と一致し、ベクトル・全文が 0 件。"""
    from nest import canon, connections, schema_apply
    c = canon.load(Path(__file__).resolve().parents[1] / "docs" / "SCHEMA.md")
    with connections.driver("personal") as d:
        schema_apply.apply(d, c)
        schema_apply.apply(d, c)
        cons = _read(d, "SHOW CONSTRAINTS YIELD name RETURN collect(name) AS names")[0]["names"]
        assert sorted(cons) == sorted(schema_apply.expected_constraint_names(c))
        idx = _read(d, "SHOW INDEXES YIELD name, type RETURN name, type")
        assert not [r for r in idx if r["type"] in ("VECTOR", "FULLTEXT", "TEXT")]
        assert set(schema_apply.expected_index_names(c)) <= {r["name"] for r in idx}
