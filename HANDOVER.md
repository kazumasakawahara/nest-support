# HANDOVER — 2026-08-03 main（WAM NET スキル整合 / serena_config 混入の切り出し）

> claude.ai 側のチャットから、`~/.claude/CLAUDE.md` の棚卸しを起点に横展開したセッション。
> nest-support 本体のコード・テスト・DBへの書き込みは**一切なし**（読み取りのみ）。
> 変更したのは `claude-skills/wamnet-provider-sync/SKILL.md` の1ファイルのみ。
> 前セッション（2026-07-13 / grade=不明 検出の追加）の HANDOVER は
> `~/.claude/backups/2026-08-03-claude-md-refactor/nest-support-HANDOVER-2026-07-13.md` と git 履歴を参照。

## 再開コマンド（前回検証済み・今回は未再検証）

```bash
cd ~/Dev-Work/project/nest-support
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
./scripts/doctor.sh                              # 環境整合
uv run python scripts/check_semantic_drift.py    # 四者一致
uv run pytest tests/ -q                          # 全テスト
```

Neo4j（support-db, port 7687）コンテナ名は `nest-support-neo4j`。本セッション末に**停止済み**（Docker Desktop も終了）。再開時は起動が要る。

---

## 現在地

### 完了：`wamnet-provider-sync/SKILL.md` の内部矛盾を解消

SKILL.md 内で MERGE キーの記述が食い違っていた。**shared-schema との矛盾ではなく、SKILL.md 内部の矛盾**だった。

| プロパティ | 中身 | 役割 |
|---|---|---|
| `providerId` | `{事業所番号}_{サービス種類コード}` | **MERGE キー**（一意） |
| `wamnetId` | 事業所番号そのもの | 名前揺れ対策・横断検索（**一意ではない**） |

旧マッピング表は「事業所番号 → `providerId`（MERGE用キー）」「`wamnetId` は事業所番号と同じ」と書いており、Q2 の複合キーの説明と矛盾していた。

修正5点：

1. マッピング表：事業所番号 → `wamnetId`、`name` に `normalize_name()` 適用を明記
2. マッピング表：`providerId` を複合キーとして正しく記載
3. **スキーマ規約の正典は `~/Dev-Work/shared-schema/SCHEMA_CONVENTION.md`** であることを明示（食い違ったら向こうを優先／camelCase のみ／正規化関数）
4. **Cypher 例に `SET sp.wamnetId` を追加**（元は欠落していた）
5. Q2 を書き下し（一意制約は `providerId` 側にかけ、`wamnetId` にはかけない）

`claude-skills/wamnet-provider-sync/` が実体で、`~/.claude/skills/wamnet-provider-sync` はそこへの symlink。片方を直せば両方に反映される（複製ではない、正しい構成）。

### 完了：`~/.serena/serena_config.yml` に紛れ込んでいた93行の切り出し

Serena のグローバル設定ファイルの先頭に、`domain_skills:` という **Serena が解釈しないキー**で WAM NET のオープンデータ取得手順が書かれていた。本来 `wamnet-provider-sync` のスキル本文に書くつもりだったもの（河原氏の記憶による）。

- 切り出し先：`~/.claude/backups/2026-08-03-claude-md-refactor/wamnet-domain-skills.yml`（93行）
- 元ファイル全体：同ディレクトリの `serena_config.yml.orig`
- `serena_config.yml` は 348 → 222行。YAML パース検証済み、トップレベルキーはすべて Serena 正規のもの
- 副産物：`# the list of registered project paths...` が18回重複していたので1つに畳んだ（Serena が `projects:` 自動更新のたびに重ねる挙動。**また増える可能性がある**）

---

## グレーな判断（次セッション冒頭で承認確認を）

**「ServiceProvider は0件だからデータ移行不要」と結論したが、確認範囲が不十分だった。**

- 照会したのは稼働中の `nest-support-neo4j` のみ → ServiceProvider **0件**、制約・インデックスなし。ラベルは Client/Supporter/Hospital 等16種で ServiceProvider を含まない
- しかし別記録に「**ServiceProvider ノード2,621件（うち約1,500件が名称未登録）**」がある
- 停止中の `neo4j-support-db`（4ヶ月前に停止、同じ 7687 を使う構成）側と推定されるが**未確認**

