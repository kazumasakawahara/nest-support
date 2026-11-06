---
name: narrative-extractor
description: 母親・支援者の語り（ナラティブ）、自分の面談記録、他の機関からの情報提供の書面から、nest-support の「書き込みの案」（JSON）を作るスキル。案を作るだけで、DB には書かない（書くのはゲート）。「テキストから抽出」「情報を抽出して」「ナラティブから登録」「この文章を構造化して」「データベースに登録して」「面談記録を入力」「聞き取り内容を登録」などの発言時、および .docx/.xlsx/.pdf/.txt ファイル添付時に使う。
---

# narrative-extractor：語りから書き込みの案（JSON）を作る

## 概要

語り・面談記録・情報提供の書面から、**書き込みの案（JSON）を作るだけ**のスキル（計画 N-25。ADR-001 D6）。

- **DB には書かない。** 書くのはゲート（`nest/gate/intake.py` → `validate.py` → `write.py`）だけ。このスキルから Cypher を流さない
- 案は、入口の点検（`nest.gate.intake.check`）が原文と突き合わせる。原文に無い引用、引用に無い数字、原文の印と違う確度、型に無い項目は、直さずに止まる
- 通った案は、ゲートが AI 由来として **未確定（Pending）** で書き、職員が引用を見て承認する（D9）
- 外部の API は使わない。案を作るのは Claude 自身

## 守ること

1. **原文に無いことを書かない。** 推し量らない。分からない項目は書かない（null で埋めない）
2. **引用（`quote`）は原文からそのまま写す。** 空白・改行の違いだけは点検が無視する。言い換えは `text` に書いてよいが、引用に無い数字（日付・回数・金額・年齢・体重など）を足さない
3. **確度は原文の印で決める。** 引用の直後（同じ行）の【…】を読む：【確認済み】→ `Confirmed`、【本人の話】→ `SelfReport`、【伝聞】【未確認】→ `Hearsay`、【推測】→ `Inference`。印が無ければ `Unspecified`。重なったら弱いほう。上げも下げもしない
4. **人を名前で結び付けない。** 既にいる人は ID（`PER-…`）、案の中の新しい人は名札（英小文字で始まる `ref`）、本人は `client` で指す。名前の似た人を同じ人と決めない（D8）
5. **語りの中の人は役割の名前で書く**（母・主治医・担当の相談員）。新しい人の名札にも実名を入れない（SEMANTICS SEM-REC-01。台帳 G-42）
6. **年のない日付に年を足さない。** 「10月2日」は引用のまま残し、`aboutDate` には年まで原文にあるときだけ書く
7. **機関 ID を書かない。** 書面の提供元は原文の名前（`providerName`）だけを書く。職員が候補から選ぶ（N-24）。「区役所の窓口で」のような名前の無い言及は `involvements` に書き、機関は担当機関の推定の候補からだけ選ぶ（N-24a）
8. 開発と試験では架空の文だけを使う

## 案の形

```text
{"documentKind": "OwnCaseRecord"（自分の記録） | "ProvisionDocument"（他の機関からの書面）,
 "providerName": 書面のときだけ。原文に書かれた提供元の名前,
 "clientId": "CLI-…"（職員が選んだ本人）,
 "receivedOn": "YYYY-MM-DD"（書面を受けた日。任意）,
 "newPeople": [{"ref"}]（任意。役割の名前で呼ぶ人。実名は書かない）,
 "facts": [{"quote", "text"?, "recordKind", "certainty", "providerCertainty"?（書面のとき）,
            "informantKind", "aboutDate"?, "heardOn"?, "toldBy"?}],
 "involvements": [{"quote", "kind", "orgId"?, "concerns"?}]（任意）,
 "ngActions": [{"quote", "action", "riskLevel", "reason"?}]（任意。禁忌の候補）,
 "carePreferences": [{"quote", "category", "instruction", "priority"?}]（任意。推奨ケアの候補）}
```

- `recordKind`：`Observation`（職員が見た）・`Interview`（聞いた）・`Notification`・`MeetingMinutes`・`Plan`・`Document`
- `informantKind`：`Self`（本人）・`Family`・`Agency`・`Neighbor`・`DocumentOnly`
- 書面では確度を二段で持つ：`providerCertainty` は原文の印、`certainty` は受けた側から見た確度（点検が決まった値を求める）
- `riskLevel`：`LifeThreatening`（生命に関わる）・`Panic`（パニック誘発）・`Discomfort`（不快）。`priority`：`High`・`Medium`・`Low`

## 禁忌・推奨ケアは二段で扱う（台帳 G-63。正典 v0.9 §6）

1. **根拠が同じ案の中にあるとき**：その話をまず事実（`facts`）として引用で残し、`ngActions`・`carePreferences` の候補の `quote` に、その事実の引用をそのまま書く。ゲートが根拠（`EVIDENCED_BY`）で結び、`Pending` で入れる。承認は一つずつ
   - 候補に確度を書かない（根拠の事実の確度を引き継ぐ）
   - `action`・`instruction` などに、引用に無い数字を足さない
2. **根拠が同じ案の中に無いとき**（前に聞いた話・職員の記憶など）：候補にしない。分かっている範囲を事実として残し、「禁忌の候補」として引用を並べて職員に知らせる（禁忌には根拠の記録が要る。SEMANTICS SEM-REC-03）

## 手順

1. 原文を受け取る（貼り付け・添付）。本人の `clientId` は職員に選んでもらう（名前から探さない）
2. 上の「守ること」に沿って案（JSON）を作る
3. 案と、候補にできなかった「禁忌の候補」（引用の一覧。二段の 2）を職員に返す。ここで止まる
4. 職員が入口の点検とゲートに通す。止まったら、点検の理由のとおりに案を直す（点検の結果を自分で読み替えて通さない）

## 例（架空）

<!-- example-original -->
```text
架空の面談記録（例）
- 10月2日、母が電話で話した。後ろから急に声をかけるとパニックになる【伝聞】
- 本人は、音楽を聴くと落ち着くと話した【本人の話】
- 受給者証の更新のことで、区役所の窓口に行ったことがある【伝聞】
```

<!-- example-proposal -->
```json
{"documentKind": "OwnCaseRecord",
 "clientId": "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ",
 "newPeople": [{"ref": "mother"}],
 "facts": [
  {"quote": "10月2日、母が電話で話した。後ろから急に声をかけるとパニックになる",
   "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family", "toldBy": "mother"},
  {"quote": "本人は、音楽を聴くと落ち着くと話した",
   "recordKind": "Interview", "certainty": "SelfReport", "informantKind": "Self", "toldBy": "client"},
  {"quote": "受給者証の更新のことで、区役所の窓口に行ったことがある",
   "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family", "toldBy": "mother"}],
 "involvements": [
  {"quote": "受給者証の更新のことで、区役所の窓口に行ったことがある", "kind": "Administrative"}],
 "ngActions": [
  {"quote": "10月2日、母が電話で話した。後ろから急に声をかけるとパニックになる",
   "action": "後ろから急に声をかける", "riskLevel": "Panic"}]}
```

- 禁忌の候補は、母の話の事実を根拠に指す。確度は根拠の事実の `Hearsay` を引き継ぐので、候補には書かない
- 「音楽を聴くと落ち着く」は推奨ケアの候補にもできるが、どう支えるか（`instruction`）が原文に無いので、事実として残すだけにした

- 「10月2日」には年が無いので、`aboutDate` を書かない
- 母は名札 `mother` で指し、名前を書かない
- 窓口の機関は推定の候補が渡されていないので `orgId` を書かない（機関未確定）
