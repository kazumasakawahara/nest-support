---
name: ecomap-generator
description: 本人（仮名 displayCode）を真ん中に、禁忌・推奨ケア・特性・支える人・関わっている機関・親の担っている役割を、個人の側の DB から読んでエコマップ（Mermaid の図）にするスキル。「エコマップ」「関係図」「支援ネットワーク図」「ビジュアルで確認」などの話題で使う。読むだけ。
---

# ecomap-generator：エコマップ

## 意義

本人を取り巻く関係と、安全に関わる情報を一枚の図にして、支援チームの共通の理解を助ける（計画 N-27g）。

## 決まり

- 道具は MCP `nest-personal` の `read_personal_cypher`（機関の名前は `nest-resource` の `read_resource_cypher`）。読むだけ
- 本人は仮名（`displayCode`）で示す。人は続柄と `personId` の末尾 4 字で示す（実名・電話は包みが返さない）
- **DB に無いものを図に足さない。** 見本の人・見本の機関で埋めない。照会が 0 件なら、その枝は描かず、図の下に「未確認」「登録なし」を書き分ける（`neo4j-support-db` の「読み方の決まり」4）
- 未確定（`Pending`）の項目は点線でつなぎ、ラベルに「未確定」と添える
- 図のラベルは DB の文字をそのまま使うが、Mermaid の記号（`"`・`[`・`]`・`{`・`}`・`|`・`<`・`>`）は全角に置き換えてから入れる
- 前の版の D3 の動く図（HTML）、感情の推移のグラフ、リスクのバッジは外した（感情の項目は正典に無い。前の DB と前の分析の部品につながっていた）。動く図が要るなら、DB につながない描画の部品として作り直す（その計画はまだ無い）

## 照会

### 1. 図に載せるもの

```cypher
MATCH (c:Client {displayCode: $code})
OPTIONAL MATCH (c)-[:MUST_AVOID]->(n:NgAction) WHERE n.status IN ['Active', 'Pending']
WITH c, collect(DISTINCT {action: n.action, riskLevel: n.riskLevel, status: n.status}) AS ngActions
OPTIONAL MATCH (c)-[:REQUIRES]->(p:CarePreference) WHERE p.status IN ['Active', 'Pending']
WITH c, ngActions, collect(DISTINCT {category: p.category, instruction: p.instruction, status: p.status}) AS carePreferences
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(cd:Condition) WHERE cd.status IN ['Active', 'Pending']
WITH c, ngActions, carePreferences, collect(DISTINCT {name: cd.name, status: cd.status}) AS conditions
OPTIONAL MATCH (pp:Person)-[rt:RELATED_TO]->(c) WHERE rt.status IN ['Active', 'Pending'] AND rt.until IS NULL
WITH c, ngActions, carePreferences, conditions,
     collect(DISTINCT {personId: pp.personId, kind: rt.kind, rank: rt.rank, status: rt.status}) AS people
OPTIONAL MATCH (i:Involvement)-[:CONCERNS]->(c) WHERE i.status IN ['Active', 'Pending'] AND i.howEnded IN ['Ongoing', 'Unknown']
OPTIONAL MATCH (o:Organization)-[:HAS_INVOLVEMENT]->(i)
WITH c, ngActions, carePreferences, conditions, people,
     collect(DISTINCT {kind: i.kind, service: i.serviceTypeName, orgId: o.orgId, status: i.status}) AS involvements
OPTIONAL MATCH (r:CareRole)-[:ROLE_FOR]->(c) WHERE r.status IN ['Active', 'Pending']
OPTIONAL MATCH (doer:Person)-[pf:PERFORMS]->(r) WHERE pf.until IS NULL
RETURN ngActions, carePreferences, conditions, people, involvements,
       collect(DISTINCT {name: r.name, performedBy: doer.personId, status: r.status}) AS careRoles
```

### 2. 機関の名前

```cypher-resource
MATCH (o:Organization)
WHERE o.orgId IN $orgIds
RETURN o.orgId AS orgId, o.name AS name, o.kind AS kind
```

### 3. 確認の状況（0 件の枝の書き分け）

```cypher
MATCH (v:Review)-[:ABOUT]->(c:Client {displayCode: $code})
WHERE v.status = 'Active'
RETURN collect(DISTINCT v.domain) AS reviewed
```

## 図の形

```text
flowchart LR
  C(("C-……"))
  C -- 禁忌 --> NG1["🔴 生命に関わる：……"]
  C -. 禁忌（未確定） .-> NG2["🟡 パニックを招く：……（未確定）"]
  C -- 推奨ケア --> CP1["✅ ……"]
  C -- 特性 --> CD1["……"]
  P1["キーパーソン（1）…a1b2"] -- 支える --> C
  O1["相談：〇〇区役所"] -- 関わり --> C
  R1["食事の用意（母）"] -- 親の役割 --> C
```

- 色の目安：禁忌は赤・黄・緑（生命に関わる・パニックを招く・不快・ストレス）、推奨ケアは青、支える人は灰、機関は緑
- 図は `.md` のファイル（Mermaid のブロック）にして渡す。外のサービスに上げない。PDF にするときは `html-to-pdf`

## 活用場面

ケース会議、担当の引き継ぎ、親なき後の備えの話し合い（`resilience-checker` と並べる）。

## 関連スキル

`neo4j-support-db`、`resilience-checker`、`visit-prep`
