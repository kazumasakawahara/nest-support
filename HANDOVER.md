# HANDOVER — 2026-11-06 redesign/adr-001（ADR-001 の作り直し。段階 A〜F 済み。止まる点 F-3 で止まっている）

> 前の HANDOVER（2026-08-03 main。WAM NET スキル整合）は git 履歴（ce627d9）にある。そこに書かれた
> `~/.config/nest/neo4j.env`・ポート 7687・`nest-support-neo4j` は**前の構成**で、この枝では使わない。

## 再開コマンド（2026-11-06 12:30 に確かめた）

```bash
cd ~/Dev-Work/project/nest-support && git switch redesign/adr-001
uv run pytest -q                       # 831 passed, 123 skipped（DB を使う試験は skip。N-38 で前の構成だけの試験 10 本を外した）
uv run python scripts/check_drift.py   # ずれ 0 件
./scripts/doctor.sh                    # 環境の点検：31 passed, 0 failed
```

DB を使う試験（結合試験のタスクのときだけ。終わったら必ず止める）：

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d     # nest-redesign-personal（37474/37687）・nest-redesign-resource（38474/38687）
NEST_LIVE_DB=1 uv run pytest -q                                       # 最後に流したのは G-77 の直しの後：1016 passed（N-38 の後は流していない）
docker compose --env-file ~/.config/nest/neo4j-redesign.env down      # --remove-orphans は使わない
```

- `neo4j-redesign.env` の中身は読まない・表示しない（接続の部品 `nest/connections.py` と試験が読む）
- 起動の前に `docker ps` で前の DB が動いていないことを確かめ、起動の後に 2 つとも 127.0.0.1 だけで待ち受けていることを確かめる（N-18 の条件）
- 2026-11-06 12:03（画面の撮影の後）に down 済み。12:30 に二つとも止まっていることを `docker ps -a` で確かめた

新しい Mac でゼロから入れる手順は `docs/SETUP_GUIDE.md` の「0. 新しい Mac でゼロから」（N-38）。

## 前提（実行前に現況で確かめること）

| 想定 | 確かめ方 | 最終確認日 |
|---|---|---|
| origin の枝は 6e6ab61（F-2 の HANDOVER）まで。**3a9b895・9ee8ca5・c240542・7171c46・de22197・52e2253 とこの HANDOVER の直し（計 7 件）が未 push（push が要る）** | `git status -sb`（`ahead N` が未 push の数） | 2026-11-06 |
| **push は河原さんが打つ。** Claude は報告に「push が要る」と書くだけ。PR は作らない・main に合流させない | — | 2026-11-06 |
| neo4j-agno-agent（`~/Dev-Work/neo4j-agno-agent`）の main に README の注記 992f3f3 をコミットした。未 push（ahead 1）。`WAM-NET/MAC_TASKS.md` の変更と `.env.txt` は Claude のものではなく、触れていない | `git -C ~/Dev-Work/neo4j-agno-agent status -sb` | 2026-11-06 |
| 前の DB（コンテナ `nest-support-neo4j`、`neo4j_data/` ほか）は止まっている。**実データが入っているものとして扱い、開かない・起動しない・消さない**（消すのは河原さん。N-05a） | `docker ps -a`（Exited のまま） | 2026-11-06 |
| `support-db-neo4j`（neo4j-agno-agent の共有層 7687）は restart=no で止まっている | `docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' support-db-neo4j` → `no` | 2026-11-06 |
| `~/nest-support-hold/`（未コミットの写し 20 件・.bak）は 700・Time Machine の対象外のまま。F-3 で前の DB の処分と一緒に決める | `stat -f '%Sp' ~/nest-support-hold` | 2026-11-06（河原さんの報告） |
| 職員のトークンの表 `~/.config/nest/field-ui-staff.json`（600）に、架空の職員 `STF-0000FAKESTAFF0000000000001` が一人いる（F-2 の画面の撮影で作った。DB の個人の側にも同じ職員がいる） | `uv run python scripts/staff_token.py list` | 2026-11-06 |
| 資源の側の写しは `~/Dist/tsunagu-net-trial-20261104`（tsunagu-net の 2026-11-04 の一式）から読み込んだもの | `MANIFEST.json`（台帳 G-55） | 2026-11-05 |
| tsunagu-net は `~/Dev-Work/tsunagu-net`、HEAD 3bf49ca。正典 SCHEMA v0.31・SEMANTICS v0.32（BRS-49）。**変えない** | `git -C ~/Dev-Work/tsunagu-net log -1` | 2026-11-06 |
| 共通の約束は v1.1（tsunagu-net `docs/contracts/nest-support-shared.md`） | 同ファイルの版の行 | 2026-11-05 |
| 令和 8 年法律第 45 号（民法等の一部を改正する法律）の施行日を定める政令は、まだ出ていない | e-Gov の法令検索 | 2026-11-05 |

