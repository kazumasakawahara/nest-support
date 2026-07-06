"""
P0-2: FastAPI サービス（field-ui / sos）の認証層の回帰テスト。

- 保護エンドポイント（/api/*）はトークンなしで 401、APP_ACCESS_TOKEN 未設定で 503。
- SOS 送信（POST /api/sos）は非対称設計により無認証で成功する。
- SOS の情報取得（GET /api/client/*）は認証必須。
- ログインは HttpOnly セッション Cookie を発行する。
"""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import lib.auth as auth

_ROOT = Path(__file__).resolve().parent.parent
TOKEN = "test-secret-token"


def _load_field_ui():
    spec = importlib.util.spec_from_file_location(
        "field_ui_server", _ROOT / "field-ui" / "server.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# lib/auth 単体
# ---------------------------------------------------------------------------

def test_verify_token(monkeypatch):
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    assert auth.verify_token(TOKEN) is True
    assert auth.verify_token("wrong") is False


def test_verify_token_unset(monkeypatch):
    monkeypatch.delenv("APP_ACCESS_TOKEN", raising=False)
    assert auth.verify_token(TOKEN) is False


# ---------------------------------------------------------------------------
# field-ui
# ---------------------------------------------------------------------------

def test_field_ui_requires_auth(monkeypatch):
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    mod = _load_field_ui()
    monkeypatch.setattr(mod, "run_query", lambda q, p=None: [{"name": "山田太郎"}])
    client = TestClient(mod.app)

    # トークンなし → 401
    assert client.get("/api/clients").status_code == 401
    # 正規トークン → 200
    ok = client.get("/api/clients", headers={"Authorization": f"Bearer {TOKEN}"})
    assert ok.status_code == 200


def test_field_ui_fail_closed_when_unset(monkeypatch):
    monkeypatch.delenv("APP_ACCESS_TOKEN", raising=False)
    mod = _load_field_ui()
    client = TestClient(mod.app)
    # APP_ACCESS_TOKEN 未設定 → 503（fail-closed）
    assert client.get("/api/clients").status_code == 503


def test_field_ui_login_sets_cookie(monkeypatch):
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    import importlib
    importlib.reload(auth)  # SESSION_COOKIE_SECURE を反映
    mod = _load_field_ui()
    client = TestClient(mod.app)

    bad = client.post("/api/login", json={"token": "wrong"})
    assert bad.status_code == 401

    good = client.post("/api/login", json={"token": TOKEN})
    assert good.status_code == 200
    assert auth.SESSION_COOKIE in good.cookies
    importlib.reload(auth)  # 後続テストへ影響しないよう戻す


# ---------------------------------------------------------------------------
# sos（非対称設計）
# ---------------------------------------------------------------------------

@pytest.fixture
def sos_mod(monkeypatch):
    import sos.api_server as sos

    async def _fake_send(message):
        return True
    monkeypatch.setattr(sos, "send_line_message", _fake_send)
    return sos


def test_sos_send_is_unauthenticated(sos_mod, monkeypatch):
    """SOS 送信は APP_ACCESS_TOKEN 設定下でも無認証で成功する（非対称設計）。"""
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    monkeypatch.setattr(sos_mod, "get_client_info", lambda cid: None)
    client = TestClient(sos_mod.app)
    resp = client.post("/api/sos", json={"client_id": "誰か"})
    assert resp.status_code == 200


def test_sos_client_lookup_requires_auth(sos_mod, monkeypatch):
    """情報取得（GET /api/client/*）は認証必須。"""
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    monkeypatch.setattr(sos_mod, "get_client_info", lambda cid: {"name": "山田太郎"})
    client = TestClient(sos_mod.app)

    assert client.get("/api/client/山田太郎").status_code == 401
    ok = client.get("/api/client/山田太郎", headers={"Authorization": f"Bearer {TOKEN}"})
    assert ok.status_code == 200
