# nest-support スキーマ正典 — v0.3

- 状態：v0.3（2026-11-05。止まる点 2 の河原さんの判断（§9）と、その後の G-38〜G-41 の判断（§9 の 10〜12）を反映した）
- 根拠：ADR-001（承認 2026-11-05。D1〜D11。D3 は 2026-11-05 に 2 回改めた）、約束 v1（`~/Dev-Work/tsunagu-net/docs/contracts/nest-support-shared.md`。2026-11-04 確定）
- 扱う範囲：個人の側の DB の、ラベル・リレーション・プロパティ・列挙値の**名前と構造**、ID の形、制約。資源の側は tsunagu-net の正典を参照するだけ
- 扱わない範囲：業務上の意味・運用の規則・列挙値の日本語の表示名（nest-support の意味の文書 `docs/SEMANTICS.md` に置く。まだ無い。ADR D1）。機械が読む JSON は N-07 で §11 に置き、この表と一致させる（N-08 の乖離の検査）
- 手本：tsunagu-net の正典 v0.29（`docs/SCHEMA.md` §1〜§4。読むだけ）。そろえた名前とそろえなかった名前は §10
- 前の正典（`docs/SCHEMA_CONVENTION.md` v3.5。shared-schema の写し）とのつき合わせは §8。前の正典は N-09 で外す

## 1. 命名

| 対象 | 形 | 例 |
|---|---|---|
| ラベル | PascalCase | `Client`, `NgAction` |
| リレーション | UPPER_SNAKE_CASE | `MUST_AVOID`, `EVIDENCED_BY` |
| プロパティ | camelCase | `riskLevel`, `birthDate` |
| 列挙値 | 英語の PascalCase | `LifeThreatening`, `Hearsay` |

- 例外は設けない。前の正典の日本語の列挙値の例外（`SupportLog.type`「日常記録」、`Review.source`「母親」など）は引き継がない（tsunagu-net の正典 §1 と同じ）。日本語の表示名は `docs/SEMANTICS.md` で持つ
- 自由な文（`situation`・`instruction`・`episode` など）は日本語のまま。列挙値ではない
- 旧い名前の読み替え（`[:MUST_AVOID|PROHIBITED]` など）は持たない。新しい DB は旧い名前を一度も書かない（前の DB を写すかは N-05a で決める）

## 2. DB

| DB | 中身 | 書き込み | 読み取り |
|---|---|---|---|
| 個人の側 | 本人と周りの人・ケアの暗黙知・聞いた記録（要配慮個人情報） | ゲートだけ（D6）。Claude は書かない | 読み取りだけの MCP の包み（N-22。実名・かな・電話・住所・生年月日を既定で返さない） |
| 資源の側 | tsunagu-net の資源 DB の書き出し（公開情報） | 読み込みの道具だけ（N-23） | 読み取りだけの MCP の包み |

- 二つをつなぐのは `orgId`（`ORG-` ＋ ULID）の値だけ。個人の側から資源のノードへ関係を張らない（D3）
- 個人の側の機関のノード `Organization` は `orgId` と `linkedAt` だけを持つ。名前・住所・種類などの機関の属性は置かず、資源の側から引く（ADR D3 の 2 回目の改め 2026-11-05）
- 資源の側の構造は tsunagu-net の正典 §5 のとおりで、ここに写さない。読み込んだ版と指紋（`MANIFEST.json`）を記録する（D2-1）

## 3. ID の形

| 対象 | 形 | 正規表現 |
|---|---|---|
| 個人の側のノード | 接頭辞 ＋ `-` ＋ ULID | `^(CLI|PER|STF|INV|REC|NGA|CPF|CND|WSH|LHS|CRL|CRT|PAS|SLG|REV|AUD)-[0-9A-HJKMNP-TV-Z]{26}$` |
| Organization（資源の側の ID。個人の側では発番しない） | `ORG-` ＋ ULID | `^ORG-[0-9A-HJKMNP-TV-Z]{26}$` |
| 表示用の仮名 | `displayCode` | 形は N-10 で決める。実名から作らない |

- ID はゲートが発番する（N-10）。名前から作らない。名前で MERGE しない（D8）
- 個人の側で発番する ID に `ORG-` を使わない。`Organization.orgId` は資源の側の ID をそのまま持つ。資源 DB に無い機関は `Organization` を作らず、関わり（§4.2 `Involvement`）だけを持つ（機関未確定）。個人の医師などは `Person`

接頭辞と tsunagu-net の正典 v0.29 §3 とのつき合わせ（2026-11-05 河原さんの指示）：

| 接頭辞 | nest-support のラベル | tsunagu-net | 判定 |
|---|---|---|---|
| `PER` | Person（本人の周りの人） | Person（ケースにかかわる人。対象者を含む） | 同じ接頭辞・同じラベル。nest-support では本人を `Client` に分けたので、`Person` は周りの人だけ |
| `STF` | Staff | Staff | 同じ意味 |
| `INV` | Involvement | Involvement | 同じ意味（§4.2。持つ項目の違いは §10） |
| `REC` | Record | Record | 同じ意味（§10） |
| `REV` | Review | Review | 同じ意味 |
| `AUD` | AuditLog | AuditLog | 同じ意味 |
| `CLI` | Client | — | nest-support だけ。tsunagu-net の接頭辞と重ならない |
| `NGA`・`CPF`・`CND`・`WSH`・`LHS`・`CRL`・`CRT`・`PAS`・`SLG` | NgAction・CarePreference・Condition・Wish・LifeHistory・CareRole・Certificate・PublicAssistance・SupportLog | — | nest-support だけ。重ならない |
| — | — | `HH`・`MTG`・`DSC`・`COR`・`SUP`・`ONT`・`ITV`・`OUT`・`DST`・`CLS`・`RTD`・`RUN`・`PRP`・`ONM` | nest-support では使わない。同じ文字列を別の意味で使わない |
| `ORG` | Organization | Organization | 同じ意味・同じ形（`orgId`・`linkedAt` だけ）。資源の側の ID を持つ |

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
| `Person` | `personId`✅, `familyName`, `givenName`, `familyNameKana`, `givenNameKana`, `phone`, `note` | 本人の周りの人（家族・キーパーソン・主治医・近隣・ヘルパー・個人の後見人など）。本人との関係は `RELATED_TO.kind`（§4.3）。ADR D3 の改め（2026-11-05）で `Doctor` のラベルを外し、ここに寄せた |
| `Staff` | `staffId`✅, `displayName`✅, `role`✅(enum) | この DB を使う人（相談支援専門員・事業所の職員）。承認と記録の書き手 |

