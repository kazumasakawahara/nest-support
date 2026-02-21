# narrative-extractor: テキストから構造化データを抽出するスキル

## 概要

母親・支援者の語り（ナラティブ）やファイルから、支援に必要な構造化データをJSON形式で抽出し、Neo4jデータベースに登録するためのスキル。

Gemini ai_extractor.py の機能をClaude Skill として実現する。

## トリガーワード

- 「テキストから抽出」「情報を抽出して」「ナラティブから登録」
- 「この文章を構造化して」「データベースに登録して」
- 「面談記録を入力」「聞き取り内容を登録」
- ファイル添付時（.docx, .xlsx, .pdf, .txt）

## 使用方法

### Step 1: テキストの提供

ユーザーがテキストを直接入力するか、ファイルを添付する。

### Step 2: 構造化データの抽出

以下のルールに従って、テキストからJSON形式のデータを抽出する。

#### 抽出ルール（厳守）

1. **絶対に入力テキストにない情報を創作・推測しない**
   - テキストに明示的に書かれていない情報は出力しない
   - 「一般的にこうだろう」という推測は禁止
   - 不明な項目は null または空配列 [] とする

2. **暗黙知の抽出を優先する**
   - 「〜すると落ち着く」「〜が好き」→ carePreferences
   - 「〜は嫌がる」「〜するとパニック」→ ngActions（最重要）
   - 「今日〜した」「〜の対応で効果があった」→ supportLogs

3. **禁忌事項（NgAction）は最優先**
   - 「絶対に〜しないで」「〜するとパニック」を漏らさない
   - riskLevel を適切に判定：LifeThreatening / Panic / Discomfort

4. **日付の変換**
   - 元号（和暦）→ 西暦（YYYY-MM-DD）に変換
   - 明治元年=1868, 大正=1912, 昭和=1926, 平成=1989, 令和=2019

5. **Entity Resolution（同一対象の統合）**
   - テキスト中の表記揺れは同一エンティティに統合すること
   - 例:「健太」「けんた」「山田健太」「山田くん」→ 同一 Client
   - 例:「お母さん」「母」「花子」→ 同一 KeyPerson
   - 既存クライアントへの追記時は、Neo4j を検索して既存ノードと突合する
   - 統合に確信が持てない場合はユーザーに確認すること

#### JSONスキーマ

```json
{
  "client": {
    "name": "氏名（必須）",
    "dob": "生年月日（YYYY-MM-DD形式、不明なら null）",
    "bloodType": "血液型（不明なら null）",
    "kana": "ふりがな（不明なら null）",
    "aliases": ["通称やニックネーム"]
  },
  "conditions": [
    { "name": "特性・診断名", "status": "Active" }
  ],
  "ngActions": [
    {
      "action": "絶対にしてはいけないこと",
      "reason": "その理由（なぜ危険か）",
      "riskLevel": "LifeThreatening | Panic | Discomfort",
      "relatedCondition": "関連する特性名（あれば）"
    }
  ],
  "carePreferences": [
    {
      "category": "食事/入浴/パニック時/移動/睡眠/服薬/コミュニケーション/その他",
      "instruction": "具体的な手順・方法",
      "priority": "High | Medium | Low",
      "relatedCondition": "関連する特性名（あれば）"
    }
  ],
  "supportLogs": [
    {
      "date": "記録日（YYYY-MM-DD形式）",
      "supporter": "記録者・支援者名",
      "situation": "状況",
      "action": "実施した対応の具体的内容",
      "effectiveness": "Effective | Neutral | Ineffective",
      "note": "詳細メモ・気づき"
    }
  ],
  "certificates": [
    {
      "type": "療育手帳/精神障害者保健福祉手帳/身体障害者手帳/障害福祉サービス受給者証/自立支援医療受給者証",
      "grade": "等級",
      "nextRenewalDate": "更新日（YYYY-MM-DD形式）"
    }
  ],
  "keyPersons": [
    {
      "name": "氏名",
      "relationship": "続柄（母, 叔父, 姉 など）",
      "phone": "電話番号",
      "role": "役割（緊急連絡先, 医療同意, 金銭管理 など）",
      "rank": 1
    }
  ],
  "guardians": [
    {
      "name": "氏名または法人名",
      "type": "成年後見/保佐/補助/任意後見",
      "phone": "連絡先",
      "organization": "所属（法人の場合）"
    }
  ],
  "hospitals": [
    {
      "name": "病院名",
      "specialty": "診療科",
      "phone": "電話番号",
      "doctor": "担当医名"
    }
  ],
  "lifeHistories": [
    {
      "era": "時期（幼少期/学齢期/青年期/成人後）",
      "episode": "エピソード内容",
      "emotion": "その時の感情・反応"
    }
  ],
  "wishes": [
    {
      "content": "願いの内容",
      "date": "記録日（YYYY-MM-DD形式）"
    }
  ]
}
```

### Step 3: ユーザー確認

抽出したJSONをユーザーに提示し、修正点がないか確認する。

### Step 4: Neo4jへの登録

