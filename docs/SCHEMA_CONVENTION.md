<!-- AUTO-GENERATED COPY — DO NOT EDIT.
  Synced from ~/Dev-Work/shared-schema/SCHEMA_CONVENTION.md
  Edit the master there and run sync-schema.sh. (synced: 20260611-075624) -->

<!--
  ============================================================================
  これは唯一の正典（マスター）です。編集はこのファイル（shared-schema）でのみ行うこと。
  各プロジェクト（neo4j-agno-agent / nest-support / oyagami-local）配下のコピーは
  sync-schema.sh による read-only 同期物であり、直接編集してはなりません。
  実行時に実際に強制力を持つ allowlist の正値は GET /api/narrative/schema を参照。
  ============================================================================
-->

# Neo4j スキーマ命名規則（Naming Convention）— 統一正典 v3.1

> **このドキュメントは、support-db（障害福祉支援DB, port 7687）のノードラベル・リレーションシップタイプ・プロパティ名の唯一の正典（Single Source of Truth）です。**
> すべての LLM（Claude, Gemini, Hermes/その他エージェント）およびすべてのコード（Python, Cypher テンプレート, Skills）は、このドキュメントに従ってください。
>
> **編集ルール**: 本ファイル（`~/Dev-Work/shared-schema/SCHEMA_CONVENTION.md`）が唯一の編集点です。各プロジェクト内のコピーは同期物なので編集しないこと。
> **実行時の権威**: 機械が従う「実際の値」は `GET /api/narrative/schema`（agno バックエンド）が返します。本ドキュメントはその「あるべき仕様」を記述します。両者は常に一致させてください。

---

## 0. 適用範囲と対象DB

- **対象**: 障害福祉支援DB（**port 7687**, コンテナ `support-db-neo4j`）のみ。
- **対象外**: 生活困窮者自立支援DB（旧 port 7688 / `livelihood-support`）は **2026-05 に廃止**。本正典では扱いません。歴史的記録が必要な場合は `nest-support/decommissioned/` および各リポのGit履歴を参照してください。

---

## 1. 命名規則の原則

### 1.1 ノードラベル → **PascalCase**
```
✅ 正: Client, NgAction, CarePreference, KeyPerson, SupportLog
❌ 誤: client, ng_action, care_preference, key_person, support_log
```

### 1.2 リレーションシップタイプ → **UPPER_SNAKE_CASE**
```
✅ 正: MUST_AVOID, HAS_KEY_PERSON, IN_CONTEXT, HAS_CERTIFICATE
❌ 誤: MustAvoid, must_avoid, hasKeyPerson, Has_Key_Person
```

### 1.3 プロパティ名 → **camelCase**
```
✅ 正: bloodType, riskLevel, nextRenewalDate, clientId, displayCode
❌ 誤: blood_type, risk_level, next_renewal_date, client_id, display_code
```

### 1.4 列挙値（Enum Values）→ **PascalCase（英語）**
```
✅ 正: LifeThreatening, Panic, Discomfort, Active, Effective, High, Medium, Low
❌ 誤: life_threatening, PANIC, active, "効果的"
```
> **例外**: `CarePreference.category` と `SupportLog.situation` / `SupportLog.triggerTag` / `SupportLog.context` の値は日本語を許容します（例: 食事, 入浴, パニック時, 大きな音）。ユーザー向け表示と直結するためです。

---

## 2. 書き込み経路と規約準拠の強制力（消費者マップ）

同一の support-db（7687）に対して、現在は複数の入口が読み書きします。**入口ごとに規約の強制力が異なる**ため、弱い経路ほど本ドキュメント＋人間レビューに依存します。

| エントリーポイント | 担当 | 書き込み方式 | 規約準拠の強制力 |
|---|---|---|---|
| **agno `/api/narrative/intake`**（FastAPI） | Python パイプライン | `register_to_database()` ＋ allowlist二重検証・normalize・dedup・embedding・監査 | **強**（コードで固定） |
| **nest `lib/db_operations.py`**（field-ui・multi_importer・scripts） | Python ＋ **Guardian Layer** | `register_to_database()`。書込前に `schema_validator.py` が camelCase変換・廃止リレ補正・列挙値検証 | **強**（コードで固定） |
| **oyagami バックエンド** | FastAPI ＋ Agno(Ollama) | Validator エージェント検証 → 登録 | **強〜中**（検証エージェント依存） |
| **Hermes narrative-intake スキル**（gemini） | gemini → agno API | `/api/narrative/intake` 経由（dryRun→承認→本登録） | **強**（書込はAPI側が保証。スキル自体の準拠は中） |
| **nest Claude Skills**（SKILL.md） | Claude Desktop/Code | neo4j MCP `execute_query` 直接 | **中**（Guardian Layer 非経由・LLM判断＋本規約） |
| **直接 Cypher / 将来エージェント** | 任意のLLM | `execute_query` 直接 | **弱**（本ドキュメントが唯一のガイド） |

