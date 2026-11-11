# 運用の手順書

> 2026-11-06 計画 N-40。相談支援の職員が、上から順に読んで動かすための一本の手順です。
> Mac の準備（Docker・uv・接続の設定のファイル・FileVault）は `docs/SETUP_GUIDE.md` の「0. 新しい Mac でゼロから」で済ませてあるものとします。
> 各段の終わりに「点検」を書きました。`./scripts/doctor.sh` の項目の番号（[1]〜[10]）か、doctor では見られないので「人が確かめる」のどちらかです。一覧は末尾の「段と点検の対応」にあります。

**先に読むこと（今の制約）**

- **実データは Claude に渡しません。** 契約の確認の記録をまだ作らないと決めました（台帳 G-80）。語り・記録を Claude に読ませる段（`narrative-extractor`）と、Claude が DB を照会する段は、架空の事例でだけ使います
- **現場の画面（field-ui）と SOS は、実データの DB を読みます。** 画面は外に送らないので、Claude へ送る経路の歯止め（NEXT-02 の設定と記録、または架空の印）は当てません。当てるのは伏せ字だけで、実名・かな・電話・住所・生年月日は画面に返りません（止まる点 H-1、2026-11-06 河原さん。台帳 G-85）。Claude の照会（MCP `nest-personal`）は今までどおり NEXT-02 の歯止めを通るので、実データの DB では動きません。SOS の LINE への送信は NEXT-05 の歯止めのままです
- **実データの DB に架空の印（`NestLiveProbe`）を置かない。** 印を置くと、Claude の照会（MCP `nest-personal`）が実データを読めるようになり、実データを Claude に渡さない歯止め（台帳 G-80）が外れます。印は架空の事例の DB にだけ、人の手で置きます
- 道具の出力に出る名前と仮名の対応は、Claude の会話に貼りません。Claude には仮名（`C-……`）だけを伝えます

---

## 0. 最初の 5 つの操作

導入した日に、まず一通り試す 5 つです。くわしい打ち方は 1〜10 の段にあります。**今は実データを Claude に渡さない**ので（台帳 G-80）、Claude を使う操作（2〜5）は、架空の事例の DB でだけ試します。**Claude を使う操作（2〜5）の前に、4.5 の段で Claude Desktop をつなぎます**（設定を写す・語りから案を作る・案を未確定で入れる）。

1. **本人を登録する**：手元のターミナルで `scripts/new_client.py add` を打ち、仮名（`C-……`）を受け取ります（4 の段）。Claude には名前を伝えません。以後、Claude にも画面にも仮名で伝えます
2. **緊急の情報を確かめる**：現場では SOS の画面（5 の段）で、仮名から確かめます。Claude に「C-…… の緊急時の情報」と頼むと `emergency-protocol` が、禁忌（命に関わる → パニックを招く → 不快）、推奨ケア、支える人、医療、後見・任意代理の順に出します。連絡先・氏名・住所は Claude からは出ないので、手元の緊急連絡カードと SOS の画面で確かめます
3. **訪問の前の準備をする**：Claude に「C-…… の訪問準備」と頼みます（`visit-prep`）。前回の記録、禁忌、最近の変化、今回確かめることがまとまります
4. **支援記録を残す**：field-ui の「支援記録の入力」（`/record`）で書きます（5 の段）。記録はゲートを通って入ります。語りから書き込みの案を作る `narrative-extractor` は、架空の事例でだけ使います
5. **更新の期限を確かめる**：Claude に「C-…… の手帳・受給者証の期限」と頼みます（`data-quality-agent`）。更新の漏れは本人の不利益に直結するので、月に一度は確かめます

---

## 1. DB を起こす

DB は使うときだけ起こし、その日の作業の終わりに止めます。この枠を打ったら、**DB を起こしたまま 2〜9 の段に進みます**。止めるのは最後の「10. その日の終わりに DB を止める」です。

```bash
cd ~/Dev-Work/project/nest-support
docker ps                                   # 前の DB（nest-support-neo4j など）が動いていないこと
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d
./scripts/doctor.sh                         # 最後の行が「0 failed」であること
```

