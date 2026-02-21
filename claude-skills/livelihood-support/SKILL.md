---
name: livelihood-support
description: 生活保護受給者尊厳支援データベース。7本柱モデルに基づき、二次被害防止と経済的安全を最優先とした支援情報を管理する。汎用neo4j MCPツールでCypherクエリを実行。
---

# 生活保護受給者尊厳支援データベース スキル

## スキル概要

このスキルは、生活保護受給者の尊厳を守るための支援情報を、**7本柱モデル**に基づき包括的に管理するNeo4jグラフデータベースに、**汎用neo4j MCPツール**を通じてアクセスします。

**対象ユーザー**: 生活保護ケースワーカー、福祉事務所職員、相談支援専門員

**設計思想**: 受給者を「ケース番号」ではなく「尊厳ある個人」として支援する

**最重要原則（Safety First）**:
1. **二次被害防止**: NgApproach（避けるべき関わり方）を常に最優先で表示
2. **経済的安全**: EconomicRisk（経済的搾取リスク）を第2優先で表示
3. **批判的表現の変換**: 「怠惰」→「症状により活動が制限されている」等

---

## 使用するMCPツール

| ツール | 用途 |
|--------|------|
| `neo4j:read_neo4j_cypher` | すべての読み取りクエリ |
| `neo4j:write_neo4j_cypher` | データの登録・更新 |
| `neo4j:get_neo4j_schema` | スキーマ確認（必要時のみ） |

---

## データモデル: 7本柱構造

### 第1の柱: ケース記録（最重要）

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:Recipient` | 受給者（中心ノード） | name, caseNumber, dob, gender, address, protectionStartDate |
| `:CaseRecord` | ケース記録 | date, category, content, caseworker, recipientResponse |
| `:HomeVisit` | 家庭訪問記録 | date, observations, recipientCondition, livingEnvironment |
| `:Observation` | 観察記録 | date, content, reliability |

### 第2の柱: 抽出された本人像

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:Strength` | 強み | description, discoveredDate, context, sourceRecord |
| `:Challenge` | 課題 | description, severity, currentStatus, supportNeeded |
| `:MentalHealthStatus` | 精神疾患 | diagnosis, currentStatus, symptoms, treatmentStatus |
| `:Pattern` | 行動パターン | description, frequency, triggers |

### 第3の柱: 関わり方の知恵（効果と禁忌）

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:EffectiveApproach` | 効果的だった関わり方 | description, context, frequency |
| `:NgApproach` | 避けるべき関わり方 ★最重要★ | description, reason, riskLevel, consequence |
| `:TriggerSituation` | 注意が必要な状況 | description, signs, recommendedResponse |

### 第4の柱: 参考情報としての申告歴

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:DeclaredHistory` | 申告された生活歴 | era, content, reliability, declaredDate |
| `:PathwayToProtection` | 保護に至った経緯 | declaredTrigger, declaredTimeline, reliability |
| `:Wish` | 本人の願い | content, priority, declaredDate, status |

### 第5の柱: 社会的ネットワーク

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:KeyPerson` | キーパーソン | name, relationship, contactInfo, role, lastContact |
| `:FamilyMember` | 家族 | name, relationship, contactStatus, supportCapacity, riskFlag |
| `:SupportOrganization` | 支援機関 | name, type, contactPerson, phone, services, utilizationStatus |
| `:MedicalInstitution` | 医療機関 | name, department, doctor, role, visitFrequency |

### 第6の柱: 法的・制度的基盤

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:ProtectionDecision` | 保護決定 | decisionDate, type, protectionCategory, monthlyAmount |
| `:Certificate` | 手帳・証明書 | type, grade, expiryDate |
| `:SupportGoal` | 支援目標 | description, targetDate, status, paceConsideration |

### 第7の柱: 金銭的安全と多機関連携

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:EconomicRisk` | 経済的リスク ★最重要★ | type, perpetrator, perpetratorRelationship, severity, status |
| `:MoneyManagementStatus` | 金銭管理状況 | capability, pattern, riskLevel, observations |
| `:DailyLifeSupportService` | 日常生活自立支援事業 | socialWelfareCouncil, services, status, specialist |
| `:CollaborationRecord` | 多機関連携記録 | date, type, participants, decisions, nextActions |
| `:CasePattern` | 類似案件パターン | patternName, indicators, recommendedInterventions |

### 監査

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:AuditLog` | 監査ログ（ハッシュチェーン） | timestamp, username, action, resourceType, resourceId, clientId, entryHash, previousHash, sequenceNumber |

