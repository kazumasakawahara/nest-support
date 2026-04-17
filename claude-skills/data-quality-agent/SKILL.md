---
name: data-quality-agent
description: Neo4jデータベースの品質を定期的に監視し、更新期限アラート・データ欠損・陳腐化・スキーマ違反を検出してレポートを生成するスキル。「データ品質」「データチェック」「整合性チェック」「更新漏れ」「期限チェック」「DB監査」「データの健全性」「メンテナンス」などの話題で必ずこのスキルを使用すること。月次・週次の定期チェックや、支援会議前のデータ確認にも使用する。scheduleスキルと組み合わせて自動実行も可能。
---

# データ品質監視エージェント (data-quality-agent)

## このスキルの意義

支援データベースは「生きた情報」であり、時間とともに劣化します。手帳の更新期限が過ぎていたら権利侵害に直結し、キーパーソンの電話番号が古ければ緊急時に連絡が取れません。禁忌事項が登録されていないクライアントがいれば、支援者が知らずに二次被害を起こすリスクがあります。

このスキルは、データの「健全性」を定期的に診断し、問題を早期に発見して対応を促します。

## 対象ユーザー

- 計画相談支援専門員（月次業務として）
- 管理者（支援品質の監視として）
- 支援会議の事前準備として

## トリガーワード

- 「データ品質チェック」「データの健全性」「DB監査」
- 「更新漏れがないか確認」「期限切れチェック」
- 「データのメンテナンス」「整合性チェック」
- 「月次チェック」「定期点検」

---

## 使用するMCPツール

| ツール | 用途 |
|--------|------|
| `neo4j:read_neo4j_cypher` | port 7687（障害福祉DB）からの読み取り |
| `neo4j:write_neo4j_cypher` | 使用しない（読み取り専用スキル） |

---

## 診断項目一覧

データ品質の問題を5つのカテゴリに分類する。それぞれ深刻度（Critical / Warning / Info）を持つ。

| カテゴリ | 内容 | 深刻度 |
|---------|------|--------|
| 期限アラート | 手帳・受給者証の更新期限が近い/超過 | Critical / Warning |
| 安全データ欠損 | 禁忌事項やキーパーソンが未登録 | Critical |
| データ陳腐化 | 長期間更新のないノード | Warning |
| 関連性の欠損 | 孤立ノード、リレーション不足 | Warning |
| スキーマ違反 | 廃止リレーション名の使用、不正な列挙値 | Info |
| 重み構造違反 | rank衝突・欠損、priority/effectiveness 不正値 | Warning |
| 重み横断一貫性 | 類似 NgAction / CarePreference で riskLevel / priority がバラついている | Warning |

---

## 実行手順

### Check 1: 更新期限アラート（Critical / Warning）

手帳・受給者証の更新期限を3段階でチェックする。

```cypher
MATCH (c:Client)-[:HAS_CERTIFICATE]->(cert:Certificate)
WHERE cert.nextRenewalDate IS NOT NULL

WITH c, cert,
     duration.inDays(date(), cert.nextRenewalDate).days AS remainingDays

RETURN
    c.name AS クライアント名,
    cert.type AS 証明書種類,
    cert.grade AS 等級,
    cert.nextRenewalDate AS 更新期限,
    remainingDays AS 残り日数,
    CASE
        WHEN remainingDays < 0 THEN 'EXPIRED'
        WHEN remainingDays <= 30 THEN 'CRITICAL'
        WHEN remainingDays <= 60 THEN 'WARNING'
        WHEN remainingDays <= 90 THEN 'NOTICE'
        ELSE 'OK'
    END AS ステータス

ORDER BY remainingDays ASC
```

判定基準:
- **EXPIRED**: 期限超過。即対応が必要 → Critical
- **CRITICAL**: 30日以内。手続き開始が必要 → Critical
- **WARNING**: 60日以内。準備を始める時期 → Warning
- **NOTICE**: 90日以内。次回訪問時に話題にする → Info

### Check 2: 安全データ欠損（Critical）

支援の安全を確保するために不可欠なデータが欠けているクライアントを検出する。

