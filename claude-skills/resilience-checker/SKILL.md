---
name: resilience-checker
description: 「もし親が倒れたら」をシミュレーションし、親が担っている機能（CareRole）の代替手段カバー率を診断するスキル。マニフェスト第5の柱「親の機能移行（Parental Transition）」を中核とし、未カバーのタスクに対する福祉サービス候補の検索も行う。「レジリエンス」「親亡き後」「もしもの時」「親が倒れたら」「カバー率」「バックアップ体制」「機能移行」「親の入院」「親が認知症」などの話題で必ずこのスキルを使用すること。parent_downプロトコル発動時にも使用する。
---

# レジリエンス診断スキル (resilience-checker)

## このスキルの意義

「親亡き後支援」の名の通り、このプロジェクトの根幹は「親がいなくなった後も本人の生活が維持できるか」にあります。親が日常的に担っている機能（食事準備、服薬管理、金銭管理、送迎など）を洗い出し、それぞれに代替手段が確保されているかを可視化することで、支援体制の脆弱性を事前に発見し、備えることができます。

## 対象ユーザー

- 計画相談支援専門員
- 支援会議の参加者
- 親の入院・死亡等の緊急時に対応する支援者

## トリガーワード

- 「レジリエンスチェック」「レジリエンス診断」「カバー率」
- 「親亡き後」「もしもの時」「親が倒れたら」「親が入院したら」
- 「バックアップ体制を確認」「機能移行」
- 「支援計画の見直し」（第5の柱に関する場合）

---

## 使用するMCPツール

| ツール | 用途 |
|--------|------|
| `neo4j:read_neo4j_cypher` | CareRole・代替手段・事業所の読み取り |
| `neo4j:write_neo4j_cypher` | CareRole の登録・更新（必要時） |

---

## データモデル（第5の柱: Parental Transition）

このスキルが主に扱うノードとリレーション:

```
(:Client)<-[:IS_PARENT_OF|FAMILY_OF]-(:Relative)
(:Relative)-[:PERFORMS]->(:CareRole)
(:CareRole)-[:CAN_BE_PERFORMED_BY]->(:ServiceProvider|:Supporter|:KeyPerson)
```

| ノード | 主要プロパティ |
|--------|---------------|
| `:Relative` | name, relationship, healthStatus, age |
| `:CareRole` | name, frequency, priority, notes |

| リレーション | 意味 |
|-------------|------|
| `IS_PARENT_OF` / `FAMILY_OF` | 親→クライアント |
| `PERFORMS` | 親→CareRole（親がこの役割を担っている） |
| `CAN_BE_PERFORMED_BY` | CareRole→代替手段（サービス/支援者/キーパーソン） |

---

## 実行手順

### Step 1: クライアント全体像の把握

まずクライアントの基本情報と親の情報を取得する。

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $clientName

OPTIONAL MATCH (c)<-[:IS_PARENT_OF|FAMILY_OF]-(r:Relative)
OPTIONAL MATCH (c)-[:USES_SERVICE]->(sp:ServiceProvider)
WHERE sp IS NULL OR NOT EXISTS { MATCH (c)-[rel:USES_SERVICE]->(sp) WHERE rel.status = 'Ended' }

RETURN
    c.name AS クライアント名,
    c.dob AS 生年月日,
    collect(DISTINCT {
        name: r.name,
        relationship: r.relationship,
        healthStatus: r.healthStatus,
        age: r.age
    }) AS 家族,
    collect(DISTINCT {
        name: sp.name,
        serviceType: COALESCE(sp.serviceType, sp.service_type)
    }) AS 利用中サービス
```

### Step 2: CareRoleの一覧と代替手段の取得

親が担っているタスクと、それぞれの代替手段を取得する。

```cypher
MATCH (c:Client)<-[:IS_PARENT_OF|FAMILY_OF]-(r:Relative)-[:PERFORMS]->(cr:CareRole)
WHERE c.name CONTAINS $clientName

OPTIONAL MATCH (cr)-[:CAN_BE_PERFORMED_BY]->(alt)

RETURN
    r.name AS 担当者,
    r.healthStatus AS 健康状態,
    cr.name AS タスク名,
    cr.frequency AS 頻度,
    cr.priority AS 優先度,
    cr.notes AS 備考,
    collect(DISTINCT {
        type: labels(alt)[0],
        name: alt.name,
        phone: alt.phone,
        serviceType: alt.serviceType
    }) AS 代替手段
