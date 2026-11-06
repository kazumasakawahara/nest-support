# HANDOVER — 2026-11-06 redesign/adr-001（ADR-001 の作り直し。段階 A〜E 済み。段階 F の N-37 まで済み。止まる点 F-2 で止まっている）

> 前の HANDOVER（2026-08-03 main。WAM NET スキル整合）は git 履歴（ce627d9）にある。そこに書かれた
> `~/.config/nest/neo4j.env`・ポート 7687・`nest-support-neo4j` は**前の構成**で、この枝では使わない。

## 再開コマンド（2026-11-06 11:44 に確かめた）

```bash
cd ~/Dev-Work/project/nest-support && git switch redesign/adr-001
uv run pytest -q                       # 889 passed, 122 skipped（DB を使う試験は skip）
uv run python scripts/check_drift.py   # ずれ 0 件
./scripts/doctor.sh                    # 環境の点検：28 passed, 0 failed（[7] FileVault・[8] ~/nest-backup・[9] nest_voice_data を足した）
```

DB を使う試験（結合試験のタスクのときだけ。終わったら必ず止める）：

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d     # nest-redesign-personal（37474/37687）・nest-redesign-resource（38474/38687）
NEST_LIVE_DB=1 uv run pytest -q                                       # 最後に流したのは 2026-11-06 11:42（N-37 の後）：1011 passed
docker compose --env-file ~/.config/nest/neo4j-redesign.env down      # --remove-orphans は使わない
```

- `neo4j-redesign.env` の中身は読まない・表示しない（接続の部品 `nest/connections.py` と試験が読む）
- 起動の前に `docker ps` で前の DB が動いていないことを確かめ、起動の後に 2 つとも 127.0.0.1 だけで待ち受けていることを確かめる（N-18 の条件）
- 2026-11-06 11:42 に down 済み。データのフォルダ `nest_neo4j_personal_data/` などは残っていて、`up -d` で作り直される

## 前提（実行前に現況で確かめること）

| 想定 | 確かめ方 | 最終確認日 |
|---|---|---|
| 枝 `redesign/adr-001` は origin に push 済み（河原さんが 2026-11-06 に打った。`origin/redesign/adr-001` = 34f2577）。その後、河原さんが b0b2177 まで push。河原さんが 186562d（F-1 の前の HANDOVER）まで push。**176260c〜d491a94 の 10 件とこの HANDOVER の直しが未 push（push が要る）** | `git status -sb`（`ahead N` が未 push の数） | 2026-11-06 |
| **push は河原さんが打つ。** Claude は報告に「push が要る」と書くだけ。PR は作らない・main に合流させない | — | 2026-11-06 |
| 前の DB（コンテナ `nest-support-neo4j`、`neo4j_data/` ほか）は止まっている。**実データが入っているものとして扱い、開かない・起動しない・消さない** | `docker ps -a`（Exited のまま） | 2026-11-06 |
| `support-db-neo4j`（neo4j-agno-agent の共有層 7687）は restart=no で止まっている | `docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' support-db-neo4j` → `no` | 2026-11-06 |
| 資源の側の写しは `~/Dist/tsunagu-net-trial-20261104`（tsunagu-net の 2026-11-04 の一式）から読み込んだもの | `MANIFEST.json`（台帳 G-55） | 2026-11-05 |
| tsunagu-net は `~/Dev-Work/tsunagu-net`、枝 `claude/tender-dijkstra-xo3wwc`、HEAD 3bf49ca。正典 SCHEMA v0.31・SEMANTICS v0.32（BRS-49）。**変えない** | `git -C ~/Dev-Work/tsunagu-net log -1` | 2026-11-06 |
| 共通の約束は v1.1（tsunagu-net `docs/contracts/nest-support-shared.md`） | 同ファイルの版の行 | 2026-11-05 |
| 令和 8 年法律第 45 号（民法等の一部を改正する法律）の施行日を定める政令は、まだ出ていない | e-Gov の法令検索（tsunagu-net journal `2026-11-05-mac-voluntary-guardianship.md` の手順） | 2026-11-05 |

## 現在地

