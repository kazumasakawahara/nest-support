---
name: insight-agent
description: 支援記録（SupportLog）の積み重ねから、効果のなくなってきた場面、同じ場面での不調の繰り返し、効果のあった関わり方、職員ごとの記録の偏りを本人（仮名 displayCode）ごとに読み、「予兆」として管理者に報告するスキル。「最近の変化」「様子がおかしい」「予兆」「リスク分析」「トレンド」「スタッフの状況」などの話題で使う。読むだけ。
---

# insight-agent：予兆の分析

## 意義と決まり

支援記録の小さな変化から、悪化の兆しや、うまくいっている関わり方を早めに見つける（計画 N-27h）。

- 道具は MCP `nest-personal` の `read_personal_cypher`。読むだけ
- 本人は仮名（`displayCode`）、職員は `staffId` で示す
- **数字を出し、判断は職員に渡す。** 「リスクが高い」と決める数え方（閾値）は決まっていない。比べる日数（`$days`）は職員に聞く。こちらで決めない
- 件数が少ないとき（目安として比べる期間のどちらかが 5 件未満）は「記録が少なく、変化と言えない」と書く
- 感情の推移（前の版の Emotion Drift）は行わない。感情・きっかけの項目は正典に無い（原文に無い評価を足さないため。N-26）
- 効果のあった関わり方を推奨ケアにするのは、このスキルではしない。職員が根拠の記録を添えて、`narrative-extractor` の案からゲートで登録する（推奨ケアには根拠の記録が要る。台帳 G-63）
- 職員が「危ない」と判断したら、`emergency-protocol` の照会 1 を先に流す

## 照会

### 1. 効果の推移（直近の期間と、その前の同じ長さの期間）

```cypher
MATCH (s:SupportLog)-[:ABOUT]->(c:Client {displayCode: $code})
WHERE s.status = 'Active' AND s.date >= date() - duration({days: 2 * $days})
WITH s, CASE WHEN s.date >= date() - duration({days: $days}) THEN 'Recent' ELSE 'Before' END AS period
RETURN period, count(*) AS logs,
       sum(CASE s.effectiveness WHEN 'Effective' THEN 1 ELSE 0 END) AS effective,
       sum(CASE s.effectiveness WHEN 'Ineffective' THEN 1 ELSE 0 END) AS ineffective
ORDER BY period
```

### 2. 同じ場面での不調の繰り返し

```cypher
MATCH (s:SupportLog)-[:ABOUT]->(c:Client {displayCode: $code})
WHERE s.status = 'Active' AND s.effectiveness = 'Ineffective' AND s.date >= date() - duration({days: $days})
RETURN s.situation AS situation, count(*) AS times, collect(s.action)[0..5] AS actions, max(s.date) AS lastDate
ORDER BY times DESC
```

不調の場面が禁忌の場面と重なっていないかは、`neo4j-support-db` の照会 2（禁忌）と並べて職員が見る。

### 3. 効果のあった関わり方

```cypher
MATCH (s:SupportLog)-[:ABOUT]->(c:Client {displayCode: $code})
WHERE s.status = 'Active' AND s.effectiveness = 'Effective'
WITH s.situation AS situation, s.action AS action, count(*) AS times, max(s.date) AS lastDate
WHERE times >= $minTimes
OPTIONAL MATCH (c2:Client {displayCode: $code})-[:REQUIRES]->(p:CarePreference)
  WHERE p.status IN ['Active', 'Pending'] AND p.instruction CONTAINS action
RETURN situation, action, times, lastDate, count(p) > 0 AS alreadyCarePreference
ORDER BY times DESC
```

`alreadyCarePreference` が偽で回数が多いものは、推奨ケアの候補として職員に知らせる（登録はしない）。

### 4. 職員ごとの記録の数（負担の偏り）

```cypher
MATCH (s:SupportLog)-[:AUTHORED_BY]->(st:Staff)
WHERE s.status = 'Active' AND s.date >= date() - duration({days: $days})
OPTIONAL MATCH (s)-[:ABOUT]->(c:Client)
RETURN st.staffId AS staffId, count(DISTINCT s) AS logs, count(DISTINCT c) AS clients,
       sum(CASE s.effectiveness WHEN 'Ineffective' THEN 1 ELSE 0 END) AS ineffective
ORDER BY logs DESC
```

### 5. 全員の一括の見渡し

```cypher
MATCH (s:SupportLog)-[:ABOUT]->(c:Client)
WHERE s.status = 'Active' AND s.date >= date() - duration({days: $days})
RETURN c.displayCode AS code, count(*) AS logs,
       sum(CASE s.effectiveness WHEN 'Ineffective' THEN 1 ELSE 0 END) AS ineffective,
       max(s.date) AS lastLog
ORDER BY ineffective DESC, logs DESC
```

記録の途切れ（`lastLog` が古い本人）も、予兆として挙げる。

## 報告の形

```text
### 📢 予兆の報告：C-……（期間：直近 … 日と、その前の … 日）
#### 効果の推移（件数と、効果なしの数。記録が少なければそう書く）
#### 同じ場面での不調の繰り返し
#### 効果のあった関わり方（推奨ケアの候補。登録はしていない）
#### 職員の記録の偏り（全体のとき）
#### 職員に確かめてほしいこと（判断は職員。危ないと判断したら emergency-protocol）
```

## 関連スキル

`emergency-protocol`、`neo4j-support-db`、`narrative-extractor`（推奨ケアの案）、`data-quality-agent`
