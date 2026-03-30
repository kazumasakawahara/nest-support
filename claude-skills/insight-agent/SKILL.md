---
name: insight-agent
description: 現場スタッフが記録した感情ログやAI相談履歴を多角的に分析し、行動障害の悪化、体調不良、スタッフの負担増などの「予兆」を管理者に報告するスキル。「最近の変化」「様子がおかしい」「予兆」「リスク分析」「トレンド」「スタッフの状況」などの話題でこのスキルを使用すること。
---

# インサイト・エージェント (insight-agent) v2.0

## このスキルの意義
グループホームや作業所の現場から得られる微細な変化（感情ログ）を統計的・文脈的に分析し、重大なトラブルやスタッフの離職・疲弊を未然に防ぐ「予防的支援」を実現する。

## アーキテクチャ

```
lib/insight_engine.py (Python)  ← 統計分析・パターン発見の中核ロジック
       ↕
insight-agent (SKILL.md)        ← Claude がクエリ実行＆結果を解釈・報告
       ↕
emergency-protocol              ← リスク「高」判定時に自動連動
```

**Python API (`lib/insight_engine.py`)** を活用することで、Neo4j MCP の生クエリに加えて、
統計的な比率計算・閾値判定・CarePreference 昇格提案を自動化できる。

---

## 予測ロジック (5段階分析)

| # | 分析項目 | 判定基準 | 報告内容 |
|---|---------|---------|---------|
| 1 | **感情の波 (Emotion Drift)** | 特定タグにおける負の感情が、ベースラインから30%以上増加 | 「〇〇さんの『作業中』のイライラが急増しています」 |
| 2 | **連鎖の検知 (Cascading Risk)** | 直近3日間で2種類以上のタグで負の感情が連続 | 「生活全般での意欲低下、または隠れた体調不良の予兆です」 |
| 3 | **スタッフSOS (Staff SOS)** | 担当する記録の負の感情比率が50%超 | 「担当スタッフAさんの支援負荷が高まっています」 |
| 4 | **成功パターン発見 (Care Pattern)** | 同一対応が3回以上 Effective と記録 | 「この対応を CarePreference に登録しませんか？」 |
| 5 | **総合リスク評価 (Risk Assessment)** | Drift高 + 連鎖あり → High → emergency-protocol 連動 | 総合レポート + 推奨アクション |

**負の感情**: Anger, Sadness, Fear, Disgust, Anxiety

---

## 実行手順

### Step 1: 感情トレンドの取得 (Emotion Drift)

過去30日のデータを元に、直近7日間の変化を算出する。

```cypher
// 感情トレンド分析 - タグ × 期間 × 感情の集計
MATCH (c:Client {name: $clientName})<-[:ABOUT]-(log:SupportLog)
WHERE log.date >= date() - duration({days: 30})
  AND log.emotion IS NOT NULL
WITH log,
     CASE WHEN log.date >= date() - duration({days: 7})
          THEN 'Recent' ELSE 'Baseline' END AS period
RETURN log.triggerTag AS triggerTag,
       log.emotion AS emotion,
       period,
       count(*) AS count
ORDER BY triggerTag, period
```

**パラメータ**: `$clientName` — クライアント名

**分析方法:**
1. タグごとに Baseline vs Recent の負の感情比率を計算
2. `(Recent比率 - Baseline比率) / Baseline比率` が 0.3 以上なら警告
3. 0.5 以上なら重大な悪化として報告

### Step 2: 複合リスクの確認 (Cascading Risk)

特定のクライアントについて、直近3日間の「負の感情の連鎖」を確認する。

```cypher
// 複合リスク検出 - 直近3日の負の感情イベント
MATCH (c:Client {name: $clientName})<-[:ABOUT]-(log:SupportLog)
WHERE log.date >= date() - duration({days: 3})
  AND log.emotion IN ['Anger', 'Sadness', 'Fear', 'Disgust', 'Anxiety']
RETURN log.date AS date,
       log.triggerTag AS triggerTag,
       log.emotion AS emotion,
       log.context AS context,
       log.situation AS situation
ORDER BY log.date DESC
```

**判定**: 2種類以上の異なる triggerTag に負の感情がまたがっている場合「連鎖」と判定。

### Step 3: 現場スタッフ負荷の確認 (Staff SOS)

```cypher
// スタッフ負荷分析 - 記録に占める負の感情比率
MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)
WHERE log.date >= date() - duration({days: 7})
WITH s.name AS staffName,
     count(log) AS totalLogs,
     count(CASE WHEN log.emotion IN ['Anger', 'Sadness', 'Fear', 'Disgust', 'Anxiety'] THEN 1 END) AS negativeLogs
RETURN staffName, totalLogs, negativeLogs,
       CASE WHEN totalLogs > 0
            THEN round(toFloat(negativeLogs) / totalLogs * 100, 1)
            ELSE 0 END AS negativePercent
ORDER BY negativePercent DESC
```

**判定**: negativePercent が 50% 以上かつ totalLogs が 3 件以上のスタッフに警告。

