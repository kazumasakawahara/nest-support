# 止まる点 F-1 で決めること（計画 N-34。2026-11-06 たたき台）

- 決めるのは河原さん。下の「案」は Claude の案で、一つに絞り、理由と却下した案を添えた
- 調べ方：前の DB の跡は**名前・種類・権限・大きさ・日付だけ**を見た（`stat`・`du`・`docker inspect` の取り付け先・`tmutil isexcluded`）。中は開いていない・起動していない。設定のファイルは中を読んでいない。Claude Desktop の設定は MCP の名前だけを読んだ
- tsunagu-net は読むだけ（HEAD 3bf49ca。`docs/proposals/2026-11-05-purge-draft.md`・`tsunagu/gate/purge.py`・`scripts/retention_due.py`・`docs/SCHEMA.md` の `RetentionDecision`）
- Neo4j の書き出しの方法は Context7 で Neo4j Operations Manual を確かめた（Community 版は DB を止めてから `neo4j-admin database dump`／`load`。`load` で今の DB を置き換えるときは `--overwrite-destination`）

---

## 1. 面談の音声ファイルの保存の期間

**案：文字起こしの記録（`Record`）が承認されたら消す。承認されなくても、録音の日から 30 日で消す。**（今の仮の既定をそのまま決まりにする）

- 理由
  - 根拠として残るのは `Record` の引用（`quote`）と原文（`text`）。承認の後に音声を持ち続ける用は無く、声は本人や家族を特定しやすい
  - 30 日は、承認が滞ったときの上限。文字起こしの直しは、30 日あれば職員が音声を聞き直して済ませられる
  - 消した後も、どの音声から作ったかは `Record.documentHash`（原本の指紋）で示せる。文字起こしの案を作るときに音声の指紋を入れる（今の正典の項目で足りる。足すものは無い）
- 消したことは、事業所の記録に「誰がいつ消したか」を残す（今の VOICE_RECORDING_GUIDE のとおり）
- 却下：事業所の記録の保存の期間（年単位）と同じにする（声を長く持つ理由が無い）。承認の時にだけ消す（承認されない音声がいつまでも残る）

## 2. バックアップの置き場所と周期

**案：置き場所は `~/nest-backup/`（リポジトリの外。権限 700、Time Machine の対象外）。DB に書き込んだ日の作業の終わりに、DB を止めてから取る。世代は 4 つ残し、それより古いものは手順の中で消す。**

- 取り方：`docker compose … down` の後に、同じ版の Neo4j の像（`neo4j:5.26.32-community`）で `neo4j-admin database dump neo4j --to-path=/backups`。個人の側だけ（資源の側は tsunagu-net の一式から読み直せるので取らない）
- 戻し方：DB を止めて `neo4j-admin database load neo4j --from-path=/backups --overwrite-destination`。N-33 の試験で、架空のデータで取る・戻すの両方を確かめる
- 理由
  - Community 版は動いたまま書き出せない。DB は使うときだけ起こす運用なので、止めるときに取るのが自然
  - 書き込みの無い日に取っても同じものが増えるだけ。書き込んだ日に限れば、失うのは最大でその日の作業
  - 4 世代：一つ壊れていても前に戻れ、廃棄（3）の後に古い世代を消す手間が小さい
  - 起動ディスクは FileVault が有効（`fdesetup status`：On。確かめた）。置き場所は書類・デスクトップのクラウド同期を避ける
  - 外のサービスには置かない（`docs/external-api.md` に行を足さない）
- 却下：毎日決まった時刻に自動で取る（Mac が DB を止めている時間に動かす仕組みが要り、止め忘れと重なると取れない）。動いたまま書き出す（Community 版にない）。Time Machine に任せる（Time Machine の先が外付けや NAS だと、暗号化と置き場所を事業所が決められない）

## 3. 廃棄の手順

**案：tsunagu-net の形（`purge.py`）にそろえ、本人（`Client`）一人ずつ、Administrator が手元の道具で消す。**

- 流れ
  1. Administrator が保存の判断（`RetentionDecision`。決めた日・残す／消す・理由・次に見直す日）をゲートで書く。人の操作だけ。AI の案からは作れない（未確定 `Pending` を経ない。`origin: Human`）
  2. 消す道具 `scripts/purge_client.py --admin STF-… --code C-……`：試しの実行（何も書かず、消す件数と残す件数だけ示す）
  3. `--write --confirm C-……`（仮名の打ち返し）で本当に消す（`DETACH DELETE`）
  4. 消したら監査ログを **1 件**だけ足す（操作 `Purge`。本人の ID、もとにした保存の判断の ID、種類ごとの件数、残した人の数。名前・本文・理由の文は書かない）
  5. 消した後に新しいバックアップを取り、戻せることを確かめてから、**消した日より前のバックアップを人が消す**（道具は消さない）
