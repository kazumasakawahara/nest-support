# nest-support スキーマ正典 — v0.1 案

- 状態：**案**（2026-11-05。N-06。止まる点 2 で河原さんの承認を待つ）
- 根拠：ADR-001（承認 2026-11-05。D1〜D11）、約束 v1（`~/Dev-Work/tsunagu-net/docs/contracts/nest-support-shared.md`。2026-11-04 確定）
- 扱う範囲：個人の側の DB の、ラベル・リレーション・プロパティ・列挙値の**名前と構造**、ID の形、制約。資源の側は tsunagu-net の正典を参照するだけ
- 扱わない範囲：業務上の意味・運用の規則・列挙値の日本語の名前（要るなら別の文書に置く。ADR D1）。機械が読む JSON は N-07 で作り、この表と一致させる（N-08 の乖離の検査）
- 手本：tsunagu-net の正典 v0.29（`docs/SCHEMA.md` §1〜§4。読むだけ）。約束にかかわる名前（確度・情報源・聞いた記録の項目）は tsunagu-net とそろえる。それ以外は nest-support が決める
- 前の正典（`docs/SCHEMA_CONVENTION.md` v3.5。shared-schema の写し）とのつき合わせは §8。前の正典はこの案の承認後、N-09 で外す
- **§9 に、止まる点 2 で決めていただくことをまとめた。** 本文の「推す」はどれも §9 の決定を待つ

## 1. 命名

| 対象 | 形 | 例 |
|---|---|---|
| ラベル | PascalCase | `Client`, `NgAction` |
| リレーション | UPPER_SNAKE_CASE | `MUST_AVOID`, `EVIDENCED_BY` |
| プロパティ | camelCase | `riskLevel`, `birthDate` |
| 列挙値 | 英語の PascalCase | `LifeThreatening`, `Hearsay` |

- 列挙値に日本語の例外を設けない（前の正典の `SupportLog.type`「日常記録」、`Review.source`「母親」などは英語の値にする。§9 論点 1）。日本語は表示の側で付ける
- 自由な文（`situation`・`instruction`・`episode` など）は日本語のまま。列挙値ではない
- 旧い名前の読み替え（`[:MUST_AVOID|PROHIBITED]` など）は持たない。新しい DB は旧い名前を一度も書かない（前の DB を写すかは N-05a で決める）

## 2. DB

| DB | 中身 | 書き込み | 読み取り |
|---|---|---|---|
| 個人の側 | 本人と周りの人・ケアの暗黙知・聞いた記録（要配慮個人情報） | ゲートだけ（D6）。Claude は書かない | 読み取りだけの MCP の包み（N-22。実名・かな・電話・住所・生年月日を既定で返さない） |
| 資源の側 | tsunagu-net の資源 DB の書き出し（公開情報） | 読み込みの道具だけ（N-23） | 読み取りだけの MCP の包み |

- 二つをつなぐのは `orgId`（`ORG-` ＋ ULID）の値だけ。個人の側から資源のノードへ関係を張らない（D3）
- 資源の側の構造は tsunagu-net の正典 §5 のとおりで、ここに写さない。読み込んだ版と指紋（`MANIFEST.json`）を記録する（D2-1）

## 3. ID の形

| 対象 | 形 | 正規表現 |
|---|---|---|
| 個人の側のノード | 接頭辞 ＋ `-` ＋ ULID | `^(CLI|PER|STF|INV|REC|NGA|CPF|CND|WSH|LHS|CRL|CRT|PAS|SLG|REV|AUD)-[0-9A-HJKMNP-TV-Z]{26}$` |
| 機関（資源の側の ID を持つだけ） | `ORG-` ＋ ULID | `^ORG-[0-9A-HJKMNP-TV-Z]{26}$` |
| 表示用の仮名 | `displayCode` | 形は N-10 で決める。実名から作らない |

- ID はゲートが発番する（N-10）。名前から作らない。名前で MERGE しない（D8）
- 個人の側の ID に `ORG-` を使わない。資源 DB に無い機関・個人の医師は `PER`（人）か、`orgId` を空にした関わり（§4.2 `Involvement`）で持つ