### 主要リレーション

| リレーション | 方向 | プロパティ |
|-------------|------|-----------
| `MUST_AVOID` | Recipient → NgApproach | — |
| `RESPONDS_WELL_TO` | Recipient → EffectiveApproach | — |
| `HAS_CONDITION` | Recipient → MentalHealthStatus | — |
| `HAS_MONEY_STATUS` | Recipient → MoneyManagementStatus | — |
| `FACES_RISK` | Recipient → EconomicRisk | — |
| `USES_SERVICE` | Recipient → DailyLifeSupportService | — |
| `HAS_RECORD` | Recipient → CaseRecord | — |
| `HAS_STRENGTH` | Recipient → Strength | — |
| `FACES` | Recipient → Challenge | — |
| `HAS_TRIGGER` | Recipient → TriggerSituation | — |
| `DECLARED_HISTORY` | Recipient → DeclaredHistory | — |
| `DECLARED_PATHWAY` | Recipient → PathwayToProtection | — |
| `WISHES` | Recipient → Wish | — |
| `HAS_KEY_PERSON` | Recipient → KeyPerson | rank（優先順位） |
| `HAS_FAMILY` | Recipient → FamilyMember | — |
| `RECEIVES_SUPPORT_FROM` | Recipient → SupportOrganization | — |
| `TREATED_AT` | Recipient → MedicalInstitution | — |
| `HAS_DECISION` | Recipient → ProtectionDecision | — |
| `HOLDS` | Recipient → Certificate | — |
| `HAS_GOAL` | Recipient → SupportGoal | — |
| `SHOWS_PATTERN` | Recipient → Pattern | — |
| `VISITED_ON` | Recipient → HomeVisit | — |
| `ABOUT` | CollaborationRecord → Recipient | — |
| `INVOLVED` | CollaborationRecord → SupportOrganization | — |
| `OBSERVED` | CaseRecord → Observation | — |
| `PROVIDED_BY` | DailyLifeSupportService → SupportOrganization | — |
| `POSES_RISK` | FamilyMember → EconomicRisk | — |
| `MATCHES_PATTERN` | Recipient → CasePattern | — |

---

## Cypherテンプレート集（読み取り）

### 1. 受給者一覧取得

```cypher
MATCH (r:Recipient)
OPTIONAL MATCH (r)-[:MUST_AVOID]->(ng:NgApproach)
OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
WHERE er IS NULL OR er.status = 'Active'
OPTIONAL MATCH (r)-[:HAS_CONDITION]->(mh:MentalHealthStatus)
OPTIONAL MATCH (r)-[:HAS_KEY_PERSON]->(kp:KeyPerson)
RETURN
    r.name AS 氏名,
    r.dob AS 生年月日,
    r.caseNumber AS ケース番号,
    count(DISTINCT ng) AS 禁忌登録数,
    count(DISTINCT er) AS 経済的リスク数,
    count(DISTINCT mh) AS 精神疾患登録数,
    count(DISTINCT kp) AS キーパーソン数
ORDER BY r.name
```

**出力加工**: 生年月日から年齢を計算して併記。

---

### 2. 受給者プロフィール取得（7本柱一括）

7本柱すべての情報を取得するため、**複数クエリに分割して実行**する。

#### 2a. 基本情報 + 第3の柱（関わり方の知恵）★最優先で実行★

```cypher
MATCH (r:Recipient)
WHERE r.name CONTAINS $recipientName

OPTIONAL MATCH (r)-[:MUST_AVOID]->(ng:NgApproach)
OPTIONAL MATCH (r)-[:RESPONDS_WELL_TO]->(ea:EffectiveApproach)
OPTIONAL MATCH (r)-[:HAS_TRIGGER]->(ts:TriggerSituation)

RETURN
    r.name AS 氏名,
    r.dob AS 生年月日,
    r.caseNumber AS ケース番号,
    r.gender AS 性別,
    r.address AS 住所,
    r.protectionStartDate AS 保護開始日,
    collect(DISTINCT {
        description: ng.description,
        reason: ng.reason,
        riskLevel: ng.riskLevel,
        consequence: ng.consequence
    }) AS 避けるべき関わり方,
    collect(DISTINCT {
        description: ea.description,
        context: ea.context
    }) AS 効果的な関わり方,
    collect(DISTINCT {
        description: ts.description,
        signs: ts.signs,
        response: ts.recommendedResponse
    }) AS 注意が必要な状況
```

