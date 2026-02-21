---
name: neo4j-support-db
description: 知的障害・精神障害のある方の支援情報を包括的に管理するNeo4jグラフデータベース。汎用neo4j MCPツールを通じてCypherクエリを実行し、計画相談支援業務を支援する。
---

# Neo4j親亡き後支援データベース スキル

## スキル概要

このスキルは、知的障害・精神障害のある方の支援情報を包括的に管理するNeo4jグラフデータベースに、**汎用neo4j MCPツール**を通じてアクセスし、計画相談支援業務を支援します。

**対象ユーザー**: 計画相談支援専門員、障害福祉サービス事業者、支援コーディネーター

**主な機能**:
- クライアント情報の検索・登録
- 支援記録の蓄積と効果的ケアパターンの発見
- 手帳・受給者証の更新期限管理
- 監査ログ・変更履歴の追跡
- データベース統計の確認

**注意**: 緊急時対応は `emergency-protocol` スキルを使用してください。

---

## 使用するMCPツール

| ツール | 用途 |
|--------|------|
| `neo4j:read_neo4j_cypher` | すべての読み取りクエリ |
| `neo4j:write_neo4j_cypher` | データの登録・更新 |
| `neo4j:get_neo4j_schema` | スキーマ確認（必要時のみ） |

---

## データモデル: 4本柱構造

### 第1の柱: 本人性（Identity & Narrative）

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:Client` | 本人 | name, dob, bloodType |
| `:LifeHistory` | 生育歴 | era, episode |
| `:Wish` | 願い | content, status |

### 第2の柱: ケアの暗黙知（Care Instructions）

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:CarePreference` | 推奨ケア | category, instruction, priority |
| `:NgAction` | 禁忌事項 ★最重要★ | action, reason, riskLevel |
| `:Condition` | 特性・診断 | name, status |

### 第3の柱: 法的基盤（Legal Basis）

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:Certificate` | 手帳・受給者証 | type, grade, nextRenewalDate |
| `:PublicAssistance` | 公的扶助 | type, grade |

### 第4の柱: 危機管理ネットワーク（Safety Net）

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:KeyPerson` | キーパーソン | name, relationship, phone, role |
| `:Guardian` | 法的代理人 | name, type, phone, organization |
| `:Supporter` | 支援者 | name, role, organization |
| `:Hospital` | 医療機関 | name, specialty, doctor, phone |

### 支援記録・監査

| ノード | 用途 | 主要プロパティ |
|--------|------|----------------|
| `:SupportLog` | 支援記録 | date, situation, action, effectiveness, note |
| `:AuditLog` | 監査ログ | timestamp, user, action, targetType, targetName, details, clientName |

### 主要リレーション

| リレーション | 方向 | プロパティ |
|-------------|------|-----------
| `MUST_AVOID` | Client → NgAction | — |
| `REQUIRES` | Client → CarePreference | — |
| `HAS_CONDITION` | Client → Condition | — |
| `HAS_KEY_PERSON` | Client → KeyPerson | rank（優先順位） |
| `HAS_LEGAL_REP` | Client → Guardian | — |
| `HAS_CERTIFICATE` | Client → Certificate | — |
| `RECEIVES` | Client → PublicAssistance | — |
| `HAS_HISTORY` | Client → LifeHistory | — |
| `HAS_WISH` | Client → Wish | — |
| `TREATED_AT` | Client → Hospital | — |
| `SUPPORTED_BY` | Client → Supporter | — |
| `LOGGED` | Supporter → SupportLog | — |
| `ABOUT` | SupportLog → Client | — |
| `IN_CONTEXT` | NgAction → Condition | — |
| `ADDRESSES` | CarePreference → Condition | — |

---

## Cypherテンプレート集

### 1. クライアント一覧取得

全クライアントの情報登録状況を一覧表示する。

```cypher
MATCH (c:Client)
OPTIONAL MATCH (c)-[:MUST_AVOID]->(ng:NgAction)
OPTIONAL MATCH (c)-[:REQUIRES]->(cp:CarePreference)
OPTIONAL MATCH (c)-[:HAS_KEY_PERSON]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(cert:Certificate)
OPTIONAL MATCH (c)-[:HAS_LEGAL_REP]->(g:Guardian)
RETURN
    c.name AS 氏名,
    c.dob AS 生年月日,
    count(DISTINCT ng) AS 禁忌登録数,
    count(DISTINCT cp) AS 配慮事項数,
    count(DISTINCT kp) AS キーパーソン数,
    count(DISTINCT cert) AS 手帳数,
    count(DISTINCT g) AS 後見人
ORDER BY c.name
```

