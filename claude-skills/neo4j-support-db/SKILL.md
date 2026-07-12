---
name: neo4j-support-db
description: 知的障害・精神障害のある方（クライアント）の支援情報を包括的に管理するNeo4jグラフデータベース（port 7687）。禁忌事項・推奨ケア・キーパーソン・手帳/受給者証・かかりつけ医・支援記録などを照会・登録する。特定のクライアント名が話題に出たとき、「〇〇さんの情報」「禁忌事項」「ケア方法」「支援記録」「手帳の更新」「クライアントを照会」「障害福祉の利用者」などの発言時に必ずこのスキルを使用すること。汎用neo4j MCPツール（execute_query）でCypherを実行する。
---

# Neo4j親なき後支援データベース スキル

> **正本参照ルール（2026-07-12 追記・検収指摘対応）**: 業務的意味・運用原則・
> 指標の解釈は、まず `docs/SEMANTIC_MODEL.md` を読むこと（プロジェクト内は
> 同期コピー。正は `~/Dev-Work/shared-schema/SEMANTIC_MODEL.md`）。
> リレーション名・列挙値・命名は `docs/SCHEMA_CONVENTION.md` が正。
> 本スキルは Cypher テンプレートの索引に徹し、意味・閾値の定義を二重化しない。

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
| `neo4j:execute_query` | すべての読み取り・登録・更新（読み書き兼用。`query` に Cypher、任意で `params`） |
| `neo4j:create_node` / `neo4j:create_relationship` | 単純なノード/リレーション作成（任意。通常は execute_query で足りる） |

> スキーマ確認が必要なときは `execute_query` で `CALL db.schema.visualization()` 等を実行する（専用のスキーマ取得ツールは無い）。

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
| `:SupportLog` | 支援記録 | date, situation, action, effectiveness, note, type, duration, nextAction |
| `:AuditLog` | 監査ログ | timestamp, user, action, targetType, targetName, details, clientName |

### 主要リレーション

| リレーション | 方向 | プロパティ |
|-------------|------|-----------
| `MUST_AVOID` | Client → NgAction | — |
| `REQUIRES` | Client → CarePreference | — |
| `HAS_CONDITION` | Client → Condition | diagnosedDate |
| `HAS_KEY_PERSON` | Client → KeyPerson | rank（優先順位） |
| `HAS_LEGAL_REP` | Client → Guardian | — |
| `HAS_CERTIFICATE` | Client → Certificate | issuedDate, status |
| `RECEIVES` | Client → PublicAssistance | — |
| `HAS_HISTORY` | Client → LifeHistory | — |
| `HAS_WISH` | Client → Wish | — |
| `TREATED_AT` | Client → Hospital | since, status |
| `SUPPORTED_BY` | Client → Supporter | since, until |
| `LOGGED` | Supporter → SupportLog | — |
| `ABOUT` | SupportLog → Client | — |
| `FOLLOWS` | SupportLog → SupportLog | — (時系列チェーン) |
| `AUDIT_FOR` | AuditLog → Client | — |
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
OPTIONAL MATCH (c)-[:HAS_KEY_PERSON|EMERGENCY_CONTACT]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE|HOLDS]->(cert:Certificate)
OPTIONAL MATCH (c)-[:HAS_LEGAL_REP|HAS_GUARDIAN]->(g:Guardian)
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
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE|HOLDS]->(cert:Certificate)
OPTIONAL MATCH (c)-[:RECEIVES]->(pa:PublicAssistance)

// 第4の柱：危機管理ネットワーク
OPTIONAL MATCH (c)-[kpRel:HAS_KEY_PERSON|EMERGENCY_CONTACT]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:HAS_LEGAL_REP|HAS_GUARDIAN]->(g:Guardian)
OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(s:Supporter)
OPTIONAL MATCH (c)-[:TREATED_AT]->(hosp:Hospital)

// 確認記録（Review）—— 0件の意味を判定するために必須
OPTIONAL MATCH (rv:Review)-[:ABOUT]->(c)

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
    collect(DISTINCT {name: hosp.name, specialty: hosp.specialty, phone: hosp.phone}) AS 医療機関,
    collect(DISTINCT {domain: rv.domain, reviewedAt: rv.reviewedAt, source: rv.source}) AS 確認記録
