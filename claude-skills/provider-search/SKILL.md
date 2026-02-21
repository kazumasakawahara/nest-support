---
name: provider-search
description: 福祉サービス事業所の検索・管理・口コミ評価を行うスキル。WAM NETから取得した事業所情報（ServiceProvider）と支援者による口コミ（ProviderFeedback）をNeo4jグラフデータベースで管理する。汎用neo4j MCPツールでCypherクエリを実行。
---

# provider-search スキル

## 概要
福祉サービス事業所の検索・管理・口コミ評価を行うスキル。WAM NETから取得した事業所情報（ServiceProvider）と支援者による口コミ（ProviderFeedback）をNeo4jグラフデータベースで管理する。

## 対象Neo4jインスタンス
- **support-db**: `bolt://localhost:7687`（HTTP: 7474）
- neo4j MCPの `read_neo4j_cypher` / `write_neo4j_cypher` を使用

## データモデル

### ノード

#### ServiceProvider（福祉サービス事業所）

**重要**: WAM NETインポート時期により**2種類のプロパティ命名規則**が混在している。

| 新形式（camelCase）| 旧形式（snake_case）| 説明 | 件数目安 |
|-------------------|---------------------|------|---------
| name | office_name | 事業所名 | 新1002件 / 旧128件 / 空1496件 |
| corporateName | corp_name | 法人名 | |
| serviceType | service_type | サービス種類 | |
| city | ― | 市区町村 | 両形式共通 |
| address | address | 住所 | 両形式共通 |
| phone | phone | 電話番号 | 両形式共通 |
| fax | ― | FAX番号 | |
| fullAddress | ― | 完全住所 | 新形式のみ |
| postalCode | ― | 郵便番号 | 新形式のみ |
| capacity | ― | 定員 | 約1084件のみ |
| currentUsers | ― | 現在利用者数 | ほぼ未設定 |
| availability | ― | 空き状況 | 997件が'未確認'、残りはnull |
| targetDisability | ― | 対象障害種別 | ほぼ未設定 |
| features | ― | 特色・特徴 | ほぼ未設定 |
| closedDays | closed_days | 休日 | |
| hoursWeekday | hours_weekday | 平日営業時間 | |
| hoursSaturday | ― | 土曜営業時間 | 新形式のみ |
| hoursSunday | ― | 日曜営業時間 | 新形式のみ |
| hoursHoliday | ― | 祝日営業時間 | 新形式のみ |
| providerId | office_number | WAM NET事業所番号 | |
| wamnetId | ― | WAM NET ID | 新形式のみ |
| prefecture | ― | 都道府県 | 新形式のみ |
| municipalityCode | city_code | 市区町村コード | |
| serviceTypeCode | ― | サービス種類コード | 新形式のみ |
| serviceCategory | ― | サービスカテゴリ | 新形式のみ |
| latitude | latitude | 緯度 | 両形式共通 |
| longitude | longitude | 経度 | 両形式共通 |
| url | ― | Webサイト | 新形式のみ |
| dataSource | data_source | データソース（WAM_NET） | |
| updatedAt | updated_at | 最終更新日 | |

**名前解決パターン**: 事業所名の表示には必ず以下のCOALESCEを使うこと:
```cypher
COALESCE(sp.name, sp.office_name, sp.corporateName, sp.corp_name, '名称未登録') AS displayName
```

**サービス種類の解決**:
```cypher
COALESCE(sp.serviceType, sp.service_type, '') AS serviceType
```

#### ProviderFeedback（口コミ・評価）
| プロパティ | 型 | 説明 |
|-----------|------|------|
| feedbackId | String | フィードバックID（UUID） |
| category | String | カテゴリ（行動障害対応/コミュニケーション/環境/送迎/食事/医療連携/その他） |
| content | String | 口コミ内容 |
| rating | String | 評価（◎良い / ○普通 / △課題あり / ×不可） |
| source | String | 情報源（支援者名 or 匿名） |
| date | String | 登録日（ISO形式） |
| isConfirmed | Boolean | 確認済みフラグ |