**出力加工**: 生年月日から年齢を計算して `生年月日（年齢）` として併記すること。
例: `1995-03-15` → `1995-03-15（30歳）`

---

### 2. クライアントプロフィール取得（4本柱一括）

マニフェスト4本柱すべての情報を1クエリで取得する。

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $clientName

// 第1の柱：本人性
OPTIONAL MATCH (c)-[:HAS_HISTORY]->(h:LifeHistory)
OPTIONAL MATCH (c)-[:HAS_WISH]->(w:Wish)

// 第2の柱：ケアの暗黙知
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(con:Condition)
OPTIONAL MATCH (c)-[:REQUIRES]->(cp:CarePreference)
OPTIONAL MATCH (c)-[:MUST_AVOID]->(ng:NgAction)

// 第3の柱：法的基盤
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(cert:Certificate)
OPTIONAL MATCH (c)-[:RECEIVES]->(pa:PublicAssistance)

// 第4の柱：危機管理ネットワーク
OPTIONAL MATCH (c)-[kpRel:HAS_KEY_PERSON]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:HAS_LEGAL_REP]->(g:Guardian)
OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(s:Supporter)
OPTIONAL MATCH (c)-[:TREATED_AT]->(hosp:Hospital)

RETURN
    c.name AS 氏名,
    c.dob AS 生年月日,
    c.bloodType AS 血液型,
    collect(DISTINCT {era: h.era, episode: h.episode}) AS 生育歴,
    collect(DISTINCT {content: w.content, status: w.status}) AS 願い,
    collect(DISTINCT {name: con.name, status: con.status}) AS 特性_診断,
    collect(DISTINCT {category: cp.category, instruction: cp.instruction, priority: cp.priority}) AS 配慮事項,
    collect(DISTINCT {action: ng.action, reason: ng.reason, riskLevel: ng.riskLevel}) AS 禁忌事項,
    collect(DISTINCT {type: cert.type, grade: cert.grade, nextRenewalDate: cert.nextRenewalDate}) AS 手帳_受給者証,
    collect(DISTINCT {type: pa.type, grade: pa.grade}) AS 公的扶助,
    collect(DISTINCT {rank: kpRel.rank, name: kp.name, relationship: kp.relationship, phone: kp.phone, role: kp.role}) AS キーパーソン,
    collect(DISTINCT {name: g.name, type: g.type, phone: g.phone}) AS 後見人等,
    collect(DISTINCT {name: s.name, role: s.role, organization: s.organization}) AS 支援者,
    collect(DISTINCT {name: hosp.name, specialty: hosp.specialty, phone: hosp.phone}) AS 医療機関
```

**パラメータ**: `$clientName`

**出力加工**:
- 各collectの結果から、主要フィールドが`null`のエントリを除外する
- 生年月日から年齢を計算して併記
- キーパーソンは`rank`昇順でソート
- 4本柱の構造に沿って整形表示:

```
【基本情報】氏名 / 生年月日（年齢）/ 血液型
【第1の柱：本人性】生育歴、願い
【第2の柱：ケアの暗黙知】特性・診断、配慮事項、🚫禁忌事項
【第3の柱：法的基盤】手帳・受給者証、公的扶助
【第4の柱：危機管理ネットワーク】キーパーソン、後見人等、支援者、医療機関
```

---

### 3. データベース統計情報

各ノードタイプの登録数を確認する。1つのクエリで一括取得。

```cypher
MATCH (n)
WHERE n:Client OR n:NgAction OR n:CarePreference OR n:Condition
   OR n:KeyPerson OR n:Certificate OR n:Guardian OR n:LifeHistory
   OR n:Wish OR n:Hospital OR n:Supporter OR n:SupportLog