| 接頭辞 | ラベル | 接頭辞 | ラベル |
|---|---|---|---|
| `CLI` | Client | `CND` | Condition |
| `PER` | Person | `WSH` | Wish |
| `STF` | Staff | `LHS` | LifeHistory |
| `INV` | Involvement | `CRL` | CareRole |
| `REC` | Record | `CRT` | Certificate |
| `NGA` | NgAction | `PAS` | PublicAssistance |
| `CPF` | CarePreference | `SLG` | SupportLog |
| `REV` | Review | `AUD` | AuditLog |

## 4. 個人の側

### 4.1 共通プロパティ（個人の側のすべてのノード）

| プロパティ | 型 | 必須 | 規則 |
|---|---|---|---|
| `registeredAt` | DateTime | ✅ | 作るときにゲートが付ける。変えない |
| `status` | enum `status` | ✅ | `Active`・`Pending`・`Inactive` |
| `origin` | enum `origin` | ✅ | `Human`・`AiExtracted`・`Imported`。`AiExtracted` は必ず `Pending` で作る（約束 4-5） |

- `Pending` を `Active` にするのは承認の操作だけ（§7）。`Inactive` にするときは理由を AuditLog に残す
- どのノードにも、名前が `embedding` で始まる・終わるプロパティを作らない。ベクトル索引を作らない（D10）

### 4.2 ノード

**人**

| ラベル | プロパティ（必須は ✅） | 説明 |
|---|---|---|
| `Client` | `clientId`✅, `displayCode`✅, `familyName`, `givenName`, `familyNameKana`, `givenNameKana`, `birthDate`(Date), `birthDatePrecision`(enum), `bloodType` | 本人。名前で一意にしない（D8） |
| `Person` | `personId`✅, `familyName`, `givenName`, `familyNameKana`, `givenNameKana`, `phone`, `note` | 本人の周りの人（家族・キーパーソン・個人の後見人・個人の医師・ほかの支援者）。役割はリレーションで表す（§9 論点 2） |
| `Staff` | `staffId`✅, `displayName`✅, `role`✅(enum) | この DB を使う人（相談支援専門員・事業所の職員）。承認と記録の書き手 |

**機関との関わり**

| ラベル | プロパティ（必須は ✅） | 説明 |
|---|---|---|
| `Involvement` | `involvementId`✅, `kind`✅(enum), `orgId`, `startDate`(Date), `endDate`(Date), `howEnded`(enum), `guardianshipType`(enum。kind が Guardianship のときだけ), `serviceTypeName` | 通院先・サービスの利用・後見・行政の窓口など。`orgId` が空なら「機関未確定」（D3）。原文の機関の名前は根拠の `Record.quote` に残り、ここには写さない（§9 論点 3） |

**ケアの暗黙知と本人の事実**（どれも根拠の記録 `Record` につなぐ。§6）

| ラベル | プロパティ（必須は ✅） | 説明 |
|---|---|---|
| `NgAction` | `ngActionId`✅, `action`✅, `riskLevel`✅(enum), `reason`, `validFrom`(Date), `validTo`(Date) | 禁忌。一つのノードにし、聞いた記録ごとに根拠としてつなぐ（D5） |
| `CarePreference` | `carePreferenceId`✅, `category`✅, `instruction`✅, `priority`(enum), `validFrom`(Date), `validTo`(Date) | ケアの好み・推奨ケア。D5 と同じ形にする（§9 論点 4） |
| `Condition` | `conditionId`✅, `name`✅, `diagnosisDate`(Date) | 特性・診断 |
| `Wish` | `wishId`✅, `content`✅ | 本人・家族の願い |
| `LifeHistory` | `lifeHistoryId`✅, `era`, `episode`✅ | 生育歴 |
| `CareRole` | `careRoleId`✅, `name`✅, `frequency`, `priority`(enum), `note` | 親などが担っている役割（親の機能移行） |
| `Certificate` | `certificateId`✅, `type`✅(enum), `grade`, `issuedDate`(Date), `nextRenewalDate`(Date) | 手帳・受給者証 |
| `PublicAssistance` | `publicAssistanceId`✅, `type`✅(enum), `startDate`(Date), `endDate`(Date) | 公的扶助 |
| `SupportLog` | `supportLogId`✅, `date`✅(Date), `situation`✅, `action`, `effectiveness`(enum), `note`, `nextAction` | 支援の記録。書いた人は `Staff`。元の文は `Record` に持つ（§9 論点 5） |

