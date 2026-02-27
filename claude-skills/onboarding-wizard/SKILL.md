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
| `neo4j:read_neo4j_cypher` | 既存登録の重複確認 |
| `neo4j:write_neo4j_cypher` | クライアント情報の登録 |

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

```cypher
MATCH (c:Client {name: $clientName})
MERGE (ng:NgAction {action: $action})
SET ng.reason = $reason,
    ng.riskLevel = $riskLevel
MERGE (c)-[:MUST_AVOID]->(ng)
RETURN ng.action AS 禁忌事項, ng.riskLevel AS リスクレベル
```

#### 配慮事項

```cypher
MATCH (c:Client {name: $clientName})
MERGE (cp:CarePreference {category: $category, instruction: $instruction})
SET cp.priority = $priority
MERGE (c)-[:REQUIRES]->(cp)
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
MERGE (kp:KeyPerson {name: $kpName})
SET kp.phone = $phone,
    kp.relationship = $relationship,
    kp.role = $role
MERGE (c)-[:HAS_KEY_PERSON {rank: $rank}]->(kp)
RETURN kp.name AS キーパーソン
```

#### 医療機関

```cypher
MATCH (c:Client {name: $clientName})
MERGE (h:Hospital {name: $hospitalName})
SET h.specialty = $specialty,
    h.phone = $phone,
    h.doctor = $doctor
MERGE (c)-[:TREATED_AT]->(h)
RETURN h.name AS 医療機関
```

#### 手帳・受給者証

```cypher
MATCH (c:Client {name: $clientName})
MERGE (cert:Certificate {type: $certType, grade: $grade})
SET cert.nextRenewalDate = date($nextRenewalDate),
    cert.issueDate = date($issueDate)
MERGE (c)-[:HAS_CERTIFICATE]->(cert)
RETURN cert.type AS 種類, cert.grade AS 等級
```

#### 後見人

```cypher
MATCH (c:Client {name: $clientName})
MERGE (g:Guardian {name: $guardianName})
SET g.type = $guardianType,
    g.phone = $phone,
    g.organization = $organization
MERGE (c)-[:HAS_LEGAL_REP]->(g)
RETURN g.name AS 後見人
```

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

```cypher
MATCH (c:Client {name: $clientName})
OPTIONAL MATCH (c)-[:MUST_AVOID]->(ng:NgAction)
OPTIONAL MATCH (c)-[:REQUIRES]->(cp:CarePreference)
OPTIONAL MATCH (c)-[kpRel:HAS_KEY_PERSON]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:TREATED_AT]->(hosp:Hospital)
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(cert:Certificate)
OPTIONAL MATCH (c)-[:HAS_LEGAL_REP]->(g:Guardian)
OPTIONAL MATCH (c)<-[:IS_PARENT_OF|FAMILY_OF]-(r:Relative)
RETURN
    c.name AS 氏名,
    c.dob AS 生年月日,
    count(DISTINCT ng) AS 禁忌登録数,
    count(DISTINCT cp) AS 配慮事項数,
    count(DISTINCT kp) AS キーパーソン数,
    count(DISTINCT hosp) AS 医療機関数,
    count(DISTINCT cert) AS 手帳数,
    count(DISTINCT g) AS 後見人数,
    count(DISTINCT r) AS 家族情報数
```

### Phase 5: チェックリスト出力

```markdown
## 登録完了チェックリスト: [クライアント名]

### 必須項目（初回）
- [x/空] 氏名・生年月日
- [x/空] 禁忌事項（NgAction）が1件以上
- [x/空] キーパーソンが1名以上（rank 1）
- [x/空] かかりつけ医

### 推奨項目（初回〜2回目）
- [x/空] 手帳・受給者証の種類と更新日
- [x/空] 成年後見人等の情報
- [x/空] 主たる介護者（親）の情報

### 次回確認すべき項目
- [不足している項目のリスト]
```

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
| `narrative-extractor` | 面談メモからの一括抽出 |
| `resilience-checker` | 第5の柱（CareRole）の登録後にカバー率診断 |
| `ecomap-generator` | 登録完了後にエコマップ自動生成 |
| `neo4j-support-db` | Cypherテンプレートの参照・プロフィール確認 |
