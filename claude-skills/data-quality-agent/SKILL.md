---
name: data-quality-agent
description: 個人の側の DB（nest-support）の品質を点検し、更新期限・安全の情報の未確認・たまった未確定・根拠の無い事実・食い違い・機関未確定・列挙値の外れを見つけて報告するスキル。「データ品質」「データチェック」「整合性チェック」「更新漏れ」「期限チェック」「DB 監査」「データの健全性」などの話題、月次・週次の点検、支援会議の前の確認で使う。読むだけで、直すのはゲートを通した職員の操作。
---

# data-quality-agent：データの点検

## 意義と決まり

記録の欠けや食い違いは、支援者が入れ替わったときに事故になる。定期的に点検し、**直すべきものを職員に並べて返す**（計画 N-27d）。

- **読むだけ。** 直す（足す・無効にする・承認する）のはゲートを通した職員の操作。このスキルから書かない
- 道具は MCP `nest-personal` の `read_personal_cypher`。本人は仮名（`displayCode`）で示す
- 包みは実名・電話・住所・生年月日・記録の原文を返さない。点検にそれらは使わない
- 「古い」の日数（`$days`）は職員に聞く。こちらで決めない
- 深刻度：**要対応**（安全・期限に直結）／**注意**／**参考**

## 点検の一覧

| # | 点検 | 深刻度 |
|---|---|---|
| 1 | 手帳・受給者証の更新期限（過ぎた・近い）、等級の書かれていない手帳 | 要対応／注意 |
| 2 | 安全の情報の未確認（禁忌・キーパーソン・後見が 0 件で、その領域の確認が無い） | 要対応 |
| 3 | たまった未確定（`Pending`）と、いちばん古いものの登録日 | 注意 |
| 4 | 根拠の記録の無い事実（`EVIDENCED_BY` が無い） | 注意 |
| 5 | 解決していない食い違い（`CONTRADICTS`） | 注意 |
| 6 | 機関未確定の関わり・終わり方を確かめていない関わり | 参考 |
| 7 | キーパーソンの順位の重なり・欠け | 注意 |
| 8 | 列挙値の外れ（ゲートを通らずに入ったもの） | 参考 |

意味の近い禁忌どうしで危険の度合いがばらついていないかの点検（前の版の「重みの横断の一貫性」）は、埋め込みをやめたので行わない（ADR-001 D10）。

## 照会

### 1. 更新期限

```cypher
MATCH (c:Client)-[:HAS_CERTIFICATE]->(ct:Certificate)
WHERE ct.status = 'Active' AND ct.nextRenewalDate IS NOT NULL AND ct.nextRenewalDate <= date() + duration({days: $days})
RETURN c.displayCode AS code, ct.type AS type, ct.nextRenewalDate AS nextRenewalDate,
       CASE WHEN ct.nextRenewalDate < date() THEN 'Overdue' ELSE 'Soon' END AS state
ORDER BY nextRenewalDate
```

```cypher
MATCH (c:Client)-[:HAS_CERTIFICATE]->(ct:Certificate)
WHERE ct.status = 'Active' AND ct.grade IS NULL AND ct.type IN ['IntellectualDisabilityHandbook', 'PhysicalDisabilityHandbook', 'MentalDisabilityHandbook']
RETURN c.displayCode AS code, ct.type AS type, ct.certificateId AS id
```

### 2. 安全の情報の未確認

```cypher
MATCH (c:Client) WHERE c.status = 'Active'
OPTIONAL MATCH (c)-[:MUST_AVOID]->(n:NgAction) WHERE n.status IN ['Active', 'Pending']
WITH c, count(n) AS ng
OPTIONAL MATCH (p:Person)-[rt:RELATED_TO {kind: 'KeyPerson'}]->(c) WHERE rt.status IN ['Active', 'Pending'] AND rt.until IS NULL
WITH c, ng, count(p) AS keyPersons
OPTIONAL MATCH (i:Involvement {kind: 'Guardianship'})-[:CONCERNS]->(c) WHERE i.status IN ['Active', 'Pending']
WITH c, ng, keyPersons, count(i) AS guardianship
OPTIONAL MATCH (v:Review)-[:ABOUT]->(c) WHERE v.status = 'Active'
WITH c, ng, keyPersons, guardianship, collect(DISTINCT v.domain) AS reviewed
WHERE (ng = 0 AND NOT 'NgAction' IN reviewed) OR (keyPersons = 0 AND NOT 'KeyPerson' IN reviewed)
   OR (guardianship = 0 AND NOT 'Guardianship' IN reviewed)
RETURN c.displayCode AS code, ng, keyPersons, guardianship, reviewed
ORDER BY code
```

