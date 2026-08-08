---
name: onboarding-wizard
description: 新規クライアントの初回面接時に、7本柱に沿った情報収集をガイドし、聞き漏らしを防止しながらNeo4jに構造化登録するスキル。「新規登録」「新しい利用者」「インテーク」「初回面接」「クライアントを追加」「初回アセスメント」などの発言時に必ずこのスキルを使用すること。面談メモやナラティブからの一括抽出にも対応する。
---

# 新規クライアント登録ウィザード (onboarding-wizard)

## なぜこのスキルが必要か

新規クライアントの登録で最も危険なのは「聞き漏らし」です。禁忌事項（NgAction）を聞き逃したまま支援が始まれば、二次被害につながります。キーパーソンの登録を忘れれば、緊急時に連絡先がわからない事態になります。

このスキルは、マニフェスト7本柱に沿って**何を聞くべきか**を体系的にガイドし、聞き取った内容を構造化してNeo4jに登録します。全てを初回で揃える必要はなく、優先度に沿って段階的に情報を蓄積していきます。

## 対象ユーザー

- 計画相談支援専門員（初回面接時）
- インテーク担当者

## トリガーワード

- 「新規登録」「新しい利用者さん」「クライアントを追加」
- 「インテーク」「初回面接」「初回アセスメント」
- 「〇〇さんを登録したい」

---

## 使用するMCPツール

| ツール | 用途 |
|--------|------|
| `neo4j:execute_query` | 既存登録の重複確認（読み取り）・クライアント情報の登録（書き込み）。読み書き兼用ツール |

---

## 実行手順

### Phase 1: 重複確認

まず、同名または類似名のクライアントが既に登録されていないか確認する。

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $nameFragment
RETURN c.name AS 氏名, c.dob AS 生年月日
```

名前の類似（漢字違い、ひらがな/カタカナ、旧姓等）にも注意する。該当がなければ次へ進む。

### Phase 2: 段階的情報収集

7本柱に沿って、優先度順に情報を収集する。ユーザーから面談メモやナラティブをまとめて受け取った場合は `narrative-extractor` スキルの抽出ルールに従って一括処理する。対話的に聞き取る場合は以下の順序でガイドする。

#### 優先度: 最高 — 初回に必ず確認

**第1の柱: 本人性 (Identity & Narrative)**

聞き取り項目:
- 氏名（フルネーム）
- 生年月日
- 血液型（不明でもOK）
- 生育歴のキーエピソード（幼少期、学齢期、成人後）
- 本人・家族の願い

**第2の柱: ケアの暗黙知 (Care Instructions)** — 安全に直結

聞き取り項目:
- **禁忌事項（NgAction）**: 「絶対にしてはいけないこと」を漏らさず確認。riskLevelを判定:
  - LifeThreatening: アレルギー、誤嚥リスクなど命に関わるもの
  - Panic: パニック誘発（大きな音、特定の状況等）
  - Discomfort: 嫌がること、苦手なこと
- **配慮事項（CarePreference）**: 食事、入浴、睡眠、移動、コミュニケーション等
- **特性・診断（Condition）**: 診断名、特性名

聞き方のコツ: 「〇〇するとどうなりますか？」「してはいけないことはありますか？」と具体的に聞く。親の語りから暗黙知を引き出すことが重要。

> ### ★ 「無い」と言われたら、それも必ず記録する（BRS-12）
>
> **新規登録は「聞いたが無かった」が最も発生する場面**である。
> ここで記録しなければ、以後永久に「確認したうえで無い」と「まだ聞いていない」が
> 区別できなくなる（リレーションの不在としては同じに見える）。
>
> 禁忌・配慮事項・キーパーソン等について「特にないです」と返ってきたら、
> **Phase 3 の「確認記録（Review）」で登録する**。必ず **誰に聞いたか（source）** を
> 控えること——「母親に確認して禁忌なし」と「本人にしか聞けていない」は、
> 同じ「0件」でも重みが全く違う。
>
> **聞けていない項目には Review を登録しない。** 未確認のまま残すのが正しい
> （空欄を埋めたいだけの登録は、未聴取を確認済みと偽ることになる）。

**第3の柱: 危機管理ネットワーク (Safety Net)**

聞き取り項目:
- キーパーソン（優先順位付き）: 氏名、続柄、電話番号、役割
- かかりつけ医: 病院名、診療科、担当医名、電話番号

#### 優先度: 高 — 初回または2回目の面接

**第4の柱: 法的基盤 (Legal Basis)**
- 手帳の種類と等級、次回更新日
- 受給者証の情報
- 成年後見人等の有無

**第5の柱: 親の機能移行 (Parental Transition)**
- 主たる介護者（親）の基本情報と健康状態
- 親が担っているタスク（CareRole）の洗い出し
  → `resilience-checker` スキルと連携

#### 優先度: 通常 — 支援開始後に順次

**第6の柱: 金銭的安全 (Financial Safety)**
- 金銭管理の状況
- 経済的搾取リスクの有無

**第7の柱: 多機関連携 (Multi-Agency Collaboration)**
- 連携している支援機関の情報

### Phase 3: データ登録

収集した情報をNeo4jに登録する。登録前に**必ず内容をユーザーに確認**すること。

#### クライアント基本情報

```cypher
MERGE (c:Client {name: $name})
SET c.dob = date($dob),
    c.bloodType = $bloodType
