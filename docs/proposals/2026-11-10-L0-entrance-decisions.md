# 提案：確認点 L-0 ── 書き込み受付（L-1）の前に決める 3 つの論点の案

- 状態：**案（決めるのは河原さん）**。2026-11-10。確認点 L-0（`docs/proposals/2026-11-09-interview-record-shape.md` の論点 8 つのうち、1・2・4・5・6 に当たる 3 つ）
- **正典（SCHEMA・SEMANTICS）・コード・手順書・試験は、この提案では変えていない。** 河原さんが可とした案だけを、段階 L の最初に「試験を先に書く → 正典の版を上げる → `check_drift.py` で FAIL 0」の順で入れる
- 関連：ADR-001（D4 確度・D5 根拠・D6 書き込み・D7 点検・D8 人の同定）、ADR-002（D1 入口・D3 案の種類）、正典 `docs/SCHEMA.md` v0.12（§4.2 `Record`・`SupportLog`、§4.3、§4.5、§6、§10）、`docs/SEMANTICS.md`（SEM-REC-01〜03、SEM-ENUM-01・02）、journal `docs/journal/2026-11-08-n46-trial.md`（詰まり #5・#9・#10）、共通の約束 v1.1（tsunagu-net `docs/contracts/nest-support-shared.md`。読むだけ）
- 用語（一行ずつ）：**入口の点検**＝`nest/gate/intake.py` の `check`。Claude の案（JSON）を原文と突き合わせる、AI を使わない点検。**受付の検証**＝`nest/gate/validate.py`。正典の形に合うかを見る（文書では「ゲート」と呼んできたもの）。**見立て**＝記録者（相談支援専門員）自身の受け取り方・推測。**面接記録**＝相談支援の訪問・来所・電話・同行・会議の記録

## 0. 三つの論点の関係（先に全体）

| 論点 | 一言で | 決めると変わるもの |
|---|---|---|
| 1 面接記録の置き場 | 面接 1 回を `SupportLog` 1 件にし、聞いた事実は `Record` に分けるか | 正典（`SupportLog` の項目）、案の形、スキル |
| 2 見立ての置き場 | `informantKind` に値を足すか、足さずに確度 `Inference` と `AUTHORED_BY` で表すか | 約束 3（足すなら）、SEMANTICS、スキル、入口の点検 |
| 3 入口の点検の範囲 | 必須の項目・列挙値を入口で見るか。根拠の無い新しい人を止めるか | 入口の点検・受付の検証・試験（正典は変わらない） |

論点 1 で案の形に `supportLog` の欄が増えるなら、その必須の項目を入口で見るか（論点 3）が直ちに問われる。論点 2 で値を足さない形を採るなら、「見立てには情報源の値が要る」という決まりを入口で伝える必要があり、これも論点 3 にかかる。組み合わせは §4 の表。

## 1. 論点 1：相談支援の面接記録の置き場

### 1.1 今の形（正典 v0.12 と試走で分かったこと）

- `Record`（`kind: Interview` など）は「聞いた記録」。**事実 1 件＝記録 1 件**で、引用（`quote`）・確度・情報源を持つ（§4.2・§6）。面談そのものは §8・§9 の 5 で「`Record {kind: Interview}` にまとめ、`sourceHash` で二重の登録を止める」とされた
- `SupportLog` は「支援の記録。構造（状況・対応・効果）を持つ事実。書いた人は `Staff`。元の文は `Record` に持つ」（§4.2）。項目は `date`✅・`situation`✅・`action`・`effectiveness`・`note`・`nextAction`。`EVIDENCED_BY` で `Record` に結べる（§4.3）。入口の点検の案の形には `SupportLog` の欄が無く、試走では field-ui が人の入力（`origin: Human`）として直接ゲートに通していた
- 試走の詰まり #5：はるとの記録 1（訪問）・2（電話）は、field-ui の「場面」（食事・作業・入浴…）に合わず「その他」になり、本文がすべて「対応」の欄に入った。**訪問・来所・電話・同行・会議という接触の種類、同席者、聞き取った事実、次の調整の置き場が、項目の上で決まっていない**
- 面接記録に出る四つのものの性質は違う：(a) 接触の種類と同席者は「その面接の出来事」、(b) 聞き取った事実は「本人についての事実（確度・情報源を持つ）」、(c) 次の調整は「記録者の予定」。(b) だけが今の `Record` の形にぴたりと合う

### 1.2 案

**案 1-A：`SupportLog` を使わない。面接は `Record` だけで持つ**

- 聞いた事実を事実ごとの `Record`（`kind: Interview`／職員が見たことは `Observation`）にする。接触の種類は `recordKind` で近づける（会議なら `MeetingMinutes`）。次の調整は `Record {kind: Plan}`。同席者は本文の役割の名前と `TOLD_BY`
- 正典の変化：**無し**（SEMANTICS に書き方の節を足すだけ）
- `SupportLog` は GH・事業所の行動支援の記録に限る

**案 1-B：面接 1 回＝`SupportLog` 1 件。聞いた事実は `Record` に分け、`SupportLog` は接触の一文を根拠に結ぶ（推す）**

