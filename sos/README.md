# SOS 緊急通知サービス

知的障害のある方が緊急時にワンタップで支援者グループへSOSを発信するためのサービスです。

## 技術スタック

- **バックエンド**: FastAPI (Python)
- **通知**: LINE Messaging API（グループLINEへプッシュ通知）
- **データベース**: 個人の側の Neo4j を、読み取りの包み（`nest.mcp_guard`）を通して読むだけ（本人の確認。仮名と「いるか」だけ）。SOS の文を作るのに DB は読まない
- **フロントエンド**: PWA（スマートフォンのホーム画面に追加可能）

## セットアップ

1. 環境変数ファイルを作成

```bash
cp .env.example .env
```

2. `.env` を編集し、以下を設定（DB の接続は `~/.config/nest/neo4j-redesign.env` を `nest.connections` が読む。sos の `.env` には書かない）
   - `LINE_CHANNEL_ACCESS_TOKEN`: LINE Messaging API のチャネルアクセストークン
   - `LINE_GROUP_ID`: 通知先の LINE グループID

LINE の認証情報が未設定の場合、自動的にモック送信モード（コンソール出力のみ）で動作します。

## 起動方法

```bash
cd sos
uv run python api_server.py
```

サーバーはポート 8000 で起動します。

## 使い方

### PWA アプリ（利用者向け）

ブラウザで以下の URL を開き、ホーム画面に追加します。

```
http://localhost:8000/app/?id=C-ZZZZZZ
```

`id` には仮名（`displayCode`、C-で始まる 8 文字）を指定します。名前では指定しません（URL や記録に名前が残らないように。計画 N-36）。画面に出すのも仮名だけです。

### API エンドポイント

**ヘルスチェック**

```
GET /
```

**SOS 送信**

```
POST /api/sos
Content-Type: application/json

{
  "client_id": "C-ZZZZZZ",
  "latitude": 35.6812,
  "longitude": 139.7671,
  "accuracy": 15.0
}
```

`latitude`、`longitude`、`accuracy` は省略可能です。PWA アプリが端末の位置情報を自動取得して送信します。

**クライアント情報取得**

```
GET /api/client/{client_id}
```

認証が要ります。仮名（`displayCode`）だけで受け、`{"displayCode": "C-ZZZZZZ", "found": true}` のように仮名と「いるか」だけを返します。名前は返しません（計画 N-36、台帳 G-66）。

- 仮名の形でなければ 400（DB を読まない）
- 読み取りの包みが読まない（NEXT-02 の歯止めがそろわない）・DB が止まっているときは 503
- アプリはこの入口を使いません。SOS の送信は、この入口の結果に関わらずできます

## SOS メッセージの内容

送るのは次だけです（計画 N-28、`docs/external-api.md` NEXT-05。LINE は既定で使いません）。

- SOS があったこと、誰のことか（仮名 `displayCode` の形のときだけ）、発信の時刻
- 位置（Google マップのリンク）
- 確かめる先：「連絡先と注意することは、手元の緊急連絡カードと SOS の画面で確かめてください」

電話・禁忌・実名・キーパーソンの名前は送りません。文を作るのに DB を読みません。
