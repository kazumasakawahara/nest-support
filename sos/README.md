# SOS 緊急通知サービス

知的障害のある方が緊急時にワンタップで支援者グループへSOSを発信するためのサービスです。

## 技術スタック

- **バックエンド**: FastAPI (Python)
- **通知**: LINE Messaging API（グループLINEへプッシュ通知）
- **データベース**: Neo4j（クライアント情報・キーパーソン・禁忌事項の取得）
- **フロントエンド**: PWA（スマートフォンのホーム画面に追加可能）

## セットアップ

1. 環境変数ファイルを作成

```bash
cp .env.example .env
```

2. `.env` を編集し、以下を設定
   - `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD`: Neo4j 接続情報
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
http://localhost:8000/app/?id=クライアント名
```

`クライアント名` には Neo4j に登録されているクライアントの名前、clientId、または displayCode を指定します。

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
  "client_id": "山田健太",
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

アプリ起動時にクライアント名を表示するために使用します。

## SOS メッセージの内容

送信されるメッセージには以下の情報が含まれます。

- クライアント名と発信時刻
- 位置情報（Google Maps リンク）
- キーパーソン（緊急連絡先）の名前・続柄・電話番号
- 禁忌事項（LifeThreatening / Panic レベルの注意点）