確認後、neo4j MCP の `write_neo4j_cypher` を使って以下のCypherテンプレートで登録する。

#### Cypherテンプレート

**クライアント基本情報:**
```cypher
MERGE (c:Client {name: $name})
SET c.dob = CASE WHEN $dob IS NOT NULL THEN date($dob) ELSE c.dob END,
    c.bloodType = COALESCE($blood, c.bloodType),
    c.kana = COALESCE($kana, c.kana),
    c.aliases = $aliases
```

**特性・診断:**
```cypher
MATCH (c:Client {name: $client})
MERGE (con:Condition {name: $name})
SET con.status = $status
MERGE (c)-[:HAS_CONDITION]->(con)
```

**禁忌事項（NgAction）- 最重要:**
```cypher
MATCH (c:Client {name: $client})
CREATE (ng:NgAction {action: $action, reason: $reason, riskLevel: $risk})
CREATE (c)-[:MUST_AVOID]->(ng)
```

**推奨ケア（CarePreference）:**
```cypher
MATCH (c:Client {name: $client})
CREATE (cp:CarePreference {category: $cat, instruction: $inst, priority: $pri})
CREATE (c)-[:REQUIRES]->(cp)
```

**手帳・受給者証（Certificate）:**
```cypher
MATCH (c:Client {name: $client})
CREATE (cert:Certificate {
    type: $type,
    grade: $grade,
    nextRenewalDate: CASE WHEN $renewal IS NOT NULL THEN date($renewal) ELSE NULL END
})
CREATE (c)-[:HAS_CERTIFICATE]->(cert)
```

**キーパーソン（KeyPerson）:**
```cypher
MATCH (c:Client {name: $client})
MERGE (kp:KeyPerson {name: $name, phone: $phone})
SET kp.relationship = $rel, kp.role = $role
MERGE (c)-[r:HAS_KEY_PERSON]->(kp)
SET r.rank = $rank
```

**後見人（Guardian）:**
```cypher
MATCH (c:Client {name: $client})
CREATE (g:Guardian {name: $name, type: $type, phone: $phone, organization: $org})
CREATE (c)-[:HAS_LEGAL_REP]->(g)
```

**医療機関（Hospital）:**
```cypher
MATCH (c:Client {name: $client})
MERGE (h:Hospital {name: $name})
SET h.specialty = $spec, h.phone = $phone, h.doctor = $doc
MERGE (c)-[:TREATED_AT]->(h)
```

**生育歴（LifeHistory）:**
```cypher
MATCH (c:Client {name: $client})
CREATE (h:LifeHistory {era: $era, episode: $episode, emotion: $emotion})
CREATE (c)-[:HAS_HISTORY]->(h)
```

**願い（Wish）:**
```cypher
MATCH (c:Client {name: $client})
CREATE (w:Wish {content: $content, status: 'Active', date: date($date)})
CREATE (c)-[:HAS_WISH]->(w)
```

**支援記録（SupportLog）:**
```cypher
MERGE (s:Supporter {name: $supporter})
WITH s
MATCH (c:Client {name: $client})
CREATE (log:SupportLog {
    date: date($date),
    situation: $situation,
    action: $action,
    effectiveness: $effectiveness,
    note: $note
})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c)
```

### Step 5: 監査ログの記録（必須）

**すべての書き込み操作の後**、AuditLog ノードを作成して監査証跡を残すこと。

**監査ログ（AuditLog）:**
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

**パラメータ**:
- `$user`: 操作者名（不明なら "narrative-extractor"）
- `$action`: "CREATE" または "UPDATE"
- `$targetType`: ノード種別（例: "Client", "NgAction", "SupportLog"）
- `$targetName`: 内容の要約
- `$details`: 登録した主要フィールドの概要
- `$clientName`: 対象クライアント名

**運用ルール**: 1回の抽出・登録操作で複数ノードを作成した場合、クライアント単位で1件の AuditLog にまとめてよい（details に登録内容の一覧を記載）。

## 命名規則（厳守）

- ノード: PascalCase (`Client`, `NgAction`)
- リレーション: UPPER_SNAKE_CASE (`MUST_AVOID`, `HAS_KEY_PERSON`)
- プロパティ: camelCase (`riskLevel`, `nextRenewalDate`)
- 廃止名 (`PROHIBITED`, `PREFERS`, `EMERGENCY_CONTACT`, `RELATES_TO`, `HAS_GUARDIAN`, `HOLDS`) は書き込み禁止

## 使用例

### 基本的な使い方
```
ユーザー: 以下の文章からクライアント情報を抽出してデータベースに登録してください。

健太は1995年3月15日生まれです。血液型はA型。
自閉スペクトラム症と診断されています。
後ろから急に声をかけないでください。パニックになります。
```

### ファイルからの抽出
```
ユーザー: [ファイル添付] この面談記録から情報を抽出して登録してください。
```

### 追記モード
```
ユーザー: 山田健太さんの情報に以下を追加してください。
かかりつけは産業医科大学病院の中村先生（精神科）です。
```