> **リスク**: 「中」「弱」の経路が ad-hoc な Cypher を生成すると、命名規則違反のリレーション・プロパティが混入し得ます。本ドキュメントと、後述の正規化／重複防止フレームワークがその防止策です。

---

## 3. 正式なノードラベル一覧（support-db, port 7687）

| ノードラベル | 柱 | 説明 | 主要プロパティ |
|---|---|---|---|
| `Client` | 本人性 | 中心ノード（本人） | name, dob, bloodType, clientId, displayCode, kana, summaryEmbedding |
| `Condition` | ケアの暗黙知 | 特性・医学的診断 | name, diagnosisDate, status |
| `NgAction` | ケアの暗黙知 | 禁忌事項（**最重要**） | action, reason, riskLevel, embedding |
| `CarePreference` | ケアの暗黙知 | 推奨ケア | category, instruction, priority, embedding |
| `KeyPerson` | 危機管理 | キーパーソン・緊急連絡先 | name, relationship, phone, role |
| `Guardian` | 法的基盤 | 成年後見人等 | name, type, phone, organization |
| `Hospital` | 危機管理 | 医療機関 | name, specialty, phone, doctor |
| `Certificate` | 法的基盤 | 手帳・受給者証 | type, grade, nextRenewalDate |
| `PublicAssistance` | 法的基盤 | 公的扶助 | type, grade, startDate |
| `Organization` | 多機関連携 | 関係機関 | name, type, contact, address |
| `Supporter` | 多機関連携 | 支援者 | name, role, organization, phone |
| `SupportLog` | 記録 | 支援記録 | date, situation, action, effectiveness, note, type, duration, nextAction, emotion, triggerTag, context, embedding |
| `MeetingRecord` | 記録 | 音声面談記録 | date, title, duration, filePath, mimeType, transcript, note, embedding, textEmbedding |
| `AuditLog` | 監査 | 監査ログ | timestamp, user, action, targetType, targetName, details |
| `LifeHistory` | 本人性 | 生育歴 | era, episode, emotion |
| `Wish` | 本人性 | 本人・家族の願い | content, status, date |
| `Identity` | 本人性 | 仮名化用個人情報（将来） | name, dob |
| `ServiceProvider` | 多機関連携 | 福祉サービス事業所 | name, corporateName, serviceType, wamnetId |
| `ProviderFeedback` | 多機関連携 | 事業所口コミ | feedbackId, category, content, rating |
| `Relative` | 親の機能移行 | 家族・主たる介護者（親等） | name, relationship, healthStatus, age |
| `CareRole` | 親の機能移行 | 親が担う機能・タスク（食事準備・服薬管理等） | name, frequency, priority, notes |

---

## 4. 正式なリレーションシップタイプ一覧（support-db, port 7687）

