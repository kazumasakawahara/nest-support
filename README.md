# nest-support

**Claude-Native 親亡き後支援データベース**

知的障害・精神障害のある方の支援情報を Neo4j グラフデータベースに蓄積し、**Claude Desktop / Claude Code + Skills + Neo4j MCP** で運用するシステムです。

親が長年かけて蓄積してきた「我が子を守るための暗黙知」を、親亡き後も機能する社会的システムへと継承するためのデジタル・アーカイブです。

---

## 特徴

- **Single Layer Architecture** — Claude が UI・分析・データ操作のすべてを担当。Streamlit や Gemini への依存なし
- **Skills-First** — 9つの Claude Skills が Cypher テンプレートを提供し、汎用 Neo4j MCP 経由でクエリを実行
- **Safety First** — 緊急時は禁忌事項（NgAction）を最優先で提示し、二次被害を防止
- **SOS 緊急通知** — スマホ PWA から LINE グループへ即時通知（FastAPI 独立サービス）

## アーキテクチャ

```
ユーザー → Claude Desktop / Claude Code
              ↓
         Skills (SKILL.md)  ←  9つのスキルがCypherテンプレートを提供
              ↓
         Neo4j MCP (@anthropic/neo4j-mcp-server)
              ↓
         Neo4j Graph Database
```

```
スマホ → SOS PWA → FastAPI → LINE Messaging API → 支援者グループ LINE
                      ↓
                  Neo4j（クライアント情報取得）
```

## 5つの価値 (The 5 Values)

| 価値 | 英語 | 定義 |
|------|------|------|
| **尊厳** | Dignity | 管理対象ではなく、歴史と意思を持つ一人の人間として記録する |
| **安全** | Safety | 緊急時に「誰が」「何を」すべきか、迷わせない構造を作る |
| **継続性** | Continuity | 支援者が入れ替わっても、ケアの質と文脈を断絶させない |
| **強靭性** | Resilience | 親が倒れた際、その機能を即座に代替できるバックアップ体制を可視化する |
| **権利擁護** | Advocacy | 本人の声なき声を拾い上げ、法的な後ろ盾と紐づける |

## クイックスタート

### 前提条件

