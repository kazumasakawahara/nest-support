---
name: emergency-protocol
description: 緊急時対応プロトコル。クライアントの安全に関わる情報を優先順位付きで取得し、二次被害を防止する。禁忌事項→推奨ケア→緊急連絡先→かかりつけ医→法的代理人の順で情報を提示。
---

# 緊急時対応プロトコル (emergency-protocol)

## ★ 最重要: このスキルについて

このスキルは**人命に関わる情報**を扱います。緊急時に支援者が迷わず適切な対応を取れるよう、
Safety Firstプロトコルに基づき**厳格な優先順位**で情報を提示します。

**絶対原則**: 禁忌事項（NgAction）を最初に表示しないと**二次被害のリスク**があります。

---

## トリガー条件

以下のいずれかに該当する場合、**即座に**このスキルを起動すること:

### 緊急ワード（即時起動）
- パニック、自傷、事故、急病、けが、救急、緊急、発作
- 倒れた、暴れている、出血、呼吸、意識がない
- 「どうすればいい」「助けて」

### 通常の緊急情報照会
- 「〇〇さんの緊急情報を見せて」
- 「〇〇さんの禁忌事項は？」
- 「〇〇さんにしてはいけないことは？」
- 「緊急連絡先を教えて」

---

## 安全ルール（厳守）

### ルール1: 情報提示の優先順位（絶対遵守）

情報は**必ず以下の順序で提示**する。順序の変更は禁止。

```
1. 🚫 禁忌事項（NgAction）       ← 二次被害防止のため最優先
2. ✅ 推奨ケア（CarePreference）  ← その場を落ち着かせるため
3. 📞 緊急連絡先（KeyPerson）     ← ランク順に連絡
4. 🏥 かかりつけ医（Hospital）    ← 医療が必要な場合
5. ⚖️ 法的代理人（Guardian）      ← 医療同意等が必要な場合
```

### ルール2: 禁忌事項のリスクレベル表示

NgActionには3段階のリスクレベルがあり、以下の順で表示する:

| レベル | 意味 | 表示 |
|--------|------|------|
| `LifeThreatening` | 命に関わる | ⚠️🔴 **最優先** |
| `Panic` | パニック誘発 | ⚠️🟡 **要注意** |
| `Discomfort` | 不快・ストレス | ⚠️🟢 **配慮必要** |

### ルール3: 状況フィルタリング

ユーザーが状況キーワード（パニック、食事、入浴等）を指定した場合:
- NgActionの`action`フィールドで関連するものをフィルタリング
- CarePreferenceの`category`フィールドで関連するものをフィルタリング
- **フィルタしてもヒットがない場合は全件表示**する（安全のため）

### ルール4: 年齢計算

生年月日（dob）が取得できた場合、必ず現在の年齢を計算して併記する。
例: `1995-04-15（30歳）`

### ルール5: 読み取り専用

このスキルは**読み取り専用**。緊急時にデータの書き込みは行わない。
すべてのクエリは `neo4j:read_neo4j_cypher` を使用する。

---

## 使用するMCPツール

| ツール | 用途 |
|--------|------|
| `neo4j:read_neo4j_cypher` | すべての読み取りクエリに使用 |

**注意**: `neo4j:write_neo4j_cypher` はこのスキルでは**使用禁止**。

---

## Cypherテンプレート集

### テンプレート1: 緊急時一括取得（推奨）

最も効率的な方法。1つのクエリで全情報を取得する。

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $clientName
OPTIONAL MATCH (c)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)
OPTIONAL MATCH (ng)-[:IN_CONTEXT]->(ngCond:Condition)
WITH c, collect(DISTINCT {
    action: ng.action,
    reason: ng.reason,
    riskLevel: ng.riskLevel,
    context: ngCond.name
}) AS ngActions

OPTIONAL MATCH (c)-[:REQUIRES|PREFERS]->(cp:CarePreference)
OPTIONAL MATCH (cp)-[:ADDRESSES]->(cpCond:Condition)
WITH c, ngActions, collect(DISTINCT {
    category: cp.category,
    instruction: cp.instruction,
    priority: cp.priority,
    forCondition: cpCond.name
}) AS carePrefs

