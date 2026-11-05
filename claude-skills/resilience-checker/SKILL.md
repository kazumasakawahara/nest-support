---
name: resilience-checker
description: 「もし親が倒れたら」を考え、親が担っている役割（CareRole）に代わりの担い手がいるかを本人（仮名 displayCode）ごとに診断するスキル。マニフェストの第 5 の柱「親の機能移行」の中核。「レジリエンス」「親なき後」「もしもの時」「親が倒れたら」「カバー率」「バックアップ体制」「機能移行」「親の入院」「親が認知症」などの話題、parent_down のプロトコルのときに使う。読むだけ。
---

# resilience-checker：親なき後の診断

## 意義

親が日々担っている役割（食事の用意・服薬・金銭の管理・送迎など）を洗い出し、それぞれに代わりの担い手がいるかを見て、支援の体制の弱いところを先に見つける（計画 N-27e）。

## 道具と決まり

- 個人の側は MCP `nest-personal` の `read_personal_cypher`、機関の名前は `nest-resource` の `read_resource_cypher`。読むだけ
- 本人は仮名（`displayCode`）で呼ぶ。人は `personId` と続柄で示す（実名・電話は包みが返さない）
- 役割の登録・代わりの担い手の結び付けは、このスキルではしない。親から聞き取った話は `narrative-extractor` の案にし、ゲートで書く
- 役割（`CareRole`）が 0 件のとき、確認（`Review`、領域 `CareRole`）が無ければ「親の担っている役割は未確認」と出す。「役割なし」と書かない

## 形（正典 v0.9 §4.3）

```text
(Person 親など)-[:PERFORMS {since, until}]->(CareRole {name, frequency, priority, note})-[:ROLE_FOR]->(Client)
(CareRole)-[:CAN_BE_PERFORMED_BY]->(Person) または (Involvement：機関の関わり)
```

## 手順

1. 照会 1 で、親（続柄 `Parent`）と、親が担っている役割を見る
2. 照会 2 で、役割ごとの代わりの担い手を見る
3. 役割ごとに判定する
   - ✅ **代わりあり**：`Active` の人か、続いている（`Ongoing`）`Active` の関わりが一つ以上
   - ⚠️ **要確認**：代わりが未確定（`Pending`）だけ、または関わりの終わり方が未確認（`Unknown`）だけ
   - 🚨 **代わりなし**：代わりが一つも無い
   - 頻度が足りるか（毎日の役割を週 1 の関わりで代われるか）は、DB から決めない。職員に確かめるよう書く
4. **カバー率 ＝ 代わりありの役割の数 ÷ 役割の数**。要確認は代わりありに数えない
5. 代わりなしの役割は、優先度（`priority`）の高い順に並べ、次の手を職員と相談する。事業所の候補探しは、資源の側の照会をまだ書き直していないので、今は職員が探す（provider-search の書き直しは N-27 の外）

## 照会

### 1. 親と、親が担っている役割

```cypher
MATCH (c:Client {displayCode: $code})
OPTIONAL MATCH (parent:Person)-[rt:RELATED_TO {kind: 'Parent'}]->(c) WHERE rt.status IN ['Active', 'Pending']
WITH c, collect(DISTINCT {personId: parent.personId, until: rt.until}) AS parents
OPTIONAL MATCH (doer:Person)-[pf:PERFORMS]->(r:CareRole)-[:ROLE_FOR]->(c)
  WHERE r.status IN ['Active', 'Pending'] AND pf.until IS NULL
RETURN parents, collect(DISTINCT {careRoleId: r.careRoleId, name: r.name, frequency: r.frequency, priority: r.priority,
       status: r.status, performedBy: doer.personId}) AS roles
```

### 2. 役割ごとの代わりの担い手

```cypher
MATCH (r:CareRole)-[:ROLE_FOR]->(c:Client {displayCode: $code})
WHERE r.status IN ['Active', 'Pending']
OPTIONAL MATCH (r)-[:CAN_BE_PERFORMED_BY]->(p:Person)
OPTIONAL MATCH (p)-[rt:RELATED_TO]->(c)
OPTIONAL MATCH (r)-[:CAN_BE_PERFORMED_BY]->(i:Involvement)
OPTIONAL MATCH (o:Organization)-[:HAS_INVOLVEMENT]->(i)
RETURN r.careRoleId AS id, r.name AS role, r.frequency AS frequency, r.priority AS priority,
       collect(DISTINCT {personId: p.personId, kind: rt.kind, status: p.status}) AS people,
       collect(DISTINCT {kind: i.kind, service: i.serviceTypeName, howEnded: i.howEnded, status: i.status,
                         orgId: o.orgId}) AS involvements
ORDER BY CASE r.priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END
```

機関の名前：

```cypher-resource
MATCH (o:Organization)
WHERE o.orgId IN $orgIds
RETURN o.orgId AS orgId, o.name AS name
```

### 3. 確認の状況（役割が 0 件のとき）

```cypher
MATCH (v:Review {domain: 'CareRole'})-[:ABOUT]->(c:Client {displayCode: $code})
WHERE v.status = 'Active'
RETURN max(v.reviewedAt) AS lastReviewedAt, collect(DISTINCT v.informantKind) AS informantKinds
```

## 報告の形

```text
## 親なき後の診断：C-……
### 親の状況（続柄と人の ID。記録にあることだけ）
### 役割ごとの代わり
| 役割 | 頻度 | 優先度 | 今の担い手 | 代わり | 判定 |
### カバー率：…%（代わりあり … ／ 役割 …。要確認 … は数えていない）
### 🚨 代わりなしの役割（優先度の順）
### 次にすること（職員と相談。頻度が足りるかの確認を含む）
```

聞き取りでよく出る役割の例（登録の案を作るときの手がかり。DB に無いものを足して書かない）：食事の用意、服薬、金銭の管理、送迎、入浴、パニックのときの対応、身の回り、見守り。

## Parent Down のプロトコル

親の入院・死亡・認知症の知らせ（`manifesto/protocols/parent_down.md`）では、`emergency-protocol` の照会 1 を先に流し、その後このスキルで代わりなしの役割を出す。

## 関連スキル

`emergency-protocol`、`neo4j-support-db`、`ecomap-generator`（支える人の図）