```cypher
MATCH (c:Client)

// 禁忌事項（NgAction）の有無
OPTIONAL MATCH (c)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)

// キーパーソンの有無
OPTIONAL MATCH (c)-[:HAS_KEY_PERSON|EMERGENCY_CONTACT]->(kp:KeyPerson)

// かかりつけ医の有無
OPTIONAL MATCH (c)-[:TREATED_AT]->(hosp:Hospital)

WITH c,
     count(DISTINCT ng) AS ngCount,
     count(DISTINCT kp) AS kpCount,
     count(DISTINCT hosp) AS hospCount

WHERE ngCount = 0 OR kpCount = 0 OR hospCount = 0

RETURN
    c.name AS クライアント名,
    ngCount AS 禁忌事項数,
    kpCount AS キーパーソン数,
    hospCount AS 医療機関数,
    CASE WHEN ngCount = 0 THEN '禁忌事項なし' ELSE '' END AS 禁忌警告,
    CASE WHEN kpCount = 0 THEN 'キーパーソンなし' ELSE '' END AS 連絡先警告,
    CASE WHEN hospCount = 0 THEN 'かかりつけ医なし' ELSE '' END AS 医療警告

ORDER BY ngCount ASC, kpCount ASC
```

特に禁忌事項（NgAction）がゼロのクライアントは最優先で対応する。禁忌事項がないということは「ない」のではなく「聞き取れていない」可能性が高い。

### Check 3: データ陳腐化（Warning）

長期間更新のない情報を検出する。支援記録（SupportLog）が1年以上ないクライアントは、支援が途切れているか記録が滞っている可能性がある。

```cypher
MATCH (c:Client)

// 最新の支援記録
OPTIONAL MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c)

WITH c,
     max(log.date) AS lastLogDate,
     count(log) AS logCount

RETURN
    c.name AS クライアント名,
    logCount AS 支援記録数,
    lastLogDate AS 最終記録日,
    CASE
        WHEN logCount = 0 THEN '記録なし'
        WHEN lastLogDate IS NOT NULL
             AND duration.inDays(lastLogDate, date()).days > 365
        THEN '1年以上更新なし'
        WHEN lastLogDate IS NOT NULL
             AND duration.inDays(lastLogDate, date()).days > 180
        THEN '6ヶ月以上更新なし'
        ELSE 'OK'
    END AS ステータス

ORDER BY
    CASE WHEN logCount = 0 THEN 0 ELSE 1 END,
    lastLogDate ASC
```

### Check 4: 関連性の欠損（Warning）

グラフ構造として不完全な状態を検出する。

```cypher
MATCH (c:Client)

// 特性（Condition）はあるが禁忌事項（NgAction）に繋がっていない
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(con:Condition)
OPTIONAL MATCH (con)<-[:IN_CONTEXT|RELATES_TO]-(ng:NgAction)<-[:MUST_AVOID|PROHIBITED]-(c)

WITH c, con,
     count(DISTINCT ng) AS linkedNgCount
WHERE con IS NOT NULL AND linkedNgCount = 0

RETURN
    c.name AS クライアント名,
    con.name AS 特性名,
    '特性に紐づく禁忌事項がない' AS 問題点
```

```cypher
// 家族情報はあるがCareRoleが未登録
MATCH (c:Client)<-[:IS_PARENT_OF|FAMILY_OF]-(r:Relative)
OPTIONAL MATCH (r)-[:PERFORMS]->(cr:CareRole)

WITH c, r, count(cr) AS careRoleCount
WHERE careRoleCount = 0

RETURN
    c.name AS クライアント名,
    r.name AS 家族名,
    r.relationship AS 続柄,
    'CareRoleが未登録（レジリエンス診断不可）' AS 問題点
```

### Check 5: スキーマ違反（Info）

廃止されたリレーション名や不正な列挙値がないか確認する。

