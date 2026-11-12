# HANDOVER — 2026-11-12 main（段階 L は main に合流済み：merge commit e353f7e。この HANDOVER は枝 docs/handover-2026-11-12）

> 前の HANDOVER（2026-11-10 stage-l）は git 履歴にある。2026-08-03 の HANDOVER（ce627d9）に書かれた
> `~/.config/nest/neo4j.env`・ポート 7687・`nest-support-neo4j` は**前の構成**で、使わない。

## 再開コマンド（2026-11-12 11:10 に確かめた）

```bash
cd ~/Dev-Work/project/nest-support && git switch main && git pull   # 次の作業は新しい枝で（main に commit しない）
uv run pytest -q                       # 1354 passed, 155 skipped（DB を使う試験は skip）
uv run python scripts/check_drift.py   # ずれ 0 件
./scripts/doctor.sh                    # 33 passed, 2 warned, 0 failed（DB が止まっているとき）
```

DB を起こす・DB を使う試験（試験は**試験用の DB だけ**で流す。台帳 G-103）：

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d               # 試走（37474/37687）・資源（38474/38687）
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d neo4j-test    # 試験用（36474/36687。profile "test"）
NEST_DB_TARGET=test NEST_LIVE_DB=1 uv run pytest -q   # 最後に流したのは 2026-11-12 10:5x：1509 passed（落ち 0）
docker compose --env-file ~/.config/nest/neo4j-redesign.env stop neo4j-test     # down だけでは試験用の DB は止まらない
docker compose --env-file ~/.config/nest/neo4j-redesign.env down                # --remove-orphans は使わない
```

- 接続してよいのは 37687（試走）・38687（資源）・36687（試験用）だけ。試験用の DB は試験の始まりに毎回空にする（試験用の印 `NestTestDbProbe` が無ければ止まる。印は 2026-11-12 に河原さんが置いた）
- `NEST_LIVE_DB=1` で試走の DB に向いていると、試験は始まりで止まる（それが正しい）。`NEST_DB_TARGET` は試験の一行の頭にだけ付ける（端末に設定したままにすると端末の道具も試験用に向く）
- `neo4j-redesign.env` の中身は読まない・表示しない。試験用の DB のパスワードは個人の側と同じ `NEST_PERSONAL_PASSWORD`
- 起動の前に `docker ps` で前の DB が動いていないこと、起動の後に 127.0.0.1 だけで待ち受けていることを確かめる。doctor は試験用の DB が起きていると INFO を一行出す
- **2026-11-12 11:10 の時点で、nest の DB は三つとも止まっている**（`docker ps` に出ない）

新しい Mac でゼロから入れる手順は `docs/SETUP_GUIDE.md` の「0. 新しい Mac でゼロから」。

## 前提（実行前に現況で確かめること）

| 想定 | 確かめ方 | 最終確認日 |
|---|---|---|
| 段階 L の枝 stage-l は main に合流済み（GitHub の PR。merge commit e353f7e。origin/main と同じ）。この HANDOVER の枝 `docs/handover-2026-11-12` は**未 push** | `git status -sb`、`git log origin/main -1` | 2026-11-12 |
| **push・PR・合流は河原さん。** Claude は commit まで。main に commit しない（hook が止める） | — | 2026-11-12 |
| 職員：管理者「事務局」STF-01M6XBX18S58S4CD90W71YTH6C、職員「相談支援専門員A」STF-01M6XC4Y216FH8S736MS5S2CNV。**書き込み受付の職員（`gate_staff`）は相談支援専門員A のまま**（河原さんの指示） | `uv run python scripts/gate_staff.py check`、`uv run python scripts/staff_token.py list` | 2026-11-12（河原さんの報告） |
| 試走の DB（37687）の中身は**消さない**（live_mark・live_cleanup を打たない）。河原さんが手で入れた本人は C-N5AE5P（はると）・C-TM2KZZ（続柄の確かめ）。ほかに試験が足した架空の本人が多数（本人は計 1160 人、未確定 819 件。11-12 の数え）。試験と手入れは、作った職員・依頼の ID では見分けられない（手で入れた仮名の一覧を除くしかない） | DB を起こして `review_proposals.py list --code C-……`、`backup.py count` | 2026-11-12 |
| 試走の DB の残りの片づけは**別に決める**（提案は 2026-11-12 の会話。手順：一覧の確かめ → dump → 試しの実行 → 河原さんが消す。どの本人にもつながらない 88 件は purge では届かない） | — | 2026-11-12 |
| 試験用の DB（36687）には `NestTestDbProbe`・`NestLiveProbe` の二つの印がある | `NEST_DB_TARGET=test` で `MATCH (m:NestTestDbProbe) RETURN count(m)` | 2026-11-12 |
| narrative-extractor の SKILL：`~/.claude/skills/narrative-extractor` はリポジトリへのリンク。続柄（守ること 13）は Desktop に届いて確かめ済み。**印の掛かり方の一文（227efeb）が Desktop に届いたかは未確認** | Desktop で SKILL の守ること 3 を見る | 未確認 |
| バックアップの世代は `~/nest-backup/20261110-121315` の 1 つ | `uv run python scripts/backup.py list` | 2026-11-12 |
| 資源の側の写しは `~/Dist/tsunagu-net-trial-20261104` から読み込んだもの | `MANIFEST.json`（台帳 G-55） | 2026-11-05 |
| tsunagu-net（`~/Dev-Work/tsunagu-net`）と共通の約束 v1.1 は**変えない**。tsunagu-net のポートは 17xxx・27xxx・47474・47687・48687 | `git -C ~/Dev-Work/tsunagu-net log -1` | 2026-11-12（ポートだけ確かめた） |
| 令和 8 年法律第 45 号の施行日を定める政令は、まだ出ていない | e-Gov | 2026-11-05 |

## 現在地

- 目標：ADR-001・ADR-002 の作り直し。段階 L（入口・書き込み受付・narrative-extractor）を試走しながら直している。計画は `docs/implementation-plan.md`、段階 L・M の案は `docs/proposals/2026-11-08-stage-L-M.md`
- 進捗：
  - [x] 段階 A〜J、確認点 L-0（前の HANDOVER のとおり）
  - [x] 段階 L の最初（正典 v0.13、入口と受付の規則、書き込み受付の MCP `nest-gate`、narrative-extractor の書き直し）
  - [x] 2026-11-11〜12 の Claude Desktop での試走と直し（記録 `docs/journal/2026-11-11-stage-L-trial-fixes.md`）：show の項目名・list --code・機関の名前・関わりの確度（G-97）・終わり方（G-98）・接触の一文（G-99）・見立ての記録の種類（G-100・G-101）
  - [x] **正典 v0.14：新しい人の続柄**（G-102。SCHEMA §7・§4.3、SEMANTICS SEM-REC-06 と語の一覧）。Desktop で C-TM2KZZ に通して確かめた。`ChangeProposal` は v0.15 に送った
  - [x] **試験用の DB**（G-103。36687。DB を使う試験は試験用だけ。バックアップの試験も試験用のコンテナを止める）
  - [x] review_proposals の表示：list の人の行に続柄・仮名は一度、各行に根拠の引用の冒頭（24 字）、関わりの承認・差し戻しの結果に機関・サービスの種類・終わり方（Desktop と本物の DB で確かめた）
  - [x] 出す人と承認する人を分けた承認を確かめた（自己承認の記録が出る）
  - [ ] `scripts/submit_proposal.py` と手順書の予備の小段を外すか（G-94。河原さんの指示待ち）
  - [ ] 段階 L・M の案（K-5）を計画に移していない

## グレーな判断

- G-102 の実装で Claude が決めたこと（報告済み・承認の言葉はまだ無い）：情報提供の書面（`ProvisionDocument`）の案に続柄があっても入口で止めない（書き込み受付が書面を受けないので今は害が無い）。人の承認は、続柄の根拠の記録がすべて差し戻し済みでも止まる（ほかの根拠と同じ扱い）
- G-103 の実装で Claude が決めたこと（報告済み）：試験用の DB のパスワードを個人の側と共有。`NEST_DB_TARGET` を端末に設定したままだと端末の道具も試験用に向く（決まった二つから選ぶ作りなので防いでいない）
- 一覧の引用の冒頭は 24 字で切る（Claude の決め。河原さんは「短く」とだけ指示）

## 未決論点

1. **L-2 で決める論点**（`docs/proposals/2026-11-08-stage-L-M.md`）：1 差し戻した禁忌の出し直し、2 危険度が分からないときの値、3（作った）、4 終わった関わり、5 照会 13 は上限 500 で新しいものが返らない（本人で絞るのを基本にするか）、6 自己承認は止めずに記録だけでよいか
2. 続柄の残り（提案 2026-11-12 §7）：既にいる人に後から続柄を足す道（職員が作る形を推す）、C-N5AE5P の結ばれていない 3 人、機関の職員は続柄で見分けられず二重に作られる
3. 支援の方針の水準の見立てを置く場所（L-3 の前に決める）、情報提供の書面の見立て
4. G-80（実データを Claude に渡す契約の形）、令和 8 年法律第 45 号の施行、SOS のポート（8010）、ダッシュボードの項目

## 既知の罠・注意

- **開かないフォルダ**：`neo4j_data/`・`neo4j_backup/`・`neo4j_livelihood_*`・`.quarantine/`。`.env`・`~/.config/nest/` の中身は読まない
- **DB を使う試験は試験用の DB で**。受付の検証やゲートを変えたら、その報告で DB を使う試験を流す許可を求める（5420ca1 で既存の試験の準備が止まり、流さずに先へ進んで見つかるのが遅れた。journal に記録）
- `docker compose down` だけでは試験用の DB は止まらない（profile "test"）。`stop neo4j-test` も打つ
- 照会口（読み取りの包み）は 500 行で切る。試走の DB は本人が 1160 人いるので、全体を並べる照会は途中で切れる
- AI 由来のノードと職員が作る続柄を一つの依頼に混ぜると止まる（別の依頼に分ける。G-102）
- review_proposals の試験の偽の DB（`tests/test_review_show_content.py` の FakeTx）は問い合わせの文字で振り分ける。問い合わせに `EVIDENCED_BY]->(e:Record)` などの同じ文字を足すと振り分けが狂う
- 確度の印は、そのすぐ前で終わる引用だけに掛かる（SEM-ENUM-02。前の文は `Unspecified`。入口は止まらない）
- 開発と試験は架空の事例だけ。実在の機関名・ID を試験・journal・手順書に書かない。直訳の比喩を文書に使わない
- rtk の hook が Bash の出力を切り詰める。日本語を含む編集は Python のスクリプトで。HEAD などは `git rev-parse` で取る
- sos の既定のポート 8000 は open-notebook が使っている（`PORT=8010`）

## 次タスク（優先度順）

- A：河原さんの次の指示を待つ。試走の DB の残りの片づけを決めるなら、手順（手で入れた本人の仮名の一覧の確かめ → `backup.py dump` → 試しの実行の件数 → 河原さんが消す）を道具にする
- B：L-2 の論点 1〜6 を決める材料をそろえる。`submit_proposal.py` を外すか（G-94）
- C：段階 L・M の案（K-5）を計画に移す。L-1 の残り（失効・交代・修正・食い違い。`ChangeProposal` は正典 v0.15）
- D：河原さんの側の未決（G-80、療育手帳の通知の照合）。tsunagu-net への提案（G-40）の渡し方