OPTIONAL MATCH (c)-[kpRel:HAS_KEY_PERSON]->(kp:KeyPerson)
WITH c, ngActions, carePrefs, collect(DISTINCT {
    rank: kpRel.rank,
    name: kp.name,
    relationship: kp.relationship,
    phone: kp.phone,
    role: kp.role
}) AS keyPersons

OPTIONAL MATCH (c)-[:TREATED_AT]->(h:Hospital)
WITH c, ngActions, carePrefs, keyPersons, collect(DISTINCT {
    name: h.name,
    specialty: h.specialty,
    phone: h.phone,
    doctor: h.doctor
}) AS hospitals

OPTIONAL MATCH (c)-[:HAS_LEGAL_REP]->(g:Guardian)
RETURN
    c.name AS clientName,
    c.dob AS dob,
    c.bloodType AS bloodType,
    ngActions,
    carePrefs,
    keyPersons,
    hospitals,
    collect(DISTINCT {
        name: g.name,
        type: g.type,
        phone: g.phone,
        organization: g.organization
    }) AS guardians
```

**パラメータ**: `$clientName` — クライアント名（部分一致）

### テンプレート2: 禁忌事項のみ取得（最速）

緊急度が最も高い場合に使用。禁忌事項だけを即座に取得する。

```cypher
MATCH (c:Client)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)
WHERE c.name CONTAINS $clientName
OPTIONAL MATCH (ng)-[:IN_CONTEXT]->(cond:Condition)
RETURN DISTINCT
    c.name AS clientName,
    ng.action AS action,
    ng.reason AS reason,
    ng.riskLevel AS riskLevel,
    cond.name AS relatedCondition
ORDER BY
    CASE ng.riskLevel
        WHEN 'LifeThreatening' THEN 1
        WHEN 'Panic' THEN 2
        WHEN 'Discomfort' THEN 3
        ELSE 4
    END
```

### テンプレート3: 状況別フィルタ付き取得

特定の状況（パニック、食事、入浴等）に関連する情報のみ取得。

```cypher
MATCH (c:Client)
WHERE c.name CONTAINS $clientName

// 状況に関連する禁忌事項
OPTIONAL MATCH (c)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)
WHERE ng.action CONTAINS $situation OR ng.reason CONTAINS $situation
OPTIONAL MATCH (ng)-[:IN_CONTEXT]->(ngCond:Condition)
WITH c, collect(DISTINCT {
    action: ng.action,
    reason: ng.reason,
    riskLevel: ng.riskLevel,
    context: ngCond.name
}) AS ngActions

// 状況に関連する推奨ケア
OPTIONAL MATCH (c)-[:REQUIRES|PREFERS]->(cp:CarePreference)
WHERE cp.category CONTAINS $situation OR cp.instruction CONTAINS $situation
WITH c, ngActions, collect(DISTINCT {
    category: cp.category,
    instruction: cp.instruction,
    priority: cp.priority
}) AS carePrefs

// 緊急連絡先（常に全件取得）
OPTIONAL MATCH (c)-[kpRel:HAS_KEY_PERSON]->(kp:KeyPerson)
WITH c, ngActions, carePrefs, collect(DISTINCT {
    rank: kpRel.rank,
    name: kp.name,
    relationship: kp.relationship,
    phone: kp.phone
}) AS keyPersons

RETURN
    c.name AS clientName,
    c.dob AS dob,
    c.bloodType AS bloodType,
    ngActions,
    carePrefs,
    keyPersons
```

**パラメータ**: `$clientName`, `$situation`

### テンプレート4: 緊急連絡先のみ取得

連絡先だけが必要な場合。

```cypher
MATCH (c:Client)-[r:HAS_KEY_PERSON]->(kp:KeyPerson)
WHERE c.name CONTAINS $clientName
RETURN
    kp.name AS name,
    kp.relationship AS relationship,
    kp.phone AS phone,
    kp.role AS role,
    r.rank AS rank
