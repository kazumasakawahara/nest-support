# 実装計画 — v0.1（ADR-001 の作り直し）

- 状態：案（2026-11-05）。1 タスク＝1 行。試験を先に書き、緑になったらコミットする
- 「止まる点」では作業を止め、河原さんに成果物を見せて承認を得る
- 試験はすべて架空の事例で行う。実案件のデータは使わない。tsunagu-net から写すのも架空の例だけ
- Neo4j を起動するのは結合試験のタスクだけ。作業の終わりに止める。tsunagu-net のポート（17474・17687・27474・27687）は使わない
- 前の DB の跡（`neo4j_data/`・`neo4j_backup/`・`neo4j_logs/`・`neo4j_livelihood_*`・コンテナ `nest-support-neo4j`）は、河原さんが確かめるまで開かない・起動しない・消さない。新しい DB は別のフォルダに作る
- 根拠：`docs/adr/ADR-001-redesign-and-shared-contract.md`（承認 2026-11-05）、約束 v1
- 新しく書くコードは `nest/`（新しいパッケージ）に置く。今の `lib/` は、置き換えが済んだ部分から外す。**`lib/genai.py`（Gemini の入口・文字起こし・OCR）も、`lib/` を `nest/` へ移すときに一緒に移す**（`nest/egress.py` には入れない。送ってよいかを決める側と送る側を分ける。台帳 G-30）
- **google-genai は 1.66.0 に固定する**（`pyproject.toml` と `uv.lock`）。版を上げるときは、送り先を変える環境変数（1.66.0 では `GOOGLE_GENAI_USE_VERTEXAI`・`GOOGLE_GEMINI_BASE_URL`・`GOOGLE_VERTEX_BASE_URL`）が増えていないか、部品の中身（`_api_client.py`・`_base_url.py`）を読み直してから上げる。版の試験（`tests/test_gemini_gate.py`）も同じときに直す（2026-11-05 河原さん。台帳 G-28）

