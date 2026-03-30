"""
多機能インポーター (Multi-Source Importer)

音声（MeetingRecord）、手書きメモ画像、PDF、テキストファイルから
「感情の揺れ」を含む構造化データを抽出し、Neo4j に一括登録するスクリプト。

前提条件:
    - GEMINI_API_KEY 環境変数が設定されていること（.env ファイル or export）
      → Gemini 2.0 Flash による音声文字起こし・画像OCR・テキスト構造化に必須
    - Neo4j が起動していること（docker compose up -d）

Usage:
    uv run python scripts/multi_importer.py <file_or_dir> --client "クライアント名" [--supporter "支援者名"]
    uv run python scripts/multi_importer.py ./data/ --client "山田太郎" --supporter "鈴木"
    uv run python scripts/multi_importer.py memo.jpg --client "山田太郎" --dry-run
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
            from lib.embedding import transcribe_audio
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
            from lib.embedding import ocr_with_gemini
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


def structurize_with_gemini(
    text: str,
    client_name: str,
    supporter_name: str | None = None,
    source_file: str = "",
) -> dict | None:
    """
    Gemini でテキストを構造化データに変換する。
    EXTRACTION_PROMPT.md のプロンプトを使用し、emotion/triggerTag/context を含む
    グラフデータを生成する。
    """
    try:
        from lib.embedding import get_genai_client
    except ImportError:
        _log("lib.embedding が利用できません", "ERROR")
        return None

    client = get_genai_client()
    if client is None:
        _log("GEMINI_API_KEY が未設定です", "ERROR")
        return None

    # EXTRACTION_PROMPT.md を読み込み
    prompt_path = Path(__file__).resolve().parent.parent / "docs" / "EXTRACTION_PROMPT.md"
    if not prompt_path.exists():
        _log(f"抽出プロンプトが見つかりません: {prompt_path}", "ERROR")
        return None

    extraction_prompt = prompt_path.read_text(encoding="utf-8")

    # コンテキスト情報を付加
    context_info = f"\n\nクライアント名: {client_name}"
    if supporter_name:
        context_info += f"\n支援者名: {supporter_name}"
    context_info += f"\nソースファイル: {source_file}"

    full_prompt = extraction_prompt + context_info + f"\n\n--- 以下のテキストを構造化してください ---\n\n{text}"

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[full_prompt],
        )
        response_text = response.text.strip()

        # JSON ブロック記法を除去
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        graph_data = json.loads(response_text.strip())
        _log(f"構造化完了: ノード{len(graph_data.get('nodes', []))}件, "
             f"リレーション{len(graph_data.get('relationships', []))}件")
        return graph_data
    except json.JSONDecodeError as e:
        _log(f"JSON パースエラー: {e}", "ERROR")
        _log(f"レスポンス先頭200文字: {response_text[:200]}", "DEBUG")
        return None
    except Exception as e:
        _log(f"Gemini 構造化エラー: {e}", "ERROR")
        return None


def register_graph(graph_data: dict, user_name: str = "multi_importer") -> dict:
    """構造化データを Neo4j に登録する"""
    from lib.db_operations import register_to_database
    return register_to_database(graph_data, user_name=user_name)


def process_file(
    file_path: Path,
    client_name: str,
    supporter_name: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    1ファイルを処理する: テキスト抽出 → 構造化 → 登録
    """
    result = {
        "file": str(file_path),
        "status": "pending",
        "text_length": 0,
        "nodes": 0,
        "relationships": 0,
    }

    # Step 1: テキスト抽出
    _log(f"処理中: {file_path.name}")
    text = extract_text(file_path)
    if not text:
        result["status"] = "extraction_failed"
        return result

    result["text_length"] = len(text)

    # Step 2: Gemini で構造化
    graph_data = structurize_with_gemini(
        text=text,
        client_name=client_name,
        supporter_name=supporter_name,
        source_file=file_path.name,
    )
    if not graph_data:
        result["status"] = "structurize_failed"
        return result

    result["nodes"] = len(graph_data.get("nodes", []))
    result["relationships"] = len(graph_data.get("relationships", []))

    if dry_run:
        result["status"] = "dry_run"
        result["graph_data"] = graph_data
        _log(f"[DRY RUN] {file_path.name}: {result['nodes']}ノード, "
             f"{result['relationships']}リレーション")
        return result

    # Step 3: Neo4j に登録
    reg_result = register_graph(graph_data)
    result["status"] = reg_result.get("status", "unknown")
    result["registration"] = reg_result

    return result


def main():
    parser = argparse.ArgumentParser(
        description="多機能インポーター: 音声・画像・PDF・テキストから感情データを含む構造化データを一括登録",
    )
    parser.add_argument("path", help="ファイルまたはディレクトリのパス")
    parser.add_argument("--client", required=True, help="クライアント名")
    parser.add_argument("--supporter", help="支援者名")
    parser.add_argument("--dry-run", action="store_true", help="登録せず構造化結果のみ表示")
    parser.add_argument("--json", action="store_true", help="結果をJSON形式で出力")
    args = parser.parse_args()

    files = collect_files(args.path)
    if not files:
        _log("処理対象ファイルが見つかりません", "ERROR")
        sys.exit(1)

    _log(f"処理対象: {len(files)}ファイル")
    results = []
    success = 0
    failed = 0

    for file_path in files:
        result = process_file(
            file_path=file_path,
            client_name=args.client,
            supporter_name=args.supporter,
            dry_run=args.dry_run,
        )
        results.append(result)
        if result["status"] in ("success", "dry_run"):
            success += 1
        else:
            failed += 1

    # 結果出力
    if args.json:
        # dry_run 時の graph_data は大きいので省略可能
        output = []
        for r in results:
            out = {k: v for k, v in r.items() if k != "graph_data"}
            output.append(out)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"多機能インポーター 処理結果")
        print(f"{'='*60}")
        print(f"クライアント: {args.client}")
        if args.supporter:
            print(f"支援者: {args.supporter}")
        print(f"対象ファイル数: {len(files)}")
        print(f"成功: {success}, 失敗: {failed}")
        print(f"{'='*60}")
        for r in results:
            status_icon = "OK" if r["status"] in ("success", "dry_run") else "NG"
            print(f"  [{status_icon}] {Path(r['file']).name}: "
                  f"{r['text_length']}文字 → {r['nodes']}ノード, "
                  f"{r['relationships']}リレーション ({r['status']})")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
