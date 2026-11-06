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

導入した日に、まず一通り試す 5 つです。くわしい打ち方は 1〜9 の段にあります。**今は実データを Claude に渡さない**ので（台帳 G-80）、Claude を使う操作（2・3・5）は、架空の事例の DB でだけ試します。

1. **本人を登録する**：手元のターミナルで `scripts/new_client.py add` を打ち、仮名（`C-……`）を受け取ります（4 の段）。Claude には名前を伝えません。以後、Claude にも画面にも仮名で伝えます
2. **緊急の情報を確かめる**：現場では SOS の画面（5 の段）で、仮名から確かめます。Claude に「C-…… の緊急時の情報」と頼むと `emergency-protocol` が、禁忌（命に関わる → パニックを招く → 不快）、推奨ケア、支える人、医療、後見・任意代理の順に出します。連絡先・氏名・住所は Claude からは出ないので、手元の緊急連絡カードと SOS の画面で確かめます
3. **訪問の前の準備をする**：Claude に「C-…… の訪問準備」と頼みます（`visit-prep`）。前回の記録、禁忌、最近の変化、今回確かめることがまとまります
4. **支援記録を残す**：field-ui の「支援記録の入力」（`/record`）で書きます（5 の段）。記録はゲートを通って入ります。語りから書き込みの案を作る `narrative-extractor` は、架空の事例でだけ使います
5. **更新の期限を確かめる**：Claude に「C-…… の手帳・受給者証の期限」と頼みます（`data-quality-agent`）。更新の漏れは本人の不利益に直結するので、月に一度は確かめます

---

## 1. DB を起こす・止める

DB は使うときだけ起こし、その日の作業の終わりに止めます。

```bash
cd ~/Dev-Work/project/nest-support
docker ps                                   # 前の DB（nest-support-neo4j など）が動いていないこと
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d
./scripts/doctor.sh                         # 最後の行が「0 failed」であること
# …作業…
docker compose --env-file ~/.config/nest/neo4j-redesign.env down
```

- `--remove-orphans` は付けません
- 接続の設定のファイル（`~/.config/nest/neo4j-redesign.env`）は開きません。人にも会話にも見せません

点検：[1] 前の DB が動いていない、[2] 新しい DB が 127.0.0.1 だけで待ち受けている、[3] 接続の設定のファイルが 600、[7] FileVault が有効

## 2. 最初の管理者を作る（bootstrap_admin）

個人の側に職員が一人もいないときに、一度だけ使います。表示名は呼び名でかまいません。

```bash
uv run python scripts/bootstrap_admin.py --name "事務局"    # 職員 ID（STF-…）が出る
```

