# nest-support 意味の文書（SEMANTICS）

正典 `docs/SCHEMA.md` が扱わない、業務上の意味・運用の規則・列挙値の日本語の表示名を置く（正典 §1、ADR-001 D1）。
列挙値の日本語の表示名は末尾の節（N-27）。ほかに担当機関の推定（計画 N-24a）、任意後見・任意代理（台帳 G-62）、記録の書き方と読み取り（台帳 G-42・G-52）の節。

## 担当機関の推定（N-24a。2026-11-05 河原さんの指示）

語りの「区役所の窓口で」のように機関の名前が無い言及に、本人の住所の区で絞った資源の側の機関の候補を添え、
Claude が確度 `Inference` の関わり（`Involvement`）の案を作れるようにする。埋め込み（文の近さ）は使わない。選ぶ根拠は住所。

### SEM-AREA-01 住所から団体コード（区）を出す

- ゲートが `Residence` を登録するとき、住所の文から 6 桁の団体コードを出して `areaCode` に持つ（`nest/area_code.py`）。依頼に `areaCode` があって住所から出した値と違えば止める
- 手元だけで出す。住所の文を外（ジオコーディングなど）に送らない
- 住所を Unicode の NFKC にそろえ、空白を除き、先頭の「福岡県」を外してから、表の名前（「北九州市小倉北区」「遠賀郡芦屋町」「芦屋町」など）が**住所の先頭に一致する**もののうち、いちばん長いものを採る
- 一致しなければ空。区の名前だけ（「小倉北区…」）・町名だけからは推測しない。空なら推定は機関未確定に倒す

**表の出どころと版**

| 項目 | 値 |
|---|---|
| ファイル | `nest/data/area-codes-kitakyushu-2026-10-25.json`（40 行） |
| 出どころ | 総務省「都道府県コード及び市区町村コード」令和6年1月1日現在（https://www.soumu.go.jp/denshijiti/code.html ） |
| 写し元 | tsunagu-net の `docs/reference/area-codes-kitakyushu-2026-10-25.json`（コミット `74ac35a`。読むだけ。変えずにそのまま写した） |
| 指紋（SHA-256） | `a7700fd45f8e7811964531344bcf0584022de9c6b7fde0f02df6212fa7e291db`（`nest/area_code.py` が読むたびに確かめる） |
| 範囲 | 北九州市と 7 区、近隣の市町村（tsunagu-net の ADR-001 D10 の範囲と、その表にある近隣） |

範囲の外の住所は空になる（機関未確定）。範囲を広げるときは表を差し替え、指紋とこの節を同時に直す。

### SEM-AREA-02 どの住所で推定するか

- 過去の言及は、言及の時期（記録の `aboutDate`）に住んでいた住所（`since` ≦ 時期 ＜ `until`）の区で推定する
- 当時の住所が記録に無いとき（`since` が空のものは当時の住所に数えない）は、今の住所（`until` が空のもの）で推定し、「今の住所で推定した」旨を案の注記（点検の結果の `notes`）に書く。職員は承認の前にそれを見る。DB には、関わりの推定の根拠（`inferenceBasis`。正典 v0.6 §4.5）として `CurrentResidenceArea` を残す。当時の住所で推定したときは `ResidenceAreaAtTheTime`。住所と区のコードは残さない（台帳 G-57）
- 言及の時期が分からないときも、今の住所で推定し、その旨を書く
- 今の住所が無い・二つある・区が出ていないときは、候補を出さない（機関未確定）
- 使う住所は承認済み（`status: Active`）のものだけ

### SEM-AREA-03 候補の絞り方

- 資源の側で、その区と、`PART_OF` で上にある市を `SERVES` で担当する機関のうち、`status: Active` で、種類が次の相談窓口のもの（2026-11-05 河原さん。台帳 G-57）。種類の値は tsunagu-net の `orgKind`（SEMANTICS ENU-14）の名前のまま
  - いつも候補にする 7 つ：`DisabilityDivision`・`HardshipSupportDesk`・`WelfareOffice`・`BasicConsultationCenter`・`MentalHealthDesk`・`SocialWelfareCouncil`（日常生活自立支援事業。お金の安全に直結するため）・`GuardianshipCenter`（後見制度の相談の窓口として）
  - 本人の年齢で足す種類は SEM-AREA-05。合わせて最大 10
  - 候補にしない：`CareInsuranceDivision`（ENU-14 では本庁の介護保険課で、施設での高齢者虐待の対応と事業所への指導の課。個人の相談窓口ではない）、`DisabilityServiceSupervision`（指定・指導の部署）、`ChildGuidanceCenter`。契約で選ぶ事業所（相談支援事業所など）は地区の担当（`SERVES`）が無いので、住所からは推定できない（名前から引く。計画 N-24）
  - 種類ごとの理由と、選ばなかった近い種類は `docs/journal/2026-11-05-g57-org-kinds.md`