**聞いた記録・確認・監査**

| ラベル | プロパティ（必須は ✅） | 説明 |
|---|---|---|
| `Record` | `recordId`✅, `kind`✅(enum), `text`✅, `quote`✅, `certainty`✅(enum), `informantKind`✅(enum), `sourceHash`✅, `aboutDate`(Date), `heardOn`(Date), `documentHash`, `providerCertainty`(enum), `receivedOn`(Date) | 聞いた記録（D4・D5 の根拠）。誰から・いつ・どの原文で。`certainty`・`text`・`quote`・`informantKind`・`documentHash`・`providerCertainty` は作った後に変えない。`sourceHash` の一致で二重の登録を止める |
| `Review` | `reviewId`✅, `domain`✅(enum), `reviewedAt`✅(DateTime), `informantKind`✅(enum), `note` | 確かめた記録。「確かめた上で 0 件」と「確かめていない」を分ける。追記だけ |
| `AuditLog` | `auditId`✅, `at`✅(DateTime), `action`✅(enum), `targetLabel`✅, `targetId`✅, `requestId`✅, `selfApproval`(Boolean。action が Approve のときだけ) | 監査ログ。追記だけ |

- 人を指すプロパティは ID で持つ。名前で持たない
- `Record.quote` は原文のその箇所をそのまま持つ（約束 4-1）。`text` は事実の言い換え。言い換えに引用に無い数字を足さない（約束 4-2。ゲートが検査する）

### 4.3 リレーション

| リレーション | 始点 → 終点 | プロパティ（必須は ✅） |
|---|---|---|
| `FAMILY_OF` | Person → Client | `kind`✅(enum `relatedKind`), `certainty`✅, `recordIds`✅(List) |
| `HAS_KEY_PERSON` | Client → Person | `rank`✅(Integer), `startDate`✅(Date), `endDate`(Date), `status`✅, `certainty`✅, `recordIds`✅(List) |
| `CONCERNS` | Involvement → Client | — |
| `INVOLVED_IN` | Person → Involvement | `asRole`(enum) |
| `MUST_AVOID` | Client → NgAction | — |
| `REQUIRES` | Client → CarePreference | — |
| `HAS_CONDITION` | Client → Condition | — |
| `IN_CONTEXT` | NgAction → Condition | — |
| `ADDRESSES` | CarePreference → Condition | — |
| `HAS_WISH` | Client → Wish | — |
| `HAS_HISTORY` | Client → LifeHistory | — |
| `HAS_CERTIFICATE` | Client → Certificate | — |
| `RECEIVES` | Client → PublicAssistance | — |
| `PERFORMS` | Person → CareRole | `since`(Date), `until`(Date) |
| `ROLE_FOR` | CareRole → Client | — |
| `CAN_BE_PERFORMED_BY` | CareRole → Person / Involvement | — |
| `EVIDENCED_BY` | （§4.2 の事実のノード）→ Record | `linkedBy`✅(enum `linkedBy`), `at`✅(DateTime) |
| `CONTRADICTS` | Record → （事実のノード） | `claim`✅, `raisedAt`✅(DateTime), `resolvedAt`(DateTime), `resolution`, `resolvedBy` |
| `CONFIRMS` | Review → Record | — |
| `ABOUT` | Record / Review / SupportLog → Client | — |
| `TOLD_BY` | Record → Person / Client | — |
| `RECORDED_BY` | Record / SupportLog / Review → Staff | — |
| `APPROVED` | Staff → （Pending だったノード） | `at`✅(DateTime), `selfApproval`✅(Boolean) |
| `AUDIT_FOR` | AuditLog → （任意のノード） | — |
| `ACTED_BY` | AuditLog → Staff | — |