**注意**: ProviderFeedbackノードは運用で登録するもの。初期状態では0件。

### リレーションシップ

```
(:Client)-[:USES_SERVICE {startDate, endDate, status, note}]->(:ServiceProvider)
(:ServiceProvider)-[:HAS_FEEDBACK]->(:ProviderFeedback)
```

**USES_SERVICE プロパティ:**
- `startDate`: 利用開始日
- `endDate`: 利用終了日
- `status`: Active（利用中）/ Pending（調整中）/ Ended（利用終了）
- `note`: 備考

**注意**: USES_SERVICE関係も運用で作成するもの。初期状態では0件。

## 評価スコア換算

| rating | スコア |
|--------|--------|
| ◎良い | 4 |
| ○普通 | 3 |
| △課題あり | 2 |
| ×不可 | 1 |

## データ統計（2026年1月時点）

| 項目 | 件数 |
|------|------|
| ServiceProvider総数 | 2621 |
| 名前あり（新形式） | 1002 |
| 名前あり（旧形式） | 128 |
| 名前なし | 1496 |
| capacity設定済み | 1084 |
| availability設定済み | 997（すべて'未確認'） |
| ProviderFeedback | 0（運用後に蓄積） |
| USES_SERVICE関係 | 0（運用後に作成） |

## Cypherテンプレート

### ── 読み取り系（read_neo4j_cypher） ──

### テンプレート1: 事業所検索（基本）

サービス種類・地域で絞り込む。名前があるレコードのみ返す。
条件は任意で組み合わせ可能（不要なWHERE行を削除して使う）。

```cypher
MATCH (sp:ServiceProvider)
WHERE (sp.name IS NOT NULL AND sp.name <> '')
  AND COALESCE(sp.serviceType, sp.service_type, '') CONTAINS $serviceType
  AND sp.city CONTAINS $city
RETURN COALESCE(sp.name, sp.office_name) AS name,
       COALESCE(sp.corporateName, sp.corp_name, '') AS corporateName,
       COALESCE(sp.serviceType, sp.service_type, '') AS serviceType,
       sp.city AS city,
       COALESCE(sp.address, sp.fullAddress, '') AS address,
       sp.phone AS phone,
       sp.capacity AS capacity,
       COALESCE(sp.availability, '未確認') AS availability,
       COALESCE(sp.closedDays, sp.closed_days, '') AS closedDays,
       sp.hoursWeekday AS hoursWeekday
ORDER BY
  CASE COALESCE(sp.availability, '未確認')
    WHEN '空きあり' THEN 1
    WHEN '要相談' THEN 2
    WHEN '未確認' THEN 3
    WHEN '満員' THEN 4
    ELSE 5
  END,
  COALESCE(sp.name, sp.office_name)
LIMIT $limit
```

**使い方**: 条件を自由に組み合わせる。

- **サービス種類のみ**: `AND COALESCE(sp.serviceType, sp.service_type, '') CONTAINS '生活介護'` のWHERE行のみ残す
- **地域のみ**: `AND sp.city CONTAINS '北九州'` のWHERE行のみ残す
- **キーワード検索追加**: `AND (COALESCE(sp.name, sp.office_name, '') CONTAINS $keyword OR COALESCE(sp.corporateName, sp.corp_name, '') CONTAINS $keyword)`
- **空き状況絞り込み**: `AND COALESCE(sp.availability, '未確認') = '空きあり'`
- **旧形式も含める**: `WHERE (sp.name IS NOT NULL AND sp.name <> '') OR (sp.office_name IS NOT NULL AND sp.office_name <> '')`

パラメータ:
- `$serviceType`: サービス種類（部分一致、例: '生活介護', 'グループホーム', '就労継続支援B型'）
- `$city`: 市区町村（部分一致、例: '北九州', '久留米'）
- `$limit`: 取得件数（デフォルト20）

