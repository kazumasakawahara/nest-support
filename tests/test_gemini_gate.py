"""N-03：Gemini の文字起こし（NEXT-03）と OCR（NEXT-04）を送信の歯止めに通す。

- 鍵（GEMINI_API_KEY）があるだけでは送らない。機能の設定と契約の確認の記録がそろった行だけ送る
- 許可は行ごと、呼ぶたびに確かめる（一度クライアントを作った後でも）
- やめた行（埋め込み NEXT-06、構造化 NEXT-07）は、設定と記録があっても送らない
- 送り先は generativelanguage.googleapis.com に固定する（Vertex AI・環境変数での base_url の差し替えを効かせない）

google.genai.Client は偽物に差し替え、外へは出さない。
"""
import subprocess

import pytest

pytest.importorskip("google.genai")
from google import genai

import lib.embedding as emb
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


def test_embedding_never_sends(fake_genai):
    allow(fake_genai, "NEXT-03", "NEXT-04", "NEXT-06")
    assert emb.embed_text("架空の文") is None
    assert emb.embed_texts_batch(["架空の文"]) == [None]
    assert emb.embed_audio(fake_genai["audio"]) is None
    assert emb.embed_image(fake_genai["image"]) is None
    assert "embed_content" not in fake_genai["calls"]


def test_structurize_never_sends(fake_genai):
    from scripts.multi_importer import structurize_with_gemini
    allow(fake_genai, "NEXT-03", "NEXT-04", "NEXT-07")
    assert structurize_with_gemini("架空の語り", "架空の人") is None
    assert fake_genai["calls"] == []


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
    out = subprocess.run(["git", "ls-files", "*.py"], capture_output=True, text=True,
                         cwd=egress.REPO, check=True).stdout.split()
    hits = [p for p in out if "genai.Client(" in (egress.REPO / p).read_text(encoding="utf-8")
            and not p.startswith("tests/")]
    assert hits == ["lib/embedding.py"]
