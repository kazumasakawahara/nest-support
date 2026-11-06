"""
nest SOS - APIサーバー
知的障害のある方が緊急時にSOSを送信するためのAPIサーバー

機能:
- SOSリクエストを受信し、LINE Messaging APIでグループLINEに通知（NEXT-05 の歯止めを通す。文を作るのに DB を読まない）
- 本人の確認（GET /api/client/{displayCode}）：仮名だけで受け、読み取りの包み（nest.mcp_guard）を通して
  個人の側を読み、仮名と「いるか」だけを返す。名前は返さない。DB に直につながない（計画 N-36）
"""

import os
import re
import sys
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# 親ディレクトリをパスに追加（nest/ からインポートするため）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nest.auth import require_auth, set_session_cookie, verify_token
from nest import egress
from nest.ids import DISPLAY_ALPHABET

# 環境変数読み込み
load_dotenv()

# --- 設定 ---
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_GROUP_ID = os.getenv("LINE_GROUP_ID", "")

# CORS設定（カンマ区切りで複数指定可能、未設定時は無効=同一オリジンのみ）
# 例: "https://example.com,https://app.example.com"
# 変数名は field-ui と統一して CORS_ALLOW_ORIGINS。旧 CORS_ORIGINS も後方互換で読む。
CORS_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", os.getenv("CORS_ORIGINS", ""))

# --- FastAPI ---
app = FastAPI(
    title="nest SOS API",
    description="知的障害のある方向けの緊急通知システム",
    version="1.0.0"
)