- `--remove-orphans` は付けません
- 接続の設定のファイル（`~/.config/nest/neo4j-redesign.env`）は開きません。人にも会話にも見せません
- `up -d` の直後は、DB が起ききるまで数十秒かかります。doctor の [2] が OK になってから次へ進みます。その前に道具を打つと `Transaction failed … retried` の行が出ることがありますが、道具が最後に結果の行を出していれば、そのままでかまいません

点検：[1] 前の DB が動いていない、[2] 新しい DB が 127.0.0.1 だけで待ち受けている、[3] 接続の設定のファイルが 600、[7] FileVault が有効

### 試走（架空の事例の DB）のときだけ：試験の残りを片づける

DB つきの試験を流した DB には、試験が作った架空の職員・本人・未確定のものが残っています。試走を始める前に、架空の印を置いてから片づけます。**実データを入れた DB では打ちません**（印を置くと Claude の照会がその DB を読めるようになり、片づけは印のほかをすべて消します）。

```bash
uv run python tests/live_mark.py       # 架空の印を置く（接続先が 37687 の個人の側でなければ止まる）
uv run python tests/live_cleanup.py    # 印のノードのほかをすべて消す（印が無い DB では止まる）
```

- 片づけると職員が一人もいなくなるので、2 の段で最初の管理者を作れます
- 印は残します（試走で Claude の照会を使うため）
- 職員のトークンの表（3 の段）は DB の外にあるので、片づけでは消えません。DB から消えた職員の行は、表からも消します（残さない）：

```bash
uv run python scripts/staff_token.py list               # 表に残っている職員 ID
uv run python scripts/staff_token.py remove STF-…       # DB から消えた職員を一人ずつ消す
```

## 2. 最初の管理者を作る（bootstrap_admin）

個人の側に職員が一人もいないときに、一度だけ使います。表示名は呼び名でかまいません。

```bash
uv run python scripts/bootstrap_admin.py --name "事務局"    # 職員 ID（STF-…）が出る
```

- 出た職員 ID を手元の紙に控えます。以後、管理者の操作でこの ID を使います
- 職員がすでにいる DB では、道具が止まり、今の Administrator の職員 ID を出します（二人目の管理者は作れません）。控えの紙が無いときは、ここに出た ID を使います。試走なら、1 の「試走のときだけ」で片づけてから打ちます

点検：人が確かめる（職員 ID が出たこと。もう一度打つと止まること）

### 二人目からの職員を登録する（new_staff）

管理者が手元で打ちます。職員はゲートを通って作られ、操作の記録は打った管理者に結ばれます。管理者でない職員の ID では止まります。

```bash
uv run python scripts/new_staff.py --admin STF-… --name "呼び名"                          # 職員（Staff）を作る。職員 ID（STF-…）が出る
uv run python scripts/new_staff.py --admin STF-… --name "呼び名" --role Administrator     # 管理者を足すとき
```

- 出力の最後の行が、そのまま打てる次のコマンドです（`uv run python scripts/staff_token.py add STF-…`。3 の段）

点検：人が確かめる（職員 ID が出たこと）

## 3. 職員のトークンを出す（staff_token）

現場の画面（field-ui）に入るための、職員ごとのトークンです。

```bash
uv run python scripts/staff_token.py add STF-…      # トークンは一度だけ画面に出る。職員に手で渡す
uv run python scripts/staff_token.py list           # 職員 ID だけが出る
uv run python scripts/staff_token.py remove STF-…   # 辞めた・なくしたとき
```

- 表は `~/.config/nest/field-ui-staff.json`（権限 600。職員 ID とトークンの sha256 だけ）
- トークンは、リポジトリにも会話にもメールにも書きません

点検：[3] `field-ui-staff.json` が 600 でリンクでない（無ければ WARN）。トークンを手で渡したことは人が確かめる

## 4. 本人を登録する（new_client）

本人は Claude の外で、手元のターミナルから作ります。仮名（`displayCode`）は道具が発番します。

```bash
uv run python scripts/new_client.py add --staff STF-… --family 氏 --given 名 --birth YYYY-MM-DD --address "住所" --address-certainty 確度
uv run python scripts/new_client.py find --family 氏 --given 名     # 名前から仮名を引く
```

