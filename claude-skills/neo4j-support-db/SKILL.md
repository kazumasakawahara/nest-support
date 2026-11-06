---
name: neo4j-support-db
description: 親なき後支援の個人の側の DB（nest-support）を読むスキル。本人の禁忌・推奨ケア・キーパーソン・関わっている機関・手帳と受給者証・支援記録・確認の状況を、仮名（displayCode、例 C-7K3M9Q）で照会する。「C-… さんの情報」「禁忌事項」「ケア方法」「支援記録」「手帳の更新」「未確定の一覧」「利用者を照会」などの発言時に使う。読むだけで、DB には書かない（書くのはゲート）。
---

# neo4j-support-db：個人の側を読む

## 概要

個人の側の DB（127.0.0.1:37687）を、MCP の包み `nest-personal` で読む（計画 N-27a。ADR-001 D6・D11-2）。

- **読むだけ。** 書き込み（登録・更新・承認）はこのスキルでしない。語りや記録からの登録は `narrative-extractor` が案を作り、ゲート（`nest/gate/`）が書く。承認は職員が一つずつ行う
- **本人は仮名（`displayCode`）で呼ぶ。** 名前を受け取る道具は無い。名前から仮名を引くのは Claude の外で行う（SEMANTICS SEM-REC-02）
- 緊急の言葉（パニック・事故・急病・SOS）が出たら `emergency-protocol` に切り替える

## 道具

| 道具（MCP `nest-personal`） | 使い方 |
|---|---|
| `read_personal_cypher(query, params)` | 下の照会を流す。読み取り以外・`LOAD CSV`・許可外の手続きは拒否される。最大 500 行 |
| `read_quote(record_id)` | 根拠の記録の引用（`quote`）を 200 字まで返す。求められたときだけ使う |
| `personal_schema()` | 正典の JSON（ラベル・リレーション・列挙値） |
| `read_resource_cypher(query, params)`（MCP `nest-resource`） | 機関の名前を `orgId` から引く（資源の側） |

包みが返さないもの：実名・かな・電話・住所・生年月日、記録の原文全体（`text`）。照会にこれらの項目の名前を書くと拒否される。年齢も出せない（生年月日を返さないため）。人は `personId` と続柄（`RELATED_TO.kind`）で示す。

## 読み方の決まり

1. **状態**：`Active` はそのまま、`Pending` は「未確定」と添える（禁忌は未確定でも警告として出す）。`Inactive` は出さない
2. **確度**：事実のノード（禁忌・推奨ケアなど）は確度を持たない。根拠の記録（`EVIDENCED_BY` → `Record`）の `certainty` を並べ、強い順（確認済み＞本人の話＞伝聞＞推測＞確度の記載なし）で一番強いものと、最も新しい `heardOn` を添える。表示名は `docs/SEMANTICS.md` SEM-ENUM-01
3. **食い違い**：解決していない `CONTRADICTS`（`resolvedAt` が無いもの）があれば「食い違いあり」と添える。上書きしない
4. **0 件を「なし」と言わない**：禁忌・推奨ケア・キーパーソン・後見・手帳・親の担ってきた役割が 0 件のとき、その領域の確認（`Review`）が無ければ「未確認」と出す。確認があれば「確認済み（0 件）」と、確認の日と情報源を添える。「禁忌なし」「特にありません」と書かない
5. **禁忌を最初に出す**：生命に関わる → パニックを招く → 不快・ストレス の順
6. 照会は必ず `$param` で値を渡す。文字列をつないで Cypher を作らない
7. 照会の結果の `truncated` が true のときは、一覧が上限（`maxRows`、500 行）で切れていることを答えに書き、仮名や期間で絞り直す（台帳 G-87）

## 照会

### 1. 本人の一覧

```cypher
MATCH (c:Client)
WHERE c.status IN ['Active', 'Pending']
RETURN c.displayCode AS code, c.status AS status
ORDER BY code
```

### 2. 禁忌（最初に出す）

```cypher
MATCH (c:Client {displayCode: $code})-[:MUST_AVOID]->(n:NgAction)
WHERE n.status IN ['Active', 'Pending']
OPTIONAL MATCH (n)-[:EVIDENCED_BY]->(r:Record)
OPTIONAL MATCH (x:Record)-[k:CONTRADICTS]->(n) WHERE k.resolvedAt IS NULL
OPTIONAL MATCH (n)-[:IN_CONTEXT]->(cd:Condition)
RETURN n.ngActionId AS id, n.action AS action, n.riskLevel AS riskLevel, n.reason AS reason, n.status AS status,
       collect(DISTINCT {recordId: r.recordId, certainty: r.certainty, heardOn: r.heardOn}) AS evidence,
       count(DISTINCT k) AS openContradictions, collect(DISTINCT cd.name) AS conditions
ORDER BY CASE n.riskLevel WHEN 'LifeThreatening' THEN 0 WHEN 'Panic' THEN 1 ELSE 2 END
```