- 担当の根拠（`servesBasis`：`Designated`／`PresumedByLocation`）と、区の一部だけを担当するか（`partOfArea`）を候補に添える。`PresumedByLocation` を `Designated` に格上げしない（tsunagu-net BRS-23）
- 点数づけをしない。区の担当を先に、市の担当を後に、名前の順に並べる
- Claude に渡すのは候補の `orgId` と名前だけ（公開情報）。区コード・住所・根拠は渡さない（`docs/external-api.md` NEXT-01）

### SEM-AREA-04 案と確定

- Claude は語りの文脈で候補から一つ選ぶか、選ばない（機関未確定）。候補の外の機関 ID は点検（`intake.check`）が止める
- 関わりの確度はいつも `Inference`、終わり方は `Unknown`。案に確度を書かせない。AI 由来なので `Pending`。職員が承認して初めて確定する（N-21）
- 後見（`Guardianship`）は推定で作らない。`GuardianshipCenter` を選んだ関わりは `Consultation` だけ（ほかの種類は点検が止める）
- 住所からの推定（`inferenceBasis` を持つ関わり）で作れる種類は `Consultation`（相談）と `Administrative`（手続き）だけ。ほかの種類（`AgencyContract`・`Guardianship`・`ServiceProvision` など）はゲートが止める。住所で分かるのは「この区の窓口が担当になりうる」ことだけで、契約や選任で決まる関わりは推し量れない（2026-11-05 河原さん。台帳 G-62）
- 親の介護の相談（親についての関わり）は、本人の関わりにしない。正典 v0.7 から、親を `Person` として持ち、その人に向けた関わり（`CONCERNS` → `Person`）にできる。ただし原文に「その人が相談した・その人に関わった」とはっきり書かれているときだけで、引用を付けて `Pending`。住所からの推定（候補から選んだ機関）では、本人以外の人の関わりを作らない（点検とゲートが止める。台帳 G-60）
- 窓口（`Window`）までは絞らない。機関の単位で止め、窓口は未確定にする。間違った窓口を確定させない

### SEM-AREA-05 本人の年齢で足す種類（2026-11-05 河原さん。台帳 G-57）

- 決まった規則で分ける。AI は使わない。出るのは候補で、決めるのは人の承認
- 年齢は、言及の時期（記録の `aboutDate`）で数える。時期が分からなければ今日で数える
- 65 歳以上：`ElderlyDivision`・`CommunityGeneralSupportCenter` を足す。区切りは介護保険の第 1 号被保険者（介護保険法（平成9年法律第123号）第 9 条第 1 号「六十五歳以上の者」。e-Gov で照合 2026-11-05）
- 18 歳未満：`ChildFamilyCenter` を足す。区切りは児童（児童福祉法（昭和22年法律第164号）第 4 条第 1 項「満十八歳に満たない者」。e-Gov で照合 2026-11-05）
- 年齢の数え方：誕生日の前日に満の年齢に達する。2 月 29 日生まれは、応当日の無い年は 3 月 1 日の前日に達する。根拠は年齢計算ニ関スル法律（明治35年法律第50号）第 1 項「年齢ハ出生ノ日ヨリ之ヲ起算ス」・第 2 項「民法第百四十三条ノ規定ハ年齢ノ計算ニ之ヲ準用ス」と、民法（明治29年法律第89号）第 143 条（どちらも e-Gov で照合 2026-11-05。年齢計算ニ関スル法律は条の番号を持たず、項だけ）。河原さんの jp-normalize の `age_at(..., legal=True)` と同じ答えになることを試験で固定した（4 月 1 日生まれは 3 月 31 日に 18 歳、2 月 29 日生まれは平年 2 月 28 日に加齢。`tests/test_org_estimate_age.py`）
- 生年月日の記録が無い（`birthDate` が無い、または `birthDatePrecision: Unknown`）：65 歳以上の窓口と 18 歳未満の窓口の両方を出し、「年齢の記録なし」と注記する
- 生年月日が年だけ（`Year`）・年月だけ（`Month`）で、区切りの前後どちらか決まらない：その区切りの窓口を出し、決まらない旨を注記する。精度（`birthDatePrecision`）が無ければ、日まで分かっているものとして読む
- 生年月日は推定の結果に入れない。Claude には渡さない（渡すのは候補の `orgId` と名前だけ）

