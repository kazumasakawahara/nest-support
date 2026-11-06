"""
P0-2: FastAPI サービス（field-ui / sos）の認証層の回帰テスト。

- 保護エンドポイント（/api/*）はトークンなしで 401、APP_ACCESS_TOKEN 未設定で 503（sos。field-ui は職員ごとのトークン。N-37）。
- SOS 送信（POST /api/sos）は非対称設計により無認証で成功する。
- SOS の情報取得（GET /api/client/*）は認証必須。
- ログインは HttpOnly セッション Cookie を発行する。
"""

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import nest.auth as auth

_ROOT = Path(__file__).resolve().parent.parent
TOKEN = "test-secret-token"


# ---------------------------------------------------------------------------
# nest/auth 単体（計画 N-35 で lib/auth.py から移した）
# ---------------------------------------------------------------------------

def test_verify_token(monkeypatch):
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    assert auth.verify_token(TOKEN) is True
    assert auth.verify_token("wrong") is False


def test_verify_token_unset(monkeypatch):
    monkeypatch.delenv("APP_ACCESS_TOKEN", raising=False)
    assert auth.verify_token(TOKEN) is False


class _FakeReq:
    def __init__(self, headers, cookies=None):
        self.headers = headers  # 小文字キー（Starlette は case-insensitive）
        self.cookies = cookies or {}


def test_proxy_header_not_trusted_by_default(monkeypatch):
    """R2-6: 既定では X-Authenticated-User を採用しない（監査なりすまし防止）。"""
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
    req = _FakeReq(headers={
        "authorization": f"Bearer {TOKEN}",
        "x-authenticated-user": "admin_spoof",
    })
    assert auth.require_auth(req) == "authenticated"


def test_proxy_header_trusted_when_enabled(monkeypatch):
    """TRUST_PROXY_HEADERS=true のときのみヘッダを採用する。"""
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    req = _FakeReq(headers={
        "authorization": f"Bearer {TOKEN}",
        "x-authenticated-user": "proxied_user",
    })
    assert auth.require_auth(req) == "proxied_user"


# ---------------------------------------------------------------------------
# field-ui は職員ごとのトークンに替えた（N-37）。試験は tests/test_field_ui_guards.py と tests/test_staff_auth.py
# ---------------------------------------------------------------------------


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
    client = TestClient(sos_mod.app)
    resp = client.post("/api/sos", json={"client_id": "誰か"})
    assert resp.status_code == 200


def test_sos_client_lookup_requires_auth(sos_mod, monkeypatch):
    """情報取得（GET /api/client/*）は認証必須。認証すれば仮名と「いるか」だけを返す（N-36。名前は返さない）。"""
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    monkeypatch.setattr(sos_mod, "lookup_client", lambda code: True)
    client = TestClient(sos_mod.app)

    assert client.get("/api/client/C-ZZZZZZ").status_code == 401
    ok = client.get("/api/client/C-ZZZZZZ", headers={"Authorization": f"Bearer {TOKEN}"})
    assert ok.status_code == 200 and ok.json() == {"displayCode": "C-ZZZZZZ", "found": True}


def test_auth_lives_in_nest_and_services_use_it():
    """N-35：認証の部品は nest/auth.py だけにあり、sos・field-ui はそこから読む"""
    assert not (_ROOT / "lib" / "auth.py").exists()
    for service, line in (("sos/api_server.py", "from nest.auth import require_auth, set_session_cookie, verify_token"),
                          ("field-ui/server.py", "from nest.auth import require_staff, set_session_cookie, staff_of")):
        text = (_ROOT / service).read_text(encoding="utf-8")
        assert line in text
        assert "lib.auth" not in text
