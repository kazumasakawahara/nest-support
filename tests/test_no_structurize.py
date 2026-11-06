"""N-05：multi_importer の Gemini による構造化（NEXT-07）を外す（ADR-001 D11-1）。

- 構造化は NEXT-01（Claude）とゲートの経路だけ。Gemini で構造化して DB に書く経路を残さない
- multi_importer は N-38 で外した（tests/test_old_db_code_isolated.py）
- field-ui の音声は文字起こし（NEXT-03）までで、構造化も登録もしない
- 「GEMINI_API_KEY が未設定です」の文言は、鍵を実際に見る nest/genai.py だけに残る（台帳 G-29）
"""
import re

import pytest

pytest.importorskip("google.genai")

from tests.test_gemini_gate import allow, fake_genai  # noqa: F401  フィクスチャ
from tests.test_no_embedding import REPO, code_files

ALL_ROWS = ("NEXT-03", "NEXT-04", "NEXT-07")


def test_no_structurize_path_in_code():
    hits = []
    for p in code_files():
        text = (REPO / p).read_text(encoding="utf-8", errors="replace")
        for pat in (r"NEXT-07", r"structurize_with_gemini", r"EXTRACTION_PROMPT"):
            if re.search(pat, text):
                hits.append("%s %s" % (p, pat))
    assert hits == []


def test_key_message_only_where_key_is_read():
    hits = [p for p in code_files() if p.endswith(".py")
            and "GEMINI_API_KEY が未設定です" in (REPO / p).read_text(encoding="utf-8")]
    assert hits == ["nest/genai.py"]


def test_field_ui_voice_transcribes_without_structuring(fake_genai, monkeypatch, tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from tests.test_field_ui_guards import AUTH, CLIENT, _load_field_ui, _set_clients, _staff_table, _voice_root

    _staff_table(monkeypatch, tmp_path)
    app_mod = _load_field_ui()
    _set_clients(monkeypatch, app_mod, {CLIENT})
    _voice_root(monkeypatch, app_mod, tmp_path)
    sent = []
    monkeypatch.setattr(app_mod, "submit_to_gate", lambda req: sent.append(req) or {"ok": True})
    allow(fake_genai, *ALL_ROWS)

    r = TestClient(app_mod.app).post(
        "/api/voice/upload",
        data={"clientId": CLIENT},
        files={"audio": ("fictional.webm", b"x" * 10, "audio/webm")},
        headers=AUTH,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "transcribed"
    assert body["transcript"] == "架空の文字起こし"
    assert body["nodes_registered"] == 0
    assert fake_genai["calls"] == ["generate_content"]  # 文字起こしの 1 回だけ
    assert sent == []  # 構造化も登録もしない（案は職員が narrative-extractor と intake で作る）


def test_field_ui_voice_needs_the_next03_gate(fake_genai, monkeypatch, tmp_path):
    """N-37：録音の文字起こしは NEXT-03 の歯止め（nest/genai.py の egress.authorize）を通る。許可が無ければ送らず、音声も残さない"""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from tests.test_field_ui_guards import AUTH, CLIENT, _load_field_ui, _set_clients, _staff_table, _voice_root

    _staff_table(monkeypatch, tmp_path)
    app_mod = _load_field_ui()
    _set_clients(monkeypatch, app_mod, {CLIENT})
    root = _voice_root(monkeypatch, app_mod, tmp_path)
    r = TestClient(app_mod.app).post("/api/voice/upload", data={"clientId": CLIENT},
                                     files={"audio": ("fictional.webm", b"x" * 10, "audio/webm")}, headers=AUTH)
    assert r.status_code == 422
    assert fake_genai["calls"] == []  # 外へ送っていない
    assert not root.exists() or list(root.iterdir()) == []
