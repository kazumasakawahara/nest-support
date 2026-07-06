"""
アプリ内認証（field-ui / sos 共通）

デプロイ前提: アプリは 127.0.0.1 にバインドし、TLS・レート制限・（必要なら）
Basic 認証はリバースプロキシに委譲する（判断ポイント: 127.0.0.1+リバースプロキシ）。
本モジュールは、その内側での多層防御として共有シークレット（APP_ACCESS_TOKEN）
による認証を提供する。

- 認証は `Authorization: Bearer <token>` ヘッダ、または `/api/login` が発行する
  HttpOnly / SameSite=Strict セッション Cookie で行う。
- APP_ACCESS_TOKEN 未設定時は fail-closed（保護エンドポイントは 503）。
- 認証済みユーザー名は、既定では "authenticated"。信頼できるリバースプロキシが
  `X-Authenticated-User` を付与する構成でのみ、`TRUST_PROXY_HEADERS=true` を
  設定するとそのヘッダを採用する。既定で信頼しないのは、トークン保持者が任意の
  操作者名を監査ログに刻める（監査証跡のなりすまし）のを防ぐため。
"""

import hmac
import os

from fastapi import HTTPException, Request, Response

APP_ACCESS_TOKEN_ENV = "APP_ACCESS_TOKEN"
SESSION_COOKIE = "nest_session"
# Cookie の Secure 属性。HTTPS 前提の本番では true。ローカル HTTP 検証時のみ false。
_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"


def _trust_proxy_headers() -> bool:
    """X-Authenticated-User を信頼するか（既定 false）。

    信頼できるリバースプロキシが外部由来のヘッダを剥がして付与する構成でのみ
    true にする。false のときはクライアント提示のヘッダを一切採用しない。
    """
    return os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true"


def _configured_token() -> str:
    return os.getenv(APP_ACCESS_TOKEN_ENV, "")


def _presented_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(SESSION_COOKIE, "")


def verify_token(token: str) -> bool:
    """提示トークンが設定値と一致するか（定数時間比較）。未設定時は常に False。"""
    configured = _configured_token()
    if not configured or not token:
        return False
    return hmac.compare_digest(token, configured)


def require_auth(request: Request) -> str:
    """認証を要求する FastAPI 依存関数。

    Returns:
        認証済みユーザー識別子。既定では "authenticated"。TRUST_PROXY_HEADERS=true
        のときのみ X-Authenticated-User ヘッダを採用する。監査ログの操作者名に使う。

    Raises:
        HTTPException 503: APP_ACCESS_TOKEN 未設定（fail-closed）
        HTTPException 401: トークン不一致・未提示
    """
    if not _configured_token():
        raise HTTPException(
            status_code=503,
            detail="認証が未設定です（APP_ACCESS_TOKEN を設定してください）",
        )
    if not verify_token(_presented_token(request)):
        raise HTTPException(status_code=401, detail="認証が必要です")
    # 既定ではプロキシヘッダを信頼しない（なりすまし防止）。
    if _trust_proxy_headers():
        return request.headers.get("x-authenticated-user") or "authenticated"
    return "authenticated"


def set_session_cookie(response: Response, token: str) -> None:
    """ログイン成功時に HttpOnly / SameSite=Strict セッション Cookie を発行する。"""
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="strict",
        secure=_COOKIE_SECURE,
        max_age=60 * 60 * 12,  # 12 時間
    )