RETURN c.name AS 氏名
```

#### 禁忌事項（最重要）

クライアント配下のノードとしてリレーションごと MERGE する（再実行で重複せず、他クライアントとノードを共有しない。
グローバルな `MERGE (ng:NgAction {action})` は同文の禁忌を持つ別クライアントとノードを共有し、riskLevel を相互に上書きするため禁止）。

```cypher
MATCH (c:Client {name: $clientName})
MERGE (c)-[:MUST_AVOID]->(ng:NgAction {action: $action})
ON CREATE SET ng.reason = $reason, ng.riskLevel = $riskLevel
ON MATCH SET  ng.reason = COALESCE($reason, ng.reason),
              ng.riskLevel = COALESCE($riskLevel, ng.riskLevel)
RETURN ng.action AS 禁忌事項, ng.riskLevel AS リスクレベル
```

#### 配慮事項

```cypher
MATCH (c:Client {name: $clientName})
MERGE (c)-[:REQUIRES]->(cp:CarePreference {category: $category, instruction: $instruction})
ON CREATE SET cp.priority = $priority
ON MATCH SET  cp.priority = COALESCE($priority, cp.priority)
RETURN cp.category AS カテゴリ
```

#### 特性・診断

```cypher
MATCH (c:Client {name: $clientName})
MERGE (con:Condition {name: $conditionName})
SET con.status = COALESCE($status, 'Active')
MERGE (c)-[:HAS_CONDITION]->(con)
RETURN con.name AS 特性
```

#### キーパーソン

```cypher
MATCH (c:Client {name: $clientName})
MERGE (c)-[r:HAS_KEY_PERSON]->(kp:KeyPerson {name: $kpName})
SET kp.phone = COALESCE($phone, kp.phone),
    kp.relationship = COALESCE($relationship, kp.relationship),
    kp.role = COALESCE($role, kp.role),
    r.rank = COALESCE($rank, r.rank)
RETURN kp.name AS キーパーソン
```

#### 医療機関

```cypher
MATCH (c:Client {name: $clientName})
MERGE (h:Hospital {name: $hospitalName})
SET h.specialty = $specialty,
    h.phone = $phone
MERGE (c)-[:TREATED_AT]->(h)
// かかりつけ医は Doctor ノードで表現（Hospital.doctor プロパティは廃止）
FOREACH (_ IN CASE WHEN $doctor IS NULL OR $doctor = '' THEN [] ELSE [1] END |
    MERGE (d:Doctor {name: $doctor})
    MERGE (h)-[:HAS_DOCTOR]->(d))
RETURN h.name AS 医療機関
```

#### 手帳・受給者証

手帳種別（type）×等級（grade）ごとに1ノード（SCHEMA_CONVENTION §10.3 の複合キー。
等級未指定は「不明」）。発行日・状態はスキーマ規約どおり
リレーション側（`HAS_CERTIFICATE {issuedDate, status}`）に持つ。

```cypher
MATCH (c:Client {name: $clientName})
MERGE (c)-[r:HAS_CERTIFICATE]->(cert:Certificate {type: $certType, grade: COALESCE($grade, '不明')})
SET cert.nextRenewalDate = CASE WHEN $nextRenewalDate IS NOT NULL
                                THEN date($nextRenewalDate) ELSE cert.nextRenewalDate END,
    r.issuedDate = CASE WHEN $issuedDate IS NOT NULL
                        THEN date($issuedDate) ELSE r.issuedDate END,
    r.status = COALESCE(r.status, 'Active')
