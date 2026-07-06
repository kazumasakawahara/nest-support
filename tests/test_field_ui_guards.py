"""
field-ui の入力ガード回帰テスト。

P1-13: 音声アップロードのサイズ/形式制限。
P1-14: 存在しないクライアント名での記録がゴースト Client を作らない（存在チェック）。
"""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parent.parent
TOKEN = "test-secret-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _load_field_ui():
    spec = importlib.util.spec_from_file_location(
        "field_ui_server_guards", _ROOT / "field-ui" / "server.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def app_mod(monkeypatch):
    monkeypatch.setenv("APP_ACCESS_TOKEN", TOKEN)
    mod = _load_field_ui()
    return mod


def _set_clients(monkeypatch, mod, existing):
    """run_query を差し替え、指定名の Client のみ存在する状態にする。"""
    def fake(query, params=None):
        params = params or {}
        if "count(c)" in query:
            return [{"n": 1 if params.get("name") in existing else 0}]
        return []
    monkeypatch.setattr(mod, "run_query", fake)


def test_support_log_rejects_unknown_client(app_mod, monkeypatch):
    """P1-14: 未登録クライアント名の記録は 404 で拒否し、登録処理へ進まない。"""
    _set_clients(monkeypatch, app_mod, existing={"山田太郎"})
    called = {"register": False}
    monkeypatch.setattr(app_mod, "register_to_database",
                        lambda *a, **k: called.__setitem__("register", True) or {"status": "success"})
    client = TestClient(app_mod.app)

    payload = {
        "clientName": "存在しない花子", "supporterName": "職員A", "date": "2026-07-01",
        "situation": "x", "action": "y", "effectiveness": "High", "emotion": "Calm",
    }
    r = client.post("/api/support-log", json=payload, headers=AUTH)
    assert r.status_code == 404
    assert called["register"] is False, "未登録クライアントなのに登録処理が走った"


def test_support_log_accepts_known_client(app_mod, monkeypatch):
    """既存クライアントなら通常どおり登録される。"""
    _set_clients(monkeypatch, app_mod, existing={"山田太郎"})
    monkeypatch.setattr(app_mod, "register_to_database",
                        lambda *a, **k: {"status": "success", "count": 3})
    client = TestClient(app_mod.app)

    payload = {
        "clientName": "山田太郎", "supporterName": "職員A", "date": "2026-07-01",
        "situation": "x", "action": "y", "effectiveness": "High", "emotion": "Calm",
    }
    r = client.post("/api/support-log", json=payload, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["status"] == "success"


def test_voice_upload_rejects_oversized(app_mod, monkeypatch):
    """P1-13: 上限超過の音声は 413 で拒否する。"""
    _set_clients(monkeypatch, app_mod, existing={"山田太郎"})
    monkeypatch.setattr(app_mod, "MAX_AUDIO_BYTES", 1024)  # 1KB に絞る
    client = TestClient(app_mod.app)

    big = b"x" * 4096
    r = client.post(
        "/api/voice/upload",
        data={"clientName": "山田太郎", "supporterName": "職員A"},
        files={"audio": ("rec.webm", big, "audio/webm")},
        headers=AUTH,
    )
    assert r.status_code == 413


def test_voice_upload_rejects_bad_format(app_mod, monkeypatch):
    """P1-13: 想定外の形式（拡張子も content-type も音声でない）は 415。"""
    _set_clients(monkeypatch, app_mod, existing={"山田太郎"})
    client = TestClient(app_mod.app)

    r = client.post(
        "/api/voice/upload",
        data={"clientName": "山田太郎", "supporterName": "職員A"},
        files={"audio": ("evil.exe", b"MZ...", "application/octet-stream")},
        headers=AUTH,
    )
    assert r.status_code == 415


def test_voice_upload_rejects_unknown_client(app_mod, monkeypatch):
    """P1-14: 音声登録でも未登録クライアントは 404（文字起こし前に弾く）。"""
    _set_clients(monkeypatch, app_mod, existing={"山田太郎"})
    client = TestClient(app_mod.app)
    r = client.post(
        "/api/voice/upload",
        data={"clientName": "誰でもない", "supporterName": "職員A"},
        files={"audio": ("rec.webm", b"x" * 10, "audio/webm")},
        headers=AUTH,
    )
    assert r.status_code == 404
