# HANDOVER — 2026-11-06 redesign/adr-001（ADR-001 の作り直し。段階 A〜H 済み。main への合流を待っている。以後は新しい枝で段階 I）

> 前の HANDOVER（2026-08-03 main。WAM NET スキル整合）は git 履歴（ce627d9）にある。そこに書かれた
> `~/.config/nest/neo4j.env`・ポート 7687・`nest-support-neo4j` は**前の構成**で、この枝では使わない。

## 再開コマンド（2026-11-06 15:00 に確かめた）

```bash
cd ~/Dev-Work/project/nest-support && git switch redesign/adr-001
uv run pytest -q                       # 893 passed, 134 skipped（DB を使う試験は skip）
uv run python scripts/check_drift.py   # ずれ 0 件
./scripts/doctor.sh                    # 環境の点検：29 passed, 2 warned, 0 failed（WARN は external-api の記録と設定のファイルが無いこと）
```

DB を使う試験（結合試験のタスクのときだけ。終わったら必ず止める）：

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d     # nest-redesign-personal（37474/37687）・nest-redesign-resource（38474/38687）
uv run python tests/live_cleanup.py                                  # 試験の DB を片づける（架空の印のある DB でだけ動く。印は試験が一時に置くので、手で流すときは一時の印を置いてから）
NEST_LIVE_DB=1 uv run pytest -q                                       # 最後に流したのは 2026-11-06 15:09（片づけの道具の後）：1027 passed（落ち 0・skip 0）
docker compose --env-file ~/.config/nest/neo4j-redesign.env down      # --remove-orphans は使わない
```

- `neo4j-redesign.env` の中身は読まない・表示しない（接続の部品 `nest/connections.py` と試験が読む）
- 起動の前に `docker ps` で前の DB が動いていないことを確かめ、起動の後に 2 つとも 127.0.0.1 だけで待ち受けていることを確かめる（N-18 の条件）
- 2026-11-06 15:10 に down 済み（`docker ps` に nest の名前が無いことを確かめた）

新しい Mac でゼロから入れる手順は `docs/SETUP_GUIDE.md` の「0. 新しい Mac でゼロから」（N-38）。

## 前提（実行前に現況で確かめること）

| 想定 | 確かめ方 | 最終確認日 |
|---|---|---|
| origin の枝は ba55283 まで（河原さんが push）。**判断 2・FIRST_5 の取り込み・この HANDOVER の 3 件が未 push（push が要る）**。合流は河原さんが GitHub で PR を作って行う。**合流の後は新しい枝（例：stage-i）で作業し、redesign/adr-001 には足さない** | `git status -sb`、`git log origin/main -1` | 2026-11-06 |
| **push は河原さんが打つ。** Claude は報告に「push が要る」と書くだけ。PR は作らない・main に合流させない（合流させるかは止まる点 H-1 で河原さんが決める。Mac は合流しない） | — | 2026-11-06 |
| 前の DB は河原さんが消した（N-05a。2026-11-06）：`nest-support-neo4j`・`neo4j_*`・`.quarantine/`・`~/.config/nest/neo4j-personal.env` が無い。`~/.config/nest/neo4j.env`（neo4j-agno-agent の設定）は残す | `docker ps -a`、`ls -d neo4j_* .quarantine` | 2026-11-06（河原さんの報告） |
| `support-db-neo4j`（neo4j-agno-agent の共有層 7687）は restart=no で止まっている | `docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' support-db-neo4j` → `no` | 2026-11-06 |
| `~/nest-support-hold/` は河原さんが消した（2026-11-06） | `ls -d ~/nest-support-hold` | 2026-11-06（河原さんの報告） |
| 職員のトークンの表 `~/.config/nest/field-ui-staff.json`（600）に、架空の職員 `STF-0000FAKESTAFF0000000000001` が一人いる（F-2 の画面の撮影で作った。DB の個人の側にも同じ職員がいる） | `uv run python scripts/staff_token.py list` | 2026-11-06 |
| 資源の側の写しは `~/Dist/tsunagu-net-trial-20261104`（tsunagu-net の 2026-11-04 の一式）から読み込んだもの | `MANIFEST.json`（台帳 G-55） | 2026-11-05 |
| tsunagu-net は `~/Dev-Work/tsunagu-net`、HEAD 3bf49ca。正典 SCHEMA v0.31・SEMANTICS v0.32（BRS-49）。**変えない** | `git -C ~/Dev-Work/tsunagu-net log -1` | 2026-11-06 |
| 共通の約束は v1.1（tsunagu-net `docs/contracts/nest-support-shared.md`） | 同ファイルの版の行 | 2026-11-05 |
| 令和 8 年法律第 45 号（民法等の一部を改正する法律）の施行日を定める政令は、まだ出ていない | e-Gov の法令検索 | 2026-11-05 |

