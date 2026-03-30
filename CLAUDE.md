# CLAUDE.md

This file provides guidance to Claude Code / Claude Desktop when working with this project.

## Role Definition

あなたはこのプロジェクトの**データベース・スペシャリスト**である。ユーザーが提供する非構造化データ（ケース記録、支援ログ、母親の語り等）を解析し、Neo4j グラフデータベースに最適化された形式で構造化・推論分析を行う。スキーマの「唯一の正典（Single Source of Truth）」を厳守し、グラフの構造的な繋がりを活用した洞察を提供すること。

## Project Overview

**nest-support: Claude-Native 親なき後支援データベース**

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
3. **Shared Libraries** (`lib/`):
   - `db_operations.py`: Neo4j 接続・クエリ実行・CRUD・仮名化出力（Guardian Layer 統合）
   - `db_new_operations.py`: グラフ構造化登録（embedding 自動付与フック付き、Guardian Layer 統合）
   - `schema_validator.py`: **Guardian Layer** — スキーマバリデーション（camelCase 自動変換・廃止リレーション修正・列挙値検証）
   - `insight_engine.py`: **Oracle Layer** — 感情トレンド分析・リスク予兆検知・ケアパターン自動発見・CarePreference 昇格提案
   - `embedding.py`: Gemini Embedding 2 によるベクトル生成・セマンティック検索・OCR・音声embedding・クライアント類似度分析
   - `file_readers.py`: ファイル読み取り（docx/xlsx/pdf/画像 + OCR フォールバック）
   - `pseudonymizer.py`: 仮名化モジュール
   - `utils.py`: 日付パース等ユーティリティ
4. **Manifesto** (`manifesto/`): 理念・プロトコル・ワークフロー

### External Services

- **Neo4j 5.15+** (via Docker): グラフデータベース
- **Gemini Embedding 2** (`gemini-embedding-2-preview`): セマンティック検索用 embedding 生成（768次元）
- **LINE Messaging API**: SOS 緊急通知
- **Neo4j MCP** (`@anthropic/neo4j-mcp-server`): Claude ↔ Neo4j 接続

---

## Skills 一覧と使い分けガイド

### 14 Skills

| Skill | 対象業務 | Neo4j Port | Templates |
|-------|----------|-----------|-----------|
| `neo4j-support-db` | 障害福祉クライアント管理 | 7687 | 10 read |
| `livelihood-support` | 生活困窮者自立支援 | 7688 | 12 read |
| `provider-search` | 事業所検索・口コミ管理 | 7687 | 6 read + 3 write |
| `emergency-protocol` | 緊急時対応プロトコル（insight-agent連動） | N/A | N/A |
| `ecomap-generator` | エコマップ・インサイト生成（D3.jsハイブリッドビュー） | N/A | N/A |
| `html-to-pdf` | HTML → PDF 変換 | N/A | N/A |
| `inheritance-calculator` | 法定相続計算 | N/A | N/A |
| `wamnet-provider-sync` | WAM NET 事業所データ同期 | 7687 | write |
| `narrative-extractor` | テキスト → 構造化データ抽出 | 7687 | write |
| `data-quality-agent` | データ品質チェック・検証 | 7687 | read |
| `onboarding-wizard` | 新規クライアント登録ウィザード | 7687 | read + write |
| `resilience-checker` | 親なき後レジリエンス診断 | 7687 | read |
| `visit-prep` | 訪問準備ブリーフィング | 7687 | read |
| `insight-agent` | 予兆検知・インサイト分析（Oracle Layer） | 7687 | read |

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
├─ データ品質・整合性チェック？
│  └─ YES → data-quality-agent
│
├─ 新規クライアント登録（対話形式）？
│  └─ YES → onboarding-wizard
│
├─ 親なき後レジリエンス診断？
│  └─ YES → resilience-checker
│
├─ 訪問準備・ブリーフィング（障害福祉）？
│  └─ YES → visit-prep
│
├─ 予兆検知・感情トレンド・リスク分析？
│  └─ YES → insight-agent（Oracle Layer: lib/insight_engine.py）
│         → リスク「高」の場合は emergency-protocol を自動連動
│
└─ 一般的な Neo4j 操作？
   └─ YES → neo4j MCP を直接使用
