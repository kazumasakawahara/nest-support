# 発展的運用ガイド: Claude + Skills との連携

---

## アーキテクチャ概要

```
ユーザー → Claude Desktop / Claude Code → Skills（SKILL.md）→ Neo4j MCP → Neo4j DB
```

Claude が SKILL.md に含まれるCypherテンプレートを参照し、汎用 Neo4j MCP の `read_neo4j_cypher` / `write_neo4j_cypher` ツールでクエリを実行します。

---

## 14の Skills

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

### 10. data-quality-agent（データ品質チェック）

**対象**: データの整合性・鮮度・欠損の定期チェック

**プロンプト例:**
```
データベースの品質チェックを実行して
更新期限が近いデータをすべてリストアップして
スキーマ違反がないかチェックして
```

### 11. onboarding-wizard（新規クライアント登録）

**対象**: 初回面接時の対話型情報収集

**プロンプト例:**
```
新しいクライアントを登録したい
初回面接の情報を入力します
新規利用者の受け入れ準備をしたい
```

### 12. resilience-checker（親なき後レジリエンス診断）

**対象**: 親が担う機能のカバー率診断

**プロンプト例:**
```
山田さんの親なき後レジリエンスを診断して
もし親が倒れたらどうなるかシミュレーションして
バックアップ体制のカバー率を確認して
```

### 13. visit-prep（訪問準備ブリーフィング）

**対象**: 訪問・同行支援の前日〜当日の準備

**プロンプト例:**
```
明日、山田さんのところに訪問します。準備情報をください
山田さんの訪問前ブリーフィングをお願い
```

### 14. insight-agent（予兆検知・インサイト分析）

**対象**: 感情トレンド分析、リスク予兆の早期検知、ケアパターン自動発見

**プロンプト例:**
```
山本翔太さんの最近の感情トレンドを分析して
最近様子がおかしい利用者がいないかチェックして
山本さんのリスク評価を実行して
効果的なケアパターンを発見して
全クライアントの感情サマリーを見せて
```

**機能:**
- **Emotion Drift**: ベースラインからのネガティブ感情の増加率を検知（閾値30%）
- **Cascading Risk**: 複数場面にまたがる負の感情の連鎖を検知
- **Staff SOS**: スタッフの負荷増大を記録比率で検知
- **Care Pattern**: 繰り返し効果的な対応を自動発見し、CarePreference への昇格を提案
- **Risk Assessment**: 総合リスク評価 → High 時は emergency-protocol を自動連動

**Python API (`lib/insight_engine.py`):**
```python
from lib.insight_engine import generate_risk_assessment
result = generate_risk_assessment("山本翔太")
# → {"risk_level": "high", "should_trigger_emergency": true, ...}
```

---

## Skills の選択ガイド

| やりたいこと | 使うSkill |
|-------------|----------|
| クライアントの情報確認 | `neo4j-support-db` |
| テキストからの情報抽出・登録 | `narrative-extractor` |
| 支援記録の追加・分析 | `neo4j-support-db` |
| 訪問前の準備（障害福祉） | `visit-prep` |
| 訪問前の準備（生活困窮者） | `livelihood-support` |
| 引き継ぎ資料の作成 | `livelihood-support` |
| 事業所の検索・比較 | `provider-search` |
| 緊急時の即時対応 | `emergency-protocol` |
| 支援関係の可視化 | `ecomap-generator` |
| 証明書の期限管理 | `neo4j-support-db` |
| 口コミの参照・登録 | `provider-search` |
| 感情トレンド・予兆の分析 | `insight-agent` |
| 新規クライアント登録 | `onboarding-wizard` |
| 親なき後レジリエンス診断 | `resilience-checker` |
| データ品質の定期チェック | `data-quality-agent` |

---

## 多機能インポーター

音声・画像・PDF・テキストから感情データを含む構造化データを一括登録するスクリプトです。

**前提**: `GEMINI_API_KEY` 環境変数が必要です（Gemini 2.0 Flash による音声文字起こし・画像OCR・テキスト構造化に使用）。

```bash
# 単一ファイル
uv run python scripts/multi_importer.py 録音.m4a --client "山田太郎" --supporter "鈴木"

# フォルダ一括
uv run python scripts/multi_importer.py ./今日の記録/ --client "山田太郎"

# ドライラン（登録せず構造化結果のみ確認）
uv run python scripts/multi_importer.py memo.jpg --client "山田太郎" --dry-run
```

対応形式: `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.docx`, `.xlsx`, `.pdf`, `.txt`, `.jpg`, `.png`, `.webp`, `.heic`

詳しい録音の仕方は [docs/VOICE_RECORDING_GUIDE.md](VOICE_RECORDING_GUIDE.md) を参照。

---

## ハイブリッド・インサイト・ビュー

D3.js による感情時系列チャート + 物理グラフ + AI相談プロンプト機能を統合したダッシュボードです。

```bash
uv run python claude-skills/ecomap-generator/scripts/generate_html.py "山本翔太" hybrid
```

- **左パネル**: 感情ポジティブ率の時系列折れ線グラフ、アラートカード、成功パターン
- **右パネル**: D3.js 物理シミュレーションによるノードグラフ
- **ノードクリック**: 詳細表示 + AI相談プロンプトのクリップボードコピー

---

## 現場UI (Field UI)

現場スタッフがスマホから直接操作できるモバイルファーストの PWA です。Claude Desktop を使わずに、ブラウザから支援記録の入力や感情サマリーの確認ができます。

### サーバーの起動

```bash
uv run uvicorn field-ui.server:app --host 0.0.0.0 --port 8001
```

### 3つの画面

| 画面 | URL | 説明 |
|------|-----|------|
| 支援記録フォーム | http://localhost:8001/record | チップ選択式の簡単入力。現場でスマホからすばやく支援記録を登録できます |
| 管理者ダッシュボード | http://localhost:8001/dashboard | クライアントの感情サマリー表示とドリルダウン分析。管理者向け |
| 音声ワンタップ録音 | http://localhost:8001/voice | ブラウザで録音 → Gemini による文字起こし → Neo4j に自動登録 |

> **Note**: 音声ワンタップ録音機能には `GEMINI_API_KEY` 環境変数の設定が必要です。`.env` ファイルに `GEMINI_API_KEY=your_key` を追記してください。

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
npx -y @alanse/mcp-neo4j-server --help
```

### Cypher クエリがエラーになる
1. Neo4j Browser (http://localhost:7474) で直接クエリを実行して確認
2. SKILL.md 内のテンプレートとスキーマが一致しているか確認
3. APOC プラグインが有効か確認: `RETURN apoc.version()`