## 現在地

- 目標：nest-support を、ADR-001（`docs/adr/ADR-001-redesign-and-shared-contract.md`）と約束 v1.1 に沿って作り直す。計画は `docs/implementation-plan.md`（1 タスク＝1 行）
- 進捗：
  - [x] 段階 A〜G（N-00〜N-39、止まる点 4・E-1〜E-3・F-1〜F-3・G-1）。N-05a（前の DB の処分）は河原さんが打った
  - [x] 段階 H（N-40〜N-42、止まる点 H-1。2026-11-06 河原さん承認）
  - [x] H-1 の判断 2：画面（field-ui・SOS）には NEXT-02 の歯止めを当てない。包みに呼び出し元（`caller="mcp"`／`"screen"`）を持たせた（台帳 G-85）
  - [x] `docs/FIRST_5_OPERATIONS.md` を `docs/OPERATIONS.md` の「0. 最初の 5 つの操作」に取り込んで外した
  - [ ] **main への合流**：河原さんが GitHub で PR を作る（Mac は合流しない）
  - [ ] **段階 I**（合流の後、新しい枝で。計画にはその枝で書く）：N-43 職員の登録の道具 `scripts/new_staff.py`、N-44 案の点検と承認の道具 `scripts/review_proposals.py`（一つずつ。自己承認は `selfApproval`）、N-45 音声を消す日はバックアップと同じ日（週に一度）・DB を起動してから流して終わったら止める、止まる点 I-1（道具 2 本を架空のデータで動かした結果）。N-43・N-44 の試験は手順書に書いたコマンドをそのまま流す形にする

## グレーな判断

- **G-85 の中**：知らない呼び出し元（`caller`）は拒否する（閉じる側）。Claude の判断
- G-79・G-81〜G-84 は止まる点 H-1 で承認済み

## 未決論点

1. **G-80**：実データを Claude に渡す経路を事業者向けの契約（API か Team/Enterprise）にするか【未決】
2. **令和 8 年法律第 45 号の施行**：政令が出たら、後見・保佐を新しく使わないようゲートで止める（SEMANTICS SEM-GUARD-02）
3. **SOS のポート**：この Mac では 8000 を open-notebook が使っているので 8010 にする（`docs/OPERATIONS.md` の 5 の段に書いた）
4. **ダッシュボード**：正典の SupportLog に感情・きっかけの項目を足すか（今は閉じている）

## 既知の罠・注意

- **開かないフォルダ**：`neo4j_data/`・`neo4j_backup/`・`neo4j_livelihood_*`・`.quarantine/`。`neo4j_plugins` は扱わない
- `Read(**/.env)`・`Read(**/.env.*)` の deny を外さない。`.env.example` も読まない。`mcp__neo4j__*` の道具は使わない
- tsunagu-net のポート（17474・17687・27474・27687、試しの 47xxx・48xxx）を使わない。nest-support の新しい DB は 37xxx・38xxx。27687 には一切つながない（G-50）
- 開発と試験は架空の事例だけ。実案件のデータをリポジトリに入れない。パスワード・トークンはリポジトリにもチャットにも書かない
- 条番号は e-Gov で照合してから書く。照合できないものは【未照合】
- rtk の hook が Bash の出力を切り詰める。長い出力・JSON・日本語を含む処理は Python のスクリプトにして流す
- sos の既定のポート 8000 は、この Mac では open-notebook が使っている。手元で起動するときは `PORT=8010` などにする
- DB つきの試験は、包みを使う試験（sos・field-ui）だけ試験の中で架空の印 NestLiveProbe を置いて消す（G-51 と同じ）
- 既定の引数に `run` を書くと試験で差し替えられない（G-77 (i)）。外の命令を呼ぶ部品は、呼ぶ時に引く
- git の hook：main への commit は止められる（枝を作ってから）。`~/nest-support-hold` の `rm -r` も止められる
- 読み取りの包みは、実名・住所などの項目の名前を部分の一致で拒否する。正典の `ADDRESSES` も拒否される（台帳 G-64）

## 次タスク（優先度順）

- A：河原さんが push し、GitHub で PR を作って main に合流する
- B：新しい枝で段階 I（N-43〜N-45、止まる点 I-1）。最初に計画へ段階 I を書く
- C：療育手帳の通知の名前と年は河原さんが確かめる。tsunagu-net への提案（台帳 G-40：列挙値と、上限で切れた印）をどこから渡すかは決めていない