### テンプレート2: クライアントの利用事業所一覧

```cypher
MATCH (c:Client)-[r:USES_SERVICE]->(sp:ServiceProvider)
WHERE c.name CONTAINS $clientName
RETURN COALESCE(sp.name, sp.office_name, sp.corporateName, '名称未登録') AS providerName,
       COALESCE(sp.serviceType, sp.service_type, '') AS serviceType,
       sp.phone AS phone,
       r.status AS status,
       r.startDate AS startDate,
       r.endDate AS endDate,
       r.note AS note
ORDER BY
  CASE r.status
    WHEN 'Active' THEN 1
    WHEN 'Pending' THEN 2
    WHEN 'Ended' THEN 3
    ELSE 4
  END,
  r.startDate DESC
```

パラメータ:
- `$clientName`: クライアント名（部分一致）

**注意**: USES_SERVICE関係が存在しない場合は空の結果が返る。

### テンプレート3: 代替事業所検索

現在利用中のサービスと同種の事業所で、まだ利用していないものを検索する。

```cypher
MATCH (c:Client)-[r:USES_SERVICE]->(current:ServiceProvider)
WHERE c.name CONTAINS $clientName
  AND r.status = 'Active'
WITH c, collect(COALESCE(current.name, current.office_name)) AS currentNames,
     collect(DISTINCT COALESCE(current.serviceType, current.service_type)) AS serviceTypes
UNWIND serviceTypes AS st
MATCH (alt:ServiceProvider)
WHERE COALESCE(alt.serviceType, alt.service_type, '') = st
  AND COALESCE(alt.name, alt.office_name, '') <> ''
  AND NOT COALESCE(alt.name, alt.office_name) IN currentNames
RETURN COALESCE(alt.name, alt.office_name) AS name,
       COALESCE(alt.corporateName, alt.corp_name, '') AS corporateName,
       COALESCE(alt.serviceType, alt.service_type, '') AS serviceType,
       alt.city AS city,
       alt.phone AS phone,
       COALESCE(alt.availability, '未確認') AS availability,
       alt.capacity AS capacity
ORDER BY
  CASE COALESCE(alt.availability, '未確認')
    WHEN '空きあり' THEN 1
    WHEN '要相談' THEN 2
    WHEN '未確認' THEN 3
    WHEN '満員' THEN 4
    ELSE 5
  END,
  COALESCE(alt.name, alt.office_name)
LIMIT 20
```

パラメータ:
- `$clientName`: クライアント名（部分一致）

### テンプレート4: 事業所の口コミ取得

```cypher
MATCH (sp:ServiceProvider)-[:HAS_FEEDBACK]->(f:ProviderFeedback)
WHERE COALESCE(sp.name, sp.office_name, sp.corporateName, '') CONTAINS $providerName
RETURN f.category AS category,
       f.content AS content,
       f.rating AS rating,
       f.source AS source,
       f.date AS date
ORDER BY f.date DESC
LIMIT $limit
```

パラメータ:
- `$providerName`: 事業所名（部分一致）
- `$limit`: 取得件数（デフォルト20）

**カテゴリ絞り込み**: `AND f.category = $category` をWHEREに追加。

### テンプレート5: 事業所の評価サマリー

```cypher
MATCH (sp:ServiceProvider)-[:HAS_FEEDBACK]->(f:ProviderFeedback)
WHERE COALESCE(sp.name, sp.office_name, sp.corporateName, '') CONTAINS $providerName
WITH sp,
     count(f) AS totalFeedbacks,
     sum(CASE WHEN f.rating STARTS WITH '◎' THEN 1 ELSE 0 END) AS excellent,
     sum(CASE WHEN f.rating STARTS WITH '○' THEN 1 ELSE 0 END) AS good,
     sum(CASE WHEN f.rating STARTS WITH '△' THEN 1 ELSE 0 END) AS fair,
     sum(CASE WHEN f.rating STARTS WITH '×' THEN 1 ELSE 0 END) AS poor,
     avg(CASE
       WHEN f.rating STARTS WITH '◎' THEN 4.0
       WHEN f.rating STARTS WITH '○' THEN 3.0
       WHEN f.rating STARTS WITH '△' THEN 2.0
       WHEN f.rating STARTS WITH '×' THEN 1.0
       ELSE 0.0
     END) AS avgScore
RETURN COALESCE(sp.name, sp.office_name, sp.corporateName) AS providerName,
       totalFeedbacks,
       excellent, good, fair, poor,
       round(avgScore * 100) / 100 AS avgScore
```