#### 2b. 第7の柱（金銭的安全）

```cypher
MATCH (r:Recipient)
WHERE r.name CONTAINS $recipientName

OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
WHERE er.status = 'Active'
OPTIONAL MATCH (r)-[:HAS_MONEY_STATUS]->(mms:MoneyManagementStatus)
OPTIONAL MATCH (r)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)

RETURN
    collect(DISTINCT {
        type: er.type,
        perpetrator: er.perpetrator,
        relationship: er.perpetratorRelationship,
        severity: er.severity,
        description: er.description
    }) AS 経済的リスク,
    mms.capability AS 金銭管理能力,
    mms.pattern AS 金銭管理パターン,
    mms.riskLevel AS 金銭管理リスク,
    mms.observations AS 金銭管理所見,
    dlss.socialWelfareCouncil AS 社協名,
    dlss.services AS 日自支援サービス,
    dlss.status AS 日自支援状態,
    dlss.specialist AS 日自支援担当者
```

#### 2c. 第2の柱（本人像）+ 第1の柱（最近のケース記録）

```cypher
MATCH (r:Recipient)
WHERE r.name CONTAINS $recipientName

OPTIONAL MATCH (r)-[:HAS_CONDITION]->(mh:MentalHealthStatus)
OPTIONAL MATCH (r)-[:HAS_STRENGTH]->(s:Strength)
OPTIONAL MATCH (r)-[:HAS_RECORD]->(cr:CaseRecord)

WITH r, mh,
     collect(DISTINCT {description: s.description, context: s.context}) AS 強み,
     cr ORDER BY cr.date DESC
WITH r, mh, 強み,
     collect(DISTINCT {
         date: cr.date,
         category: cr.category,
         content: cr.content,
         response: cr.recipientResponse
     })[..5] AS 最近のケース記録

RETURN
    mh.diagnosis AS 精神疾患_診断,
    mh.currentStatus AS 精神疾患_状態,
    mh.symptoms AS 精神疾患_症状,
    mh.treatmentStatus AS 治療状況,
    強み,
    最近のケース記録
```

#### 2d. 第5の柱（社会的ネットワーク）

```cypher
MATCH (r:Recipient)
WHERE r.name CONTAINS $recipientName

OPTIONAL MATCH (r)-[kpRel:HAS_KEY_PERSON]->(kp:KeyPerson)
OPTIONAL MATCH (r)-[:RECEIVES_SUPPORT_FROM]->(so:SupportOrganization)
OPTIONAL MATCH (r)-[:TREATED_AT]->(mi:MedicalInstitution)

RETURN
    collect(DISTINCT {
        rank: kpRel.rank,
        name: kp.name,
        relationship: kp.relationship,
        contactInfo: kp.contactInfo,
        role: kp.role
    }) AS キーパーソン,
    collect(DISTINCT {
        name: so.name,
        type: so.type,
        contact: so.contactPerson
    }) AS 支援機関,
    collect(DISTINCT {
        name: mi.name,
        department: mi.department,
        doctor: mi.doctor
    }) AS 医療機関
```

**パラメータ**: `$recipientName`

**出力加工**:
- 2a → 2b → 2c → 2d の順で実行
- Safety First: 避けるべき関わり方 → 経済的リスク → 精神疾患 → 効果的な関わり方 の順で表示
- 各collectの結果から主要フィールドが`null`のエントリを除外
- キーパーソンは`rank`昇順でソート
- 7本柱の構造に沿って整形表示

```
⚠️【避けるべき関わり方】（最優先）
⚠️【経済的リスク】（第2優先）
🏥【精神疾患の状況】
💰【金銭管理と支援サービス】
✅【効果的だった関わり方】
💪【強み】
📋【最近のケース記録】
🤝【社会的ネットワーク】
```

---

### 3. データベース統計情報

```cypher
MATCH (n)
WHERE n:Recipient OR n:NgApproach OR n:EffectiveApproach OR n:EconomicRisk
   OR n:MoneyManagementStatus OR n:MentalHealthStatus OR n:CaseRecord
   OR n:KeyPerson OR n:FamilyMember OR n:SupportOrganization
   OR n:Certificate OR n:CollaborationRecord OR n:AuditLog
   OR n:Strength OR n:DailyLifeSupportService
WITH labels(n)[0] AS label
RETURN label AS ノード種別, count(*) AS 登録数
ORDER BY 登録数 DESC
```

