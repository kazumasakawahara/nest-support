# HANDOVER — 2026-11-06 redesign/adr-001（ADR-001 の作り直し。段階 A〜D 済み、段階 E の前）

> 前の HANDOVER（2026-08-03 main。WAM NET スキル整合）は git 履歴（ce627d9）にある。そこに書かれた
> `~/.config/nest/neo4j.env`・ポート 7687・`nest-support-neo4j` は**前の構成**で、この枝では使わない。

## 再開コマンド（2026-11-06 に DB なしの 2 行を確かめた。HANDOVER を書いたのは 05:54）

```bash
cd ~/Dev-Work/project/nest-support && git switch redesign/adr-001
uv run pytest -q                       # 679 passed, 75 skipped（DB を使う試験は skip）
uv run python scripts/check_drift.py   # ずれ 0 件
```

DB を使う試験（結合試験のタスクのときだけ。終わったら必ず止める）：

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d     # nest-redesign-personal（37474/37687）・nest-redesign-resource（38474/38687）
NEST_LIVE_DB=1 uv run pytest -q                                       # 最後に流したのは 2026-11-05（DB を止めたのは 19:59）：717 passed
docker compose --env-file ~/.config/nest/neo4j-redesign.env down      # --remove-orphans は使わない
```

- `neo4j-redesign.env` の中身は読まない・表示しない（接続の部品 `nest/connections.py` と試験が読む）
- 2026-11-06 時点、nest-redesign のコンテナは無い（down 済み）。データのフォルダは残っていて、`up -d` で作り直される

## 前提（実行前に現況で確かめること）

| 想定 | 確かめ方 | 最終確認日 |
|---|---|---|
| 枝 `redesign/adr-001` は HEAD de2737b、main より 66 先、**未 push**（upstream なし） | `git rev-parse --short HEAD`・`git rev-list --count main..HEAD` | 2026-11-06 |
| 前の DB（コンテナ `nest-support-neo4j`、`neo4j_data/` ほか）は止まっている。**実データが入っているものとして扱い、開かない・起動しない・消さない** | `docker ps -a`（Exited のまま） | 2026-11-06 |
| `support-db-neo4j`（neo4j-agno-agent の共有層 7687）は restart=no で止まっている | `docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' support-db-neo4j` → `no` | 2026-11-05 |
| 資源の側の写しは `~/Dist/tsunagu-net-trial-20261104`（tsunagu-net の 2026-11-04 の一式）から読み込んだもの | `MANIFEST.json`（台帳 G-55） | 2026-11-05 |
| tsunagu-net は `~/Dev-Work/tsunagu-net`、枝 `claude/tender-dijkstra-xo3wwc`、HEAD 3bf49ca。正典 SCHEMA v0.31・SEMANTICS v0.32（BRS-49） | `git -C ~/Dev-Work/tsunagu-net log -1` | 2026-11-06 |
| 共通の約束は v1.1（tsunagu-net `docs/contracts/nest-support-shared.md`） | 同ファイルの版の行 | 2026-11-05 |
| 令和 8 年法律第 45 号（民法等の一部を改正する法律）の施行日を定める政令は、まだ出ていない | e-Gov の法令検索（tsunagu-net journal `2026-11-05-mac-voluntary-guardianship.md` の手順） | 2026-11-05 |

## 現在地

- 目標：nest-support を、ADR-001（`docs/adr/ADR-001-redesign-and-shared-contract.md`。承認 2026-11-05）と約束 v1.1 に沿って作り直す。計画は `docs/implementation-plan.md`（1 タスク＝1 行）
- 進捗：
  - [x] 段階 A（送らない・埋め込まない）：N-00〜N-05・N-05b・N-18a
  - [x] 段階 B（正典）：N-06〜N-09。正典は `docs/SCHEMA.md` **v0.8**、意味の文書は `docs/SEMANTICS.md`（SEM-AREA-01〜05・SEM-GUARD-01〜02）
  - [x] 段階 C（ゲート）：N-10〜N-17
  - [x] 段階 D（DB と書き込み・承認）：N-18〜N-24a。止まる点 4 の承認済み
  - [x] N-24b（2026-11-06）：任意後見・任意代理を tsunagu-net の BRS-49 に合わせた（0270cd3）。住所からの推定で作れる関わりを `Consultation`・`Administrative` だけにした（de2737b）。どちらも台帳 G-62
  - [ ] N-05a 前の DB の処分（河原さんが中身を確かめるまで手を付けない）
  - [ ] 段階 E：N-25〜N-30（スキルと文書。未着手）

