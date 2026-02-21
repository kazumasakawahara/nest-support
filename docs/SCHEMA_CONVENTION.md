# Neo4j スキーマ命名規則（Naming Convention）

> **このドキュメントは、本プロジェクトの Neo4j データベースにおけるノードラベル・リレーションシップタイプ・プロパティ名の唯一の正典（Single Source of Truth）です。**
> すべての LLM（Gemini, Claude, その他エージェント）およびすべてのコード（Python, Cypher テンプレート, Skills）は、このドキュメントに従ってください。

---

## 目的

本プロジェクトでは、複数の LLM・エージェントが Neo4j データベースへの読み書きを行います：

| エントリーポイント | 担当LLM | 書き込み方式 | 規約準拠の強制力 |
|---|---|---|---|
| `lib/ai_extractor.py` → `lib/db_operations.py` | Gemini 2.0 Flash | EXTRACTION_PROMPT → register_to_database() | **強**（コードで固定） |
| `server.py` (MCP server) | Claude Desktop | run_cypher_query() 経由 | **中**（Skill テンプレート依存） |
| Claude Skills (SKILL.md) | Claude Desktop | neo4j MCP の read/write_neo4j_cypher | **弱**（LLMの判断に依存） |
| `mobile/api_server.py` | Gemini 2.0 Flash | 上記と同じ extract → register | **強**（コードで固定） |
| 将来のエージェント | 任意のLLM | 未定 | **弱**（このドキュメントが唯一のガイド） |

**リスク**: Skills 経由や将来のエージェントが ad-hoc な Cypher を生成する際、命名規則に準拠しないリレーションやプロパティが作成される可能性があります。このドキュメントはその防止策です。

---

## 命名規則の原則

### 1. ノードラベル → **PascalCase**

```
✅ 正: Client, NgAction, CarePreference, KeyPerson, SupportLog
❌ 誤: client, ng_action, care_preference, key_person, support_log
```

### 2. リレーションシップタイプ → **UPPER_SNAKE_CASE**

```
✅ 正: MUST_AVOID, HAS_KEY_PERSON, IN_CONTEXT, HAS_CERTIFICATE
❌ 誤: MustAvoid, must_avoid, hasKeyPerson, Has_Key_Person
```

### 3. プロパティ名 → **camelCase**

```
✅ 正: bloodType, riskLevel, nextRenewalDate, clientId, displayCode
❌ 誤: blood_type, risk_level, next_renewal_date, client_id, display_code
```

### 4. 列挙値（Enum Values）→ **PascalCase（英語）**

```
✅ 正: LifeThreatening, Panic, Discomfort, Active, Effective, High, Medium, Low
❌ 誤: life_threatening, PANIC, active, "効果的"
```

> **例外**: `CarePreference.category` と `SupportLog.situation` の値は日本語を許容します（例: 食事, 入浴, パニック時）。これはユーザー向け表示と直結するためです。

---

## 正式なノードラベル一覧

### 障害福祉支援DB（port 7687）

| ノードラベル | 柱 | 説明 | 主要プロパティ |
|---|---|---|---|
| `Client` | 本人性 | 中心ノード（本人） | name, dob, bloodType, clientId, displayCode, kana |
| `Condition` | ケアの暗黙知 | 特性・医学的診断 | name, diagnosisDate, status |
| `NgAction` | ケアの暗黙知 | 禁忌事項（**最重要**） | action, reason, riskLevel |
| `CarePreference` | ケアの暗黙知 | 推奨ケア | category, instruction, priority |
| `KeyPerson` | 危機管理 | キーパーソン・緊急連絡先 | name, relationship, phone, role |
| `Guardian` | 法的基盤 | 成年後見人等 | name, type, phone, organization |
| `Hospital` | 危機管理 | 医療機関 | name, specialty, phone, doctor |
| `Certificate` | 法的基盤 | 手帳・受給者証 | type, grade, nextRenewalDate |
| `PublicAssistance` | 法的基盤 | 公的扶助 | type, grade, startDate |
| `Organization` | 多機関連携 | 関係機関 | name, type, contact, address |
| `Supporter` | 多機関連携 | 支援者 | name, role, organization, phone |
| `SupportLog` | 記録 | 支援記録 | date, situation, action, effectiveness, note |
| `AuditLog` | 監査 | 監査ログ | timestamp, user, action, targetType, targetName, details |
| `LifeHistory` | 本人性 | 生育歴 | era, episode, emotion |
| `Wish` | 本人性 | 本人・家族の願い | content, status, date |
| `Identity` | 本人性 | 仮名化用個人情報（将来） | name, dob |
| `ServiceProvider` | 多機関連携 | 福祉サービス事業所 | name, corporateName, serviceType, wamnetId |
| `ProviderFeedback` | 多機関連携 | 事業所口コミ | feedbackId, category, content, rating |