- 目標：nest-support を、ADR-001（`docs/adr/ADR-001-redesign-and-shared-contract.md`。承認 2026-11-05）と約束 v1.1 に沿って作り直す。計画は `docs/implementation-plan.md`（1 タスク＝1 行）
- 進捗：
  - [x] 段階 A（送らない・埋め込まない）：N-00〜N-05・N-05b・N-18a
  - [x] 段階 B（正典）：N-06〜N-09。正典は `docs/SCHEMA.md` **v0.10**（G-63、G-64 で ADDRESSES → RESPONDS_TO）、意味の文書は `docs/SEMANTICS.md`
  - [x] 段階 C（ゲート）：N-10〜N-17
  - [x] 段階 D（DB と書き込み・承認）：N-18〜N-24a。止まる点 4 の承認済み
  - [x] N-24b：任意後見・任意代理を BRS-49 に合わせた（0270cd3・de2737b。台帳 G-62）
  - [x] 台帳の承認欄が空だった 20 件に河原さんの判断を書き、直しを入れた（f0e49c0）。前の DB を指す script を git から外した（14d1b18。G-49）
  - [x] N-25：narrative-extractor を「書き込みの案（JSON）を出すだけ」に書き直した（34f2577）
  - [x] G-63：入口に禁忌・推奨ケアの候補の欄（`ngActions`・`carePreferences`）。正典 v0.9（855b06e）
  - [x] 前の DB を指す残り 7 か所が新しい DB を指さないことを試験で固定した（2d6635a。`tests/test_old_db_code_isolated.py`）
  - [x] N-26：EXTRACTION_PROMPT から埋める指示を消し、案の形を SKILL.md に一本化した（e5fbe4f）
  - [x] N-27：列挙値の表示名を SEMANTICS に置きコードがそこから読む（G-47）、読み取りのスキル 8 本を書き直した（N-27a〜h）。G-63 の範囲を推奨ケアのすべてに広げた
  - [x] 止まる点 E-1（承認 2026-11-06）
  - [x] G-64：ADDRESSES を RESPONDS_TO に改名、正典 v0.10（41949d9）
  - [x] N-20a：確認の記録（Review）を職員がゲートで作る操作 `nest.gate.write.record_review`（b0337b2）
  - [x] N-27i：provider-search を資源の側の読み取りに。口コミ・書き込みを外した（6eb2370。台帳 G-65 に未書き直しのスキル 3 本の案）
  - [x] emergency-protocol に「手元の緊急連絡カードと SOS の画面で確かめる」の一行（4233852）
  - [x] N-28：SOS の LINE の文は SOS・仮名・時刻・位置・確かめる先だけ。external-api v0.7（f583388。台帳 G-66）
  - [x] E-2 の DB の試験：架空の本人を一人入れ、neo4j-support-db の 15 本の中身を確かめた（f4e366e。照会 15 を直した。台帳 G-67）
  - [x] 止まる点 E-2（承認 2026-11-06。G-65〜G-67 も承認）
  - [x] G-65：wamnet-provider-sync を外し、inheritance-calculator に架空の印（056d02e）。G-67：照会 15 の範囲を一行で（58f1b7a）
  - [x] N-29：利用者向けの文書を今の構成に合わせて書き直した（55c839c。台帳 G-68）
  - [x] N-30：doctor.sh を新しい構成の点検に（2290041。台帳 G-69）
  - [x] 止まる点 E-3 の判断（2026-11-06）：.env.example の試験（8ba3e66。G-70）、SOS の本人の入口を閉じて 503（8b199e1。G-66）、実務の文書を直し配布の文書 5 本を外した（04bd8a5。G-71）、廃棄 N-32・バックアップ N-33 を計画に足し仮の既定を書いた（56fe9a8。G-72。N-31 が埋まっていたので 33）
  - [x] 段階 F を計画に書いた（承認 2026-11-06。1e49ff9）
  - [x] N-34：F-1 の材料（`docs/proposals/2026-11-06-f1-decisions.md`。3d9ff96。台帳 G-73）
  - [x] 止まる点 F-1（2026-11-06 河原さん。6 点とも提案どおり、条件つき。台帳 G-74。176260c）
  - [x] 正典 v0.11：保存の判断 `RetentionDecision`・`DECIDES_ON`・監査の `Purge`（f941962）
  - [x] N-32 廃棄：`nest/gate/purge.py`・`scripts/purge_client.py`。保存の判断（消す）が無ければ試しの実行もしない（4d98e40）
  - [x] G-75：Neo4j の匿名の利用の情報の送信を止めた（6ab180d。Claude の判断）
  - [x] N-33 バックアップ：`nest/backup.py`・`scripts/backup.py`、`~/nest-backup/`、4 世代、doctor.sh（b524068）
  - [x] N-35：`lib/auth.py` を `nest/auth.py` へ（a9bbac9）
  - [x] N-36 sos：本人の入口は仮名だけ、仮名と「いるか」だけ返す。包みで読む（468cfcb。台帳 G-76）
  - [x] N-37 field-ui：職員ごとのトークン（67f13ec）、包みで読みゲートで書く・ダッシュボードは閉じる（6078e40）、音声の置き場所と消す道具（d491a94）。台帳 G-77
  - [ ] **止まる点 F-2**：sos と field-ui の画面と送る中身を河原さんに見ていただく
  - [ ] F-2 の後：N-38（新しい Mac での入れ方が済みの条件）→ F-3。N-31（任意）は段階の外
  - [ ] N-05a 前の DB の処分：移さない（決定）。消すのは河原さんが「実データの原本が別にある」を確かめてから、河原さんが打つ（手順は計画の N-05a の行）