## グレーな判断

判断の台帳 `docs/gray-decisions.md` で、**承認欄が空の行が 20 件**ある（2026-11-06 に数えた）：
G-2・G-5・G-6・G-7・G-10・G-11・G-14・G-15・G-22・G-42・G-45〜G-52・G-54・G-61。
多くは作業の中で決めた細部（置き場所・試験の形・ゲートの細かい決まり）。次のセッションの冒頭で、まとめて承認を取るか、河原さんに見ていただく順を相談する。

- G-5 は、この HANDOVER の更新で中身が古いまま、という状態が解消した（承認欄はまだ空）
- G-42・G-50 は「未決」として書かれている（下の未決論点）

## 未決論点

1. **枝を push するか**（公開のリポジトリ。河原さんが別に決める。それまで push しない）
2. **G-50**：資源の側を nest-support 専用の写し（`nest-redesign-resource`、38687）にするか、動いている tsunagu-net の資源 DB につなぐか（本番の前に決める）
3. **G-42**：N-22 の読み取りで、職員が呼ぶ名前を `displayCode` に対応づける入口（名前を入れて仮名だけを返す形／職員が仮名で呼ぶ運用）。決めたら `docs/external-api.md` の NEXT-02 も直す
4. **jp-normalize**（G-61）：今は依存にせず、自前の `_reached` と同じ答えを固定する試験で進める。共通の道具にするなら、公開のリポジトリに置いてコミットを固定する（LICENSE のファイルも要る）
5. **令和 8 年法律第 45 号の施行**：政令が出たら、後見・保佐を新しく使わないようゲートで止める（tsunagu-net の T-31a に合わせる。SEMANTICS SEM-GUARD-02）
6. **N-05a**：前の DB（`neo4j_data/`・`neo4j_backup/`・`neo4j_livelihood_*`）の処分。河原さんが確かめるまでそのまま

## 既知の罠・注意

- **開かないフォルダ**：`neo4j_data/`・`neo4j_backup/`・`neo4j_livelihood_*`・`.quarantine/`。`neo4j_plugins` は扱わない
- `Read(**/.env)`・`Read(**/.env.*)` の deny を外さない。`.env.example` も読まない。`mcp__neo4j__*` の道具は使わない
- tsunagu-net のポート（17474・17687・27474・27687、試しの 47xxx・48xxx）を使わない。nest-support の新しい DB は 37xxx・38xxx
- 開発と試験は架空の事例だけ。実案件のデータをリポジトリに入れない。パスワードはリポジトリにもチャットにも書かない
- 条番号は e-Gov で照合してから書く。照合できないものは【未照合】
- rtk の hook が Bash の出力を切り詰める。長い出力・JSON・日本語を含む処理は Python のスクリプトにして流す
- 試験の数の目安：DB なし 679 passed・75 skipped（2026-11-06）、DB つき 717 passed（2026-11-05。N-24b の 37 件が足されたので、次に流すと増える）

## 次タスク（優先度順）

- A：台帳の承認欄が空の 20 件を、河原さんに見ていただく（まとめて／順に）
- A：枝を push するかの判断を待つ（こちらからは push しない）
- B：N-25 narrative-extractor の書き直し（書き込みの案の JSON を出すだけにする。案の例がゲートを通ることを架空の例で確かめる）→ N-26 EXTRACTION_PROMPT
- B：N-24b の後に DB つきの試験を一度流す（`NEST_LIVE_DB=1`。終わったら down）
- C：N-27〜N-30（読み取りのスキル、SOS の中身、文書、`doctor.sh`）