| リレーション | 方向 | プロパティ | 説明 |
|---|---|---|---|
| `HAS_CONDITION` | Client → Condition | diagnosedDate, severity | 特性・診断の紐付け |
| `MUST_AVOID` | Client → NgAction | — | **禁忌事項（最重要）** |
| `IN_CONTEXT` | NgAction → Condition | — | 禁忌の文脈（関連特性） |
| `REQUIRES` | Client → CarePreference | — | 推奨ケアの紐付け |
| `ADDRESSES` | CarePreference → Condition | — | ケアが対応する特性 |
| `HAS_KEY_PERSON` | Client → KeyPerson | rank | キーパーソン（rank で優先順位） |
| `HAS_LEGAL_REP` | Client → Guardian | — | 法定代理人 |
| `HAS_CERTIFICATE` | Client → Certificate | issuedDate, status | 手帳・受給者証 |
| `RECEIVES` | Client → PublicAssistance | — | 公的扶助の受給 |
| `REGISTERED_AT` | Client → Organization | — | 関係機関への登録 |
| `TREATED_AT` | Client → Hospital | since, status | 通院先 |
| `SUPPORTED_BY` | Client → Supporter | since, until | 支援者の紐付け |
| `LOGGED` | Supporter → SupportLog | — | 支援記録の作成 |
| `RECORDED` | Supporter → MeetingRecord | — | 面談記録の作成（音声） |
| `ABOUT` | SupportLog/MeetingRecord → Client | — | 記録の対象者 |
| `FOLLOWS` | SupportLog → SupportLog | — | 時系列チェーン（新→旧） |
| `AUDIT_FOR` | AuditLog → Client | — | 監査ログの対象クライアント |
| `HAS_HISTORY` | Client → LifeHistory | — | 生育歴 |
| `HAS_WISH` | Client → Wish | — | 願い |
| `HAS_IDENTITY` | Client → Identity | — | 仮名化対応（将来） |
| `USES_SERVICE` | Client → ServiceProvider | startDate, endDate, status | サービス利用 |
| `HAS_FEEDBACK` | ServiceProvider → ProviderFeedback | — | 口コミ |
| `WROTE` | Supporter → ProviderFeedback | — | 口コミ作成者 |
| `IS_PARENT_OF` | Relative → Client | — | 親子関係（親→本人） |
| `FAMILY_OF` | Relative → Client | — | 親以外の家族関係 |
| `PERFORMS` | Relative → CareRole | — | 家族が担っている役割（第5の柱） |
| `CAN_BE_PERFORMED_BY` | CareRole → ServiceProvider / Supporter / KeyPerson | — | 役割の代替手段（レジリエンス診断用） |

---

## 5. 廃止されたリレーション名（書き込み禁止）

| 廃止名 | 正式名 | 備考 |
|---|---|---|
| ~~`PROHIBITED`~~ | `MUST_AVOID` | DBに旧名が残存している可能性あり |
| ~~`PREFERS`~~ | `REQUIRES` | 同上 |
| ~~`EMERGENCY_CONTACT`~~ | `HAS_KEY_PERSON` | 同上 |
| ~~`RELATES_TO`~~ | `IN_CONTEXT` | NgAction → Condition の文脈紐付け |
| ~~`HAS_GUARDIAN`~~ | `HAS_LEGAL_REP` | 後見人リレーション |
| ~~`HOLDS`~~ | `HAS_CERTIFICATE` | 手帳リレーション |

### 読み取りクエリでの後方互換性
旧名でデータが残存している可能性があるため、**読み取り**クエリでは新旧両方を対象に：
```cypher
-- 読み取り時: 新旧両方にマッチ（推奨）
MATCH (c:Client)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)
MATCH (c:Client)-[:REQUIRES|PREFERS]->(cp:CarePreference)
MATCH (c:Client)-[:HAS_KEY_PERSON|EMERGENCY_CONTACT]->(kp:KeyPerson)
MATCH (ng:NgAction)-[:IN_CONTEXT|RELATES_TO]->(cond:Condition)

-- 書き込み時: 正式名のみ使用（厳守）
CREATE (c)-[:MUST_AVOID]->(ng)   // ✅
CREATE (c)-[:PROHIBITED]->(ng)   // ❌ 使用禁止
```

---

## 6. プロパティ命名の詳細規則

### 6.1 共通プロパティ
| プロパティ | 型 | 説明 | 例 |
|---|---|---|---|
| `name` | String | 名称 | "山田太郎" |
| `dob` | Date | 生年月日 | date("1990-01-15") |
| `status` | String | 状態 | "Active" |
| `date` | Date | 記録日 | date("2025-12-01") |

### 6.2 日付型プロパティの命名パターン
```
単一の日付: date, dob
特定用途: issueDate, startDate, endDate, diagnosisDate
更新・期限: nextRenewalDate, updatedAt
タイムスタンプ: timestamp (AuditLog用)
```

### 6.3 ID系プロパティ
```
clientId → Client の一意識別子 / displayCode → 表示用コード
wamnetId → WAM NET 連携用ID / feedbackId → 口コミの一意識別子
```

### 6.4 ServiceProvider のプロパティ統一
WAM NET インポート時期によりレガシーの snake_case が残存。**新規作成時は camelCase のみ**。
| 正式名（camelCase） | レガシー名（snake_case） | 読み取り対応 |
|---|---|---|
| `name` | `office_name` | COALESCE(sp.name, sp.office_name) |
| `corporateName` | `corp_name` | COALESCE(sp.corporateName, sp.corp_name) |
| `serviceType` | `service_type` | COALESCE(sp.serviceType, sp.service_type) |
| `wamnetId` | `office_number` | COALESCE(sp.wamnetId, sp.office_number) |
| `closedDays` | `closed_days` | COALESCE(sp.closedDays, sp.closed_days) |
| `hoursWeekday` | `hours_weekday` | COALESCE(sp.hoursWeekday, sp.hours_weekday) |
| `updatedAt` | `updated_at` | COALESCE(sp.updatedAt, sp.updated_at) |

