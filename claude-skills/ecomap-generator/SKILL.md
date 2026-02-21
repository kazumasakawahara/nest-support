---
name: ecomap-generator
description: 支援ネットワークをエコマップ（支援関係図）として可視化するスキル。HTML形式（Neo4j風）・Mermaid形式・SVG形式での出力に対応し、4種類のテンプレート（全体像、支援会議用、緊急時、引き継ぎ用）を提供。
---

# エコマップ生成スキル (ecomap-generator)

知的障害・精神障害のある方の支援ネットワークを**エコマップ（支援関係図）**として可視化するスキルです。

## 使用条件

- **neo4j-support-db**スキルが有効であること
- Neo4jデータベースにクライアント情報が登録済みであること

## 使用トリガー

ユーザーが以下のように依頼した場合にこのスキルを使用：

- 「〇〇さんのエコマップを作って」
- 「支援会議用にエコマップを表示して」
- 「緊急連絡体制を図にして」
- 「引き継ぎ用のエコマップが欲しい」
- 「Neo4j風のグラフで表示して」

## エコマップの種類

| テンプレート | 用途 | 含まれる情報 |
|-------------|------|-------------|
| `full_view` | 全体像把握 | 全ての関係者・機関 |
| `support_meeting` | ケース会議 | 推奨ケア、キーパーソン、最近の支援記録 |
| `emergency` | 緊急時対応 | 禁忌事項（最優先）、キーパーソン、医療機関 |
| `handover` | 担当者引き継ぎ | 全情報＋支援記録履歴 |

## 実行方法

### 方法1: HTML形式（ブラウザで表示・推奨）

Neo4j風のインタラクティブなグラフをブラウザで表示します。
外部CDNに依存せず、純粋なSVGで描画するため確実に表示されます。
ノードのドラッグ移動、クリックで詳細表示が可能です。

```bash
cd claude-skills/ecomap-generator/scripts
uv run python generate_html.py "クライアント名" -t テンプレート名
```

**例：**
```bash
uv run python generate_html.py "山田健太" -t full_view
# → outputs/山田健太_ecomap_full_view.html が生成される
```

生成されたHTMLファイルをブラウザで開いてください。

### 方法2: Mermaid形式（チャット内表示）

```bash
cd claude-skills/ecomap-generator/scripts
uv run python generate_mermaid.py "クライアント名" -t テンプレート名
```

**例：**
```bash
uv run python generate_mermaid.py "山田健太" -t emergency
```

### 方法3: SVG形式（印刷用ファイル）

```bash
cd claude-skills/ecomap-generator/scripts
uv run python generate_svg.py "クライアント名" -t テンプレート名
```

**例：**
```bash
uv run python generate_svg.py "山田健太" -t support_meeting
```

出力先: `claude-skills/ecomap-generator/outputs/`

### 方法4: Neo4jブラウザで表示

以下のCypherクエリをNeo4jブラウザ（http://localhost:7474）で実行：

**全体像:**
```cypher
MATCH path = (c:Client {name: 'クライアント名'})-[*1..2]-()
RETURN path LIMIT 100
```

**緊急時体制:**
```cypher
MATCH (c:Client {name: 'クライアント名'})
OPTIONAL MATCH (c)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)
OPTIONAL MATCH (c)-[:REQUIRES|PREFERS]->(cp:CarePreference)
WHERE cp.priority = 'High'
OPTIONAL MATCH (c)-[kp_rel:HAS_KEY_PERSON|EMERGENCY_CONTACT]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:HAS_GUARDIAN|HAS_LEGAL_REP]->(g:Guardian)
OPTIONAL MATCH (c)-[:TREATED_AT]->(h:Hospital)
RETURN c, ng, cp, kp, kp_rel, g, h
```

## neo4j-support-dbとの連携

エコマップ生成前に、以下のツールでデータを確認：

| ツール | 用途 |
|--------|------|
| `list_clients` | クライアント一覧 |
| `get_client_profile` | クライアント全体像 |
| `search_emergency_info` | 緊急時情報 |

## データモデル

### ノード

- `Client` - 本人（赤）
- `NgAction` - 禁忌事項（赤）
- `CarePreference` - 推奨ケア（緑）
- `KeyPerson` - キーパーソン（オレンジ）
- `Guardian` - 後見人（紫）
- `Hospital` - 医療機関（青）
- `Certificate` - 手帳（グレー）
- `Condition` - 特性（黄）
- `Supporter` - 支援者（青紫）

### リレーション

| 現行名（推奨） | 旧名（後方互換） | 用途 |
|---|---|---|
| `MUST_AVOID` | `PROHIBITED` | 禁忌事項 |
| `REQUIRES` | `PREFERS` | 推奨ケア |
| `HAS_KEY_PERSON` | `EMERGENCY_CONTACT` | キーパーソン |
| `HAS_LEGAL_REP` | `HAS_GUARDIAN` | 後見人 |
| `TREATED_AT` | - | 医療機関 |
| `HAS_CERTIFICATE` | - | 手帳 |
| `HAS_CONDITION` | - | 特性 |

**注意**: 読み取りクエリでは `[:MUST_AVOID|PROHIBITED]` のように旧名との後方互換性を確保しています。書き込み時は現行名のみ使用してください。

## ファイル構成

```
claude-skills/ecomap-generator/
├── SKILL.md              ← このファイル
├── pyproject.toml        ← 依存関係定義
├── scripts/
│   ├── generate_html.py    ← HTML形式出力（推奨）
│   ├── generate_mermaid.py ← Mermaid形式出力
│   ├── generate_svg.py     ← SVG形式出力
│   └── cypher_templates.py ← クエリテンプレート
├── templates/            ← Cypherテンプレート
│   ├── full_view.cypher
│   ├── support_meeting.cypher
│   ├── emergency.cypher
│   └── handover.cypher
└── outputs/              ← 生成ファイル
```

## バージョン

- v1.1.0 (2026-02-17) - HTML出力追加、SVGバグ修正、パス修正
- v1.0.0 (2025-12-26) - 初版リリース