---

### 4. 証明書の更新期限チェック

```cypher
MATCH (r:Recipient)-[:HOLDS]->(cert:Certificate)
WHERE cert.expiryDate IS NOT NULL
  AND ($recipientName = '' OR r.name CONTAINS $recipientName)
WITH r, cert,
     duration.inDays(date(), cert.expiryDate).days AS daysUntilExpiry
WHERE daysUntilExpiry <= $days AND daysUntilExpiry >= 0
RETURN
    r.name AS 受給者,
    cert.type AS 証明書種類,
    cert.grade AS 等級,
    cert.expiryDate AS 有効期限,
    daysUntilExpiry AS 残り日数
ORDER BY daysUntilExpiry ASC
```

**パラメータ**: `$recipientName`（空文字で全員）, `$days`（デフォルト90）

**出力加工**: 残り日数で緊急度をグループ化

---

### 5. ケース記録の取得

```cypher
MATCH (r:Recipient)-[:HAS_RECORD]->(cr:CaseRecord)
WHERE r.name CONTAINS $recipientName
RETURN cr.date AS 日付,
       cr.category AS 区分,
       cr.content AS 内容,
       cr.caseworker AS 記録者,
       cr.recipientResponse AS 本人の反応
ORDER BY cr.date DESC
LIMIT $limit
```

**パラメータ**: `$recipientName`, `$limit`（デフォルト10、最大50）

---

### 6. 効果的ケアパターンの発見

```cypher
MATCH (r:Recipient)-[:RESPONDS_WELL_TO]->(ea:EffectiveApproach)
WHERE r.name CONTAINS $recipientName
RETURN ea.description AS 効果的な関わり方,
       ea.context AS 状況,
       ea.frequency AS 頻度
```

**パラメータ**: `$recipientName`

---

### 7. 監査ログ取得

```cypher
MATCH (al:AuditLog)
WHERE ($recipientName = '' OR al.clientId CONTAINS $recipientName)
  AND ($userName = '' OR al.username CONTAINS $userName)
RETURN al.timestamp AS 日時,
       al.username AS 操作者,
       al.action AS 操作,
       al.resourceType AS 対象種別,
       al.resourceId AS 対象名,
       al.details AS 詳細,
       al.clientId AS 受給者,
       al.sequenceNumber AS 連番,
       al.entryHash AS ハッシュ
ORDER BY al.timestamp DESC
LIMIT $limit
```

**パラメータ**: `$recipientName`（空文字OK）, `$userName`（空文字OK）, `$limit`（デフォルト30）

---

### 8. 受給者変更履歴

```cypher
MATCH (al:AuditLog)
WHERE al.clientId CONTAINS $recipientName
RETURN al.timestamp AS 日時,
       al.username AS 操作者,
       al.action AS 操作,
       al.resourceType AS 対象種別,
       al.resourceId AS 内容,
       al.details AS 詳細
ORDER BY al.timestamp DESC
LIMIT $limit
```

**パラメータ**: `$recipientName`, `$limit`（デフォルト20）

---

### 9. 訪問前ブリーフィング

訪問前に必ず確認すべき情報を Safety First 順で取得。

```cypher
MATCH (r:Recipient)
WHERE r.name CONTAINS $recipientName

OPTIONAL MATCH (r)-[:MUST_AVOID]->(ng:NgApproach)
OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
WHERE er.status = 'Active'
OPTIONAL MATCH (r)-[:HAS_CONDITION]->(mh:MentalHealthStatus)
OPTIONAL MATCH (r)-[:HAS_MONEY_STATUS]->(mms:MoneyManagementStatus)
OPTIONAL MATCH (r)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)
OPTIONAL MATCH (r)-[:RESPONDS_WELL_TO]->(ea:EffectiveApproach)

RETURN r.name AS 受給者名,
       collect(DISTINCT {
         description: ng.description,
         reason: ng.reason,
         risk: ng.riskLevel
       }) AS 避けるべき関わり方,
       collect(DISTINCT {
         type: er.type,
         perpetrator: er.perpetrator,
         severity: er.severity
       }) AS 経済的リスク,
       mh.diagnosis AS 精神疾患,
       mh.currentStatus AS 疾患の状態,
       mms.capability AS 金銭管理能力,
       mms.pattern AS 金銭管理パターン,
       dlss.services AS 自立支援サービス,
       collect(DISTINCT {
         description: ea.description,
         context: ea.context
       }) AS 効果的な関わり方
```