## グレーな判断

F-2 で見ていただく、Claude が決めたこと（台帳 `docs/gray-decisions.md`。承認欄は「未承認（F-2 で確かめる）」）：

- **G-75**：Neo4j の利用の情報の送信を止めた。external-api に行（案 NEXT-08）を足すかは河原さんの判断。バックアップの DB つき試験の 1 回目の失敗の原因は確かめられていない
- **G-76**（sos）：仮名の形でなければ 400、`?name=` を受けない、アプリは `/api/client` を呼ばない、`sos/.env.example` は読めないので前の `NEO4J_*` の行が残っていれば河原さんが消す、sos の既定のポート 8000 がこの Mac の open-notebook とぶつかる
- **G-77**（field-ui）：支援記録は origin Human、文字起こしは全文を返す、消す道具は自動では動かない、却下された記録の音声は 30 日で消える、本人の廃棄では音声を消さない、sos は共有のトークンのまま、など (a)〜(i)

## 未決論点

1. **令和 8 年法律第 45 号の施行**：政令が出たら、後見・保佐を新しく使わないようゲートで止める（tsunagu-net の T-31a に合わせる。SEMANTICS SEM-GUARD-02）
2. **N-05a**：前の DB の跡は、河原さんが原本を確かめてから河原さんが消す。それまでそのまま
4. **音声を消す道具をいつ流すか**（自動にするか）・本人の廃棄のときに音声もすぐ消すか（G-77 (c)(e)）
5. **ダッシュボード**：正典の SupportLog に感情・きっかけの項目を足すか（今は閉じている）
3. **G-42 (2)**：職員を仮名で呼ぶ運用が使いにくければ、実データを入れる前にもう一度決める

## 既知の罠・注意

- **開かないフォルダ**：`neo4j_data/`・`neo4j_backup/`・`neo4j_livelihood_*`・`.quarantine/`。`neo4j_plugins` は扱わない
- `Read(**/.env)`・`Read(**/.env.*)` の deny を外さない。`.env.example` も読まない。`mcp__neo4j__*` の道具は使わない
- tsunagu-net のポート（17474・17687・27474・27687、試しの 47xxx・48xxx）を使わない。nest-support の新しい DB は 37xxx・38xxx。27687 には一切つながない（G-50）
- 開発と試験は架空の事例だけ。実案件のデータをリポジトリに入れない。パスワードはリポジトリにもチャットにも書かない
- 条番号は e-Gov で照合してから書く。照合できないものは【未照合】
- rtk の hook が Bash の出力を切り詰める。長い出力・JSON・日本語を含む処理は Python のスクリプトにして流す
- 前の構成のまま残るコード（G-49。新しい DB を指さないことを `tests/test_old_db_code_isolated.py` で固定）：`lib/`（field-ui は `lib/genai.py` の文字起こしだけを使う）・`scripts/rotate_password.py`・`scripts/multi_importer.py`・`setup.sh`・`setup.ps1`・`installer/*`（外した文書へのリンクが残る。G-71）。sos と field-ui は N-36・N-37 で置き換えた
- field-ui を動かすには職員のトークンの表 `~/.config/nest/field-ui-staff.json` が要る（`uv run python scripts/staff_token.py add STF-…`。トークンは一度だけ出る。河原さんが作る。まだ作っていない）
- DB つきの試験は、包みを使う試験（sos・field-ui）だけ試験の中で架空の印 NestLiveProbe を置いて消す（G-51 と同じ）
- 既定の引数に `run` を書くと試験で差し替えられない（G-77 (i)）。外の命令を呼ぶ部品は、呼ぶ時に引く
- 試験の数の目安：DB なし 889 passed・122 skipped、DB つき 1011 passed（2026-11-06 11:42）
- 段階 E の止まる点は E-1（N-27 の後）・E-2（N-28 の後）・E-3（N-30 の後）。計画の表にある
- 読み取りの包みは、実名・住所などの項目の名前を部分の一致で拒否する。正典の `ADDRESSES` も拒否される（台帳 G-64。決まるまでスキルで使わない）

## 次タスク（優先度順）

- A：止まる点 F-2（河原さんが sos・field-ui の画面と送る中身を見る。G-75〜G-77 の承認）
- B：F-2 の後に N-38（新しい Mac での入れ方）→ 止まる点 F-3
- C：未照合（手帳・年金・手当の条番号）は N-27 の SEMANTICS の行の「照合して書く」のまま。急がない