- かなは `--family-kana`・`--given-kana` で入れられます。生年月日と住所は分かれば入れます
- 住所を入れるときは、確度（`--address-certainty`）も必ず入れます。**確度は後から変えられない**ので、何で確かめた住所かで選びます（台帳 G-93）

  | 値 | 選ぶとき |
  |---|---|
  | `Confirmed` | 住民票・受給者証などの書類で確かめた |
  | `SelfReport` | 本人の申告 |
  | `Hearsay` | 家族・関係者からの伝聞 |
  | `Inference` | 推定 |
  | `Unspecified` | 分からない |
- 同じ氏名の本人がいて、生年月日が同じか、どちらかに生年月日が無ければ作りません（二重登録のおそれ）。出た仮名で、その人が別人かを確かめます
- 出た仮名を、本人の紙の記録に書き添えます。Claude にはこの仮名で伝えます

点検：人が確かめる（`find` で仮名が引けること）

## 4.5 Claude Desktop をつなぐ（設定と、語りから未確定で入れる）

段 0 の操作 2〜5 と、5 の段の後半（書き込みの案を承認する）は、この段を済ませてから使います。**今は架空の事例の DB でだけ使います**（台帳 G-80）。Claude の照会と書き込み受付は、架空の印のある DB でだけ動きます（試走では 1 の「試走のときだけ」で印を置いています）。

### (a) 設定を足す

設定の JSON は手で開きません。道具が、Claude Desktop の設定（`~/Library/Application Support/Claude/claude_desktop_config.json`）に 3 つを足します：読むだけの照会口 `nest-personal`・`nest-resource` と、書き込み受付 `nest-gate`（案を点検して未確定で入れる道具）。中身はひな形 `configs/claude_desktop_config.json` と同じで、このフォルダと uv の完全なパスを道具が埋めます。ほかの道具の設定は消しません。前の設定は同じ場所に `.bak` として残ります。

続けて、書き込み受付が「誰が出した案か」を知るための職員の ID を設定します。書くのは、この Mac で Claude Desktop に語りを貼る人、つまり**案を出す人**の職員 ID（`STF-…`）を一つです。**案を出す人と承認する人を分けるときは、職員（Staff）の ID を書きます**（2 の段の後半の `new_staff` で作った職員）。承認は 5 の段の後半で、別の人の ID（管理者など）で打ちます。管理者の ID（2 の段で控えたもの）を書くと、その人が自分で出した案を自分で承認することになり、承認の記録に自己承認（selfApproval）が付きます。一人で回す試走ではそれでもかまいません。ファイルは `~/.config/nest/nest-gate.env`（権限 600）で、道具が作ります。中身は開きません。Claude にも見せません（Claude は職員の ID を指定できません）。DB を起こしてから打ちます（Active の職員かを確かめるため）。

```bash
uv run python scripts/desktop_config.py add     # 「足した：nest-personal・nest-resource・nest-gate …」と出ること
uv run python scripts/desktop_config.py check   # 「足してある：…」と出ること
uv run python scripts/gate_staff.py set --staff STF-…   # 「設定した：…（権限 600）」と出ること
uv run python scripts/gate_staff.py check       # 「設定してある：…」と出ること（ID そのものは出ない）
```

- 「止めた：Desktop の設定が読めない」と出たら、何も書いていません。設定を自分で直さず、出た行を Claude Code に伝えます
- 「止めた：個人の側に Active の職員としていない」と出たら、何も書いていません。2 の段で出た職員 ID を打ち直します
- Claude Desktop を終了して（⌘Q）、起動し直します。道具（`nest-personal`・`nest-resource`・`nest-gate`）が見えることを確かめます
- doctor の [3] が「`nest-gate.env`: 権限 600」、[10] が「Desktop の設定に nest-personal がある」「Desktop の設定に nest-gate（書き込み受付）がある」になることを確かめます

```bash
./scripts/doctor.sh                         # [3] nest-gate.env が権限 600、[10] nest-personal と nest-gate があること
```

### (b) Claude Desktop に語りを貼る（narrative-extractor → 仮名の復唱 → 未確定で入る）