### Step 4: ケアの成功パターン発見

```cypher
// 効果的なケアパターンの自動発見
MATCH (c:Client {name: $clientName})<-[:ABOUT]-(log:SupportLog)
WHERE log.effectiveness IN ['Effective', 'High']
  AND log.action IS NOT NULL
  AND log.action <> ''
WITH log.triggerTag AS triggerTag,
     log.situation AS situation,
     log.action AS action,
     log.emotion AS emotion,
     count(*) AS frequency
WHERE frequency >= 2
RETURN triggerTag, situation, action, emotion, frequency
ORDER BY frequency DESC
LIMIT 10
```

**昇格判定**: frequency >= 3 かつ既存 CarePreference に同一 instruction が未登録の場合、
CarePreference への昇格を提案する。

```cypher
// 既存の CarePreference を確認
MATCH (c:Client {name: $clientName})-[:REQUIRES|PREFERS]->(cp:CarePreference)
RETURN cp.category AS category, cp.instruction AS instruction
```

### Step 5: 総合リスク評価 (Risk Assessment)

Step 1〜4 の結果を統合し、以下の基準でリスクレベルを判定する:

| リスクレベル | 条件 | アクション |
|------------|------|---------|
| **High** | Drift高 + 連鎖あり | **emergency-protocol を即時起動** |
| **Medium** | Drift高 or (連鎖あり + イベント3件以上) | ケース会議に議題追加 |
| **Low** | Medium以下のアラート | 経過観察を継続 |

---

## emergency-protocol との連動

### 自動連動フロー

```
Risk Assessment = "High"
  ↓
emergency-protocol スキルを起動
  ↓
1. 🚫 NgAction（禁忌事項）を確認
2. ✅ CarePreference（推奨ケア）を確認
3. 📞 KeyPerson（緊急連絡先）を提示
  ↓
管理者への具体的な初動指示:
- 「本日中に〇〇さんの状態を直接確認してください」
- 「〇〇場面でのケアを重点的に見直してください」
- 「△△スタッフとの面談を今週中に設定してください」
```

**重要**: Risk = High の場合、レポート冒頭に以下を表示:

```
🚨 リスクレベル: 高
emergency-protocol の情報を以下に表示します。
管理者は本日中に対応を開始してください。
```

---

## 報告テンプレート (Insight Report)

```markdown
### 📢 インサイト・アラート：[クライアント名]
**分析期間:** [日付] 〜 [日付] | **リスクレベル:** [高/中/低]

#### 🚩 検知された変化 (Emotion Drift)
- **[重要度: 高]** 「[triggerTag]」のネガティブ感情が先月平均の[X]倍に増加
  - ベースライン: [X]% → 直近: [Y]% (変化率: +[Z]%)
- **[重要度: 中]** 「[triggerTag]」で[emotion]が[N]件記録

#### ⚡ 負の連鎖 (Cascading Risk)
[is_cascading = true の場合]
直近3日間で[N]種類の場面（[タグ一覧]）で負の感情が記録されています。
生活全般での意欲低下、または隠れた体調不良の予兆の可能性があります。

#### 💡 AIの考察と提案
[context フィールドの頻出キーワードを分析し、背景要因を推測]
1. [具体的なアクション提案]
2. [具体的なアクション提案]

#### 🔄 成功パターンの発見
以下の対応が繰り返し効果的と記録されています:
- 「[triggerTag]」時 → [action] (Effective [N]回)
  → **CarePreference への登録を推奨**

#### 👥 現場スタッフの状況
[negativePercent > 50% のスタッフがいる場合]
[staffName]さんの記録に占めるネガティブ感情の割合が[X]%です。面談を推奨します。
```

---

## 全クライアント一括スキャン

特定のクライアント名を指定せず、全クライアントを一括でスキャンする場合:

```cypher
// 全クライアントの直近7日間の感情サマリー
MATCH (c:Client)<-[:ABOUT]-(log:SupportLog)
WHERE log.date >= date() - duration({days: 7})
  AND log.emotion IS NOT NULL
WITH c.name AS clientName,
     count(log) AS totalLogs,
     count(CASE WHEN log.emotion IN ['Anger', 'Sadness', 'Fear', 'Disgust', 'Anxiety'] THEN 1 END) AS negativeLogs
WHERE totalLogs >= 3
RETURN clientName, totalLogs, negativeLogs,
       round(toFloat(negativeLogs) / totalLogs * 100, 1) AS negativePercent
ORDER BY negativePercent DESC
```

negativePercent が高いクライアントから順に詳細分析を実施する。

---

## 関連スキル
- `emergency-protocol`: リスクが「高」と判定された場合に自動連動
- `resilience-checker`: 家族の支援体制（第5の柱）との照合
- `neo4j-support-db`: 支援記録の登録・参照
- `visit-prep`: 訪問前ブリーフィングでインサイト情報を活用

## バージョン
- v2.0.0 (2026-03-30) - 5段階分析、emergency-protocol連動、CarePattern自動発見、lib/insight_engine.py 統合
- v1.0.0 (2026-03-20) - 初版
