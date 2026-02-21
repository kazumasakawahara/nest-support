# CLAUDE.md

This file provides guidance to Claude Code / Claude Desktop when working with this project.

## Project Overview

**nest-support: Claude-Native 親亡き後支援データベース**

Neo4j グラフデータベースに蓄積された障害福祉支援情報を、**Claude Desktop / Claude Code + Skills + Neo4j MCP** のみで運用するシステム。Streamlit UI や Gemini API への依存を完全に排除した Single Layer アーキテクチャ。

### Core Manifesto (5 Values + 7 Pillars)

**5 Values:**
1. **Dignity (尊厳)**: 管理対象としてではなく、歴史と意思を持つ一人の人間として記録する
2. **Safety (安全)**: 緊急時に「誰が」「何を」すべきか、迷わせない構造を作る
3. **Continuity (継続性)**: 支援者が入れ替わっても、ケアの質と文脈を断絶させない
4. **Resilience (強靭性)**: 親が倒れた際、その機能を即座に代替できるバックアップ体制を可視化する
5. **Advocacy (権利擁護)**: 本人の声なき声を拾い上げ、法的な後ろ盾と紐づける

**7 Data Pillars:**
1. Identity & Narrative (本人性)
2. Care Instructions (ケアの暗黙知)
3. Safety Net (危機管理ネットワーク)
4. Legal Basis (法的基盤)
5. Parental Transition (親の機能移行)
6. Financial Safety (金銭的安全)
7. Multi-Agency Collaboration (多機関連携)

See `manifesto/MANIFESTO.md` for the complete v4.0 manifesto.

---

## Architecture

### Single Layer Design

```
ユーザー → Claude Desktop / Claude Code → Skills (SKILL.md) → Neo4j MCP → Neo4j DB
```

Claude が SKILL.md に含まれる Cypher テンプレートを参照し、汎用 Neo4j MCP の `read_neo4j_cypher` / `write_neo4j_cypher` ツールでクエリを実行する。

### System Components

1. **Skills** (`claude-skills/` → `~/.claude/skills/` via symlink): Cypher テンプレート集
2. **SOS Service** (`sos/`): FastAPI + LINE Messaging API による緊急通知（独立サービス）
3. **Shared Libraries** (`lib/`): Neo4j 接続、ユーティリティ（SOS サービスから使用）
4. **Manifesto** (`manifesto/`): 理念・プロトコル・ワークフロー

### External Services

- **Neo4j 5.15+** (via Docker): グラフデータベース
- **LINE Messaging API**: SOS 緊急通知
- **Neo4j MCP** (`@anthropic/neo4j-mcp-server`): Claude ↔ Neo4j 接続

---

## Skills 一覧と使い分けガイド

### 9 Skills

| Skill | 対象業務 | Neo4j Port | Templates |
|-------|----------|-----------|-----------|
| `neo4j-support-db` | 障害福祉クライアント管理 | 7687 | 8 read |
| `livelihood-support` | 生活困窮者自立支援 | 7688 | 12 read |
| `provider-search` | 事業所検索・口コミ管理 | 7687 | 6 read + 3 write |
| `emergency-protocol` | 緊急時対応プロトコル | N/A | N/A |
| `ecomap-generator` | エコマップ（支援関係図）生成 | N/A | N/A |
| `html-to-pdf` | HTML → PDF 変換 | N/A | N/A |
| `inheritance-calculator` | 法定相続計算 | N/A | N/A |
| `wamnet-provider-sync` | WAM NET 事業所データ同期 | 7687 | write |
| `narrative-extractor` | テキスト → 構造化データ抽出 | 7687 | write |

### ルーティング判断フロー

```
ユーザー入力
│
├─ 緊急ワード？（パニック、SOS、倒れた、救急）
│  └─ YES → emergency-protocol → 必要に応じて neo4j-support-db
│
├─ テキスト/ファイルからの情報抽出・登録？
│  └─ YES → narrative-extractor
│
├─ クライアント名が含まれる？
│  └─ YES → neo4j-support-db（port 7687）
│
├─ 受給者名＋経済リスク・金銭管理の話題？
│  └─ YES → livelihood-support（port 7688）
│
├─ 事業所検索・口コミの話題？
│  └─ YES → provider-search
│
├─ 訪問前ブリーフィング・引き継ぎ？
│  └─ YES → livelihood-support
│
├─ エコマップ・ネットワーク図？
│  └─ YES → ecomap-generator
│
├─ WAM NET データ同期？
│  └─ YES → wamnet-provider-sync
│
├─ 相続計算？
│  └─ YES → inheritance-calculator
│
└─ 一般的な Neo4j 操作？
   └─ YES → neo4j MCP を直接使用
```