**パラメータ**: `$recipientName`

**出力加工**:
```
⚠️ 避けるべき関わり方（最初に必ず確認）
⚠️ 経済的リスク（搾取の有無）
🏥 精神疾患の状況
💰 金銭管理状況と支援サービス
✅ 効果的だった関わり方
```

---

### 10. 引き継ぎサマリー

担当者交代時に新担当者へ渡す情報を取得。テンプレート2（プロフィール一括）の結果を以下の順序で整形する。

**出力構造**:
```
# {受給者名}さん 引き継ぎサマリー

## ⚠️ 避けるべき関わり方（最初に警告）
## ⚠️ 経済的リスク
## 🏥 精神疾患の状況
## ✅ 効果的だった関わり方
## 💪 発見された強み
## 💰 金銭管理と支援サービス
## 🤝 連携機関
```

テンプレート2のクエリ群を実行し、上記順序で整形すること。

---

### 11. 類似案件検索

```cypher
MATCH (target:Recipient)
WHERE target.name CONTAINS $recipientName
MATCH (target)-[:FACES_RISK]->(er:EconomicRisk)
WITH target, collect(er.type) AS targetRiskTypes

MATCH (other:Recipient)-[:FACES_RISK]->(otherRisk:EconomicRisk)
WHERE other.name <> target.name
  AND otherRisk.type IN targetRiskTypes
OPTIONAL MATCH (other)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)

RETURN DISTINCT
       other.name AS 類似ケース,
       collect(DISTINCT otherRisk.type) AS 共通リスク,
       dlss.services AS 利用サービス,
       otherRisk.status AS リスク状態
```

**パラメータ**: `$recipientName`

---

### 12. 多機関連携履歴

```cypher
MATCH (cr:CollaborationRecord)-[:ABOUT]->(r:Recipient)
WHERE r.name CONTAINS $recipientName
OPTIONAL MATCH (cr)-[:INVOLVED]->(so:SupportOrganization)
RETURN cr.date AS 日付,
       cr.type AS 種別,
       cr.participants AS 参加者,
       cr.decisions AS 決定事項,
       cr.nextActions AS 次回アクション,
       collect(so.name) AS 関係機関
ORDER BY cr.date DESC
LIMIT $limit
```

**パラメータ**: `$recipientName`, `$limit`（デフォルト10）

---

## データ登録パターン（書き込みクエリ）

### ★重要: AI構造化プロセス

旧システムでは Gemini API でケース記録テキストを構造化していたが、スキルベースの新システムでは **Claude自身がテキストを構造化** してからCypherで登録する。

#### 構造化の手順

1. ユーザーからケース記録テキストを受け取る
2. 以下の情報を抽出:
   - `category`: 相談/訪問/電話/来所/同行/会議/その他
   - `content`: 記録内容
   - `caseworker`: 記録者名
   - `recipientResponse`: 本人の反応
   - `observations`: 観察された事実のリスト
3. **同時に以下も検出**:
   - 避けるべき関わり方（NgApproach）
   - 経済的リスクのサイン
   - 効果的だった関わり方
   - 多機関連携のサイン
   - 批判的表現（変換が必要）

---

### ケース記録の登録

```cypher
MATCH (r:Recipient {name: $recipientName})
CREATE (cr:CaseRecord {
    date: date($date),
    category: $category,
    content: $content,
    caseworker: $caseworker,
    recipientResponse: $response,
    createdAt: datetime()
})
CREATE (r)-[:HAS_RECORD]->(cr)
RETURN cr.date AS 日付, cr.category AS 区分
```

**パラメータ**: `$recipientName`, `$date`, `$category`, `$content`, `$caseworker`, `$response`

---

### NgApproach（避けるべき関わり方）の登録

```cypher
MATCH (r:Recipient {name: $recipientName})
CREATE (ng:NgApproach {
    description: $description,
    reason: $reason,
    riskLevel: $riskLevel,
    consequence: $consequence,
    createdAt: datetime()
})
CREATE (r)-[:MUST_AVOID]->(ng)
RETURN ng.description AS 内容, ng.riskLevel AS リスク
```

**パラメータ**: `$recipientName`, `$description`, `$reason`, `$riskLevel` (High/Medium/Low), `$consequence`

---

### EconomicRisk（経済的リスク）の登録

