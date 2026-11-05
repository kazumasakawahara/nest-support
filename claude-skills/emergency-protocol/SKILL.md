---
name: emergency-protocol
description: 緊急時対応プロトコル。本人（仮名 displayCode、例 C-7K3M9Q）の安全に関わる情報を、禁忌 → 推奨ケア → 支える人 → 医療 → 法的な代理 の順で個人の側の DB から読み、二次被害を防ぐ。「パニック」「自傷」「事故」「急病」「けが」「救急」「発作」「倒れた」「助けて」などの緊急の言葉、「C-… さんの緊急情報」「してはいけないことは？」で使う。読むだけ。
---

# emergency-protocol：緊急時対応

## 最重要

人命に関わる情報を扱う。**禁忌を最初に出さないと二次被害のおそれがある**（計画 N-27c）。

- **読むだけ。** 緊急時に書き込みはしない
- 本人は仮名（`displayCode`）で呼ぶ。名前は受け取らない（SEMANTICS SEM-REC-02）。仮名が分からなければ、職員に仮名を確かめてもらう（名前で探さない）
- 道具は MCP `nest-personal` の `read_personal_cypher`（機関の名前は `nest-resource` の `read_resource_cypher`）
- **包みは実名・電話・住所・生年月日を返さない。** 連絡先の電話番号、救急隊に伝える氏名・住所・年齢は、Claude からは出せない。手元の緊急連絡カード・事業所の連絡網・SOS の仕組み（`sos/`）で確かめるよう、出力の頭に書く

## 出す順（変えない）

1. 🚫 禁忌（生命に関わる → パニックを招く → 不快・ストレス）
2. ✅ 推奨ケア（その場を落ち着かせる）
3. 📞 支える人（キーパーソンを先に、`rank` の順。続柄だけ。電話は連絡網で）
4. 🏥 医療（医療の関わりの機関、主治医の続柄の人）
5. ⚖️ 法的な代理（後見・保佐・補助・任意後見、任意代理）

## 安全の決まり

1. **状況で絞る**：職員が状況（パニック・食事・入浴など）を言ったら、照会 1 の `$situation` に入れる。絞って 0 件なら、絞らずに全部出す（安全のため）
2. **未確定**（`Pending`）の禁忌も出す。「未確定」と添える
3. **禁忌が 0 件のとき「なし」と言わない**：禁忌の確認（`Review`、領域 `NgAction`）が無ければ「🚨 禁忌は未確認。登録が無いだけで、禁忌が無いとは確かめられていない。慎重に動き、キーパーソンに確かめる」と出す。確認があれば「✅ 確認済み（0 件）— 確認の日・情報源」。「禁忌なし」「登録なし」「特にありません」と書かない
4. 確度は根拠の記録の確度を添える（表示名は `docs/SEMANTICS.md` SEM-ENUM-01）。食い違い（解決していない `CONTRADICTS`）があれば「食い違いあり」と添える
5. 「後見の関わりが 0 件」も、確認（領域 `Guardianship`）が無ければ「未確認」と出す

## 照会

### 1. 緊急時の一括（禁忌・推奨ケア。状況で絞る）

`$situation` は状況の言葉（無ければ空の文字列 `''`）。

```cypher
MATCH (c:Client {displayCode: $code})
OPTIONAL MATCH (c)-[:MUST_AVOID]->(n:NgAction)
  WHERE n.status IN ['Active', 'Pending'] AND ($situation = '' OR n.action CONTAINS $situation OR n.reason CONTAINS $situation)
OPTIONAL MATCH (n)-[:EVIDENCED_BY]->(nr:Record)
OPTIONAL MATCH (x:Record)-[k:CONTRADICTS]->(n) WHERE k.resolvedAt IS NULL
WITH c, n, collect(DISTINCT nr.certainty) AS ngEvidence, count(DISTINCT k) AS ngOpen
WITH c, collect(CASE WHEN n IS NULL THEN NULL ELSE {action: n.action, riskLevel: n.riskLevel, reason: n.reason,
       status: n.status, evidence: ngEvidence, openContradictions: ngOpen} END) AS ngActions
OPTIONAL MATCH (c)-[:REQUIRES]->(p:CarePreference)
  WHERE p.status IN ['Active', 'Pending'] AND ($situation = '' OR p.category CONTAINS $situation OR p.instruction CONTAINS $situation)
RETURN c.bloodType AS bloodType, ngActions,
       collect(CASE WHEN p IS NULL THEN NULL ELSE {category: p.category, instruction: p.instruction, priority: p.priority,
       status: p.status} END) AS carePreferences
```