| ツール | 用途 |
|-------|------|
| [Docker Desktop](https://docs.docker.com/get-docker/) | Neo4j データベース |
| [Claude Desktop](https://claude.ai/download) | AI 操作 |
| [Node.js](https://nodejs.org/) (npx) | Neo4j MCP サーバー |

### セットアップ

```bash
git clone https://github.com/kazumasakawahara/nest-support.git
cd nest-support

# 1. セットアップ（Neo4j起動 + Skills インストール）
chmod +x setup.sh
./setup.sh

# 2. Claude Desktop 設定ファイルに Neo4j MCP を追加
# Mac: ~/Library/Application Support/Claude/claude_desktop_config.json
# テンプレート: configs/claude_desktop_config.json
```

`claude_desktop_config.json` に追加する内容:

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

### 動作確認

Claude Desktop を再起動し、以下のように話しかけてください:

```
データベースの統計情報を教えて
```

```
以下の文章からクライアント情報を抽出して登録してください。

健太は1995年3月15日生まれです。血液型はA型。
自閉スペクトラム症と診断されています。
後ろから急に声をかけないでください。パニックになります。
パニック時は静かな部屋に移動して背中をゆっくりさすると落ち着きます。
```

## Skills 一覧

| Skill | 対象業務 | 説明 |
|-------|----------|------|
| `neo4j-support-db` | 障害福祉クライアント管理 | プロフィール、支援記録、ケアパターン発見、更新期限チェック |
| `livelihood-support` | 生活困窮者自立支援 | 訪問前ブリーフィング、引き継ぎサマリー、類似ケース検索 |
| `provider-search` | 事業所検索・口コミ | サービス種類・地域・空き状況での検索、口コミ評価 |
| `emergency-protocol` | 緊急時対応 | Safety First プロトコル（禁忌→推奨ケア→連絡先→医療→後見人）|
| `ecomap-generator` | エコマップ生成 | 支援ネットワーク可視化（Mermaid / SVG）|
| `narrative-extractor` | テキスト→構造化データ | 母親の語りやファイルから JSON 抽出→Neo4j 登録 |
| `html-to-pdf` | HTML→PDF 変換 | Chrome 印刷機能を利用した PDF 生成 |
| `inheritance-calculator` | 法定相続計算 | 日本民法に基づく相続人・相続分の計算 |
| `wamnet-provider-sync` | WAM NET 同期 | 障害福祉サービス情報公表システムからのデータ同期 |

## データ登録の方法（narrative-extractor）

このシステムの核心機能です。親御さんの語りや支援記録などの**自然な日本語テキスト**を Claude に渡すだけで、構造化データとして Neo4j に登録できます。

### 登録フロー

```
テキスト入力 → Claude が JSON に構造化 → ユーザー確認 → Neo4j に登録
```

旧システム（Streamlit + Gemini）の4ステップ GUI を、**Claude との会話**で実現しています。

### トリガーワード

以下のフレーズを含めると `narrative-extractor` スキルが自動的に選択されます：

- **「抽出して」「構造化して」「登録してください」**
- **「聞き取り内容」「面談記録」「ナラティブ」**
- **「情報を追加して」**（既存クライアントへの追記）
- **ファイル添付**（.docx, .xlsx, .pdf, .txt）

### プロンプト例

**基本的な使い方:**
```
以下の文章からクライアント情報を抽出してデータベースに登録してください。

健太は1995年3月15日生まれです。血液型はA型。
自閉スペクトラム症と診断されています。
後ろから急に声をかけないでください。パニックになります。
パニック時は静かな部屋に移動して背中をゆっくりさすると落ち着きます。
```

**母親の語り（物語調）:**
```
以下の聞き取り内容を構造化してデータベースに登録してください。

うちの太郎はね、昭和62年の夏に生まれたんです。小さい頃から
音に敏感で、運動会のピストルの音で泣いてしまって...。
今でも大きな音は絶対ダメです。掃除機も怖がります。
でもね、音楽は好きなんですよ。童謡を歌ってあげると
にこにこして、すごく穏やかになるの。
かかりつけは北九州中央病院の田中先生です。月に一回通ってます。
療育手帳はA1で、来年の3月に更新です。
```

**既存クライアントへの追記:**
```
山田健太さんの情報に以下を追加してください。
かかりつけは産業医科大学病院の中村先生（精神科）です。
```

**支援記録の登録:**
```
以下の支援記録をデータベースに登録してください。

2024年12月15日、訪問支援。担当：鈴木。
健太さんが昼食時にスプーンを投げてしまった。
隣の利用者が大きな声を出したのがきっかけ。
別室に誘導し、好きな音楽をかけたところ10分で落ち着いた。
この対応は効果的だった。
```

### 自動抽出される情報

テキスト中の表現から、以下のデータが自動的に分類・抽出されます：

| テキスト中の表現 | 抽出先 | 重要度 |
|----------------|--------|--------|
| 「〜しないで」「〜するとパニック」「絶対ダメ」 | **NgAction（禁忌事項）** | 最重要 |
| 「〜すると落ち着く」「〜が好き」「〜の方法で」 | CarePreference（推奨ケア） | 高 |
| 「〜と診断」「〜の特性がある」 | Condition（特性・診断） | 高 |
| 「母は〜」「連絡先は〜」 | KeyPerson（緊急連絡先） | 高 |
| 「〜病院の〜先生」 | Hospital（かかりつけ医） | 中 |
| 「手帳は〜」「受給者証」「更新は〜」 | Certificate（手帳・証明書） | 中 |
| 「後見人は〜」 | Guardian（法定代理人） | 中 |
| 「小さい頃は〜」「学校では〜」 | LifeHistory（生育歴） | 中 |
| 「〜したい」「〜が夢」 | Wish（願い） | 中 |

> **Note**: 和暦（昭和・平成・令和等）は自動的に西暦に変換されます。

## グラフデータモデル

```
                    ┌─────────────┐
                    │   Client    │ ← 中心ノード（本人）
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  NgAction   │ │CarePreference│ │  KeyPerson  │
    │  (禁忌事項)  │ │ (推奨ケア)   │ │(緊急連絡先)  │
    └─────────────┘ └─────────────┘ └─────────────┘
           │
    ┌──────▼──────┐
    │  Condition  │     ┌─────────────┐  ┌─────────────┐
    │ (特性・診断) │     │  Hospital   │  │  Guardian   │
    └─────────────┘     │(かかりつけ医)│  │  (後見人)    │
                        └─────────────┘  └─────────────┘

    (:Client)-[:MUST_AVOID]->(:NgAction)        # 禁忌事項（最重要）
    (:Client)-[:REQUIRES]->(:CarePreference)    # 推奨ケア
    (:Client)-[:HAS_KEY_PERSON]->(:KeyPerson)   # キーパーソン
    (:Client)-[:HAS_CONDITION]->(:Condition)    # 特性・診断
    (:Client)-[:TREATED_AT]->(:Hospital)        # 通院先
    (:Client)-[:HAS_LEGAL_REP]->(:Guardian)     # 法定代理人
    (:Supporter)-[:LOGGED]->(:SupportLog)-[:ABOUT]->(:Client)  # 支援記録
```

## SOS 緊急通知サービス

知的障害のある方がスマホからワンタップで支援者グループに SOS を送信できる PWA アプリです。

```bash
cd sos
cp .env.example .env
# .env に LINE_CHANNEL_ACCESS_TOKEN と LINE_GROUP_ID を設定
uv run python api_server.py
```

アプリURL: `http://localhost:8000/app/?id=クライアント名`

詳細: [sos/README.md](sos/README.md)

## プロジェクト構成

```
nest-support/
├── CLAUDE.md                  # Claude 向けプロジェクト指示書
├── docker-compose.yml         # Neo4j コンテナ設定
├── pyproject.toml             # Python 依存関係
├── setup.sh                   # セットアップスクリプト
├── manifesto/                 # 理念・プロトコル・ワークフロー
│   ├── MANIFESTO.md           # マニフェスト v4.0（5 Values + 7 Pillars）
│   ├── protocols/             # 緊急時、親の機能不全、新規登録、引き継ぎ
│   └── workflows/             # 訪問準備、レジリエンスレポート、更新チェック
├── lib/                       # 共有 Python ライブラリ（SOS 用）
│   ├── db_operations.py       # Neo4j 接続・クエリ実行
│   └── utils.py               # 日付パース（和暦対応）
├── claude-skills/             # 9つの Claude Skills
│   ├── neo4j-support-db/      # 障害福祉 DB
│   ├── livelihood-support/    # 生活困窮者支援
│   ├── provider-search/       # 事業所検索
│   ├── emergency-protocol/    # 緊急時プロトコル
│   ├── ecomap-generator/      # エコマップ生成
│   ├── narrative-extractor/   # テキスト→構造化データ抽出
│   ├── html-to-pdf/           # HTML→PDF 変換
│   ├── inheritance-calculator/ # 法定相続計算
│   └── wamnet-provider-sync/  # WAM NET データ同期
├── sos/                       # SOS 緊急通知サービス
│   ├── api_server.py          # FastAPI サーバー
│   └── app/                   # PWA フロントエンド
├── configs/                   # Claude Desktop 設定テンプレート
├── docs/                      # ドキュメント
│   ├── QUICK_START.md         # クイックスタートガイド
│   ├── SCHEMA_CONVENTION.md   # Neo4j 命名規則
│   └── ADVANCED_USAGE.md      # Skills 詳細使い方
└── scripts/                   # ユーティリティ
    └── backup.sh              # Neo4j バックアップ
```

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| AI | Claude Desktop / Claude Code + Skills |
| データベース | Neo4j 5.15+ (Docker) |
| DB 接続 | Neo4j MCP (`@anthropic/neo4j-mcp-server`) |
| SOS API | FastAPI + uvicorn |
| SOS 通知 | LINE Messaging API |
| SOS フロントエンド | PWA (HTML + Service Worker) |
| 言語 | Python 3.12+ |
| パッケージ管理 | uv |

## ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [CLAUDE.md](CLAUDE.md) | Claude 向けプロジェクト指示書（スキーマ規則、Skills ルーティング含む）|
| [docs/QUICK_START.md](docs/QUICK_START.md) | 5分セットアップガイド |
| [docs/ADVANCED_USAGE.md](docs/ADVANCED_USAGE.md) | Skills の詳細な使い方とプロンプト例 |
| [docs/SCHEMA_CONVENTION.md](docs/SCHEMA_CONVENTION.md) | Neo4j 命名規則（Single Source of Truth）|
| [manifesto/MANIFESTO.md](manifesto/MANIFESTO.md) | マニフェスト v4.0 |
| [sos/README.md](sos/README.md) | SOS 緊急通知サービスの詳細 |

## 開発背景

このシステムは、知的障害のある方の家族を支援する NPO と協働する弁護士によって開発されました。主介護者が不在になった緊急時に、支援スタッフが重要なケア情報に即座にアクセスできることを最優先に設計されています。

**設計思想**: 親の暗黙知を構造化されたグラフデータとして保存し、危機的状況においても自然言語で照会可能にする。

## ライセンス

MIT License