```cypher
MATCH (r:Recipient {name: $recipientName})
CREATE (er:EconomicRisk {
    type: $type,
    perpetrator: $perpetrator,
    perpetratorRelationship: $relationship,
    severity: $severity,
    description: $description,
    discoveredDate: date($discoveredDate),
    status: $status,
    createdAt: datetime()
})
CREATE (r)-[:FACES_RISK]->(er)

WITH r, er
OPTIONAL MATCH (fm:FamilyMember {recipientName: $recipientName})
WHERE fm.relationship = $relationship OR fm.name = $perpetrator
FOREACH (_ IN CASE WHEN fm IS NOT NULL THEN [1] ELSE [] END |
    MERGE (fm)-[:POSES_RISK]->(er)
    SET fm.riskFlag = true
)

RETURN er.type AS 種類, er.severity AS 深刻度
```

**パラメータ**: `$recipientName`, `$type`, `$perpetrator`, `$relationship`, `$severity` (High/Medium/Low), `$description`, `$discoveredDate`, `$status` (Active/Monitoring/Resolved)

---

### MoneyManagementStatus（金銭管理状況）の登録

```cypher
MATCH (r:Recipient {name: $recipientName})
MERGE (mms:MoneyManagementStatus {recipientName: $recipientName})
SET mms.capability = $capability,
    mms.pattern = $pattern,
    mms.riskLevel = $riskLevel,
    mms.observations = $observations,
    mms.assessmentDate = date($assessmentDate),
    mms.updatedAt = datetime()
MERGE (r)-[:HAS_MONEY_STATUS]->(mms)
RETURN mms.capability AS 能力, mms.riskLevel AS リスク
```

**パラメータ**: `$recipientName`, `$capability` (自己管理可能/支援があれば可能/支援が必要/困難/不明), `$pattern`, `$riskLevel`, `$observations`, `$assessmentDate`

---

### EffectiveApproach（効果的だった関わり方）の登録

```cypher
MATCH (r:Recipient {name: $recipientName})
CREATE (ea:EffectiveApproach {
    description: $description,
    context: $context,
    frequency: $frequency,
    createdAt: datetime()
})
CREATE (r)-[:RESPONDS_WELL_TO]->(ea)
RETURN ea.description AS 内容
```

**パラメータ**: `$recipientName`, `$description`, `$context`, `$frequency`

---

### SupportOrganization（支援機関）の登録

```cypher
MATCH (r:Recipient {name: $recipientName})
MERGE (so:SupportOrganization {name: $orgName})
SET so.type = $orgType,
    so.contactPerson = $contactPerson,
    so.phone = $phone,
    so.services = $services,
    so.utilizationStatus = $status,
    so.updatedAt = datetime()
MERGE (r)-[:RECEIVES_SUPPORT_FROM]->(so)
RETURN so.name AS 機関名
```

**パラメータ**: `$recipientName`, `$orgName`, `$orgType`, `$contactPerson`, `$phone`, `$services`, `$status` (利用中/利用終了/調整中)

---

### CollaborationRecord（多機関連携記録）の登録

```cypher
MATCH (r:Recipient {name: $recipientName})
CREATE (cr:CollaborationRecord {
    date: date($date),
    type: $type,
    participants: $participants,
    agenda: $agenda,
    discussion: $discussion,
    decisions: $decisions,
    nextActions: $nextActions,
    createdBy: $createdBy,
    createdAt: datetime()
})
CREATE (cr)-[:ABOUT]->(r)
RETURN cr.date AS 日付, cr.type AS 種別
```

**パラメータ**: `$recipientName`, `$date`, `$type` (ケース会議/情報共有/緊急対応/定期連絡), `$participants` (配列), `$agenda`, `$discussion`, `$decisions` (配列), `$nextActions` (配列), `$createdBy`

---

### 監査ログの記録

データ変更時には必ず監査ログを残す。

```cypher
CREATE (al:AuditLog {
    timestamp: datetime(),
    username: $userName,
    action: $action,
    resourceType: $resourceType,
    resourceId: $resourceId,
    details: $details,
    clientId: $recipientName,
    result: 'SUCCESS'
})
RETURN al.timestamp AS 記録日時
```

**パラメータ**: `$userName`, `$action` (CREATE/UPDATE/DELETE), `$resourceType`, `$resourceId`, `$details`, `$recipientName`

---

## AI処理ルール

### ルール1: 批判的表現の変換

ケース記録テキストに以下の表現があった場合、登録前に適切に変換する。