- `SupportLog` を「支援の接触の記録」と読み直す。GH の行動支援の記録（状況・対応・効果）も、相談支援の面接（訪問・電話…）も、同じラベルの時系列に並ぶ
- 正典の変化（SCHEMA §4.2・§4.5・§11）：
  - `SupportLog` に任意の項目 **`contactKind`**（列挙 `contactKind`。nest-support だけ）を足す。値は `Visit`（訪問）・`OfficeVisit`（来所）・`Phone`（電話）・`Accompaniment`（同行）・`Meeting`（会議）の 5 つ。合わないときは空のまま（「その他」の値は作らない。分からない値は空にする ADR-001 D7 のとおり）。GH の行動支援の記録は空でよい
  - 既にある項目の意味を SEMANTICS で定める（項目の名前・必須は変えない）：`date`＝接触の日、`situation`＝「どこで・誰と」（同席者は役割の名前で。例「自宅。母と本人」。GH では今までどおり食事・作業などの場面）、`action`＝記録者がしたこと、`nextAction`＝次の調整、`note`＝ほか、`effectiveness`＝行動支援の記録だけが使う
  - 関係は今のまま：`(SupportLog)-[:ABOUT]->(Client)`、`(SupportLog)-[:AUTHORED_BY]->(Staff)`、`(SupportLog)-[:EVIDENCED_BY]->(Record)`
- 案の形（`intake.py`）の変化：最上位に **`supportLog`**（0 か 1 件）を足す。`{"quote", "date", "contactKind"?, "situation", "action"?, "nextAction"?, "note"?}`。`quote` は案の事実の引用のどれか（禁忌・推奨ケアの候補と同じ仕組み。その記録を根拠に結ぶ）。`effectiveness` は案に書かせない（効果の判定は職員が行い、要るなら承認の後に修正の案で足す）。`situation`・`action`・`nextAction`・`note` に、**原文全体に無い数字**を足していれば止める（候補の「引用に無い数字」より広い。面接 1 回のまとめだから）。AI 由来なので `Pending` で入る
- 同席者：`situation` に役割の名前で書く。話し手は事実ごとの `TOLD_BY`。**同席者を人のノードと結ぶ新しい関係は作らない**（名前が個人の情報になる。論点 8 つの 3 は開いたまま。後で `PRESENT_AT` のような関係を足す余地はこの案で塞がれない）

**案 1-C：`SupportLog` は GH の行動支援に限り、面接のために新しいラベル `Contact`（接触の記録）を足す**

- `Contact {contactId✅, date✅, contactKind✅, situation, summary, nextAction}`、接頭辞を一つ足す、`ABOUT`・`AUTHORED_BY`・`EVIDENCED_BY` の始点に `Contact` を足す
- 正典の変化：ラベル 1・接頭辞 1・列挙 1・関係の始点 3 か所・`check_drift` の表 3 か所

### 1.3 推す案と理由、却下した案と理由

**推す：案 1-B**

1. 正典 §4.2 の `SupportLog` の定義「構造を持つ事実。元の文は `Record` に持つ」をそのまま使え、変える項目は任意の 1 つだけ
2. 支援の時系列が一つのラベルに並ぶ。読むスキル（`visit-prep`・`insight-agent`・`neo4j-support-db` の照会）は `SupportLog` を読んでいるので、面接も同じ経路で見える。GH と相談支援の記録が混ざって困る照会は `contactKind` で分けられる
3. 聞いた事実は `Record` に分かれ、禁忌・推奨ケア・食い違い（`CONTRADICTS`）の根拠になれる。はるとの記録 1 の「薬を出し忘れることが二回あった」は、§2 の「飲み忘れはない」との食い違いの材料で、`SupportLog` の本文に埋まっていては使えない
4. 試走の詰まり #5 の原因（場面の選択肢が GH の語彙に固定されていたこと）は field-ui の画面の制約で、ADR-002 で画面はやめる。項目そのものは面接にも使える

**却下：案 1-A**

- 訪問・来所・電話・同行を表す項目が無い（`recordKind` は記録の種類で、接触の手段ではない）。面接 1 回という出来事のノードが無く、「最後に会ったのはいつか」「月に何回接触したか」が引けない
- 次の調整を `Record {kind: Plan}` にすると、確度（`certainty`）を持たない記録者の予定に確度を書くことになる

**却下：案 1-C**

- 新しいラベルは、正典・接頭辞・読むスキル・廃棄（`purge.py` の削除の表）・試験の全部に手が入る。時系列のノードが二つになり、読むスキルが二つを合わせて並べる手間が増える
- 分ける理由（GH と相談支援で語彙が違う）は、`contactKind` と SEMANTICS の書き方で足りる。1-B で `situation` の読み方が現場で混乱すると分かったら、そのときに 1-C に移る（撤退線）

### 1.4 試走の実例への当てはめ（案 1-B）

記録 1・2 には確度の印が無いので、どの事実も `certainty: Unspecified` になる（入口の点検の規則のとおり。格上げしない）。記録者自身の面接記録に印を付けるかは、今回扱わない「Unspecified の扱い」の論点（§7）。

**記録 1（2026-11-01、訪問）**

案（抜粋）：

```json
{"documentKind": "OwnCaseRecord", "clientId": "CLI-…（はると）",
 "facts": [
  {"quote": "自宅を訪問。母と本人に会う。", "recordKind": "Observation", "certainty": "Unspecified", "informantKind": "Agency"},
  {"quote": "本人は居間でお茶を飲みながら、絵カードの予定表を見せてくれた。", "recordKind": "Observation", "certainty": "Unspecified", "informantKind": "Agency"},
  {"quote": "母は「最近、夜に薬を出し忘れることが二回あった」と自分から話した。", "recordKind": "Interview", "certainty": "Unspecified", "informantKind": "Family", "toldBy": "PER-…（母。§2 で入った人）"},
  {"quote": "本人の様子は落ち着いていた。", "recordKind": "Observation", "certainty": "Unspecified", "informantKind": "Agency"}],
 "supportLog": {"quote": "自宅を訪問。母と本人に会う。", "date": "2026-11-01", "contactKind": "Visit",
                "situation": "自宅。母と本人", "action": "母と本人に会い、話を聞いた",
                "nextAction": "次回は主治医への通院に同行する（母と確認）"}}
```