**機関と、機関との関わり**

| ラベル | プロパティ（必須は ✅） | 説明 |
|---|---|---|
| `Organization` | `orgId`✅, `linkedAt`✅(DateTime) | 資源の側の機関の ID を持つだけのノード（tsunagu-net と同じ形）。`orgId` で MERGE する（ID だけなので名前の一致にならない）。名前・住所・電話・種類は持たない（D3） |
| `Involvement` | `involvementId`✅, `kind`✅(enum), `howEnded`✅(enum), `certainty`✅(enum。作った後は変えない), `startDate`(Date), `endDate`(Date), `guardianshipType`(enum。kind が Guardianship のときだけ), `serviceTypeName` | 通院先・サービスの利用・後見・行政の窓口など（tsunagu-net の `Involvement` と同じ形）。機関は `(Organization)-[:HAS_INVOLVEMENT]->` で指す。その辺が無ければ「機関未確定」（D3）。原文の機関の名前は根拠の `Record.quote` に残り、ここには写さない。医療機関は `kind: Medical` |

**ケアの暗黙知と本人の事実**（どれも根拠の記録 `Record` に `EVIDENCED_BY` でつなぐ。§6）

| ラベル | プロパティ（必須は ✅） | 説明 |
|---|---|---|
| `NgAction` | `ngActionId`✅, `action`✅, `riskLevel`✅(enum), `reason`, `validFrom`(Date), `validTo`(Date) | 禁忌。一つのノードにし、聞いた記録ごとに根拠としてつなぐ（D5） |
| `CarePreference` | `carePreferenceId`✅, `category`✅, `instruction`✅, `priority`(enum), `validFrom`(Date), `validTo`(Date) | ケアの好み・推奨ケア |
| `Condition` | `conditionId`✅, `name`✅, `diagnosisDate`(Date) | 特性・診断 |
| `Wish` | `wishId`✅, `content`✅ | 本人・家族の願い |
| `LifeHistory` | `lifeHistoryId`✅, `era`, `episode`✅ | 生育歴 |
| `CareRole` | `careRoleId`✅, `name`✅, `frequency`, `priority`(enum), `note` | 親などが担っている役割（親の機能移行） |
| `Certificate` | `certificateId`✅, `type`✅(enum), `grade`, `issuedDate`(Date), `nextRenewalDate`(Date) | 手帳・受給者証 |
| `PublicAssistance` | `publicAssistanceId`✅, `type`✅(enum), `startDate`(Date), `endDate`(Date) | 公的扶助・年金・手当 |
| `SupportLog` | `supportLogId`✅, `date`✅(Date), `situation`✅, `action`, `effectiveness`(enum), `note`, `nextAction` | 支援の記録。構造（状況・対応・効果）を持つ事実。書いた人は `Staff`。元の文は `Record` に持つ |

**聞いた記録・確認・監査**

| ラベル | プロパティ（必須は ✅） | 説明 |
|---|---|---|
| `Record` | `recordId`✅, `kind`✅(enum), `text`✅, `quote`✅, `certainty`✅(enum), `informantKind`✅(enum), `sourceHash`✅, `aboutDate`(Date), `heardOn`(Date), `documentHash`, `providerCertainty`(enum), `receivedOn`(Date) | 聞いた記録（D4・D5 の根拠）。項目は tsunagu-net の `Record` とすべて同じ名前（§10）。面談は `kind: Interview`。`certainty`・`text`・`quote`・`informantKind`・`documentHash`・`providerCertainty` は作った後に変えない。`sourceHash` の一致で二重の登録を止める |
| `Review` | `reviewId`✅, `domain`✅(enum), `reviewedAt`✅(DateTime), `informantKind`✅(enum), `note` | 確かめた記録。「確かめた上で 0 件」と「確かめていない」を分ける。追記だけ |
| `AuditLog` | `auditId`✅, `at`✅(DateTime), `action`✅(enum), `targetLabel`✅, `targetId`✅, `requestId`✅, `selfApproval`(Boolean。action が Approve のときだけ) | 監査ログ。追記だけ。行った人は `ACTED_BY` で `Staff` の ID を指し、名前を残さない |

- 人を指すプロパティは ID で持つ。名前で持たない
- `Record.quote` は原文のその箇所をそのまま持つ（約束 4-1）。`text` は事実の言い換え。言い換えに引用に無い数字を足さない（約束 4-2。ゲートが検査する）
- 音声のファイルの置き場所・保存の期間は DB に持たない。運用の文書に書く（計画 N-29）。音声の指紋は `Record.documentHash`

### 4.3 リレーション