| 入力表現 | 変換後 |
|---------|--------|
| 「怠惰」「怠けている」 | 「症状により活動が制限されている」 |
| 「指導した」 | 「情報提供した（本人の反応を確認）」 |
| 「改善しない」 | 「現時点では変化が見られない」 |
| 「嘘をついている」 | 「申告内容と記録に相違がある」 |
| 「問題ケース」 | 「複合的な支援ニーズがある」 |
| 「言うことを聞かない」 | 「本人の意向と支援方針に相違がある」 |
| 「何度言っても」 | 「別のアプローチを検討する必要がある」 |
| 「金遣いが荒い」 | 「金銭管理に支援が必要」 |
| 「家族に甘い」 | 「家族との関係性に課題がある」 |

**重要**: 変換が必要な表現を検出した場合、ユーザーに検出結果を報告してから変換して登録する。

---

### ルール2: 経済的リスクサインの検出

ケース記録テキストから以下のパターンを検出し、EconomicRiskの登録を提案する。

| テキストパターン | リスクサイン | 想定原因 |
|-----------------|------------|---------|
| 「お金がない」「足りない」（受給日直後） | 金銭不足 | 金銭搾取, 浪費, 金銭管理困難 |
| 「息子/娘/家族」+「渡した/持っていかれた/取られた」 | 親族への金銭流出 | 金銭搾取 |
| 「息子/娘/家族」+「来て/来ると」+「お金/金」 | 親族の訪問と金銭の関連 | 金銭搾取, 無心・たかり |
| 「断ると/断れない」+「怒/怖」 | 金銭要求への恐怖 | 無心・たかり, 金銭搾取 |
| 「通帳」+「預けている/渡している/管理されている」 | 通帳の他者管理 | 通帳管理強要 |
| 「受給日」+「数日/すぐ」+「ない/なくなる」 | 受給日直後の金銭枯渇 | 金銭搾取, 浪費 |
| 「パチンコ」「競馬」「ギャンブル」 | ギャンブルへの言及 | 浪費 |
| 「借金/ローン」+「代わりに/肩代わり」 | 借金の肩代わり | 借金の肩代わり強要 |
| 「電話/メール」+「送金/振込」 | 遠隔での送金 | 詐欺被害リスク |

**重要**: リスクサインを検出した場合、必ずユーザーに報告し、EconomicRisk登録の確認を求める。

---

### ルール3: 多機関連携サインの検出

| テキストパターン | 連携種別 |
|-----------------|---------
| 「ケース会議」「カンファレンス」 | ケース会議 |
| 「社協」「社会福祉協議会」 | 社会福祉協議会との連携 |
| 「地域包括」「包括支援」 | 地域包括支援センターとの連携 |
| 「日常生活自立支援」「日自」「金銭管理サービス」 | 日常生活自立支援事業 |
| 「主治医/病院/クリニック」+「連絡/相談/報告」 | 医療機関との連携 |

連携サインを検出した場合、CollaborationRecordの登録を提案する。

---

## AI運用プロトコル

### プロトコル1: Safety First（最重要）

受給者情報を表示する際は、常に以下の順序を守る:
1. ⚠️ NgApproach（避けるべき関わり方）
2. ⚠️ EconomicRisk（経済的リスク）
3. 🏥 MentalHealthStatus（精神疾患）
4. ✅ EffectiveApproach（効果的な関わり方）
5. その他の情報

### プロトコル2: 緊急時は emergency-protocol を優先

「パニック」「事故」「急病」「緊急」「搾取」「暴力」などのワードを検知したら、**`emergency-protocol` スキル**の利用を検討すること。

### プロトコル3: 書き込み時は確認を求める

データの新規登録・更新前に、登録内容をユーザーに確認すること。特に:
- NgApproach（避けるべき関わり方）の新規登録
- EconomicRisk（経済的リスク）の登録
- MoneyManagementStatus（金銭管理状況）の更新

### プロトコル4: パラメータ化クエリの徹底

すべてのクエリで `$param` 形式のパラメータを使用。文字列連結によるCypher構築は**禁止**。

### プロトコル5: 監査ログの記録

すべてのデータ変更操作後に、監査ログを記録すること。

### プロトコル6: 年齢の自動計算

生年月日（dob）が取得できた場合、必ず現在の年齢を計算して併記する。

### プロトコル7: 金銭管理能力の自動チェック