# CORS設定（スマホアプリからのアクセスを許可）
# 既定は無効（同一オリジン運用・リバースプロキシ配下を想定）。クロスオリジンで使う
# 場合のみ CORS_ALLOW_ORIGINS にカンマ区切りで許可元を明示する。ワイルドカード '*' は
# allow_credentials=True と併用不可・資格情報漏洩面になるため使わない。
cors_origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip() and o.strip() != "*"]
if cors_origins:
    print(f"CORS許可オリジン: {cors_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    print("CORS_ALLOW_ORIGINS 未設定のため CORS を無効化（同一オリジンのみ許可）")


# --- リクエストモデル ---
class SOSRequest(BaseModel):
    client_id: str  # 仮名（displayCode）。仮名の形でなくても送る（緊急の導線は止めない）が、文には書かない
    latitude: float | None = None
    longitude: float | None = None
    accuracy: float | None = None


class SOSResponse(BaseModel):
    # 成否のみ返す。DB 由来の実名（client_name）は返さない。無認証の POST /api/sos に
    # 連番 displayCode を投げて実名を収集する「displayCode→実名オラクル」を防ぐため。
    # 本人確認表示が必要な場合は送信された識別子（入力値）をそのまま echo する。
    # 送信メッセージ全文（電話番号・禁忌等）や mock_mode も返さない（P0-3 / R2-1）。
    success: bool
    message: str
    received_id: str | None = None


# --- LINE Messaging API ---
_mock_mode = False

async def send_line_message(message: str) -> bool:
    """LINE Messaging APIでメッセージ送信（モック対応）"""
    global _mock_mode
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    group_id = os.getenv("LINE_GROUP_ID")

    if not token or token == "YOUR_ACCESS_TOKEN" or not group_id:
        _mock_mode = True
        print("\n[模擬送信モード] LINE認証情報が未設定のためモック送信します")
        print(f"[模擬送信] 送信先グループ: {group_id or '未設定'}")
        print(f"[模擬送信] メッセージ内容:\n{'='*40}\n{message}\n{'='*40}")
        return True

    _mock_mode = False
    url = "https://api.line.me/v2/bot/message/push"
    # 送信の歯止め（N-02・external-api NEXT-05）。鍵があっても、機能の設定と契約の確認の記録が
    # そろわなければ送らない。
    try:
        egress.ensure("NEXT-05", url)
    except egress.EgressDenied as e:
        print(f"LINE送信を止めました（NEXT-05 不許可）: {e}")
        return False
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "to": group_id,
        "messages": [{"type": "text", "text": message}]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                print("LINE送信成功")
                return True
            else:
                print(f"LINE送信失敗: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        print(f"LINE送信エラー: {e}")
        return False


# --- SOSメッセージ作成 ---
# N-28（ADR-001 D11-3、external-api NEXT-05）：LINE に送るのは SOS・誰のことか（仮名）・位置・確かめる先だけ。
# 電話・禁忌・実名・キーパーソンの名前は送らない。文を作るのに DB を読まない。
DISPLAY_CODE = re.compile(r"C-[%s]{6}" % DISPLAY_ALPHABET)
CONFIRM_LINE = "📇 連絡先と注意することは、手元の緊急連絡カードと SOS の画面で確かめてください"


def create_sos_message(
    code: str,
    latitude: float | None = None,
    longitude: float | None = None,
    accuracy: float | None = None,
) -> str:
    """SOS の文。誰のことかは仮名（displayCode）の形のときだけ書く"""
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    who = code if isinstance(code, str) and DISPLAY_CODE.fullmatch(code) else "（仮名の形でない ID のため書かない）"
    message = f"🆘【緊急SOS】\n\n対象: {who}\n⏰ 発信時刻: {now}\n"
    if latitude is not None and longitude is not None:
        acc_text = f"（精度: 約{int(accuracy)}m）" if accuracy else ""
        message += f"\n📍 現在地:\nhttps://www.google.com/maps?q={latitude},{longitude}\n{acc_text}\n"
    else:
        message += "\n📍 位置: 取得できませんでした\n"
    message += "\n" + CONFIRM_LINE + "\n"
    return message


# --- エンドポイント ---
@app.get("/")
async def root():
    """ヘルスチェック"""
    return {"status": "ok", "service": "nest SOS API"}


@app.post("/api/sos", response_model=SOSResponse)
async def receive_sos(request: SOSRequest):
    """
    SOSリクエストを受信し、LINEグループに通知
    """
    message = create_sos_message(
        request.client_id,
        latitude=request.latitude,
        longitude=request.longitude,
        accuracy=request.accuracy,
    )
    # 登録の有無で文の形も応答も変えない（登録有無オラクル封じ）。DB は読まない
    if await send_line_message(message):
        return SOSResponse(
            success=True,
            message="SOSを送信しました",
            received_id=request.client_id,
        )
    raise HTTPException(
        status_code=500,
        detail="LINE送信に失敗しました"
    )


class LoginInput(BaseModel):
    token: str


@app.post("/api/login")
async def login(data: LoginInput, response: Response):
    """セッション Cookie を発行する（情報取得エンドポイント用）。"""
    if not verify_token(data.token):
        raise HTTPException(status_code=401, detail="トークンが正しくありません")
    set_session_cookie(response, data.token)
    return {"status": "ok"}


@app.get("/api/client/{client_id}")
async def get_client(client_id: str, user: str = Depends(require_auth)):
    """
    本人の確認（アプリ起動時）。認証必須（非対称設計：SOS 送信は無認証）。
    仮名（displayCode）だけで受け、仮名と「いるか」だけを返す。名前は返さない（計画 N-36、台帳 G-66）。
    """
    if not DISPLAY_CODE.fullmatch(client_id):
        raise HTTPException(status_code=400, detail="仮名（C-で始まる 8 文字）で指定してください")
    try:
        found = lookup_client(client_id)
    except Exception:
        # 包みが読まない（NEXT-02 の歯止めがそろわない）・DB が止まっている。中身は返さない
        raise HTTPException(status_code=503, detail="いまは本人の確認ができません（SOS の送信はできます）")
    return {"displayCode": client_id, "found": found}


def lookup_client(code: str) -> bool:
    """個人の側に、その仮名の本人がいるか。読み取りの包み（nest.mcp_guard）を通して読む"""
    from nest import connections, mcp_guard
    with connections.driver("personal") as d:
        mcp_guard.require_personal_allowed(d)
        rows = mcp_guard.run_read(d, "MATCH (c:Client {displayCode: $code}) RETURN count(c) AS n", {"code": code},
                                  personal=True)
    return bool(rows and rows[0]["n"])


# --- 静的ファイル配信（スマホアプリ） ---
# appフォルダが存在する場合、静的ファイルとして配信
import os.path
app_dir = os.path.join(os.path.dirname(__file__), "app")
if os.path.exists(app_dir):
    app.mount("/app", StaticFiles(directory=app_dir, html=True), name="app")


# --- 起動 ---
if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("nest SOS API サーバー")
    print("=" * 50)
    print(f"LINE設定: {'設定済み' if LINE_CHANNEL_ACCESS_TOKEN else '未設定'}")
    print("=" * 50)
    print("アプリURL: http://localhost:8000/app/?id=仮名（C-……）")
    print("API URL: http://localhost:8000/api/sos")
    print("=" * 50)

    # 既定は 127.0.0.1（TLS・レート制限はリバースプロキシに委譲）。
    uvicorn.run(
        app,
        host=os.getenv("BIND_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )
