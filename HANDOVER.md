# HANDOVER — 2026-11-06 redesign/adr-001（ADR-001 の作り直し。段階 A〜G 済み。段階 H の N-40〜N-42 まで済み。止まる点 H-1 で止まっている）

> 前の HANDOVER（2026-08-03 main。WAM NET スキル整合）は git 履歴（ce627d9）にある。そこに書かれた
> `~/.config/nest/neo4j.env`・ポート 7687・`nest-support-neo4j` は**前の構成**で、この枝では使わない。

## 再開コマンド（2026-11-06 14:30 に確かめた）

```bash
cd ~/Dev-Work/project/nest-support && git switch redesign/adr-001
uv run pytest -q                       # 865 passed, 129 skipped（DB を使う試験は skip）
uv run python scripts/check_drift.py   # ずれ 0 件
./scripts/doctor.sh                    # 環境の点検：29 passed, 2 warned, 0 failed（WARN は external-api の記録と設定のファイルが無いこと）
```

DB を使う試験（結合試験のタスクのときだけ。終わったら必ず止める）：

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d     # nest-redesign-personal（37474/37687）・nest-redesign-resource（38474/38687）
NEST_LIVE_DB=1 uv run pytest -q                                       # 最後に流したのは 2026-11-06 12:44（N-39 の後）：970 passed
docker compose --env-file ~/.config/nest/neo4j-redesign.env down      # --remove-orphans は使わない
```

- `neo4j-redesign.env` の中身は読まない・表示しない（接続の部品 `nest/connections.py` と試験が読む）
- 起動の前に `docker ps` で前の DB が動いていないことを確かめ、起動の後に 2 つとも 127.0.0.1 だけで待ち受けていることを確かめる（N-18 の条件）
- 2026-11-06 12:45 に down 済み（二つとも止まっていることを `docker ps` で確かめた）

新しい Mac でゼロから入れる手順は `docs/SETUP_GUIDE.md` の「0. 新しい Mac でゼロから」（N-38）。

## 前提（実行前に現況で確かめること）

| 想定 | 確かめ方 | 最終確認日 |
|---|---|---|
| origin の枝は 120125b（G-80）まで（河原さんが push）。**244565d・6a8ba45・aa9d5a3・a3a8fd3 とこの HANDOVER の直しが未 push（push が要る）** | `git status -sb`（`ahead N` が未 push の数） | 2026-11-06 |
| **push は河原さんが打つ。** Claude は報告に「push が要る」と書くだけ。PR は作らない・main に合流させない（合流させるかは止まる点 H-1 で河原さんが決める。Mac は合流しない） | — | 2026-11-06 |
| 前の DB は河原さんが消した（N-05a。2026-11-06）：`nest-support-neo4j`・`neo4j_*`・`.quarantine/`・`~/.config/nest/neo4j-personal.env` が無い。`~/.config/nest/neo4j.env`（neo4j-agno-agent の設定）は残す | `docker ps -a`、`ls -d neo4j_* .quarantine` | 2026-11-06（河原さんの報告） |
| `support-db-neo4j`（neo4j-agno-agent の共有層 7687）は restart=no で止まっている | `docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' support-db-neo4j` → `no` | 2026-11-06 |
| 写し 3 件は `docs/archive/` にコミットした（c5813e6）。`~/nest-support-hold/2026-11-05-uncommitted/` の残り 17 件と `.DS_Store` は河原さんが消す。N-09 の `.bak` の置き場所（`2026-11-05-n09-bak/`）は 2026-11-06 に見たとき無かった | `find ~/nest-support-hold -type f` | 2026-11-06 |
| 職員のトークンの表 `~/.config/nest/field-ui-staff.json`（600）に、架空の職員 `STF-0000FAKESTAFF0000000000001` が一人いる（F-2 の画面の撮影で作った。DB の個人の側にも同じ職員がいる） | `uv run python scripts/staff_token.py list` | 2026-11-06 |
| 資源の側の写しは `~/Dist/tsunagu-net-trial-20261104`（tsunagu-net の 2026-11-04 の一式）から読み込んだもの | `MANIFEST.json`（台帳 G-55） | 2026-11-05 |
| tsunagu-net は `~/Dev-Work/tsunagu-net`、HEAD 3bf49ca。正典 SCHEMA v0.31・SEMANTICS v0.32（BRS-49）。**変えない** | `git -C ~/Dev-Work/tsunagu-net log -1` | 2026-11-06 |
| 共通の約束は v1.1（tsunagu-net `docs/contracts/nest-support-shared.md`） | 同ファイルの版の行 | 2026-11-05 |
| 令和 8 年法律第 45 号（民法等の一部を改正する法律）の施行日を定める政令は、まだ出ていない | e-Gov の法令検索 | 2026-11-05 |

