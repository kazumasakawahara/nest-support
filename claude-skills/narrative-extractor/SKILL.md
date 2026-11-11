---
name: narrative-extractor
description: 母親・支援者の語り（ナラティブ）、自分の面談・面接記録、他の機関からの情報提供の書面から、nest-support の「書き込みの案」（JSON）を作り、対象の仮名を職員に復唱して確かめてから、書き込み受付（MCP nest-gate の submit_proposal）に出すスキル。Claude は DB に直接書かない（書くのはゲートで、未確定で入る）。「テキストから抽出」「情報を抽出して」「ナラティブから登録」「この文章を構造化して」「データベースに登録して」「面談記録を入力」「面接記録を入力」「聞き取り内容を登録」などの発言時、および .docx/.xlsx/.pdf/.txt ファイル添付時に使う。
---

# narrative-extractor：語りから書き込みの案（JSON）を作り、書き込み受付に出す

## 概要

語り・面談記録・面接記録・情報提供の書面から**書き込みの案（JSON）を作り**、職員の確かめを経て**書き込み受付（MCP `nest-gate` の `submit_proposal`）に出す**スキル（計画 N-25、段階 L の L-1。ADR-001 D6、ADR-002 D1・D2）。

- **Claude は DB に書かない。** 書くのはゲート（`nest/gate/intake.py` → `validate.py` → `write.py`）だけで、書き込み受付がゲートに渡す。このスキルから Cypher を流さない
- 書き込み受付は、案を原文と突き合わせる（入口の点検）。原文に無い引用、引用に無い数字、原文の印と違う確度、型に無い項目は、直さずに止まる
- 通った案は、ゲートが AI 由来として **未確定（Pending）** で書き、職員が引用を見て一件ずつ承認する（D9）
- 外部の API は使わない。案を作るのは Claude 自身

## 守ること

1. **原文に無いことを書かない。** 推し量らない。分からない項目は書かない（null で埋めない）
2. **引用（`quote`）は原文からそのまま写す。** 空白・改行の違いだけは点検が無視する。言い換えは `text` に書いてよいが、引用に無い数字（日付・回数・金額・年齢・体重など）を足さない
3. **確度は原文の印で決める。** 引用の直後（同じ行）の【…】を読む：【確認済み】→ `Confirmed`、【本人の話】→ `SelfReport`、【伝聞】【未確認】→ `Hearsay`、【推測】→ `Inference`。印が無ければ `Unspecified`。重なったら弱いほう。上げも下げもしない
4. **人を名前で結び付けない。** 既にいる人は ID（`PER-…`）、案の中の新しい人は名札（`ref`）、本人は `client` で指す。名前の似た人を同じ人と決めない（D8）
   - 名札は英小文字で始め、英字・数字・ハイフンだけ（例：`mother`・`supportWorker`・`sister-2`）。一人に一つ。点検が使う名札（`client`・`provider`・`support-log`・`fact-1` のような「種類-番号」）は使わない
5. **語りの中の人は役割の名前で書く**（母・主治医・担当の相談員）。新しい人の名札にも実名を入れない（SEMANTICS SEM-REC-01。台帳 G-42）
6. **年のない日付に年を足さない。** 「10月2日」は引用のまま残し、`aboutDate` には年まで原文にあるときだけ書く
7. **機関 ID を書かない。** 書面の提供元は原文の名前（`providerName`）だけを書く。職員が候補から選ぶ（N-24）。「区役所の窓口で」のような名前の無い言及は `involvements` に書き、機関は担当機関の推定の候補からだけ選ぶ（N-24a）
   - 関わりの引用に機関の名前（呼び名を含む。例：「つばさ」）が書かれていれば、その関わりの `orgName` に引用のとおりに写す（引用に無い名前は止まる）。サービスの種類（例：生活介護）が原文に書かれていれば `serviceTypeName` に写す。機関 ID は書かない。結ぶ機関は、返事の候補から職員が選ぶ（手順 6）
   - `orgName` のある関わりで、原文から今も続いていると読めるとき（「通っている」「利用している」など）だけ `howEnded` に `Ongoing` を書く。読めなければ書かない（推し量って書かない。`Unknown` で入る）。`orgName` の無い関わりには書かない。原文に、もうやめた・通っていないとある終わった関わりは、今は `involvements` に書けない（止まる）。事実として `facts` に残すだけにする