DB に入るもの（すべて `Pending`・`origin: AiExtracted`）：

| ノード／関係 | 値 |
|---|---|
| `SupportLog` | `date: 2026-11-01`、`contactKind: Visit`、`situation: 自宅。母と本人`、`action: 母と本人に会い、話を聞いた`、`nextAction: 次回は主治医への通院に同行する（母と確認）` |
| `(SupportLog)-[:ABOUT]->(Client)`、`-[:AUTHORED_BY]->(Staff)` | 本人と、案を通した職員 |
| `(SupportLog)-[:EVIDENCED_BY {linkedBy, at}]->(Record)` | 引用「自宅を訪問。母と本人に会う。」の記録 |
| `Record` ×4 | 上の `facts`。`documentHash` は記録 1 の原文の指紋（4 件で同じ）。母の話の 1 件は `(Record)-[:TOLD_BY]->(Person 母)` |
| `Record` の `informantKind: Agency`（職員が自分で見たこと） | 論点 2 の案 2-B の決まり（§2.4）。`PROVIDED_BY` が無いので「自分の事業所の職員が見た」と読める |

- 「次回は主治医への通院に同行することを母と確認。」は `nextAction` に入れ、`Record` にはしない（記録者の予定で、本人についての事実ではない）
- 母の「薬を出し忘れることが二回あった」は、§2 の「飲み忘れはない」（母・伝聞）と食い違う。食い違いの案（`CONTRADICTS`）は L-1 の種類「食い違い」で出す。この提案では事実として残すところまで
- `situation` の数字の点検：「二回」は漢数字で、数字の点検（算用数字）の対象にならない。`nextAction` に数字は無い

**記録 2（2026-11-05、電話）**

```json
{"documentKind": "OwnCaseRecord", "clientId": "CLI-…",
 "newPeople": [{"ref": "sister"}],
 "facts": [
  {"quote": "姉から電話。母の体調について「次の母の通院に自分も付き添う」とのこと。", "recordKind": "Interview", "certainty": "Unspecified", "informantKind": "Family", "toldBy": "sister"},
  {"quote": "本人のことで、将来の住まい（グループホーム）を見学したいという希望が姉から出た。", "recordKind": "Interview", "certainty": "Unspecified", "informantKind": "Family", "toldBy": "sister"}],
 "supportLog": {"quote": "姉から電話。母の体調について「次の母の通院に自分も付き添う」とのこと。", "date": "2026-11-05", "contactKind": "Phone",
                "situation": "電話。姉から", "action": "母の体調と、本人の将来の住まいについて聞いた",
                "nextAction": "事業所に見学先の候補を相談する"}}
```

- 姉が §2 の案で既に `Person` として入っていれば `toldBy` は `PER-…`。入っていなければ `newPeople` の `sister`（名前は書かない）。どちらでも、`toldBy` に使われているので論点 3 の「根拠の無い人」にならない
- 「グループホームを見学したいという希望」は**姉の希望**で、本人の `Wish` の案は出さない（原文に無い事実を補わない）
- 「事業所に見学先の候補を相談することにした。」は `nextAction` だけに置く

### 1.5 正典への影響（案 1-B）

- `docs/SCHEMA.md`：**v0.12 → v0.13**。§4.2 の `SupportLog` の行に `contactKind`(enum)、§4.5 に `contactKind`（nest-support だけ）の行、§11 の機械検証ブロックに次の 3 行の差分。変更履歴に一行
  ```
  "SupportLog": {"required": ["supportLogId", "date", "situation"], "optional": ["action", "effectiveness", "note", "nextAction", "contactKind"], ...}
  "enums": {..., "contactKind": ["Visit", "OfficeVisit", "Phone", "Accompaniment", "Meeting"]}
  "enumBindings": {..., "SupportLog.contactKind": "contactKind"}
  ```
  ラベル・接頭辞・関係・必須の項目は変わらない。`check_drift.py` は §4.2・§4.5 の表と JSON の両方を直せば FAIL 0
- 機械検証ブロックの `"version"` は `0.5` のまま（v0.5 以降、文書の版と別に止まっている。`tests/test_canon.py` が `0.5` を固定している）。今回も触らないのを推す（触るなら別の決めごと）
- `docs/SEMANTICS.md`：版の番号を持たない文書なので、節を足す。SEM-ENUM-01 に `contactKind` の表示名 5 行、新しい節 **SEM-REC-04「面接記録の書き方」**（面接 1 回＝`SupportLog` 1 件、`situation`・`action`・`nextAction` の埋め方、同席者は役割の名前、聞いた事実は `Record` に分ける、`effectiveness` は行動支援の記録だけ）
- `docs/SCHEMA.md` §8 の表（前の正典とのつき合わせ）は変えない。HANDOVER の未決論点 4（`SupportLog` に感情・きっかけを足すか）は閉じたまま

### 1.6 共通の約束 v1.1 への影響

- **無し。** `SupportLog` と `contactKind` は nest-support だけのもの。`Record` の項目・`recordKind`・`certainty`・`informantKind` は変わらない。tsunagu-net へ出す提案も無い

### 1.7 既にある試験と道具への影響