| リレーション | 始点 → 終点 | プロパティ（必須は ✅） |
|---|---|---|
| `RELATED_TO` | Person → Client | `kind`✅(enum `clientRelationKind`), `certainty`✅, `evidenceRecordIds`✅(List), `status`✅, `rank`(Integer。kind が KeyPerson のときは必須), `since`(Date), `until`(Date) |
| `HAS_INVOLVEMENT` | Organization / Person → Involvement | — |
| `CONCERNS` | Involvement → Client | — |
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
| `EVIDENCED_BY` | （§4.2 の事実のノード 9 つと Involvement）→ Record | `linkedBy`✅(enum), `at`✅(DateTime) |
| `CONTRADICTS` | Record → （事実のノード 9 つと Involvement） | `claim`✅, `raisedAt`✅(DateTime), `resolvedAt`(DateTime), `resolution`, `resolvedBy` |
| `CONFIRMS` | Review → Record | — |
| `ABOUT` | Record / Review / SupportLog → Client | — |
| `TOLD_BY` | Record → Person / Client | — |
| `PROVIDED_BY` | Record → Organization | — |
| `AUTHORED_BY` | Record / SupportLog → Staff | — |
| `REVIEWED` | Staff → Review | — |
| `APPROVED` | Staff → （Pending だったノード） | `at`✅(DateTime), `selfApproval`✅(Boolean) |
| `AUDIT_FOR` | AuditLog → （任意のノード） | — |
| `ACTED_BY` | AuditLog → Staff | — |

- `RELATED_TO` の向きは「始点の人が、本人の〈kind〉である」。例：`(母)-[:RELATED_TO {kind: Parent}]->(本人)`。同じ人が家族でキーパーソンでもあるときは、`kind` ごとに一本ずつ張る（同じ `Person` のまま。D8）
- `RELATED_TO` は関係そのものが事実なので、確度（`certainty`。作った後は変えない）と根拠の記録の ID の一覧（`evidenceRecordIds`）を関係に持つ。確かめ直したら、新しい `Record` の ID を一覧に足す。一覧から消さない（関係に関係をつなげないため。§9 の 6）
- 交代・終わりは張り替えない。終わった関係・関わりに `until`・`endDate` と `Inactive` を書き、新しく作る（前の正典 §7.10 の考え方を残す）
- `EVIDENCED_BY.linkedBy` は `Gate`（取り込みで新しい事実と一緒に作った）か `Human`（人が既にある事実に結んだ）。既にある事実に結ぶのは人だけ（D5）
- 資源 DB に無い個人の主治医は `Person` と `RELATED_TO {kind: PrimaryDoctor}`。医療機関は `(Organization)-[:HAS_INVOLVEMENT]->(Involvement {kind: Medical})`。医師をその関わりにつなぐときは `(Person)-[:HAS_INVOLVEMENT]->`
- `PROVIDED_BY` は、その記録をどの機関から受け取ったか（書面・連絡）。`providerCertainty`（二段の確度の提供元の側）と、第三者から受けた情報の管理を辺で辿るため

### 4.4 制約と索引

- 一意制約：§3 の ID のプロパティすべて（`Organization.orgId` を含む）と、`Client.displayCode`
- RANGE 索引：`Record.sourceHash`、`Client.familyNameKana`・`Person.familyNameKana`（候補を出すため）、`Client.birthDate`
- Community 版には存在制約が無い。必須の項目と、条件つきの必須（`RELATED_TO.rank`・`Involvement.guardianshipType`・`AuditLog.selfApproval`）はゲートで強制する
- ベクトル索引：作らない（D10）。全文索引：作らない（ADR 未決論点 9 が決まるまで）
- 名前の一意制約（前の `Client.name`）は作らない（D8）

### 4.5 列挙値

| 名前 | 値 |
|---|---|
| `status` | `Active`, `Pending`, `Inactive` |
| `origin` | `Human`, `AiExtracted`, `Imported` |
| `certainty`（約束 3。tsunagu-net と同じ） | `Confirmed`, `Hearsay`, `SelfReport`, `Inference`, `Unspecified` |
| `informantKind`（tsunagu-net と同じ） | `Self`, `Family`, `Agency`, `Neighbor`, `DocumentOnly` |
| `recordKind`（tsunagu-net と同じ） | `Observation`, `Interview`, `Notification`, `MeetingMinutes`, `Plan`, `Document` |
| `riskLevel` | `LifeThreatening`, `Panic`, `Discomfort` |
| `clientRelationKind`（nest-support だけ） | `Parent`, `Child`, `Spouse`, `Partner`, `Sibling`, `Grandparent`, `Grandchild`, `OtherRelative`, `KeyPerson`, `PrimaryDoctor`, `Neighbor`, `Helper`, `OtherSupporter` |
| `involvementKind` | `Consultation`, `CaseManagement`, `ServiceProvision`, `Protection`, `Education`, `Medical`, `Monitoring`, `Guardianship`（ここまで tsunagu-net と同じ 8 つ）, `Employment`, `Administrative`（この 2 つは tsunagu-net に無い。足す提案を台帳 G-40 に書いた） |
| `howEnded`（tsunagu-net と同じ） | `Ongoing`, `Lapsed`, `DeclinedByPerson`, `EndedByAgency`, `Unknown` |
| `guardianshipType` | `Guardianship`, `Curatorship`, `Assistance`, `VoluntaryGuardianship`（最後の値は tsunagu-net に無い。同じ値を足す提案を台帳 G-40 に書いた） |
| `birthDatePrecision`（tsunagu-net と同じ） | `Day`, `Month`, `Year`, `Unknown` |
| `staffRole`（tsunagu-net の部分集合） | `Staff`, `Administrator` |
| `reviewDomain` | `NgAction`, `CarePreference`, `KeyPerson`, `Guardianship`, `Certificate`, `CareRole` |
| `auditAction` | `Create`, `Approve`, `Reject`, `Inactivate`, `LinkEvidence`, `RaiseContradiction`, `ResolveContradiction`, `Read` |
| `linkedBy` | `Gate`, `Human` |
| `effectiveness` | `Effective`, `Ineffective`, `Neutral`, `Unknown` |
| `priority` | `High`, `Medium`, `Low` |
| `certificateType` | `IntellectualDisabilityHandbook`, `PhysicalDisabilityHandbook`, `MentalDisabilityHandbook`, `DisabilityServiceRecipientCertificate`, `ChildDayServiceRecipientCertificate`, `SupportiveMedicalCareCertificate`, `Other` |
| `publicAssistanceType` | `PublicAssistance`, `DisabilityBasicPension`, `DisabilityEmployeesPension`, `SpecialDisabilityAllowance`, `SpecialChildRearingAllowance`, `Other` |