RETURN cert.type AS 種類, cert.grade AS 等級
```

> 訂正（2026-07-12）: 旧テンプレートは `{type}` のみを MERGE キーとしていたが、
> SCHEMA_CONVENTION §10.3 の複合キー `["type","grade"]` に合わせて修正した（DRIFT-08）。

#### 後見人

```cypher
MATCH (c:Client {name: $clientName})
MERGE (c)-[:HAS_LEGAL_REP]->(g:Guardian {name: $guardianName})
SET g.type = COALESCE($guardianType, g.type),
    g.phone = COALESCE($phone, g.phone),
    g.organization = COALESCE($organization, g.organization)
RETURN g.name AS 後見人
```

#### 確認記録（Review）——「聞いたが無かった」を残す ★新規登録では必須★

聞き取りの結果「無い」だった領域は、**必ず Review を登録する**。
登録しなければ、その聞き取りは**行われなかったのと同じ扱い**になる（次の支援者に伝わらない）。
追記のみ。既存の Review を更新・削除してはならない。

```cypher
MATCH (c:Client {name: $clientName})
MERGE (s:Supporter {name: $supporterName})
CREATE (rv:Review {
    domain: $domain,
    reviewedAt: date($reviewedAt),
    source: $source,
    note: $note
})
MERGE (s)-[:REVIEWED]->(rv)
MERGE (rv)-[:ABOUT]->(c)
RETURN rv.domain AS 領域, rv.reviewedAt AS 確認日, rv.source AS 情報源
```

**パラメータ**:
- `$clientName`（完全一致）, `$supporterName`（確認を行った支援者）
- `$domain`: `NgAction` / `CarePreference` / `KeyPerson` / `Guardian` / `Certificate` / `CareRole`
  （SCHEMA_CONVENTION §7.7。他の値は使わない）
- `$reviewedAt`: 確認日（通常は面接日。YYYY-MM-DD）
- `$source`: **誰に確認したか**。`本人` / `母親` / `父親` / `家族・親族` / `主治医` /
  `前事業所` / `相談支援専門員` / `後見人等` / `記録のみ`（§7.8）
- `$note`: 補足（任意）

> **登録対象は「0件の領域」だけではない。**
> 1件以上登録した領域でも、「この3件で全部だと確認した」なら Review を残す価値がある
> （後から「他にもあるのか、これで全部なのか」を問わなくて済む）。

> **`$source` を推測で埋めないこと。** 面接の相手が誰だったか不明なら、支援者に聞く。

#### 監査ログ（全登録操作で必須）

```cypher
CREATE (al:AuditLog {
    timestamp: datetime(),
    user: $user,
    action: 'CREATE',
    targetType: $targetType,
    targetName: $targetName,
    details: $details,
    clientName: $clientName
})
RETURN al.timestamp AS 記録日時
```

### Phase 4: 登録確認と不足項目の提示

登録後にプロフィールを取得し、不足情報を明示する。
**件数0の項目は、確認記録（Review）と照らして「確認済み」か「未確認」かを判定する（BRS-12）。**

```cypher
MATCH (c:Client {name: $clientName})
OPTIONAL MATCH (c)-[:MUST_AVOID]->(ng:NgAction)
OPTIONAL MATCH (c)-[:REQUIRES]->(cp:CarePreference)
OPTIONAL MATCH (c)-[kpRel:HAS_KEY_PERSON]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:TREATED_AT]->(hosp:Hospital)
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(cert:Certificate)
OPTIONAL MATCH (c)-[:HAS_LEGAL_REP]->(g:Guardian)
OPTIONAL MATCH (c)<-[:IS_PARENT_OF|FAMILY_OF]-(r:Relative)

// 確認記録（Review）—— 0件の意味を判定するために必須
OPTIONAL MATCH (rvNg:Review {domain: 'NgAction'})-[:ABOUT]->(c)
OPTIONAL MATCH (rvCp:Review {domain: 'CarePreference'})-[:ABOUT]->(c)
OPTIONAL MATCH (rvKp:Review {domain: 'KeyPerson'})-[:ABOUT]->(c)

