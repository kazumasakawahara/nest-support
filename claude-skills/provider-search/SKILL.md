---
name: provider-search
description: 事業所・機関の公開情報（名前・種別・所在・電話・提供するサービス・対象の区域）を、tsunagu-net の資源の DB から読むスキル。本人（仮名 displayCode）が関わっている機関の一覧と、同じ区域で同じサービスを出している別の事業所（代わりの候補）も示す。「事業所を探して」「近くの〇〇」「どこが使える」「代わりの事業所」「この事業所の連絡先」などの発言時に使う。読むだけ。
---

# provider-search：事業所を探す（読むだけ）

## なぜ要るか

親が倒れたとき、今の事業所が受けられないとき、職員は「同じ区域で同じサービスを出しているところ」をすぐに知りたい。事業所の情報は公開情報なので、tsunagu-net の資源の DB にまとめて持ち、nest は読むだけにする（計画 N-27i）。

## 決まり

- **資源の側（事業所の公開情報）は MCP `nest-resource` の `read_resource_cypher` で読む**（下の ```` ```cypher-resource ```` の照会）。tsunagu-net の正典 §5 のとおりで、nest からは書かない
- **本人の側（誰がどこに関わっているか）は MCP `nest-personal` の `read_personal_cypher` で読む**（下の ```` ```cypher ```` の照会）。本人は仮名（`displayCode`）で呼ぶ
- 二つの DB はまたげない。本人の側で関わりの `orgId` を取り、それを資源の側の照会に `$orgIds` として渡す
- 事業所の電話・所在地は公開情報なので示してよい。本人や家族の電話は、このスキルでは出さない（個人の側の包みが止める）
- **前の版の口コミ（評価・コメント）と、空き状況の更新・利用の紐付けの書き込みは、やめた。** 口コミは個人の評価を含み、正典に置き場所が無い。利用の関わり（`Involvement`）を足すのは、職員がゲートを通して行う
- 資源の DB の情報は確かめた日（`checkedOn`）とともに示す。古ければ「電話で確かめてから」と添える。空き状況はこの DB に無い。必ず電話で確かめる

## 照会

### 1. 名前で探す（資源の側。`$name` は空白を除いた名前の一部）

```cypher-resource
MATCH (o:Organization {status: 'Active'})
WITH o, replace(replace(normalize(o.name, NFKC), ' ', ''), '　', '') AS own
OPTIONAL MATCH (o)-[:HAS_NAME]->(x:OrgName)
WITH o, own, collect(replace(replace(normalize(x.name, NFKC), ' ', ''), '　', '')) AS aliases
WHERE own CONTAINS $name OR any(a IN aliases WHERE a CONTAINS $name)
RETURN o.orgId AS orgId, o.name AS name, o.kind AS kind, o.checkedOn AS checkedOn
ORDER BY name, orgId
LIMIT $limit
```

### 2. 区域とサービスの種類で探す（資源の側。`$areaCode` は区域の番号、`$serviceType` はサービスの名前の一部）

```cypher-resource
MATCH (a:Area {areaCode: $areaCode})-[:PART_OF*0..2]->(x:Area)<-[r:SERVES]-(o:Organization {status: 'Active'})
MATCH (o)-[:PROVIDES]->(s:Service {status: 'Active'})
WHERE s.serviceTypeName CONTAINS $serviceType
RETURN DISTINCT o.orgId AS orgId, o.name AS name, o.kind AS kind, s.serviceTypeName AS service,
       s.capacity AS capacity, r.basis AS servesBasis, coalesce(r.partOfArea, false) AS partOfArea,
       x.areaCode <> $areaCode AS viaParent, o.checkedOn AS checkedOn
ORDER BY viaParent, name, orgId
LIMIT $limit
```

区域を受け持つ（`SERVES`）ことが分からない事業所は、所在（`LOCATED_IN`）で探す。

```cypher-resource
MATCH (o:Organization {status: 'Active'})-[:LOCATED_IN]->(a:Area {areaCode: $areaCode})
MATCH (o)-[:PROVIDES]->(s:Service {status: 'Active'})
WHERE s.serviceTypeName CONTAINS $serviceType
RETURN DISTINCT o.orgId AS orgId, o.name AS name, o.kind AS kind, s.serviceTypeName AS service, o.checkedOn AS checkedOn
ORDER BY name, orgId
LIMIT $limit
```

### 3. 事業所の詳しい公開情報（資源の側。`$orgIds`）

```cypher-resource
MATCH (o:Organization)
WHERE o.orgId IN $orgIds
OPTIONAL MATCH (o)-[:PROVIDES]->(s:Service)
WHERE s.status IN ['Active', 'Pending']
RETURN o.orgId AS orgId, o.name AS name, o.kind AS kind, o.status AS status, o.corporateName AS corporateName,
       o.address AS address, o.phone AS phone, o.sourceUrl AS sourceUrl, o.checkedOn AS checkedOn,
       collect(DISTINCT s.serviceTypeName) AS services
ORDER BY name
```

`status` が `Active` でない事業所は「廃止・休止の届けがあった」と添える。

### 4. 本人が関わっている機関（本人の側）

```cypher
MATCH (o:Organization)-[:HAS_INVOLVEMENT]->(i:Involvement)-[:CONCERNS]->(c:Client {displayCode: $code})
WHERE i.status IN ['Active', 'Pending'] AND i.endDate IS NULL
RETURN o.orgId AS orgId, i.kind AS kind, i.serviceTypeName AS service, i.startDate AS startDate,
       i.status = 'Pending' AS unconfirmed
ORDER BY kind
```

ここで得た `orgId` を照会 3 に渡して、名前と連絡先を示す。`unconfirmed` が真のものは「未確定」と書く。

### 5. 代わりの候補

照会 4 で今のサービス（`service`）と `orgId` を得て、本人の住む区域（職員に聞く）で照会 2 を流し、今の事業所（`$orgIds`）を除いて示す。

```cypher-resource
MATCH (a:Area {areaCode: $areaCode})-[:PART_OF*0..2]->(x:Area)<-[:SERVES]-(o:Organization {status: 'Active'})
WHERE NOT o.orgId IN $orgIds
MATCH (o)-[:PROVIDES]->(s:Service {status: 'Active'})
WHERE s.serviceTypeName = $serviceType
RETURN DISTINCT o.orgId AS orgId, o.name AS name, s.capacity AS capacity, x.areaCode <> $areaCode AS viaParent,
       o.checkedOn AS checkedOn
ORDER BY viaParent, name
LIMIT $limit
```

## 示し方

```text
### 事業所の候補（区域：…／サービス：…）
| 名前 | 種別 | 定員 | 電話 | 確かめた日 |
- 空き状況はこの DB に無い。電話で確かめる
- 確かめた日が古いものは、そう添える
- 0 件なら「この区域・この名前では見つからなかった」と書く（「無い」と言い切らない。区域を広げる、名前を変える）
```

## 関連スキル

`neo4j-support-db`（本人の関わり）、`resilience-checker`（親の役割の代わり）、`emergency-protocol`
