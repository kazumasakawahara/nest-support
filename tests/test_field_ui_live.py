"""N-37：field-ui が起動した個人の側（127.0.0.1:37687）を、包みで読み、ゲートを通して支援記録を書くこと。
NEST_LIVE_DB=1 のときだけ。

    NEST_LIVE_DB=1 uv run pytest -q tests/test_field_ui_live.py

架空の本人を一人ゲートで作り、職員ごとのトークンの表（試験の一時の場所）で field-ui にログインして、
本人の一覧（ID と仮名だけ）と支援記録の登録（ABOUT・AUTHORED_BY・監査の記録）を確かめる。
包みは NEXT-02 の歯止めがそろわないと読まないので、試験の間だけ架空の印（NestLiveProbe）を置き、終わったら外す（G-51）。
"""
import importlib.util
import json
import os
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")
pytest.importorskip("fastapi")

REPO = Path(__file__).resolve().parents[1]
TOKEN = "fictional-live-token-" + uuid.uuid4().hex  # 試験ごとの架空のトークン


def _q(d, query, **params):
    records, _, _ = d.execute_query(query, params, database_="neo4j")
    return [r.data() for r in records]


def _load():
    spec = importlib.util.spec_from_file_location("field_ui_server_live", REPO / "field-ui" / "server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_field_ui_reads_through_the_wrapper_and_writes_through_the_gate(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from nest import auth, connections
    from nest.gate import write as gw
    probe = "fui-" + uuid.uuid4().hex
    with connections.driver("personal") as d:
        admin = _q(d, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")
        if not admin:
            pytest.skip("Administrator がいない（ほかの DB つきの試験を先に流す）")
        staff = admin[0]["id"]
        d.execute_query("CREATE (:NestLiveProbe {probe: $probe, _fictional: true})", {"probe": probe}, database_="neo4j")
        _cleanup().clear_fictional_clients(d)  # 流す前に試験の DB の架空の本人を片づける
        out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": staff,
                         "nodes": [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空"}}],
                         "relationships": []}, d)
        assert out["ok"], out["errors"]
        client_id = out["ids"]["c"]
    table = tmp_path / "field-ui-staff.json"
    table.write_text(json.dumps({"version": 1, "staff": {staff: auth.token_hash(TOKEN)}}), encoding="utf-8")
    os.chmod(table, 0o600)
    monkeypatch.setattr(auth, "staff_tokens_path", lambda: table)
    try:
        c = TestClient(_load().app)
        h = {"Authorization": "Bearer " + TOKEN}
        clients = c.get("/api/clients", headers=h).json()["clients"]
        mine = [x for x in clients if x["clientId"] == client_id]
        assert len(mine) == 1 and set(mine[0]) == {"clientId", "displayCode"}
        r = c.post("/api/support-log", headers=h, json={
            "clientId": client_id, "date": "2026-07-01", "situation": "（架空）食事", "effectiveness": "Effective"})
        assert r.status_code == 200, r.text
        log_id = r.json()["supportLogId"]
        bad = c.post("/api/support-log", headers=h, json={
            "clientId": client_id, "date": "2026-07-01", "situation": "（架空）", "effectiveness": "とても良い"})
        assert bad.status_code == 422  # 列挙に無い値はゲートが止める
    finally:
        with connections.driver("personal") as d:
            d.execute_query("MATCH (n:NestLiveProbe {probe: $probe}) DELETE n", {"probe": probe}, database_="neo4j")
    with connections.driver("personal") as d:
        row = _q(d, """MATCH (l:SupportLog {supportLogId: $id})-[:ABOUT]->(c:Client {clientId: $c})
                       MATCH (l)-[:AUTHORED_BY]->(s:Staff {staffId: $s})
                       OPTIONAL MATCH (a:AuditLog)-[:AUDIT_FOR]->(l)
                       WITH l, a ORDER BY a.targetLabel
                       RETURN l.origin AS origin, l.status AS status, toString(l.date) AS date,
                              collect(a.action + ' ' + a.targetLabel) AS audits""",
                 id=log_id, c=client_id, s=staff)
    # ゲートは、ノードと関係の一つずつに作成の監査の記録を残す
    assert row == [{"origin": "Human", "status": "Active", "date": "2026-07-01",
                    "audits": ["Create ABOUT", "Create AUTHORED_BY", "Create SupportLog"]}]


def _cleanup():
    spec = importlib.util.spec_from_file_location("live_cleanup", Path(__file__).with_name("live_cleanup.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_client_list_is_newest_first_and_marked_when_cut(tmp_path, monkeypatch):
    """合流前の直し（2026-11-06 河原さん）：上限（試験では 3 行）より多い架空の本人を入れると、
    新しい順に上限まで返し、truncated と件数が付く。流す前に試験の DB の架空の本人を片づける"""
    from fastapi.testclient import TestClient
    from nest import auth, connections, mcp_guard
    from nest.gate import write as gw
    probe = "fui-cut-" + uuid.uuid4().hex
    with connections.driver("personal") as d:
        admin = _q(d, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")
        if not admin:
            pytest.skip("Administrator がいない（ほかの DB つきの試験を先に流す）")
        staff = admin[0]["id"]
        d.execute_query("CREATE (:NestLiveProbe {probe: $probe, _fictional: true})", {"probe": probe}, database_="neo4j")
        try:
            _cleanup().clear_fictional_clients(d)
            made = []
            for _ in range(4):
                out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": staff,
                                 "nodes": [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空"}}],
                                 "relationships": []}, d)
                assert out["ok"], out["errors"]
                made.append(out["ids"]["c"])
        finally:
            d.execute_query("MATCH (n:NestLiveProbe {probe: $probe}) DELETE n", {"probe": probe}, database_="neo4j")
    table = tmp_path / "field-ui-staff.json"
    table.write_text(json.dumps({"version": 1, "staff": {staff: auth.token_hash(TOKEN)}}), encoding="utf-8")
    os.chmod(table, 0o600)
    monkeypatch.setattr(auth, "staff_tokens_path", lambda: table)
    monkeypatch.setattr(mcp_guard, "MAX_ROWS", 3)
    body = TestClient(_load().app).get("/api/clients", headers={"Authorization": "Bearer " + TOKEN}).json()
    assert body["truncated"] is True and body["total"] == 4
    assert [c["clientId"] for c in body["clients"]] == list(reversed(made))[:3]