## 段階 A　送らない・埋め込まない（DB なしで動くもの）

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-18a | compose の `restart:` を `"no"` にする（N-18 から繰り上げ。2026-11-05 河原さん）。直すまで `docker compose up` を打たない | compose の `restart:` の行がすべて `"no"`（`tests/test_compose_restart.py`） | ✅ 2026-11-05 |
| N-00 | `docs/external-api.md` を書く（送り先ごとに何を送るか。既定は「送らない」。使う人が契約を確かめた記録の欄。ADR D11） | — | ✅ 2026-11-05（v0.2 で河原さん承認） |
| N-01 | Python の骨格（`nest/`）と、フィクスチャの架空の注記の検査 | 注記の無いフィクスチャで失敗し、ある物で通る | ✅ 2026-11-05（`nest/fixtures_check.py`、`tests/test_fixtures_fictional.py` 13 件。全体 188 passed） |
| N-02 | 送信の歯止め（`nest/egress.py`）：送り先の一覧（文書の NEXT 行のホスト）をコードに持ち、一覧外・やめた行へは送らない。Gemini・LINE は、機能ごとの明示の設定（`~/.config/nest/external-api-features.json`）と契約の確認の記録（`~/.config/nest/external-api-record.json`）の両方がそろわなければ送らない。記録の条件は external-api §5 の 6 つ（行ごと・5 項目がすべて埋まる・要配慮は明示の true だけ・次に確かめる日・無い／読めない／600 より広いは不許可・置き場所はコードに固定で環境変数で変えない）。LINE の送信（`sos/api_server.py`）をこの歯止めに通す。Gemini は N-03 | 6 条件のそれぞれで不許可になる例と、そろって許可になる例。鍵だけある状態で送らない。一覧外のホスト・やめた行で失敗する。一覧と文書の行がずれたら失敗する。HOME を変えても置き場所が変わらない | ✅ 2026-11-05（`nest/egress.py`、`tests/test_egress.py` 60 件・`tests/test_egress_line.py` 3 件。全体 251 passed） |
| N-03 | Gemini を既定で止める：文字起こし（`transcribe_audio`・field-ui の音声）・OCR（`file_readers`・`ocr_with_gemini`）を N-02 の歯止めに通す | 鍵があっても、設定と記録が無ければ外部への呼び出しが 0 回（偽の送信先で数える） | ✅ 2026-11-05（`lib/embedding.py` の `get_genai_client(row)` が呼ぶたびに許可を確かめる。埋め込みは NEXT-06、`multi_importer` の構造化は NEXT-07 で常に不許可。送り先を固定。`tests/test_gemini_gate.py` 10 件。全体 267 passed。台帳 G-28・G-29） |
| N-04 | 埋め込みを外す（ADR D10）：登録時の埋め込み、`backfill_embeddings.py`、ベクトル索引の作成、意味検索、似た本人の検索。関係する既存の試験を改める | コードの中に埋め込みの呼び出しとベクトル索引の作成が残っていない検査 | ✅ 2026-11-05（`lib/embedding.py`・`scripts/backfill_embeddings.py`・`scripts/check_weight_consistency.py` を外した。Gemini の入口・文字起こし・OCR は `lib/genai.py`、面談記録の登録は `lib/meeting_record.py`（埋め込みなし）へ移した。`tests/test_no_embedding.py` 3 件・`tests/test_gemini_gate.py` 13 件。google-genai を 1.66.0 に固定。全体 267 passed。台帳 G-30〜G-33） |
| N-05 | `multi_importer.py` の Gemini による構造化を外す（ADR D11-1） | 構造化の経路が外部を呼ばない検査。`structurize_with_gemini` の記録の文言「GEMINI_API_KEY が未設定です」の消し忘れが無いことを確かめる（台帳 G-29）。外した後は `tests/test_no_embedding.py` の許す行から NEXT-07 を除く |  ✅ 2026-11-05（`structurize_with_gemini` と、構造化の結果を DB に書く経路を外した。`multi_importer` は文字を取り出して出力するだけ。field-ui の音声は文字起こしを返すだけで、構造化も登録もしない。文言「GEMINI_API_KEY が未設定です」は鍵を読む `lib/genai.py` だけに残ることを試験で確かめる。`tests/test_no_structurize.py` 4 件。全体 270 passed。台帳 G-34） |
| N-05a | 前の DB の処分を決める：`neo4j_data/`・`neo4j_backup/`（埋め込みの値を含みうる。要配慮個人情報から派生した値として扱う。台帳 G-33）と `neo4j_logs/`・`neo4j_livelihood_*`・`.quarantine/`。消すか、新しい DB に移すときに落とすか。新しい DB への切り替え（段階 D）の前に、河原さんが中身を確かめてから決める | — | |

## 段階 B　正典（nest-support の中に持つ）

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-06 | 正典の案 `docs/SCHEMA.md`：ラベル・関係・値、確度（5 値・二段）、聞いた記録と禁忌の結び方（D5）、`orgId`、ID の形、承認（D9）、CarePreference などに D5 の形を広げるか | — | |
| **止まる点 2** | 正典の案（型）を河原さんに見せる。ラベル・関係の名前、D5 を広げる範囲 | | |
| N-07 | 正典の JSON と、それを読む部品（`nest/canon.py`） | 壊れた JSON・欠けたキーで失敗する | |
| N-08 | 乖離の検査（`scripts/check_drift.py`）：正典の表と JSON、のちにゲートの許す一覧と突き合わせる | 表と JSON がずれた入力で失敗する | |
| N-09 | shared-schema の写しを外す：`docs/SCHEMA_CONVENTION.md`・`docs/SEMANTIC_MODEL.md` とその `.bak`、`check_semantic_drift.py` の agno・shared-schema の参照（付録の表） | 外した後に、リポジトリの中に shared-schema・`/api/narrative` への参照が残っていない検査（記録の文書は除く） | |

