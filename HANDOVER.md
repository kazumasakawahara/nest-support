# HANDOVER — 2026-11-06 redesign/adr-001（ADR-001 の作り直し。段階 A〜D 済み、段階 E の途中。止まる点 E-3 で止まっている）

> 前の HANDOVER（2026-08-03 main。WAM NET スキル整合）は git 履歴（ce627d9）にある。そこに書かれた
> `~/.config/nest/neo4j.env`・ポート 7687・`nest-support-neo4j` は**前の構成**で、この枝では使わない。

## 再開コマンド（2026-11-06 07:44、止まる点 E-3 で確かめた）

```bash
cd ~/Dev-Work/project/nest-support && git switch redesign/adr-001
uv run pytest -q                       # 788 passed, 111 skipped（DB を使う試験は skip）
uv run python scripts/check_drift.py   # ずれ 0 件
./scripts/doctor.sh                    # 環境の点検（今は wamnet-provider-sync のリンクの残りで 1 件 FAIL）
```

DB を使う試験（結合試験のタスクのときだけ。終わったら必ず止める）：

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d     # nest-redesign-personal（37474/37687）・nest-redesign-resource（38474/38687）
NEST_LIVE_DB=1 uv run pytest -q                                       # 最後に流したのは 2026-11-06（止まる点 E-2。DB を止めたのは 07:13）：882 passed
docker compose --env-file ~/.config/nest/neo4j-redesign.env down      # --remove-orphans は使わない
```

- `neo4j-redesign.env` の中身は読まない・表示しない（接続の部品 `nest/connections.py` と試験が読む）
- 起動の前に `docker ps` で前の DB が動いていないことを確かめ、起動の後に 2 つとも 127.0.0.1 だけで待ち受けていることを確かめる（N-18 の条件）
- 2026-11-06 07:13 に down 済み。データのフォルダは残っていて、`up -d` で作り直される

## 前提（実行前に現況で確かめること）

| 想定 | 確かめ方 | 最終確認日 |
|---|---|---|
| 枝 `redesign/adr-001` は origin に push 済み（河原さんが 2026-11-06 に打った。`origin/redesign/adr-001` = 34f2577）。その後、河原さんが b0b2177 まで push。河原さんが 960e8d9 まで push。**056d02e からこの HANDOVER の直しまでの 5 件が未 push（push が要る）** | `git status -sb`（`ahead N` が未 push の数） | 2026-11-06 |
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
  - [ ] **止まる点 E-3**（段階 E の外したもの・残したものと、未照合の一覧を河原さんが見る）
  - [ ] N-31（任意）。G-68 の「まだ直していない文書」、未決（音声の保存の期間・バックアップ・廃棄）
  - [ ] N-05a 前の DB の処分（河原さんが中身を確かめるまで手を付けない）

## グレーな判断

台帳 `docs/gray-decisions.md` の承認欄が空の行は、2026-11-06 の判断で埋まった（G-63 も同日に判断済み）。新しく自分で決めたことは台帳に足し、止まる点で見ていただく。

## 未決論点

1. **令和 8 年法律第 45 号の施行**：政令が出たら、後見・保佐を新しく使わないようゲートで止める（tsunagu-net の T-31a に合わせる。SEMANTICS SEM-GUARD-02）
2. **N-05a**：前の DB（`neo4j_data/`・`neo4j_backup/`・`neo4j_livelihood_*`）の処分。河原さんが確かめるまでそのまま
3. **G-42 (2)**：職員を仮名で呼ぶ運用が使いにくければ、実データを入れる前にもう一度決める

## 既知の罠・注意

- **開かないフォルダ**：`neo4j_data/`・`neo4j_backup/`・`neo4j_livelihood_*`・`.quarantine/`。`neo4j_plugins` は扱わない
- `Read(**/.env)`・`Read(**/.env.*)` の deny を外さない。`.env.example` も読まない。`mcp__neo4j__*` の道具は使わない
- tsunagu-net のポート（17474・17687・27474・27687、試しの 47xxx・48xxx）を使わない。nest-support の新しい DB は 37xxx・38xxx。27687 には一切つながない（G-50）
- 開発と試験は架空の事例だけ。実案件のデータをリポジトリに入れない。パスワードはリポジトリにもチャットにも書かない
- 条番号は e-Gov で照合してから書く。照合できないものは【未照合】
- rtk の hook が Bash の出力を切り詰める。長い出力・JSON・日本語を含む処理は Python のスクリプトにして流す
- 前の DB を指すコードの残り（G-49）：`lib/db_operations.py`・`sos/api_server.py`・`scripts/doctor.sh`・`scripts/rotate_password.py`・`setup.sh`・`installer/*`・`claude-skills/ecomap-generator/scripts/generate_mermaid.py`。消した script の名前を書いた文書（`CLAUDE.md`・`docs/PRIVACY_GUIDELINES.md`）は N-29
- 試験の数の目安：DB なし 749 passed・84 skipped、DB つき 833 passed（2026-11-06 止まる点 E-1）
- 段階 E の止まる点は E-1（N-27 の後）・E-2（N-28 の後）・E-3（N-30 の後）。計画の表にある
- 読み取りの包みは、実名・住所などの項目の名前を部分の一致で拒否する。正典の `ADDRESSES` も拒否される（台帳 G-64。決まるまでスキルで使わない）

## 次タスク（優先度順）

- A：止まる点 E-1 の河原さんの判断（スキル 8 本、G-64）
- B：N-28 SOS の中身 → 止まる点 E-2
- C：N-29 文書、N-30 `doctor.sh` → 止まる点 E-3