### Neo4j インスタンスの使い分け

| インスタンス | Bolt | HTTP | 対象スキル |
|------------|------|------|-----------|
| support-db | localhost:7687 | localhost:7474 | neo4j-support-db, provider-search, narrative-extractor |
| livelihood-support | localhost:7688 | localhost:7475 | livelihood-support |

**`neo4j` MCP のデフォルト接続先は port 7687。** livelihood-support のクエリは `neo4j-livelihood` MCP（port 7688）を使用すること。

---

## Neo4j スキーマ規則

> **このセクションは命名規則の Single Source of Truth です。** 詳細は `docs/SCHEMA_CONVENTION.md` を参照。

### 命名規則

| 対象 | 規則 | 例 |
|------|------|-----|
| ノードラベル | PascalCase | `Client`, `NgAction`, `CarePreference` |
| リレーション | UPPER_SNAKE_CASE | `MUST_AVOID`, `HAS_KEY_PERSON` |
| プロパティ | camelCase | `riskLevel`, `nextRenewalDate` |
| 列挙値 | PascalCase (英語) | `LifeThreatening`, `Panic`, `Active` |

### 主要ノードラベル（障害福祉 port 7687）

`Client`, `Condition`, `NgAction`, `CarePreference`, `KeyPerson`, `Guardian`, `Hospital`, `Certificate`, `PublicAssistance`, `Organization`, `Supporter`, `SupportLog`, `AuditLog`, `LifeHistory`, `Wish`, `Identity`, `ServiceProvider`, `ProviderFeedback`

### 主要リレーション

```cypher
(:Client)-[:HAS_CONDITION]->(:Condition)
(:Client)-[:MUST_AVOID]->(:NgAction)-[:IN_CONTEXT]->(:Condition)
(:Client)-[:REQUIRES]->(:CarePreference)
(:Client)-[:HAS_KEY_PERSON {rank: 1}]->(:KeyPerson)
(:Client)-[:HAS_LEGAL_REP]->(:Guardian)
(:Client)-[:HAS_CERTIFICATE]->(:Certificate)
(:Client)-[:TREATED_AT]->(:Hospital)
(:Supporter)-[:LOGGED]->(:SupportLog)-[:ABOUT]->(:Client)
(:Client)-[:HAS_HISTORY]->(:LifeHistory)
(:Client)-[:HAS_WISH]->(:Wish)
(:Client)-[:USES_SERVICE]->(:ServiceProvider)
```

### 廃止されたリレーション名（書き込み禁止）

| 廃止名 | 正式名 |
|--------|--------|
| ~~`PROHIBITED`~~ | `MUST_AVOID` |
| ~~`PREFERS`~~ | `REQUIRES` |
| ~~`EMERGENCY_CONTACT`~~ | `HAS_KEY_PERSON` |
| ~~`RELATES_TO`~~ | `IN_CONTEXT` |
| ~~`HAS_GUARDIAN`~~ | `HAS_LEGAL_REP` |

**読み取りクエリ** では旧名との後方互換性を `[:NEW|OLD]` 構文で確保すること。
**書き込みクエリ** では正式名のみを使用すること。

### riskLevel 列挙値

| 値 | 意味 |
|---|---|
| `LifeThreatening` | 生命に関わる（アレルギー、誤嚥リスク等） |
| `Panic` | パニック誘発（大きな音、特定の状況等） |
| `Discomfort` | 不快・ストレス（嫌がる行為、苦手な環境等） |

---

## Emergency Information Priority

**NgAction (禁忌事項)** ノードは安全に関わる最重要データ。緊急時は以下の順で情報を提示：

1. 🔴 NgAction（禁忌事項）— LifeThreatening → Panic → Discomfort
2. 🟡 CarePreference（推奨ケア）
3. 🟢 KeyPerson（緊急連絡先）— rank 順
4. 🏥 Hospital（かかりつけ医）
5. 👤 Guardian（後見人）