ORDER BY r.rank
```

---

## 出力フォーマット

### 緊急時の出力テンプレート

クエリ結果を取得したら、以下の形式で整形して提示する:

```
⚠️ 緊急対応情報: 【クライアント名】
生年月日: YYYY-MM-DD（XX歳） / 血液型: X型

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 1. 禁忌事項（絶対にしないこと）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️🔴 【LifeThreatening】...
⚠️🟡 【Panic】...
⚠️🟢 【Discomfort】...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 2. 推奨ケア（こうすると落ち着く）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[カテゴリ] 手順...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 3. 緊急連絡先
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1位: 名前（続柄）TEL: XXX-XXXX-XXXX
2位: 名前（続柄）TEL: XXX-XXXX-XXXX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏥 4. かかりつけ医
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
病院名 / 診療科 / 担当医 / TEL: XXX-XXXX-XXXX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚖️ 5. 法的代理人
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
名前 / 種別 / TEL: XXX-XXXX-XXXX
```

### データが空の場合の処理

各セクションでデータが空（`null`値のみ）の場合:
- 空のエントリを除外する（`action`や`name`が`null`のレコードは表示しない）
- 「登録されていません」と表示する
- **禁忌事項が0件の場合も「禁忌事項: 登録なし」と明示する**（確認済みであることを示す）

---

## 典型的な使用シナリオ

### シナリオ1: パニック発生

```
ユーザー: 「山田健太さんがパニックを起こしています！」

手順:
1. テンプレート3（状況別フィルタ）を使用
   → $clientName = "山田健太", $situation = "パニック"
2. フィルタ結果が0件の場合 → テンプレート1（全件取得）にフォールバック
3. 出力フォーマットに従い、禁忌事項から順に提示
```

### シナリオ2: 初めて担当するクライアント

```
ユーザー: 「佐藤花子さんの緊急情報を確認したい」

手順:
1. テンプレート1（一括取得）を使用
   → $clientName = "佐藤花子"
2. 全情報を出力フォーマットに従い提示
```

### シナリオ3: 救急隊への情報提供

```
ユーザー: 「山田健太さんの情報を救急隊に伝えたい」

手順:
1. テンプレート1（一括取得）を使用
2. 以下を簡潔にまとめて提示:
   - 氏名、年齢、血液型
   - 禁忌事項（医療処置に影響するもの）
   - かかりつけ医
   - 緊急連絡先（第1位）
```

### シナリオ4: クライアントが見つからない場合

```
クエリ結果が0件の場合:
1. 「該当するクライアントが見つかりませんでした」と通知
2. list_clients相当のクエリで候補を提示:

MATCH (c:Client)
RETURN c.name AS name
ORDER BY c.name

3. 「もしかして: 〇〇さん？」と候補を提示
```

---

## 関連スキルとの連携

| スキル | 連携タイミング |
|--------|---------------|
| `neo4j-support-db` | 緊急対応後の支援記録追加 |
| `livelihood-support` | 経済的リスクの確認（生活保護受給者の場合） |
| `ecomap-generator` | 支援ネットワーク図の生成 |

---

## データモデル参照

### 関連ノード

| ノード | 役割 | 主要プロパティ |
|--------|------|----------------|
| `Client` | 本人 | name, dob, bloodType |
| `NgAction` | 禁忌事項 | action, reason, riskLevel |
| `CarePreference` | 推奨ケア | category, instruction, priority |
| `KeyPerson` | 緊急連絡先 | name, relationship, phone, role |
| `Hospital` | かかりつけ医 | name, specialty, doctor, phone |
| `Guardian` | 法的代理人 | name, type, phone, organization |
| `Condition` | 特性・診断 | name, status |

### 関連リレーション

| リレーション | 方向 | 備考 |
|-------------|------|------|
| `MUST_AVOID` | Client → NgAction | **正式名**（書き込み時はこちらを使用） |
| ~~`PROHIBITED`~~ | Client → NgAction | **廃止**（読み取り時のみ後方互換で対応） |
| `REQUIRES` | Client → CarePreference | **正式名**（書き込み時はこちらを使用） |
| ~~`PREFERS`~~ | Client → CarePreference | **廃止**（読み取り時のみ後方互換で対応） |
| `HAS_KEY_PERSON` | Client → KeyPerson | rankプロパティで優先順位 |
| `TREATED_AT` | Client → Hospital | — |
| `HAS_LEGAL_REP` | Client → Guardian | — |
| `IN_CONTEXT` | NgAction → Condition | 禁忌の文脈（関連特性） |
| `ADDRESSES` | CarePreference → Condition | ケアの対象特性 |

---

## バージョン

- v1.0.0 (2026-02-12) - 初版: server.py の search_emergency_info から移行
