"""面談記録（音声）の登録。

lib/embedding.py から移した（N-04）。埋め込み（音声・文字起こしのベクトル）は ADR-001 D10 で外した。
文字起こしは lib.genai.transcribe_audio（NEXT-03。歯止めが許可したときだけ送る）。
"""
import os
import sys

from lib.genai import _AUDIO_MIME_TYPES, transcribe_audio


def log(message: str, level: str = "INFO"):
    """ログ出力（標準エラー出力）"""
    sys.stderr.write(f"[MeetingRecord:{level}] {message}\n")
    sys.stderr.flush()


def _run_query(query: str, params: dict = None) -> list:
    """Neo4j クエリ実行（db_operations を遅延インポート）"""
    from lib.db_operations import run_query
    return run_query(query, params)


def _get_audio_duration(path: str) -> float:
    """ffprobe で音声の長さ（秒）を取得。ffprobe がなければ -1 を返す"""
    import subprocess
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return -1


def register_meeting_record(
    audio_path: str,
    client_name: str,
    supporter_name: str,
    date: str,
    title: str = "",
    note: str = "",
    auto_transcribe: bool = True,
) -> dict:
    """
    音声ファイルから面談記録を登録

    1. auto_transcribe=True なら transcribe_audio() で文字起こし（歯止めが不許可なら None のまま）
    2. MeetingRecord ノードを作成
    3. Supporter→RECORDED→MeetingRecord→ABOUT→Client のリレーションを作成

    Returns:
        {"status": "success", "transcript": str, ...} または {"status": "error", ...}
    """
    if not os.path.exists(audio_path):
        return {"status": "error", "message": f"音声ファイルが見つかりません: {audio_path}"}

    # 存在しないクライアント名での登録は幽霊 Client を生むため先に弾く（R2-2）
    exists = _run_query(
        "MATCH (c:Client {name: $name}) RETURN count(c) AS n", {"name": client_name}
    )
    if not exists or exists[0].get("n", 0) == 0:
        return {
            "status": "error",
            "message": f"未登録のクライアントです: '{client_name}'。先にクライアント登録を行ってください。",
        }

    abs_path = os.path.abspath(audio_path)

    import mimetypes
    mime_type, _ = mimetypes.guess_type(audio_path)
    if mime_type is None:
        ext = os.path.splitext(audio_path)[1].lower()
        mime_type = _AUDIO_MIME_TYPES.get(ext, "audio/mpeg")

    duration = _get_audio_duration(audio_path)

    transcript = None
    if auto_transcribe:
        transcript = transcribe_audio(audio_path)

    try:
        duration_int = int(duration) if duration > 0 else None
        _run_query(
            """
            MATCH (c:Client {name: $client_name})
            MERGE (s:Supporter {name: $supporter_name})
            CREATE (m:MeetingRecord {
                date: date($date),
                title: $title,
                duration: $duration,
                filePath: $file_path,
                mimeType: $mime_type,
                transcript: $transcript,
                note: $note
            })
            CREATE (s)-[:RECORDED]->(m)
            CREATE (m)-[:ABOUT]->(c)
            RETURN elementId(m) AS id
            """,
            {
                "client_name": client_name,
                "supporter_name": supporter_name,
                "date": date,
                "title": title or f"面談記録 {date}",
                "duration": duration_int,
                "file_path": abs_path,
                "mime_type": mime_type,
                "transcript": transcript,
                "note": note or None,
            },
        )
        log(f"面談記録登録完了: {client_name} ({date})")
        return {
            "status": "success",
            "client_name": client_name,
            "date": date,
            "transcript": transcript,
        }
    except Exception as e:
        log(f"面談記録登録エラー: {e}", "ERROR")
        return {"status": "error", "message": str(e)}