---

## Protocols & Workflows

### プロトコル（判断と行動のルール）

| ファイル | 内容 | トリガー |
|---------|------|---------|
| `manifesto/protocols/emergency.md` | 緊急時対応 | パニック、事故、急病、SOS |
| `manifesto/protocols/parent_down.md` | 親の機能不全 | 親の入院、死亡、認知症 |
| `manifesto/protocols/onboarding.md` | 新規クライアント登録 | 新規相談、初回面接 |
| `manifesto/protocols/handover.md` | 担当者引き継ぎ | 異動、退職、担当変更 |

### ワークフロー（業務手順の定型化）

| ファイル | 内容 | 使用場面 |
|---------|------|---------|
| `manifesto/workflows/visit_preparation.md` | 訪問前ブリーフィング | 訪問・同行支援の前日〜当日 |
| `manifesto/workflows/resilience_report.md` | レジリエンス・レポート | 支援計画の策定・見直し |
| `manifesto/workflows/renewal_check.md` | 更新期限チェック | 月次業務、期限管理 |

---

## Setup

```bash
# 1. セットアップスクリプト実行
chmod +x setup.sh
./setup.sh

# 2. Claude Desktop 設定
# configs/claude_desktop_config.json を参照して Neo4j MCP を追加

# 3. SOS サービス（必要な場合）
cd sos && cp .env.example .env && uv run python api_server.py
```

See `docs/QUICK_START.md` for detailed setup instructions.

---

## File Organization

```
nest-support/
├── CLAUDE.md                      # このファイル
├── docker-compose.yml             # Neo4j (port 7687)
├── pyproject.toml                 # 最小依存
├── .env.example                   # 環境変数テンプレート
├── .python-version                # 3.12
├── setup.sh                       # Neo4j起動 + Skills symlink
├── manifesto/                     # 理念・プロトコル・ワークフロー
│   ├── MANIFESTO.md
│   ├── protocols/                 # emergency, parent_down, onboarding, handover
│   └── workflows/                 # visit_preparation, resilience_report, renewal_check
├── lib/                           # 共有Python (SOS用)
│   ├── db_operations.py           # Neo4j接続・クエリ実行・CRUD
│   └── utils.py                   # 日付パース等ユーティリティ
├── claude-skills/                 # Skills (→ ~/.claude/skills/ へ symlink)
│   ├── neo4j-support-db/
│   ├── livelihood-support/
│   ├── provider-search/
│   ├── emergency-protocol/
│   ├── ecomap-generator/
│   ├── html-to-pdf/
│   ├── inheritance-calculator/
│   ├── wamnet-provider-sync/
│   └── narrative-extractor/       # テキスト→構造化データ抽出
├── sos/                           # SOS緊急通知サービス
│   ├── api_server.py              # FastAPI + LINE
│   ├── app/                       # PWA frontend
│   ├── .env.example
│   └── README.md
├── scripts/                       # ユーティリティ
│   └── backup.sh
├── configs/                       # Claude Desktop設定テンプレート
│   └── claude_desktop_config.json
└── docs/                          # ドキュメント
    ├── QUICK_START.md
    ├── SCHEMA_CONVENTION.md
    └── ADVANCED_USAGE.md
```

## Important Constraints

### Data Integrity
- **Never fabricate data**: AI extraction must not infer missing information
- **Prohibition priority**: NgAction nodes are safety-critical, treat with highest importance
- **Date validation**: Use `lib/utils.py::safe_date_parse()` for all date inputs

### Neo4j Query Patterns
- Use `MERGE` for idempotent client/node creation
- Always use parameterized queries (`$param`) to prevent Cypher injection
- Handle optional fields with `COALESCE()` or `CASE WHEN ... ELSE ... END`
- Check existence before creating relationships to avoid duplicates
- 読み取りクエリでは旧名との後方互換性を `[:NEW|OLD]` 構文で確保する

### Development Context
This system was developed by a lawyer working with NPOs supporting families of children with intellectual disabilities. The design prioritizes **real-world emergency scenarios** where staff need immediate access to critical care information when primary caregivers are unavailable.

**Design Philosophy**: Preserve parental tacit knowledge in structured format, queryable in natural language during crisis situations.