### 生活保護受給者DB（port 7688）

| ノードラベル | 説明 | 主要プロパティ |
|---|---|---|
| `Recipient` | 受給者（中心ノード） | name, caseNumber, dob, gender |
| `CaseRecord` | ケース記録 | date, category, content, caseworker |
| `HomeVisit` | 家庭訪問記録 | date, observations, recipientCondition |
| `Strength` | 強み | description, discoveredDate, context |
| `Challenge` | 課題 | description, severity, currentStatus |
| `MentalHealthStatus` | 精神疾患 | diagnosis, currentStatus, symptoms |
| `EffectiveApproach` | 効果的関わり方 | description, context, frequency |
| `NgApproach` | 避けるべき関わり方 | description, reason, riskLevel |
| `EconomicRisk` | 経済的搾取リスク | type, perpetrator, severity, status |
| `MoneyManagementStatus` | 金銭管理状況 | capability, pattern, riskLevel |
| `KeyPerson` | キーパーソン | name, relationship, phone, role |

---

## 正式なリレーションシップタイプ一覧

### 障害福祉支援DB（port 7687）

| リレーション | 方向 | プロパティ | 説明 |
|---|---|---|---|
| `HAS_CONDITION` | Client → Condition | — | 特性・診断の紐付け |
| `MUST_AVOID` | Client → NgAction | — | **禁忌事項（最重要）** |
| `IN_CONTEXT` | NgAction → Condition | — | 禁忌の文脈（関連特性） |
| `REQUIRES` | Client → CarePreference | — | 推奨ケアの紐付け |
| `ADDRESSES` | CarePreference → Condition | — | ケアが対応する特性 |
| `HAS_KEY_PERSON` | Client → KeyPerson | rank | キーパーソン（rank で優先順位） |
| `HAS_LEGAL_REP` | Client → Guardian | — | 法定代理人 |
| `HAS_CERTIFICATE` | Client → Certificate | — | 手帳・受給者証 |
| `RECEIVES` | Client → PublicAssistance | — | 公的扶助の受給 |
| `REGISTERED_AT` | Client → Organization | — | 関係機関への登録 |
| `TREATED_AT` | Client → Hospital | — | 通院先 |
| `SUPPORTED_BY` | Client → Supporter | — | 支援者の紐付け |
| `LOGGED` | Supporter → SupportLog | — | 支援記録の作成 |
| `ABOUT` | SupportLog → Client | — | 記録の対象者 |
| `HAS_HISTORY` | Client → LifeHistory | — | 生育歴 |
| `HAS_WISH` | Client → Wish | — | 願い |
| `HAS_IDENTITY` | Client → Identity | — | 仮名化対応（将来） |
| `USES_SERVICE` | Client → ServiceProvider | startDate, endDate, status | サービス利用 |
| `HAS_FEEDBACK` | ServiceProvider → ProviderFeedback | — | 口コミ |
| `WROTE` | Supporter → ProviderFeedback | — | 口コミ作成者 |

### 生活保護受給者DB（port 7688）

| リレーション | 方向 | 説明 |
|---|---|---|
| `HAS_RECORD` | Recipient → CaseRecord | ケース記録 |
| `HAS_VISIT` | Recipient → HomeVisit | 家庭訪問 |
| `HAS_STRENGTH` | Recipient → Strength | 強み |
| `HAS_CHALLENGE` | Recipient → Challenge | 課題 |
| `HAS_MENTAL_HEALTH` | Recipient → MentalHealthStatus | 精神状態 |
| `RESPONDS_WELL_TO` | Recipient → EffectiveApproach | 効果的関わり |
| `MUST_AVOID` | Recipient → NgApproach | 避けるべき関わり |
| `HAS_ECONOMIC_RISK` | Recipient → EconomicRisk | 経済的リスク |
| `HAS_MONEY_MGMT` | Recipient → MoneyManagementStatus | 金銭管理 |
| `HAS_KEY_PERSON` | Recipient → KeyPerson | キーパーソン |
| `HOLDS` | Recipient → Certificate | 証明書 |

