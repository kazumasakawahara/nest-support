# 発展的運用ガイド: Claude + Skills との連携

---

## アーキテクチャ概要

```
ユーザー → Claude Desktop / Claude Code → Skills（SKILL.md）→ Neo4j MCP → Neo4j DB
```

Claude が SKILL.md に含まれるCypherテンプレートを参照し、汎用 Neo4j MCP の `read_neo4j_cypher` / `write_neo4j_cypher` ツールでクエリを実行します。

---

## 9つの Skills

### 1. neo4j-support-db（障害福祉）

**対象**: 知的障害・精神障害のある方の支援情報管理

**プロンプト例:**
```
山田健太さんのプロフィールを表示して
更新期限が近い証明書を全クライアント分チェックして
佐藤さんの最近の支援記録を分析して、効果的だったケアパターンを教えて
```

### 2. livelihood-support（生活困窮者支援）

**対象**: 生活保護受給者の尊厳を守る支援情報管理
**ポート**: `bolt://localhost:7688`

**プロンプト例:**
```
田中さんの訪問前ブリーフィングをお願いします
山田さんの引き継ぎサマリーを作成して
佐藤さんと類似したリスクを持つ過去のケースを検索して
```

### 3. provider-search（事業所検索）

**プロンプト例:**
```
北九州市の生活介護事業所で空きのあるところを探して
行動障害対応の評価が高い事業所を教えて
山田さんの就労B型の代替事業所を探して
```

### 4. emergency-protocol（緊急時対応）

**Safety First プロトコル:**
1. NgAction（禁忌事項）→ 2. CarePreference → 3. KeyPerson → 4. Hospital → 5. Guardian

**プロンプト例:**
```
田中さんがパニックを起こしています。緊急対応情報をください。
山田さんの緊急連絡先を教えて
```

### 5. ecomap-generator（エコマップ生成）

**プロンプト例:**
```
田中太郎さんのエコマップを作成して
佐藤さんの緊急時体制のエコマップをMermaid形式で表示して
```

### 6. narrative-extractor（テキスト → 構造化データ）

**プロンプト例:**
```
以下の文章からクライアント情報を抽出してデータベースに登録してください。
[テキストまたはファイル添付]
```

### 7. html-to-pdf

**プロンプト例:**
```
このHTMLファイルをPDFに変換して
```

### 8. inheritance-calculator

**プロンプト例:**
```
配偶者と子供2人がいる場合の法定相続分を計算して
```

### 9. wamnet-provider-sync

**プロンプト例:**
```
WAM NETから最新の事業所データを取得して同期して
```

---

## Skills の選択ガイド

| やりたいこと | 使うSkill |
|-------------|----------|
| クライアントの情報確認 | `neo4j-support-db` |
| テキストからの情報抽出・登録 | `narrative-extractor` |
| 支援記録の追加・分析 | `neo4j-support-db` |
| 訪問前の準備 | `livelihood-support` |
| 引き継ぎ資料の作成 | `livelihood-support` |
| 事業所の検索・比較 | `provider-search` |
| 緊急時の即時対応 | `emergency-protocol` |
| 支援関係の可視化 | `ecomap-generator` |
| 証明書の期限管理 | `neo4j-support-db` |
| 口コミの参照・登録 | `provider-search` |

---

## Skills のカスタマイズ

### SKILL.md の編集

Skills は `~/.claude/skills/` にシンボリックリンクされているため、`claude-skills/` ディレクトリの SKILL.md を直接編集できます。

```bash
vim claude-skills/neo4j-support-db/SKILL.md
```

### 新しい Skill の追加

1. `claude-skills/` に新しいディレクトリを作成
2. `SKILL.md` を作成（既存のSkillを参考に）
3. `setup.sh` の `SKILLS` 配列に追加
4. `./setup.sh --skills` を再実行

---

## トラブルシューティング

### Skills が認識されない
```bash
ls -la ~/.claude/skills/
./setup.sh --skills  # 再インストール
```

### Neo4j MCP に接続できない
```bash
docker ps | grep neo4j
curl -s http://localhost:7474
npx -y @anthropic/neo4j-mcp-server --help
```

### Cypher クエリがエラーになる
1. Neo4j Browser (http://localhost:7474) で直接クエリを実行して確認
2. SKILL.md 内のテンプレートとスキーマが一致しているか確認
3. APOC プラグインが有効か確認: `RETURN apoc.version()`