8. **本人の `clientId` は書かない。** 本人は仮名（`C-……`）で指し、書き込み受付が仮名から入れる。clientId は書かない（別の本人の ID が書いてあると止まる）
9. **事実ごとに `recordKind` と `informantKind` を必ず書く**（正典の値だけ。日本語や別の値に読み替えない）
   - 接触そのものを述べる一文（記録者がしたこと・見たこと。例：「自宅を訪問。母と本人に会う。」「姉から電話。」「事業所の生活支援員から電話で聞き取りました。」「〜に電話し、様子を聞いた」）は `Observation`。相手が語った中身（例：「本人は週五日、休まず通っているとのこと。」「母は『夜に薬を出し忘れた』と話した。」）は `Interview`。「聞き取りました」と書いてあっても、聞いたという行為を述べるだけの一文は `Observation` にする
10. **見立て**（記録者自身の受け取り方・推測。原文の【推測】の一文）は、値を足さずに書く（SEMANTICS SEM-REC-04）：`certainty: Inference`、`informantKind` はその見立てのもとになった情報源（本人の話から `Self`、家族の話から `Family`、職員が自分で見たことから `Agency`、記録だけから `DocumentOnly`）。`toldBy` は書かない（誰かが言ったことではない）。根拠が見立てだけの禁忌の候補は作らない（止まる）。推奨ケアの候補は作れるが注意が付く
11. **面接記録**（訪問・来所・電話・同行・会議・文書のやり取り）は、面接 1 回を `supportLog` 一つにし、聞いた事実・見たことは事実ごとに `facts` に分ける（SEM-REC-04）。`supportLog` の `quote` は接触の一文の事実の引用。同席者は `situation` に役割の名前で書く。次の調整は `nextAction` に置き、事実にしない。`effectiveness` は書かない（効果の判定は職員）。`supportLog` の本文に原文に無い数字を足さない
12. **新しい人（`newPeople`）は、どれかの事実の `toldBy` か関わりの `concerns` に使う。** どこにも使わない人は案に入れない（止まる）
13. 開発と試験では架空の文だけを使う

## 案の形

```text
{"documentKind": "OwnCaseRecord"（自分の記録） | "ProvisionDocument"（他の機関からの書面）,
 "providerName": 書面のときだけ。原文に書かれた提供元の名前,
 "receivedOn": "YYYY-MM-DD"（書面を受けた日。任意）,
 "newPeople": [{"ref"}]（任意。役割の名前で呼ぶ人。実名は書かない）,
 "facts": [{"quote", "text"?, "recordKind", "certainty", "providerCertainty"?（書面のとき）,
            "informantKind", "aboutDate"?, "heardOn"?, "toldBy"?}],
 "involvements": [{"quote", "kind", "orgName"?（引用に書かれた機関の名前）, "serviceTypeName"?（原文のサービスの種類）, "howEnded"?（"Ongoing" だけ。orgName のあるときだけ）, "orgId"?, "concerns"?}]（任意）,
 "ngActions": [{"quote", "action", "riskLevel", "reason"?}]（任意。禁忌の候補）,
 "carePreferences": [{"quote", "category", "instruction", "priority"?}]（任意。推奨ケアの候補）,
 "supportLog": {"quote", "date", "contactKind"?, "situation", "action"?, "nextAction"?, "note"?}（任意。面接記録。面接 1 回に一つ）}
```