WITH labels(n)[0] AS label
RETURN label AS ノード種別, count(*) AS 登録数
ORDER BY 登録数 DESC
```

---

### 4. 手帳・受給者証の更新期限チェック

```cypher
MATCH (c:Client)-[:HAS_CERTIFICATE]->(cert:Certificate)
WHERE cert.nextRenewalDate IS NOT NULL
  AND ($clientName = '' OR c.name CONTAINS $clientName)
WITH c, cert,
     duration.inDays(date(), cert.nextRenewalDate).days AS daysUntilRenewal
WHERE daysUntilRenewal <= $days AND daysUntilRenewal >= 0
RETURN
    c.name AS クライアント,
    cert.type AS 証明書種類,
    cert.grade AS 等級,
    cert.nextRenewalDate AS 更新期限,
    daysUntilRenewal AS 残り日数
ORDER BY daysUntilRenewal ASC
```

**パラメータ**: `$clientName`（空文字で全員）, `$days`（デフォルト90）

**出力加工**: 残り日数で緊急度をグループ化:
- 🔴 緊急: 30日以内
- 🟡 注意: 31-60日
- 🟢 確認: 61日以上

---

### 5. 支援記録の取得

```cypher
MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c:Client)
WHERE c.name CONTAINS $clientName
RETURN log.date AS 日付,
       s.name AS 支援者,
       log.situation AS 状況,
       log.action AS 対応,
       log.effectiveness AS 効果,
       log.note AS メモ
ORDER BY log.date DESC
LIMIT $limit
```

**パラメータ**: `$clientName`, `$limit`（デフォルト10、最大50）

---

### 6. 効果的ケアパターンの発見

複数回効果があった対応方法を自動検出する。

```cypher
MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c:Client)
WHERE c.name CONTAINS $clientName
  AND (toLower(toString(log.effectiveness)) STARTS WITH 'effective'
       OR toLower(toString(log.effectiveness)) STARTS WITH 'excellent'
       OR toString(log.effectiveness) CONTAINS '効果')
WITH log.action AS 対応方法, count(*) AS 回数,
    collect(DISTINCT log.situation) AS 状況一覧
WHERE 回数 >= $minFrequency
RETURN 対応方法, 回数, 状況一覧
ORDER BY 回数 DESC
```

**パラメータ**: `$clientName`, `$minFrequency`（デフォルト2）

---

### 7. 監査ログ取得

```cypher
MATCH (al:AuditLog)
WHERE ($clientName = '' OR al.clientName CONTAINS $clientName)
  AND ($userName = '' OR al.user CONTAINS $userName)
RETURN al.timestamp AS 日時,
       al.user AS 操作者,
       al.action AS 操作,
       al.targetType AS 対象種別,
       al.targetName AS 対象名,
       al.details AS 詳細,
       al.clientName AS クライアント
ORDER BY al.timestamp DESC
LIMIT $limit
```

**パラメータ**: `$clientName`（空文字OK）, `$userName`（空文字OK）, `$limit`（デフォルト30、最大100）

---

### 8. クライアント変更履歴

特定クライアントに絞った監査ログ。

```cypher
MATCH (al:AuditLog)
WHERE al.clientName CONTAINS $clientName
RETURN al.timestamp AS 日時,
       al.user AS 操作者,
       al.action AS 操作,
       al.targetType AS 対象種別,
       al.targetName AS 内容,
       al.details AS 詳細
ORDER BY al.timestamp DESC
LIMIT $limit
```

**パラメータ**: `$clientName`, `$limit`（デフォルト20）

---

## データ登録パターン（書き込みクエリ）

データの登録・更新には `neo4j:write_neo4j_cypher` を使用する。

### 支援記録の登録

#### ★重要: AI構造化プロセス

旧システムでは Gemini API で支援記録テキストを構造化していたが、スキルベースの新システムでは **Claude自身がテキストを構造化** してからCypherで登録する。

**構造化の手順**:
1. ユーザーから物語風テキストを受け取る
2. 以下の情報を抽出する:
   - `situation`: 何が起きたか（状況）
   - `action`: どう対応したか（対応）
   - `effectiveness`: 効果があったか（`Effective` / `Ineffective` / `Neutral`）
   - `note`: その他のメモ
   - 支援者名（判別できる場合）
3. 追加で抽出可能なら:
   - 新たな禁忌事項（NgAction）
   - 新たな推奨ケア（CarePreference）

**例**: 「今日、急な音に驚いてパニックになりました。テレビを消して静かにしたら5分で落ち着きました。」
→ situation: "急な音に驚いてパニック"
→ action: "テレビを消して静かにした"
→ effectiveness: "Effective"
→ note: "5分で落ち着いた"

#### 支援記録の書き込みCypher

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $clientName
MERGE (s:Supporter {name: $supporterName})
CREATE (log:SupportLog {
    date: date($date),
    situation: $situation,
    action: $action,
    effectiveness: $effectiveness,
    note: $note
})
MERGE (s)-[:LOGGED]->(log)
MERGE (log)-[:ABOUT]->(c)
RETURN log.date AS 日付, log.situation AS 状況
```