- 消す範囲：その本人と、その本人にだけつながるもの（禁忌・推奨ケア・役割・手帳・記録・関わり・確認・支援記録など。つながる先がすべて消えるものを繰り返したどる）
- 残すもの：**ほかの本人にもつながる人**（きょうだいの両方が本人のときの親など）と、その人についての記録。この本人へのつながりだけ外す。職員・機関の ID・今までの監査ログ（閲覧の記録を含む。つなぎが外れ、ID の文字だけ残る）
- 止まる場合：Administrator でない・保存の判断が無い・最後の判断が「残す」・仮名の打ち返しが合わない・本人が無い
- 限界（手順書に書く）：Neo4j は消した場所をすぐには上書きしない。トランザクションの記録も既定の期間は残る。守りは FileVault と、古いバックアップを消すこと
- いつ消すか（保存の期間）：事業所の記録の保存の規程による。法令の年数は【未照合】で、ここでは決めない。見直しの時期の一覧（tsunagu-net の `retention_due.py`）は、今は作らない（本人の数が少なく、Administrator が一覧 `neo4j-support-db` 照会 1 で見られる。要るなら後で足す）
- 理由：tsunagu-net の 5 つの判断（2026-11-05 の案 A〜E）と同じ形にすれば、約束の「確度の言葉」と同じく、二つの DB で消し方の意味がそろう。nest-support は世帯ではなく本人が中心なので、単位を本人に置き換えた
- 却下：`Inactive` にするだけ（中身が残る）。本文だけ消して形を残す（形にも続柄・生年月日が残る）。Claude に消させる（読み取りの包みは書けない。書くのはゲートだけ）

## 4. 正典に足すラベル（廃棄のため。3 を採るときだけ）

**案：tsunagu-net の正典 v0.29〜v0.30 と同じ名前で、次だけを足す（正典 v0.11）。**

| 足すもの | 中身 |
|---|---|
| ノード `RetentionDecision` | `retentionId`✅（`RTD-` ＋ ULID）, `decidedOn`✅(Date), `decision`✅(enum), `reason`✅, `nextReviewOn`(Date)。常に CREATE。Administrator が書く |
| リレーション `DECIDES_ON` | `RetentionDecision` → `Client`（tsunagu-net は → `Household`。nest-support は本人が中心） |
| 列挙値 `retentionDecision` | `Keep`, `Delete`（tsunagu-net と同じ） |
| 列挙値 `auditAction` に | `Purge` |
| `AuditLog` の項目（`action: Purge` のときだけ） | `retentionId`, `purgedCounts`, `keptPersons` |

- 理由：消したことと、何に基づいて消したかを、名前を残さずに示すのに最小の形。名前を tsunagu-net にそろえれば、正典 §10（そろえた名前）に一行足すだけで済む
- 足さないもの：事案の終了（`CaseClosure`）と見直しの一覧。3 の「いつ消すか」のとおり今は要らない
- 却下：監査ログだけで済ませる（「消す」と決めた判断と、消した操作が分かれず、誰がいつ決めたかが残らない）

---

## 5. 前の DB の処分（N-05a）

### 5.1 一覧（2026-11-06 10:00 ごろに確かめた。中は開いていない）

| もの | 種類・大きさ・日付 | 今の守り | 何か（台帳） |
|---|---|---|---|
| コンテナ `nest-support-neo4j` | neo4j:5.15-community、止まっている（Exited、restart=no） | — | 前の DB。`neo4j_data/`・`neo4j_backup/`・`neo4j_logs/`・`neo4j_plugins/` を取り付けている |
| `neo4j_data/` | 518M、2026-11-05 | 700・Time Machine 対象外・git 対象外 | 前の DB の中身。実データとして扱う。埋め込みの値を含みうる（G-33） |
| `neo4j_backup/` | 523M、2026-11-05 | 同上 | 前の DB の書き出しとみられる。同上 |
| `neo4j_logs/` | 8.4M、2026-11-05 | 同上 | 前の DB のログ |
| `neo4j_livelihood_data/`・`_logs/`・`_plugins/` | 516M・648K・13M、2026-11-05 | 同上 | 生活困窮者支援の跡。対応するコンテナは無い（G-13） |
| `.quarantine/` | 13M、2026-11-05 | 同上 | 中身は分からない（G-13・G-33） |
| `~/nest-support-hold/2026-11-05-n09-bak/` | 20 ファイル（`.bak` 19 件と `SHA256SUMS.before`） | 700・Time Machine 対象外 | 前の正典の写し（shared-schema の写し。G-45） |
| `~/nest-support-hold/2026-11-05-uncommitted/` | 20 ファイル | 同上 | 作り直しの前に未コミットだった 10 件の写しと差分（G-1） |
| `~/.config/nest/neo4j.env` | 402B、2026-10-31、600 | **Time Machine の対象** | 共有層（`support-db-neo4j`、7687）の接続の設定。漏れたパスワードと同じ値（G-70） |
| `~/.config/nest/neo4j-personal.env` | 190B、600 | **Time Machine の対象** | 前の個人層（7688）の接続の設定（G-35・G-49。一覧に無かったが見つかった） |
| Claude Desktop の設定の `neo4j`・`neo4j-shared` | MCP の名前が残っている | — | 前の MCP（G-35。直すのは河原さん） |