RETURN
    c.name AS 氏名,
    c.dob AS 生年月日,
    count(DISTINCT ng)   AS 禁忌登録数,
    CASE WHEN count(DISTINCT ng) > 0 THEN '登録あり'
         WHEN max(rvNg.reviewedAt) IS NULL THEN '🚨 未確認'
         ELSE '✅ 確認済み（0件）' END AS 禁忌状態,
    max(rvNg.reviewedAt) AS 禁忌確認日,
    collect(DISTINCT rvNg.source) AS 禁忌情報源,
    count(DISTINCT cp)   AS 配慮事項数,
    CASE WHEN count(DISTINCT cp) > 0 THEN '登録あり'
         WHEN max(rvCp.reviewedAt) IS NULL THEN '🚨 未確認'
         ELSE '✅ 確認済み（0件）' END AS 配慮状態,
    count(DISTINCT kp)   AS キーパーソン数,
    CASE WHEN count(DISTINCT kp) > 0 THEN '登録あり'
         WHEN max(rvKp.reviewedAt) IS NULL THEN '🚨 未確認'
         ELSE '✅ 確認済み（0件）' END AS 連絡先状態,
    count(DISTINCT hosp) AS 医療機関数,
    count(DISTINCT cert) AS 手帳数,
    count(DISTINCT g)    AS 後見人数,
    count(DISTINCT r)    AS 家族情報数
```

> **🚨 未確認を見つけたら、「次回確認」ではなく「今聞けないか」を提起する。**
> 面接中ならその場で聞ける。とりわけ **NgAction の未確認のまま支援を開始しない**。

### Phase 5: チェックリスト出力

**安全直結項目は2値（ある/ない）ではなく3値で表現する**——
登録あり / ✅ 確認済み（0件）/ 🚨 未確認。
「1件以上あること」を完了条件にすると、**聞いたうえで本当に禁忌が無い人は永久に
未完了になる**し、逆に空欄のまま流せば未確認と区別がつかなくなる。

```markdown
## 登録完了チェックリスト: [クライアント名]

### 必須項目（初回）
- [x/空] 氏名・生年月日
- 禁忌事項（NgAction）: [登録あり（N件）/ ✅ 確認済み（0件・2026-07-12、母親）/ 🚨 未確認]
- キーパーソン: [登録あり（rank 1 あり）/ ✅ 確認済み（0件）/ 🚨 未確認]
- [x/空] かかりつけ医

### 推奨項目（初回〜2回目）
- 手帳・受給者証: [登録あり / ✅ 確認済み（0件）/ 🚨 未確認]
- 成年後見人等: [登録あり / ✅ 確認済み（0件）/ 🚨 未確認]
- [x/空] 主たる介護者（親）の情報

### 🚨 未確認の項目（最優先）
- [未確認の領域と、次に誰に聞くべきか]
```

> **「禁忌なし」と書いてはならない（BRS-12）。**
> Review がある場合のみ「✅ 確認済み（0件）」と書き、**必ず確認日と情報源を併記**する。
> Review が無い0件は「🚨 未確認」であり、**支援開始前に埋めるべき欠損**である。

---

## ナラティブからの一括登録

ユーザーが面談メモや親の語りをまとめて提供した場合は、`narrative-extractor` スキルの抽出ルールに従ってJSON形式でデータを抽出し、確認後に一括登録する。

抽出時の最重要ルール:
1. テキストにない情報を**絶対に創作しない**
2. 禁忌事項（NgAction）は**最優先で漏らさず抽出**する
3. 表記揺れは同一エンティティに統合する

---

## 関連スキル

| スキル | 連携タイミング |
|--------|---------------|
| `support-db-write-gate` | 書き込み（MERGE/更新/削除）の直前に必読 |
| `narrative-extractor` | 面談メモからの一括抽出 |
| `resilience-checker` | 第5の柱（CareRole）の登録後にカバー率診断 |
| `ecomap-generator` | 登録完了後にエコマップ自動生成 |
| `neo4j-support-db` | Cypherテンプレートの参照・プロフィール確認 |

## 証拠・鮮度モデル（Track A Phase 1・2026-08-08 正典収載）

SCHEMA_CONVENTION **v3.4 §7.9** / SEMANTIC_MODEL **v1.6 BRS-13**（河原氏承認 2026-08-08）で
NgAction / CarePreference に `source`（ENU-17 語彙）/ `sourceDetail` / `status`（Active・Pending・
Inactive の3値制限）/ `lastConfirmedAt` / `staleAfter` が、リレーション `CONTRADICTS`（矛盾の保留・
追記専用）/ `CONFIRMS`（Review→事実の個別確認）が正典収載された。

本スキルへの影響（挙動実装は Phase 1 ステップ3以降）:
- 新規登録する NgAction / CarePreference には `source`（ENU-17 語彙。聞き取り相手）と
  `lastConfirmedAt`（=登録日）の付与が必須になる（正典 §7.9・requiredProperties）。
- `sourceDetail` に「2026-07 面談で母親から聴取」のような支援者が読める文を残す。