- 出た職員 ID を手元の紙に控えます。以後、管理者の操作でこの ID を使います
- 職員がすでにいる DB では、道具が止まります（二人目の管理者は作れません）

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
uv run python scripts/new_client.py add --staff STF-… --family 氏 --given 名 --birth YYYY-MM-DD --address "住所"
uv run python scripts/new_client.py find --family 氏 --given 名     # 名前から仮名を引く
```

- かなは `--family-kana`・`--given-kana` で入れられます。生年月日と住所は分かれば入れます
- 同じ氏名の本人がいて、生年月日が同じか、どちらかに生年月日が無ければ作りません（二重登録のおそれ）。出た仮名で、その人が別人かを確かめます
- 出た仮名を、本人の紙の記録に書き添えます。Claude にはこの仮名で伝えます

点検：人が確かめる（`find` で仮名が引けること）

## 5. 支援記録を入れる（field-ui）

```bash
uv run python field-ui/server.py          # http://127.0.0.1:8001/
cd sos && PORT=8010 uv run python api_server.py     # SOS：http://127.0.0.1:8010/app/?id=C-……
```

- field-ui は、ブラウザで開き、3 で受け取った職員のトークンで入ります。「支援記録の入力」（`/record`）で記録を書きます。記録はゲートを通って入ります
- SOS の既定のポートは 8000 です。ほかで使っていれば `PORT` で変えます。**この Mac では 8000 を別の道具（open-notebook）が使っているので 8010 にします**
- 本人の一覧は登録の新しい順で、包みの上限（500 人）を超えると「登録の新しい順に 500 人だけ出しています」と画面に出ます（古い本人は一覧に出ません）
- SOS は職員のトークンではなく、共通のトークン（環境変数 `APP_ACCESS_TOKEN`）で入ります。起動する端末で設定します。値はリポジトリにも会話にも書きません。設定が無ければ SOS は止まります
- 上の http://127.0.0.1 で使うときは、二つとも `SESSION_COOKIE_SECURE=false` を付けて起動します（例：`SESSION_COOKIE_SECURE=false uv run python field-ui/server.py`）。付けないと、ブラウザによっては入れません。https を通すときは付けません
- 二つのサーバーは前面で動きます。別々の端末で起動します。SOS の端末は `cd sos` したままになるので、ほかの道具（`scripts/…`）はリポジトリの直下の端末で打ちます
- 画面には実名・かな・電話・住所・生年月日が出ません。本人は仮名で選びます（先頭の「先に読むこと」）

点検：人が確かめる（画面が 127.0.0.1 で開き、トークンで入れること。doctor は画面のサーバーを見ません）

## 6. 音声を扱う（録音・文字起こし・purge_voice）

- 録音は field-ui の「音声の録音」（`/voice`）で行います。録音は `nest_voice_data/` に置かれます（権限 700・Time Machine の対象外）
- **文字起こしは既定で止まっています**（Google の Gemini に送るため。`docs/external-api.md` NEXT-03）。使うのは、事業所が Gemini の契約を確かめ、`docs/EXTERNAL_API_SETUP.md` の手順で記録と設定を作ったときだけです
- **文字起こしが止まっている間は、録音は残りません。** 録音を置くのは文字起こしができた後だけで、できなければ画面は「文字起こしに失敗しました」と返し、録音を消します。止めている間は、聞きながら文に起こします
- 録音そのもの・文字起こしの全文は DB に入れません。詳しくは `docs/VOICE_RECORDING_GUIDE.md`

音声は、文字起こしの記録が承認されたら消し、遅くとも 30 日で消します。道具は自動では動かないので、人が流します。

```bash
uv run python scripts/purge_voice.py            # 数えるだけ（消さない）
uv run python scripts/purge_voice.py --write    # 消す
```

- 流す日は事業所で決めます（まだ決めていません。Claude の案：承認をした日の作業の終わり）

点検：[9] 置き場所が 700・Time Machine の対象外・30 日を過ぎた音声が無い（あれば FAIL）。文字起こしの設定は [3]（`external-api-features.json`・`external-api-record.json` が無ければ WARN。今は無いのが正しい状態）

## 7. バックアップを取る・戻す（backup）

**DB に書き込んだ日の作業の終わりに、DB を止めてから取ります**（止まる点 F-1 で決めた周期）。世代は 4 つで、古いものは道具が消します。

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env down
uv run python scripts/backup.py dump       # ~/nest-backup/<日時>/neo4j.dump
uv run python scripts/backup.py list       # 世代の一覧
```

戻すとき（今の個人の側を、その世代で置き換えます）：

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env down
uv run python scripts/backup.py restore <日時>
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d
uv run python scripts/new_client.py find --family 氏 --given 名     # 戻ったことを、知っている本人で確かめる
```

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
- 消した後：7 の手順で新しいバックアップを取り、戻せることを確かめてから、消した日より前のバックアップを人が消します（`docs/PRIVACY_GUIDELINES.md` §5）

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

---

## 段と点検の対応

| 段 | 点検 |
|---|---|
| 1. DB を起こす・止める | [1] [2] [3] [7] |
| 2. 最初の管理者（bootstrap_admin） | 人が確かめる |
| 3. 職員のトークン（staff_token） | [3]。トークンを手で渡したことは人が確かめる |
| 4. 本人の登録（new_client） | 人が確かめる |
| 5. 支援記録の入力（field-ui） | 人が確かめる |
| 6. 音声（録音・文字起こし・purge_voice） | [9]（音声）・[3]（文字起こしの設定） |
| 7. バックアップ（backup） | [7] [8]。取ったこと・周期・戻せることは人が確かめる |
| 8. 本人の廃棄（purge_client） | 人が確かめる。音声の残りは [9]、バックアップは [8] |
| 9. 点検（doctor） | [1] [2] [3] [4] [5] [6] [7] [8] [9] [10] |

## 道具がまだ無いこと・決まっていないこと

1. **書き込みの案を通す・承認する**：`narrative-extractor` の案を点検に通し（`nest/gate/intake.py`）、未確定のものを承認する（`nest/gate/approve.py`）操作に、手元で打つ道具はまだありません。実データでは、Claude に渡せない間（台帳 G-80）この段は使いません
2. **音声を消す日**：決めていません（6）