- `clientRelationKind` は tsunagu-net の `relatedKind`（親族の 8 つ）をそのまま頭に置き、親族でない関係を足した。名前を分けたのは、同じ名前の列挙値の中身が二つの DB で違わないようにするため
- `certificateType`・`publicAssistanceType` の値は制度の名前から付けた英語で固定する（2026-11-05 河原さん。台帳 G-39）。日本語の表示名と根拠の条番号は `docs/SEMANTICS.md`（N-27）で持ち、この正典には書かない。条番号は e-Gov で照合するまで SEMANTICS の側に【未照合】を付ける

## 5. 資源の側

- tsunagu-net の正典 §5（v0.29 時点。読み込んだ書き出しの版を記録する）のとおり。nest-support は写しを持たない（約束 1）
- 個人の側が持つのは `Organization {orgId, linkedAt}` だけ。名前・住所・電話・窓口は、読む道具が `orgId` で資源の側から引く（D2-2・D3）

## 6. 確度と根拠の形（D4・D5）

```
(Client)-[:MUST_AVOID]->(NgAction)-[:EVIDENCED_BY]->(Record)-[:TOLD_BY]->(Person)
                                                   (Record)-[:ABOUT]->(Client)
(Record)-[:CONTRADICTS]->(NgAction)          … 食い違う話は上書きせず保留
(Review)-[:CONFIRMS]->(Record)                … 確かめ直した記録
(Person)-[:RELATED_TO {kind, certainty, evidenceRecordIds}]->(Client)   … 関係そのものが事実のとき
```

- 事実のノード 9 つ（§4.2）は確度を持たない。確度は根拠の `Record.certainty` にあり、事実の強さは、つながる記録の確度から読む道具が計算する（最も強いもの・最も新しいものなど、見せ方は読む側で決める）
- 関係（`RELATED_TO`）と関わり（`Involvement`）は、tsunagu-net と同じく自分の `certainty` を持つ。根拠は `RELATED_TO.evidenceRecordIds`、`Involvement` は `EVIDENCED_BY`
- 確度は作った後に変えない。確かめ直したら、新しい `Record`（または `Review` が `CONFIRMS`）を作り、元の記録はそのまま残す（約束 3）
- 情報源は `Record.informantKind`（5 値）と `TOLD_BY`（誰か。分かるときだけ）。確度に混ぜない
- 他の機関から受けた書面は二段：`providerCertainty`（提供元の原文の印）と `certainty`（受けた側から見た確度。提供元より強くしない）。`receivedOn` と `documentHash` を添える（約束 3・tsunagu-net BRS-44 と同じ）
- 「最後に確かめた日」は事実のノードに書き足さない。`EVIDENCED_BY` の先の `Record.heardOn` と、`CONFIRMS` の元の `Review.reviewedAt` から計算する（D4）
- 新しく聞いた話を既にある事実に結ぶのは人だけ（`linkedBy: Human`）。結ばなければ、新しい事実（`Pending`）として入る。似た文の自動の重複検出はしない（D5・D10）

## 7. 承認（D9）

- ゲートが書く事実・関係・記録は、AI 由来なら `Pending`（§4.1）
- 承認は書き込みとは別の操作。`(Staff)-[:APPROVED {at, selfApproval}]->(ノード)` を作り、`status` を `Active` にし、`AuditLog`（`action: Approve`、`selfApproval`）を残す
- 一人で使う人は、自分が取り込んだものを自分で承認してよい。そのときは `selfApproval: true`。`APPROVED.selfApproval` は必須で、自己承認の数がいつでも数えられる
- 承認の役割（tsunagu-net の `Approver`）は持たない。`staffRole` は tsunagu-net の 3 値の部分集合（`Staff`・`Administrator`）
- 承認の操作は、そのノードの根拠の `Record.quote` を並べて見せてから行う。AI 由来のノードをまとめて一括で承認しない（一回の操作で一つのノード）
- 却下は `status: Inactive` と `AuditLog`（`action: Reject`）。消さない

## 8. 前の正典（v3.5）とのつき合わせ