---

## 廃止されたリレーション名（使用禁止）

以下のリレーション名はプロジェクト初期に使用されていましたが、現在は**廃止**されています。
**新規作成時には絶対に使用しないでください。**

| 廃止名 | 正式名 | 備考 |
|---|---|---|
| ~~`PROHIBITED`~~ | `MUST_AVOID` | データベースに旧名が残存している可能性あり |
| ~~`PREFERS`~~ | `REQUIRES` | 同上 |
| ~~`EMERGENCY_CONTACT`~~ | `HAS_KEY_PERSON` | 同上 |
| ~~`RELATES_TO`~~ | `IN_CONTEXT` | NgAction → Condition の文脈紐付け |
| ~~`HAS_GUARDIAN`~~ | `HAS_LEGAL_REP` | 後見人リレーション |
| ~~`HOLDS`~~ | `HAS_CERTIFICATE` | 手帳リレーション |

### 読み取りクエリでの後方互換性

旧名でデータが残存している可能性があるため、**読み取り**クエリでは以下のパターンで両方を対象にしてください：

```cypher
-- 読み取り時: 新旧両方にマッチ（推奨）
MATCH (c:Client)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)
MATCH (c:Client)-[:REQUIRES|PREFERS]->(cp:CarePreference)
MATCH (c:Client)-[:HAS_KEY_PERSON|EMERGENCY_CONTACT]->(kp:KeyPerson)
MATCH (ng:NgAction)-[:IN_CONTEXT|RELATES_TO]->(cond:Condition)

-- 書き込み時: 正式名のみ使用（厳守）
CREATE (c)-[:MUST_AVOID]->(ng)         // ✅
CREATE (c)-[:PROHIBITED]->(ng)         // ❌ 使用禁止
```

---

## プロパティ命名の詳細規則

### 共通プロパティ

| プロパティ | 型 | 説明 | 例 |
|---|---|---|---|
| `name` | String | 名称 | "山田太郎" |
| `dob` | Date | 生年月日 | date("1990-01-15") |
| `status` | String | 状態 | "Active" |
| `date` | Date | 記録日 | date("2025-12-01") |

### 日付型プロパティの命名パターン

```
単一の日付: date, dob
特定用途の日付: issueDate, startDate, endDate, diagnosisDate
更新・期限: nextRenewalDate, updatedAt
タイムスタンプ: timestamp (AuditLog用)
```

### ID系プロパティの命名パターン

```
clientId     → Client の一意識別子
displayCode  → 表示用コード
wamnetId     → WAM NET 連携用ID
feedbackId   → 口コミの一意識別子
```

### ServiceProvider のプロパティ統一

WAM NET インポート時期によりレガシーの snake_case プロパティが残存しています。
**新規作成時は camelCase のみを使用してください。**

| 正式名（camelCase） | レガシー名（snake_case） | 対応方法 |
|---|---|---|
| `name` | `office_name` | COALESCE(sp.name, sp.office_name) |
| `corporateName` | `corp_name` | COALESCE(sp.corporateName, sp.corp_name) |
| `serviceType` | `service_type` | COALESCE(sp.serviceType, sp.service_type) |
| `wamnetId` | `office_number` | COALESCE(sp.wamnetId, sp.office_number) |
| `closedDays` | `closed_days` | COALESCE(sp.closedDays, sp.closed_days) |
| `hoursWeekday` | `hours_weekday` | COALESCE(sp.hoursWeekday, sp.hours_weekday) |
| `updatedAt` | `updated_at` | COALESCE(sp.updatedAt, sp.updated_at) |

---

## riskLevel 列挙値

NgAction の riskLevel プロパティで使用する値（優先度順）：