パラメータ:
- `$providerName`: 事業所名（部分一致）

### テンプレート6: 口コミ評価で事業所検索

特定カテゴリの口コミが良い事業所を探す。

```cypher
MATCH (sp:ServiceProvider)-[:HAS_FEEDBACK]->(f:ProviderFeedback)
WHERE f.category = $category
WITH sp,
     count(f) AS feedbackCount,
     avg(CASE
       WHEN f.rating STARTS WITH '◎' THEN 4.0
       WHEN f.rating STARTS WITH '○' THEN 3.0
       WHEN f.rating STARTS WITH '△' THEN 2.0
       WHEN f.rating STARTS WITH '×' THEN 1.0
       ELSE 0.0
     END) AS avgScore,
     collect(f.content)[0..3] AS topExamples
WHERE feedbackCount >= 1
RETURN COALESCE(sp.name, sp.office_name, sp.corporateName) AS providerName,
       COALESCE(sp.serviceType, sp.service_type, '') AS serviceType,
       sp.city AS city,
       COALESCE(sp.availability, '未確認') AS availability,
       feedbackCount,
       round(avgScore * 100) / 100 AS avgScore,
       topExamples
ORDER BY avgScore DESC, feedbackCount DESC
LIMIT $limit
```

パラメータ:
- `$category`: 口コミカテゴリ（行動障害対応/コミュニケーション/環境/送迎/食事/医療連携）
- `$limit`: 取得件数（デフォルト20）

**追加フィルタ**:
- 評価絞り込み: `AND f.rating STARTS WITH '◎'`
- サービス種類: `AND COALESCE(sp.serviceType, sp.service_type, '') CONTAINS $serviceType`
- 地域: `AND sp.city CONTAINS $city`

### ── 書き込み系（write_neo4j_cypher） ──

### テンプレート7: クライアントと事業所の紐付け

```cypher
MERGE (c:Client {name: $clientName})
MERGE (sp:ServiceProvider {name: $providerName})
MERGE (c)-[r:USES_SERVICE]->(sp)
ON CREATE SET
  r.startDate = $startDate,
  r.status = $status,
  r.note = $note
ON MATCH SET
  r.status = $status,
  r.note = $note,
  r.endDate = CASE WHEN $status = 'Ended' THEN toString(date()) ELSE r.endDate END
RETURN c.name AS client, sp.name AS provider, r.status AS status, r.startDate AS startDate
```

パラメータ:
- `$clientName`: クライアント名
- `$providerName`: 事業所名（既存のServiceProvider.nameと完全一致させること）
- `$startDate`: 利用開始日（YYYY-MM-DD、空の場合は事前にdate().toString()をセット）
- `$status`: 利用状況（Active / Pending / Ended、デフォルト: Active）
- `$note`: 備考（任意）

**注意**: MERGE (sp:ServiceProvider {name: $providerName}) で名前完全一致が必要。事前にテンプレート1で正確な名前を確認すること。

### テンプレート8: 口コミ・評価の登録

