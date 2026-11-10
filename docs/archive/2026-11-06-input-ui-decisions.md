> **保管の記録（2026-11-08）**：この文書は 2026-11-06 のたたき台。翌 11-07 の対話で「ITが苦手な職員向けの画面」をやめ、特定の専門職が Claude Desktop だけを入口にする方針に変えた。その決定は `docs/adr/ADR-002-claude-as-entrance.md`（2026-11-08 承認）。
> - 判断 1・判断 4（「案を入れる」「承認待ち」の二画面、段階 K の行）：**不採用**。画面は作らず、承認は MCP の機能として Claude Desktop の会話で行う（ADR-002）。
> - 判断 2（Claude の契約の形）：ADR-002 の未決論点へ引き継ぎ。
> - 判断 3（録音の文字起こしを Mac 内で行うか）：未決のまま。段階 L で再検討。
> - 「導入と運用を分ける」の原則：ADR-002 の「管理者の手順書・引継ぎの章」に引き継ぎ。
> 原文は変えていない。

# nest-support 入力 UI：4 つの判断と、Mac への指示（2026-11-06 たたき台）

- 決めるのは河原さん。下の「推す案」は Claude の案で、理由と却下した案を添えた
- 読んだもの：nest-support main（GitHub の写し。ADR-001、`docs/external-api.md` v0.11、`docs/EXTERNAL_API_SETUP.md`、`nest/egress.py`・`nest/gate/*`・`nest/mcp_guard.py`・`nest/mcp_personal.py`、`field-ui/server.py`、`scripts/review_proposals.py`、`claude-skills/narrative-extractor/SKILL.md`、HANDOVER、台帳 G-80〜G-91）。tsunagu-net は読んでいない・変えていない。前の DB は開いていない
- Web で確かめたもの（一次資料）：Anthropic Commercial Terms（発効 2025-06-17）、Data Processing Addendum（発効 2025-02-24）、「API and data retention」（platform.claude.com）。**確かめられなかったもの**：個人情報保護委員会の Q&A（`ppc.go.jp` はこのセッションの網の外）、Anthropic の商用の保存期間の記事（`privacy.claude.com`、同じく網の外）、`~/Obsidian/my-research/`（この雲のセッションからは Mac のファイルに届かない）。これらは【未照合】と書く

---

## 判断 1　段階 K を先に作るか、段階 L に直接進むか

**推す案：K を先に作る。ただし K の中身を「L から Claude API の呼び出しだけを抜いたもの」に組み替える。MCP の `submit_proposal` は作らない。**

K の中身（組み替え後）：

1. field-ui「案を入れる」画面：原文と、Claude（Desktop の narrative-extractor）が返した案の JSON を貼る → サーバーが `nest.gate.intake.check` で点検 → 止まれば理由をそのまま出す → 通れば本人（`clientId`）・提供元の機関（候補から職員が選ぶ）を付けて `nest.gate.write.submit` → **未確定（Pending）で入る**。画面は「未確定で入りました。承認はまだです」と出す（「登録完了」とは書かない。G-34）
2. field-ui「承認待ち」画面：`scripts/review_proposals.py` の画面版。一覧（古い順・仮名だけ）→ 一件ごとに根拠の引用を並べ → 承認／差し戻しを一件ずつ（`nest.gate.approve.approve`／`reject`。`approve_many` は使わない）。職員 ID はトークンから決める。自己承認は `selfApproval` を画面にも出す

理由：

