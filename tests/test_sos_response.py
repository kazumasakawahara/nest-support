"""
SOS の応答に個人の情報を混ぜないこと、登録の有無が分からないこと（P0-3 の回帰）。

E-3（2026-11-06 河原さん）：前の DB から実名・キーパーソン・禁忌を引く関数（get_client_info・get_client_cautions）と、
実名を返す GET /api/client/{id} の入口を外した。入口は 503 を返す（sos の置き換えで作り直す）。台帳 G-66。
"""

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import sos.api_server as sos

TOKEN = "fictional-token-for-tests-only"  # 架空


@pytest.fixture
def client(monkeypatch):
    async def _fake_send(message):
        return True
    monkeypatch.setattr(sos, "send_line_message", _fake_send)
    return TestClient(sos.app)


def test_old_lookup_functions_are_gone():
    for name in ("get_client_info", "get_client_cautions", "resolve_client_raw", "get_display_name", "run_query"):
        assert not hasattr(sos, name), name


def test_sos_response_has_no_message_or_name(client):
    resp = client.post("/api/sos", json={"client_id": "C-ZZZZZZ"})
    assert resp.status_code == 200
    body = resp.json()
    for key in ("sent_message", "mock_mode", "client_name"):
        assert key not in body
    assert body.get("received_id") == "C-ZZZZZZ"


def test_sos_does_not_leak_registration_status(client):
    a = client.post("/api/sos", json={"client_id": "C-ZZZZZZ"}).json()
    b = client.post("/api/sos", json={"client_id": "C-YYYYYY"}).json()
    assert a["message"] == b["message"] and set(a) == set(b)


def test_client_lookup_returns_503_and_no_name(client, monkeypatch):
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    resp = client.get("/api/client/C-ZZZZZZ", headers={"Authorization": "Bearer " + TOKEN})
    assert resp.status_code == 503
    assert "置き換え" in resp.json()["detail"]
    assert "name" not in resp.json()