SKILL.md の修正内容自体はどちらのDBでも正しい（内部矛盾の解消と欠落補完のため）。ただし**既存2,621件が `providerId` / `wamnetId` をどう持っているかは未確認**で、同期を実行する前に確かめる必要がある。

---

## 既知の罠・注意

- **Serena は MCP クライアントごとにプロセスが立つ。** ダッシュボードのポートは 24282 から順に上がる（24283, 24284...）。「TOOL USAGE が空」のときは別インスタンスを見ている可能性を疑う。確実なのは、そのセッションで `open_dashboard` を呼ばせること
- **Serena の CONTEXT が `desktop-app` のまま。** プラグイン（`plugin:serena:serena`）の `.mcp.json` に `--context` がなく、既定値にフォールバックしている。Claude Code から使う場合は `claude-code` context のほうが適切（重複ツールが減る）。ただし実使用実績がまだ乏しいため、TOOL USAGE に数字が溜まってから判断する方針とした
- `~/.serena/contexts/ide-assistant-enhanced.yml` は2025年11月に自作されたが、`--context` で名指しされていないため**読み込まれていない**。移行時の参照資料として残置
- `download_wamnet.py` は**自動ダウンロードをしない**。ポータルURLを案内して手動DLを促すだけ（21行目に「手動ダウンロード用」と明記）。ファイル名例は都道府県別（`shogai_fukuoka_YYYYMM.csv`）を想定

---

## 次タスク（優先度順）

### A: 必須

1. **`neo4j-support-db` の ServiceProvider を確認する。** 2,621件が実在するか、`providerId` / `wamnetId` をどう持っているか、制約はどこにかかっているか。同期を実行する前に必須。`nest-support-neo4j` と同じ 7687 を使うので、起動時のポート衝突に注意

### B: 推奨

2. **切り出した93行を SKILL.md に統合する。** 内容は CSV 直接DL の URL 形式とサービス種別コード一覧。統合先は `## WAM NETオープンデータについて` の `### データソース` 節が有力（現状は人間向けポータルURLのみで、機械可読な入口がない）

   ```
   https://www.wam.go.jp/content/files/pcpub/top/sfkopendata/{YYYYMM}/sfkopendata_{YYYYMM}_{SERVICE_CODE}.zip
   ```

3. **上記 URL が現在も有効か確認する。** WAM NET は年2回更新（4月・10月頃）なので、最新の `{YYYYMM}` も要確認。生きていれば `download_wamnet.py` を手動案内から自動取得へ書き換えられる。**スキルの実用性が大きく変わる**

### C: 余裕があれば

4. `shared-schema/SCHEMA_CONVENTION.md` §6.4 の「WAM NET インポート時期によりレガシーの snake_case が残存」が現状と合っているか確認。稼働中DBには ServiceProvider が0件なので残存していない。ただし停止中DB側の記録の可能性があるため、A の確認とセットで判断すること（**削除は慎重に**）
5. Serena の context 変更（プラグイン無効化 ＋ `claude mcp add serena -- ... --context claude-code`）。使用実績が溜まってから

## Neo4j 認証の置き場（2026-09-04）

- Neo4j 認証の正典は `~/.config/nest/neo4j.env`（`NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` の3行、chmod 600）。各リポジトリの `.env` にはもう書かない（`NEO4J_LIVELIHOOD_*` は対象外で従来どおり `.env`）。
- `~/.zshrc` が `set -a` で読み込むので、シェルから起動するプロセスと `docker compose` の `${NEO4J_USERNAME}` / `${NEO4J_PASSWORD}` 展開はこれで賄う。未設定のまま `docker compose` を実行すると `:?` で止まる（`see ~/.config/nest/neo4j.env`）。
- パスワード変更は `project/nest-support/scripts/rotate_password.py`（`uv run python scripts/rotate_password.py`）。DB 側の `ALTER CURRENT USER SET PASSWORD` と正典ファイルの書き換えを一括で行い、値は表示しない。実行後は開いているシェルで `source ~/.config/nest/neo4j.env` し直す。
- compose の `NEO4J_AUTH` は初回起動時（データディレクトリが空のとき）にしか効かない。既存データの DB のパスワードは compose ではなく rotate_password.py で変える。