```cypher
// 廃止リレーションの検出
MATCH ()-[r:PROHIBITED]->()
RETURN 'PROHIBITED（正: MUST_AVOID）' AS 違反内容, count(r) AS 件数

UNION ALL

MATCH ()-[r:PREFERS]->()
RETURN 'PREFERS（正: REQUIRES）' AS 違反内容, count(r) AS 件数

UNION ALL

MATCH ()-[r:EMERGENCY_CONTACT]->()
RETURN 'EMERGENCY_CONTACT（正: HAS_KEY_PERSON）' AS 違反内容, count(r) AS 件数

UNION ALL

MATCH ()-[r:RELATES_TO]->()
RETURN 'RELATES_TO（正: IN_CONTEXT）' AS 違反内容, count(r) AS 件数

UNION ALL

MATCH ()-[r:HAS_GUARDIAN]->()
RETURN 'HAS_GUARDIAN（正: HAS_LEGAL_REP）' AS 違反内容, count(r) AS 件数

UNION ALL

MATCH ()-[r:HOLDS]->()
RETURN 'HOLDS（正: HAS_CERTIFICATE）' AS 違反内容, count(r) AS 件数
```

```cypher
// riskLevel の不正値検出
MATCH (ng:NgAction)
WHERE ng.riskLevel IS NOT NULL
  AND NOT ng.riskLevel IN ['LifeThreatening', 'Panic', 'Discomfort']
RETURN
    ng.action AS 禁忌事項,
    ng.riskLevel AS 現在の値,
    '有効値: LifeThreatening, Panic, Discomfort' AS 期待値
```

### Check 7: 重み構造違反（Warning）— 優先度・ランクの整合性

リレーションやノードに付与された「重み」（rank / riskLevel / priority / effectiveness）が、構造的に整合しているかをチェックする。

#### 7a. NgAction.riskLevel 欠損

```cypher
MATCH (c:Client)-[:MUST_AVOID]->(ng:NgAction)
WHERE ng.riskLevel IS NULL OR ng.riskLevel = ''
RETURN
    c.name AS クライアント名,
    ng.action AS 禁忌事項,
    '⚠️ riskLevel 未設定' AS 問題点
ORDER BY c.name
```

riskLevel がない NgAction は緊急度判断ができないため、最優先で補完する。

#### 7b. CarePreference.priority 不正値 / 欠損

```cypher
MATCH (c:Client)-[:REQUIRES]->(cp:CarePreference)
WHERE cp.priority IS NULL
   OR cp.priority = ''
   OR NOT cp.priority IN ['High', 'Medium', 'Low']
RETURN
    c.name AS クライアント名,
    cp.category AS カテゴリ,
    cp.instruction AS 推奨ケア,
    coalesce(cp.priority, '(null)') AS 現在の値,
    '有効値: High / Medium / Low' AS 期待値
ORDER BY c.name
```

#### 7c. SupportLog.effectiveness 不正値

```cypher
MATCH (log:SupportLog)
WHERE log.effectiveness IS NOT NULL
  AND NOT log.effectiveness IN ['Effective', 'Neutral', 'Ineffective']
OPTIONAL MATCH (log)-[:ABOUT]->(c:Client)
RETURN
    c.name AS クライアント名,
    log.date AS 日付,
    log.effectiveness AS 現在の値,
    '有効値: Effective / Neutral / Ineffective' AS 期待値
ORDER BY log.date DESC
```

#### 7d. HAS_KEY_PERSON の rank 衝突

同一クライアントに対して同じ rank が複数存在すると、緊急時の連絡優先度が破綻する。

```cypher
MATCH (c:Client)-[r:HAS_KEY_PERSON]->(kp:KeyPerson)
WHERE r.rank IS NOT NULL
WITH c, r.rank AS rank, count(kp) AS cnt, collect(kp.name) AS names
WHERE cnt > 1
RETURN
    c.name AS クライアント名,
    rank AS 衝突ランク,
    cnt AS 重複人数,
    names AS 該当者リスト
ORDER BY c.name, rank
```

#### 7e. HAS_KEY_PERSON の rank 欠損

```cypher
MATCH (c:Client)-[r:HAS_KEY_PERSON]->(kp:KeyPerson)
WHERE r.rank IS NULL
RETURN
    c.name AS クライアント名,
    kp.name AS キーパーソン名,
    kp.relationship AS 続柄,
    '⚠️ rank 未設定' AS 問題点
ORDER BY c.name
```