```

**パラメータ**: `$clientName`

**出力加工**:
- 各collectの結果から、主要フィールドが`null`のエントリを除外する
- 生年月日から年齢を計算して併記
- キーパーソンは`rank`昇順でソート
- **0件の項目は、確認記録と照らしてルール8（BRS-12）のとおり表示する**。
  禁忌・キーパーソン等が0件で Review も無ければ、「なし」ではなく「未確認」と書く
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
MATCH (c:Client)-[:HAS_CERTIFICATE|HOLDS]->(cert:Certificate)
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
       OR toString(log.effectiveness) CONTAINS '効果')
WITH log.action AS 対応方法, count(*) AS 回数,
    collect(DISTINCT log.situation) AS 状況一覧
WHERE 回数 >= $minFrequency
RETURN 対応方法, 回数, 状況一覧
ORDER BY 回数 DESC
```

**パラメータ**: `$clientName`, `$minFrequency`（デフォルト2）

> 訂正（2026-07-12）: 旧クエリは `STARTS WITH 'excellent'` も判定に含めていたが、
> `effectiveness` の正式な値域（SEMANTIC_MODEL ENU-02: Effective / Ineffective /
> Neutral / Unknown）に `Excellent` は存在しないため削除した（DRIFT-03）。

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

データの登録・更新には `neo4j:execute_query` を使用する（読み取りと同じツール。書き込み Cypher を `query` に渡す）。

> **書き込み時のクライアント照合は完全一致 `{name: $clientName}` を使うこと。**
> 部分一致（`CONTAINS`）は複数クライアントにヒットした場合、全員にデータが付与される事故につながる。
> 書き込み前にテンプレート1または2で正確な氏名を確定してから実行する。

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
MATCH (c:Client {name: $clientName})
MERGE (s:Supporter {name: $supporterName})
CREATE (log:SupportLog {
    date: date($date),
    situation: $situation,
    action: $action,
    effectiveness: $effectiveness,
    note: $note,
    type: $type,
    duration: $duration,
    nextAction: $nextAction
})
MERGE (s)-[:LOGGED]->(log)
MERGE (log)-[:ABOUT]->(c)

// 直前の支援記録との時系列チェーンを構築
WITH log, c
OPTIONAL MATCH (prevLog:SupportLog)-[:ABOUT]->(c)
WHERE prevLog <> log AND prevLog.date <= log.date
WITH log, prevLog ORDER BY prevLog.date DESC LIMIT 1
FOREACH (_ IN CASE WHEN prevLog IS NOT NULL THEN [1] ELSE [] END |
    CREATE (log)-[:FOLLOWS]->(prevLog)
)

RETURN log.date AS 日付, log.situation AS 状況
```

**パラメータ**:
- `$clientName`: クライアント名
- `$supporterName`: 支援者名（不明の場合は "不明"）
- `$date`: 日付（YYYY-MM-DD形式、不明なら今日の日付）
- `$situation`, `$action`, `$effectiveness`, `$note`
- `$type`: 記録種別（日常記録 / インシデント / 会議 / 引き継ぎ、デフォルト: 日常記録）
- `$duration`: 対応にかかった時間（例: "30分"、任意）
- `$nextAction`: 次回のアクション（任意）

#### 禁忌事項（NgAction）の追加登録

クライアント配下のノードとしてリレーションごと MERGE する（再実行で重複せず、他クライアントとノードを共有しない）。

```cypher
MATCH (c:Client {name: $clientName})
MERGE (c)-[:MUST_AVOID]->(ng:NgAction {action: $action})
ON CREATE SET ng.reason = $reason, ng.riskLevel = $riskLevel
ON MATCH SET  ng.reason = COALESCE($reason, ng.reason),
              ng.riskLevel = COALESCE($riskLevel, ng.riskLevel)