1. **Claude Desktop（Mac のアプリ）のチャットで**新しい会話を開き、「C-…… の面談記録から書き込みの案を作って」と頼んで、続けて原文を貼ります（`narrative-extractor` が動きます）。フォルダーは選びません。フォルダーを選ばせる画面は Claude Code（ターミナルの Claude Code と同じもの）で、`nest-gate` がつながっていません。ターミナルの Claude Code にも貼りません
   - **原文は、見出しの行（日付のある行。例：「2026-11-02 訪問」）から貼ります。** 見出しの行が無いと面接の日が分からず、面接記録（supportLog）が作れません
2. 架空の事例（`fixture_kakuu_haruto.md`）は、**§2 の語りをそのまま貼ってかまいません**（§3 も同じ）。**§1（本人の登録の値。実名・住所・生年月日）は貼りません。** 実データは貼りません（台帳 G-80）
3. 語りに確度の印を付けるなら、文の直後（句点「。」の後）に【本人の話】【伝聞】【確認済み】【未確認】【推測】のどれかを置きます。印はその直前の一文にだけかかります（文の前に置かない。ほかの語の印は点検で止まります）
4. Claude が案の要点（事実の件数・面接記録・禁忌と推奨ケアの候補）を示し、「対象は C-…… の本人です。この本人に未確定で入れてよいですか」と仮名を復唱します。**本人の紙の記録に書き添えた仮名と一字ずつ見比べ**、合っていれば「はい」と答えます。違えば「違う。C-…… です」と正しい仮名を伝えます（「はい」と答えるまで Claude は出しません）
5. 「はい」の後、Claude が書き込み受付（`nest-gate` の `submit_proposal`）を呼び、案が入口の点検とゲートを通って**未確定（Pending）で入ります**。Claude Desktop が道具を使ってよいかを聞いてきたら、許可します。返事に入れた先の仮名と件数が出ます（例：「C-…… に未確定（Pending）で 12 件入れた（Record 11・SupportLog 1）」）。仮名が 4 で復唱したものと同じかを確かめます
6. 止まったときは、返事に「C-…… には何も入れていない（0 件）」と理由が出ます。**DB には何も入りません**（入口の点検でもゲートでも同じ）。Claude が理由をそのまま示し、理由のとおりに案を作り直して、4 の復唱からやり直します。案の JSON は人が手で直さないでください。原文に無いことを足して通すこともしません。同じ理由で二度止まったら、Claude は出し直さずに相談してきます
- Claude は DB に直接書きません。書くのはゲートだけで、通った案は AI 由来なので未確定で入ります
- **原文は、引用の照合と原本の指紋（documentHash）にだけ使い、DB に入れません。** DB に入るのは事実ごとの要約（text）と引用（quote）です
- 今は自分の記録（OwnCaseRecord）だけを受けます。他の機関からの書面（ProvisionDocument）は止まります

### (c) 未確定で入ったことを確かめる（review_proposals list）

```bash
uv run python scripts/review_proposals.py list --code C-……   # (b) で復唱した仮名の本人の分だけ、未確定で並ぶ
```

- 並んだ件数が (b) の返事の件数と合うかを確かめます。合わないときは `--code` を外して全部を出し、違う本人の行に並んでいたら、承認せずに差し戻します（5 の段の後半）
- 全部を出したときの本人「―」の行は、どの本人にも結ばれていないもの（本人の記録・関わりのどれともつながっていない）です。承認の前に `show` で中身を見ます
- 承認・差し戻しは 5 の段の後半（review_proposals）で一つずつ行います

点検：[3]（`nest-gate.env` が 600）・[10]（Desktop の設定に nest-personal・nest-gate がある）。仮名を見比べて「はい」と答えたこと、案が未確定で並んだことは人が確かめる（`review_proposals.py list`）

### MCP が使えないときの予備（submit_proposal）

Claude Desktop で `nest-gate` が使えないとき（道具が見えない・設定が無いと言われる）だけ使います。Claude には (b) の 1〜3 のとおりに頼み、案（JSON）だけを返してもらいます。**河原さんが Claude Desktop で (a)〜(c) の一巡を確かめた後に、この予備の道具は外します**（台帳 G-94・G-96）。