| 対象 | 変わること |
|---|---|
| `nest/gate/intake.py` | `TOP_KEYS` に `supportLog`。`_check_support_log`（quote は事実の引用のどれか・`date` は日付・`contactKind` は列挙値・本文の数字は原文全体にあるもの・知らない項目は止める）。`_request` が `SupportLog` のノードと `ABOUT`・`AUTHORED_BY`・`EVIDENCED_BY` を作る |
| `nest/gate/validate.py` | 変更なし（`contactKind` は正典の `enumBindings` から読まれる） |
| `scripts/submit_proposal.py` | 変更なし（件数の表示に `SupportLog` が入る） |
| `scripts/review_proposals.py`・`nest/gate/approve.py` | 変更なし。`list` は `(Client)--(Pending)` で `SupportLog` を拾い、`show` は `EVIDENCED_BY` の先の引用を出す |
| `claude-skills/narrative-extractor/SKILL.md` | 案の形に `supportLog`。「面接記録のときの書き方」の節と、架空の例に面接 1 件 |
| `claude-skills/insight-agent`・`visit-prep`・`neo4j-support-db` | 照会に `contactKind` を出す。`insight-agent` の「同じ場面での不調の繰り返し」は行動支援の記録だけを数えるよう `contactKind IS NULL` で絞るかを L-4 で決める |
| `field-ui/server.py` | 変更なし（ADR-002 で外す。`SupportLogInput` は `extra="forbid"` なので `contactKind` を受けないが、画面から足す必要は無い） |
| 試験（新しく書く） | `tests/test_canon_v013_*.py`（v0.13 の表と JSON）、`tests/test_intake.py`（`supportLog` を通す・quote が事実に無いと止まる・原文に無い数字で止まる・`effectiveness` を書くと止まる）、`tests/test_submit_proposal.py`（記録 1・2 の案が入口を通る）、`tests/test_semantics_enums.py` は `contactKind` の表示名が無いと落ちる（表示名を足せば通る）、`tests/test_narrative_extractor_skill.py`（例に面接が入れば） |
| 試験（変わらない） | `tests/test_canon.py` のラベルの集合・共有の列挙値の試験、`tests/test_gate_validate.py`、`tests/test_field_ui_*` |

## 2. 論点 2：記録者自身の見立ての置き場

### 2.1 今の形と詰まり #9

- `Record.informantKind` は 5 値（`Self`・`Family`・`Agency`・`Neighbor`・`DocumentOnly`。tsunagu-net の ENU-04 と同じ）で必須。「記録者自身」に当たる値は無い
- 確度 `Inference` は、約束 3 と tsunagu-net の ENU-03 で「**記録者の推測**で、事実ではない」と定義されている。つまり **`Inference` の記録は、定義の上で記録者（`AUTHORED_BY` の `Staff`）が主体**になっている
- 試走の fact-11「ヘルパーの交代が多いと落ち着かないのだろうと、私（相談支援専門員）は受け取りました。【推測】」は、Claude が `informantKind` を空にし、受付の検証で止まった（止まったことは正しい）
- tsunagu-net の入口の試験（`tests/test_intake.py`）には「保育所の送り迎えと夕食の用意も翔太がしている様子【本人の話からの推測】」を `certainty: Inference`、`informantKind: Agency`（提供元の機関の記録）で通す例がある。tsunagu-net では、見立ても「どの情報源の話から記録者が推し量ったか」で情報源を付けている

### 2.2 案

**案 2-A：`informantKind` に値を足す**

- 値 `Recorder`（表示名「記録者自身」）を足す。見立ては `certainty: Inference`・`informantKind: Recorder`
- 正典の変化：SCHEMA §4.5 と §11 の `informantKind`、SEMANTICS SEM-ENUM-01 に 1 行。**約束 3 の文（情報源は「本人・家族・機関・近隣・既存の記録だけ」）を変えることになる**（§2.6）
- tsunagu-net の正典（SCHEMA の `informantKind`、SEMANTICS ENU-04）にも同じ値を足す提案が要る。tsunagu-net が受けるまで、二つの DB で列挙値がそろわない

**案 2-B：値を足さない。見立ては `certainty: Inference` の `Record` で持ち、`informantKind` は見立てのもとになった情報源、記録者は `AUTHORED_BY` で表す（推す）**

- SEMANTICS に決まりを書く（SEM-REC-04 の一部）：
  - 見立て（記録者の受け取り方・推測）は、原文で【推測】の印を付けた一文を `Record` にする。`certainty: Inference`（印から。入口の点検がそのまま決める）
  - `informantKind` は、**その見立てのもとになった話・観察の情報源**：本人の話から → `Self`、家族の話から → `Family`、職員が自分で見たこと（観察）から → `Agency`（自分の事業所。`PROVIDED_BY` の無い `Agency` は自分の事業所の職員の見聞と読む）、既存の記録だけから → `DocumentOnly`
  - `TOLD_BY` は張らない（誰かが言ったことではない）。記録者は `AUTHORED_BY` の `Staff`
  - `recordKind` は、面接の中で受け取ったなら `Interview`、観察からなら `Observation`
  - 見立ては禁忌・推奨ケアの候補の根拠（`EVIDENCED_BY`）になれる。候補は根拠の確度を引き継ぐので `Inference` のまま（約束 4-3。格上げしない）。入口の点検は、根拠が見立てだけの候補に注意を出す（止めない）
- 正典の変化：**SCHEMA は無し。SEMANTICS に節を足す**
- 案の形の変化：無し。入口の点検に「`certainty` が `Inference` で `informantKind` が無いときは、もとになった情報源を書くよう理由を出して止める」を足す（論点 3 の案 3-A の一部）

**案 2-C：見立てを `Record` にせず、`SupportLog.note` か新しいラベル（`Assessment`）に置く**

- 見立ては事実ではないので、事実の記録（`Record`）と分ける考え方
- 正典の変化：`note` に置くなら無し。新しいラベルなら 1-C と同じ規模

### 2.3 推す案と理由、却下した案と理由

**推す：案 2-B**

