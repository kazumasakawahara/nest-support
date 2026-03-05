# クイックスタートガイド

5分で始められるセットアップ手順です。

---

## 前提条件

| ツール | 必須 | 用途 |
|-------|------|------|
| Docker Desktop | ○ | Neo4j データベース |
| Claude Desktop | ○ | AI 分析・操作 |
| Node.js (npx) | ○ | Neo4j MCP サーバー |

---

## ステップ 1: セットアップの実行

```bash
cd nest-support
chmod +x setup.sh
./setup.sh
```

このスクリプトが以下を実行します:

1. **Neo4j の起動** — Docker コンテナで2つのデータベースを立ち上げ
2. **Skills のインストール** — `claude-skills/` から `~/.claude/skills/` にシンボリックリンクを作成
3. **設定ガイダンスの表示** — 次に行うべきことを案内

> Neo4j のブラウザ UI は http://localhost:7474 でアクセスできます（認証: neo4j / password）

### ワンクリックインストーラー（推奨）

前提条件のインストールも含めて自動化したい場合は:

```bash
chmod +x installer/install-mac.sh
./installer/install-mac.sh
```

---

## ステップ 2: Claude Desktop の設定

### 自動設定（推奨）

```bash
chmod +x installer/configure-claude.sh
./installer/configure-claude.sh
```

### 手動設定

Claude Desktop の設定ファイルを開きます:

**Mac:**
```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

以下の内容を追加（または `configs/claude_desktop_config.json` からコピー）:

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "npx",
      "args": ["-y", "@anthropic/neo4j-mcp-server"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password"
      }
    },
    "livelihood-support-db": {
      "command": "npx",
      "args": ["-y", "@anthropic/neo4j-mcp-server"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7688",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password"
      }
    }
  }
}
```

> 既に他の MCP サーバーが設定されている場合は、`mcpServers` オブジェクト内に追加してください。

---

## ステップ 3: Claude Desktop の再起動

設定を保存した後、Claude Desktop を完全に終了して再起動します。

起動後、ツールアイコンに `neo4j` が表示されていれば成功です。

---

## ステップ 4: デモデータの投入（オプション）

動作確認やデモ用に、匿名化された架空データを投入できます:

```bash
chmod +x installer/load-demo-data.sh
./installer/load-demo-data.sh
```

デモデータの削除:
```bash
./installer/load-demo-data.sh --remove
```

---

## 動作確認

Claude Desktop で以下のように話しかけてみましょう:

```
データベースの統計情報を教えて
```

デモデータ投入済みの場合:

```
山本翔太さんのプロフィールを見せて
鈴木花さんの禁忌事項を教えて
```

初めてクライアントを登録する場合:

```
新しいクライアントを登録したい
```

→ `onboarding-wizard` スキルが対話的に案内します。

---

## 2つのデータベースについて

nest-support は2つのNeo4jインスタンスで構成されています:

| インスタンス | Bolt | ブラウザUI | 用途 |
|------------|------|-----------|------|
| support-db | localhost:7687 | http://localhost:7474 | 障害福祉クライアント管理 |
| livelihood-support | localhost:7688 | http://localhost:7475 | 生活困窮者自立支援 |

`docker-compose.yml` で両方が自動起動されます。

---

## Skills の一覧（13スキル）

| Skill | 用途 | Neo4j Port |
|-------|------|------------|
| `neo4j-support-db` | 障害福祉クライアント管理 | 7687 |
| `livelihood-support` | 生活困窮者自立支援 | 7688 |
| `provider-search` | 事業所検索・口コミ | 7687 |
| `emergency-protocol` | 緊急時対応プロトコル | — |
| `ecomap-generator` | エコマップ生成 | — |
| `html-to-pdf` | HTML → PDF 変換 | — |
| `inheritance-calculator` | 法定相続計算 | — |
| `wamnet-provider-sync` | WAM NET データ同期 | 7687 |
| `narrative-extractor` | テキスト → 構造化データ抽出 | 7687 |
| `data-quality-agent` | データ品質チェック・検証 | 7687 |
| `onboarding-wizard` | 新規クライアント登録ウィザード | 7687 |
| `resilience-checker` | 親亡き後レジリエンス診断 | 7687 |
| `visit-prep` | 訪問準備ブリーフィング | 7687 |

---

## トラブルシューティング

### Skills が認識されない
```bash
ls -la ~/.claude/skills/
./setup.sh --skills  # 再インストール
```

### Neo4j に接続できない
```bash
docker ps | grep neo4j
curl -s http://localhost:7474
docker compose restart
```

### Claude Desktop で MCP が表示されない
```bash
# 設定ファイルの内容を確認
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
# 自動設定ツールで修復
./installer/configure-claude.sh
```

詳しくは [FAQ.md](./FAQ.md) を参照してください。

---

## 次のステップ

- [SETUP_GUIDE.md](./SETUP_GUIDE.md) — 初めての方向けの詳細セットアップガイド
- [ADVANCED_USAGE.md](./ADVANCED_USAGE.md) — Skills の詳細な使い方とプロンプト例
- [SCHEMA_CONVENTION.md](./SCHEMA_CONVENTION.md) — Neo4j 命名規則
- [FAQ.md](./FAQ.md) — よくある質問とトラブルシューティング
- [Neo4j Browser](http://localhost:7474) — データの直接確認・操作