---

## 7. 列挙値（Enum）

### 7.1 NgAction.riskLevel（優先度順）
| 値 | 意味 | 説明 |
|---|---|---|
| `LifeThreatening` | 生命に関わる | アレルギー、誤嚥リスク等 |
| `Panic` | パニック誘発 | 大きな音、特定の状況等 |
| `Discomfort` | 不快・ストレス | 嫌がる行為、苦手な環境等 |

### 7.2 SupportLog.effectiveness
`Effective` / `Ineffective` / `Neutral` / `Unknown`

### 7.3 SupportLog.type
| 値 | 意味 |
|---|---|
| `日常記録` | 日常の支援記録（デフォルト） |
| `インシデント` | 事故・トラブル等 |
| `会議` | ケース会議記録 |
| `引き継ぎ` | 担当交代時の申し送り |

### 7.4 SupportLog.emotion（感情・insight-agent / field-ui が使用）
`Joy` / `Anger` / `Sadness` / `Fear` / `Surprise` / `Disgust` / `Calm` / `Anxiety` / `Confusion` / `Neutral`

- テキストから本人の感情状態を読み取り、最も近い値を選択する。明確でない場合は `Neutral`。
- **負の感情**（insight-agent のリスク分析対象）: `Anger`, `Sadness`, `Fear`, `Disgust`, `Anxiety`

### 7.5 SupportLog.triggerTag / context（日本語許容・自由値）
- `triggerTag`: 出来事の引き金を短い日本語タグで表現（例: 大きな音, 環境変化, 人間関係, 体調不良, スケジュール変更, 感覚過敏）
- `context`: 出来事の背景の自由記述（例: 「昼食時、外で工事が始まった」）

---

## 8. インデックスと制約

### 8.1 UNIQUE 制約
| 制約名 | ノード | プロパティ | 備考 |
|---|---|---|---|
| `constraint_client_name_unique` | Client | name | 自動的にRANGEインデックスを含む |

> Community Edition は複合 NODE KEY 非対応のため、`Client(name + dob)` の複合一意性はアプリ層（`validate_client_uniqueness()`）で検証。NOT NULL 制約も非対応のためアプリ層で必須チェック（`Client.name`, `Client.dob`, `SupportLog.date`）。

### 8.2 RANGE インデックス
`idx_hospital_name`, `idx_supporter_name`, `idx_keyperson_name`, `idx_condition_name`,
`idx_ngaction_risklevel`, `idx_carepreference_category`, `supportlog_date`, `idx_supportlog_type`,
`certificate_renewal`, `auditlog_timestamp`, `idx_auditlog_clientname`, `idx_auditlog_user`,
`supportlog_sourcehash_idx`, `meetingrecord_sourcehash_idx`, `lifehistory_sourcehash_idx`, `wish_sourcehash_idx`

### 8.3 VECTOR インデックス（Gemini Embedding 2, 768次元, cosine）
| インデックス名 | ノード | プロパティ |
|---|---|---|
| `support_log_embedding` | SupportLog | embedding |
| `care_preference_embedding` | CarePreference | embedding |
| `ng_action_embedding` | NgAction | embedding |
| `client_summary_embedding` | Client | summaryEmbedding |
| `meeting_record_embedding` | MeetingRecord | embedding |
| `meeting_record_text_embedding` | MeetingRecord | textEmbedding |

> ベクトルは `db.create.setNodeVectorProperty()` で設定（通常の `SET` ではインデックスに認識されない）。バックフィルは各プロジェクトの `scripts/backfill_embeddings.py --all`。

### 8.4 FULLTEXT インデックス
| インデックス名 | ノード | プロパティ |
|---|---|---|
| `idx_supportlog_fulltext` | SupportLog | situation, action, note |
| `idx_lifehistory_fulltext` | LifeHistory | episode |

---

## 9. Guardian Layer（書き込み時バリデーション）

nest-support 系の Python 書き込み経路では、`lib/schema_validator.py`（**Guardian Layer**）が `register_to_database()` の前段で自動補正・検証を行う。