1. 約束 3 の定義「`Inference`＝記録者の推測」と、`AUTHORED_BY` が記録者を指すことで、**記録者が主体であることは既に表せている**。足りないのは「見立てに何の情報源を書くか」の決まりで、値ではない
2. 「本人の話から受け取った見立て」と「母の話から受け取った見立て」を分けて読める。`Recorder` 一つにまとめると、この区別が落ちる（見立ての強さは、もとの話が誰のものかで変わる）
3. 共通の約束と二つの DB の列挙値を変えない。tsunagu-net の入口の試験の例（上の 2.1）と同じ読み方になる
4. 読む側（`review_proposals show`、照会口）は、確度「推測」を見れば見立てだと分かる。表示に「見立て」と添えるのは読む道具の側で足せる（L-2 の `show_pending`）

**却下：案 2-A**

- 約束 3 の文と二つの正典を変える。tsunagu-net が受けるまで、同じ名前の列挙値の中身が二つの DB で違う期間ができる（§4.5 の `clientRelationKind` を別の名前にした理由と同じ心配）
- 「記録者自身」は情報源の軸（誰から聞いたか）ではなく、確度の軸（`Inference`）に既に入っている。情報源に足すと、確度と情報源を混ぜない決まり（ADR-001 D4）に触れる
- ただし、「職員自身の観察を `Agency` と読む」ことに違和感が残るなら、2-A が次の候補（§6 の決めごと 7）

**却下：案 2-C**

- `note` に置くと、引用・確度・情報源・`documentHash` が無く、点検（約束 4）が働かない。後で食い違い（`CONTRADICTS`）の材料にも、承認の対象にもならない
- 新しいラベルは 1-C と同じ理由。tsunagu-net の「見立ての要約」は読み取りの出力であって、保存のラベルではない

### 2.4 試走の実例への当てはめ（案 2-B）

**fact-11**（§2 の第 3 段落の最後の一文）：

```json
{"quote": "ヘルパーの交代が多いと落ち着かないのだろうと、私（相談支援専門員）は受け取りました。",
 "recordKind": "Interview", "certainty": "Inference", "informantKind": "Self"}
```

| ノード／関係 | 値 |
|---|---|
| `Record` | `kind: Interview`、`certainty: Inference`（印【推測】から）、`informantKind: Self`（直前の本人の話「ヘルパーさんは、おふろの日に来る人がいい」から受け取った見立て）、`quote` は上の一文、`text` は省くか言い換え、`documentHash` は §2 の原文の指紋 |
| `(Record)-[:ABOUT]->(Client)`、`-[:AUTHORED_BY]->(Staff)` | 本人と、案を通した職員（記録者） |
| `TOLD_BY` | 張らない |
| 候補 | この一文から推奨ケアの候補（例：ヘルパーを固定する）は**作らない**。原文に「どう支えるか」が無い。作るなら根拠は `Inference` の記録一つで、入口の点検が注意を出す |

- 記録 1 の職員の観察 3 件（「自宅を訪問。母と本人に会う。」など）は、見立てではないが同じ決まりの「職員が自分で見たこと」で `informantKind: Agency`（§1.4）
- Library の `fixtures_kakuu_3cases.md` の「【推定】本人は決めることに関わりたい気持ちと不安の両方を持っていると、私は受け取った。」（A-1）と「【推定】本人は麦の制限を自分で理解していると私は受け取った。」（C-2）も同じ形になる（印は【推測】に、位置は文の直後に直してから。`docs/fixtures/` に移すときに）

### 2.5 正典への影響（案 2-B）

- `docs/SCHEMA.md`：**無し**（版は上がらない。1-B と合わせて v0.13 にするときは、変更履歴に「見立ての書き方は SEMANTICS SEM-REC-04」と一行）
- `docs/SEMANTICS.md`：SEM-REC-04 に「見立て」の項（上の 2.2 の箇条）。SEM-ENUM-02（原文の印）は変わらない
- 機械検証ブロックの差分：無し

### 2.6 共通の約束 v1.1 への影響

- 案 2-B：**無し**
- 案 2-A を採る場合：約束 3 の「情報源（本人・家族・機関・近隣・既存の記録だけ）」に「記録者自身」を足す改訂（v1.2）が要り、両方の正典に反映する。tsunagu-net へ出す提案の要旨（tsunagu-net は変えない。台帳 G-40 と同じ経路）：
  > `informantKind` に `Recorder`（記録者自身。表示名「記録者自身」）を足す。用途は、記録者の見立て（`certainty: Inference`）と、記録者自身の観察（`kind: Observation`）の情報源。ENU-04 に「`Recorder`：記録した職員自身。見立てと観察に使う。他の人・機関から聞いたことには使わない」を足す。入口の点検（`tsunagu/gate/intake.py`）の列挙値は正典から読むので、正典の版上げだけで通る。既にある記録の値は変えない

### 2.7 既にある試験と道具への影響（案 2-B）

| 対象 | 変わること |
|---|---|
| `nest/gate/intake.py` | `certainty: Inference` で `informantKind` が無い事実に、理由（「見立ては、もとになった情報源を書く：本人の話なら Self…」）を出して止める。根拠が `Inference` の記録だけの候補に注意 |
| `nest/gate/validate.py`・`write.py` | 変更なし |
| `claude-skills/narrative-extractor/SKILL.md` | 「守ること」に 9 として見立ての書き方。架空の例に【推測】の一文を足す |
| `scripts/review_proposals.py`（と L-2 の `show_pending`） | 確度が `Inference` の引用に「見立て」と添える（任意。読む側の表示だけ） |
| 試験（新しく書く） | `tests/test_intake.py`（見立てが `Self` で通る・`informantKind` 無しは入口で止まり理由に「情報源」が出る）、`tests/test_narrative_extractor_skill.py`（例の見立てが入口と検証を通る）、`tests/test_submit_proposal.py`（fact-11 を含む §2 の案が通る。今の `test_fixture_section_2_passes_the_intake_check` は全部の事実に `Family` を付けて通している。2-B の規則は `informantKind` が無いときだけ止めるので、この試験は落ちないが、見立ての行だけ `Self` にする形に直すのが望ましい） |
| 試験（変わらない） | `tests/test_canon.py::test_repository_canon_shared_enums_match_contract`（5 値のまま）、`tests/test_semantics_enums.py` |
| 案 2-A のとき | 上に加えて `tests/test_canon.py` の共有の列挙値の試験・`tests/test_semantics_enums.py`・`validate.py` は正典から読むので変更なし。tsunagu-net の正典が変わるまで「nest-support だけの値」として §10 に書く |