| 前の正典 | この正典 | 理由 |
|---|---|---|
| `Hospital`・`Organization`（属性つき）・`ServiceProvider`・`ProviderFeedback` | 外す。機関は ID だけの `Organization {orgId, linkedAt}` と `HAS_INVOLVEMENT` | D3（2 回目の改め）。口コミは ADR 未決論点 5 |
| `Doctor` | `Person` ＋ `RELATED_TO {kind: PrimaryDoctor}` | ADR D3 の改め（2026-11-05） |
| `KeyPerson`・`Relative`・`Guardian`（個人）・`Supporter` | `Person` と `RELATED_TO`（kind で役割）・`HAS_INVOLVEMENT` | 同じ人（母がキーパーソンで家族）が二つのノードになるのを防ぐ。名前で同定しない（D8） |
| `HAS_KEY_PERSON {rank}` | `RELATED_TO {kind: KeyPerson, rank}` | 関係の種類を `kind` にまとめた |
| `IS_PARENT_OF`・`FAMILY_OF` | `RELATED_TO {kind: Parent など}` | 同上 |
| `Guardian`（法人）・`HAS_LEGAL_REP` | `(Organization)-[:HAS_INVOLVEMENT]->(Involvement {kind: Guardianship, guardianshipType})` | D3 |
| `TREATED_AT`・`HAS_DOCTOR`・`USES_SERVICE`・`REGISTERED_AT`・`SUPPORTED_BY` | `Involvement` と `CONCERNS`・`HAS_INVOLVEMENT` | 関わりそのものをノードにし、始まり・終わり・確度を持たせるため（tsunagu-net と同じ形） |
| `MeetingRecord` | `Record`（kind `Interview`。音声の指紋は `documentHash`） | 面談も聞いた記録の一つ。ファイルの置き場所（`filePath`）は持たない |
| `SupportLog.emotion`・`triggerTag`・`context`・`type`・`duration` | 入れない | `emotion`・`triggerTag` は ADR 未決論点 7。決まるまで入れない |
| `FOLLOWS`（SupportLog の鎖） | 外す | 日付で並べられる。書き込みのたびに鎖を張り直す処理が要らなくなる |
| `NgAction`・`CarePreference` の `source`・`sourceDetail`・`lastConfirmedAt`・`staleAfter` | `Record` の側へ。`lastConfirmedAt` は計算する | D4・D5 |
| `Review.source`（日本語の値） | `Review.informantKind`（5 値） | 約束 3 の情報源にそろえた |
| `AuditLog` の `user`・`targetName`・`details` | `ACTED_BY`・`targetId`・`requestId` | 名前を監査ログに残さない |
| `Supporter -[:LOGGED]->`・`-[:RECORDED]->` | `AUTHORED_BY`（→ Staff） | tsunagu-net の名前にそろえた |
| `Identity`・`HAS_IDENTITY`（仮名化の将来の構想） | 外す | 実名は `Client` に持ち、読む道具が伏せる（N-22） |
| `CONTRADICTS`・`CONFIRMS`・`Review` | 残す（始点・終点を `Record` に寄せた） | 前の正典 v3.4 の考え方（D5） |
| 列挙値の日本語の例外 | 外す | §1 |
| `embedding`・`summaryEmbedding`・`textEmbedding`・ベクトル索引 6 本 | 外す | D10（N-04 でコードから外した） |
| `Client.name` の一意制約・名前の MERGE | 外す | D8 |

## 9. 止まる点 2 の決定（2026-11-05 河原さん。tsunagu-net の正典 v0.29 と照らした上で）

1. **列挙値の日本語の例外**：なくす。日本語の表示名は `docs/SEMANTICS.md` で持つ（§1）
2. **周りの人を `Person` 一つにする**：する。条件 (1) ADR D3 の「`Doctor` は残す」は ADR の改めとして明示する（ADR-001 D3 の改め 2026-11-05）。(2) 本人との関係の種類は `RELATED_TO.kind` の nest-support だけの列挙値にする（`clientRelationKind`。§4.5）。医療機関そのものは `Involvement {kind: Medical}` と `orgId`
3. **`Involvement` ノード**：する。tsunagu-net と同じ形（`HAS_INVOLVEMENT`・`CONCERNS`、`kind`・`certainty`・`guardianshipType`・`howEnded`）。機関の指し方は下の 10
4. **D5 の形を広げる範囲**：9 ラベルすべて。`certainty` と `informantKind` の列挙値は tsunagu-net と同じ
5. **面談記録**：`Record {kind: Interview}` にまとめ、`sourceHash` で二重の登録を止める。音声の置き場所・保存の期間は運用の文書に書く（N-29）
6. **関係そのものが事実のとき**：関係に `certainty` と根拠の記録の ID の一覧（`evidenceRecordIds`）を持たせ、確かめ直すたびに足す
7. **任意後見**：`VoluntaryGuardianship` を足す。tsunagu-net へ同じ値を足す提案を台帳に書く（G-40。tsunagu-net は変えない）
8. **`Staff` の役割**：`Staff`・`Administrator`。tsunagu-net の `staffRole` の部分集合。`APPROVED.selfApproval` を必ず残す
9. **`Record` の項目の名前**：tsunagu-net の `Record` の項目すべてとそろえる。そろえなかったものとその理由は §10

その後の判断（2026-11-05 河原さん。正典 v0.2 を見た上で）：

10. **機関の指し方（G-38）**：ID だけの `Organization {orgId, linkedAt}` を個人の側に置く。ADR D3 を 2 回目に改めた。`HAS_INVOLVEMENT` の始点に `Organization` を足し、`PROVIDED_BY`（Record → Organization）を足す。理由：(1) 記録をどの機関から得たかを辿れないと、`providerCertainty` と第三者から受けた情報の管理が辿れない (2) 「この機関に関わる本人」「この本人とこの機関の関わり」をプロパティの値の一致ではなく辺で引ける (3) tsunagu-net と同じ形になり、突き合わせに変換が要らない
11. **関わりの種類（G-41）**：tsunagu-net の 8 つをすべて持ち、`Employment`・`Administrative` を足す。足した 2 つは tsunagu-net へ足す提案として台帳 G-40 に書く
12. **手帳・受給者証・公的扶助の値（G-39）**：案のまま固定する。日本語の表示名と条番号は SEMANTICS（N-27）で持ち、照合までは【未照合】

