"""
nest-support 現場UI サーバー

現場の職員向けの Web の画面を出す FastAPI のサーバー。

画面:
  /                  → トップ（メニュー）
  /record            → A. 支援記録の入力
  /dashboard         → B. ダッシュボード（今は閉じている。推移は insight-agent スキルで見る）
  /voice             → C. 音声の録音（文字起こしまで）

決まり（計画 N-37。2026-11-06 河原さん）:
  - 認証は職員ごとのトークン（nest.auth.require_staff）。ゲートに渡す職員 ID はトークンから決める
  - 読むのは読み取りの包み（nest.mcp_guard）を通してだけ。本人は ID と仮名で扱い、名前を返さない
  - 支援記録はゲート（nest.gate.write.submit）に依頼として渡す。DB に直に書かない
  - 音声は文字起こし（docs/external-api.md NEXT-03 の歯止めを通す）まで。構造化も登録もしない。
    書き込みの案は、職員が文字起こしを原文にして narrative-extractor と intake で作る
  - 文字起こしができた音声は nest_voice_data/ に「文字起こしの sha256（＝ documentHash）＋ 拡張子」で置く。
    承認されたら・遅くとも 30 日で scripts/purge_voice.py が消す

起動:
  uv run python field-ui/server.py      # 既定は 127.0.0.1:8001
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from nest.auth import require_staff, set_session_cookie, staff_of
from nest import auth, voice

app = FastAPI(
    title="nest-support 現場UI",
    description="支援記録の入力・音声の録音",
    version="2.0.0",
)

# CORS は既定で無効（同一オリジン運用・リバースプロキシ配下を想定）。
# クロスオリジンで使う場合のみ CORS_ALLOW_ORIGINS にカンマ区切りで許可元を明示する。
# ワイルドカード '*' は Cookie 認証（nest_session）と併用できず、資格情報漏洩面にもなるため使わない。
_cors_env = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip() and o.strip() != "*"]
if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 音声アップロード上限・許可形式
MAX_AUDIO_BYTES = int(os.getenv("MAX_AUDIO_MB", "25")) * 1024 * 1024
ALLOWED_AUDIO_EXT = {".webm", ".ogg", ".oga", ".mp3", ".m4a", ".mp4", ".wav", ".aac", ".flac"}
VOICE_ROOT = voice.VOICE_DIR  # 音声の置き場所（nest/voice.py。権限 700、Time Machine の対象外）
DASHBOARD_CLOSED = "ダッシュボードは閉じています（計画 N-37）。支援記録の推移は insight-agent スキルで見てください"


# =============================================================================
# DB：読むのは包み、書くのはゲート
# =============================================================================

def read_personal(query: str, params: dict | None = None) -> list[dict]:
    """個人の側を読み取りの包みで読む（画面の経路：NEXT-02 の歯止めは通さない。読み取りだけ、実名などは返さない。台帳 G-85）。"""
    from nest import connections, mcp_guard
    with connections.driver("personal") as d:
        mcp_guard.require_personal_allowed(d, caller="screen")
        return mcp_guard.run_read(d, query, params, personal=True)


def submit_to_gate(req: dict) -> dict:
    """ゲートに依頼を渡す（検証・職員の役割の確かめ・監査の記録はゲートが行う）。"""
    from nest import connections
    from nest.gate import write as gw
    with connections.driver("personal") as d:
        return gw.submit(req, d)


def _client_exists(client_id: str) -> bool:
    """既にいる本人か（ゲートに渡す前・文字起こしの前に弾く）。読めなければ 503。"""
    try:
        rows = read_personal("MATCH (c:Client {clientId: $id}) RETURN count(c) AS n", {"id": client_id})
    except Exception:
        raise HTTPException(status_code=503, detail="いまは本人を確かめられません（DB を読めない）")
    return bool(rows and rows[0].get("n", 0) > 0)


def _require_client(client_id: str) -> None:
    if not _client_exists(client_id):
        raise HTTPException(status_code=404, detail="いない本人です（%s）。本人の登録は Claude の外で行います" % client_id)


# 静的ファイル配信
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# =============================================================================
# ページ配信
# =============================================================================

@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/record")
async def record_page():
    return FileResponse(STATIC_DIR / "record-form.html")

@app.get("/dashboard")
async def dashboard_page():
    return FileResponse(STATIC_DIR / "dashboard.html")

@app.get("/voice")
async def voice_page():
    return FileResponse(STATIC_DIR / "voice-recorder.html")

@app.get("/login")
async def login_page():
    return FileResponse(STATIC_DIR / "login.html")


# =============================================================================
# API: ログイン（セッション Cookie 発行）
# =============================================================================

class LoginInput(BaseModel):
    token: str

@app.post("/api/login")
async def api_login(data: LoginInput, response: Response):
    try:
        staff_id = staff_of(data.token)
    except auth.StaffTableError:
        raise HTTPException(status_code=503, detail="認証が未設定です（職員のトークンの表を作ってください）")
    if staff_id is None:
        raise HTTPException(status_code=401, detail="トークンが正しくありません")
    set_session_cookie(response, data.token)
    return {"status": "ok"}


# =============================================================================
# API: 本人の一覧（ID と仮名だけ）
# =============================================================================

@app.get("/api/clients")
async def api_clients(staff: str = Depends(require_staff)):
    try:
        return read_personal("MATCH (c:Client) WHERE c.status = 'Active' "
                             "RETURN c.clientId AS clientId, c.displayCode AS displayCode ORDER BY displayCode")
    except Exception:
        raise HTTPException(status_code=503, detail="いまは本人の一覧を読めません")


# =============================================================================
# API: 支援記録の登録（ゲートを通す）
# =============================================================================

class SupportLogInput(BaseModel):
    """正典の SupportLog の項目だけ（docs/SCHEMA.md）。ほかの欄があれば 422。"""
    model_config = ConfigDict(extra="forbid")
    clientId: str
    date: str
    situation: str
    action: str | None = None
    effectiveness: str | None = None
    note: str | None = None
    nextAction: str | None = None


def support_log_request(staff_id: str, data: SupportLogInput, request_id: str) -> dict:
    """支援記録を書く依頼。人が入れた記録なので origin は Human。空の欄は送らない。値の検証はゲートが行う。"""
    props = {k: v for k, v in data.model_dump(exclude={"clientId"}).items() if v not in (None, "")}
    return {"requestId": request_id, "actorStaffId": staff_id,
            "nodes": [{"ref": "log", "label": "SupportLog", "origin": "Human", "properties": props}],
            "relationships": [
                {"type": "ABOUT", "from": "log", "to": {"label": "Client", "id": data.clientId}, "properties": {}},
                {"type": "AUTHORED_BY", "from": "log", "to": {"label": "Staff", "id": staff_id}, "properties": {}}]}


@app.post("/api/support-log")
async def api_create_support_log(data: SupportLogInput, staff: str = Depends(require_staff)):
    _require_client(data.clientId)
    req = support_log_request(staff, data, "field-ui-" + uuid.uuid4().hex)
    try:
        out = submit_to_gate(req)
    except Exception:
        raise HTTPException(status_code=503, detail="いまは登録できません（DB に届かない）")
    if not out.get("ok"):
        raise HTTPException(status_code=422, detail=out.get("errors", []))
    return {"ok": True, "supportLogId": out["ids"]["log"]}


# =============================================================================
# API: ダッシュボード（閉じている）
# =============================================================================

@app.get("/api/dashboard/summary")
async def api_dashboard_summary(staff: str = Depends(require_staff)):
    raise HTTPException(status_code=503, detail=DASHBOARD_CLOSED)


@app.get("/api/dashboard/alerts/{client_id}")
async def api_dashboard_alerts(client_id: str, staff: str = Depends(require_staff)):
    raise HTTPException(status_code=503, detail=DASHBOARD_CLOSED)


@app.get("/api/dashboard/recent-logs/{client_id}")
async def api_recent_logs(client_id: str, staff: str = Depends(require_staff)):
    raise HTTPException(status_code=503, detail=DASHBOARD_CLOSED)


# =============================================================================
# API: 音声アップロード → 文字起こし
# =============================================================================

@app.post("/api/voice/upload")
async def api_voice_upload(
    audio: UploadFile = File(...),
    clientId: str = Form(...),
    staff: str = Depends(require_staff),
):
    """音声ファイルをアップロードし、文字起こしの全文と documentHash を返す（NEXT-03）。構造化と登録はしない（N-05・ADR-001 D6）。
    全文を返すのは、職員がそのまま原文にすると documentHash が音声の名前と合い、承認で音声を消せるため。"""
    # いない本人は、文字起こし（外への送信）の前に弾く
    _require_client(clientId)

    # 形式・拡張子の検証（想定外ファイルの処理・保存を防ぐ）
    suffix = Path(audio.filename or "audio.webm").suffix.lower() or ".webm"
    ct = (audio.content_type or "").lower()
    if suffix not in ALLOWED_AUDIO_EXT and not (ct.startswith("audio/") or ct == "video/webm"):
        raise HTTPException(
            status_code=415,
            detail=f"対応していない音声形式です（{audio.filename or ct}）",
        )

    # サイズ上限を超える入力はメモリを食い潰す前にチャンク読みで打ち切る
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        total = 0
        while True:
            chunk = await audio.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_AUDIO_BYTES:
                tmp.close()
                os.unlink(tmp.name)
                raise HTTPException(
                    status_code=413,
                    detail=f"音声ファイルが大きすぎます（上限 {MAX_AUDIO_BYTES // (1024*1024)}MB）",
                )
            tmp.write(chunk)
        tmp_path = tmp.name
    if total == 0:
        os.unlink(tmp_path)
        raise HTTPException(status_code=422, detail="空の音声ファイルです")

    try:
        from nest import genai
        transcript = genai.transcribe_audio(tmp_path)
        if not transcript:
            raise HTTPException(status_code=422, detail="音声の文字起こしに失敗しました（送信が許されていないときも）")
        digest = voice.store(tmp_path, transcript, suffix, VOICE_ROOT)
        return {
            "status": "transcribed",
            "transcript": transcript,
            "documentHash": digest,
            "nodes_registered": 0,
        }
    finally:
        if os.path.exists(tmp_path):  # 置き場所へ移せなかったとき・文字起こしできなかったときは残さない
            os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn
    # 既定は 127.0.0.1（TLS・レート制限はリバースプロキシに委譲）。
    uvicorn.run(
        app,
        host=os.getenv("BIND_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8001")),
    )