#### 7f. HAS_KEY_PERSON の rank 不連続（任意チェック）

rank=1 が無い、rank=1→3 のように途中が抜けている場合を検出。

```cypher
MATCH (c:Client)-[r:HAS_KEY_PERSON]->(kp:KeyPerson)
WHERE r.rank IS NOT NULL
WITH c, collect(DISTINCT r.rank) AS ranks
WITH c, ranks, apoc.coll.min(ranks) AS minRank, size(ranks) AS n
WHERE minRank > 1 OR size(ranks) <> (apoc.coll.max(ranks) - apoc.coll.min(ranks) + 1)
RETURN
    c.name AS クライアント名,
    ranks AS 登録済みランク,
    '⚠️ rank が不連続または 1 が欠落' AS 問題点
```

> **Note**: 7f は APOC プラグインが必要。未導入環境では代替として最小値チェックのみ行う。

---

### Check 8: 重み横断一貫性（Warning）— 類似事象間のブレ検出

同じ意味の NgAction や CarePreference が、別のクライアントで**異なる riskLevel / priority に分類**されていないかを検出する。embedding（Gemini Embedding 2）で意味的類似度を計算し、類似度 ≥ 0.85 のペアで重みが異なる場合に警告する。

**実装**: 専用 Python スクリプト `scripts/check_weight_consistency.py` を使用（Cypher のみでは意味類似度を扱えないため）。

#### 実行コマンド

```bash
# 全件チェック（NgAction + CarePreference）
uv run python scripts/check_weight_consistency.py

# 閾値を下げて広めに検出
uv run python scripts/check_weight_consistency.py --threshold 0.75

# NgAction のみ
uv run python scripts/check_weight_consistency.py --only ng

# 特定クライアントに関連するものだけ
uv run python scripts/check_weight_consistency.py --client "テスト太郎"
```

#### 出力例

```
=== 類似 NgAction 間の riskLevel 不一致 ===
類似度 0.89:
  [LifeThreatening] 後ろから突然声をかける  (田中大輝)
  [Panic]           急に後ろから話しかける  (鈴木美咲)
  → 推奨: どちらかに統一（自傷行動を誘発するなら LifeThreatening）

類似度 0.87:
  [LifeThreatening] エビ・カニを含む食品を提供する  (テスト太郎)
  [Discomfort]     甲殻類アレルギー                (山田健太)
  → 推奨: アレルギーは原則 LifeThreatening
```

#### 判断基準
- **類似度 ≥ 0.85**: ほぼ同義と見なす
- **riskLevel の段差が 1 段 (Panic ⇄ Discomfort)**: 要確認
- **riskLevel の段差が 2 段 (LifeThreatening ⇄ Discomfort)**: 重大な不整合、要修正

#### 前提条件
- `GEMINI_API_KEY` 環境変数が設定されていること
- NgAction / CarePreference に embedding が付与されていること
  - 未付与の場合: `uv run python scripts/backfill_embeddings.py --label NgAction`

---

### Check 6: 全体統計サマリー

データベース全体の概況を把握する。

```cypher
MATCH (c:Client)
OPTIONAL MATCH (c)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)
OPTIONAL MATCH (c)-[:HAS_KEY_PERSON|EMERGENCY_CONTACT]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:TREATED_AT]->(hosp:Hospital)
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(con:Condition)
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(cert:Certificate)
OPTIONAL MATCH (c)-[:REQUIRES|PREFERS]->(cp:CarePreference)

RETURN
    count(DISTINCT c) AS クライアント総数,
    count(DISTINCT ng) AS 禁忌事項総数,
    count(DISTINCT kp) AS キーパーソン総数,
    count(DISTINCT hosp) AS 医療機関総数,
    count(DISTINCT con) AS 特性総数,
    count(DISTINCT cert) AS 証明書総数,
    count(DISTINCT cp) AS 配慮事項総数
```

---

## レポート出力形式

全チェック完了後、以下の形式でレポートを出力する。

