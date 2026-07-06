# 認証・ログイン導線 手動検証記録（R2-5 / 2026-07-06）

Round 2 R2-5 の完了条件「ローカルで `APP_ACCESS_TOKEN` を設定して起動し、ログイン→記録フォーム送信→ダッシュボード表示の一連を手動確認」の記録。

## 手順

field-ui を認証つきで起動（HTTP 検証のため Cookie Secure=false）:

```bash
APP_ACCESS_TOKEN="verify-token-xyz" SESSION_COOKIE_SECURE="false" \
  BIND_HOST="127.0.0.1" PORT="8011" uv run python field-ui/server.py
```

## 結果（すべて期待どおり）

| # | 検証 | 期待 | 実際 |
|---|------|------|------|
| 1 | 未認証で `GET /api/clients` | 401 | ✅ 401 |
| 2 | `GET /login`（ログインページ配信） | 200 | ✅ 200 |
| 3 | 誤トークンで `POST /api/login` | 401 | ✅ 401 |
| 4 | 正トークンで `POST /api/login` | 200 + `nest_session` Cookie 発行 | ✅ 200 / Cookie 発行 |
| 5 | Cookie 付きで `GET /api/clients` | 200（一覧取得） | ✅ 200 |
| 6 | Cookie 付きで `GET /api/dashboard/summary` | 200 | ✅ 200 |
| 7 | 未認証で `POST /api/support-log` | 401 | ✅ 401 |
| 8 | Cookie 付き・未存在クライアントで `POST /api/support-log` | 404（認証通過＋ゴーストガード、実データ非書込） | ✅ 404 |

実データ（既存クライアント）への書き込みは検証で行っていない（8 は未存在名で 404 を確認し、実 SupportLog は作成していない）。

## 実装（R2-5）

- `field-ui/static/login.html`（新規）: 合言葉入力→`/api/login`→セッション Cookie 取得→`next` へ戻る（オープンリダイレクト防止つき）。
- `field-ui/server.py`: `GET /login` ルート追加。
- `dashboard.html` / `record-form.html` / `voice-recorder.html`: `window.fetch` をラップし、401 応答時に `/login?next=...` へ誘導。
- `sos/app/index.html`: 起動時のクライアント確認（認証必須 API）が 401/失敗でも SOS 送信 UI を止めないよう `response.ok` 判定を追加（緊急導線を殺さない）。SOS 画面にはログイン誘導ラッパーを入れていない。
