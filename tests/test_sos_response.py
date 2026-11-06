"""
SOS の応答に個人の情報を混ぜないこと、登録の有無が分からないこと（P0-3 の回帰）。

E-3（2026-11-06 河原さん）：前の DB から実名・キーパーソン・禁忌を引く関数（get_client_info・get_client_cautions）と、
実名を返す GET /api/client/{id} の入口を外した（台帳 G-66）。
N-36（2026-11-06）：入口を作り直した。仮名（displayCode）だけで受け、読み取りの包み（nest.mcp_guard）を通して
個人の側を読み、仮名と「いるか」だけを返す。名前は返さない。sos は DB に直につながない。
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


REPO = __import__("pathlib").Path(__file__).resolve().parents[1]


@pytest.fixture
def authed(client, monkeypatch):
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    calls = []

    def _lookup(code):
        calls.append(code)
        return code == "C-ZZZZZZ"
    monkeypatch.setattr(sos, "lookup_client", _lookup)
    return client, calls, {"Authorization": "Bearer " + TOKEN}


def test_client_lookup_returns_the_code_and_no_name(authed):
    client, calls, h = authed
    resp = client.get("/api/client/C-ZZZZZZ", headers=h)
    assert resp.status_code == 200
    assert resp.json() == {"displayCode": "C-ZZZZZZ", "found": True}
    assert client.get("/api/client/C-YYYYYY", headers=h).json() == {"displayCode": "C-YYYYYY", "found": False}
    assert calls == ["C-ZZZZZZ", "C-YYYYYY"]


@pytest.mark.parametrize("ident", ["山田太郎", "c-zzzzzz", "C-ZZZZZ", "C-ZZZZZZ1", "CL-0001"])
def test_client_lookup_takes_only_a_display_code(authed, ident):
    client, calls, h = authed
    resp = client.get("/api/client/" + ident, headers=h)
    assert resp.status_code == 400
    assert calls == []  # 仮名の形でなければ DB を読まない


def test_client_lookup_is_503_when_the_wrapper_refuses(client, monkeypatch):
    from nest import mcp_guard
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)

    def _refuse(code):
        raise mcp_guard.NotReadOnly("NEXT-02 の歯止めがそろっていない（架空）")
    monkeypatch.setattr(sos, "lookup_client", _refuse)
    resp = client.get("/api/client/C-ZZZZZZ", headers={"Authorization": "Bearer " + TOKEN})
    assert resp.status_code == 503
    assert "name" not in resp.json()


def test_lookup_reads_through_the_wrapper(monkeypatch):
    """lookup_client は個人の側を、読み取りの包み（require_personal_allowed・run_read の personal=True）で読む"""
    import contextlib
    from nest import connections, mcp_guard
    seen = {}

    @contextlib.contextmanager
    def _driver(side):
        seen["side"] = side
        yield "fake-driver"
    monkeypatch.setattr(connections, "driver", _driver)
    monkeypatch.setattr(mcp_guard, "require_personal_allowed", lambda d: seen.setdefault("allowed", d))

    def _run_read(d, query, params, personal):
        seen.update(query=query, params=params, personal=personal)
        return [{"n": 1}]
    monkeypatch.setattr(mcp_guard, "run_read", _run_read)
    assert sos.lookup_client("C-ZZZZZZ") is True
    assert seen["side"] == "personal" and seen["allowed"] == "fake-driver" and seen["personal"] is True
    assert seen["params"] == {"code": "C-ZZZZZZ"} and "$code" in seen["query"]


def test_sos_does_not_connect_to_a_db_directly():
    text = (REPO / "sos" / "api_server.py").read_text(encoding="utf-8")
    for word in ("GraphDatabase", "NEO4J_PASSWORD", "NEO4J_URI", "lib."):
        assert word not in text, word


def test_the_app_shows_no_name_and_takes_only_id():
    html = (REPO / "sos" / "app" / "index.html").read_text(encoding="utf-8")
    assert "data.name" not in html
    assert "params.get('name')" not in html
