"""
多機能インポーター (Multi-Source Importer) — 文字の取り出しだけ

音声・手書きメモ画像・PDF・Word・Excel・テキストから文字を取り出して出力する。
DB には書かない。構造化（書き込みの案）は Claude（docs/external-api.md NEXT-01）と
ゲートの経路で行う（ADR-001 D6・D11-1。Gemini による構造化は N-05 で外した）。

音声の文字起こし・画像の OCR は Gemini に送る（NEXT-03・NEXT-04）。機能の設定と契約の確認の
記録がそろわなければ送らず、その文書は「取り出せない」になる。鍵の有無は送る印にしない。

Usage:
    uv run python scripts/multi_importer.py <file_or_dir> [--json]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.file_readers import SUPPORTED_EXTENSIONS, _IMAGE_EXTENSIONS


def _log(message: str, level: str = "INFO"):
    sys.stderr.write(f"[MultiImporter:{level}] {message}\n")
    sys.stderr.flush()


# 音声ファイルの拡張子
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4"}

# 全対応拡張子
ALL_EXTENSIONS = set(SUPPORTED_EXTENSIONS.keys()) | AUDIO_EXTENSIONS


def collect_files(path: str) -> list[Path]:
    """指定パス（ファイル or ディレクトリ）から対応ファイルを収集する"""
    target = Path(path)
    if target.is_file():
        if target.suffix.lower() in ALL_EXTENSIONS:
            return [target]
        _log(f"非対応ファイル: {target.suffix}", "WARN")
        return []

    if target.is_dir():
        files = []
        for f in sorted(target.iterdir()):
            if f.is_file() and f.suffix.lower() in ALL_EXTENSIONS:
                files.append(f)
        return files

    _log(f"パスが存在しません: {path}", "ERROR")
    return []


def extract_text(file_path: Path) -> str | None:
    """ファイルからテキストを抽出する"""
    suffix = file_path.suffix.lower()

    # 音声ファイル → Gemini で文字起こし
    if suffix in AUDIO_EXTENSIONS:
        try:
            from lib.genai import transcribe_audio
            text = transcribe_audio(str(file_path))
            if text:
                _log(f"音声文字起こし完了: {file_path.name} ({len(text)}文字)")
                return text
        except Exception as e:
            _log(f"音声文字起こし失敗: {file_path.name}: {e}", "ERROR")
        return None

    # 画像ファイル → Gemini OCR
    if suffix in _IMAGE_EXTENSIONS:
        try:
            from lib.genai import ocr_with_gemini
            text = ocr_with_gemini(
                str(file_path),
                instruction=(
                    "この文書のすべてのテキストを正確に抽出してください。"
                    "手書き部分も含めて読み取ってください。"
                    "支援記録・ケース記録の場合は、日付、状況、対応、効果、"
                    "本人の感情状態がわかる記述に注目してください。"
                ),
            )
            if text:
                _log(f"OCR完了: {file_path.name} ({len(text)}文字)")
                return text
        except Exception as e:
            _log(f"OCR失敗: {file_path.name}: {e}", "ERROR")
        return None

    # その他 (docx, xlsx, pdf, txt) → file_readers
    try:
        from lib.file_readers import read_docx, read_xlsx, read_pdf, read_txt

        with open(file_path, "rb") as f:
            if suffix == ".docx":
                return read_docx(f)
            elif suffix == ".xlsx":
                return read_xlsx(f)
            elif suffix == ".pdf":
                return read_pdf(f)
            elif suffix == ".txt":
                return read_txt(f)
    except Exception as e:
        _log(f"テキスト抽出失敗: {file_path.name}: {e}", "ERROR")

    return None


def process_file(file_path: Path) -> dict:
    """1 ファイルから文字を取り出す。DB には書かない。"""
    _log(f"処理中: {file_path.name}")
    text = extract_text(file_path)
    if not text:
        return {"file": str(file_path), "status": "extraction_failed", "text_length": 0, "text": None}
    return {"file": str(file_path), "status": "extracted", "text_length": len(text), "text": text}


def main():
    parser = argparse.ArgumentParser(
        description="多機能インポーター: 音声・画像・PDF・文書から文字を取り出す（DB には書かない）",
    )
    parser.add_argument("path", help="ファイルまたはディレクトリのパス")
    parser.add_argument("--json", action="store_true", help="結果をJSON形式で出力")
    args = parser.parse_args()

    files = collect_files(args.path)
    if not files:
        _log("処理対象ファイルが見つかりません", "ERROR")
        sys.exit(1)

    _log(f"処理対象: {len(files)}ファイル")
    results = [process_file(f) for f in files]
    failed = sum(1 for r in results if r["status"] != "extracted")

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"{'='*60}")
            print(f"{Path(r['file']).name}（{r['status']}, {r['text_length']}文字）")
            print(f"{'='*60}")
            if r["text"]:
                print(r["text"])
        print(f"\n取り出し: {len(results) - failed}件, 失敗: {failed}件")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
