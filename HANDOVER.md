# HANDOVER — 2026-11-06 redesign/adr-001（ADR-001 の作り直し。段階 A〜F 済み。段階 G の N-39 まで済み。止まる点 G-1 で止まっている）

> 前の HANDOVER（2026-08-03 main。WAM NET スキル整合）は git 履歴（ce627d9）にある。そこに書かれた
> `~/.config/nest/neo4j.env`・ポート 7687・`nest-support-neo4j` は**前の構成**で、この枝では使わない。

## 再開コマンド（2026-11-06 12:45 に確かめた）

```bash
cd ~/Dev-Work/project/nest-support && git switch redesign/adr-001
uv run pytest -q                       # 841 passed, 129 skipped（DB を使う試験は skip）
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
| origin の枝は 61a9963（F-3 の HANDOVER）まで（河原さんが push）。**9f65bf1・ce0a6cf・9de8587・8176555 とこの HANDOVER の直しが未 push（push が要る）** | `git status -sb`（`ahead N` が未 push の数） | 2026-11-06 |
| **push は河原さんが打つ。** Claude は報告に「push が要る」と書くだけ。PR は作らない・main に合流させない | — | 2026-11-06 |
| 前の DB（コンテナ `nest-support-neo4j`、`neo4j_data/` ほか）は止まっている。**実データが入っているものとして扱い、開かない・起動しない・消さない**（消すのは河原さん。N-05a） | `docker ps -a`（Exited のまま） | 2026-11-06 |
| `support-db-neo4j`（neo4j-agno-agent の共有層 7687）は restart=no で止まっている | `docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' support-db-neo4j` → `no` | 2026-11-06 |
| `~/nest-support-hold/`（未コミットの写し 20 件・.bak）は 700・Time Machine の対象外のまま。F-3 で決めた：`COMPLETE_MANUAL.md`・`COMPLETE_MANUAL.html`・`家族聴き取りマニュアル.docx` は河原さんが実名の無いことを確かめたうえで `docs/archive/` にコミットする（Mac が git add する。docx は読まない）。残りの 17 件と .bak は、その後に河原さんが消す | `stat -f '%Sp' ~/nest-support-hold` | 2026-11-06（河原さんの報告） |
| 職員のトークンの表 `~/.config/nest/field-ui-staff.json`（600）に、架空の職員 `STF-0000FAKESTAFF0000000000001` が一人いる（F-2 の画面の撮影で作った。DB の個人の側にも同じ職員がいる） | `uv run python scripts/staff_token.py list` | 2026-11-06 |
| 資源の側の写しは `~/Dist/tsunagu-net-trial-20261104`（tsunagu-net の 2026-11-04 の一式）から読み込んだもの | `MANIFEST.json`（台帳 G-55） | 2026-11-05 |
| tsunagu-net は `~/Dev-Work/tsunagu-net`、HEAD 3bf49ca。正典 SCHEMA v0.31・SEMANTICS v0.32（BRS-49）。**変えない** | `git -C ~/Dev-Work/tsunagu-net log -1` | 2026-11-06 |
| 共通の約束は v1.1（tsunagu-net `docs/contracts/nest-support-shared.md`） | 同ファイルの版の行 | 2026-11-05 |
| 令和 8 年法律第 45 号（民法等の一部を改正する法律）の施行日を定める政令は、まだ出ていない | e-Gov の法令検索 | 2026-11-05 |

## 現在地

- 目標：nest-support を、ADR-001（`docs/adr/ADR-001-redesign-and-shared-contract.md`）と約束 v1.1 に沿って作り直す。計画は `docs/implementation-plan.md`（1 タスク＝1 行）
- 進捗：
  - [x] 段階 A〜E（N-00〜N-30、止まる点 4・E-1〜E-3）。経緯は git 履歴の前の HANDOVER（6e6ab61）と計画の表
  - [x] 段階 F（N-32〜N-38、止まる点 F-1〜F-3。F-3 の承認 2026-11-06）
  - [x] F-3 の直し：本人の廃棄は音声を先に消し、そのあと DB を消す（9f65bf1）。doctor の WARN の段・external-api v0.10 の NEXT-04（ce0a6cf）。計画に段階 G（9de8587）
  - [x] 段階 G の最初の DB つきの試験：958 passed（N-38 の後）
  - [x] N-39：本人を Claude の外で作る入口 `scripts/new_client.py`（add・find。8176555。台帳 G-79）
  - [ ] **止まる点 G-1**：実データを入れる前の最後の確認（契約の確認の記録・機能の設定・NEXT-02 の歯止め・doctor の FAIL 0）
  - [ ] `docs/archive/` に写し 3 件をコミットする（河原さんが実名の無いことを確かめてから）
  - [ ] N-05a 前の DB の処分：河原さんが打つ（手順は計画の N-05a の行。`neo4j_plugins/` も消す）

## グレーな判断

G-1 で見ていただく、Claude が決めたこと（台帳 `docs/gray-decisions.md`）：

- **G-79**（N-39）：二重登録は「同じ氏・名で、生年月日が同じか、どちらかに無い」とき止める（かなは見ない。それでも作る指定は付けない）。住まいの確度は Confirmed。find は仮名だけを出す。出力を Claude に貼らないことは文で知らせるだけ
- **G-77 の直しの中**：音声を一つでも消せなければ DB は消さず、理由を出して止める

## 未決論点

1. **令和 8 年法律第 45 号の施行**：政令が出たら、後見・保佐を新しく使わないようゲートで止める（tsunagu-net の T-31a に合わせる。SEMANTICS SEM-GUARD-02）
2. **N-05a**：前の DB の跡は、河原さんが原本を確かめてから河原さんが消す
3. **G-1 の確認の材料**：`~/.config/nest/external-api-record.json`（契約の確認の記録）と `external-api-features.json`（機能の設定）がまだ無い。今は NEXT-01〜05 がすべて止まる（`egress.authorize` で確かめた）。個人の側の MCP は架空の印のある DB でしか動かない
4. **ダッシュボード**：正典の SupportLog に感情・きっかけの項目を足すか（今は閉じている）
5. **G-42 (2)**：職員を仮名で呼ぶ運用が使いにくければ、実データを入れる前にもう一度決める（N-39 で名前から仮名を引く入口はできた）

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

- A：止まる点 G-1（河原さんが、実データを入れる前の確認をする。G-79 の承認。push）
- B：`docs/archive/` の写し 3 件（河原さんの確認の後）。N-05a の処分（河原さんが打つ）
- C：未照合の条番号は急がない