```cypher
MATCH (sp:ServiceProvider)
WHERE COALESCE(sp.name, sp.office_name, sp.corporateName, '') CONTAINS $providerName
WITH sp LIMIT 1
CREATE (f:ProviderFeedback {
  feedbackId: randomUUID(),
  category: $category,
  content: $content,
  rating: $rating,
  source: $source,
  date: toString(date()),
  isConfirmed: false
})
CREATE (sp)-[:HAS_FEEDBACK]->(f)
RETURN COALESCE(sp.name, sp.office_name, sp.corporateName) AS provider,
       f.feedbackId AS feedbackId,
       f.category AS category,
       f.rating AS rating
```

パラメータ:
- `$providerName`: 事業所名（部分一致で最初の1件にマッチ）
- `$category`: カテゴリ（行動障害対応/コミュニケーション/環境/送迎/食事/医療連携/その他）
- `$content`: 口コミ内容
- `$rating`: 評価（◎良い / ○普通 / △課題あり / ×不可、デフォルト: ○普通）
- `$source`: 情報源（支援者名 or 匿名、デフォルト: 匿名）

### テンプレート9: 事業所の空き状況更新

```cypher
MATCH (sp:ServiceProvider)
WHERE COALESCE(sp.name, sp.office_name, sp.corporateName, '') CONTAINS $providerName
WITH sp LIMIT 1
SET sp.availability = $availability,
    sp.updatedAt = toString(datetime())
WITH sp, $currentUsers AS newUsers
FOREACH (_ IN CASE WHEN newUsers >= 0 THEN [1] ELSE [] END |
  SET sp.currentUsers = newUsers
)
RETURN COALESCE(sp.name, sp.office_name, sp.corporateName) AS provider,
       sp.availability AS availability,
       sp.currentUsers AS currentUsers,
       sp.updatedAt AS updatedAt
```

パラメータ:
- `$providerName`: 事業所名（部分一致で最初の1件にマッチ）
- `$availability`: 空き状況（空きあり / 要相談 / 満員 / 未確認）
- `$currentUsers`: 現在利用者数（-1の場合は更新しない）

## 運用ガイドライン

### 検索のベストプラクティス

1. **名前付きレコードのみ検索**: 最初のWHERE句に `sp.name IS NOT NULL AND sp.name <> ''` を入れる
2. **旧形式も含める場合**: `(sp.name <> '' OR sp.office_name <> '')` に変更
3. **COALESCEを必ず使う**: 表示名とサービス種類は両形式に対応するCOALESCEが必須
4. **空き優先ソート**: availability は null が多いため `COALESCE(sp.availability, '未確認')` でnull安全に
5. **LIMIT必須**: 2621件のデータがあるため必ずLIMITを付ける

### 口コミ評価のカテゴリ

| カテゴリ | 観点 |
|---------|------|
| 行動障害対応 | パニック・他害・自傷等への対応力 |
| コミュニケーション | 意思疎通の工夫、家族との連携 |
| 環境 | 施設設備、衛生、バリアフリー |
| 送迎 | 送迎の柔軟性、時間帯、対応範囲 |
| 食事 | 食事の質、アレルギー対応、嚥下配慮 |
| 医療連携 | 医療機関との連携、服薬管理 |
| その他 | 上記に当てはまらないもの |

### サービス種類一覧（主要なもの）

| サービス種類 | 件数 |
|------------|------|
| 就労継続支援B型 | 494 |
| 生活介護 | 329 |
| 計画相談支援 | 325 |
| 放課後等デイサービス | 299 |
| グループホーム | 174 |
| 共同生活援助 | 167 |
| 重度訪問介護 | 138 |
| 障害児相談支援 | 127 |
| 同行援護 | 88 |

### 注意事項

- **データ混在**: 新形式（camelCase）と旧形式（snake_case）が混在。テンプレートのCOALESCEパターンを必ず使うこと
- **名前なしレコード**: 約1500件は名前が空。検索時は名前のフィルタを入れること
- **availability**: 初期状態では 'または null。運用中にテンプレート9で更新する
- **ProviderFeedback**: 初期状態では0件。運用中にテンプレート8で蓄積する
- **USES_SERVICE**: 初期状態では0件。運用中にテンプレート7で作成する
