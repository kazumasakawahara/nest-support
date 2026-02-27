---
name: visit-prep
description: 訪問・同行支援の前に、クライアントの禁忌事項・推奨ケア・直近の支援記録・更新期限を自動収集し、簡潔なブリーフィングシートを生成するスキル。「訪問準備」「訪問前に確認」「明日〇〇さんのところに行く」「同行支援の注意点」「ブリーフィング」などの発言時に必ずこのスキルを使用すること。訪問や面談の予定がある場合にも積極的に使用する。
---

# 訪問準備ブリーフィング スキル (visit-prep)

## なぜこのスキルが必要か

訪問支援で最も危険なのは「知らなかったこと」による事故です。禁忌事項を知らずに大きな音を出してパニックを誘発する、前回の訪問で問題があったことを把握せずに同じ過ちを繰り返す、といった二次被害を防ぐために、訪問前に必要な情報を自動的に集約します。

## 対象

- 計画相談支援専門員、ヘルパー、同行支援員
- 訪問・同行支援の前日〜当日に使用

## トリガーワード

- 「訪問準備」「訪問前に確認」「ブリーフィング」
- 「明日〇〇さんのところに行く」「〇〇さんの訪問がある」
- 「同行支援の注意点」「外出支援の準備」
- 「〇〇さんに会う前に確認しておきたい」

---

## 使用するMCPツール

| ツール | 用途 |
|--------|------|
| `neo4j:read_neo4j_cypher` | port 7687（障害福祉DB）からの読み取り |
| `neo4j:write_neo4j_cypher` | 使用しない（読み取り専用スキル） |

---

## 実行手順

### Step 1: クライアント名の特定

ユーザーの発言からクライアント名を抽出する。曖昧な場合はクライアント一覧から候補を提示して確認する。

### Step 2: 安全情報の取得（最優先）

禁忌事項と推奨ケアを取得する。この情報は**必ず最初に表示**する。

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $clientName

// 禁忌事項（最重要）
OPTIONAL MATCH (c)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)
OPTIONAL MATCH (ng)-[:IN_CONTEXT|RELATES_TO]->(ngCon:Condition)

// 推奨ケア
OPTIONAL MATCH (c)-[:REQUIRES|PREFERS]->(cp:CarePreference)

// 特性・診断
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(con:Condition)

RETURN
    c.name AS 氏名,
    c.dob AS 生年月日,
    c.bloodType AS 血液型,
    collect(DISTINCT {
        action: ng.action,
        reason: ng.reason,
        riskLevel: ng.riskLevel,
        context: ngCon.name
    }) AS 禁忌事項,
    collect(DISTINCT {
        category: cp.category,
        instruction: cp.instruction,
        priority: cp.priority
    }) AS 配慮事項,
    collect(DISTINCT {
        name: con.name,
        status: con.status
    }) AS 特性
```

**パラメータ**: `$clientName`

### Step 3: 緊急連絡先の取得

```cypher
MATCH (c:Client)-[kpRel:HAS_KEY_PERSON|EMERGENCY_CONTACT]->(kp:KeyPerson)
WHERE c.name CONTAINS $clientName
OPTIONAL MATCH (c)-[:TREATED_AT]->(hosp:Hospital)
RETURN
    collect(DISTINCT {
        rank: kpRel.rank,
        name: kp.name,
        relationship: kp.relationship,
        phone: kp.phone,
        role: kp.role
    }) AS キーパーソン,
    collect(DISTINCT {
        name: hosp.name,
        specialty: hosp.specialty,
        phone: hosp.phone,
        doctor: hosp.doctor
    }) AS 医療機関
```

### Step 4: 直近の支援記録の確認

前回訪問からの変化や申し送り事項を把握する。

```cypher
MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c:Client)
WHERE c.name CONTAINS $clientName
RETURN
    log.date AS 日付,
    s.name AS 支援者,
    log.situation AS 状況,
    log.action AS 対応,
    log.effectiveness AS 効果,
    log.note AS メモ
ORDER BY log.date DESC
LIMIT 5
```

### Step 5: 効果的ケアパターンの確認

繰り返し効果があった対応方法を抽出する。

```cypher
MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c:Client)
WHERE c.name CONTAINS $clientName
  AND (toLower(toString(log.effectiveness)) STARTS WITH 'effective'
       OR toLower(toString(log.effectiveness)) STARTS WITH 'excellent'
       OR toString(log.effectiveness) CONTAINS '効果')
WITH log.action AS 対応方法, count(*) AS 回数,
    collect(DISTINCT log.situation) AS 状況一覧
WHERE 回数 >= 2
RETURN 対応方法, 回数, 状況一覧
ORDER BY 回数 DESC
```

### Step 6: 更新期限のチェック

訪問時に手続きの話をすべき証明書があるか確認する。

```cypher
MATCH (c:Client)-[:HAS_CERTIFICATE]->(cert:Certificate)
WHERE c.name CONTAINS $clientName
  AND cert.nextRenewalDate IS NOT NULL
WITH c, cert,
     duration.inDays(date(), cert.nextRenewalDate).days AS 残り日数
WHERE 残り日数 <= 90 AND 残り日数 >= 0
RETURN
    cert.type AS 証明書種類,
    cert.grade AS 等級,
    cert.nextRenewalDate AS 更新期限,
    残り日数
ORDER BY 残り日数 ASC
```

### Step 7: ブリーフィングシートの出力

以下の形式で整形して表示する。**禁忌事項は必ず最初に配置**すること。

```markdown
## 訪問前ブリーフィング
**対象:** [クライアント名]（[年齢]歳）
**訪問日:** [日付]
**訪問目的:** [目的]（ユーザーから聞き取り）

---

### 絶対に避けること
[riskLevel順: LifeThreatening → Panic → Discomfort]
- [禁忌事項] — 理由: [reason]

### 効果的な関わり方
- [推奨ケアリスト]
- [効果的ケアパターン（複数回効果実証済み）]

### 特性・診断
- [Conditionリスト]

### 緊急時の連絡先
1. [キーパーソン1]（[続柄]）TEL: [電話番号]
2. [キーパーソン2]（[続柄]）TEL: [電話番号]
   かかりつけ: [病院名] TEL: [電話番号]

### 前回からの申し送り
[直近5件の支援記録の要点]

### 確認すべき期限
[90日以内に更新期限が来る証明書]
```

---

## 同行支援（外出）の場合の追加確認

訪問目的が外出や同行支援の場合は、以下も確認して追記する。

- **パニックの引き金**: 禁忌事項からIN_CONTEXTの関連で外出に関わるものを抽出
- **落ち着ける方法**: CarePreferenceからcategory = 'パニック' を抽出
- **持ち物チェック**: 薬、緊急連絡先カード、好きなアイテム
- **最寄り医療機関**: Hospital情報

---

## PDF/HTML出力

ブリーフィングシートをファイルとして出力する場合は、以下の連携スキルを使用する。

| 形式 | スキル |
|------|--------|
| PDF | `html-to-pdf` スキル（HTML作成→Chrome印刷） |
| HTML | 直接HTMLファイルを生成 |

---

## 関連スキル

| スキル | 連携 |
|--------|------|
| `emergency-protocol` | 訪問中に緊急事態が発生した場合 |
| `neo4j-support-db` | Cypherテンプレートの参照元 |
| `ecomap-generator` | 支援ネットワークの可視化が必要な場合 |
