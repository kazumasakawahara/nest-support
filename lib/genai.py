"""Gemini の入口（N-03・N-04。docs/external-api.md NEXT-03・NEXT-04、ADR-001 D11-1）。

- Gemini のクライアントを作るのは、このモジュールの get_genai_client だけ
- 呼ぶたびに送信の歯止め（nest.egress）で行ごとの許可を確かめる。鍵の有無は許可の印にしない
- 送り先は歯止めの一覧（NEXT-03・04）のホストに固定する。Vertex AI への切り替えと環境変数での差し替えを効かせない
- google-genai は 1.66.0 に固定（pyproject）。版を上げるときは、送り先を変える環境変数が増えていないか部品の中身を読み直す

埋め込みは N-04 で外した（ADR-001 D10）。
"""
import os
import sys
from typing import Optional

from dotenv import load_dotenv

from nest import egress

load_dotenv()

# 生成モデル（OCR・音声文字起こし・テキスト構造化に使用）
# 既定 gemini-2.5-pro（GA・高精度）。GEMINI_GENERATION_MODEL で上書き可
# 注: gemini-2.0-flash は 2026-06-01 に提供終了のため既定から除外。
GENERATION_MODEL = os.getenv("GEMINI_GENERATION_MODEL", "gemini-2.5-pro")

# 送り先：歯止めの一覧と同じ定数から作る（二か所に書かない。G-28）
GEMINI_BASE_URL = "https://%s/" % egress.DESTINATIONS["NEXT-03"].host

# 音声MIME タイプのフォールバック用マッピング
_AUDIO_MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
}


def log(message: str, level: str = "INFO"):
    """ログ出力（標準エラー出力）"""
    sys.stderr.write(f"[Gemini:{level}] {message}\n")
    sys.stderr.flush()


_genai_client = None


def get_genai_client(row: str):
    """google-genai クライアントを取得（シングルトン）。

    row は docs/external-api.md の行（NEXT-03 文字起こし・NEXT-04 OCR など）。
    呼ぶたびに送信の歯止め（nest.egress）で許可を確かめ、不許可なら None を返す。
    """
    try:
        egress.authorize(row)
        egress.check_url(row, GEMINI_BASE_URL)
    except egress.EgressDenied as e:
        log("Gemini に送らない（%s）" % e, "WARN")
        return None
    global _genai_client
    if _genai_client is None:
        from google import genai
        from google.genai import types
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            log("GEMINI_API_KEY が未設定です", "ERROR")
            return None
        _genai_client = genai.Client(
            api_key=api_key,
            vertexai=False,
            http_options=types.HttpOptions(base_url=GEMINI_BASE_URL),
        )
        log("Gemini クライアント初期化完了")
    return _genai_client


def transcribe_audio(
    audio_path: str,
    instruction: str = "この音声を正確に文字起こししてください。話者が複数いる場合は区別してください。",
) -> Optional[str]:
    """Gemini 生成モデルで音声をテキストに文字起こし（NEXT-03）。失敗・不許可なら None。"""
    client = get_genai_client("NEXT-03")
    if client is None:
        return None

    from google.genai import types
    import mimetypes

    mime_type, _ = mimetypes.guess_type(audio_path)
    if mime_type is None:
        ext = os.path.splitext(audio_path)[1].lower()
        mime_type = _AUDIO_MIME_TYPES.get(ext, "audio/mpeg")

    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                instruction,
            ],
        )
        text = response.text
        log(f"音声文字起こし完了: {len(text)}文字, {audio_path}")
        return text
    except Exception as e:
        log(f"音声文字起こしエラー: {e}", "ERROR")
        return None


def ocr_with_gemini(
    file_path: str,
    instruction: str = "この文書のすべてのテキストを正確に抽出してください。手書き部分も含めて読み取ってください。",
) -> Optional[str]:
    """Gemini 生成モデルでスキャンPDF/手書き画像からテキストを抽出（NEXT-04）。失敗・不許可なら None。"""
    client = get_genai_client("NEXT-04")
    if client is None:
        return None

    from google.genai import types
    import mimetypes

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        if file_path.lower().endswith(".pdf"):
            mime_type = "application/pdf"
        else:
            mime_type = "image/png"

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=[
                instruction,
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            ],
        )
        text = response.text
        log(f"OCR完了: {len(text)}文字抽出, {file_path}")
        return text
    except Exception as e:
        log(f"OCRエラー: {e}", "ERROR")
        return None