## 現在地

- 目標：nest-support を、ADR-001（`docs/adr/ADR-001-redesign-and-shared-contract.md`）と約束 v1.1 に沿って作り直す。計画は `docs/implementation-plan.md`（1 タスク＝1 行）
- 進捗：
  - [x] 段階 A〜E（N-00〜N-30、止まる点 4・E-1〜E-3）。経緯は git 履歴の前の HANDOVER（6e6ab61）と計画の表
  - [x] 段階 F：N-34 → F-1（G-74）→ N-32 廃棄・N-33 バックアップ → N-35 → N-36 sos・N-37 field-ui → F-2（承認 2026-11-06）
  - [x] F-2 の後：G-75 を external-api §2 の NEXT-12 に（9ee8ca5）。G-77 の直し：本人の廃棄で、その本人の記録の音声も同じ操作で消す・doctor.sh に「30 日を過ぎた音声」の FAIL（c240542）
  - [x] N-38：`lib/genai.py` → `nest/genai.py`（7171c46）、前の構成を外した（de22197。台帳 G-78）、新しい Mac の手順・`scripts/bootstrap_admin.py`・doctor.sh [3] の設定のファイル（52e2253）
  - [ ] **止まる点 F-3**：段階 F の「外したもの・残したもの」と N-05a の処分の手順を河原さんに見ていただく。G-78 の承認
  - [ ] N-05a 前の DB の処分：移さない（決定）。消すのは河原さんが「実データの原本が別にある」と確かめてから、河原さんが打つ（手順は計画の N-05a の行）

## グレーな判断

F-3 で見ていただく、Claude が決めたこと（台帳 `docs/gray-decisions.md`）：

- **G-78**（N-38）：消したコードだけを試していた試験 10 本を消した。依存 4 つ（pykakasi・python-docx・openpyxl・pdfplumber）を外した。OCR（`ocr_with_gemini`、NEXT-04）は呼ぶところが無くなったが関数は残した。doctor.sh [3] は設定のファイルが無ければ INFO
- **G-77 の直し**：doctor.sh の「30 日を過ぎた音声」は FAIL にした（知らせるだけにしなかった）。音声を先に消し、そのあと DB を消す（F-3 で河原さんが順を決めた）。音声の件数は Purge の監査ログに入れない

## 未決論点

1. **令和 8 年法律第 45 号の施行**：政令が出たら、後見・保佐を新しく使わないようゲートで止める（tsunagu-net の T-31a に合わせる。SEMANTICS SEM-GUARD-02）
2. **N-05a**：前の DB の跡と `~/nest-support-hold/` は、河原さんが原本を確かめてから河原さんが消す。それまでそのまま
3. **本人を作る入口（Claude の外）がまだ無い**。架空の本人は試験と撮影の中でゲートに直に渡して作っている。実データを入れる前に要る
4. **OCR（NEXT-04）**：呼ぶところが無い。関数ごと外すか、手書きの記録の入口を作り直すか
5. **ダッシュボード**：正典の SupportLog に感情・きっかけの項目を足すか（今は閉じている）
6. **G-42 (2)**：職員を仮名で呼ぶ運用が使いにくければ、実データを入れる前にもう一度決める

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

- A：止まる点 F-3（河原さんが「外したもの・残したもの」と N-05a の手順を見る。G-78 の承認。push）
- B：N-05a の処分（河原さんが打つ）。そのあと段階 G（本人を作る入口・OCR・ダッシュボードなど、未決論点 3〜5）を計画に書くかを決める
- C：N-38 の後の DB つき試験を一度流す（N-38 はコードの読み込みを変えたが、DB つきの試験の範囲には触れていない）。未照合の条番号は急がない