## 段階 C　ゲート（約束 4）

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-10 | ID の発番と検査（ULID）。個人の側の ID が `ORG-` の形にならない。`orgId` の形の検査 | `ORG-` の形の誤りを拒否する。個人の側の ID に `ORG-` を使うと失敗する | |
| N-11 | tsunagu-net の `tests/test_intake.py` の例（両方向・架空）を写す | 写した直後は赤 | |
| N-12 | 引用の点検：事実ごとに原文の引用を持ち、原文に無ければ止める | N-11 の該当の例 | |
| N-13 | 数字の点検：引用に無い数字（日付・回数・金額・年齢・体重など）を足していれば止める | N-11 の該当の例 | |
| N-14 | 確度の点検：原文の印の読み方、重なったら弱いほう、印が無ければ記載なし、二段の確度。AI が上げても下げても止める | N-11 の該当の例 | |
| N-15 | 型の点検：型に無い項目・値は直さずに止めて理由を返す。直すのは大文字・小文字と確度の日本語名だけ | snake_case・旧い関係名・riskLevel の別名（「高」など）で止まる | |
| N-16 | AI 由来は未確定。人は名前で同定しない（参照は ID か候補） | 名前だけで既にある人を指す案で止まる | |
| N-17 | Guardian Layer（`lib/schema_validator.py`）の自動補正を外し、書き込みの経路をゲートに切り替える。`test_schema_validator.py` を改める | 自動補正が起きないこと | |

## 段階 D　DB と書き込み・承認

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-18 | compose を改める：127.0.0.1 だけで待ち受け、新しいデータのフォルダ。資源の Neo4j をもう一つ立てる（D2-2。2026-11-05 承認）。`restart: "no"` は N-18a で済み | 起動の後に両方へ接続でき、互いのデータが見えない。前のデータのフォルダを使っていない | |
| **止まる点 3** | ポート番号（tsunagu-net の 17474・17687・27474・27687 と別）を河原さんに見せる。読み込み方は D2-2 で承認済み | | |
| N-19 | スキーマの適用：正典の JSON から一意制約・インデックスを作る | ベクトル索引が 0 件。制約の一覧が JSON と一致 | |
| N-20 | ゲートの書き込み：未確定で書き、AuditLog を残す。禁忌と聞いた記録（D5）、食い違いの保留。既にある禁忌に結ぶのは人の指定だけ | 自動でまとめない。結ぶ指定が無ければ新しい禁忌（未確定） | |
| N-21 | 承認の操作（D9）：書き込みとは別の操作、引用を並べて見せる、AI 由来の一括の承認を拒否、AuditLog | 一括の承認で失敗する。承認の AuditLog が残る | |
| N-22 | 読み取りだけの MCP の包み（個人の側と資源の側の両方）。手本は tsunagu-net の枝 `claude/tender-dijkstra-xo3wwc` のコミット `d8e6e2d` の `tsunagu/mcp_resource.py`（main に未収録。main に入ったら参照先を書き換える）。手本から持ち込むもの：(1) EXPLAIN の種類が r でなければ拒否 (2) 種類が r でも計画に LOAD CSV があれば拒否 (3) 手続きの呼び出しは許可の一覧（`db.labels`・`db.relationshipTypes`・`db.propertyKeys`）だけ (4) 計画が読めないときは閉じる側に倒す (5) 返す行数の上限 500 と読み取りのトランザクション。強めるところ（2026-11-05 河原さん）：歯止めは EXPLAIN の判定の側に置き、`routing_="r"` は保険とする。行数は全部を受け取ってから切らず、結果を流しながら 500 行で止める（Cypher に LIMIT を差し込まない）。EXPLAIN・PROFILE つきと空も拒否。個人の側は、同じ形に、実名・かな・電話・住所・生年月日の伏せ字を足したもの（2026-11-05 河原さん）。`.mcp.json` から `neo4j-shared` を外す。注記：手本の (5) は `routing_="r"`（読み取りの経路）で、tsunagu-net G-14 のとおりアクセス制御にはならない。行数は全部を受け取ってから切っている | 書き込み・スキーマの変更・LOAD CSV・許可外の手続き・読めない計画・EXPLAIN つき・空を、実行前に拒否する（手本と同じ例）。行数が 500 を超えない。個人の側の既定の結果に実名・かな・電話・住所・生年月日が無い | |
| N-23 | 資源 DB の読み込み（D2）：版と指紋（`MANIFEST.json`）の記録。資源の側への書き込みはこの道具だけ | 指紋が合わない書き出しを拒否する | |
| N-24 | 機関の候補（D3）：原文の名前から候補を出し、人が `orgId` を選ぶ。選ぶまでは機関未確定 | 名前の一致だけで `orgId` を入れる案で止まる | |
| **止まる点 4** | 架空の語りで、取り込み→点検→未確定→承認→照会を通して見せる | | |