1. 貼った原文と返ってきた案を、リポジトリの外の手元のフォルダに保存します（例：原文は `~/nest-intake/原文.txt`、案は `~/nest-intake/案.json`）。原文は貼ったものと一字も変えません。案の `clientId` は空か `CLI-…` のままでかまいません（道具が仮名から入れます）
2. 次を打ちます

```bash
mkdir -m 700 -p ~/nest-intake
uv run python scripts/submit_proposal.py --staff STF-… --code C-…… --original ~/nest-intake/原文.txt --proposal ~/nest-intake/案.json
```

- 道具は書き込み受付と同じ点検（原文に無い引用・引用に無い数字・原文の印と違う確度・型に無い項目）を通してから、ゲートに渡します。**点検で止まっても、ゲートで止まっても（`止めた：…`・`止めた（ゲート）：…`）、DB には何も入りません**
- 止まったときの直し方：**案の JSON は手で直さない。** 止めた行をそのまま会話に貼り、「この理由で止まった。案を作り直して」と頼みます。返ってきた案で `~/nest-intake/案.json` を置き換え、同じコマンドを打ち直します。点検の結果を自分で読み替えて通しません
- 通ったら (c) で確かめます。`~/nest-intake/` の原文と案のファイルを消します

## 5. 支援記録を入れる（field-ui）

```bash
uv run python field-ui/server.py          # http://127.0.0.1:8001/
cd sos && PORT=8010 uv run python api_server.py     # SOS：http://127.0.0.1:8010/app/?id=C-……
```

- field-ui は、ブラウザで開き、3 で受け取った職員のトークンで入ります。「支援記録の入力」（`/record`）で記録を書きます。記録はゲートを通って入ります
- 一度入ると、ブラウザが 12 時間覚えていて、field-ui を起こし直しても聞かれずに入れます。出る操作（ログアウト）はありません。**共用の端末では使いません**（次の人がそのまま本人の一覧を見られるため）。使うときはブラウザのプライベートウィンドウで開き、終わったらウィンドウを閉じます（閉じると覚えていたものが消えます）。端末を置き忘れたなど、すぐに入れなくしたいときは、その職員のトークンを `uv run python scripts/staff_token.py remove STF-…` で消し、3 の段で出し直します
- SOS の既定のポートは 8000 です。ほかで使っていれば `PORT` で変えます。**この Mac では 8000 を別の道具（open-notebook）が使っているので 8010 にします**
- 本人の一覧は登録の新しい順で、包みの上限（500 人）を超えると「登録の新しい順に 500 人だけ出しています」と画面に出ます（古い本人は一覧に出ません）
- SOS は職員のトークンではなく、共通のトークン（環境変数 `APP_ACCESS_TOKEN`）で入ります。起動する端末で設定します。値はリポジトリにも会話にも書きません。設定が無ければ SOS は止まります
- 上の http://127.0.0.1 で使うときは、二つとも `SESSION_COOKIE_SECURE=false` を付けて起動します（例：`SESSION_COOKIE_SECURE=false uv run python field-ui/server.py`）。付けないと、ブラウザによっては入れません。https を通すときは付けません
- 二つのサーバーは前面で動きます。別々の端末で起動します。SOS の端末は `cd sos` したままになるので、ほかの道具（`scripts/…`）はリポジトリの直下の端末で打ちます
- 画面には実名・かな・電話・住所・生年月日が出ません。本人は仮名で選びます（先頭の「先に読むこと」）

点検：人が確かめる（画面が 127.0.0.1 で開き、トークンで入れること。doctor は画面のサーバーを見ません）

### 書き込みの案を点検して承認する（review_proposals）

AI が作ったもの（`narrative-extractor` の案など）は未確定（Pending）で入ります（入れ方は 4.5 の (b)。確かめ方は (c)）。職員が一つずつ見て、承認するか差し戻します。

```bash
uv run python scripts/review_proposals.py list                                   # 未確定の一覧（古い順）。本人は仮名で出る
uv run python scripts/review_proposals.py show --id REC-…                        # 一件の項目（列挙値は表示名つき）と根拠の引用を見る
uv run python scripts/review_proposals.py approve --staff STF-… --id REC-…       # 承認する（Active になる）
uv run python scripts/review_proposals.py reject --staff STF-… --id REC-… --reason "…"   # 差し戻す（Inactive になる）。理由は一行・任意・名前を書かない
uv run python scripts/review_proposals.py list --rejected                        # 差し戻したものを理由と見る
```