## 3. 論点 3：入口の点検で見る範囲

### 3.1 今の形と詰まり #9・#10

- 入口の点検（`intake.check`）が見ているもの：知らない項目、`documentKind`、提供元、`clientId` の形、引用が原文にあるか、本文の数字、`toldBy` の指し方、確度が原文の印と合うか、関わりと候補の規則、`newPeople` の `ref` の形。**見ていないもの**：`recordKind`・`informantKind` の有無と列挙値（確度は印との比較で実質的に見ている）。欠けは受付の検証（`validate`）まで進んで「必須の `informantKind` が無い」で止まる（#9。止まる結果は同じで、理由が遅く出る）
- `newPeople` のうち、どの事実の `toldBy` にも、どの関わりの `concerns` にも使われない人は、注意を出して通す（#10 の直し。2026-11-09）。通ると、根拠の記録にも本人にも結ばれない `Person` が `Pending` で入り、`review_proposals show` では「本人「―」、根拠の引用：無い」と出る
- 受付の検証は、`Person` に結びつきを求めていない（禁忌・推奨ケア・本人以外の人への関わりには根拠を求めている）

### 3.2 案

**案 3-A：入口で、必須の項目と列挙値まで見る。根拠の無い新しい人は入口で止める（推す）**

- 入口の点検に足すもの：
  1. 事実ごとに `recordKind`・`informantKind` が有ること、値が正典の列挙にあること（正典の JSON から読む。直さずに止める）
  2. `certainty: Inference` で `informantKind` が無いときの理由（論点 2 の 2-B）
  3. `newPeople` の使われない `ref` は**止める**（今の注意から変える）。理由：「どの事実の `toldBy` か関わりの `concerns` に書くか、案から外す」
  4. 論点 1 の `supportLog` の必須（`date`・`situation`・`quote`）と列挙値（`contactKind`）
- 受付の検証（`validate.py`）に足すもの：**AI 由来（`AiExtracted`）の `Person` は、同じ依頼の中で `TOLD_BY` の終点か、`CONCERNS` の終点か、`RELATED_TO` の始点のどれかであること**。無ければ止める。入口を通らない道（L-1 の受付 MCP が別の形を受けるとき）でも同じ規則が働く。人が端末で登録する `Person`（`origin: Human`）は対象にしない（今はその道具は無い）
- 「根拠」の形：`Person` を `EVIDENCED_BY` の始点に足さない。新しい人の根拠は、その人が話した記録（`TOLD_BY`）か、その人についての関わり（`CONCERNS`）か、本人との関係（`RELATED_TO.evidenceRecordIds`）で足りる。L-1 で案の形に `RELATED_TO`（事例 A の `Person`＋`RELATED_TO`）が入れば、それも根拠に数える
- 正典の変化：**無し**

**案 3-B：入口は今のまま。受付の検証にだけ `Person` の結びつきの規則を足す**

- 理由の出る場所は変わらない（遅い）が、止まる結果はそろう。入口の試験は増えない

**案 3-C：今のまま（必須は受付の検証で、人は注意だけ）**

- 根拠の無い人は `Pending` で入り、承認する人が「根拠の引用：無い」を見て差し戻す

### 3.3 推す案と理由、却下した案と理由

**推す：案 3-A**

1. 入口の点検は「Claude の案を直してもらう」ための点検で、理由が早く・具体的に出るほど、職員が止めた行を Claude に貼る（手順書 4.5 (c)）だけで直る。受付の検証の理由（「ノード 13（fact-11）：必須の informantKind が無い」）は正典の言葉で、入口の理由（「事実 11：見立ては、もとになった情報源を書く」）は案の言葉
2. 根拠の無い `Person` は、承認の画面で引用が無く、承認する材料が無い。入る前に止めるほうが、差し戻しの記録（`Reject`）を増やさない
3. 受付の検証にも規則を置くのは、L-1 で案の入口が増える（五つの種類）ため。入口だけに置くと、別の入口から同じ穴が開く
4. 正典を変えずにできる

**却下：案 3-B**

- #9 の「理由が遅く出る」が残る。入口と受付で二重に見るのは、tsunagu-net の入口と受付の分担（入口は原文との突き合わせ、受付は正典の形）と同じで、重なりは問題にならない

**却下：案 3-C**

- 承認する人の目に頼る。一人で使う前提（自己承認）では、注意を読み飛ばすと根拠の無い人が確定する

### 3.4 試走の実例への当てはめ（案 3-A）

**根拠の無い Person**（#10。案の `newPeople` に、どの `toldBy`・`concerns` にも使われない `ref` が 1 件）：

- 入口の点検：`止めた：newPeople の neighbor は、どの事実の toldBy にも、どの関わりの concerns にも使われていない。どの事実の toldBy か関わりの concerns に書くか、案から外す`。DB には何も入らない。職員はこの行を Claude Desktop に貼り、作り直してもらう
- 受付の検証（入口を通らない道から来た場合）：`ノード 2（neighbor）：AI 由来の Person は、同じ依頼の中で TOLD_BY・CONCERNS・RELATED_TO のどれかで結ぶ`
- 作り直した案で、その人が「近所の人の話では…」の `toldBy` に使われれば、`(Record)-[:TOLD_BY]->(Person)` が根拠になり、通る。`Person` は `Pending` で入り、`show` に引用が出る