## 段階 E　スキルと文書

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-25 | narrative-extractor の書き直し：書き込みの案（JSON）を出すだけ。Cypher の書き込みと、名前の統合の指示を消す | 案の例がゲートを通る（架空） | |
| N-26 | EXTRACTION_PROMPT の書き直し：原文に無い値で埋める指示を消す | — | |
| N-27 | 読み取りのスキル（neo4j-support-db・visit-prep・emergency-protocol・data-quality-agent・resilience-checker・onboarding-wizard・ecomap-generator・insight-agent）の照会を新しい正典に合わせる。スキルごとに 1 行に分ける | 照会のテンプレートを正典の JSON と突き合わせる検査 | |
| N-28 | SOS の中身（D11-3）：LINE には SOS・誰のことか・位置・確かめる先だけ | 送る文に電話と禁忌が無い | |
| N-29 | 文書を直す：PRIVACY_GUIDELINES（条番号は e-Gov で照合）・CLAUDE.md・README・QUICK_START・SETUP_GUIDE・manifesto の共有層と 7687 の記述（付録の表） | — | |
| N-30 | `doctor.sh` を新しい構成に合わせる | doctor.sh が新しい構成で全項目を通る | |

## 付録　neo4j-agno-agent の共有層（7687）・shared-schema に頼っている箇所（2026-11-05 時点）

記録の文書（HANDOVER・MIGRATION_LOG・SUMMARY・ADR・台帳）と、git 管理外の跡（`neo4j_livelihood_logs/`・`.quarantine/`）は直す対象にしない。

| 箇所 | 頼っている中身 | 直すタスク |
|---|---|---|
| `.mcp.json`・`configs/claude_desktop_config.json`・`.claude/settings.local.json` | MCP `neo4j-shared`（`~/.config/nest/neo4j.env` で 7687 へ） | N-22 |
| `claude-skills/provider-search/SKILL.md` | 共有層 7687・`neo4j-shared`・shared-schema の写しの注記 | nest-support の DB からは使わない。スキルは消さない（ADR D2-4）。注記だけ N-29 |
| `claude-skills/wamnet-provider-sync/scripts/sync_providers.py`・`generate_report.py` | 既定の接続先が `bolt://localhost:7687` | 同上（スキルは消さない） |
| `scripts/check_semantic_drift.py` | shared-schema のマスター、agno の `/api/narrative/schema` | N-09（N-08 に置き換える） |
| `docs/SCHEMA_CONVENTION.md`・`docs/SEMANTIC_MODEL.md`・`docs/*.bak-*`・`docs/semantic-model-instruction.md` | shared-schema の写し（同期の対象） | N-09 |
| `claude-skills/` の neo4j-support-db・visit-prep・emergency-protocol・data-quality-agent・insight-agent | 「正は shared-schema の SEMANTIC_MODEL」の注記、「port 7687」の記述 | N-27 |
| `lib/schema_validator.py` | `VALID_NODE_LABELS_7687` などの名前（中身は個人層） | N-17 |
| `lib/embedding.py` | agno 由来のベクトル索引名の分岐 | ✅ N-04 でファイルごと外した |
| `lib/db_operations.py`・`scripts/migrate_*.py`・`claude-skills/ecomap-generator/scripts/generate_mermaid.py` | 「`neo4j.env`（共有層 7687）より個人層を優先する」読み込みの順 | N-29（`migrate_*` は外す候補） |
| `sos/.env.example` | `NEO4J_URI=bolt://localhost:7687` | N-28 |
| `scripts/rotate_password.py`・`scripts/backup.sh`・`scripts/doctor.sh` | 共有層 7687 の説明と除外 | N-30 |
| `.env.example`・`README.md`・`docs/QUICK_START.md`・`docs/SETUP_GUIDE.md`・`docs/SETUP_GUIDE.html`・`docs/PRIVACY_GUIDELINES.md`・`CLAUDE.md`・`manifesto/MANIFESTO.md`・`manifesto/protocols/emergency.md`・`onboarding.md`・`docker-compose.yml` の注記 | 共有層・7687・neo4j-agno-agent の記述 | N-29 |
| `tests/test_db_module_consolidation.py` | neo4j-agno-agent のファイルの場所への言及 | N-17 |
| `~/Dev-Work/shared-schema/sync-schema.sh`（リポジトリの外） | `--write-prod` で nest-support の `docs/` に書き込む | 変えない（ADR 未決論点 3） |