## 10. tsunagu-net の正典 v0.29 とそろえなかったもの

| 項目 | tsunagu-net | nest-support | 理由 |
|---|---|---|---|
| `Record.quote` | 任意 | 必須 | 約束 4-1。nest-support の記録はどれも原文（語り・書面・自分の面談記録）から作るので、引用の無い記録を作らない |
| `Record.heardOn` | 無い | 任意（nest-support だけ） | いつ聞いたか。`aboutDate`（いつのことか）と分ける。「最後に確かめた日」の計算に使う（D4） |
| `Record` の `OWNED_BY`（→ Organization） | ある | 持たない | tsunagu-net では、どの機関の記録かを分けるため。nest-support の DB は一つの事業所の職員が使い、記録はどれもその事業所のもの。分ける必要が出たら足す |
| `WORKS_AT`（Staff → Organization） | ある | 持たない | 同じ理由。nest-support の `Staff` は DB を置く一つの事業所の職員だけ。複数の事業所で一つの DB を使うことになったら足す |
| `CONTRADICTS` の終点 | Record | 事実のノードと Involvement | D5：食い違いは事実に対して挙げる。聞いた記録どうしは上書きしない |
| `HAS_INVOLVEMENT` の始点 | Organization / Supporter | Organization / Person | 個人の支援者は `Supporter` に分けず `Person` に持つ（§9 の 2） |
| `CONCERNS` の終点 | Person / Household | Client | 本人一人が中心（ADR-001 背景）。世帯を持たない |
| `RELATED_TO` | Person → Person、`kind`（親族 8 つ）・`certainty` | Person → Client、`kind`（`clientRelationKind`）・`certainty`・`evidenceRecordIds`・`status`・`rank`・`since`・`until` | §9 の 2・6 |
| `involvementKind` の値 | 8 つ | 8 つ ＋ `Employment`・`Administrative` | 足した 2 つは tsunagu-net へ足す提案（台帳 G-40）。そろうまでの差 |
| `staffRole` | `Approver` がある | 無い | §9 の 8 |
| `APPROVED.selfApproval` | 無い | 必須 | D9 |
| `AuditLog.selfApproval` | 無い | 任意（Approve のとき） | D9 |
| `Person` のプロパティ | `birthDate`・`recordedSex`・`nameConsentAt` など | `phone`・`note` | 本人は `Client`。周りの人には連絡先が要り、生年月日は要らない |
| `guardianshipType` | 3 値 | 4 値（`VoluntaryGuardianship`） | §9 の 7 |

## 11. 機械検証ブロック

`nest/canon.py`（N-07）が読む。`idPrefixes` は個人の側で発番する ID の接頭辞、`externalIds` は資源の側の ID をそのまま持つラベル（`Organization` の `ORG` だけ）。乖離の検査（`scripts/check_drift.py`。N-08）は、この JSON を正として本書の表と突き合わせ、のちにゲートの許す一覧とも突き合わせる。`"*"` は「個人の側の任意のラベル」。条件つきの必須（§4.4）はゲートで強制し、ここには書かない。