- `--id` には一覧に出た ID（`REC-…`・`NGA-…`・`CPF-…` など）を一つだけ書きます。まとめての承認はしません
- 差し戻しの理由（`--reason`）は AuditLog の `reason` に残り、`show` と `list --rejected` で見えます。理由は一行・200 字までで、省けます。名前（本人・家族・職員）を書きません（台帳 G-91）
- 承認・差し戻しは AuditLog に残ります。自分で登録したものを承認すると「自己承認」と出て、`selfApproval` が付きます
- 承認する前に、`show` で根拠の引用を読みます。引用が無いもの・引用と中身が合わないものは差し戻します
- 実データでは、Claude に渡せない間（台帳 G-80）AI の案が無いので、この段は使いません

点検：人が確かめる（一覧が古い順で、根拠の引用を読んでから決めたこと）

## 6. 音声を扱う（録音・文字起こし・purge_voice）

- 録音は field-ui の「音声の録音」（`/voice`）で行います。録音は `nest_voice_data/` に置かれます（権限 700・Time Machine の対象外）
- **文字起こしは既定で止まっています**（Google の Gemini に送るため。`docs/external-api.md` NEXT-03）。使うのは、事業所が Gemini の契約を確かめ、`docs/EXTERNAL_API_SETUP.md` の手順で記録と設定を作ったときだけです
- **文字起こしが止まっている間は、録音は残りません。** 録音を置くのは文字起こしができた後だけで、できなければ画面は「…（外部への送信を止めているか、文字起こしに失敗しました）。録音は残していません…」と返し、録音を消します。止めている間は、聞きながら文に起こします
- 録音そのもの・文字起こしの全文は DB に入れません。詳しくは `docs/VOICE_RECORDING_GUIDE.md`

今の既定（文字起こしを止めている）で打つのは、録音が残らないことの確かめだけです。5 の段で起こした field-ui を使います。

```bash
# (1) field-ui の「音声の録音」（/voice）で本人を選び、数秒録音して送る → 「…外部への送信を止めているか…録音は残していません…」と出る
ls -A nest_voice_data          # (2) 何も出ないか「No such file or directory」なら、録音は残っていない
```

音声は、文字起こしの記録が承認されたら消し、遅くとも 30 日で消します。道具は自動では動かないので、人が流します。

- **流す日は、週に一度、バックアップを取る日です**（2026-11-06 河原さん。計画 N-45）。曜日は金曜日（書き込みが無ければ、その週の最後に書き込んだ日。7 の段）。コマンドは 7 の枠にあります（DB を起こして流し、DB を止めてからバックアップを取る）
- DB が起きていないと、承認済みの音声を見分けられず、30 日を過ぎたものだけを消します（道具は「DB を読めない」と知らせます）

点検：[9] 置き場所が 700・Time Machine の対象外・30 日を過ぎた音声が無い（あれば FAIL）。文字起こしの設定は [3]（`external-api-features.json`・`external-api-record.json` が無ければ WARN。今は無いのが正しい状態）

## 7. バックアップを取る・戻す（backup）

**DB に書き込んだ日の作業の終わりに、DB を止めてから取ります**（止まる点 F-1 で決めた周期）。世代は 4 つで、古いものは道具が消します。

