"""関わりを資源の側の機関に結ぶ一往復を、起動した二つの DB で流す（2026-11-11 河原さん）。NEST_LIVE_DB=1 のときだけ。

- 候補はその場で引いて選ぶ。選んだ実在の事業所の名前と機関 ID は、試験に書かない・出力に出さない
- submit_proposal（_submit）の返り値に候補（所在地の市区・サービスの種類つき）が出る → link_organization（_link）で結ぶ
- 関わりは未確定のまま。HAS_INVOLVEMENT と、その AuditLog が残る。二度目・候補に無い機関は止まる
- 資源の側には書かない（機関の件数が前後で同じ）
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

NAME = "つばさ"


def _q(d, query, **params):
    records, _, _ = d.execute_query(query, params, database_="neo4j")
    return [r.data() for r in records]


@pytest.fixture
def drivers():
    from nest import connections
    with connections.driver("personal") as p, connections.driver("resource") as r:
        yield p, r


@pytest.fixture
def setup(drivers, monkeypatch):
    from nest.gate import write as gw
    personal, _ = drivers
    admin = _q(personal, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")[0]["id"]
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                     "nodes": [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空"}}],
                     "relationships": []}, personal)
    assert out["ok"], out["errors"]
    monkeypatch.setenv("NEST_GATE_STAFF_ID", admin)
    code = _q(personal, "MATCH (c:Client {clientId: $id}) RETURN c.displayCode AS code", id=out["ids"]["c"])[0]["code"]
    phone = "本人が週一回通っている「%s」の生活支援員に電話した %s。" % (NAME, uuid.uuid4().hex[:6])
    proposal = {"documentKind": "OwnCaseRecord",
                "facts": [{"quote": phone, "recordKind": "Interview", "certainty": "Unspecified", "informantKind": "Agency"}],
                "involvements": [{"quote": phone, "kind": "ServiceProvision", "orgName": NAME, "serviceTypeName": "生活介護"}]}
    return {"code": code, "original": "架空の面接記録\n2026-11-05 電話\n%s\n" % phone, "proposal": proposal}


def test_the_round_trip_links_the_chosen_org_and_keeps_the_involvement_pending(drivers, setup):
    from nest import mcp_gate
    personal, resource = drivers
    orgs_before = _q(resource, "MATCH (o:Organization) RETURN count(o) AS n")[0]["n"]
    sub = mcp_gate._submit(personal, setup["code"], setup["original"], setup["proposal"], resource_driver=resource)
    assert sub["ok"], sub["errors"]
    (choice,) = sub["orgChoices"]
    assert choice["orgName"] == NAME and choice["candidates"], "候補が出ない（資源の側の一式を確かめる）"
    assert all({"areas", "serviceTypes", "kind", "name", "orgId"} <= set(c) for c in choice["candidates"])
    inv = choice["involvementId"]
    assert _q(personal, "MATCH (i:Involvement {involvementId: $id}) RETURN i.serviceTypeName AS s, i.status AS st", id=inv) == \
        [{"s": "生活介護", "st": "Pending"}]

    chosen = choice["candidates"][0]["orgId"]  # 人が番号で選んだことに当たる。名前も ID も出さない
    linked = mcp_gate._link(personal, resource, setup["code"], inv, NAME, chosen)
    assert linked["ok"], linked["errors"]
    rows = _q(personal, "MATCH (o:Organization)-[:HAS_INVOLVEMENT]->(i:Involvement {involvementId: $id}) "
                        "RETURN o.orgId = $org AS same, i.status AS st", id=inv, org=chosen)
    assert rows == [{"same": True, "st": "Pending"}]
    assert _q(personal, "MATCH (a:AuditLog {targetLabel: 'HAS_INVOLVEMENT', targetId: $org})-[:ACTED_BY]->(:Staff) "
                        "RETURN count(a) > 0 AS ok", org=chosen) == [{"ok": True}]

    again = mcp_gate._link(personal, resource, setup["code"], inv, NAME, chosen)
    assert not again["ok"] and any("すでに機関" in e for e in again["errors"])
    assert _q(resource, "MATCH (o:Organization) RETURN count(o) AS n")[0]["n"] == orgs_before  # 資源の側は変わらない


def test_an_org_outside_the_candidates_stops_and_writes_nothing(drivers, setup):
    from nest import mcp_gate
    personal, resource = drivers
    sub = mcp_gate._submit(personal, setup["code"], setup["original"], setup["proposal"], resource_driver=resource)
    assert sub["ok"], sub["errors"]
    inv = sub["orgChoices"][0]["involvementId"]
    listed = {c["orgId"] for c in sub["orgChoices"][0]["candidates"]}
    other = next(r["id"] for r in _q(resource, "MATCH (o:Organization) RETURN o.orgId AS id ORDER BY id LIMIT 50")
                 if r["id"] not in listed)
    out = mcp_gate._link(personal, resource, setup["code"], inv, NAME, other)
    assert not out["ok"] and any("候補に無い" in e for e in out["errors"])
    assert _q(personal, "MATCH (o:Organization)-[:HAS_INVOLVEMENT]->(:Involvement {involvementId: $id}) RETURN count(o) AS n",
              id=inv) == [{"n": 0}]