```json machine-check
{
  "version": "0.3",
  "personal": {
    "commonRequired": ["registeredAt", "status", "origin"],
    "immutable": ["registeredAt"],
    "immutableByLabel": {"Record": ["certainty", "text", "quote", "informantKind", "documentHash", "providerCertainty"], "Involvement": ["certainty"]},
    "immutableByRelationship": {"RELATED_TO": ["certainty"]},
    "appendOnlyByRelationship": {"RELATED_TO": ["evidenceRecordIds"]},
    "nodes": {
      "Client":           {"required": ["clientId", "displayCode"], "optional": ["familyName", "givenName", "familyNameKana", "givenNameKana", "birthDate", "birthDatePrecision", "bloodType"], "unique": ["clientId", "displayCode"]},
      "Person":           {"required": ["personId"], "optional": ["familyName", "givenName", "familyNameKana", "givenNameKana", "phone", "note"], "unique": ["personId"]},
      "Staff":            {"required": ["staffId", "displayName", "role"], "optional": [], "unique": ["staffId"]},
      "Organization":     {"required": ["orgId", "linkedAt"], "optional": [], "unique": ["orgId"]},
      "Involvement":      {"required": ["involvementId", "kind", "howEnded", "certainty"], "optional": ["startDate", "endDate", "guardianshipType", "serviceTypeName"], "unique": ["involvementId"]},
      "NgAction":         {"required": ["ngActionId", "action", "riskLevel"], "optional": ["reason", "validFrom", "validTo"], "unique": ["ngActionId"]},
      "CarePreference":   {"required": ["carePreferenceId", "category", "instruction"], "optional": ["priority", "validFrom", "validTo"], "unique": ["carePreferenceId"]},
      "Condition":        {"required": ["conditionId", "name"], "optional": ["diagnosisDate"], "unique": ["conditionId"]},
      "Wish":             {"required": ["wishId", "content"], "optional": [], "unique": ["wishId"]},
      "LifeHistory":      {"required": ["lifeHistoryId", "episode"], "optional": ["era"], "unique": ["lifeHistoryId"]},
      "CareRole":         {"required": ["careRoleId", "name"], "optional": ["frequency", "priority", "note"], "unique": ["careRoleId"]},
      "Certificate":      {"required": ["certificateId", "type"], "optional": ["grade", "issuedDate", "nextRenewalDate"], "unique": ["certificateId"]},
      "PublicAssistance": {"required": ["publicAssistanceId", "type"], "optional": ["startDate", "endDate"], "unique": ["publicAssistanceId"]},
      "SupportLog":       {"required": ["supportLogId", "date", "situation"], "optional": ["action", "effectiveness", "note", "nextAction"], "unique": ["supportLogId"]},
      "Record":           {"required": ["recordId", "kind", "text", "quote", "certainty", "informantKind", "sourceHash"], "optional": ["aboutDate", "heardOn", "documentHash", "providerCertainty", "receivedOn"], "unique": ["recordId"]},
      "Review":           {"required": ["reviewId", "domain", "reviewedAt", "informantKind"], "optional": ["note"], "unique": ["reviewId"]},
      "AuditLog":         {"required": ["auditId", "at", "action", "targetLabel", "targetId", "requestId"], "optional": ["selfApproval"], "unique": ["auditId"]}
    },
    "relationships": {
      "RELATED_TO":          {"from": ["Person"], "to": ["Client"], "required": ["kind", "certainty", "evidenceRecordIds", "status"], "optional": ["rank", "since", "until"]},
      "HAS_INVOLVEMENT":     {"from": ["Organization", "Person"], "to": ["Involvement"], "required": [], "optional": []},
      "CONCERNS":            {"from": ["Involvement"], "to": ["Client"], "required": [], "optional": []},
      "MUST_AVOID":          {"from": ["Client"], "to": ["NgAction"], "required": [], "optional": []},
      "REQUIRES":            {"from": ["Client"], "to": ["CarePreference"], "required": [], "optional": []},
      "HAS_CONDITION":       {"from": ["Client"], "to": ["Condition"], "required": [], "optional": []},
      "IN_CONTEXT":          {"from": ["NgAction"], "to": ["Condition"], "required": [], "optional": []},
      "ADDRESSES":           {"from": ["CarePreference"], "to": ["Condition"], "required": [], "optional": []},
      "HAS_WISH":            {"from": ["Client"], "to": ["Wish"], "required": [], "optional": []},
      "HAS_HISTORY":         {"from": ["Client"], "to": ["LifeHistory"], "required": [], "optional": []},
      "HAS_CERTIFICATE":     {"from": ["Client"], "to": ["Certificate"], "required": [], "optional": []},
      "RECEIVES":            {"from": ["Client"], "to": ["PublicAssistance"], "required": [], "optional": []},
      "PERFORMS":            {"from": ["Person"], "to": ["CareRole"], "required": [], "optional": ["since", "until"]},
      "ROLE_FOR":            {"from": ["CareRole"], "to": ["Client"], "required": [], "optional": []},
      "CAN_BE_PERFORMED_BY": {"from": ["CareRole"], "to": ["Person", "Involvement"], "required": [], "optional": []},
      "EVIDENCED_BY":        {"from": ["NgAction", "CarePreference", "Condition", "Wish", "LifeHistory", "CareRole", "Certificate", "PublicAssistance", "SupportLog", "Involvement"], "to": ["Record"], "required": ["linkedBy", "at"], "optional": []},
      "CONTRADICTS":         {"from": ["Record"], "to": ["NgAction", "CarePreference", "Condition", "Wish", "LifeHistory", "CareRole", "Certificate", "PublicAssistance", "SupportLog", "Involvement"], "required": ["claim", "raisedAt"], "optional": ["resolvedAt", "resolution", "resolvedBy"]},
      "CONFIRMS":            {"from": ["Review"], "to": ["Record"], "required": [], "optional": []},
      "ABOUT":               {"from": ["Record", "Review", "SupportLog"], "to": ["Client"], "required": [], "optional": []},
      "TOLD_BY":             {"from": ["Record"], "to": ["Person", "Client"], "required": [], "optional": []},
      "PROVIDED_BY":         {"from": ["Record"], "to": ["Organization"], "required": [], "optional": []},
      "AUTHORED_BY":         {"from": ["Record", "SupportLog"], "to": ["Staff"], "required": [], "optional": []},
      "REVIEWED":            {"from": ["Staff"], "to": ["Review"], "required": [], "optional": []},
      "APPROVED":            {"from": ["Staff"], "to": ["*"], "required": ["at", "selfApproval"], "optional": []},
      "AUDIT_FOR":           {"from": ["AuditLog"], "to": ["*"], "required": [], "optional": []},
      "ACTED_BY":            {"from": ["AuditLog"], "to": ["Staff"], "required": [], "optional": []}
    }
  },
  "idPrefixes": {
    "Client": "CLI", "Person": "PER", "Staff": "STF", "Involvement": "INV", "Record": "REC",
    "NgAction": "NGA", "CarePreference": "CPF", "Condition": "CND", "Wish": "WSH", "LifeHistory": "LHS",
    "CareRole": "CRL", "Certificate": "CRT", "PublicAssistance": "PAS", "SupportLog": "SLG",
    "Review": "REV", "AuditLog": "AUD"
  },
  "externalIds": {"Organization": "ORG"},
  "enums": {
    "status": ["Active", "Pending", "Inactive"],
    "origin": ["Human", "AiExtracted", "Imported"],
    "certainty": ["Confirmed", "Hearsay", "SelfReport", "Inference", "Unspecified"],
    "informantKind": ["Self", "Family", "Agency", "Neighbor", "DocumentOnly"],
    "recordKind": ["Observation", "Interview", "Notification", "MeetingMinutes", "Plan", "Document"],
    "riskLevel": ["LifeThreatening", "Panic", "Discomfort"],
    "clientRelationKind": ["Parent", "Child", "Spouse", "Partner", "Sibling", "Grandparent", "Grandchild", "OtherRelative", "KeyPerson", "PrimaryDoctor", "Neighbor", "Helper", "OtherSupporter"],
    "involvementKind": ["Consultation", "CaseManagement", "ServiceProvision", "Protection", "Education", "Medical", "Monitoring", "Guardianship", "Employment", "Administrative"],
    "howEnded": ["Ongoing", "Lapsed", "DeclinedByPerson", "EndedByAgency", "Unknown"],
    "guardianshipType": ["Guardianship", "Curatorship", "Assistance", "VoluntaryGuardianship"],
    "birthDatePrecision": ["Day", "Month", "Year", "Unknown"],
    "staffRole": ["Staff", "Administrator"],
    "reviewDomain": ["NgAction", "CarePreference", "KeyPerson", "Guardianship", "Certificate", "CareRole"],
    "auditAction": ["Create", "Approve", "Reject", "Inactivate", "LinkEvidence", "RaiseContradiction", "ResolveContradiction", "Read"],
    "linkedBy": ["Gate", "Human"],
    "effectiveness": ["Effective", "Ineffective", "Neutral", "Unknown"],
    "priority": ["High", "Medium", "Low"],
    "certificateType": ["IntellectualDisabilityHandbook", "PhysicalDisabilityHandbook", "MentalDisabilityHandbook", "DisabilityServiceRecipientCertificate", "ChildDayServiceRecipientCertificate", "SupportiveMedicalCareCertificate", "Other"],
    "publicAssistanceType": ["PublicAssistance", "DisabilityBasicPension", "DisabilityEmployeesPension", "SpecialDisabilityAllowance", "SpecialChildRearingAllowance", "Other"]
  },
  "enumBindings": {
    "*.status": "status", "*.origin": "origin",
    "Client.birthDatePrecision": "birthDatePrecision", "Staff.role": "staffRole",
    "Involvement.kind": "involvementKind", "Involvement.howEnded": "howEnded", "Involvement.certainty": "certainty", "Involvement.guardianshipType": "guardianshipType",
    "NgAction.riskLevel": "riskLevel", "CarePreference.priority": "priority", "CareRole.priority": "priority",
    "Certificate.type": "certificateType", "PublicAssistance.type": "publicAssistanceType", "SupportLog.effectiveness": "effectiveness",
    "Record.kind": "recordKind", "Record.certainty": "certainty", "Record.providerCertainty": "certainty", "Record.informantKind": "informantKind",
    "Review.domain": "reviewDomain", "Review.informantKind": "informantKind", "AuditLog.action": "auditAction",
    "RELATED_TO.kind": "clientRelationKind", "RELATED_TO.certainty": "certainty", "RELATED_TO.status": "status",
    "EVIDENCED_BY.linkedBy": "linkedBy"
  },
  "types": {
    "*.registeredAt": "DateTime",
    "Client.birthDate": "Date", "Organization.linkedAt": "DateTime", "Involvement.startDate": "Date", "Involvement.endDate": "Date",
    "NgAction.validFrom": "Date", "NgAction.validTo": "Date", "CarePreference.validFrom": "Date", "CarePreference.validTo": "Date",
    "Condition.diagnosisDate": "Date", "Certificate.issuedDate": "Date", "Certificate.nextRenewalDate": "Date",
    "PublicAssistance.startDate": "Date", "PublicAssistance.endDate": "Date", "SupportLog.date": "Date",
    "Record.aboutDate": "Date", "Record.heardOn": "Date", "Record.receivedOn": "Date",
    "Review.reviewedAt": "DateTime", "AuditLog.at": "DateTime", "AuditLog.selfApproval": "Boolean",
    "RELATED_TO.evidenceRecordIds": "List", "RELATED_TO.rank": "Integer", "RELATED_TO.since": "Date", "RELATED_TO.until": "Date",
    "PERFORMS.since": "Date", "PERFORMS.until": "Date",
    "EVIDENCED_BY.at": "DateTime", "CONTRADICTS.raisedAt": "DateTime", "CONTRADICTS.resolvedAt": "DateTime",
    "APPROVED.at": "DateTime", "APPROVED.selfApproval": "Boolean"
  },
  "indexes": [
    {"label": "Record", "property": "sourceHash", "kind": "RANGE"},
    {"label": "Client", "property": "familyNameKana", "kind": "RANGE"},
    {"label": "Person", "property": "familyNameKana", "kind": "RANGE"},
    {"label": "Client", "property": "birthDate", "kind": "RANGE"}
  ]
}
```

## 変更履歴

- v0.3（2026-11-05）：G-38〜G-41 の河原さんの判断（§9 の 10〜12）。ID だけの `Organization {orgId, linkedAt}`、`HAS_INVOLVEMENT` の始点に Organization、`PROVIDED_BY`（Record → Organization）。`Involvement.orgId` を外した。`involvementKind` を tsunagu-net の 8 つ ＋ 2 つに。JSON に `externalIds`。§10 に `OWNED_BY`・`WORKS_AT` を持たない理由
- v0.2（2026-11-05）：止まる点 2 の河原さんの判断を反映（§9）。`FAMILY_OF`・`HAS_KEY_PERSON`・`INVOLVED_IN`・`RECORDED_BY` を外し、`RELATED_TO`（Person → Client）・`HAS_INVOLVEMENT`・`AUTHORED_BY`・`REVIEWED` にした。`Involvement` に `certainty`・`howEnded`（必須）、`clientRelationKind`・`certificateType`・`publicAssistanceType` の値、`guardianshipType` に `VoluntaryGuardianship`。接頭辞のつき合わせ（§3）と、tsunagu-net とそろえなかったもの（§10）を足した
- v0.1 案（2026-11-05）：初版（N-06）。止まる点 2 の前
