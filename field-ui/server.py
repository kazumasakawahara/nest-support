"""
nest-support 現場UI サーバー

現場スタッフ・管理者向けのWebインターフェースを提供するFastAPIサーバー。
Claude Desktop を使わなくても、スマホやPCから直接操作できる。

画面:
  /                  → トップ（メニュー）
  /record            → A. 支援記録入力フォーム
  /dashboard         → B. 管理者ダッシュボード
  /voice             → C. 音声ワンタップ録音

前提条件:
  - Neo4j が起動していること (docker compose up -d)
  - GEMINI_API_KEY が設定されていること（音声処理に必要）

起動:
  cd field-ui
  uv run uvicorn server:app --host 0.0.0.0 --port 8001 --reload
"""

import os
import sys
import json
import tempfile
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from lib.db_operations import run_query, register_to_database

app = FastAPI(
    title="nest-support 現場UI",
    description="支援記録入力・ダッシュボード・音声録音",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# =============================================================================
# API: クライアント一覧
# =============================================================================

@app.get("/api/clients")
async def api_clients():
    rows = run_query("MATCH (c:Client) RETURN c.name AS name ORDER BY c.name")
    return [r["name"] for r in rows]


# =============================================================================
# API: 支援記録の登録
# =============================================================================

class SupportLogInput(BaseModel):
    clientName: str
    supporterName: str
    date: str
    situation: str
    action: str
    effectiveness: str
    emotion: str
    triggerTag: str = ""
    context: str = ""
    note: str = ""

@app.post("/api/support-log")
async def api_create_support_log(data: SupportLogInput):
    graph = {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {"name": data.clientName}},
            {"temp_id": "s1", "label": "Supporter", "properties": {"name": data.supporterName}},
            {"temp_id": "log1", "label": "SupportLog", "properties": {
                "date": data.date,
                "situation": data.situation,
                "action": data.action,
                "effectiveness": data.effectiveness,
                "emotion": data.emotion,
                "triggerTag": data.triggerTag,
                "context": data.context,
                "note": data.note,
            }},
        ],
        "relationships": [
            {"source_temp_id": "s1", "target_temp_id": "log1", "type": "LOGGED", "properties": {}},
            {"source_temp_id": "log1", "target_temp_id": "c1", "type": "ABOUT", "properties": {}},
        ],
    }
    result = register_to_database(graph, user_name=f"field-ui:{data.supporterName}")
    return result


# =============================================================================
# API: ダッシュボード用データ
# =============================================================================

@app.get("/api/dashboard/summary")
async def api_dashboard_summary():
    """全クライアントの感情サマリー"""
    rows = run_query("""
        MATCH (c:Client)<-[:ABOUT]-(log:SupportLog)
        WHERE log.date >= date() - duration({days: 7})
          AND log.emotion IS NOT NULL
        WITH c.name AS clientName,
             count(log) AS totalLogs,
             count(CASE WHEN log.emotion IN ['Anger','Sadness','Fear','Disgust','Anxiety'] THEN 1 END) AS negativeLogs
        WHERE totalLogs >= 1
        RETURN clientName, totalLogs, negativeLogs
        ORDER BY toFloat(negativeLogs)/totalLogs DESC
    """)
    results = []
    for r in rows:
        total = r.get("totalLogs", 0)
        negative = r.get("negativeLogs", 0)
        results.append({
            "clientName": r["clientName"],
            "totalLogs": total,
            "negativeLogs": negative,
            "negativeRate": round(negative / total * 100, 1) if total > 0 else 0,
        })
    return results


@app.get("/api/dashboard/alerts/{client_name}")
async def api_dashboard_alerts(client_name: str):
    """特定クライアントのインサイト分析"""
    try:
        from lib.insight_engine import generate_risk_assessment
        result = generate_risk_assessment(client_name)
        return JSONResponse(content=json.loads(json.dumps(result, default=str)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/recent-logs/{client_name}")
async def api_recent_logs(client_name: str):
    """直近の支援記録"""
    rows = run_query("""
        MATCH (c:Client {name: $name})<-[:ABOUT]-(log:SupportLog)
        OPTIONAL MATCH (s:Supporter)-[:LOGGED]->(log)
        RETURN log.date AS date, log.situation AS situation,
               log.action AS action, log.emotion AS emotion,
               log.triggerTag AS triggerTag, log.effectiveness AS effectiveness,
               log.context AS context, s.name AS supporter
        ORDER BY log.date DESC
        LIMIT 20
    """, {"name": client_name})
    return [
        {k: str(v) if v is not None else "" for k, v in r.items()}
        for r in rows
    ]


# =============================================================================
# API: 音声アップロード → 構造化 → 登録
# =============================================================================

@app.post("/api/voice/upload")
async def api_voice_upload(
    audio: UploadFile = File(...),
    clientName: str = Form(...),
    supporterName: str = Form(""),
):
    """音声ファイルをアップロードし、文字起こし→構造化→登録"""
    # 一時ファイルに保存
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Step 1: 文字起こし
        from lib.embedding import transcribe_audio
        transcript = transcribe_audio(tmp_path)
        if not transcript:
            raise HTTPException(status_code=422, detail="音声の文字起こしに失敗しました")

        # Step 2: 構造化
        from scripts.multi_importer import structurize_with_gemini
        graph_data = structurize_with_gemini(
            text=transcript,
            client_name=clientName,
            supporter_name=supporterName or None,
            source_file=audio.filename or "voice_recording",
        )
        if not graph_data:
            raise HTTPException(status_code=422, detail="テキストの構造化に失敗しました")

        # Step 3: 登録
        result = register_to_database(
            graph_data,
            user_name=f"voice-ui:{supporterName or 'anonymous'}",
        )

        return {
            "status": result.get("status", "unknown"),
            "transcript": transcript[:500],
            "nodes_registered": result.get("count", result.get("registered_count", 0)),
        }
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