### 3. 推奨ケア

```cypher
MATCH (c:Client {displayCode: $code})-[:REQUIRES]->(p:CarePreference)
WHERE p.status IN ['Active', 'Pending']
OPTIONAL MATCH (p)-[:EVIDENCED_BY]->(r:Record)
OPTIONAL MATCH (p)-[:RESPONDS_TO]->(cd:Condition)
RETURN p.carePreferenceId AS id, p.category AS category, p.instruction AS instruction, p.priority AS priority,
       p.status AS status, collect(DISTINCT {recordId: r.recordId, certainty: r.certainty, heardOn: r.heardOn}) AS evidence,
       collect(DISTINCT cd.name) AS conditions
ORDER BY CASE p.priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END
```

### 4. 特性・本人の願い・生活の歴史

```cypher
MATCH (c:Client {displayCode: $code})
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(cd:Condition) WHERE cd.status IN ['Active', 'Pending']
OPTIONAL MATCH (c)-[:HAS_WISH]->(w:Wish) WHERE w.status IN ['Active', 'Pending']
OPTIONAL MATCH (c)-[:HAS_HISTORY]->(h:LifeHistory) WHERE h.status IN ['Active', 'Pending']
RETURN collect(DISTINCT {name: cd.name, diagnosisDate: cd.diagnosisDate, status: cd.status}) AS conditions,
       collect(DISTINCT {content: w.content, status: w.status}) AS wishes,
       collect(DISTINCT {era: h.era, episode: h.episode, status: h.status}) AS history
```

### 5. 支える人（キーパーソン・家族・主治医など）

```cypher
MATCH (p:Person)-[rt:RELATED_TO]->(c:Client {displayCode: $code})
WHERE rt.status IN ['Active', 'Pending'] AND rt.until IS NULL
RETURN p.personId AS personId, rt.kind AS kind, rt.rank AS rank, rt.certainty AS certainty, rt.status AS status,
       rt.evidenceRecordIds AS evidenceRecordIds
ORDER BY CASE rt.kind WHEN 'KeyPerson' THEN 0 ELSE 1 END, rt.rank
```

### 6. 関わっている機関・後見

```cypher
MATCH (i:Involvement)-[:CONCERNS]->(c:Client {displayCode: $code})
WHERE i.status IN ['Active', 'Pending']
OPTIONAL MATCH (o:Organization)-[:HAS_INVOLVEMENT]->(i)
OPTIONAL MATCH (p:Person)-[:HAS_INVOLVEMENT]->(i)
RETURN i.involvementId AS id, i.kind AS kind, i.guardianshipType AS guardianshipType, i.serviceTypeName AS service,
       i.howEnded AS howEnded, i.certainty AS certainty, i.inferenceBasis AS inferenceBasis, i.startDate AS startDate,
       i.endDate AS endDate, i.status AS status, o.orgId AS orgId, p.personId AS personId
ORDER BY i.kind
```

機関の名前は資源の側から引く（`orgId` が無い関わりは「機関未確定」と出す）。

```cypher-resource
MATCH (o:Organization)
WHERE o.orgId IN $orgIds
RETURN o.orgId AS orgId, o.name AS name, o.kind AS kind
```

### 7. 手帳・受給者証・年金と手当

```cypher
MATCH (c:Client {displayCode: $code})
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(ct:Certificate) WHERE ct.status IN ['Active', 'Pending']
OPTIONAL MATCH (c)-[:RECEIVES]->(pa:PublicAssistance) WHERE pa.status IN ['Active', 'Pending']
RETURN collect(DISTINCT {type: ct.type, grade: ct.grade, issuedDate: ct.issuedDate, nextRenewalDate: ct.nextRenewalDate,
                         status: ct.status}) AS certificates,
       collect(DISTINCT {type: pa.type, startDate: pa.startDate, endDate: pa.endDate, status: pa.status}) AS assistance
```

### 8. 更新期限が近い手帳・受給者証（全員）

```cypher
MATCH (c:Client)-[:HAS_CERTIFICATE]->(ct:Certificate)
WHERE ct.status = 'Active' AND ct.nextRenewalDate IS NOT NULL
  AND ct.nextRenewalDate <= date() + duration({days: $days})
RETURN c.displayCode AS code, ct.type AS type, ct.nextRenewalDate AS nextRenewalDate
ORDER BY nextRenewalDate
```

### 9. 確認の状況（0 件の判定に使う）

