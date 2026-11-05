---
name: onboarding-wizard
description: 新しい本人の初回面接で、7 本の柱に沿って聞き取りを案内し、聞き漏らしを防ぐスキル。登録済みの項目と未確認の項目を個人の側の DB から読み（仮名 displayCode）、聞いた話は narrative-extractor の書き込みの案にする。「新規登録」「新しい利用者」「インテーク」「初回面接」「初回アセスメント」などの発言時に使う。DB には書かない。
---

# onboarding-wizard：初回面接の案内

## なぜ要るか

初回面接は「聞いたが無かった」と「まだ聞いていない」が最も入り混じる場面。聞き漏らしを防ぎ、聞いた話を根拠つきで残す（計画 N-27f）。

## 決まり

- **このスキルは DB に書かない。** 書くのはゲートだけ
- **本人の作成（氏名・生年月日）は Claude の外で行う。** 名前を受け取る道具は無い（SEMANTICS SEM-REC-02。台帳 G-42 (2)）。職員が手元の入口で本人を作り、仮名（`displayCode`）を受け取ってから、このスキルを使う。同じ人の重なりの確かめもその入口で行う
- 聞いた話は `narrative-extractor` の書き込みの案（JSON）にする。禁忌・推奨ケアは、同じ案の事実の引用を根拠にした候補にする（台帳 G-63）
- 語りの中の人は役割の名前で書く（母・主治医・担当の相談員。SEMANTICS SEM-REC-01）
- 道具は MCP `nest-personal` の `read_personal_cypher`（登録の状況を見るだけ）

## 「無い」と言われたら

「特にないです」は、確認（`Review`）として残す必要がある。残さなければ、以後「確かめたうえで無い」と「まだ聞いていない」が区別できない。

- 誰に聞いたか（本人・家族・機関）を必ず控える
- **確認の記録は、今は作る手順が無い。** 入口の案（`narrative-extractor`）に `Review` の欄が無く、ゲートで `Review` を作る手順も試験もまだ無い。チェックリストに「確認の記録を作るもの」として、何を・誰に聞いて「無い」と言われたかを書き、職員に渡す
- 聞けていない項目に確認を作らない（未確認のまま残すのが正しい）

## 聞き取りの順（7 本の柱）

**最初に必ず**
1. 本人性：生活の歴史のキーになる出来事、本人・家族の願い（`LifeHistory`・`Wish`）
2. ケアの暗黙知：**禁忌**（してはいけないこと。生命に関わる／パニックを招く／不快・ストレス）、推奨ケア（食事・入浴・睡眠・移動・やりとり）、特性・診断。「〇〇するとどうなりますか」「してはいけないことはありますか」と具体的に聞く
3. 危機管理の網：キーパーソン（順位）、主治医、医療の機関。連絡先の電話番号は Claude の外の入口で登録する

**初回か 2 回目**
4. 法的基盤：手帳・受給者証（種類・等級・次の更新日）、後見・保佐・補助・任意後見・任意代理
5. 親の機能移行：親が担っている役割 → `resilience-checker`

**支援の始まりの後に順に**
6. 金銭の安全：年金・手当・生活保護、金銭の管理
7. 多機関の連携：関わっている機関

## 登録の状況を見る照会

### 1. 柱ごとの件数と確認

```cypher
MATCH (c:Client {displayCode: $code})
OPTIONAL MATCH (c)-[:HAS_HISTORY]->(h:LifeHistory) WHERE h.status IN ['Active', 'Pending']
WITH c, count(DISTINCT h) AS history
OPTIONAL MATCH (c)-[:HAS_WISH]->(w:Wish) WHERE w.status IN ['Active', 'Pending']
WITH c, history, count(DISTINCT w) AS wishes
OPTIONAL MATCH (c)-[:MUST_AVOID]->(n:NgAction) WHERE n.status IN ['Active', 'Pending']
WITH c, history, wishes, count(DISTINCT n) AS ngActions
OPTIONAL MATCH (c)-[:REQUIRES]->(p:CarePreference) WHERE p.status IN ['Active', 'Pending']
WITH c, history, wishes, ngActions, count(DISTINCT p) AS carePreferences
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(cd:Condition) WHERE cd.status IN ['Active', 'Pending']
WITH c, history, wishes, ngActions, carePreferences, count(DISTINCT cd) AS conditions
OPTIONAL MATCH (k:Person)-[rt:RELATED_TO {kind: 'KeyPerson'}]->(c) WHERE rt.status IN ['Active', 'Pending']
WITH c, history, wishes, ngActions, carePreferences, conditions, count(DISTINCT k) AS keyPersons
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(ct:Certificate) WHERE ct.status IN ['Active', 'Pending']
WITH c, history, wishes, ngActions, carePreferences, conditions, keyPersons, count(DISTINCT ct) AS certificates
OPTIONAL MATCH (g:Involvement)-[:CONCERNS]->(c) WHERE g.status IN ['Active', 'Pending']
  AND g.kind IN ['Guardianship', 'AgencyContract']
WITH c, history, wishes, ngActions, carePreferences, conditions, keyPersons, certificates, count(DISTINCT g) AS legal
OPTIONAL MATCH (r:CareRole)-[:ROLE_FOR]->(c) WHERE r.status IN ['Active', 'Pending']
WITH c, history, wishes, ngActions, carePreferences, conditions, keyPersons, certificates, legal, count(DISTINCT r) AS careRoles
OPTIONAL MATCH (c)-[:RECEIVES]->(pa:PublicAssistance) WHERE pa.status IN ['Active', 'Pending']
WITH c, history, wishes, ngActions, carePreferences, conditions, keyPersons, certificates, legal, careRoles,
     count(DISTINCT pa) AS assistance
OPTIONAL MATCH (i:Involvement)-[:CONCERNS]->(c) WHERE i.status IN ['Active', 'Pending']
WITH c, history, wishes, ngActions, carePreferences, conditions, keyPersons, certificates, legal, careRoles, assistance,
     count(DISTINCT i) AS involvements
OPTIONAL MATCH (v:Review)-[:ABOUT]->(c) WHERE v.status = 'Active'
RETURN history, wishes, ngActions, carePreferences, conditions, keyPersons, certificates, legal, careRoles, assistance,
       involvements, collect(DISTINCT v.domain) AS reviewed
```

### 2. 未確定（承認を待っている）の数

```cypher
MATCH (n {status: 'Pending'})
WHERE (n)-[:ABOUT]->(:Client {displayCode: $code})
   OR (:Client {displayCode: $code})-[:MUST_AVOID|REQUIRES|HAS_CONDITION|HAS_WISH|HAS_HISTORY|HAS_CERTIFICATE|RECEIVES]->(n)
RETURN labels(n)[0] AS label, count(*) AS pending
```

## チェックリストの形

```text
## 初回面接チェックリスト：C-……
### 🚨 未確認（件数 0 で確認も無い。最優先で聞く）
- 禁忌／キーパーソン／後見／親の担っている役割 ……
### ✅ 聞いた（件数。未確定なら「未確定 …件」と添える）
### 次の面接で聞くこと（柱 4〜7）
### 確認の記録を職員が作るもの（「無い」と聞いたもの。誰に聞いたか）
```

0 件の項目を「なし」と書かない。確認があるものだけ「確認済み（0 件）」と書く。

## 関連スキル

`narrative-extractor`（聞いた話を案にする）、`resilience-checker`（親の役割）、`neo4j-support-db`、`visit-prep`