- **L は判断 2（契約）が決まるまで作れない。** K の二つの画面は契約と無関係で、今の架空の事例の運用（N-46 の試走）でそのまま使える
- **K の二画面は、そのまま L の後半になる。** L は「貼る」の代わりにサーバーが Claude API を呼んで案を作るだけで、点検 → 未確定 → 承認の流れは同じ。K を作れば L は「API を呼ぶ部品 1 本」を足す作業になる
- **MCP の `submit_proposal` はやめる。** ADR-001 D6 は「MCP は読み取りだけにする」。未確定で入るだけでも、Claude の道具から DB に書く道ができる（読み取りだけの包みという約束が崩れ、`tests/test_no_structurize.py` 系の「Claude は書かない」の試験の意味も薄れる）。しかも NEXT-01 が止まっている間、Claude Desktop に実データは渡せないので、この道具は架空の事例でしか使えない。field-ui に「貼る」画面があれば用は足りる
- 「AI が承認することは仕組み上できない」は、承認の入口を field-ui の職員トークンだけにし、MCP にも API にも承認の道具を置かないことで保つ（今と同じ）

却下した案：

- **L に直接進む**：契約が未決のまま API の部品を書くと、送る中身（NEXT-01 の書き換え）が決まらないまま試験を書くことになる。K を飛ばすと、試走の間も福祉専門職がターミナルで承認し続ける
- **K を MCP の `submit_proposal` ＋ 承認画面にする（前の案）**：上のとおり D6 に触れる

ADR の未決論点 10（field-ui の方針）は、ここで「作り直す。入力の入口は field-ui に一本化する」と決まる。

---

## 判断 2　Claude API の契約の形と、NEXT-01 の書き換え

### 2-1 一次資料で確かめたこと（2026-11-06）

