"""N-03：Gemini の文字起こし（NEXT-03）と OCR（NEXT-04）を送信の歯止めに通す。

- 鍵（GEMINI_API_KEY）があるだけでは送らない。機能の設定と契約の確認の記録がそろった行だけ送る
- 許可は行ごと、呼ぶたびに確かめる（一度クライアントを作った後でも）
- 埋め込み（NEXT-06）は N-04、構造化（NEXT-07）は N-05 でコードから外した（tests/test_no_embedding.py・tests/test_no_structurize.py）
- 送り先は generativelanguage.googleapis.com に固定する（Vertex AI・環境変数での base_url の差し替えを効かせない）

google.genai.Client は偽物に差し替え、外へは出さない。
"""
import subprocess

import pytest

pytest.importorskip("google.genai")
from google import genai
from urllib.parse import urlsplit

import nest.genai as emb
from nest import egress
from tests.test_egress import TODAY, good_entry, write


class FakeModels:
    def __init__(self, calls):
        self.calls = calls

    def generate_content(self, **kw):
        self.calls.append("generate_content")

        class R:
            text = "架空の文字起こし"
        return R()

    def embed_content(self, **kw):
        self.calls.append("embed_content")

        class E:
            values = [0.0]

        class R:
            embeddings = [E()]
        return R()


@pytest.fixture
def fake_genai(monkeypatch, tmp_path):
    state = {"made": [], "calls": []}

    class FakeClient:
        def __init__(self, **kw):
            state["made"].append(kw)
            self.models = FakeModels(state["calls"])

    monkeypatch.setattr(genai, "Client", FakeClient)
    monkeypatch.setattr(emb, "_genai_client", None)
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-not-a-key")
    rec = tmp_path / "record.json"
    feat = tmp_path / "features.json"
    monkeypatch.setattr(egress, "record_path", lambda: rec)
    monkeypatch.setattr(egress, "features_path", lambda: feat)
    monkeypatch.setattr(egress, "today", lambda: TODAY)
    state["rec"], state["feat"] = rec, feat
    audio = tmp_path / "fictional.mp3"
    audio.write_bytes(b"x" * 10)
    image = tmp_path / "fictional.png"
    image.write_bytes(b"x" * 10)
    state["audio"], state["image"] = str(audio), str(image)
    return state


def allow(state, *rows):
    write(state["feat"], {r: True for r in rows})
    write(state["rec"], {"version": 1, "destinations": {r: good_entry() for r in rows}})


def test_key_alone_sends_nothing(fake_genai):
    assert emb.transcribe_audio(fake_genai["audio"]) is None
    assert emb.ocr_with_gemini(fake_genai["image"]) is None
    assert fake_genai["calls"] == []
    assert fake_genai["made"] == []


def test_transcribe_sends_when_next03_allowed(fake_genai):
    allow(fake_genai, "NEXT-03")
    assert emb.transcribe_audio(fake_genai["audio"]) == "架空の文字起こし"
    assert fake_genai["calls"] == ["generate_content"]


def test_next03_does_not_open_ocr(fake_genai):
    allow(fake_genai, "NEXT-03")
    assert emb.ocr_with_gemini(fake_genai["image"]) is None
    assert fake_genai["calls"] == []


def test_ocr_sends_when_next04_allowed(fake_genai):
    allow(fake_genai, "NEXT-04")
    assert emb.ocr_with_gemini(fake_genai["image"]) == "架空の文字起こし"
    assert fake_genai["calls"] == ["generate_content"]


def test_rechecks_every_call_after_client_made(fake_genai):
    allow(fake_genai, "NEXT-03")
    assert emb.transcribe_audio(fake_genai["audio"]) is not None
    fake_genai["feat"].unlink()  # 設定を外す
    assert emb.transcribe_audio(fake_genai["audio"]) is None
    assert fake_genai["calls"] == ["generate_content"]


def test_destination_fixed_to_gemini_api(fake_genai, monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_GEMINI_BASE_URL", "https://example.invalid/")
    allow(fake_genai, "NEXT-03")
    emb.transcribe_audio(fake_genai["audio"])
    (kw,) = fake_genai["made"]
    assert kw.get("vertexai") is False
    assert kw["http_options"].base_url == "https://generativelanguage.googleapis.com/"


def test_get_genai_client_requires_row(fake_genai):
    with pytest.raises(TypeError):
        emb.get_genai_client()


def test_only_one_place_builds_gemini_client():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], capture_output=True, text=True,
                         cwd=egress.REPO, check=True).stdout.split()
    hits = [p for p in out if (egress.REPO / p).is_file() and "genai.Client(" in (egress.REPO / p).read_text(encoding="utf-8")
            and not p.startswith("tests/")]
    assert hits == ["nest/genai.py"]


# --- G-28 の条件（2026-11-05 河原さん） --------------------------------------------

def test_real_client_keeps_gemini_host_under_env_overrides(monkeypatch, tmp_path):
    """本物の genai.Client を作る（作るだけで送らない）。二つの環境変数があっても送り先は変わらない。"""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-not-a-key")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_GEMINI_BASE_URL", "https://example.invalid/")
    monkeypatch.setattr(emb, "_genai_client", None)
    rec, feat = tmp_path / "record.json", tmp_path / "features.json"
    monkeypatch.setattr(egress, "record_path", lambda: rec)
    monkeypatch.setattr(egress, "features_path", lambda: feat)
    monkeypatch.setattr(egress, "today", lambda: TODAY)
    write(feat, {"NEXT-03": True})
    write(rec, {"version": 1, "destinations": {"NEXT-03": good_entry()}})
    client = emb.get_genai_client("NEXT-03")
    api = client._api_client
    assert api.vertexai is False
    assert urlsplit(api._http_options.base_url).hostname == "generativelanguage.googleapis.com"


def test_unpinned_client_would_be_redirected(monkeypatch):
    """固定しなければ環境変数で送り先が変わる（部品のふるまいの確かめ。版が変わって崩れたら読み直す）。"""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-not-a-key")
    monkeypatch.setenv("GOOGLE_GEMINI_BASE_URL", "https://example.invalid/")
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    api = genai.Client(api_key="dummy-not-a-key")._api_client
    assert urlsplit(api._http_options.base_url).hostname == "example.invalid"


def test_client_host_comes_from_egress_rows():
    """クライアントに固定したホストは、歯止めの NEXT-03・04 のホストと同じ定数から来る。"""
    host = urlsplit(emb.GEMINI_BASE_URL).hostname
    assert host == egress.DESTINATIONS["NEXT-03"].host == egress.DESTINATIONS["NEXT-04"].host
    rows = egress.rows_from_document(egress.DOCUMENT)
    assert rows["NEXT-03"][0] == rows["NEXT-04"][0] == host
    assert "generativelanguage.googleapis.com" not in (egress.REPO / "nest" / "genai.py").read_text(encoding="utf-8")


def test_google_genai_pinned_to_reviewed_version():
    """版を上げるときは、部品の中身（送り先を変える環境変数）を読み直してから（計画 N-04）。"""
    from importlib.metadata import version
    assert version("google-genai") == "1.66.0"
    assert '"google-genai==1.66.0"' in (egress.REPO / "pyproject.toml").read_text(encoding="utf-8")
