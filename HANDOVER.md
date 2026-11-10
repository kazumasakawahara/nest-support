# HANDOVER — 2026-11-10 stage-l（ADR-001・ADR-002 の作り直し。段階 J は main に合流済み（9cb72ca。確認点 J-1 可）。確認点 L-0 は決定（80a677b）。段階 L：正典 v0.13・入口と受付の規則・書き込み受付の MCP・narrative-extractor の書き直しを stage-l に置いた）

> 前の HANDOVER（2026-08-03 main。WAM NET スキル整合）は git 履歴（ce627d9）にある。そこに書かれた
> `~/.config/nest/neo4j.env`・ポート 7687・`nest-support-neo4j` は**前の構成**で、この枝では使わない。

## 再開コマンド（2026-11-10 22:10 に確かめた）

```bash
cd ~/Dev-Work/project/nest-support && git switch stage-l
uv run pytest -q                       # 1096 passed, 146 skipped（DB を使う試験は skip）
uv run python scripts/check_drift.py   # ずれ 0 件
./scripts/doctor.sh                    # 環境の点検：31 passed, 3 warned, 0 failed（WARN は external-api の記録と設定のファイル、nest-gate.env が無いこと。nest-gate.env は手順書 4.5 (a) で作る）
```

DB を使う試験（結合試験のタスクのときだけ。終わったら必ず止める）：

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d     # nest-redesign-personal（37474/37687）・nest-redesign-resource（38474/38687）
# 試走の DB の中身（下の「前提」）を残している間は live_cleanup.py を打たない（印のほかをすべて消す）
NEST_LIVE_DB=1 uv run pytest -q                                       # 最後に流したのは 2026-11-10（stage-l。22:25 の時点で済んでいた）：1242 passed（落ち 0）
docker compose --env-file ~/.config/nest/neo4j-redesign.env down      # --remove-orphans は使わない
```

- `neo4j-redesign.env` の中身は読まない・表示しない（接続の部品 `nest/connections.py` と試験が読む）
- 起動の前に `docker ps` で前の DB が動いていないことを確かめ、起動の後に 2 つとも 127.0.0.1 だけで待ち受けていることを確かめる（N-18 の条件）
- 2026-11-10 の夜（22:25 より前）に起こし、**起こしたまま**（河原さんの指示。止めていない）

新しい Mac でゼロから入れる手順は `docs/SETUP_GUIDE.md` の「0. 新しい Mac でゼロから」（N-38）。

## 前提（実行前に現況で確かめること）

| 想定 | 確かめ方 | 最終確認日 |
|---|---|---|
| origin の枝は ba55283 まで（河原さんが push）。**判断 2・FIRST_5 の取り込み・この HANDOVER の 3 件が未 push（push が要る）**。合流は河原さんが GitHub で PR を作って行う。**合流の後は新しい枝（例：stage-i）で作業し、redesign/adr-001 には足さない** | `git status -sb`、`git log origin/main -1` | 2026-11-06 |
| **push は河原さんが打つ。** Claude は報告に「push が要る」と書くだけ。PR は作らない・main に合流させない（合流させるかは止まる点 H-1 で河原さんが決める。Mac は合流しない） | — | 2026-11-06 |
| 前の DB は河原さんが消した（N-05a。2026-11-06）：`nest-support-neo4j`・`neo4j_*`・`.quarantine/`・`~/.config/nest/neo4j-personal.env` が無い。`~/.config/nest/neo4j.env`（neo4j-agno-agent の設定）は残す | `docker ps -a`、`ls -d neo4j_* .quarantine` | 2026-11-06（河原さんの報告） |
| `support-db-neo4j`（neo4j-agno-agent の共有層 7687）は restart=no で止まっている | `docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' support-db-neo4j` → `no` | 2026-11-06 |
| `~/nest-support-hold/` は河原さんが消した（2026-11-06） | `ls -d ~/nest-support-hold` | 2026-11-06（河原さんの報告） |
| 職員のトークンの表 `~/.config/nest/field-ui-staff.json`（600）から、架空の職員 `STF-0000FAKESTAFF0000000000001` は消した（N-46 #3）。今の管理者は「事務局」STF-01M6XBX18S58S4CD90W71YTH6C、職員は「相談支援専門員A」STF-01M6XC4Y216FH8S736MS5S2CNV | `uv run python scripts/staff_token.py list` | 2026-11-10（河原さんの報告） |
| 11-06 の入力 UI のたたき台（未 commit だったもの）は `docs/archive/2026-11-06-input-ui-decisions.md` へ移した（85e5237。ADR-002 で画面を不採用にした経緯を頭に記す） | `git log --oneline -1 -- docs/archive/2026-11-06-input-ui-decisions.md` | 2026-11-10 |
| 試走の DB（個人の側）の中身：はると（C-N5AE5P）、承認 1・差し戻し 2、Pending（試走の案と、DB つきの試験が足した案）、DB つきの試験が足した架空の本人、架空の印（NestLiveProbe）1 個。**消さない**（live_mark・live_cleanup を打たない） | `uv run python scripts/review_proposals.py list`、`uv run python scripts/backup.py count`（DB を起こして） | 2026-11-10 |
| バックアップの世代は `~/nest-backup/20261110-121315` の 1 つ（段 8 の廃棄の後に取り、prune で前の世代を消した） | `uv run python scripts/backup.py list` | 2026-11-10 |
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
  - [x] main への合流（河原さん。merge commit e62f214。redesign/adr-001 は残してある）
  - [x] 段階 I の N-43（`scripts/new_staff.py`）・N-44（`scripts/review_proposals.py`）・N-45（手順書の 7 に purge_voice）。枝 `stage-i`（d458397・65d5096・e523421・a55f6eb）。台帳 G-88〜G-90
  - [x] 止まる点 I-1（2026-11-06 河原さん承認。G-88〜G-90。音声を消すのは金曜日、書き込みが無ければその週の最後に書き込んだ日）
  - [x] 段階 I の main への合流（河原さん。merge commit cb9a3f8。stage-i は残してある）
  - [x] G-91：差し戻しの理由（AuditLog の `reason`。正典 v0.12。`reject --reason`・`list --rejected`）。台帳 G-92
  - [x] **N-46 運用の試走**（2026-11-08〜11-10）：段 0〜10 を通した。詰まり 16 件、#5 のほかは直した（#5 は L-0 の提案に）。記録 `docs/journal/2026-11-08-n46-trial.md`
  - [x] **止まる点 J-1**：可（main に合流。merge commit 9cb72ca）
  - [x] **確認点 L-0**（2026-11-10 河原さん）：1-B ＋ 2-B ＋ 3-A。決めごと 13 項目（`docs/proposals/2026-11-10-L0-entrance-decisions.md` §6。台帳 G-95）
  - [x] 段階 L の最初（枝 `stage-l`。2026-11-10）：正典 SCHEMA v0.13（`SupportLog.contactKind` 6 値）・SEMANTICS SEM-REC-04（ba69fe4）、入口の点検と受付の検証の規則（9c6ae0d）、書き込み受付の MCP `nest-gate`（`nest/mcp_gate.py` の `submit_proposal`。中身は `nest/gate/proposal.py`。dac0074。台帳 G-96）、narrative-extractor を `submit_proposal` を呼ぶ形に（仮名の復唱・止まったら理由を示して作り直す）
  - [x] G-96 (f)：`desktop_config.py` の add・check に `nest-gate`、職員の ID の設定 `scripts/gate_staff.py`（set・check。`~/.config/nest/nest-gate.env`・600）、doctor の [3]・[10]、手順書 4.5 を「(a) 設定 → (b) 語りを貼る・仮名の復唱に「はい」・未確定で入る → (c) list で確かめる」に。`submit_proposal.py` は 4.5 の末尾の予備へ
  - [x] `submit_proposal` の返事に、入れた先の仮名と件数（`summary`・`code`・`pending`・`counts`）が、止まったとき（0 件）も必ず出る
  - [ ] 河原さんが Claude Desktop で 4.5 (a)〜(c) を一巡する（この Mac ではまだ `desktop_config.py add`・`gate_staff.py set` を打っていない）。一巡の後に `scripts/submit_proposal.py` を外す
  - [ ] 段階 L・M の案（K-5）は、まだ計画（`docs/implementation-plan.md`）に移していない

## グレーな判断

- **G-85 の中**：知らない呼び出し元（`caller`）は拒否する（閉じる側）。Claude の判断
- G-79・G-81〜G-85 は止まる点 H-1 で承認済み
- G-88〜G-90 は止まる点 I-1 で承認済み
- G-91 は承認済み（実装した）。G-92 は承認済み（理由は 200 字まで）

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

- A：河原さんが Claude Desktop で 4.5 (a)〜(c) を一巡する。済んだら `scripts/submit_proposal.py` と手順書の予備の小段を外す（G-94）
- B：仮名の復唱を道具の側で確かめる仕組みは L-2（引用の印）と合わせて決める
- C：段階 L・M の案（K-5）を計画に移す（L-2・L-3 の行に決めごと 7 の表示の条件を書いてある）。L-1 の残り（失効・交代・修正・食い違い。正典 v0.14 の `ChangeProposal`）
- D：残る未決は河原さんの側（G-80：Claude に実データを渡す契約の形、療育手帳の通知の照合）。tsunagu-net への提案（台帳 G-40：列挙値と、上限で切れた印）をどこから渡すかは決めていない