| 項目 | 内容 | 出どころ |
|---|---|---|
| 契約 | Anthropic Commercial Terms of Service（発効 2025-06-17）。「Services under these Terms are not for consumer use」。Claude.ai の個人向けは別の Consumer Terms | anthropic.com/legal/commercial-terms |
| 学習に使うか | 「Anthropic may not train models on Customer Content from Services」。Customer Content は入力と出力の両方 | 同上 §B |
| DPA | Commercial Terms に参照で取り込まれる（「incorporated into these Terms by reference」）。別に署名が要るとは書いていない（Console の組織で API を使えば当然に掛かると読める。**要確認**） | 同上 §C、DPA 冒頭 |
| 保存の期間（既定） | API では「Conversation content (your prompts and Claude's outputs) is not retained by default」。例外は Covered Models（Fable 5／5.1、Mythos 5／5.1）で 30 日の保存が必須、ZDR 不可 | platform.claude.com「API and data retention」 |
| 保存の期間（例外） | 自動の安全の仕組みが flag したものは、ZDR でも最長 2 年保存。法の求めも同じ | 同上「Retention regardless of arrangement」 |
| ZDR（保存ゼロ） | 営業を通した組織ごとの取り決め。Messages API は対象。Batch API（29 日保存）・Files API（消すまで保存）・code execution（30 日）は対象外 | 同上の eligibility 表 |
| 契約終了時 | 終了から 30 日以内に Customer Data を消す（法の求め・紛争・不正対策の例外あり） | DPA §H.1 |
| 処理の場所 | DPA は国を書かない。EU 向けは SCC（Module 2／3）。サーバーは米国と見てよい（**国名は一次資料で未確認。Subprocessor 一覧 anthropic.com/subprocessors で確かめる**） | DPA §I、Schedule 3 |
| 再委託先 | Schedule 4（anthropic.com/subprocessors）。新しい再委託先は事前の通知、15 日以内に異議がなければ同意とみなす | DPA §C |
| 安全管理 | AES-256（保存）・TLS 1.2+（通信）、MFA、年次の外部ペネトレーションテスト、SOC 2 報告書は求めれば出る | DPA Schedule 2・§F |

### 2-2 法律の整理（河原さんの判断の材料。Claude は Q&A を照合していない）

- 個人向け（Ultra）は Consumer Terms なので、G-80 のとおり記録を満たせない。**実データを Claude に渡す経路は API（事業者向け）に一本化する**のが筋。Team／Enterprise は Claude Desktop の MCP（NEXT-02）を実データで使うときの話で、NEXT-01（語りの構造化）には要らない
- 委託（第 27 条第 5 項第 1 号）と見る土台：Commercial Terms で学習に使わない、DPA で処理の目的・期間・再委託の通知・終了時の消去が決まっている
- 外国にある第三者（第 28 条）：Anthropic は米国の事業者。本人同意を取らないなら「基準適合体制」（規則 第 16 条：契約などの適切かつ合理的な方法で、OECD 8 原則に相当する措置を確保）に当たるかを、DPA の中身で河原さんが判断する。**ここが記録の `legalArrangement` の核**
- クラウド例外（委員会 Q&A 7-53「取り扱わないこととなっている場合」）は、**当たらないと見るのが安全**。推論そのものが取り扱いで、flag されたものは最長 2 年保存される。【未照合：Q&A の原文はこのセッションから読めなかった】
- Q12-1（河原さんが示したもの）も同じく【未照合】

### 2-3 推す形

- **モデルは `claude-opus-5-5` に固定する。** Covered Models（Fable／Mythos）は 30 日保存が必須で ZDR も不可なので使わない。モデル名に `fable`・`mythos` が入ったら試験で止める（保存の条件が変わるため）
- **Messages API だけを使う。** Batch API・Files API・code execution・Managed Agents は使わない（保存される）。原文は本文に入れて送る（添付にしない）
- **ZDR は申し込む価値がある**（Messages API は対象）。ただし申し込めるかは組織の規模と営業次第。申し込めなくても「既定で保持しない」と「flag は最長 2 年」を記録に書けば、記録の項目は埋まる
- 鍵は `~/.config/nest/anthropic-api.env`（600）に置く。`.env` には書かない。鍵の有無は送ってよい印にしない（Gemini と同じ）
- **記録（NEXT-01）の書き方（案）**：`contractName`「Anthropic Commercial Terms of Service ＋ Data Processing Addendum（API、Console の組織）」／`contractVersion`「Terms 2025-06-17、DPA 2025-02-24」／`trainingUse`「使わない（Terms §B）」／`retention`「既定で保持しない。安全の仕組みが flag したものは最長 2 年。ZDR の取り決めがあればその旨」／`legalArrangement`「委託（27 条 5 項 1 号）。外国にある第三者（28 条）としては基準適合体制（DPA）による／本人同意による、のどちらかを河原さんが書く」／`sendsSensitiveData: true`／`nextReviewOn` は Terms の改定に備えて 1 年以内

### 2-4 NEXT-01 の書き換え（external-api.md v0.12 の案）

| 欄 | 今（v0.11） | 書き換え |
|---|---|---|
| 外部 API（ホスト） | Claude（Claude Desktop・Claude Code を通る）。個人向けプランでは満たせない見込み | **Claude API（`api.anthropic.com`。事業者向け Commercial Terms＋DPA）。nest-support のサーバー（field-ui）が呼ぶ。** Claude Desktop・Claude Code（個人向け）からは実データを渡さない（開発と架空の事例だけ） |
| 使う場面 | 語り・面談記録・添付から案を作る | 同じ。field-ui「語りを入れる」画面から |
| 送るもの | 原文、機関の候補の一覧 | 原文、機関の候補（`orgId` と名前。公開情報）、**守ること（SKILL.md の規則）の指示文**。**本人の ID・仮名・職員 ID は送らない**（案に `clientId` が要るが、サーバーが Claude の返事を受けてから付ける） |
| 送らないもの | DB の中身、ほかの本人の記録 | 同じ ＋ 添付ファイル（Files API を使わない）、音声 |
| 既定 | 実データは使わない | **止める**（設定と記録がそろうまで。NEXT-03 と同じ形）。モデルは `claude-opus-5-5` に固定。Covered Models は使わない |

`nest/egress.py` は `"NEXT-01": Destination("api.anthropic.com", "gated")` に変え、`check_url` で送り先を固定する。NEXT-02（MCP の照会の結果）は `host=None` のまま（送るのは Claude のアプリ）。

### 2-5 費用の目安

Opus 5.5 は入力 $4／100 万トークン、出力 $20／100 万トークン。語り 2,000 字と指示文で 4,000 トークン前後、案の JSON が 2,000 トークン前後として、**1 回あたり数円**。月に 100 件でも数百円。

---

## 判断 3　録音の文字起こしを外に出すか、Mac 内で行うか

**推す案：Mac 内で行う。外に出す道（NEXT-03 Gemini）は、Mac 内の文字起こしが架空の音声で使えると分かった時点で「やめる」に移す。**

- 候補は二つ。どちらも Mac の中で完結し、外には送らない
  - **mlx-whisper／whisper.cpp（large-v3-turbo）**：Apple Silicon で動く。英語では mlx-whisper が whisper.cpp より約 2 倍速いという個人の測定がある。**日本語の精度を比べた資料は見つからなかった**
  - **Apple SpeechAnalyzer（macOS 26 の Speech フレームワーク、オンデバイス、`ja_JP` 対応）**：英語では Whisper より速く精度も良いという測定があるが、**日本語の測定は無い**。macOS 26 が要る。Swift の小さな CLI を書く
- 推す順：**まず mlx-whisper で試す**（Python から呼べ、nest の試験に乗せやすい。モデルは Hugging Face から一度だけ取ってくる）。日本語が物足りなければ SpeechAnalyzer を試す
- 決め方：架空の音声（職員が架空の面談を読み上げたもの）で両方を流し、誤変換の数と句読点を河原さんが見る（止まる点）
- 理由：声は本人・家族を最も特定しやすい。文字起こしを Mac 内に置けば、録音を外に送る理由が無くなり、NEXT-03・NEXT-04（Gemini）の契約の確認そのものが要らなくなる。文字起こしの誤りは、職員が案を作る前に原文を直せるので、精度が多少落ちても流れは壊れない
- 外部送信の一覧への影響：モデルを取ってくる `huggingface.co` は §3「取ってくるだけ」に **NEXT-13** として足す（送るのはモデルの名前だけ。取ったファイルは指紋で固定）。Apple の方式ならモデルは OS が持つので行は要らない
- 却下：**Gemini のまま**（録音という最も強い識別子を外に出す。契約の確認が Claude と別にもう一つ要る）。**Claude API に音声を送る**（Messages API は音声の入力に対応していない。要らない）

---

## 判断 4　画面の形

### 4-1 流れ（二段に分ける。D9「承認は書き込みとは別の操作」を画面でも保つ）

```
[案を入れる]  原文を貼る → 案の JSON を貼る（L では「案を作る」ボタンに変わる）
              → 本人を選ぶ（仮名の一覧。名前は出ない）
              → 「点検する」 … intake.check の結果をそのまま出す（止まった理由は読み替えない）
              → 提供元の機関を候補から選ぶ／関わりの機関を推定の候補から選ぶ（未確定のままも可）
              → 「未確定として入れる」 … gate.write.submit。「未確定で入りました。承認は『承認待ち』で」
[承認待ち]    一覧（古い順・仮名・由来・種類）→ 一件を開く → 根拠の引用 → 承認 ／ 差し戻し（理由）
```

### 4-2 案と引用の並べ方

- 左に原文（貼ったまま）。右に案の項目をカードで並べる：事実（facts）→ 関わり（involvements）→ 禁忌の候補（ngActions）→ 推奨ケアの候補（carePreferences）
- 各カード：**引用（原文からそのまま）** を一番上に太く、その下に言い換え（text）、確度（原文の印【…】も横に出す）、情報源、話し手（名札か ID）。原文の側で引用の箇所を黄色に塗る（クリックで対応するカードへ）
- 点検で止まった項目はカードを赤くし、intake の理由をそのまま添える。通った項目だけが「未確定として入れる」の対象。**一部だけ入れる操作は作らない**（案は一つの依頼として通す。直すなら Claude に差し戻して案を作り直す）
- 「承認待ち」の一件の画面は `review_proposals.py show` と同じ中身（根拠の記録 ID・確度・話し手・引用）。関わりには `involvement_content` の中身（種類・確度・終わり方・推定の根拠・機関）も出す
- 承認・差し戻しは一件ずつ。「すべて承認」のボタンは置かない。自分で登録したものは「自己承認になります」と一行出してから承認

### 4-3 機関未確定の候補の選び方

- 提供元（`providerName`）：`org_candidates.by_name` の候補を並べ、職員が一つ選ぶか「未確定のまま」を選ぶ。**候補が一つでも自動で選ばない**。選ぶまで「未確定として入れる」は押せない（intake は `provider_org_id` が無いと依頼を作らない）
- 関わり（`involvements`）：`org_estimate.estimate` の候補だけから選ぶ。既定は機関未確定（候補から選んだときだけ `orgId` が入る）。推定の注記（notes）を候補の横に出す
- 候補の名前は資源の側から `orgId` で引く（個人の側には置かない）

### 4-4 差し戻しの理由

- **G-91 を採る**ことを推す：AuditLog（Reject）に `reason` を一行持つ。画面では差し戻しに理由を必須にする（空では押せない）。名前を書かないよう注意書きを置く（機械では止めない）
- 理由：画面で差し戻すと「なぜ戻ったか」が Claude に案を作り直させる手がかりになる。ターミナルの頃は職員の頭の中にあった
- tsunagu-net の AuditLog には理由が無いが、nest-support の正典 §10（そろえた名前）に「`AuditLog.reason` は nest-support だけ」と一行書けば済む。tsunagu-net は変えない

### 4-5 画面の決まり（今の field-ui と同じ）

- 127.0.0.1 だけ。職員トークン。読むのは包み（`caller="screen"`）。書くのはゲート。実名・かな・電話・住所・生年月日は返さない
- 実データの DB で「案を入れる」を使うのは、L で NEXT-01 の歯止めが通ってから。K の間は、原文を Claude Desktop に貼る段で実データを渡さない決まり（G-80）がそのまま掛かる

---

## Mac への指示（計画に足す段階 K の行。河原さんが渡す）

前提：枝は main から新しく切る（例 `stage-k`）。段階 J（N-46）の試走と並行してよい。試験を先に書き、緑になったらコミット。push・PR・main への合流は河原さん。前の DB は起動しない。tsunagu-net は変えない。開発と試験は架空の事例だけ。

| # | タスク | 先に書く試験 | 止まる点 |
|---|---|---|---|
| N-47 | ADR-001 の未決論点 10 を「field-ui を作り直す。入力の入口は field-ui に一本化する。MCP に書く道具は作らない」と書き、台帳に判断 1 の理由を残す | — | — |
| N-48 | field-ui「承認待ち」：`GET /api/proposals`（Pending の一覧。`review_proposals.py` の PENDING と同じ照会。仮名だけ）、`GET /api/proposals/{id}`（根拠の引用。`approve._quotes`、関わりは `involvement_content`）、`POST /api/proposals/{id}/approve`・`/reject`（`approve.approve`／`reject` を一件ずつ。職員 ID はトークンから）。画面 `review.html` | 一覧が古い順で実名を含まない／一件に引用が出る／承認で Active・AuditLog Approve・自己承認で selfApproval／`approve_many` を呼ばない（grep で固定）／承認の道具が MCP に無い（`nest/mcp_personal.py` の tool が 3 本のまま） | — |
| N-49 | field-ui「案を入れる」：`POST /api/proposals/check`（原文＋案 JSON ＋ clientId → `intake.check`。止まった理由をそのまま返す）、`GET /api/orgs/candidates?name=`（`org_candidates.by_name`、資源の側）、`GET /api/orgs/estimate?clientId=&aboutDate=`（`org_estimate.estimate`）、`POST /api/proposals/submit`（点検を通った依頼を `write.submit`。結果は「未確定」と明記）。画面 `proposal.html`（原文の引用の塗り分け、カード、候補の選択） | `tests/fixtures/narratives/fictional-001-mother.txt` と SKILL.md の例の案が点検を通り Pending で入る／引用に無い数字を足した案が止まり、理由が intake の文言のまま／`provider_org_id` 無しでは submit できない／候補が一つでも自動で入らない／返事に「登録完了」の文字列が無い／`clientId` 以外の本人の情報を受け取らない | **止まる点 K-1**：河原さんが架空の事例で二画面を通し、並べ方と文言を見る |
| N-50 | 差し戻しの理由（G-91 を採るとき）：正典に `AuditLog.reason`（Reject のときだけ）を足し、§10 に「nest-support だけ」と書く。`approve.reject` に `reason` を足し、画面で必須にする | 理由なしの差し戻しがゲートで止まる／AuditLog に一行入る／`check_drift.py` のずれ 0 | — |
| N-51 | `docs/OPERATIONS.md` の 5 の段に二画面を足し、`review_proposals.py` は「画面が使えないとき」の予備にする | `tests/test_docs_operations.py` の形で、書いた URL と道具が実在する | — |
| N-52 | 文字起こしの試し（判断 3）：`nest/transcribe_local.py` に mlx-whisper を呼ぶ部品（外の命令を呼ぶ時に引く。G-77 (i)）。モデルの取得先 `huggingface.co` を external-api.md §3 に NEXT-13 として足し、`egress` の一覧に `open` で入れる。架空の音声で流す | 送信の歯止めの一覧と文書がずれない（既存の試験）／偽の送信先で外部への呼び出しが huggingface.co 以外に 0 回／文字起こしの結果が `voice.store` の指紋の形に乗る | **止まる点 K-2**：河原さんが架空の音声の文字起こしを見て、Mac 内で行くか決める。行くなら NEXT-03・04 を「やめる」に移す行（N-53）を切る |
| N-54 | NEXT-01 の書き換え（判断 2 を河原さんが決めた後）：external-api.md v0.12、`egress.DESTINATIONS["NEXT-01"]` を `api.anthropic.com` の gated に、モデル名の固定と Covered Models の禁止 | モデル名に `fable`・`mythos` が入ると止まる／設定と記録が無ければ api.anthropic.com への呼び出しが 0 回／送る本文に `CLI-`・`C-`・`STF-` の ID が入らない | **止まる点 K-3**：段階 L（サーバーが Claude API で案を作る）に進むかを決める |

段階 L の行（N-55〜）は K-3 の後に書く。L で足すのは「案を作る」部品 1 本（Messages API、`claude-opus-5-5`、構造化出力で案の JSON、SKILL.md の「守ること」をサーバーの指示文に一本化し、SKILL.md と同じ文であることを試験で固定）だけで、点検 → 未確定 → 承認は K のまま。

---

## 河原さんに決めてもらうこと（まとめ）

1. 判断 1：K を先に、MCP の `submit_proposal` は作らない — 可否
2. 判断 2：API（事業者向け）に一本化、`claude-opus-5-5` 固定、Covered Models 禁止、記録の `legalArrangement` の書き方（基準適合体制か本人同意か）— 河原さんの判断。Q&A 7-53・12-1 は未照合
3. 判断 3：Mac 内の文字起こしを試す（mlx-whisper → だめなら SpeechAnalyzer）、通れば Gemini の行を「やめる」に — 可否
4. 判断 4：二段の流れ、候補は手で選ぶ、G-91（差し戻しの理由）を採る — 可否
5. 段階 K の行（N-47〜N-54、止まる点 K-1〜K-3）を計画に足してよいか

---

# 追記（2026-11-06 の後半。河原さんとの対話で変わったこと）

## 共有した前提

- tsunagu-net は資源 DB（本体）と多問題家族のケース DB（世帯が中心、雛形。ADR-008）を持つ。nest-support は親なき後の支援の DB（本人が中心）。資源 DB は写しを読むだけ。この整理で合意した
- GitHub の tsunagu-net `main` には README と法令の照合しか無く、本体は枝 `claude/tender-dijkstra-xo3wwc`（2026-11-05）と Mac の `~/Dev-Work/tsunagu-net`（HEAD 3bf49ca）にある

## 判断 1 の取り下げと書き換え

- 「MCP の `submit_proposal` は作らない」を**取り下げる**。Claude に添付するだけで済む道には、この道具が要る
- 入力の道は三つ要る。どれも後半（点検 → 未確定 → 画面で一件ずつ承認）は共通

| 道 | 誰向け | 要るもの | 障害 |
|---|---|---|---|
| A　Claude に添付するだけ | Claude を使う職員 | MCP に「未確定の案を出す」道具 1 本（intake.check → write.submit、Pending）。承認は画面 | D6 の改め。実データは Team／Enterprise の契約（G-80） |
| B　画面に貼る／画面で作る | Claude を直接触らない職員 | field-ui「案を入れる」。段階 L でサーバーが API を呼ぶ | 判断 2（API の契約） |
| C　AI を使わない | AI を使わない配布先 | 画面で事実を一つずつ入れる（引用・確度・情報源を人が付ける。origin: Human） | 画面が無い |

- 作る順：**承認の画面 → C の入力の画面 → A の道具 1 本 → B の API**
- D6 の改めの案：「Claude は確定を書かない。書けるのは、点検を通った案を未確定として出すことまで。承認の道具は MCP にも API にも置かない」。AI が承認できない芯は残る。決めるのは河原さん（止まる点）
- tsunagu-net のケース DB にも同じ三つの道が要る。配布先（行政・社協）では C の比重が大きい

## 新しい原則：導入と運用を分ける（nest-support・tsunagu-net の両方）

今の敷居（nest-support）：ブラウザだけで済むのは支援記録の入力と録音の 2 つ。導入 12 手順、毎日の起動に端末 3 つ、本人の登録・案の承認・週一の整理・廃棄・Claude Desktop の設定はターミナル。tsunagu-net の配布先の手順は「世帯を見る」までターミナルで、さらに重い。

1. **導入は一度きりで、やる人が違う。** 配布物（導入スクリプト）と「管理者の手順書」。Docker・暗号化（FileVault）・契約の確認の記録だけは人の手と明記
2. **運用はブラウザと一つの起動ボタンだけ。** 起動と停止（バックアップを含む）を一つに。見る・入れる・承認する・本人（世帯）を登録するを画面に。ターミナルの道具は予備に格下げ
3. **手順書を二冊に分ける。** 管理者の手順と職員の手順。職員の手順にコマンドが一行でも出たら設計の未完

置き場所の推し：それぞれの ADR（nest-support は ADR-002、tsunagu-net は ADR-009）。四つの約束には足さない（約束は DB の形をそろえる文書）。tsunagu-net は書くだけの提案（台帳 G-40 と同じ形）

## 明日やること（河原さんの可否を待っているもの）

1. 判断 1 を三つの道に書き換え、段階 K の行を「承認の画面 → C → A → B」に並べ直す。D6 の改めを止まる点に入れる
2. 「導入と運用を分ける」の ADR-002（nest-support）の草案と、tsunagu-net 向けの提案文を書く。段階 M（起動を一つに、導入スクリプト、手順書二冊）の行を足す
3. 判断 2〜4 は前半の文書のまま。河原さんの可否待ち