- `FAMILY_OF`・`HAS_KEY_PERSON` は関係そのものが事実なので、確度と根拠の記録の ID（`recordIds`）を関係に持つ。関係に関係をつなげないため（§9 論点 6）
- 交代・終わりは張り替えない。終わった関係・関わりに `endDate` と `Inactive` を書き、新しく作る（前の正典 §7.10 の考え方を残す）
- `EVIDENCED_BY.linkedBy` は `Gate`（取り込みで新しい事実と一緒に作った）か `Human`（人が既にある事実に結んだ）。既にある事実に結ぶのは人だけ（D5）

### 4.4 制約と索引

- 一意制約：§3 の ID のプロパティすべてと、`Client.displayCode`
- RANGE 索引：`Record.sourceHash`、`Client.familyNameKana`・`Person.familyNameKana`（候補を出すため）、`Client.birthDate`
- Community 版には存在制約が無い。必須の項目はゲートで強制する
- ベクトル索引：作らない（D10）。全文索引：作らない（ADR 未決論点 9 が決まるまで）
- 名前の一意制約（前の `Client.name`）は作らない（D8）

### 4.5 列挙値

| 名前 | 値 |
|---|---|
| `status` | `Active`, `Pending`, `Inactive` |
| `origin` | `Human`, `AiExtracted`, `Imported` |
| `certainty`（約束 3） | `Confirmed`, `Hearsay`, `SelfReport`, `Inference`, `Unspecified` |
| `informantKind`（tsunagu-net と同じ） | `Self`, `Family`, `Agency`, `Neighbor`, `DocumentOnly` |
| `recordKind`（tsunagu-net と同じ） | `Observation`, `Interview`, `Notification`, `MeetingMinutes`, `Plan`, `Document` |
| `riskLevel` | `LifeThreatening`, `Panic`, `Discomfort` |
| `relatedKind`（tsunagu-net と同じ） | `Parent`, `Child`, `Spouse`, `Partner`, `Sibling`, `Grandparent`, `Grandchild`, `OtherRelative` |
| `involvementKind` | `Medical`, `ServiceProvision`, `CaseManagement`, `Consultation`, `Guardianship`, `Education`, `Employment`, `Administrative` |
| `howEnded`（tsunagu-net と同じ） | `Ongoing`, `Lapsed`, `DeclinedByPerson`, `EndedByAgency`, `Unknown` |
| `guardianshipType`（tsunagu-net と同じ） | `Guardianship`, `Curatorship`, `Assistance`。任意後見を足すかは §9 論点 7 |
| `birthDatePrecision`（tsunagu-net と同じ） | `Day`, `Month`, `Year`, `Unknown` |
| `staffRole` | `Staff`, `Administrator` |
| `reviewDomain` | `NgAction`, `CarePreference`, `KeyPerson`, `Guardianship`, `Certificate`, `CareRole`（前の正典の 6 領域。後見は関わりに移したので名前を変えた） |
| `auditAction` | `Create`, `Approve`, `Reject`, `Inactivate`, `LinkEvidence`, `RaiseContradiction`, `ResolveContradiction`, `Read` |
| `linkedBy` | `Gate`, `Human` |
| `effectiveness` | `Effective`, `Ineffective`, `Neutral`, `Unknown` |
| `priority` | `High`, `Medium`, `Low` |
| `certificateType`・`publicAssistanceType`・`asRole` | N-07 で前の正典と前の DB のスキルから集めて決める（この案では値を決めない） |

## 5. 資源の側

- tsunagu-net の正典 §5（v0.29 時点。読み込んだ書き出しの版を記録する）のとおり。nest-support は写しを持たない（約束 1）
- 個人の側が使うのは `Organization.orgId` の値だけ。名前・住所・電話・窓口は、読む道具が `orgId` で資源の側から引く（D2-2・D3）

## 6. 確度と根拠の形（D4・D5）

```
(Client)-[:MUST_AVOID]->(NgAction)-[:EVIDENCED_BY]->(Record)-[:TOLD_BY]->(Person)
                                                   (Record)-[:ABOUT]->(Client)
(Record)-[:CONTRADICTS]->(NgAction)          … 食い違う話は上書きせず保留
(Review)-[:CONFIRMS]->(Record)                … 確かめ直した記録
```