プロフィール表示時に以下を自動チェック:
- 金銭管理が「困難」「支援が必要」 → 日常生活自立支援事業の利用がなければ提案
- 深刻な経済的リスクがある → 日常生活自立支援事業の導入を推奨
- 精神疾患あり＋NgApproachなし → NgApproach登録を促す

---

## 典型的なユースケース

### ケース1: 訪問前の準備

```
ユーザー: 「田中太郎さんの訪問前ブリーフィング」

手順:
1. テンプレート9（訪問前ブリーフィング）を実行
2. Safety First順で表示
3. 前回の訪問記録があればテンプレート5で確認
```

### ケース2: ケース記録の追加

```
ユーザー: 「田中太郎さんの記録: 今日訪問したら『お金がない』と訴えた。
受給日から3日しか経っていない。息子が来てお金を持っていったとのこと。」

手順:
1. テキストを構造化（CaseRecord）
2. 経済的リスクサインを検出:
   - 「お金がない」（受給日直後）→ 金銭不足
   - 「息子が来てお金を持っていった」→ 親族による金銭搾取
3. 検出結果をユーザーに報告
4. ケース記録の登録（確認後）
5. EconomicRisk登録を提案（確認後）
6. 監査ログ記録
```

### ケース3: 引き継ぎ

```
ユーザー: 「田中太郎さんの引き継ぎサマリーを作って」

手順:
1. テンプレート2のクエリ群を実行
2. テンプレート10の構造で整形
3. Safety First順で表示
```

### ケース4: 批判的表現の検出

```
ユーザー: 「記録: 田中さんは怠惰で、何度指導しても改善しない。
金遣いが荒く、受給日にすぐ使い果たす。」

手順:
1. 批判的表現を検出:
   - 「怠惰」→「症状により活動が制限されている」
   - 「指導しても」→「情報提供したが」
   - 「改善しない」→「現時点では変化が見られない」
   - 「金遣いが荒く」→「金銭管理に支援が必要で」
2. 変換結果をユーザーに報告
3. 変換後のテキストでケース記録を登録
4. 金銭管理リスクサインも検出・報告
```

---

## 関連スキルとの連携

| スキル | 連携タイミング |
|--------|---------------
| `emergency-protocol` | 緊急ワード検知時に即座に切り替え |
| `neo4j-support-db` | 障害福祉サービス利用者の情報参照（別スキーマ注意） |
| `ecomap-generator` | 支援ネットワーク図の生成 |
| `provider-search` | 事業所検索（該当する場合） |
| `pdf` / `xlsx` | レポート出力時 |

---

## セキュリティとプライバシー

### 最重要取り扱い注意情報
- NgApproach（避けるべき関わり方）- 悪用されると二次被害
- EconomicRisk（経済的リスク）- 加害者情報含む
- FamilyMember（家族情報）- riskFlagの取り扱い注意

### 監査ログのハッシュチェーン
- 全操作がハッシュチェーンで記録される
- 改ざん防止のためSHA-256ハッシュチェーンを使用
- 各エントリは前のエントリのハッシュを含む

### アクセス制御
- 本人・家族からの要望があれば、データの修正・削除に応じる
- 変更時は必ず監査ログを残す

---

## ⚠️ neo4j-support-db との違い

| 項目 | neo4j-support-db | livelihood-support |
|------|------------------|--------------------|
| 中心ノード | `:Client` | `:Recipient` |
| モデル | 4本柱 | 7本柱 |
| 禁忌ノード | `:NgAction` | `:NgApproach` |
| 禁忌リレーション | `MUST_AVOID` | `MUST_AVOID` |
| 経済的リスク | なし | `:EconomicRisk` |
| 金銭管理 | なし | `:MoneyManagementStatus` |
| 効果的ケア | `:CarePreference` | `:EffectiveApproach` |
| 支援記録 | `:SupportLog` | `:CaseRecord` |
| 監査ログ | 単純記録 | ハッシュチェーン |
| Neo4jポート | bolt://localhost:7687 | bolt://localhost:7688 |

**重要**: 2つのスキーマは**別のNeo4jインスタンス**で稼働している。neo4j MCPツールの接続先を正しく設定すること。
- support-db: `bolt://localhost:7687`（HTTP: 7474）
- livelihood-support: `bolt://localhost:7688`（HTTP: 7475）

---

## バージョン

- v2.0.0 (2026-02-12) - neo4j MCPツールベースに移行、Cypherテンプレート集追加
- v1.0.0 - livelihood-support-db カスタムMCPツールベース（旧版）