```

### Neo4j インスタンスの使い分け

| インスタンス | Bolt | HTTP | 対象スキル |
|------------|------|------|-----------|
| support-db | localhost:7687 | localhost:7474 | neo4j-support-db, provider-search, narrative-extractor |
| livelihood-support | localhost:7688 | localhost:7475 | livelihood-support |

**`neo4j` MCP のデフォルト接続先は port 7687。** livelihood-support のクエリは `livelihood-support-db` MCP サーバー（port 7688）経由の専用ツール群（`mcp__livelihood-support-db__*`）を使用すること。

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

> **日本語値の例外**: ユーザー向け表示に直結するプロパティ（`category`, `situation`, `episode`, `content` 等）は日本語値を許容する。列挙型（`riskLevel`, `effectiveness`, `status`）は必ず英語 PascalCase を使用すること。

### 主要ノードラベル（障害福祉 port 7687）

`Client`, `Condition`, `NgAction`, `CarePreference`, `KeyPerson`, `Guardian`, `Hospital`, `Certificate`, `PublicAssistance`, `Organization`, `Supporter`, `SupportLog`, `MeetingRecord`, `AuditLog`, `LifeHistory`, `Wish`, `Identity`, `ServiceProvider`, `ProviderFeedback`

### 主要ノードラベル（生活困窮者自立支援 port 7688）

`Recipient`, `CaseRecord`, `HomeVisit`, `Strength`, `Challenge`, `MentalHealthStatus`, `NgApproach`, `EffectiveApproach`, `EconomicRisk`, `MoneyManagement`, `KeyPerson`, `Hospital`, `SupportOrganization`, `CollaborationRecord`, `AuditLog`

> 詳細は `docs/SCHEMA_CONVENTION.md` の「livelihood-support スキーマ」セクションを参照。

### 主要リレーション

```cypher
(:Client)-[:HAS_CONDITION {diagnosedDate}]->(:Condition)
(:Client)-[:MUST_AVOID]->(:NgAction)-[:IN_CONTEXT]->(:Condition)
(:Client)-[:REQUIRES]->(:CarePreference)
(:Client)-[:HAS_KEY_PERSON {rank: 1}]->(:KeyPerson)
(:Client)-[:HAS_LEGAL_REP]->(:Guardian)
(:Client)-[:HAS_CERTIFICATE {issuedDate, status}]->(:Certificate)
(:Client)-[:TREATED_AT {since, status}]->(:Hospital)
(:Supporter)-[:LOGGED]->(:SupportLog)-[:ABOUT]->(:Client)
(:Supporter)-[:RECORDED]->(:MeetingRecord)-[:ABOUT]->(:Client)
(:SupportLog)-[:FOLLOWS]->(:SupportLog)
(:AuditLog)-[:AUDIT_FOR]->(:Client)
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
| ~~`HOLDS`~~ | `HAS_CERTIFICATE` |

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
├── docker-compose.yml             # Neo4j (port 7687 + 7688)
├── pyproject.toml                 # 最小依存
├── .env.example                   # 環境変数テンプレート
├── .python-version                # 3.12
├── setup.sh                       # Neo4j起動 + Skills symlink (macOS/Linux)
├── setup.ps1                      # Neo4j起動 + Skills symlink (Windows)
├── manifesto/                     # 理念・プロトコル・ワークフロー
│   ├── MANIFESTO.md
│   ├── protocols/                 # emergency, parent_down, onboarding, handover
│   └── workflows/                 # visit_preparation, resilience_report, renewal_check
├── lib/                           # 共有Pythonライブラリ
│   ├── db_operations.py           # Neo4j接続・クエリ実行・CRUD・仮名化出力（Guardian Layer統合）
│   ├── db_new_operations.py       # グラフ構造化登録（embedding自動付与、Guardian Layer統合）
│   ├── schema_validator.py        # Guardian Layer: スキーマバリデーション・camelCase変換
│   ├── insight_engine.py          # Oracle Layer: 感情トレンド分析・リスク予兆検知
│   ├── embedding.py               # Gemini Embedding 2（ベクトル生成・検索・OCR）
│   ├── file_readers.py            # ファイル読み取り（docx/xlsx/pdf/画像+OCR）
│   ├── pseudonymizer.py           # 仮名化（Pseudonymization）モジュール
│   └── utils.py                   # 日付パース等ユーティリティ
├── claude-skills/                 # Skills (→ ~/.claude/skills/ へ symlink)
│   ├── neo4j-support-db/
│   ├── livelihood-support/
│   ├── provider-search/
│   ├── emergency-protocol/        # 緊急時対応（insight-agent連動）
│   ├── ecomap-generator/          # エコマップ・インサイト生成（D3.jsハイブリッドビュー）
│   ├── html-to-pdf/
│   ├── inheritance-calculator/
│   ├── wamnet-provider-sync/
│   ├── narrative-extractor/       # テキスト→構造化データ抽出
│   ├── data-quality-agent/        # データ品質チェック・検証
│   ├── onboarding-wizard/         # 新規クライアント登録ウィザード
│   ├── resilience-checker/        # 親なき後レジリエンス診断
│   ├── visit-prep/                # 訪問準備ブリーフィング
│   └── insight-agent/             # 予兆検知・インサイト分析（Oracle Layer）
├── sos/                           # SOS緊急通知サービス
│   ├── api_server.py              # FastAPI + LINE
│   ├── app/                       # PWA frontend
│   ├── .env.example
│   └── README.md
├── scripts/                       # ユーティリティ
│   ├── backup.sh
│   ├── backfill_embeddings.py      # 既存ノードへのembedding一括付与
│   ├── multi_importer.py           # 多機能インポーター（音声・画像・PDF→構造化→登録）
│   ├── migrate_schema_v2.py        # スキーマ改善マイグレーション（インデックス・制約・リレーション拡張）
│   └── migrate_pseudonymization.py # 仮名化スキーマ・マイグレーション
├── configs/                       # Claude Desktop設定テンプレート
│   └── claude_desktop_config.json
├── tests/                         # テスト
│   ├── test_schema_validator.py   # Guardian Layerテスト (17テスト)
│   ├── test_insight_engine.py     # Oracle Layerテスト (12テスト)
│   ├── test_simulation_scenario.py # シナリオテスト (6テスト)
│   └── test_pseudonymizer.py      # 仮名化モジュールのユニットテスト
├── installer/                     # インストーラー
│   ├── install-mac.sh             # macOSワンクリックインストーラー
│   ├── install-windows.ps1        # Windowsワンクリックインストーラー
│   ├── configure-claude.sh        # Claude Desktop設定自動化 (macOS)
│   ├── configure-claude.ps1       # Claude Desktop設定自動化 (Windows)
│   ├── demo-data.cypher           # デモデータ（架空）
│   ├── simulation-emotion-data.cypher # 感情シミュレーションデータ（insight-agent検証用）
│   ├── load-demo-data.sh          # デモデータ投入・削除 (macOS) --simulationオプション対応
│   └── load-demo-data.ps1         # デモデータ投入・削除 (Windows)
└── docs/                          # ドキュメント
    ├── QUICK_START.md
    ├── SETUP_GUIDE.md             # 詳細セットアップガイド
    ├── SCHEMA_CONVENTION.md
    ├── ADVANCED_USAGE.md
    ├── EXTRACTION_PROMPT.md       # Gemini構造化プロンプト（emotion/triggerTag/context対応）
    ├── VOICE_RECORDING_GUIDE.md   # 声の記録マニュアル（現場スタッフ向け）
    ├── PRIVACY_GUIDELINES.md      # プライバシーガイドライン
    ├── FIRST_5_OPERATIONS.md      # 初めての5つの操作
    ├── FAQ.md                     # FAQ・トラブルシューティング
    └── VIDEO_SCRIPTS.md           # 動画チュートリアルスクリプト