**fact-11**（#9）：案 2-B と合わせて、`informantKind` が無ければ入口で `止めた：事実 11：見立て（確度 推測）には、もとになった情報源を informantKind に書く（本人の話なら Self、家族の話なら Family、職員の観察なら Agency、記録だけなら DocumentOnly）`。`Self` を書いた案は通る

**記録 1・2**：`supportLog` の `date` が無い・`contactKind` が列挙に無い（例：「訪問」と日本語で書く）は入口で止まる（直さずに止める。ADR-001 D7）

### 3.5 正典への影響

- 無し。SCHEMA・SEMANTICS の版は上がらない（SEM-REC-04 に「新しい人には根拠が要る」の一文を足すのを推す）

### 3.6 共通の約束 v1.1 への影響

- 無し。約束 4 の「型に無い項目は自動で直さずに止める」「人は名前で同定しない」の範囲の中

### 3.7 既にある試験と道具への影響（案 3-A）

| 対象 | 変わること |
|---|---|
| `nest/gate/intake.py` | 事実の `recordKind`・`informantKind` の有無と列挙値。使われない `newPeople` を注意から誤りに。`supportLog` の点検 |
| `nest/gate/validate.py` | `_check_person_tied`（AI 由来の `Person` の結びつき） |
| `scripts/submit_proposal.py` | 変更なし（注意・止めた行の出し方は今のまま） |
| `docs/OPERATIONS.md` 4.5 (c) | 変更なし（「点検でもゲートでも止まれば何も入らない」のまま。段階 M で書き直す） |
| 試験（変わる） | `tests/test_intake.py::test_new_person_tied_to_nothing_gets_a_warning` → 止まる形に書き直す（名前も `_is_stopped` に）。`tests/test_submit_proposal.py::test_gate_stop_tells_how_to_fix` は「`informantKind` の無い事実が**受付の検証**で止まる」ことを前提にしているので、入口で止まるようになると前提が崩れる。受付でだけ止まる例（例：`write.submit` の二重登録や、職員が `Active` でない）に差し替えるか、受付を差し替えて「止めた（ゲート）」の文言だけを確かめる形にする |
| 試験（新しく書く） | `tests/test_intake.py`（`recordKind` 無し・列挙に無い `informantKind`・見立ての理由・使われない人で止まる。両方向：使われる人は通る）、`tests/test_gate_validate.py`（AI 由来の `Person` が結ばれていないと止まる。`TOLD_BY`・`CONCERNS`・`RELATED_TO` のどれかで通る。`Human` の `Person` は対象外） |
| 試験（変わらない） | `tests/test_gate_write.py`、`tests/test_involvement_concerns_person.py`、`tests/test_intake_care_candidates.py` |

## 4. 三つの論点のつながり（組み合わせ）

| 論点 1 | 論点 2 | 論点 3 | 正典の版 | 約束 v1.1 | 評価 |
|---|---|---|---|---|---|
| **1-B** | **2-B** | **3-A** | SCHEMA v0.13（`contactKind` だけ）。SEMANTICS に SEM-REC-04 | 変えない | **推す。** 入口の点検に `supportLog` の欄・見立ての理由・必須の項目が一度に入る。tsunagu-net へ出す提案は無い |
| 1-B | 2-A | 3-A | SCHEMA v0.13（`contactKind` と `informantKind` の値） | **変える（v1.2）** | 見立ての表し方は分かりやすいが、tsunagu-net が受けるまで列挙値がずれる。tsunagu-net へ提案文が要る |
| 1-A | 2-B | 3-A | SCHEMA は変えない。SEMANTICS だけ | 変えない | 正典に手が入らないが、面接 1 回のノードが無く、接触の種類が残らない。読むスキルの時系列が `Record` の `heardOn` だけになる |
| 1-C | 2-B | 3-A | SCHEMA v0.13（ラベル・接頭辞・関係の始点） | 変えない | 時系列のノードが二つ。読むスキル・廃棄・試験の手直しが最も多い |
| 1-B | 2-B | 3-B／3-C | 同上 | 変えない | `supportLog` の必須の欠けも、見立ての情報源の欠けも、受付の検証まで進んでから止まる（#9 の「理由が遅い」が残る）。**1-B を採るなら 3-A をそろえるのを推す** |
| 1-B | 2-B | 3-A（ただし `Person` の規則を受付に置かない） | 同上 | 変えない | 入口を通る案には足りるが、L-1 で入口が増えると穴になる |

論点どうしの依存：
- 1 → 3：`supportLog` の欄を足すなら、その必須を入口で見る（3-A の 4）。1-A なら 3-A の 4 は要らない
- 2 → 3：2-B は「見立てには情報源が要る」の決まりを入口で伝える（3-A の 2）。2-A なら、値を足すだけで入口の変更は列挙値の読み込みだけ
- 1 → 2：1-B で職員の観察（`Observation`）を `Record` に分けると、「職員自身の見聞の情報源は `Agency`」の読み方（2-B）が面接記録でも使われる。1-A でも同じ

## 5. 推す組み合わせ

**1-B ＋ 2-B ＋ 3-A。**