RETURN ng.action AS 禁忌事項, ng.riskLevel AS リスクレベル
```

**パラメータ**: `$clientName`（完全一致）, `$action`, `$reason`, `$riskLevel` (LifeThreatening / Panic / Discomfort)

#### 推奨ケア（CarePreference）の追加登録

```cypher
MATCH (c:Client {name: $clientName})
MERGE (c)-[:REQUIRES]->(cp:CarePreference {category: $category, instruction: $instruction})
ON CREATE SET cp.priority = $priority
ON MATCH SET  cp.priority = COALESCE($priority, cp.priority)
RETURN cp.category AS カテゴリ, cp.instruction AS 手順
```

**パラメータ**: `$clientName`（完全一致）, `$category`, `$instruction`, `$priority` (High / Medium / Low)

#### キーパーソンの登録

```cypher
MATCH (c:Client {name: $clientName})
MERGE (c)-[r:HAS_KEY_PERSON]->(kp:KeyPerson {name: $name})
SET kp.relationship = COALESCE($relationship, kp.relationship),
    kp.phone = COALESCE($phone, kp.phone),
    kp.role = COALESCE($role, kp.role),
    r.rank = COALESCE($rank, r.rank)
RETURN kp.name AS 名前, kp.relationship AS 続柄
```

**パラメータ**: `$clientName`（完全一致）, `$name`, `$relationship`, `$phone`, `$role`, `$rank`（優先順位番号）

#### 手帳・受給者証の登録

手帳種別（type）×等級（grade）ごとに1ノード（SCHEMA_CONVENTION §10.3 の複合キー。
等級未指定は「不明」）。等級が変わった場合は別ノードになる（療育手帳AとBは別ノード）。
発行日・状態はスキーマ規約どおりリレーション側（`HAS_CERTIFICATE {issuedDate, status}`）に持つ。

```cypher
MATCH (c:Client {name: $clientName})
MERGE (c)-[r:HAS_CERTIFICATE]->(cert:Certificate {type: $type, grade: COALESCE($grade, '不明')})
SET cert.nextRenewalDate = CASE WHEN $nextRenewalDate IS NOT NULL
                                THEN date($nextRenewalDate) ELSE cert.nextRenewalDate END,
    r.issuedDate = CASE WHEN $issuedDate IS NOT NULL
                        THEN date($issuedDate) ELSE r.issuedDate END,
    r.status = COALESCE($status, r.status, 'Active')
RETURN cert.type AS 種類, cert.grade AS 等級, cert.nextRenewalDate AS 更新日
```

**パラメータ**: `$clientName`（完全一致）, `$type`, `$grade`（未指定は '不明'）, `$nextRenewalDate`, `$issuedDate`（任意・nullで省略可）, `$status`（任意・nullで省略可）

> 訂正（2026-07-12）: 旧テンプレートは `{type}` のみを MERGE キーとし等級を SET で
> 上書きしていたが、SCHEMA_CONVENTION §10.3 の複合キー `["type","grade"]`（等級違いは
> 別ノード）に合わせて修正した（DRIFT-08）。等級未設定の既存ノードは grade='不明' の
> 新ノードとマッチしないため、更新時は既存データの等級を先に確認すること。

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
WITH al
OPTIONAL MATCH (c:Client {name: $clientName})
WHERE $clientName <> ''
FOREACH (_ IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
    CREATE (al)-[:AUDIT_FOR]->(c)
)
RETURN al.timestamp AS 記録日時
```

**パラメータ**: `$user`（操作者名）, `$action`（例: "CREATE", "UPDATE"）, `$targetType`（例: "SupportLog", "NgAction"）, `$targetName`（内容の要約）, `$details`（詳細）, `$clientName`

#### 確認記録（Review）の登録

**「確認したが、何も無かった」を記録できる唯一の手段。**
支援者が「母親に聞いたが禁忌は無いとのことだった」と言ったら、必ずこれを登録する。
登録しなければ、その確認は**行われなかったのと同じ扱い**になる（次の支援者には伝わらない）。

**追記のみ。既存の Review を更新・削除してはならない**（確認の履歴を積み上げる）。

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
- `$clientName`（**完全一致**。BRS-08）
- `$supporterName`: 確認を行った支援者
- `$domain`: `NgAction` / `CarePreference` / `KeyPerson` / `Guardian` / `Certificate` / `CareRole`
  （SCHEMA_CONVENTION §7.7。他の値は使わない）
- `$reviewedAt`: 確認日（YYYY-MM-DD）
- `$source`: **誰に確認したか**。`本人` / `母親` / `父親` / `家族・親族` / `主治医` /
  `前事業所` / `相談支援専門員` / `後見人等` / `記録のみ`（§7.8）