## 任意後見と任意代理（2026-11-06 河原さん。台帳 G-62）

tsunagu-net の SEMANTICS v0.32 の BRS-49 と ENU-05・10・20 に合わせた。値と定義は正典 §4.5。条は tsunagu-net が e-Gov で照合した記録
（tsunagu-net `docs/laws/verified/laws-verified-voluntary-guardianship-2026-11-05.json`、2026-11-05 照合。現行の版 411AC0000000150_20260624_508AC0000000045 ほか）から引いた。

### SEM-GUARD-01 根拠の条

- 任意後見契約は、任意後見監督人が選任された時から効力を生ずる定めのある委任契約（任意後見契約に関する法律 第2条第1号）。公正証書でする（同 第3条）
- 効力の前の受任者は任意後見受任者、後は任意後見人（同 第2条第3号・第4号）。受任者の段階でも契約は登記され、受任者の氏名又は名称が記録される（後見登記等に関する法律 第5条第3号）
- 任意後見監督人の選任は、契約が登記され、本人の事理を弁識する能力が不十分な状況にあるとき、本人・配偶者・四親等内の親族・任意後見受任者の請求による（任意後見契約に関する法律 第4条第1項）
- 任意代理（`AgencyContract`）は委任（民法 第643条）と代理（民法 第99条第1項）による契約。「財産管理契約」の語は任意後見契約に関する法律に無い
- 任意後見契約の委任者は本人（任意後見契約に関する法律 第2条第2号）。親なき後の支援で、親が親自身のために結んだ任意後見は、親についての関わり（`CONCERNS` → `Person`。正典 §4.3、台帳 G-60）で、本人（`Client`）の後見の関わりではない

### SEM-GUARD-02 法改正（令和 8 年法律第 45 号）

- 民法等の一部を改正する法律（令和 8 年法律第 45 号。2026-06-24 公布）で、任意後見の効力が生じるのは任意後見開始の審判の時になり、監督の必要が明らかにないときは任意後見監督人を選任しないことができる。民法の後見・保佐は補助に一つになり、施行日前に始まった後見・保佐は施行の後も残る【未照合：改正後の条と附則。tsunagu-net が e-Gov の未施行の版を読んだが、照合の道具の外】
- 施行は公布の日から起算して二年六月を超えない範囲内において政令で定める日。政令は 2026-11-05 の時点で e-Gov に無い。施行日は政令で定まってから書く
- 施行の後、後見（`Guardianship`）・保佐（`Curatorship`）は新しく使わないが、値は消さない。ゲートで止めるのは政令の後（tsunagu-net の T-31a に合わせる）

## 記録の書き方と読み取り（2026-11-06 河原さん。台帳 G-42・G-52）

### SEM-REC-01 語りの中の人は役割の名前で書く

- 語りや記録を登録するとき、本人以外の人は実名ではなく役割の名前で書く（例：母・主治医・担当の相談員）。記録の原文（`text`）と引用（`quote`）は自由な文なので、読み取りの包みの伏せ字（項目の名前と、実名とそっくり同じ文字列）では拾いきれないため
- 読み取りの包みは、記録の原文全体（`text`）を返さない。引用（`quote`）は求められたとき（道具 `read_quote`）だけ、200 字までを返す。自由な Cypher では `text`・`quote` を読ませない（台帳 G-42 (1)）

### SEM-REC-02 仮名で呼ぶ

- 職員は Claude の中では本人を仮名（`displayCode`）で呼ぶ。名前から仮名を引く入口は Claude の外（手元の小さなコマンドか画面）に置き、MCP の包みには名前を受け取る道具を作らない。包みが名前を受け取ると、名前と仮名の対応が Anthropic の側の記録に残るため（台帳 G-42 (2)）。使いにくければ、実データを入れる前にもう一度決める

### SEM-REC-03 禁忌には根拠の記録が要る