- 範囲の外として書くだけ：別のリポジトリ `neo4j-livelihood-support` の Docker のボリューム 4 つ、`support-db-neo4j`（neo4j-agno-agent の共有層。止まっている）、~/Dev-Work の下で 7688 を指す 7 か所（G-36）

### 5.2 中身を新しい DB へ移すか

**案：移さない。**

- 理由
  - 前の DB には、根拠の記録（`Record`）・確度・引用が無い。新しい正典は「禁忌・推奨ケアには根拠の記録が要る」なので、移してもゲートを通らない。通すには、人が元の資料から聞き直して書き込みの案を作り直すことになり、それは移すのではなく入れ直し
  - 埋め込みの値（要配慮個人情報から作った値。G-33）と実名を新しい DB に持ち込まない
  - 実データは、契約の確認の記録がそろうまで Claude に渡さない（`docs/external-api.md` §5）。移す作業そのものが Claude に中身を見せることになる
- 要る事案があれば：河原さんか職員が、紙や元の記録から `narrative-extractor` の案を作り直し、ゲートで入れる（このときは実データの扱いの決まりに従う）
- 却下：ゲートを通る形で移す道具を作る（根拠の記録を後から作ることになり、`certainty` の意味が崩れる）。そのまま写す（ゲートを通らない書き込みの道になる）

### 5.3 それぞれの扱い

| もの | 案 | 理由 |
|---|---|---|
| `nest-support-neo4j`・`neo4j_data/`・`neo4j_backup/`・`neo4j_logs/` | **消す**（河原さんが中身を確かめた後。コンテナ → フォルダの順。写しは残さない） | 移さない（5.2）ので持つ理由が無い。埋め込みの値を含みうる。中を確かめるのに起動するなら、ネットワークから切り、起動の直後にパスワードを変える（G-70） |
| `neo4j_livelihood_*`・`.quarantine/` | **消す**（河原さんが中身を確かめた後） | nest-support の新しい構成では使わない。生活困窮者支援の本体は別のリポジトリにある。中身が分からないものを持ち続けるほうが危ない |
| `~/nest-support-hold/2026-11-05-n09-bak/` | **消す**（今すぐでよい） | 前の正典の写しで、個人の情報は無い（G-33 で確かめた範囲）。新しい正典に置き換わった。元は shared-schema にある |
| `~/nest-support-hold/2026-11-05-uncommitted/` | **消す**（河原さんが一覧を見た後） | 作り直しの前の未コミットの変更で、作り直しで置き換わった。要るものがあれば河原さんが拾う |
| `~/.config/nest/neo4j-personal.env` | **消す**（前の DB と一緒に） | 前の個人層にしか使わない |
| `~/.config/nest/neo4j.env` | **残す**（nest-support からは使わない。パスワードを替えるのは neo4j-agno-agent の側で） | `support-db-neo4j`（別のプロジェクトの共有層）の設定で、nest-support の持ち物ではない。消すと向こうが動かなくなる。漏れた値なので、向こうを起動する前にパスワードを替える |
| Time Machine の中の古い世代 | **知らせるだけ**（`~/.config/nest/` は Time Machine の対象。古い世代に二つの設定のファイルが残る） | 消すかは河原さん。`~/.config/nest/` を対象外にするかも河原さん |
| Claude Desktop の `neo4j`・`neo4j-shared` | **外す**（河原さんが設定から） | 前の MCP。`npx` で外の部品を取ってくる |
| `neo4j_plugins/` | 決めない（これまでの決まりどおり扱わない） | 前のコンテナを消すと使う者がいなくなる。消すかは前の DB と一緒に河原さんが |

- 消すのは河原さん（Claude は前の DB の跡を消さない決まり）。消した後に `scripts/doctor.sh` の [1] と、`docker ps -a` で確かめる手順を N-05a の済みの判定に書く