報告では「禁忌は未確認」のように書く。「禁忌なし」と書かない。

### 3. たまった未確定

```cypher
MATCH (n {status: 'Pending'})
WHERE n:NgAction OR n:CarePreference OR n:Condition OR n:Wish OR n:LifeHistory OR n:Involvement OR n:Record OR n:Person
RETURN labels(n)[0] AS label, count(*) AS pending, min(n.registeredAt) AS oldest
ORDER BY pending DESC
```

### 4. 根拠の記録の無い事実

```cypher
MATCH (n)
WHERE (n:NgAction OR n:CarePreference OR n:Condition OR n:Wish OR n:LifeHistory OR n:CareRole OR n:Certificate
       OR n:PublicAssistance OR n:SupportLog OR n:Involvement OR n:Residence)
  AND n.status IN ['Active', 'Pending'] AND NOT (n)-[:EVIDENCED_BY]->(:Record)
RETURN labels(n)[0] AS label, count(*) AS withoutEvidence
ORDER BY withoutEvidence DESC
```

### 5. 解決していない食い違い

```cypher
MATCH (r:Record)-[k:CONTRADICTS]->(n)
WHERE k.resolvedAt IS NULL
OPTIONAL MATCH (r)-[:ABOUT]->(c:Client)
RETURN c.displayCode AS code, labels(n)[0] AS label, k.raisedAt AS raisedAt
ORDER BY raisedAt
```

### 6. 機関未確定・終わり方を確かめていない関わり

```cypher
MATCH (i:Involvement)-[:CONCERNS]->(c:Client)
WHERE i.status IN ['Active', 'Pending']
OPTIONAL MATCH (x)-[:HAS_INVOLVEMENT]->(i)
WITH c, i, count(x) AS holders
WHERE holders = 0 OR i.howEnded = 'Unknown'
RETURN c.displayCode AS code, i.kind AS kind, holders = 0 AS orgUnknown, i.howEnded = 'Unknown' AS endUnknown
ORDER BY code
```

勤め先（`Employment`）は資源の側に載らないので、機関未確定でよい（正典 §4.5）。報告から外す。

### 7. キーパーソンの順位（欠け・重なり）

```cypher
MATCH (p:Person)-[rt:RELATED_TO {kind: 'KeyPerson'}]->(c:Client)
WHERE rt.status = 'Active' AND rt.until IS NULL
WITH c, rt.rank AS rank, count(*) AS n
WHERE rank IS NULL OR n > 1
RETURN c.displayCode AS code, rank, n
ORDER BY code
```

### 8. 列挙値の外れ

```cypher
MATCH (n:NgAction) WHERE NOT n.riskLevel IN ['LifeThreatening', 'Panic', 'Discomfort']
RETURN 'NgAction.riskLevel' AS field, n.riskLevel AS value, count(*) AS n
UNION ALL
MATCH (p:CarePreference) WHERE p.priority IS NOT NULL AND NOT p.priority IN ['High', 'Medium', 'Low']
RETURN 'CarePreference.priority' AS field, p.priority AS value, count(*) AS n
UNION ALL
MATCH (s:SupportLog) WHERE s.effectiveness IS NOT NULL AND NOT s.effectiveness IN ['Effective', 'Ineffective', 'Neutral', 'Unknown']
RETURN 'SupportLog.effectiveness' AS field, s.effectiveness AS value, count(*) AS n
UNION ALL
MATCH (r:Record) WHERE NOT r.certainty IN ['Confirmed', 'Hearsay', 'SelfReport', 'Inference', 'Unspecified']
RETURN 'Record.certainty' AS field, r.certainty AS value, count(*) AS n
```

値の一覧は正典（`personal_schema()` の `enums`）が正。ここに写した値とずれたら、正典に合わせて直す。

### 全体の数

```cypher
MATCH (n)
WHERE n.status IS NOT NULL
RETURN labels(n)[0] AS label, n.status AS status, count(*) AS n
ORDER BY label, status
```

## 報告の形

```text
## データ品質の報告（日付）
### 要対応
- 期限：……（仮名・種類・期限）
- 安全の情報の未確認：……（仮名・どの領域）
### 注意
- 未確定：……件（いちばん古いもの：……）／根拠の無い事実／食い違い／キーパーソンの順位
### 参考
- 機関未確定・終わり方未確認／列挙値の外れ
### 次にすること（職員の操作。このスキルからは直さない）
```

## 関連スキル

`neo4j-support-db`（本人ごとの照会）、`resilience-checker`、`schedule`（定期の実行）