**パラメータ**:
- `$clientName`: クライアント名
- `$supporterName`: 支援者名（不明の場合は "不明"）
- `$date`: 日付（YYYY-MM-DD形式、不明なら今日の日付）
- `$situation`, `$action`, `$effectiveness`, `$note`

#### 禁忌事項（NgAction）の追加登録

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $clientName
MERGE (ng:NgAction {
    action: $action,
    reason: $reason,
    riskLevel: $riskLevel
})
MERGE (c)-[:MUST_AVOID]->(ng)
RETURN ng.action AS 禁忌事項, ng.riskLevel AS リスクレベル
```

**パラメータ**: `$clientName`, `$action`, `$reason`, `$riskLevel` (LifeThreatening / Panic / Discomfort)

#### 推奨ケア（CarePreference）の追加登録

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $clientName
MERGE (cp:CarePreference {
    category: $category,
    instruction: $instruction,
    priority: $priority
})
MERGE (c)-[:REQUIRES]->(cp)
RETURN cp.category AS カテゴリ, cp.instruction AS 手順
```

**パラメータ**: `$clientName`, `$category`, `$instruction`, `$priority` (High / Medium / Low)

#### キーパーソンの登録

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $clientName
MERGE (kp:KeyPerson {
    name: $name,
    relationship: $relationship,
    phone: $phone,
    role: $role
})
MERGE (c)-[:HAS_KEY_PERSON {rank: $rank}]->(kp)
RETURN kp.name AS 名前, kp.relationship AS 続柄
```

**パラメータ**: `$clientName`, `$name`, `$relationship`, `$phone`, `$role`, `$rank`（優先順位番号）

#### 手帳・受給者証の登録

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $clientName
MERGE (cert:Certificate {
    type: $type,
    grade: $grade,
    nextRenewalDate: date($nextRenewalDate)
})
MERGE (c)-[:HAS_CERTIFICATE]->(cert)
RETURN cert.type AS 種類, cert.grade AS 等級, cert.nextRenewalDate AS 更新日
```

#### 監査ログの記録

データ変更時には必ず監査ログを残す。

```cypher
CREATE (al:AuditLog {
    timestamp: datetime(),
    user: $user,
    action: $action,
    targetType: $targetType,
    targetName: $targetName,
    details: $details,
    clientName: $clientName
})
RETURN al.timestamp AS 記録日時
```

**パラメータ**: `$user`（操作者名）, `$action`（例: "CREATE", "UPDATE"）, `$targetType`（例: "SupportLog", "NgAction"）, `$targetName`（内容の要約）, `$details`（詳細）, `$clientName`

---

## レポート生成

PDFやExcelのレポート生成が必要な場合は、以下の別スキルを使用する:

| 出力形式 | 使用スキル | 内容 |
|----------|-----------|------|
| PDF | `pdf` スキル | 緊急時情報シート（A4 1枚） |
| Excel | `xlsx` スキル | 詳細データシート（全データ） |

**手順**: まずこのスキルのテンプレート2（プロフィール一括取得）でデータを取得し、PDFまたはExcelスキルに渡して整形する。

---

## AI運用プロトコル

### ルール1: 緊急時は emergency-protocol を優先

「パニック」「事故」「急病」「緊急」などのワードを検知したら、このスキルではなく **`emergency-protocol` スキル**を即座に起動すること。

### ルール2: 年齢の自動計算

生年月日（dob）が取得できた場合、必ず現在の年齢を計算して併記する。
例: `1995-03-15` → `1995-03-15（30歳）`

### ルール3: 禁忌事項の最優先表示