```cypher
MATCH (v:Review)-[:ABOUT]->(c:Client {displayCode: $code})
WHERE v.status IN ['Active', 'Pending']
RETURN v.domain AS domain, max(v.reviewedAt) AS lastReviewedAt,
       collect(DISTINCT v.informantKind) AS informantKinds
```

領域（`domain`）と数える先：`NgAction`＝禁忌、`CarePreference`＝推奨ケア、`KeyPerson`＝`RELATED_TO {kind: 'KeyPerson'}`、`Guardianship`＝`kind: 'Guardianship'` の関わり、`Certificate`＝手帳・受給者証、`CareRole`＝親の担ってきた役割（`ROLE_FOR`）。

### 10. 支援記録（新しい順）

```cypher
MATCH (s:SupportLog)-[:ABOUT]->(c:Client {displayCode: $code})
WHERE s.status IN ['Active', 'Pending']
RETURN s.supportLogId AS id, s.date AS date, s.situation AS situation, s.action AS action,
       s.effectiveness AS effectiveness, s.nextAction AS nextAction, s.status AS status
ORDER BY s.date DESC
LIMIT $limit
```

### 11. 効果のあったケア（場面ごと）

```cypher
MATCH (s:SupportLog)-[:ABOUT]->(c:Client {displayCode: $code})
WHERE s.status = 'Active' AND s.effectiveness = 'Effective'
RETURN s.situation AS situation, s.action AS action, count(*) AS times, max(s.date) AS lastDate
ORDER BY times DESC
```

### 12. 根拠の記録と引用

```cypher
MATCH (n {status: 'Active'})-[:EVIDENCED_BY]->(r:Record)-[:ABOUT]->(c:Client {displayCode: $code})
WHERE n.ngActionId = $id OR n.carePreferenceId = $id
OPTIONAL MATCH (r)-[:TOLD_BY]->(p:Person)
RETURN r.recordId AS recordId, r.kind AS kind, r.certainty AS certainty, r.informantKind AS informantKind,
       r.heardOn AS heardOn, r.aboutDate AS aboutDate, p.personId AS toldBy
ORDER BY r.heardOn DESC
```

引用が要るときは、`recordId` ごとに `read_quote` を呼ぶ。

### 13. 未確定（承認待ち）の一覧

古いものから点検するため、古い順に並べる。

```cypher
MATCH (n {status: 'Pending', origin: 'AiExtracted'})
WHERE n:NgAction OR n:CarePreference OR n:Condition OR n:Wish OR n:LifeHistory OR n:Involvement OR n:Record
RETURN labels(n)[0] AS label, n.registeredAt AS registeredAt,
       coalesce(n.ngActionId, n.carePreferenceId, n.conditionId, n.wishId, n.lifeHistoryId, n.involvementId, n.recordId) AS id
ORDER BY registeredAt
```

承認は職員がゲートの承認の操作で一つずつ行う（正典 §7）。このスキルからは承認しない。

### 14. 解決していない食い違い

```cypher
MATCH (r:Record)-[k:CONTRADICTS]->(n)
WHERE k.resolvedAt IS NULL
MATCH (r)-[:ABOUT]->(c:Client {displayCode: $code})
RETURN labels(n)[0] AS label, r.recordId AS recordId, k.claim AS claim, k.raisedAt AS raisedAt
ORDER BY raisedAt
```

### 15. 本人についての操作の記録

拾う範囲は、本人のノードと、本人と直接つながるノード（禁忌・推奨ケア・記録・関わりなど）の操作まで。二つ先のノード（事実の根拠の記録の先など）の操作は拾わない（台帳 G-67）。

```cypher
MATCH (c:Client {displayCode: $code})
OPTIONAL MATCH (c)--(t) WHERE NOT t:AuditLog
WITH c, collect(DISTINCT t) + c AS targets
UNWIND targets AS t
MATCH (a:AuditLog)-[:AUDIT_FOR]->(t)
OPTIONAL MATCH (a)-[:ACTED_BY]->(s:Staff)
RETURN a.at AS at, a.action AS action, a.targetLabel AS targetLabel, a.targetId AS targetId, s.staffId AS staffId
ORDER BY at DESC
LIMIT $limit
```

## 権利擁護の視点

本人を管理の対象ではなく、歴史と意思を持つ一人の人として読む。本人の願い（照会 4）と、本人の話（確度「本人の話」）の記録を、支援者の観察と同じ重さで出す。

## 関連スキル

| スキル | いつ |
|---|---|
| `emergency-protocol` | 緊急の言葉が出たとき |
| `narrative-extractor` | 語り・記録から書き込みの案を作るとき |
| `visit-prep` | 訪問の前の準備 |
| `data-quality-agent` | 欠け・食い違い・期限の点検 |