| 値 | 意味 | 説明 |
|---|---|---|
| `LifeThreatening` | 生命に関わる | アレルギー、誤嚥リスク等 |
| `Panic` | パニック誘発 | 大きな音、特定の状況等 |
| `Discomfort` | 不快・ストレス | 嫌がる行為、苦手な環境等 |

---

## LLM・エージェント向けガイドライン

### Cypher 書き込み時の必須チェックリスト

1. **ノードラベル**: PascalCase か？ → `Client` ✅ / `client` ❌
2. **リレーション**: UPPER_SNAKE_CASE か？ → `MUST_AVOID` ✅ / `MustAvoid` ❌
3. **リレーション名**: 正式名を使用しているか？ → `MUST_AVOID` ✅ / `PROHIBITED` ❌
4. **プロパティ**: camelCase か？ → `riskLevel` ✅ / `risk_level` ❌
5. **パラメータ化**: Cypher インジェクション対策で `$param` を使用しているか？
6. **MERGE vs CREATE**: 重複防止が必要なノードには `MERGE` を使用しているか？
7. **監査ログ**: 書き込み操作は `AuditLog` に記録しているか？

### Skills（SKILL.md）でのテンプレート記述時の注意

- 書き込みテンプレートでは**正式なリレーション名のみ**を使用する
- 読み取りテンプレートでは**新旧両方**を `[:NEW|OLD]` 構文で対象にする
- テンプレートにコメントで「正式名: XXX」を明記する

### 新しいノードラベル・リレーションを追加する場合

1. まずこのドキュメントに追記する
2. 命名規則（PascalCase / UPPER_SNAKE_CASE / camelCase）に従う
3. 関連する SKILL.md を更新する
4. `lib/db_operations.py` に対応する register 関数を追加する

---

## マイグレーション方針

### 旧リレーションの完全移行（将来実施）

旧名のリレーションが残存するデータベースを正式名に移行するための Cypher:

```cypher
// 移行前にバックアップを取得すること

// PROHIBITED → MUST_AVOID
MATCH (c:Client)-[old:PROHIBITED]->(ng:NgAction)
WHERE NOT (c)-[:MUST_AVOID]->(ng)
CREATE (c)-[:MUST_AVOID]->(ng)
DELETE old;

// PREFERS → REQUIRES
MATCH (c:Client)-[old:PREFERS]->(cp:CarePreference)
WHERE NOT (c)-[:REQUIRES]->(cp)
CREATE (c)-[:REQUIRES]->(cp)
DELETE old;

// EMERGENCY_CONTACT → HAS_KEY_PERSON
MATCH (c:Client)-[old:EMERGENCY_CONTACT]->(kp:KeyPerson)
WHERE NOT (c)-[:HAS_KEY_PERSON]->(kp)
CREATE (c)-[r:HAS_KEY_PERSON]->(kp)
SET r.rank = COALESCE(old.rank, 99)
DELETE old;

// RELATES_TO → IN_CONTEXT
MATCH (ng:NgAction)-[old:RELATES_TO]->(cond:Condition)
WHERE NOT (ng)-[:IN_CONTEXT]->(cond)
CREATE (ng)-[:IN_CONTEXT]->(cond)
DELETE old;

// 移行後の確認
MATCH ()-[r:PROHIBITED|PREFERS|EMERGENCY_CONTACT|RELATES_TO]->()
RETURN type(r) AS oldRelation, count(r) AS remaining;
// → 0件であれば移行完了
```

### ServiceProvider プロパティの統一移行（将来実施）

```cypher
// snake_case → camelCase への移行
MATCH (sp:ServiceProvider)
WHERE sp.office_name IS NOT NULL AND sp.name IS NULL
SET sp.name = sp.office_name,
    sp.corporateName = sp.corp_name,
    sp.serviceType = sp.service_type,
    sp.wamnetId = sp.office_number,
    sp.closedDays = sp.closed_days,
    sp.hoursWeekday = sp.hours_weekday,
    sp.updatedAt = sp.updated_at
REMOVE sp.office_name, sp.corp_name, sp.service_type,
       sp.office_number, sp.closed_days, sp.hours_weekday,
       sp.updated_at;
```

---

## 変更履歴

| 日付 | 変更内容 |
|---|---|
| 2026-02-16 | 初版作成。正式リレーション名の確定、廃止リレーションの明記、LLM向けガイドライン追加 |