- 確度は `Record.certainty` にだけ持つ。事実のノード（NgAction など）に確度を書かない。事実の強さは、つながる記録の確度から読む道具が計算する（最も強いもの・最も新しいものなど、見せ方は読む側で決める）
- 確度は作った後に変えない。確かめ直したら、新しい `Record`（または `Review` が `CONFIRMS`）を作り、元の記録はそのまま残す（約束 3）
- 情報源は `Record.informantKind`（5 値）と `TOLD_BY`（誰か。分かるときだけ）。確度に混ぜない
- 他の機関から受けた書面は二段：`providerCertainty`（提供元の原文の印）と `certainty`（受けた側から見た確度。提供元より強くしない）。`receivedOn` と `documentHash` を添える（約束 3・tsunagu-net BRS-44 と同じ）
- 「最後に確かめた日」は事実のノードに書き足さない。`EVIDENCED_BY` の先の `Record.heardOn` と、`CONFIRMS` の元の `Review.reviewedAt` から計算する（D4）
- 新しく聞いた話を既にある事実に結ぶのは人だけ（`linkedBy: Human`）。結ばなければ、新しい事実（`Pending`）として入る。似た文の自動の重複検出はしない（D5・D10）

## 7. 承認（D9）

- ゲートが書く事実・関係・記録は、AI 由来なら `Pending`（§4.1）
- 承認は書き込みとは別の操作。`(Staff)-[:APPROVED {at, selfApproval}]->(ノード)` を作り、`status` を `Active` にし、`AuditLog`（`action: Approve`、`selfApproval`）を残す
- 一人で使う人は、自分が取り込んだものを自分で承認してよい。そのときは `selfApproval: true`
- 承認の操作は、そのノードの根拠の `Record.quote` を並べて見せてから行う。AI 由来のノードをまとめて一括で承認しない（一回の操作で一つのノード）
- 却下は `status: Inactive` と `AuditLog`（`action: Reject`）。消さない

## 8. 前の正典（v3.5）とのつき合わせ

| 前の正典 | この案 | 理由 |
|---|---|---|
| `Hospital`・`Organization`・`ServiceProvider`・`ProviderFeedback` | 外す。機関は `Involvement.orgId` | D3。口コミは ADR 未決論点 5 |
| `Doctor` | `Person`（個人の医師）＋ `INVOLVED_IN` で通院の関わりにつなぐ | D3 は「資源 DB に無い個人の医師として残す」とした。ラベルを分けず `Person` に寄せるのを推す（§9 論点 2） |
| `KeyPerson`・`Relative`・`Guardian`（個人）・`Supporter` | `Person` と役割のリレーション（`HAS_KEY_PERSON`・`FAMILY_OF`・`INVOLVED_IN`） | 同じ人（母がキーパーソンで家族）が二つのノードになるのを防ぐ。名前で同定しない（D8） |
| `Guardian`（法人）・`HAS_LEGAL_REP` | `Involvement`（kind `Guardianship`、`orgId`） | D3 |
| `IS_PARENT_OF` | `FAMILY_OF {kind: Parent}` | 関係の種類を一つの名前にまとめた |
| `TREATED_AT`・`HAS_DOCTOR`・`USES_SERVICE`・`REGISTERED_AT`・`SUPPORTED_BY` | `Involvement` と `CONCERNS`・`INVOLVED_IN` | 機関のノードを持たないため（D3） |
| `MeetingRecord` | `Record`（kind `Interview`。音声のファイルの指紋は `documentHash`） | 面談も聞いた記録の一つ。ファイルの置き場所（`filePath`）は持たない（§9 論点 5） |
| `SupportLog.emotion`・`triggerTag`・`context`・`type`・`duration` | この案には入れない | `emotion`・`triggerTag` は ADR 未決論点 7。決まるまで入れない |
| `FOLLOWS`（SupportLog の鎖） | 外す | 日付で並べられる。書き込みのたびに鎖を張り直す処理が要らなくなる |
| `NgAction`・`CarePreference` の `source`・`sourceDetail`・`lastConfirmedAt`・`staleAfter` | `Record` の側へ。`lastConfirmedAt` は計算する | D4・D5 |
| `Review.source`（日本語の値） | `Review.informantKind`（5 値） | 約束 3 の情報源にそろえた |
| `AuditLog` の `user`・`targetName`・`details` | `ACTED_BY`・`targetId`・`requestId` | 名前を監査ログに残さない |
| `Identity`・`HAS_IDENTITY`（仮名化の将来の構想） | 外す | 実名は `Client` に持ち、読む道具が伏せる（N-22） |
| `CONTRADICTS`・`CONFIRMS`・`Review` | 残す（始点・終点を `Record` に寄せた） | 前の正典 v3.4 の考え方（D5） |
| 列挙値の日本語の例外 | 外す | §1 |
| `embedding`・`summaryEmbedding`・`textEmbedding`・ベクトル索引 6 本 | 外す | D10（N-04 でコードから外した） |
| `Client.name` の一意制約・名前の MERGE | 外す | D8 |