- 新しい禁忌（`NgAction`）には、根拠の記録（`EVIDENCED_BY` → `Record`）が一つは要る。無ければゲートが止める（ADR D5。台帳 G-52 (7)）
- 職員が直接知った禁忌は、先に職員の記録（`Record`、`kind: Observation`）を作り、それを根拠にする
- 取り込みの案の禁忌・推奨ケアの候補は、同じ案の事実を根拠に指す。指していない候補はゲートが止める。新しい推奨ケア（`CarePreference`）にも、由来によらず根拠の記録が要る。職員が直接知ったことは、禁忌と同じく先に職員の記録（`kind: Observation`）を作る（台帳 G-63。正典 v0.9 §6）

## 列挙値の表示名（計画 N-27。台帳 G-47）

正典 §4.5 の列挙値の日本語の表示名。コード（`nest/semantics.py`）はこの表から読む。コードに日本語名の対応表を直に書かない。
tsunagu-net と同じ列挙（`status`・`origin`・`certainty`・`informantKind`・`recordKind`・`howEnded`・`guardianshipType`・`staffRole`、`involvementKind` の 9 つ、`clientRelationKind` の親族の 8 つ）は、tsunagu-net の SEMANTICS §3（ENU-01〜ENU-20）の日本語に合わせた。ほかは nest-support で付けた（2026-11-06。止まる点 E-1 で見ていただく）。
`certificateType`・`publicAssistanceType` の根拠の条番号は、まだ書いていない【未照合】（正典 §4.5。e-Gov で照合してから足す）。

### SEM-ENUM-01 表示名