`ngActions` を `riskLevel` の順（生命に関わる → パニックを招く → 不快・ストレス）に並べ替えて出す。

### 2. 支える人・医療・法的な代理

```cypher
MATCH (c:Client {displayCode: $code})
OPTIONAL MATCH (p:Person)-[rt:RELATED_TO]->(c)
  WHERE rt.status IN ['Active', 'Pending'] AND rt.until IS NULL
WITH c, p, rt ORDER BY CASE rt.kind WHEN 'KeyPerson' THEN 0 WHEN 'PrimaryDoctor' THEN 2 ELSE 1 END, rt.rank
WITH c, collect(CASE WHEN p IS NULL THEN NULL ELSE {personId: p.personId, kind: rt.kind, rank: rt.rank,
       status: rt.status} END) AS people
OPTIONAL MATCH (i:Involvement)-[:CONCERNS]->(c)
  WHERE i.status IN ['Active', 'Pending'] AND i.howEnded IN ['Ongoing', 'Unknown']
    AND i.kind IN ['Medical', 'Guardianship', 'AgencyContract']
OPTIONAL MATCH (o:Organization)-[:HAS_INVOLVEMENT]->(i)
OPTIONAL MATCH (q:Person)-[:HAS_INVOLVEMENT]->(i)
RETURN people, collect(CASE WHEN i IS NULL THEN NULL ELSE {kind: i.kind, guardianshipType: i.guardianshipType,
       service: i.serviceTypeName, orgId: o.orgId, personId: q.personId, status: i.status} END) AS involvements
```

機関の名前：

```cypher-resource
MATCH (o:Organization)
WHERE o.orgId IN $orgIds
RETURN o.orgId AS orgId, o.name AS name, o.kind AS kind
```

### 3. 確認の状況（0 件のとき）

```cypher
MATCH (v:Review)-[:ABOUT]->(c:Client {displayCode: $code})
WHERE v.status = 'Active' AND v.domain IN ['NgAction', 'CarePreference', 'KeyPerson', 'Guardianship']
RETURN v.domain AS domain, max(v.reviewedAt) AS lastReviewedAt, collect(DISTINCT v.informantKind) AS informantKinds
```

## 出力の形

```text
⚠️ 緊急対応情報：C-……（血液型：……。記録があるときだけ）
※ 氏名・住所・年齢・電話番号は Claude からは出せない。緊急連絡カード・連絡網・SOS で確かめる

🚫 1. 禁忌（絶対にしないこと）
⚠️🔴【生命に関わる】……（確度・未確定・食い違い）
⚠️🟡【パニックを招く】……
⚠️🟢【不快・ストレス】……
（0 件の扱いは「安全の決まり」3）

✅ 2. 推奨ケア（こうすると落ち着く）
📞 3. 支える人（キーパーソン → 家族ほか。続柄と順位だけ）
🏥 4. 医療（機関の名前・主治医の続柄の人）
⚖️ 5. 法的な代理（類型・機関の名前。0 件で確認が無ければ「未確認」）
```

救急隊に伝えるときは、禁忌のうち医療の処置に関わるもの（生命に関わる禁忌）と、医療の機関を先に短くまとめる。

## 関連スキル

`neo4j-support-db`（詳しい照会）、`visit-prep`、`insight-agent`（予兆の分析。リスクが高いと出たら、このスキルの照会 1 を先に流す）