- **camelCase 自動変換**: snake_case プロパティを camelCase に補正
- **廃止リレーション補正**: `PROHIBITED→MUST_AVOID` 等を正式名へ自動置換
- **列挙値検証**: `riskLevel` / `effectiveness` / `status` の値域チェック

> Guardian Layer は Python 経路（field-ui・multi_importer・scripts）には効くが、**Claude Skills の neo4j MCP 直叩きには効かない**（§2 の「中」経路）。Skills 経由の書き込みは本ドキュメント遵守が頼り。

---

## 10. 正規化・重複防止フレームワーク（agno バックエンドが実装）

`/api/narrative/intake` を含む agno の Python パイプラインが、登録前に以下を自動実行する。Hermes の narrative-intake スキルもこの恩恵を受ける。

### 10.1 テキスト正規化（MERGE 前処理）
| ラベル | 正規化方式 | 例 |
|---|---|---|
| Client | `normalize_name()` ＋ `name_to_kana()`（kana 自動生成） | "田中太郎" → name="田中太郎", kana="たなかたろう" |
| Supporter/KeyPerson/Guardian/Hospital/Organization/ServiceProvider | `normalize_name()`: NFC ＋ 全角→半角 ＋ 空白正規化 ＋ 敬称除去 | "田中太郎さん" → "田中太郎" |
| Condition | `normalize_condition()`: 上記 ＋ 医学用語エイリアス解決 | "ASD" → "自閉症スペクトラム障害" |
| NgAction/CarePreference/Certificate 等 | `normalize_text()`: NFC ＋ 全角→半角 ＋ 空白正規化 | "  大きな　音  " → "大きな 音" |

### 10.2 sourceHash 冪等性
`SupportLog`/`MeetingRecord`/`LifeHistory`/`Wish` は CREATE 時に `sourceHash`(SHA256) を自動生成。同一プロパティから決定的に同じハッシュ → 重複登録をスキップ。`AuditLog`/`PublicAssistance` は除外。

### 10.3 MERGE キー戦略
- **Certificate**: 複合キー `["type","grade"]`（療育手帳A と B は別ノード。grade 未指定は "不明"）
- **ServiceProvider**: `wamnetId` があれば優先 MERGE（名前の表記揺れに強い）。なければ `name` でフォールバック。

### 10.4 セマンティック重複検出
既存ベクトルインデックスで意味的に類似するノードを検出（「大きな音」と「騒音」等）。
- **NgAction**: 閾値 0.85 で **409 ブロッキング**（安全に直結するため `confirmDuplicates:true` での確認必須）
- **CarePreference**: 閾値 0.85 で **警告のみ**

### 10.5 読み仮名（kana）ファジーマッチ
Client/KeyPerson/Supporter/Guardian の kana を `SequenceMatcher` で比較（閾値 0.8）。同音異字の重複（「田中」と「多中」）を検出。

### 10.6 登録前重複チェック API
`POST /api/dedup/check` が ①完全一致 ②kana ファジー ③セマンティック類似 の3段でチェック。

### 10.7 医学用語エイリアス（`CONDITION_ALIASES`）
| 正式名 | エイリアス |
|---|---|
| 自閉症スペクトラム障害 | ASD, 自閉スペクトラム, 自閉症, アスペルガー症候群, PDD 等 |
| 注意欠如多動症 | ADHD, ADD, 注意欠陥多動性障害 等 |
| 知的障害 | 知的発達症, 精神遅滞 等 |
| てんかん | 癲癇, epilepsy |
| ダウン症候群 | ダウン症, 21トリソミー |
| 脳性麻痺 | CP, 脳性まひ |

### 10.8 重複検出・マージツール
`scripts/detect_merge_duplicates.py --scan / --merge --label <Label> [--dry-run]`

---

## 11. LLM・エージェント向けガイドライン

### 11.1 Cypher 書き込み時の必須チェックリスト
1. ノードラベルは PascalCase か（`Client` ✅ / `client` ❌）
2. リレーションは UPPER_SNAKE_CASE か（`MUST_AVOID` ✅）
3. リレーション名は正式名か（`MUST_AVOID` ✅ / `PROHIBITED` ❌）
4. プロパティは camelCase か（`riskLevel` ✅ / `risk_level` ❌）
5. `$param` でパラメータ化しているか（インジェクション対策）
6. 重複防止が必要なノードに `MERGE` を使っているか
7. 書き込みを `AuditLog` に記録しているか
8. **実行時の allowlist 正値は `GET /api/narrative/schema` で確認したか**