- `$note`: 補足（任意）

> **`$source` を推測で埋めないこと。** 誰に確認したかが不明なら、支援者に聞く。
> 「母親に確認して禁忌なし」と「本人にしか聞けていない」は、同じ「0件」でも
> 重みが全く違う（ENU-17）。

登録後は監査ログを残す（`$targetType` = "Review"）。

---

### 9. 支援記録の全文検索

キーワードで支援記録を横断検索する。全文検索インデックス `idx_supportlog_fulltext` を使用。

```cypher
CALL db.index.fulltext.queryNodes('idx_supportlog_fulltext', $keyword)
YIELD node, score
MATCH (s:Supporter)-[:LOGGED]->(node)-[:ABOUT]->(c:Client)
WHERE $clientName = '' OR c.name CONTAINS $clientName
RETURN node.date AS 日付,
       s.name AS 支援者,
       c.name AS クライアント,
       node.situation AS 状況,
       node.action AS 対応,
       node.effectiveness AS 効果,
       score AS スコア
ORDER BY score DESC
LIMIT $limit
```

**パラメータ**: `$keyword`（検索語）, `$clientName`（空文字で全員）, `$limit`（デフォルト20）

**注意**: Neo4jの全文検索はデフォルトで英語アナライザーを使用するため、日本語の形態素解析には制限があります。単語単位の検索（例: "パニック"）には有効ですが、複合語の場合は `CONTAINS` との併用を推奨します。

---

### 10. 支援記録のタイムラインチェーン追跡

FOLLOWS リレーションで支援記録の時系列を辿り、ケアの変遷を追跡する。

```cypher
MATCH (log:SupportLog)-[:ABOUT]->(c:Client)
WHERE c.name CONTAINS $clientName
OPTIONAL MATCH path = (log)-[:FOLLOWS*0..10]->(older:SupportLog)
WITH c, log, older, length(path) AS depth
ORDER BY log.date DESC, depth ASC
RETURN log.date AS 日付,
       log.situation AS 状況,
       log.action AS 対応,
       log.effectiveness AS 効果,
       log.type AS 種別,
       depth AS チェーン深度
LIMIT $limit
```

**パラメータ**: `$clientName`, `$limit`（デフォルト30）

---

### 11. 確認状況（Review）の取得と未確認の検出

**0件が「確認したうえで無い」のか「まだ聞いていない」のかを判定する。**
6領域（NgAction / CarePreference / KeyPerson / Guardian / Certificate / CareRole）について、
登録件数と最新の確認記録を並べて返す。

```cypher
MATCH (c:Client)
WHERE ($clientName = '' OR c.name CONTAINS $clientName)

// 領域ごとの登録件数（旧リレーション名にもマッチ。BRS-07）
OPTIONAL MATCH (c)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)
OPTIONAL MATCH (c)-[:REQUIRES|PREFERS]->(cp:CarePreference)
OPTIONAL MATCH (c)-[:HAS_KEY_PERSON|EMERGENCY_CONTACT]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:HAS_LEGAL_REP|HAS_GUARDIAN]->(g:Guardian)
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE|HOLDS]->(cert:Certificate)
OPTIONAL MATCH (rel:Relative)-[:IS_PARENT_OF|FAMILY_OF]->(c)
OPTIONAL MATCH (rel)-[:PERFORMS]->(cr:CareRole)
WITH c,
     count(DISTINCT ng)   AS nNg,   count(DISTINCT cp) AS nCp,
     count(DISTINCT kp)   AS nKp,   count(DISTINCT g)  AS nG,
     count(DISTINCT cert) AS nCert, count(DISTINCT cr) AS nCr

// 6領域を行に展開
UNWIND [
  {domain:'NgAction',       cnt:nNg},   {domain:'CarePreference', cnt:nCp},
  {domain:'KeyPerson',      cnt:nKp},   {domain:'Guardian',       cnt:nG},
  {domain:'Certificate',    cnt:nCert}, {domain:'CareRole',       cnt:nCr}
] AS d

// 当該領域の最新の確認記録
OPTIONAL MATCH (rv:Review {domain: d.domain})-[:ABOUT]->(c)
WITH c, d, rv ORDER BY rv.reviewedAt DESC
WITH c, d, head(collect(rv)) AS latest

RETURN
    c.name            AS クライアント,
    d.domain          AS 領域,
    d.cnt             AS 登録件数,
    latest.reviewedAt AS 確認日,
    latest.source     AS 情報源,
    CASE
      WHEN d.cnt > 0        THEN '登録あり'
      WHEN latest IS NULL   THEN '🚨 未確認'
      ELSE '✅ 確認済み（0件）'
    END               AS 状態
ORDER BY クライアント,
    CASE d.domain WHEN 'NgAction' THEN 1 WHEN 'KeyPerson' THEN 2 ELSE 3 END
```

