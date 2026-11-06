---
name: visit-prep
description: 訪問・同行支援の前に、本人（仮名 displayCode、例 C-7K3M9Q）の禁忌・推奨ケア・特性・前回からの申し送り・更新期限を個人の側の DB から読み、短い訪問前ブリーフィングを作るスキル。「訪問準備」「訪問前に確認」「明日 C-… さんのところに行く」「同行支援の注意点」「ブリーフィング」などの発言時に使う。読むだけで、DB には書かない。
---

# visit-prep：訪問前ブリーフィング

## なぜ要るか

訪問で最も危ないのは「知らなかったこと」による事故。禁忌を知らずにパニックを招く、前回の問題を知らずに同じことを繰り返す、を防ぐ（計画 N-27b）。

## 道具と決まり

- 個人の側は MCP `nest-personal` の `read_personal_cypher`、機関の名前は `nest-resource` の `read_resource_cypher` で読む。読むだけ
- 本人は仮名（`displayCode`）で呼ぶ。名前は受け取らない（SEMANTICS SEM-REC-02）
- 包みは実名・電話・住所・生年月日・記録の原文を返さない。**連絡先の電話番号はブリーフィングに出せない。** 「連絡先は事業所の連絡網・紙の緊急連絡カードで確かめる」と書く
- 読み方の決まり（未確定の添え方、確度の出し方、0 件を「なし」と言わない）は `neo4j-support-db` の「読み方の決まり」と同じ
- 訪問の目的は職員から聞く。推し量って書かない

## 手順

1. 職員から仮名と訪問の目的・日を聞く
2. 下の照会 1〜4 を流す（`$code` に仮名、`$days` は 90）
3. 禁忌が 0 件なら、照会 4 で禁忌の確認（`Review`、領域 `NgAction`）があるかを見る
4. 下の形でブリーフィングを書く。未確定（`Pending`）の項目には「未確定」と添える
5. 外出・同行支援なら「同行の追加の確認」も書く

## 照会

### 1. 禁忌と推奨ケア（安全を先に）

```cypher
MATCH (c:Client {displayCode: $code})
OPTIONAL MATCH (c)-[:MUST_AVOID]->(n:NgAction) WHERE n.status IN ['Active', 'Pending']
OPTIONAL MATCH (n)-[:EVIDENCED_BY]->(nr:Record)
OPTIONAL MATCH (n)-[:IN_CONTEXT]->(ncd:Condition)
WITH c, n, collect(DISTINCT nr.certainty) AS ngEvidence, collect(DISTINCT ncd.name) AS ngContext
WITH c, collect(CASE WHEN n IS NULL THEN NULL ELSE {action: n.action, riskLevel: n.riskLevel, reason: n.reason,
       status: n.status, evidence: ngEvidence, context: ngContext} END) AS ngActions
OPTIONAL MATCH (c)-[:REQUIRES]->(p:CarePreference) WHERE p.status IN ['Active', 'Pending']
OPTIONAL MATCH (p)-[:EVIDENCED_BY]->(pr:Record)
WITH ngActions, p, collect(DISTINCT pr.certainty) AS cpEvidence
RETURN ngActions, collect(CASE WHEN p IS NULL THEN NULL ELSE {category: p.category, instruction: p.instruction,
       priority: p.priority, status: p.status, evidence: cpEvidence} END) AS carePreferences
```

### 2. 特性と、前回からの申し送り

```cypher
MATCH (c:Client {displayCode: $code})
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(cd:Condition) WHERE cd.status IN ['Active', 'Pending']
WITH c, collect(DISTINCT {name: cd.name, status: cd.status}) AS conditions
OPTIONAL MATCH (s:SupportLog)-[:ABOUT]->(c) WHERE s.status IN ['Active', 'Pending']
WITH conditions, s ORDER BY s.date DESC
RETURN conditions, collect({date: s.date, situation: s.situation, action: s.action, effectiveness: s.effectiveness,
       nextAction: s.nextAction})[0..5] AS recentLogs
```

### 3. 支える人・関わっている機関・更新期限

```cypher
MATCH (c:Client {displayCode: $code})
OPTIONAL MATCH (p:Person)-[rt:RELATED_TO]->(c) WHERE rt.status IN ['Active', 'Pending'] AND rt.until IS NULL
WITH c, collect(DISTINCT {personId: p.personId, kind: rt.kind, rank: rt.rank}) AS people
OPTIONAL MATCH (i:Involvement)-[:CONCERNS]->(c) WHERE i.status IN ['Active', 'Pending'] AND i.howEnded = 'Ongoing'
OPTIONAL MATCH (o:Organization)-[:HAS_INVOLVEMENT]->(i)
WITH c, people, collect(DISTINCT {kind: i.kind, service: i.serviceTypeName, orgId: o.orgId}) AS involvements
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(ct:Certificate)
  WHERE ct.status = 'Active' AND ct.nextRenewalDate <= date() + duration({days: $days})
RETURN people, involvements, collect(DISTINCT {type: ct.type, nextRenewalDate: ct.nextRenewalDate}) AS renewals
```

機関の名前（`orgId` から）：

```cypher-resource
MATCH (o:Organization)
WHERE o.orgId IN $orgIds
RETURN o.orgId AS orgId, o.name AS name
```

### 4. 確認の状況（0 件のとき）

```cypher
MATCH (v:Review)-[:ABOUT]->(c:Client {displayCode: $code})
WHERE v.status = 'Active' AND v.domain IN ['NgAction', 'CarePreference', 'KeyPerson']
RETURN v.domain AS domain, max(v.reviewedAt) AS lastReviewedAt, collect(DISTINCT v.informantKind) AS informantKinds
```

## ブリーフィングの形

```text
## 訪問前ブリーフィング
対象：C-……　訪問日：……　目的：……（職員から聞いた言葉のまま）

### 絶対に避けること（生命に関わる → パニックを招く → 不快・ストレス）
- ……（根拠の確度：……、未確定なら「未確定」）
（0 件で確認が無いとき）🚨 禁忌は未確認。避けることが無いとは確かめられていない。今回の訪問で聞き取る
（0 件で確認があるとき）✅ 確認済み（0 件）— 確認の日・情報源

### 効果的な関わり方
- 推奨ケア（優先度の順）／効果のあった支援記録

### 特性
### 支える人・関わっている機関（連絡先は連絡網で確かめる）
### 前回からの申し送り（直近 5 件）
### 確認すべき期限（90 日以内の更新）
```

## 同行の追加の確認（外出・同行支援のとき）

- パニックの引き金：禁忌の `context`（`IN_CONTEXT` の特性）から外出に関わるもの
- 落ち着ける方法：推奨ケアから、パニックのときの関わり方
- 持ち物（薬・緊急連絡カード・好きな物）は職員に確かめるよう書く。DB から推し量らない

## 出力

ファイルにするときは `html-to-pdf`。ファイルを外のサービスに上げない。

## 関連スキル

`neo4j-support-db`（詳しい照会）、`emergency-protocol`（緊急時）、`resilience-checker`（親なき後の診断）
