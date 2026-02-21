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

1. **Neo4j の起動** — Docker コンテナでデータベースを立ち上げ
2. **Skills のインストール** — `claude-skills/` から `~/.claude/skills/` にシンボリックリンクを作成
3. **設定ガイダンスの表示** — 次に行うべきことを案内

> Neo4j のブラウザ UI は http://localhost:7474 でアクセスできます（認証: neo4j / password）

---

## ステップ 2: Claude Desktop の設定

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
    }
  }
}
```

> 既に他の MCP サーバーが設定されている場合は、`mcpServers` オブジェクト内に `"neo4j": {...}` を追加してください。

---

## ステップ 3: Claude Desktop の再起動

設定を保存した後、Claude Desktop を完全に終了して再起動します。

起動後、ツールアイコンに `neo4j` が表示されていれば成功です。

---

## 動作確認

Claude Desktop で以下のように話しかけてみましょう:

```
データベースの統計情報を教えて
```

初回は空のデータベースなので、データを登録してみましょう:

```
テスト用のクライアント「田中太郎」さんを登録して。
生年月日は1990年4月15日、血液型はA型。
```

---

## 2つのデータベースを使う場合

生活困窮者自立支援（livelihood-support）も使う場合は、`docker-compose.override.yml` を作成:

```yaml
services:
  neo4j-livelihood:
    image: neo4j:5.15-community
    container_name: livelihood-db-neo4j
    ports:
      - "7475:7474"
      - "7688:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_server_memory_pagecache_size=512M
      - NEO4J_server_memory_heap_initial__size=512M
      - NEO4J_server_memory_heap_max__size=512M
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - ./neo4j_livelihood_data:/data
      - ./neo4j_livelihood_logs:/logs
    restart: unless-stopped
```

Claude Desktop 設定に `neo4j-livelihood` MCP を追加:

```json
{
  "mcpServers": {
    "neo4j": { "..." : "..." },
    "neo4j-livelihood": {
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

---

## Skills の一覧

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
docker compose restart neo4j
```

---

## 次のステップ

- [ADVANCED_USAGE.md](./ADVANCED_USAGE.md) — Skills の詳細な使い方とプロンプト例
- [SCHEMA_CONVENTION.md](./SCHEMA_CONVENTION.md) — Neo4j 命名規則
- [Neo4j Browser](http://localhost:7474) — データの直接確認・操作
