"""field-ui の作り直し（計画 N-37。2026-11-06 河原さん：職員ごとのトークン・ダッシュボードは今回は閉じる）。DB を使わない。

- 認証は職員ごとのトークン（nest.auth.require_staff）。ゲートに渡す職員 ID はトークンから決める（自己申告にしない）
- 読むのは読み取りの包み（read_personal：require_personal_allowed・run_read の personal=True）。本人は ID と仮名だけ。名前を返さない
- 支援記録はゲート（nest.gate.write.submit）に依頼として渡す。人が入れた記録なので origin は Human。DB に直に書かない
- 支援記録の項目は正典の SupportLog の項目だけ（日付・場面・対応・効果・メモ・次の対応）。感情・きっかけの欄は無い
- ダッシュボードの API は閉じる（503）。推移は insight-agent スキルで見る
- 音声の大きさ・形式の点検（P1-13）と、いない本人を弾くこと（P1-14）は前のまま
- 文字起こしができた音声は nest_voice_data/ に「文字起こしの sha256 ＋ 拡張子」で置き、文字起こしの全文と documentHash を返す。  できなければ音声を残さない（消す道具は nest/voice.py）
DB つきの確かめは tests/test_field_ui_live.py。
"""
import contextlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import nest.auth as auth

_ROOT = Path(__file__).resolve().parent.parent
TOKEN = "fictional-staff-token"  # 架空
STAFF = "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"
CLIENT = "CLI-01AAAAAAAAAAAAAAAAAAAAAAAA"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _load_field_ui():
    spec = importlib.util.spec_from_file_location("field_ui_server_guards", _ROOT / "field-ui" / "server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _staff_table(monkeypatch, tmp_path):
    p = tmp_path / "field-ui-staff.json"
    p.write_text(json.dumps({"version": 1, "staff": {STAFF: auth.token_hash(TOKEN)}}), encoding="utf-8")
    os.chmod(p, 0o600)
    monkeypatch.setattr(auth, "staff_tokens_path", lambda: p)
    return p


def _set_clients(monkeypatch, mod, existing):
    """read_personal を差し替え、指定の本人 ID だけがいる状態にする。読んだ問い合わせを返す。"""
    seen = []

    def fake(query, params=None):
        seen.append((query, params or {}))
        if "count(c)" in query:
            return [{"n": 1 if (params or {}).get("id") in existing else 0}]
        return [{"clientId": cid, "displayCode": "C-ZZZZZZ"} for cid in sorted(existing)]
    monkeypatch.setattr(mod, "read_personal", fake)
    return seen


def _voice_root(monkeypatch, mod, tmp_path):
    """音声の置き場所を一時の場所にし、tmutil を呼ばないようにする。"""
    from nest import voice
    root = tmp_path / "nest_voice_data"
    monkeypatch.setattr(mod, "VOICE_ROOT", root)
    monkeypatch.setattr(voice, "run", lambda args: (0, ""))
    return root


@pytest.fixture
def app_mod(monkeypatch, tmp_path):
    _staff_table(monkeypatch, tmp_path)
    return _load_field_ui()


@pytest.fixture
def gate(monkeypatch, app_mod):
    sent = []

    def fake_submit(req):
        sent.append(req)
        return {"ok": True, "errors": [], "ids": {"log": "SLG-01AAAAAAAAAAAAAAAAAAAAAAAA"}}
    monkeypatch.setattr(app_mod, "submit_to_gate", fake_submit)
    return sent


LOG = {"clientId": CLIENT, "date": "2026-07-01", "situation": "食事", "action": "（架空）別室に移った",
       "effectiveness": "Effective"}


# --- 認証 ---

def test_requires_a_staff_token(app_mod, monkeypatch):
    _set_clients(monkeypatch, app_mod, {CLIENT})
    c = TestClient(app_mod.app)
    assert c.get("/api/clients").status_code == 401
    assert c.get("/api/clients", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert c.get("/api/clients", headers=AUTH).status_code == 200


def test_no_staff_table_is_503(monkeypatch, tmp_path):
    monkeypatch.setattr(auth, "staff_tokens_path", lambda: tmp_path / "none.json")
    mod = _load_field_ui()
    assert TestClient(mod.app).get("/api/clients", headers=AUTH).status_code == 503


def test_login_takes_a_staff_token(app_mod, monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    c = TestClient(app_mod.app)
    assert c.post("/api/login", json={"token": "wrong"}).status_code == 401
    good = c.post("/api/login", json={"token": TOKEN})
    assert good.status_code == 200 and auth.SESSION_COOKIE in good.cookies


# --- 読み取り ---

def test_clients_are_ids_and_codes_without_names(app_mod, monkeypatch):
    seen = _set_clients(monkeypatch, app_mod, {CLIENT})
    r = TestClient(app_mod.app).get("/api/clients", headers=AUTH)
    assert r.json() == [{"clientId": CLIENT, "displayCode": "C-ZZZZZZ"}]
    query = seen[0][0]
    assert "Name" not in query and "name" not in query


def test_read_personal_goes_through_the_wrapper(app_mod, monkeypatch):
    from nest import connections, mcp_guard
    seen = {}

    @contextlib.contextmanager
    def _driver(side):
        seen["side"] = side
        yield "fake-driver"
    monkeypatch.setattr(connections, "driver", _driver)
    monkeypatch.setattr(mcp_guard, "require_personal_allowed", lambda d, caller="mcp": seen.update(caller=caller) or seen.setdefault("allowed", d))
    monkeypatch.setattr(mcp_guard, "run_read", lambda d, q, p, personal: seen.update(personal=personal) or [{"n": 1}])
    assert app_mod.read_personal("MATCH (c:Client) RETURN count(c) AS n") == [{"n": 1}]
    assert seen == {"side": "personal", "allowed": "fake-driver", "caller": "screen", "personal": True}


def test_field_ui_does_not_use_the_old_db_code():
    text = (_ROOT / "field-ui" / "server.py").read_text(encoding="utf-8")
    for word in ("lib.db_operations", "run_query", "register_to_database", "insight_engine", "GraphDatabase"):
        assert word not in text, word


# --- 支援記録（ゲートを通す） ---

def test_support_log_goes_to_the_gate_as_a_human_record(app_mod, monkeypatch, gate):
    _set_clients(monkeypatch, app_mod, {CLIENT})
    r = TestClient(app_mod.app).post("/api/support-log", json=dict(LOG, note="", nextAction=None), headers=AUTH)
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "supportLogId": "SLG-01AAAAAAAAAAAAAAAAAAAAAAAA"}
    (req,) = gate
    assert req["actorStaffId"] == STAFF and req["requestId"].startswith("field-ui-")
    assert req["nodes"] == [{"ref": "log", "label": "SupportLog", "origin": "Human",
                             "properties": {"date": "2026-07-01", "situation": "食事", "action": "（架空）別室に移った",
                                            "effectiveness": "Effective"}}]  # 空の欄は送らない
    assert req["relationships"] == [
        {"type": "ABOUT", "from": "log", "to": {"label": "Client", "id": CLIENT}, "properties": {}},
        {"type": "AUTHORED_BY", "from": "log", "to": {"label": "Staff", "id": STAFF}, "properties": {}}]


def test_support_log_refuses_fields_outside_the_canon(app_mod, monkeypatch, gate):
    _set_clients(monkeypatch, app_mod, {CLIENT})
    for extra in ({"emotion": "Calm"}, {"triggerTag": "大きな音"}, {"supporterName": "架空"}, {"clientName": "架空"}):
        r = TestClient(app_mod.app).post("/api/support-log", json=dict(LOG, **extra), headers=AUTH)
        assert r.status_code == 422, extra
    assert gate == []


def test_support_log_rejects_unknown_client(app_mod, monkeypatch, gate):
    """P1-14：いない本人の記録は 404 で、ゲートに渡さない。"""
    _set_clients(monkeypatch, app_mod, {CLIENT})
    r = TestClient(app_mod.app).post("/api/support-log", json=dict(LOG, clientId="CLI-01BBBBBBBBBBBBBBBBBBBBBBBB"),
                                     headers=AUTH)
    assert r.status_code == 404 and gate == []


def test_support_log_shows_gate_errors(app_mod, monkeypatch):
    _set_clients(monkeypatch, app_mod, {CLIENT})
    monkeypatch.setattr(app_mod, "submit_to_gate", lambda req: {"ok": False, "errors": ["（架空）止めた理由"], "ids": {}})
    r = TestClient(app_mod.app).post("/api/support-log", json=LOG, headers=AUTH)
    assert r.status_code == 422 and r.json()["detail"] == ["（架空）止めた理由"]


def test_support_log_is_503_when_the_db_cannot_be_read(app_mod, monkeypatch, gate):
    def _down(query, params=None):
        raise RuntimeError("（架空）つながらない")
    monkeypatch.setattr(app_mod, "read_personal", _down)
    r = TestClient(app_mod.app).post("/api/support-log", json=LOG, headers=AUTH)
    assert r.status_code == 503 and gate == []


# --- ダッシュボードは閉じる ---

@pytest.mark.parametrize("path", ["/api/dashboard/summary", "/api/dashboard/alerts/" + CLIENT,
                                  "/api/dashboard/recent-logs/" + CLIENT])
def test_dashboard_api_is_closed(app_mod, path):
    r = TestClient(app_mod.app).get(path, headers=AUTH)
    assert r.status_code == 503 and "insight-agent" in r.json()["detail"]


# --- 画面 ---

def test_the_record_form_has_only_canon_fields():
    html = (_ROOT / "field-ui" / "static" / "record-form.html").read_text(encoding="utf-8")
    for gone in ("emotion", "triggerTag", "supporterName", "clientName", "この画面は使わないでください"):
        assert gone not in html, gone
    for field in ("clientId", "situation", "action", "effectiveness", "note", "nextAction"):
        assert 'id="%s"' % field in html, field


# --- 音声（P1-13・P1-14） ---

def test_voice_upload_rejects_oversized(app_mod, monkeypatch):
    _set_clients(monkeypatch, app_mod, {CLIENT})
    monkeypatch.setattr(app_mod, "MAX_AUDIO_BYTES", 1024)
    r = TestClient(app_mod.app).post("/api/voice/upload", data={"clientId": CLIENT},
                                     files={"audio": ("rec.webm", b"x" * 4096, "audio/webm")}, headers=AUTH)
    assert r.status_code == 413


def test_voice_upload_rejects_bad_format(app_mod, monkeypatch):
    _set_clients(monkeypatch, app_mod, {CLIENT})
    r = TestClient(app_mod.app).post("/api/voice/upload", data={"clientId": CLIENT},
                                     files={"audio": ("evil.exe", b"MZ...", "application/octet-stream")}, headers=AUTH)
    assert r.status_code == 415


def test_voice_upload_rejects_unknown_client(app_mod, monkeypatch):
    _set_clients(monkeypatch, app_mod, {CLIENT})
    r = TestClient(app_mod.app).post("/api/voice/upload", data={"clientId": "CLI-01BBBBBBBBBBBBBBBBBBBBBBBB"},
                                     files={"audio": ("rec.webm", b"x" * 10, "audio/webm")}, headers=AUTH)
    assert r.status_code == 404


TRANSCRIPT = "（架空）散歩の途中で座り込んだ。" * 40  # 500 字を超える


def test_voice_upload_keeps_the_audio_under_the_transcript_hash(app_mod, monkeypatch, tmp_path):
    import hashlib
    import stat
    import nest.genai
    _set_clients(monkeypatch, app_mod, {CLIENT})
    root = _voice_root(monkeypatch, app_mod, tmp_path)
    monkeypatch.setattr(nest.genai, "transcribe_audio", lambda path: TRANSCRIPT)
    r = TestClient(app_mod.app).post("/api/voice/upload", data={"clientId": CLIENT},
                                     files={"audio": ("rec.webm", b"audio", "audio/webm")}, headers=AUTH)
    assert r.status_code == 200, r.text
    body = r.json()
    digest = hashlib.sha256(TRANSCRIPT.encode("utf-8")).hexdigest()
    assert body == {"status": "transcribed", "transcript": TRANSCRIPT, "documentHash": digest, "nodes_registered": 0}
    kept = root / (digest + ".webm")
    assert kept.read_bytes() == b"audio"
    assert stat.S_IMODE(os.stat(root).st_mode) == 0o700 and stat.S_IMODE(os.stat(kept).st_mode) == 0o600


def test_voice_upload_keeps_nothing_when_transcription_fails(app_mod, monkeypatch, tmp_path):
    import nest.genai
    _set_clients(monkeypatch, app_mod, {CLIENT})
    root = _voice_root(monkeypatch, app_mod, tmp_path)
    monkeypatch.setattr(nest.genai, "transcribe_audio", lambda path: None)
    r = TestClient(app_mod.app).post("/api/voice/upload", data={"clientId": CLIENT},
                                     files={"audio": ("rec.webm", b"audio", "audio/webm")}, headers=AUTH)
    assert r.status_code == 422
    assert not root.exists() or list(root.iterdir()) == []