- 正典の版上げは SCHEMA v0.13 の一回（`SupportLog.contactKind` と列挙 `contactKind` を足す。ラベル・関係・必須の項目・共有の列挙値は変えない）。SEMANTICS に SEM-REC-04（面接記録の書き方・見立ての書き方・新しい人の根拠）と `contactKind` の表示名
- 共通の約束 v1.1 は変えない。tsunagu-net へ出す提案は無い
- コードの変更は入口の点検（`supportLog`・必須の項目・見立ての理由・使われない人）と受付の検証（AI 由来の `Person` の結びつき）だけ。書き込み（`write.py`）・承認（`approve.py`）は変わらない
- ADR-002 の正典の版上げ（`ChangeProposal`・`TARGETS`・`changeKind`。段階 L の最初）とは**別の版**にする（v0.13 → v0.14）。試験を分けて書けるため。一つにまとめるかは河原さんの判断（§6 の 12）
- 順：河原さんの可否 → 段階 L の最初に、試験を先に書いて v0.13（1-B）と SEM-REC-04（2-B）と入口・受付の規則（3-A）を入れる → `check_drift.py` FAIL 0・`uv run pytest -q` → L-1 に進む

## 6. 河原さんに決めてもらうこと（はい／いいえ）

論点 1

1. 面接 1 回を `SupportLog` 1 件にし、聞いた事実は `Record` に分ける（案 1-B）。── はい／いいえ（いいえなら 1-A か 1-C を指定）
2. `SupportLog` に任意の項目 `contactKind`（`Visit`・`OfficeVisit`・`Phone`・`Accompaniment`・`Meeting` の 5 値。nest-support だけ。「その他」は作らない）を足す。── はい／いいえ
3. 同席者は `situation` に役割の名前で書き、人のノードと結ぶ新しい関係は作らない。── はい／いいえ
4. `SupportLog` の根拠（`EVIDENCED_BY`）は、案の事実の引用 1 つ（接触の一文）に結ぶ。── はい／いいえ（いいえなら、同じ案の全部の事実に結ぶ）
5. `effectiveness` は案に書かせない（判定は職員。要るなら承認の後に修正の案で）。── はい／いいえ

論点 2

6. 見立ては値を足さずに表す（`certainty: Inference`、`informantKind` はもとになった情報源、記録者は `AUTHORED_BY`。案 2-B）。── はい／いいえ（いいえなら 2-A。約束 v1.2 と tsunagu-net への提案が要る）
7. 職員自身の観察・見立ての情報源を `Agency`（自分の事業所）と読む。── はい／いいえ（いいえなら、`Recorder` の値を足す 2-A に戻る）
8. 根拠が見立て（`Inference`）の記録だけの禁忌・推奨ケアの候補は、入口の点検が**注意を出して通す**。── はい／いいえ（いいえなら止める）

論点 3

9. 入口の点検で、事実の `recordKind`・`informantKind` の有無と列挙値、`supportLog` の必須と列挙値を見る（案 3-A）。── はい／いいえ
10. どの `toldBy`・`concerns` にも使われない新しい人は、入口で**止める**（今の注意から変える）。── はい／いいえ
11. 受付の検証にも「AI 由来の `Person` は同じ依頼の `TOLD_BY`・`CONCERNS`・`RELATED_TO` のどれかで結ばれている」規則を足す。── はい／いいえ

正典の版

12. 今回の正典の変更を SCHEMA v0.13 とし、ADR-002 の `ChangeProposal` の版上げ（v0.14）と分ける。── はい／いいえ（いいえなら一つの版にまとめる）
13. 機械検証ブロックの `"version"`（`0.5`）は今回も触らない。── はい／いいえ

## 7. 今回扱わなかった論点との関係（一行ずつ）

- **Unspecified の扱い**：記録 1・2 のように印の無い記録者自身の面接記録は、今の規則では全部 `Unspecified` になる。1-B はこれを変えないし塞がない（面接記録に印を付ける運用にするか、記録者の観察を別に読むかは、別の決めごと）
- **仮名の取り違え（論点 8 つの 7）**：`supportLog` の欄は本人の指定（`clientId`）を変えない。塞がない
- **照会の記録（論点 8 つの 8）**：読み取りの道具は触れていない。塞がない
- **同席者を関係で持つか（論点 8 つの 3）**：1-B は `situation` の役割の名前で持つ。後で関係を足す余地は残る
- **条番号**：この提案に条番号は無い

---

読んだもの：`docs/proposals/2026-11-09-interview-record-shape.md`、`docs/journal/2026-11-08-n46-trial.md`（#5・#7・#9・#10・注意）、`docs/SCHEMA.md` v0.12（§3・§4・§6・§7・§8・§9・§10・§11）、`docs/SEMANTICS.md`、`docs/adr/ADR-001`（D4〜D9）・`ADR-002`（D1〜D6・受け入れ試験・未決論点）、`nest/gate/intake.py`・`validate.py`・`write.py`・`approve.py`（引用の照会）・`purge.py`（削除の表）、`scripts/submit_proposal.py`・`review_proposals.py`・`check_drift.py`、`nest/canon.py`、`claude-skills/narrative-extractor/SKILL.md`、`tests/test_intake.py`・`test_submit_proposal.py`・`test_canon.py`・`test_canon_v012_audit_reason.py`・`test_semantics_enums.py`・`test_gate_review.py`（試験の名前と前提）、`field-ui/server.py`・`static/record-form.html`（場面の選択肢）、`fixture_kakuu_haruto.md`、Library の `fixtures_kakuu_3cases.md`（事例の中身だけ）、tsunagu-net の `docs/contracts/nest-support-shared.md` v1.1・`docs/SCHEMA.md` v0.31（`Record`・`Meeting`・列挙値）・`docs/SEMANTICS.md` v0.32（ENU-03・04・09、BRS-08）・`tests/test_intake.py`（`Inference` の例）・HANDOVER。DB は起動していない。tsunagu-net は変えていない。