> **検証済み**（2026-07-12、nest-support-neo4j にて構文確認）。
> なお、`CALL (c, domain) { ... }` 形式のスコープ付きサブクエリはこの Neo4j では
> **構文エラーになる**（バージョンが 5.23 未満）。使わないこと。

**パラメータ**: `$clientName`（空文字で全員）

**出力加工**:
- `🚨 未確認` を最上位に表示する。とりわけ **NgAction の未確認は最優先の欠損**
- `✅ 確認済み（0件）` は必ず**情報源と確認日を併記**する
  （例:「✅ 確認済み（0件）— 2026-03-10、母親に確認」）
- `記録のみ` が情報源の場合は、弱い確認である旨を添える

> クエリが重い場合は、禁忌のみに絞った簡易版でもよい:
> ```cypher
> MATCH (c:Client) WHERE c.name CONTAINS $clientName
> OPTIONAL MATCH (c)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)
> OPTIONAL MATCH (rv:Review {domain:'NgAction'})-[:ABOUT]->(c)
> RETURN c.name AS クライアント, count(DISTINCT ng) AS 禁忌件数,
>        max(rv.reviewedAt) AS 最終確認日, collect(DISTINCT rv.source) AS 情報源
> ```

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
**0件の場合の扱いはルール8に従う（「なし」と書いてはならない）。**

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

### ルール7: 個人紐づけデータをセマンティック検索に載せない ★standing rule の例外★

**グローバル standing rule「DBアクセスはまず graphrag-hybrid（LightRAG）で検索する」は、
このDBには適用しない。support-db の照会は常に Cypher（`neo4j:execute_query`）で行う。**

これは utility による例外ではなく、**設計上の禁則**である。

#### 禁止すること

- クライアント個人に紐づくデータ（`NgAction` / `CarePreference` / `Condition` /
  `SupportLog` / `KeyPerson` / `Guardian` / `Hospital` / `Certificate` / `LifeHistory` / `Wish`）を
  **support-db の外にある別ストア（LightRAG / graphrag-hybrid 等）に複製・投入すること**
- 上記データの照会手段として、Cypher の代わりにセマンティック検索を用いること
- 「まずgraphrag-hybridで検索」の standing rule を根拠に、上記を実行すること

#### 適用外（このルールは禁じていない）

support-db **内部**のベクトルインデックス（`ng_action_embedding` 等6本。
SCHEMA_CONVENTION §8.3）は既存の正規機能であり、本ルールの対象外。
その**用途制限は SEMANTIC_MODEL BRS-03 が管轄する**（発見の補助・重複検出に限定。
禁忌の確認は常に構造側が正）。本ルールが禁じるのは**別ストアへの複製**であって、
内部 embedding の使用ではない。

#### 理由（2つとも独立に致命的）

1. **再現率（recall）**：禁忌事項は「取りこぼしが静かに起きる」ことが許されない否定的制約。
   セマンティック検索は近い意味のものを上位に返す仕組みであり、5件中4件しか返らなくても
   出力は自然に見えてしまう。欠けた1件が現場の事故に直結する。
   Cypher なら「そのクライアントに紐づく全件」が決定的に返る（BRS-03）。
2. **PIIの拡散**：別ストアへの複製は、個人情報の実体を増やし、管理と削除の範囲を
   広げる。現在の LightRAG 構成は LLM 側が Anthropic API バインディング（Haiku 4.5）のため、
   インデックス構築時に実データが外部APIに出る経路も増える。

#### 代替（「意味で探したい」場合）