## 9. 止まる点 2 で決めていただくこと

計画の止まる点 2（ラベル・関係の名前、D5 を広げる範囲）と、案を書く中で出てきたもの。どれも「推す」を本文に書いてある。

1. **列挙値の日本語の例外をなくすか**：推す＝なくす（§1）。`SupportLog.type`・`Review.source` は英語の値にし、日本語は表示の側で付ける。スキルの表示の書き直し（N-27）が増える
2. **周りの人を `Person` 一つにするか**：推す＝一つにする（家族・キーパーソン・個人の後見人・個人の医師・支援者）。ADR D3 の「`Doctor` は残す」は、ラベルとしてではなく「個人の医師を個人の側で持つ」意味に読み替えることになる。分けたままにする案は、母がキーパーソンでもあるときに二つのノードになり、どちらが同じ人かを人が決める手間が増える
3. **機関との関わりを `Involvement` ノードにするか**：推す＝する（tsunagu-net の `Involvement` と同じ名前と考え方）。機関未確定（`orgId` が空）も同じ形で持てる。別の案は、関係（`TREATED_AT` など）のプロパティに `orgId` を持たせる形だが、関係の終点にする機関のノードが個人の側に要り、D3 の「機関のラベルを外す」と合わない
4. **D5 の形（事実のノード＋聞いた記録）を広げる範囲**：推す＝§4.2 の「ケアの暗黙知と本人の事実」の 9 つすべて（NgAction・CarePreference・Condition・Wish・LifeHistory・CareRole・Certificate・PublicAssistance・SupportLog）。家族の語りから入るものはどれも、確度を持つのは聞いた記録の側になる。NgAction と CarePreference だけにする案は、ほかの事実の確度をどこに持つかを別に決める必要がある
5. **面談記録と支援記録**：推す＝`MeetingRecord` は `Record`（kind `Interview`）にまとめ、音声のファイルの置き場所は DB に持たない（指紋だけ）。`SupportLog` は構造（状況・対応・効果）を持つ事実として残し、元の文は `Record` に持つ
6. **関係そのものが事実のとき（家族・キーパーソン）**：推す＝関係に `certainty` と `recordIds`（根拠の記録の ID の一覧）を持たせる。別の案は、関係をノード（例：`KeyPersonship`）にして `EVIDENCED_BY` でつなぐ形。形はそろうが、照会が一段深くなる
7. **任意後見**：`guardianshipType` に任意後見（例：`VoluntaryGuardianship`）を足すか。tsunagu-net の値は法定後見の 3 つだけ。足すなら nest-support だけの値になる（約束の範囲外なので足してよい）
8. **`Staff` と承認の役割**：推す＝`Staff` の役割は `Staff`・`Administrator` の 2 つ。tsunagu-net の `Approver` は持たない（D9 で一人の人の自己承認を認めたため）
9. **`Record` の項目の名前を tsunagu-net とそろえる範囲**：推す＝約束にかかわる項目（`certainty`・`informantKind`・`quote`・`providerCertainty`・`documentHash`・`receivedOn`・`sourceHash`）は同じ名前にする。tsunagu-net の試験の例（N-11）を写しやすくするため。`heardOn`（いつ聞いたか）は nest-support だけの項目

## 変更履歴

- v0.1 案（2026-11-05）：初版（N-06）。止まる点 2 の前