### 11.2 新しいラベル・リレーションを追加する場合
1. **本マスター（shared-schema）に追記** → 2. 命名規則に従う → 3. 関連 SKILL.md / プロンプトを更新 → 4. `lib/db_operations.py`（および allowlist）に対応を追加 → 5. `sync-schema.sh` で各リポへ反映

### 11.3 No Fabrication
データ欠損時に情報を補完・推測してはならない。推測を述べる場合は必ず推測である旨を明記する。

---

## 12. マイグレーション（参考）

### 12.1 旧リレーションの完全移行
```cypher
// バックアップ取得後に実行
MATCH (c:Client)-[old:PROHIBITED]->(ng:NgAction)
WHERE NOT (c)-[:MUST_AVOID]->(ng) CREATE (c)-[:MUST_AVOID]->(ng) DELETE old;
MATCH (c:Client)-[old:PREFERS]->(cp:CarePreference)
WHERE NOT (c)-[:REQUIRES]->(cp) CREATE (c)-[:REQUIRES]->(cp) DELETE old;
MATCH (c:Client)-[old:EMERGENCY_CONTACT]->(kp:KeyPerson)
WHERE NOT (c)-[:HAS_KEY_PERSON]->(kp)
CREATE (c)-[r:HAS_KEY_PERSON]->(kp) SET r.rank = COALESCE(old.rank, 99) DELETE old;
MATCH (ng:NgAction)-[old:RELATES_TO]->(cond:Condition)
WHERE NOT (ng)-[:IN_CONTEXT]->(cond) CREATE (ng)-[:IN_CONTEXT]->(cond) DELETE old;
// 確認（0件なら完了）
MATCH ()-[r:PROHIBITED|PREFERS|EMERGENCY_CONTACT|RELATES_TO]->()
RETURN type(r) AS oldRelation, count(r) AS remaining;
```

### 12.2 ServiceProvider プロパティ統一
```cypher
MATCH (sp:ServiceProvider)
WHERE sp.office_name IS NOT NULL AND sp.name IS NULL
SET sp.name=sp.office_name, sp.corporateName=sp.corp_name, sp.serviceType=sp.service_type,
    sp.wamnetId=sp.office_number, sp.closedDays=sp.closed_days,
    sp.hoursWeekday=sp.hours_weekday, sp.updatedAt=sp.updated_at
REMOVE sp.office_name, sp.corp_name, sp.service_type, sp.office_number,
       sp.closed_days, sp.hours_weekday, sp.updated_at;
```

---

## 変更履歴

| 日付 | バージョン | 変更内容 |
|---|---|---|
| 2026-06-11 | **v3.1** | **既使用スキーマの正典追記**。(1) 第5の柱（親の機能移行）の `Relative` / `CareRole` ノードと `IS_PARENT_OF` / `FAMILY_OF` / `PERFORMS` / `CAN_BE_PERFORMED_BY` リレーションを §3/§4 に追加（resilience-checker / onboarding-wizard / data-quality-agent が使用中）、(2) `SupportLog.emotion / triggerTag / context` を §3/§7 に追加（insight-agent / field-ui / EXTRACTION_PROMPT が使用中）、(3) §1.4 の日本語許容例外に triggerTag / context を追記 |
| 2026-06-06 | **v3.0** | **統一正典化**。neo4j-agno-agent 版（v2.6）をベースに、(1) 7688/生活保護DBを全削除し7687専用に、(2) nest の Guardian Layer 記述を §9 に統合、(3) §2 を4経路＋将来エージェントの「強制力マップ」に刷新、(4) 実行時の権威=`/api/narrative/schema` を明記、(5) shared-schema をマスターとする編集ルール・同期前提を冒頭に追加 |
| 2026-04-14 | v2.6 | 根本的重複防止（全書込パス正規化統一・NgAction確認付きブロッキング・重複検出マージツール） |
| 2026-04-14 | v2.3–2.5 | 正規化・Conditionエイリアス・sourceHash・セマンティック重複検出・kanaファジー・登録前重複チェックAPI |
| 2026-03-12 | v2.1–2.2 | ベクトルインデックス（Gemini Embedding 2, 768次元）、MeetingRecord/RECORDED 追加 |
| 2026-03-09 | v2.0 | インデックス13本・UNIQUE制約・AUDIT_FOR/FOLLOWS・SupportLog拡張・全文検索 |
| 2026-02-16 | v1.0 | 初版 |