**週に一度、金曜日のバックアップで、音声も消します**（6。計画 N-45・台帳 G-90）。金曜日に書き込みが無ければ（バックアップを取らない日なら）、その週の最後に書き込んだ日に流します。その日は、DB が起きているうちに purge_voice を流してから DB を止めます。ほかの日は purge_voice の 2 行を飛ばします。

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d          # 止めていたら起こす（音声を消すため）
uv run python scripts/backup.py count                                        # DB が起ききるまで待つ（数も出る）
uv run python scripts/purge_voice.py                                         # 週に一度の日：消す音声を数える（消さない）
uv run python scripts/purge_voice.py --write                                 # 週に一度の日：消す
docker compose --env-file ~/.config/nest/neo4j-redesign.env down
uv run python scripts/backup.py dump       # ~/nest-backup/<日時>/neo4j.dump
uv run python scripts/backup.py list       # 世代の一覧
```

- 音声を先に消してからバックアップを取ります。バックアップに音声は入りません（音声は `nest_voice_data/` にあり、DB の外です）

戻すとき（今の個人の側を、その世代で置き換えます）：

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d          # 止めていたら起こす
uv run python scripts/backup.py count                                        # 起ききるまで待つ。戻す前の数（控える）
uv run python scripts/new_client.py add --staff STF-… --family 確かめ --given 戻し     # 試走のときだけ：取った後に架空の本人を一人足す
docker compose --env-file ~/.config/nest/neo4j-redesign.env down
uv run python scripts/backup.py restore <日時>                               # list に出た名前をそのまま（例：20261110-114507）
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d
uv run python scripts/backup.py count                                        # 起ききるまで待つ。戻した後の数が、戻す前の数と同じこと
uv run python scripts/new_client.py find --family 確かめ --given 戻し        # 試走のときだけ：「見つからない」なら戻せた
```

- restore が「戻した：…」を出さず「止めた：…」を出したら、戻っていません。先に進まない（その後の数も find も、戻す前の DB を見ているだけです）
- 戻せたかは数で見ます。戻した後の数が、その世代を取ったときの中身と合うかを確かめます。知っている本人を find で引くだけでは、戻す前の DB にも同じ本人がいるので区別できません
- 試走のときだけ、戻す前の数を控えた後に架空の本人（確かめ 戻し）を一人足してから戻します。戻せていれば、その本人は find で「見つからない」になり、戻した後の数は控えた数と同じです（戻せていなければ本人（Client）が一つ多い）。実データでは、この 2 行を飛ばします
- `up -d` の後の `count` は、DB が起ききるまで待ってから数を出します（起きる前に道具を打つと再試行の行が出るため）

- バックアップは要配慮個人情報の写しです。外のサービス（クラウドのドライブなど）に置きません

点検：[7] FileVault が有効、[8] `~/nest-backup` が 700・Time Machine の対象外。取ったこと・周期を守っていること・戻せることは人が確かめる（doctor は日付を見ません）

## 8. 本人を廃棄する（purge_client）

管理者（Administrator）が手元で、本人一人ずつ行います。Claude は廃棄しません。

```bash
# (1) 保存の判断を書く（理由に名前を書かない）
uv run python scripts/purge_client.py decide --admin STF-… --code C-…… --decision Delete --decided-on YYYY-MM-DD --reason "…"
# (2) 試しの実行（何も消さない）
uv run python scripts/purge_client.py purge --admin STF-… --code C-……
# (3) 消す（仮名を打ち返す）
uv run python scripts/purge_client.py purge --admin STF-… --code C-…… --write --confirm C-……
```