クライアント情報を表示する際、NgAction（禁忌事項）が存在する場合は **最初に強調表示** すること。

### ルール4: 支援記録の構造化ルール

ユーザーから支援記録テキストを受け取った場合:
1. テキストから situation / action / effectiveness / note を抽出
2. 効果の判定:
   - 「落ち着いた」「効果的」「うまくいった」→ `Effective`
   - 「逆効果」「悪化」「失敗」→ `Ineffective`
   - 判断できない場合 → `Neutral`
3. 追加で禁忌事項や推奨ケアが抽出できれば同時に登録
4. 登録後に監査ログを記録

### ルール5: 書き込み時は確認を求める

データの新規登録や更新を行う前に、登録内容をユーザーに確認すること。特に:
- 禁忌事項（NgAction）の新規登録
- キーパーソンの変更
- 手帳・受給者証の更新日変更

### ルール6: パラメータ化クエリの徹底

すべてのクエリで `$param` 形式のパラメータを使用すること。文字列連結によるCypher構築は**禁止**（インジェクション対策）。

---

## 典型的なユースケース

### ケース1: 新規支援計画作成

```
ユーザー: 「山田健太さんの情報を全部見せて」

手順:
1. テンプレート2（プロフィール一括）を実行
   → $clientName = "山田健太"
2. 4本柱の構造に沿って整形表示
3. 不足情報（更新期限切れの手帳、未登録のキーパーソン等）を指摘
```

### ケース2: 支援記録の追加

```
ユーザー: 「山田健太さんの記録: 今日パニックになったけど、イヤーマフをつけたら5分で落ち着いた」

手順:
1. テキストを構造化:
   - situation: "パニック発生"
   - action: "イヤーマフを装着"
   - effectiveness: "Effective"
   - note: "5分で落ち着いた"
2. 登録内容を確認提示
3. 承認後、支援記録の書き込みCypherを実行
4. 監査ログを記録
```

### ケース3: 効果的ケアの振り返り

```
ユーザー: 「山田健太さんに効果的だった対応を教えて」

手順:
1. テンプレート6（ケアパターン発見）を実行
   → $clientName = "山田健太", $minFrequency = 2
2. パターンがない場合はテンプレート5（支援記録取得）で最新記録を表示
3. 効果的だった対応と逆効果だった対応を分類して提示
```

### ケース4: 更新期限の管理

```
ユーザー: 「来月更新期限を迎える手帳は？」

手順:
1. テンプレート4（更新期限チェック）を実行
   → $clientName = "", $days = 30
2. 緊急度別にグループ化して表示
3. 更新手続きの流れを補足
```

### ケース5: クライアントが見つからない場合

```
クエリ結果が空の場合:
1. テンプレート1（クライアント一覧）を実行して候補を提示
2. 「もしかして: 〇〇さん？」と表示
```

---

## 関連スキルとの連携

| スキル | 連携タイミング |
|--------|---------------|
| `emergency-protocol` | 緊急ワード検知時に即座に切り替え |
| `livelihood-support` | 経済的リスク・金銭管理の確認（生活保護受給者の場合） |
| `ecomap-generator` | 支援ネットワーク図の生成 |
| `provider-search` | 事業所検索・利用状況の確認 |
| `pdf` / `xlsx` | レポート出力時 |

---

## セキュリティとプライバシー

### 取り扱い注意情報
- 禁忌事項（NgAction）- 悪用されると危険
- キーパーソンの連絡先
- 医療情報
- 後見人情報

### アクセス制御
- 本人・家族からの要望があれば、データの修正・削除に応じる
- 変更時は必ず監査ログを残す

---

## 権利擁護の視点

このデータベースは単なる情報管理ツールではなく、**クライアントの権利擁護**のためのツールです。

### 基本原則
1. **尊厳**: クライアントを管理対象ではなく、歴史と意思を持つ一人の人間として記録
2. **安全**: 緊急時に迷わせない構造を作る
3. **継続性**: 支援者が入れ替わってもケアの質を維持
4. **権利擁護**: 本人の声なき声を拾い上げ、法的な後ろ盾と紐づける

---

## バージョン

- v2.0.0 (2026-02-12) - neo4j MCPツールベースに移行、Cypherテンプレート集追加
- v1.0.0 - support-db カスタムMCPツールベース（旧版）