ORDER BY cr.priority DESC
```

### Step 3: カバー率の算出

Step 2の結果から、各CareRoleのカバー状態を判定する。

| カバー状態 | アイコン | 判定基準 |
|-----------|---------|---------|
| 完全カバー | ✅ | 代替サービスまたは代替人物が1つ以上登録済み |
| 部分カバー | ⚠️ | 代替手段はあるが、頻度や種類に不足がある |
| 未カバー | 🚨 | 代替手段なし。緊急の支援調整が必要 |

**カバー率 = 完全カバーのCareRole数 / 全CareRole数 × 100%**

### Step 4: 未カバーのCareRoleに対する候補検索

未カバーのCareRoleがある場合、対応可能な福祉サービス事業所を検索する。

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $clientName
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(con:Condition)

// クライアントの居住地域を推定
OPTIONAL MATCH (c)-[:USES_SERVICE]->(existingSp:ServiceProvider)

WITH c, collect(DISTINCT con.name) AS 特性一覧,
     collect(DISTINCT existingSp.city)[0] AS 推定市区町村

// 該当サービス種類の事業所を検索
MATCH (sp:ServiceProvider)
WHERE sp.city = 推定市区町村
  AND COALESCE(sp.serviceType, sp.service_type) CONTAINS $serviceKeyword
  AND (sp.availability IS NULL OR sp.availability <> '満員')
RETURN
    COALESCE(sp.name, sp.office_name) AS 事業所名,
    COALESCE(sp.serviceType, sp.service_type) AS サービス種類,
    sp.city AS 市区町村,
    sp.phone AS 電話番号,
    sp.availability AS 空き状況
LIMIT 10
```

**パラメータ**: `$clientName`, `$serviceKeyword`（CareRoleに応じて設定。例: 食事準備→「居宅介護」、送迎→「移動支援」）

### Step 5: レジリエンス・レポートの出力

```markdown
## レジリエンス診断レポート
**対象:** [クライアント名]（[年齢]歳）
**診断日:** [日付]
**総合カバー率:** [XX]%

---

### 親の状況
| 氏名 | 続柄 | 年齢 | 健康状態 |
|------|------|------|---------|
| [親の名前] | [続柄] | [年齢] | [healthStatus] |

### CareRole カバー状況

| # | タスク | 担当 | 頻度 | 代替手段 | 状態 |
|---|--------|------|------|---------|------|
| 1 | 食事準備 | 母 | 毎日 | ヘルパー（居宅介護） | ✅ |
| 2 | 服薬管理 | 母 | 毎日 | なし | 🚨 |
| 3 | 送迎 | 父 | 週5 | 移動支援事業所 | ⚠️ |

### 🚨 緊急対応が必要なタスク

**服薬管理** — 現在、代替手段が登録されていません。
→ 候補事業所:
  - [事業所A]（居宅介護）TEL: xxx-xxxx 空き: あり
  - [事業所B]（居宅介護）TEL: xxx-xxxx 空き: 要相談

### 推奨アクション
1. [未カバーのCareRoleへの対応策]
2. [部分カバーの改善策]
3. [次回確認すべき事項]
```

---

## CareRole の登録（データがない場合）

CareRoleが未登録のクライアントの場合、親への聞き取りを元に登録する。

### 典型的なCareRole

| タスク名 | 頻度例 | 対応サービス例 |
|---------|--------|-------------|
| 食事準備 | 毎日 | 居宅介護、配食サービス |
| 服薬管理 | 毎日 | 居宅介護、訪問看護 |
| 金銭管理 | 月1-2回 | 日常生活自立支援事業、後見人 |
| 送迎 | 週3-5 | 移動支援、事業所送迎 |
| 入浴介助 | 週2-3 | 居宅介護、デイサービス |
| パニック対応 | 不定期 | 行動援護、短期入所 |
| 身辺介助 | 毎日 | 居宅介護、グループホーム |
| 見守り | 常時 | グループホーム、日中一時支援 |

### 登録Cypher

```cypher
MATCH (c:Client)<-[:IS_PARENT_OF|FAMILY_OF]-(r:Relative)
WHERE c.name CONTAINS $clientName AND r.name CONTAINS $relativeName
MERGE (cr:CareRole {name: $taskName})
SET cr.frequency = $frequency,
    cr.priority = $priority,
    cr.notes = $notes
MERGE (r)-[:PERFORMS]->(cr)
RETURN cr.name AS タスク, r.name AS 担当者
```

### 代替手段の紐付けCypher

```cypher
MATCH (cr:CareRole {name: $taskName})
MATCH (alt)
WHERE (alt:ServiceProvider OR alt:Supporter OR alt:KeyPerson)
  AND alt.name CONTAINS $altName
MERGE (cr)-[:CAN_BE_PERFORMED_BY]->(alt)
RETURN cr.name AS タスク, alt.name AS 代替手段
```

---

## Parent Down プロトコルとの連携

`protocols/parent_down.md` が発動した場合（親の入院・死亡等）、このスキルは「事前準備型」から「緊急対応型」に切り替わります。

緊急時は:
1. まず `emergency-protocol` で安全を確保
2. このスキルで CareRole のカバー状況を即座に確認
3. 未カバーのタスクに対する緊急手配を開始

---

## 関連スキル

| スキル | 連携 |
|--------|------|
| `emergency-protocol` | 親の急変時の安全確保 |
| `provider-search` | 代替事業所の詳細検索・口コミ確認 |
| `ecomap-generator` | 支援体制の可視化 |
| `neo4j-support-db` | クライアント基本情報の参照 |