- `recordKind`：`Observation`（職員が見た）・`Interview`（聞いた）・`Notification`・`MeetingMinutes`・`Plan`・`Document`
- `informantKind`：`Self`（本人）・`Family`・`Agency`・`Neighbor`・`DocumentOnly`
- 書面では確度を二段で持つ：`providerCertainty` は原文の印、`certainty` は受けた側から見た確度（点検が決まった値を求める）
- `riskLevel`：`LifeThreatening`（生命に関わる）・`Panic`（パニック誘発）・`Discomfort`（不快）。`priority`：`High`・`Medium`・`Low`
- `contactKind`：`Visit`（訪問）・`OfficeVisit`（来所）・`Phone`（電話）・`Accompaniment`（同行）・`Meeting`（会議）・`Correspondence`（文書・メール・FAX 等）。合わなければ書かない。`date` は接触の日（`YYYY-MM-DD`。原文に年まであるときだけ）
- 書き込み受付は、今は自分の記録（`OwnCaseRecord`）だけを受ける。書面の案は作れるが、出すと止まる

## 禁忌・推奨ケアは二段で扱う（台帳 G-63。正典 v0.9 §6）

1. **根拠が同じ案の中にあるとき**：その話をまず事実（`facts`）として引用で残し、`ngActions`・`carePreferences` の候補の `quote` に、その事実の引用をそのまま書く。ゲートが根拠（`EVIDENCED_BY`）で結び、`Pending` で入れる。承認は一つずつ
   - 候補に確度を書かない（根拠の事実の確度を引き継ぐ）
   - `action`・`instruction` などに、引用に無い数字を足さない
   - 根拠が見立て（`Inference`）だけなら、禁忌の候補にしない（守ること 10）
2. **根拠が同じ案の中に無いとき**（前に聞いた話・職員の記憶など）：候補にしない。分かっている範囲を事実として残し、「禁忌の候補」として引用を並べて職員に知らせる（禁忌には根拠の記録が要る。SEMANTICS SEM-REC-03）

## 手順

1. 原文を受け取る（貼り付け・添付）。対象の本人の仮名（`C-……`）を職員に聞く（名前から探さない。clientId は書かない）
2. 上の「守ること」に沿って案（JSON）を作る
3. 案の要点（事実の件数・面接記録・禁忌と推奨ケアの候補）と、候補にできなかった「禁忌の候補」（引用の一覧。二段の 2）を職員に示す
4. **仮名を復唱する**：「対象は C-…… の本人です。この本人に未確定で入れてよいですか」と仮名を一字ずつそのまま書いて聞き、職員の「はい」を待つ。違うと言われたら仮名を聞き直す。「はい」が無ければ出さない
5. 「はい」の後に、書き込み受付（MCP `nest-gate`）の submit_proposal を呼ぶ：`code` に仮名、`original` に職員が渡した原文をそのまま、`proposal` に案
6. 返事の `summary`（入れた先の仮名と件数。止まったときは「…には何も入れていない（0 件）」）を、通っても止まっても最初にそのまま伝え、仮名と件数を職員に見てもらう（復唱した仮名と同じか）
   - **通ったら**（`ok` が真）：「未確定で入った。承認は職員が一件ずつ、引用を見てから行う」を伝える。注意（`warnings`）があれば、そのまま伝える
   - **機関の候補（`orgChoices`）があれば**：関わりごとに、候補を番号つきで見せる（名前・種類・所在地の市区・サービスの種類。返事の順のまま。並べ替えない・減らさない。`truncated` なら「上限で切れている」と添える）。「『つばさ』の機関はどれですか。番号で答えてください。無ければ『無い』と答えてください」と尋ねる。**自分で選ばない**（候補が一件でも尋ねる。案のサービスの種類と合いそうでも決めない）。番号が返ったら、その候補の機関 ID で `link_organization`（`nest-gate`）を呼ぶ（`code` は仮名、`involvement_id` と `org_name` は `orgChoices` のとおり）。返事の `summary` をそのまま伝える。「無い」と言われたら結ばない（関わりは機関未確定のまま）。候補が 0 件のときも尋ねずに「候補が無い。機関未確定のまま」と伝える