## 現在地

- 目標：nest-support を、ADR-001（`docs/adr/ADR-001-redesign-and-shared-contract.md`）と約束 v1.1 に沿って作り直す。計画は `docs/implementation-plan.md`（1 タスク＝1 行）
- 進捗：
  - [x] 段階 A〜F（N-00〜N-38、止まる点 4・E-1〜E-3・F-1〜F-3）。経緯は git 履歴の前の HANDOVER と計画の表
  - [x] 段階 G（N-39、止まる点 G-1。2026-11-06 河原さん）：写し 3 件を `docs/archive/` に（c5813e6）。契約の確認の記録はまだ作らない（台帳 G-80。external-api v0.11。120125b）
  - [x] N-05a：前の DB の処分（河原さんが打った。計画の行に結果と残りを書いた。244565d）
  - [x] N-40：運用の手順書 `docs/OPERATIONS.md`（6a8ba45。台帳 G-81）
  - [x] N-41：契約の確認の記録と機能の設定の作り方 `docs/EXTERNAL_API_SETUP.md`（aa9d5a3。台帳 G-82）
  - [x] N-42：SEMANTICS SEM-ENUM-03 の条番号（a3a8fd3。台帳 G-83。療育手帳だけ【未照合】のまま理由を書いた）
  - [ ] **止まる点 H-1**：河原さんが N-40・N-41 の手順書を読む。`redesign/adr-001` を main に合流させるかを河原さんが決める（Mac は合流しない）

## グレーな判断

H-1 で見ていただく、Claude が決めたこと（台帳 `docs/gray-decisions.md`）：

- **G-81**（N-40）：doctor に項目を足さず、点検できない段は「人が確かめる」と書いた。field-ui と SOS が実データの DB を読まないことを見つけ、コードは変えず手順書に書いた。手元で打つ道具の無い段（二人目からの職員の登録、案の点検と承認）を書いた。音声を消す日は Claude の案と分けた
- **G-82**（N-41）：例は NEXT-03。文字の項目は〈…〉、日付は書きかけで、写しただけでは通らない
- **G-83**（N-42）：根拠は別の節 SEM-ENUM-03。生活保護は第 1 条。療育手帳は【未照合】（通知の名前と年は照合していない）
- **G-79**（N-39）の承認の欄は、まだ空いている

## 未決論点

1. **field-ui と SOS が実データの DB を読む条件**（N-40 で見つけた）：二つとも Claude と同じ包みの歯止め（`require_personal_allowed`：NEXT-02 か架空の印 `NestLiveProbe`）を通る。G-80 のままだと、実データの DB では画面に本人の一覧が出ず、SOS も読めない。画面は Claude に送らないので、この歯止めを画面に当てるかを決め直す
2. **G-80**：実データを Claude に渡す経路を事業者向けの契約（API か Team/Enterprise）にするか【未決】
3. **令和 8 年法律第 45 号の施行**：政令が出たら、後見・保佐を新しく使わないようゲートで止める（tsunagu-net の T-31a に合わせる。SEMANTICS SEM-GUARD-02）
4. **手元で打つ道具が無い段**：二人目からの職員の登録、書き込みの案の点検と承認（`docs/OPERATIONS.md` の末尾）
5. **音声を消す日**：決めていない
6. **ダッシュボード**：正典の SupportLog に感情・きっかけの項目を足すか（今は閉じている）

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

- A：止まる点 H-1（河原さんが手順書を読む。main に合流させるかを決める。G-79・G-81〜G-83 の承認。未決 1 の決め直し。push）
- B：`docs/FIRST_5_OPERATIONS.md` は前の構成の書き方（Claude に名前で登録する）のまま。直すか外すかは別に決める（Claude は触っていない）
- C：未照合の条番号は急がない