- **Cypher で全件取得 → 取得済みの小さな集合の上で意味的に絞り込む。**
  例：「入浴介助の場面に関係する禁忌は？」→ MUST_AVOID を全件取得したうえで解釈する。
  網羅性を Cypher で担保し、解釈だけを柔らかくやる。
- LightRAG に載せてよいのは **個人非紐づけの一般ケア知識**（対応技法・行動障害の一般論・
  制度解説など）に限る。氏名・生年月日・事業所名等が結び付いた形では載せない。

#### 判断が必要になったら

「一般知識か、個人紐づけか」が曖昧なケースは、**LightRAG に載せない側に倒し、河原さんに確認する**。

> 確定日: 2026-07-12（河原さんとの検討により、standing rule の明示的例外として固定）
> 関連: `pii-safe-data-handling` スキル / SEMANTIC_MODEL BRS-03

### ルール8: 0件を「なし」と言わない（BRS-12） ★最重要★

**禁忌0件には二つの意味がある——「確認したうえで無い」と「まだ聞き取れていない」。
前者は安心してよく、後者は事故と隣り合わせである。リレーションの不在だけではこの二つは区別できない。**

判定には **Review（確認記録）** を使う。対象は0件が安全・権利に直結する6領域
（NgAction / CarePreference / KeyPerson / Guardian / Certificate / CareRole）。

| 状態 | 表示 |
|---|---|
| 件数 > 0 | 通常どおり内容を提示 |
| 件数 0・当該 domain の Review **なし** | **「🚨 未確認」と表示する** |
| 件数 0・当該 domain の Review **あり** | 「✅ 確認済み（0件）— 2026-03-10、母親に確認」のように**情報源と確認日を併記** |

**禁止表現**（Review が無い0件に対して）:
「禁忌なし」「特にありません」「該当なし」「登録されていません（だから安全）」

→ これらは **No Fabrication 違反**であり、**未聴取を確認済みと偽ることに等しい**。
支援者はこれを読んで「大丈夫なのだな」と判断する。その判断が事故につながる。

**確認状況の取得はテンプレート11**。未確認を見つけたら、河原さんに「未確認です。
誰に確認しますか」と能動的に提起すること。確認できたら**テンプレート「Review の登録」で必ず記録**する
（記録しなければ、その確認は次の支援者に伝わらない）。

> 確定日: 2026-07-12（河原氏決定）
> 根拠: SEMANTIC_MODEL BRS-12 / BRS-04 / ENT-24 / ENU-16-17
> 陳腐化判定（確認が古いことの警告）は**今回は実装しない**（スコープ外）

---

## 典型的なユースケース

具体的な操作手順の例（新規支援計画作成・支援記録追加・効果的ケア振り返り・更新期限管理・
クライアント未発見時）は付録に分離した。必要なときに参照すること:
**[reference/use-cases.md](reference/use-cases.md)**

---

## 関連スキルとの連携

| スキル | 連携タイミング |
|--------|---------------|
| `emergency-protocol` | 緊急ワード検知時に即座に切り替え |
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

### 外部ストアへの複製禁止

上記の取り扱い注意情報を含む**個人紐づけデータは、support-db の外にある別ストア
（LightRAG / graphrag-hybrid 等）に複製・投入してはならない**（→ AI運用プロトコル ルール7）。
support-db が個人情報の唯一のストアである状態を維持する。
support-db 内部のベクトルインデックスは対象外（用途制限は BRS-03）。

### アクセス制御
- 本人・家族からの要望があれば、データの修正・削除に応じる
- 変更時は必ず監査ログを残す

---

## 権利擁護の視点

このデータベースは単なる情報管理ツールではなく、**クライアントの権利擁護**のための
ツールである（尊厳・安全・継続性・権利擁護の基本原則）。詳細は
**[reference/use-cases.md](reference/use-cases.md)** を参照。

---

## バージョン

- v3.0.0 (2026-03-09) - テンプレート9・10追加、FOLLOWS/AUDIT_FORリレーション、リレーションプロパティ拡張
- v2.0.0 (2026-02-12) - neo4j MCPツールベースに移行、Cypherテンプレート集追加
- v1.0.0 - support-db カスタムMCPツールベース（旧版）