7. **止まったら**（`ok` が偽）：何も書かれていない。`errors` の理由をそのまま職員に示す（理由を読み替えない・言い換えて隠さない）。理由のとおりに案を作り直し、どこを直したかを示してから、手順 4 の復唱を経て出し直す
   - 「原文に無い」「引用に無い数字」と言われたら、その項目を消すか原文どおりに直す。原文に無いことを足して通さない
   - `stage` が `input`（仮名の本人がいない・本人が違う）なら作り直さず、仮名を職員に確かめる
   - `stage` が `gate` で、案では直せない理由（職員が Active でない など）なら、作り直さず管理者に伝えるよう職員に言う
   - 同じ理由で二度止まったら、三度目は出さずに職員に相談する
8. `nest-gate` が使えないとき（道具が無い・設定が無いと言われる）は、案（JSON）を職員に渡して止まる。管理者の予備の道具（`scripts/submit_proposal.py`）で通してもらう

## 例（架空）

<!-- example-original -->
```text
架空の面接記録（例）
2026-11-02 訪問
自宅を訪問。母と本人に会う。
- 10月2日、母が電話で話した。後ろから急に声をかけるとパニックになる【伝聞】
- 本人は、音楽を聴くと落ち着くと話した【本人の話】
- 受給者証の更新のことで、区役所の窓口に行ったことがある【伝聞】
- 予定が急に変わると落ち着かないのだろうと、私は受け取った【推測】
- 次回は通院に同行することを母と確認。
```

<!-- example-proposal -->
```json
{"documentKind": "OwnCaseRecord",
 "newPeople": [{"ref": "mother"}],
 "facts": [
  {"quote": "自宅を訪問。母と本人に会う。",
   "recordKind": "Observation", "certainty": "Unspecified", "informantKind": "Agency"},
  {"quote": "10月2日、母が電話で話した。後ろから急に声をかけるとパニックになる",
   "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family", "toldBy": "mother"},
  {"quote": "本人は、音楽を聴くと落ち着くと話した",
   "recordKind": "Interview", "certainty": "SelfReport", "informantKind": "Self", "toldBy": "client"},
  {"quote": "受給者証の更新のことで、区役所の窓口に行ったことがある",
   "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family", "toldBy": "mother"},
  {"quote": "予定が急に変わると落ち着かないのだろうと、私は受け取った",
   "recordKind": "Interview", "certainty": "Inference", "informantKind": "Agency"}],
 "involvements": [
  {"quote": "受給者証の更新のことで、区役所の窓口に行ったことがある", "kind": "Administrative"}],
 "ngActions": [
  {"quote": "10月2日、母が電話で話した。後ろから急に声をかけるとパニックになる",
   "action": "後ろから急に声をかける", "riskLevel": "Panic"}],
 "supportLog": {"quote": "自宅を訪問。母と本人に会う。", "date": "2026-11-02", "contactKind": "Visit",
                "situation": "自宅。母と本人", "action": "母と本人に会い、話を聞いた",
                "nextAction": "次回は通院に同行する（母と確認）"}}
```

- 本人は仮名で指すので、案に `clientId` を書かない。出す前に「対象は C-…… の本人です。この本人に未確定で入れてよいですか」と復唱する
- 面接 1 回を `supportLog` 一つにし、根拠は接触の一文（「自宅を訪問。母と本人に会う。」）の事実に結ぶ。次の調整は `nextAction` に置き、事実にしない。`effectiveness` は書かない
- 見立て（「予定が急に変わると落ち着かないのだろうと、私は受け取った」）は `Inference`。職員が自分で見たことから受け取ったので `informantKind` は `Agency`、`toldBy` は書かない。これだけを根拠に禁忌の候補は作らない
- 禁忌の候補は、母の話の事実を根拠に指す。確度は根拠の事実の `Hearsay` を引き継ぐので、候補には書かない
- 「音楽を聴くと落ち着く」は推奨ケアの候補にもできるが、どう支えるか（`instruction`）が原文に無いので、事実として残すだけにした
- 「10月2日」には年が無いので、`aboutDate` を書かない
- 母は名札 `mother` で指し、名前を書かない
- 窓口の機関は推定の候補が渡されていないので `orgId` を書かない（機関未確定）