| 列挙 | 値 | 表示名 |
|---|---|---|
| `status` | `Active` | 有効 |
| `status` | `Pending` | 未確定 |
| `status` | `Inactive` | 無効 |
| `origin` | `Human` | 人が入力 |
| `origin` | `AiExtracted` | AI が抽出 |
| `origin` | `Imported` | 他のシステムから移した |
| `certainty` | `Confirmed` | 確認済み |
| `certainty` | `Hearsay` | 伝聞 |
| `certainty` | `SelfReport` | 本人の話 |
| `certainty` | `Inference` | 推測 |
| `certainty` | `Unspecified` | 確度の記載なし |
| `informantKind` | `Self` | 本人 |
| `informantKind` | `Family` | 家族・親族 |
| `informantKind` | `Agency` | 機関 |
| `informantKind` | `Neighbor` | 近隣・知人 |
| `informantKind` | `DocumentOnly` | 記録を見ただけ |
| `recordKind` | `Observation` | 観察 |
| `recordKind` | `Interview` | 聞き取り |
| `recordKind` | `Notification` | 通告・通報 |
| `recordKind` | `MeetingMinutes` | 会議録 |
| `recordKind` | `Plan` | 支援の計画 |
| `recordKind` | `Document` | 文書の要旨 |
| `riskLevel` | `LifeThreatening` | 生命に関わる |
| `riskLevel` | `Panic` | パニックを招く |
| `riskLevel` | `Discomfort` | 不快・ストレス |
| `clientRelationKind` | `Parent` | 親 |
| `clientRelationKind` | `Child` | 子 |
| `clientRelationKind` | `Spouse` | 配偶者 |
| `clientRelationKind` | `Partner` | 内縁など |
| `clientRelationKind` | `Sibling` | きょうだい |
| `clientRelationKind` | `Grandparent` | 祖父母 |
| `clientRelationKind` | `Grandchild` | 孫 |
| `clientRelationKind` | `OtherRelative` | その他の親族 |
| `clientRelationKind` | `KeyPerson` | キーパーソン |
| `clientRelationKind` | `PrimaryDoctor` | 主治医 |
| `clientRelationKind` | `Neighbor` | 近隣・知人 |
| `clientRelationKind` | `Helper` | 手伝ってくれる人 |
| `clientRelationKind` | `OtherSupporter` | その他の支える人 |
| `involvementKind` | `Consultation` | 相談 |
| `involvementKind` | `CaseManagement` | 計画・調整 |
| `involvementKind` | `ServiceProvision` | サービスの提供 |
| `involvementKind` | `Protection` | 保護・措置 |
| `involvementKind` | `Education` | 教育・保育 |
| `involvementKind` | `Medical` | 医療 |
| `involvementKind` | `Monitoring` | 見守り |
| `involvementKind` | `Guardianship` | 成年後見等 |
| `involvementKind` | `AgencyContract` | 任意代理（委任契約） |
| `involvementKind` | `Employment` | 勤め先 |
| `involvementKind` | `Administrative` | 申請・更新の手続き |
| `howEnded` | `Ongoing` | 続いている |
| `howEnded` | `Lapsed` | 途切れた |
| `howEnded` | `DeclinedByPerson` | 本人・家族が断った |
| `howEnded` | `EndedByAgency` | 機関が終えた |
| `howEnded` | `Unknown` | 未確認 |
| `howEnded` | `Transitioned` | 任意後見に移った |
| `guardianshipType` | `Guardianship` | 後見 |
| `guardianshipType` | `Curatorship` | 保佐 |
| `guardianshipType` | `Assistance` | 補助 |
| `guardianshipType` | `VoluntaryGuardianship` | 任意後見 |
| `guardianshipType` | `VoluntaryGuardianshipContracted` | 任意後見受任者 |
| `birthDatePrecision` | `Day` | 日まで |
| `birthDatePrecision` | `Month` | 月まで |
| `birthDatePrecision` | `Year` | 年まで |
| `birthDatePrecision` | `Unknown` | 不明 |
| `staffRole` | `Staff` | 職員 |
| `staffRole` | `Administrator` | 管理者 |
| `reviewDomain` | `NgAction` | 禁忌 |
| `reviewDomain` | `CarePreference` | 推奨ケア |
| `reviewDomain` | `KeyPerson` | キーパーソン |
| `reviewDomain` | `Guardianship` | 後見 |
| `reviewDomain` | `Certificate` | 手帳・受給者証 |
| `reviewDomain` | `CareRole` | 親が担ってきた役割 |
| `auditAction` | `Create` | 作成 |
| `auditAction` | `Approve` | 承認 |
| `auditAction` | `Reject` | 却下 |
| `auditAction` | `Inactivate` | 無効にした |
| `auditAction` | `LinkEvidence` | 根拠を結んだ |
| `auditAction` | `RaiseContradiction` | 食い違いを挙げた |
| `auditAction` | `ResolveContradiction` | 食い違いを裁定した |
| `auditAction` | `Read` | 読んだ |
| `linkedBy` | `Gate` | 取り込みで結んだ |
| `linkedBy` | `Human` | 人が結んだ |
| `effectiveness` | `Effective` | 効果があった |
| `effectiveness` | `Ineffective` | 効果がなかった |
| `effectiveness` | `Neutral` | どちらとも言えない |
| `effectiveness` | `Unknown` | 分からない |
| `priority` | `High` | 高 |
| `priority` | `Medium` | 中 |
| `priority` | `Low` | 低 |
| `certificateType` | `IntellectualDisabilityHandbook` | 療育手帳 |
| `certificateType` | `PhysicalDisabilityHandbook` | 身体障害者手帳 |
| `certificateType` | `MentalDisabilityHandbook` | 精神障害者保健福祉手帳 |
| `certificateType` | `DisabilityServiceRecipientCertificate` | 障害福祉サービス受給者証 |
| `certificateType` | `ChildDayServiceRecipientCertificate` | 通所受給者証（障害児通所支援） |
| `certificateType` | `SupportiveMedicalCareCertificate` | 自立支援医療受給者証 |
| `certificateType` | `Other` | その他 |
| `publicAssistanceType` | `PublicAssistance` | 生活保護 |
| `publicAssistanceType` | `DisabilityBasicPension` | 障害基礎年金 |
| `publicAssistanceType` | `DisabilityEmployeesPension` | 障害厚生年金 |
| `publicAssistanceType` | `SpecialDisabilityAllowance` | 特別障害者手当 |
| `publicAssistanceType` | `SpecialChildRearingAllowance` | 特別児童扶養手当 |
| `publicAssistanceType` | `Other` | その他 |
| `inferenceBasis` | `ResidenceAreaAtTheTime` | 当時の住所の区から推定 |
| `inferenceBasis` | `CurrentResidenceArea` | 今の住所の区から推定 |

### SEM-ENUM-02 原文の確度の印

取り込みの案の点検（`nest/gate/intake.py`）が、引用の直後（同じ行）の【…】から確度を決める表。上から弱い順に並べる。印に二つ以上の語が入っていたら、上にある（弱い）ほうを採る。

| 印 | 確度 |
|---|---|
| 推測 | `Inference` |
| 伝聞 | `Hearsay` |
| 未確認 | `Hearsay` |
| 本人の話 | `SelfReport` |
| 確認済み | `Confirmed` |