```markdown
## データ品質レポート
**診断日:** [日付]
**対象DB:** 障害福祉支援DB（port 7687）

---

### データベース概況
- クライアント: [N]名
- 禁忌事項: [N]件 / キーパーソン: [N]名 / 医療機関: [N]件

---

### 🔴 Critical（即対応が必要）

#### 期限超過・期限切迫
| クライアント | 証明書 | 期限 | 残り日数 | 状態 |
|------------|--------|------|---------|------|
| [名前] | [種類] | [日付] | [日数] | EXPIRED/CRITICAL |

#### 安全データ欠損
| クライアント | 禁忌事項 | キーパーソン | かかりつけ医 |
|------------|---------|------------|------------|
| [名前] | ⚠️なし | ✅あり | ⚠️なし |

---

### 🟡 Warning（早めの対応を推奨）

#### データ陳腐化
| クライアント | 最終記録日 | 経過 |
|------------|----------|------|
| [名前] | [日付] | 1年以上 |

#### 関連性の欠損
| クライアント | 問題点 |
|------------|--------|
| [名前] | 特性に紐づく禁忌事項がない |

---

### 🔵 Info（参考情報）

#### スキーマ違反
| 違反内容 | 件数 |
|---------|------|
| PROHIBITED（正: MUST_AVOID） | [N]件 |

#### riskLevel不正値
[該当があれば表示]

---

### 推奨アクション
1. [Criticalの問題に対するアクション]
2. [Warningの問題に対するアクション]
3. [次回チェック推奨日]
```

---

## スケジュール実行

`schedule` スキルと組み合わせて定期実行する場合のプロンプト例:

**月次チェック（推奨）:**
> 「毎月1日にデータ品質チェックを実行して、レポートをMarkdownで保存して」

**週次期限チェック（更新期限のみ）:**
> 「毎週月曜に更新期限のチェックだけ実行して」

スケジュール実行時は、レポートを `~/AI-Workspace/data-quality-reports/` に日付付きファイル名で保存する。
ファイル名例: `data-quality-report-2026-02-27.md`

---

## オンデマンド実行のバリエーション

ユーザーの要望に応じてチェック範囲を調整できる。

| リクエスト例 | 実行するチェック |
|------------|----------------|
| 「全体チェック」 | Check 1〜8 全て |
| 「期限だけ確認」 | Check 1 のみ |
| 「安全データの確認」 | Check 2 のみ |
| 「○○さんのデータ品質」 | 全チェックをクライアント指定で実行 |
| 「スキーマ違反を直して」 | Check 5 + 廃止リレーションのマイグレーション提案 |
| 「重みをチェック」「優先度をチェック」 | Check 7 + Check 8 |
| 「riskLevel のブレを確認」 | Check 8 (`--only ng`) |
| 「priority のブレを確認」 | Check 8 (`--only cp`) |

特定クライアントに絞る場合は、各クエリの `MATCH (c:Client)` に `WHERE c.name CONTAINS $clientName` を追加する。

---

## 廃止リレーションのマイグレーション

Check 5 でスキーマ違反が見つかった場合、マイグレーション（旧名→正式名への変更）を提案できる。実行前に必ずユーザーに確認すること。

マイグレーション例（PROHIBITED → MUST_AVOID）:

```cypher
// Step 1: 確認（件数を表示）
MATCH (c)-[old:PROHIBITED]->(ng:NgAction)
RETURN count(old) AS マイグレーション対象件数

// Step 2: マイグレーション実行（ユーザー承認後）
MATCH (c)-[old:PROHIBITED]->(ng:NgAction)
MERGE (c)-[:MUST_AVOID]->(ng)
DELETE old
RETURN count(*) AS マイグレーション完了件数
```

各廃止リレーションについて同様のパターンで実行する。マイグレーション後は再度 Check 5 を実行して完了を確認する。

---

## 関連スキル

| スキル | 連携 |
|--------|------|
| `neo4j-support-db` | Cypherテンプレートの参照元 |
| `onboarding-wizard` | Check 2 で欠損が見つかったクライアントへの情報追加 |
| `resilience-checker` | Check 4 でCareRole未登録が見つかった場合の登録支援 |
| `schedule` | 定期実行のスケジューリング |