- (2) で、消す件数・残す人（ほかの本人にもつながる人）の数・他の機関から受け取った記録の件数・音声の件数を見ます。他の機関から受け取った記録を消してよいかは、人が確かめます
- (3) は音声を先に消し、そのあと DB を消します。音声を一つでも消せなければ DB は消さず、理由を出して止まります。音声を手で消してから、もう一度流します
- 消した後：新しいバックアップを取り、戻せることを確かめてから、消した日より前のバックアップを消します（`docs/PRIVACY_GUIDELINES.md` §5）。次の枠を上から打ちます。`rm` は使いません

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env down
uv run python scripts/backup.py dump                                       # 「取った：…/<日時>」の日時が <新しい世代>。控える
uv run python scripts/backup.py restore <新しい世代>                        # dump の「取った：…/20261110-121315」の最後の名前をそのまま
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d
uv run python scripts/backup.py count                                      # 起ききるまで待つ。廃棄の前より、消した件数だけ減っている
uv run python scripts/new_client.py find --family 氏 --given 名            # 廃棄した本人の氏名で引き、「見つからない」こと
uv run python scripts/backup.py prune --before <新しい世代>                 # 消す世代の一覧（何も消さない）。<新しい世代> は残る
uv run python scripts/backup.py prune --before <新しい世代> --write         # 消して、残った世代を出す
```

- restore が「止めた：…」を出したら先に進まない（7 と同じ。古い世代も消さない）
- `--before` に在る世代の名前を打たないと、何も消さずに止まります（打ち間違えで新しい方を消さないため）。消すのは `<新しい世代>` より前の世代だけです

点検：人が確かめる（試しの実行の件数、消した後のバックアップ）。音声の残りは [9]、バックアップの置き場所は [8]

## 9. 点検する（doctor）と WARN・FAIL の読み方

```bash
./scripts/doctor.sh
```

DB を起こした後と、設定を変えた後に流します。最後の行が `=== Summary: N passed, N warned, N failed ===` です。

| 段 | 意味 | すること |
|---|---|---|
| OK | 決まりのとおり | なし |
| FAIL | 決まりから外れている。最後に 1 つでもあれば、道具は 1 を返す | 行に書いてある直し方で直し、流し直す。直るまで実データを扱わない |
| WARN | 設定のファイルが無い。新しい Mac なら出てよい。設定済みの Mac で出たら、壊れている印 | 新しい Mac か、設定済みの Mac かで読む。今は external-api の 2 つの WARN が正しい状態（台帳 G-80） |
| INFO | 知らせるだけ（まだ無い置き場所、Claude Desktop の設定） | なし |

doctor の項目：[1] 前の DB は動いていない、[2] 新しい DB の待ち受け、[3] 接続の設定のファイル、[4] `.mcp.json`、[5] スキルのリンク、[6] 正典のずれ、[7] FileVault、[8] バックアップの置き場所、[9] 音声の置き場所、[10] Claude Desktop の設定

点検：[1]〜[10]

## 10. その日の終わりに DB を止める

その日の作業が終わったら、DB を止めます。バックアップを取る日は 7 の枠の中で止めているので、この段は飛ばします。

### 試走（架空の事例の DB）のときだけ：止める前に DB つきの試験を流す

試走の終わりに、DB を起こしたまま、DB つきの試験をまとめて流します。**実データを入れた DB では流しません**（試験は架空の職員・本人・案を DB に足します）。

```bash
NEST_LIVE_DB=1 uv run pytest -q             # 最後の行に failed が無いこと
```

- 試験が足した架空の本人・案は残ります（試走の DB の中身も消しません）。そのため、`review_proposals.py list` などに試験のものが混ざります
- 段 1 の `live_mark.py` で置いた架空の印は残したままでかまいません（試験は印の数が始める前と同じかを見ます）

### 止める

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env down
docker ps                                   # 新しい DB（nest-redesign-personal・nest-redesign-resource）が出ないこと
```

点検：人が確かめる（`docker ps` に新しい DB の 2 つが出ないこと）

---

## 段と点検の対応

| 段 | 点検 |
|---|---|
| 1. DB を起こす | [1] [2] [3] [7] |
| 2. 最初の管理者（bootstrap_admin） | 人が確かめる |
| 3. 職員のトークン（staff_token） | [3]。トークンを手で渡したことは人が確かめる |
| 4. 本人の登録（new_client） | 人が確かめる |
| 4.5 Claude Desktop をつなぐ（設定・narrative-extractor・書き込み受付 nest-gate） | [3]（nest-gate.env）・[10]。仮名を見比べて「はい」と答えたこと、案が未確定で並んだことは人が確かめる |
| 5. 支援記録の入力（field-ui） | 人が確かめる |
| 6. 音声（録音・文字起こし・purge_voice） | [9]（音声）・[3]（文字起こしの設定） |
| 7. バックアップ（backup） | [7] [8]。取ったこと・周期・戻せることは人が確かめる |
| 8. 本人の廃棄（purge_client） | 人が確かめる。音声の残りは [9]、バックアップは [8] |
| 9. 点検（doctor） | [1] [2] [3] [4] [5] [6] [7] [8] [9] [10] |
| 10. その日の終わりに DB を止める | 人が確かめる（`docker ps` に新しい DB の 2 つが出ないこと） |

## 道具がまだ無いこと・決まっていないこと

- 今は無し（段階 I で、職員の登録・書き込みの案の承認・purge_voice を流す日を埋めた。2026-11-06）