```

## Important Constraints

### Data Integrity
- **Never fabricate data**: AI extraction must not infer missing information
- **Prohibition priority**: NgAction nodes are safety-critical, treat with highest importance
- **Date validation**: Use `lib/utils.py::safe_date_parse()` for all date inputs
- **推測の明記**: データの欠損がある場合や推論に基づく結論を述べる場合は、推測であることを必ず明記すること
- **スキーマの不可侵性**: 提供されたスキーマ規約に存在しないノードラベル、リレーション、プロパティを勝手に定義してはならない。新しい概念が必要な場合はユーザーに提案し承認を得ること
- **Client一意性検証**: 新規登録前に `validate_client_uniqueness(name, dob)` で重複チェックを行うこと（Community Edition では複合UNIQUE制約が非対応のためアプリレベルで検証）

### Neo4j Query Patterns
- Use `MERGE` for idempotent client/node creation
- Always use parameterized queries (`$param`) to prevent Cypher injection
- Handle optional fields with `COALESCE()` or `CASE WHEN ... ELSE ... END`
- Check existence before creating relationships to avoid duplicates
- 読み取りクエリでは旧名との後方互換性を `[:NEW|OLD]` 構文で確保する

### Graph-based Analysis（グラフ横断分析）

Skills の定型テンプレートに加え、**グラフの「繋がり（パス）」を辿った構造的洞察**を積極的に提供すること。単純なキーワード検索では見えないパターンを発見するため、以下のようなアドホック分析を行ってよい：

- **パス探索**: Client → Condition → NgAction → Supporter の経路を辿り、「ある特性に対する禁忌事項が、どの支援者に共有されているか」を分析
- **ネットワーク分析**: KeyPerson / Supporter / Guardian の繋がりから、支援体制の手薄な領域を検出
- **時系列パターン**: SupportLog の日付と effectiveness を辿り、ケアの改善・悪化傾向を発見
- **リスク連鎖**: Condition → NgAction のパスから、複数の特性が重なった場合のリスク増幅を推論

クエリはスキーマ規則に準拠し、`$param` パラメータ化を徹底すること。

### Embedding & Semantic Search

Gemini Embedding 2（`gemini-embedding-2-preview`）による768次元ベクトルでセマンティック検索を実現。

**ベクトルインデックス（6つ、port 7687）:**

| インデックス名 | 対象ノード | プロパティ | 次元 | 類似度 |
|---------------|-----------|-----------|------|--------|
| `support_log_embedding` | SupportLog | embedding | 768 | cosine |
| `care_preference_embedding` | CarePreference | embedding | 768 | cosine |
| `ng_action_embedding` | NgAction | embedding | 768 | cosine |
| `client_summary_embedding` | Client | summaryEmbedding | 768 | cosine |
| `meeting_record_embedding` | MeetingRecord | embedding | 768 | cosine |
| `meeting_record_text_embedding` | MeetingRecord | textEmbedding | 768 | cosine |

**自動付与フロー:**
- `lib/db_new_operations.py::register_to_database()` — ノード登録時にベストエフォートで embedding 自動付与
- `lib/db_new_operations.py::register_to_database()` — ノード登録時に Client の summaryEmbedding もベストエフォートで自動付与
- `lib/db_new_operations.py::register_support_log()` — 支援記録登録時に embedding 自動付与
- `db.create.setNodeVectorProperty()` を使用（通常の `SET` ではベクトルインデックスに認識されない）

**検索関数（`lib/embedding.py`）:**
- `semantic_search(query, label, index_name, top_k)` — 汎用セマンティック検索
- `search_support_logs_semantic(query, client_name, top_k)` — 支援記録の意味検索
- `search_ng_actions_semantic(query, client_name, top_k)` — 禁忌事項の意味検索
- `search_meeting_records_semantic(query, client_name, top_k)` — 面談記録の意味検索

**音声・面談記録関数（`lib/embedding.py`）:**
- `embed_audio(audio_path)` — 音声ファイルからembeddingベクトルを生成（最大80秒）
- `transcribe_audio(audio_path)` — Gemini 2.0 Flash で音声をテキストに文字起こし
- `register_meeting_record(audio_path, client_name, supporter_name, date, ...)` — 音声面談記録の一括登録（文字起こし + dual embedding + Neo4j登録）

**クライアント類似度分析関数（`lib/embedding.py`）:**
- `build_client_summary_text(client_name)` — クライアントの関連情報を集約し概要テキストを構築
- `embed_client_summary(client_name)` — Client の summaryEmbedding を生成・付与
- `find_similar_clients(client_name, top_k)` — 支援特性が類似するクライアントを検索
- `search_similar_clients_by_text(description, top_k)` — テキスト説明から類似クライアントを検索

**バックフィル:**
```bash
uv run python scripts/backfill_embeddings.py --all               # 全ノード
uv run python scripts/backfill_embeddings.py --label SupportLog   # 特定ラベル
uv run python scripts/backfill_embeddings.py --label Client       # Client summaryEmbedding
uv run python scripts/backfill_embeddings.py --stats              # 統計のみ
```

> **Note**: `GEMINI_API_KEY` 未設定時は embedding 処理をスキップ（登録処理はブロックしない）。

### Pseudonymization (仮名化)

`PSEUDONYMIZATION_ENABLED=true` の場合、`db_operations.py` の読み取り関数は自動的に出力を仮名化する。Neo4j 内の実データは変更されない。

- **mask モード**: 部分マスク（山田→山●●●）- 研修・デモ向け
- **pseudonym モード**: 架空名に置換 - テスト・開発向け
- **安全例外**: NgAction（禁忌事項）と CarePreference（推奨ケア）は仮名化しない

詳細は `docs/PRIVACY_GUIDELINES.md` および `lib/pseudonymizer.py` を参照。

### Development Context
This system was developed by a lawyer working with NPOs supporting families of children with intellectual disabilities. The design prioritizes **real-world emergency scenarios** where staff need immediate access to critical care information when primary caregivers are unavailable.

**Design Philosophy**: Preserve parental tacit knowledge in structured format, queryable in natural language during crisis situations.
