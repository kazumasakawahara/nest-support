# 実装計画 — v0.1（ADR-001 の作り直し）

- 状態：案（2026-11-05）。1 タスク＝1 行。試験を先に書き、緑になったらコミットする
- 「止まる点」では作業を止め、河原さんに成果物を見せて承認を得る
- 試験はすべて架空の事例で行う。実案件のデータは使わない。tsunagu-net から写すのも架空の例だけ
- Neo4j を起動するのは結合試験のタスクだけ。作業の終わりに止める。tsunagu-net のポート（17474・17687・27474・27687）は使わない
- 前の DB の跡（`neo4j_data/`・`neo4j_backup/`・`neo4j_logs/`・`neo4j_livelihood_*`・コンテナ `nest-support-neo4j`）は、河原さんが確かめるまで開かない・起動しない・消さない。新しい DB は別のフォルダに作る
- 根拠：`docs/adr/ADR-001-redesign-and-shared-contract.md`（承認 2026-11-05）、約束 v1.1（2026-11-05 改め）
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
| N-05a | 前の DB の処分を決める：`neo4j_data/`・`neo4j_backup/`（埋め込みの値を含みうる。要配慮個人情報から派生した値として扱う。台帳 G-33）と `neo4j_logs/`・`neo4j_livelihood_*`・`.quarantine/`。消すか、新しい DB に移すときに落とすか。新しい DB への切り替え（段階 D）の前に、河原さんが中身を確かめてから決める。**~/Dev-Work の下で前の DB（7688）を指す 7 か所（台帳 G-36）も一緒に扱う**。**N-09 で `~/nest-support-hold/2026-11-05-n09-bak/` に移した `docs/*.bak-*` の 19 件の処分も、ここで一緒に決める**（台帳 G-45。2026-11-05 河原さん） **前の DB のパスワードは `sos/.env.example` の履歴（GitHub にも上がっている）と `~/.config/nest/neo4j.env` にある（台帳 G-70）。処分するときは `~/.config/nest/neo4j.env` も一緒に消す。処分せず起動する場合は、起動の直後にパスワードを変える。** | — | F-1 で決めた（2026-11-06 河原さん。台帳 G-74）：**中身は新しい DB へ移さない。要る記録は、原本（紙・資料）から入口の点検とゲートを通して入れ直す**。消すのは河原さん（Claude は消さない）。`neo4j_data/`・`neo4j_backup/`・`neo4j_logs/`・コンテナ `nest-support-neo4j` は、河原さんが「実データの原本が別にある」と確かめてから消す。確かめるまでは今のまま（700・Time Machine 対象外・起動しない）。`neo4j_livelihood_*`・`.quarantine/` も同じ。`~/.config/nest/neo4j-personal.env` は一緒に消す。`~/.config/nest/neo4j.env` は残す（neo4j-agno-agent の設定。向こうを起動する前にパスワードを替える）。**消す手順（河原さんが打つ）**：(1) `docker ps -a --filter name=nest-support-neo4j` で止まっていることを確かめる (2) `docker rm nest-support-neo4j`（取り付けは bind なのでボリュームは無い。`docker volume ls` に nest-support の前の DB の名前が無いことを確かめる） (3) `rm -rf neo4j_data neo4j_backup neo4j_logs neo4j_livelihood_data neo4j_livelihood_logs neo4j_livelihood_plugins neo4j_plugins .quarantine`（リポジトリの直下で。`neo4j_plugins/` も消す：新しい compose は APOC を入れない。N-18。2026-11-06 河原さん） (4) `rm ~/.config/nest/neo4j-personal.env` (5) 確かめ：`docker ps -a` に `nest-support-neo4j` が無い、`ls -d neo4j_* .quarantine` が何も出さない、`./scripts/doctor.sh` が FAIL 0。`~/nest-support-hold/` の写しのうち `COMPLETE_MANUAL.md`・`COMPLETE_MANUAL.html`・`家族聴き取りマニュアル.docx` は、河原さんが実名の無いことを確かめたうえで `docs/archive/` にコミットする（Mac が git add する。docx は読まない）。残りの 17 件と .bak は、その後に河原さんが消す（止まる点 F-3。2026-11-06 河原さん）。**✅ 済み（2026-11-06。河原さんが打った）**：`docker ps -a` に `nest-support-neo4j` が無い。`neo4j_*`・`.quarantine/` が無い。`~/.config/nest/neo4j-personal.env` を消した。doctor 29 passed・2 warned・0 failed（WARN は external-api の記録と設定が無いこと。台帳 G-80）。写し 3 件は `docs/archive/` にコミットした（c5813e6）。**残っているもの**：コンテナ `support-db-neo4j`（Exited。nest-support の前の DB ではない）、`~/.config/nest/neo4j.env`（neo4j-agno-agent の設定。残す）、`~/nest-support-hold/2026-11-05-uncommitted/` の残り 17 件と `.DS_Store`（河原さんが消す）。N-09 の `.bak` の置き場所 `~/nest-support-hold/2026-11-05-n09-bak/` は、2026-11-06 に見たとき無かった |
| N-05b | 段階 A の締め（台帳 G-35 の手当て）：`.mcp.json` から Neo4j の MCP（`neo4j`・`neo4j-shared`）を外す（NEXT-11 の前倒し。N-22 の包みができたら入れ直す）。Claude Desktop の設定にある同じ項目の場所を河原さんに伝える。APOC は公式の文書だけで確かめ、「URL を読みに行ける」と仮定して扱う。~/Dev-Work の下で 7688・7687・`bolt://`・`neo4j://` を読み取りだけで探し、台帳に載せる | `.mcp.json` に Neo4j の MCP が無い（`tests/test_mcp_config.py`） | ✅ 2026-11-05（全体 271 passed。台帳 G-35・G-36） |

## 段階 B　正典（nest-support の中に持つ）

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-06 | 正典の案 `docs/SCHEMA.md`：ラベル・関係・値、確度（5 値・二段）、聞いた記録と禁忌の結び方（D5）、`orgId`、ID の形、承認（D9）、CarePreference などに D5 の形を広げるか | — | ✅ 2026-11-05（v0.1 案 → 止まる点 2 の河原さんの判断 → v0.2。ADR D3 を改めた。台帳 G-37〜G-41） |
| **止まる点 2** | 正典の案（型）を河原さんに見せる。ラベル・関係の名前、D5 を広げる範囲 | | |
| N-07 | 正典の JSON と、それを読む部品（`nest/canon.py`） | 壊れた JSON・欠けたキーで失敗する |  ✅ 2026-11-05（正典 v0.2 §11 に JSON を置いた。ブロックの数・壊れた JSON・欠けたキー・無いラベルへの関係・接頭辞の欠け・重なり・`ORG`・無い列挙値への対応で失敗する。本物の正典で、ラベル 16、約束の列挙値、`Record` の項目が tsunagu-net とそろうこと、埋め込みの項目が無いことを確かめる。`tests/test_canon.py` 30 件。全体 301 passed） |
| N-08 | 乖離の検査（`scripts/check_drift.py`）：正典の表と JSON、のちにゲートの許す一覧と突き合わせる | 表と JSON がずれた入力で失敗する |  ✅ 2026-11-05（正典の表と JSON：§3 の接頭辞、§4.2 のノードと項目（✅＝必須）、§4.3 の始点・終点と項目、§4.5 の列挙値（順も）。節・表が見つからないとき、JSON が読めないときも失敗。読めるように §4.3 の `EVIDENCED_BY`・`CONTRADICTS` の始点・終点をラベルの並びで書き、「（…ノード）」は任意のラベルとした。本物の正典でずれ 0 件。ゲートの許す一覧との突き合わせはゲート（N-15）ができてから足す。`tests/test_check_drift.py` 15 件。全体 321 passed） |
| N-09 | shared-schema の写しを外す：`docs/SCHEMA_CONVENTION.md`・`docs/SEMANTIC_MODEL.md` とその `.bak`、`check_semantic_drift.py` の agno・shared-schema の参照（付録の表） | 外した後に、リポジトリの中に shared-schema・`/api/narrative` への参照が残っていない検査（記録の文書は除く） |  ✅ 2026-11-05（git から 4 件を外した。`docs/*.bak-*` 19 件は git の外なので保管の場所へ移した。参照の行は台帳 G-45。検査は、コードと設定に `shared-schema`・`/api/narrative`・`check_semantic_drift` が無いこと。文書・スキルの説明文は N-27・N-29。`tests/test_old_canon_removed.py` 3 件。全体 325 passed。**段階 B を閉じた**（2026-11-05 河原さん）） |

## 段階 C　ゲート（約束 4）

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-10 | ID の発番と検査（ULID）。個人の側の ID が `ORG-` の形にならない。`orgId` の形の検査 | `ORG-` の形の誤りを拒否する。個人の側の ID に `ORG-` を使うと失敗する |  ✅ 2026-11-05（`nest/ids.py`。接頭辞の表は正典の JSON と同じであることを試験で確かめる。`ORG-` は形だけ確かめ、個人の側では発番しない。団体コードの検査数字（`Residence.areaCode` 用）。`tests/test_ids.py` 40 件。全体 365 passed） |
| N-11 | tsunagu-net の `tests/test_intake.py` の例（両方向・架空）を写す | 写した直後は赤 |  ✅ 2026-11-05（`tests/test_intake.py` に 20 件。架空の原文は `tests/fixtures/intake/`。写した直後は 20 件とも赤。N-12〜N-16 のどれで緑にするかを `xfail(strict=True)` で印した。台帳 G-46） |
| N-12 | 引用の点検：事実ごとに原文の引用を持ち、原文に無ければ止める | N-11 の該当の例 |  ✅ 2026-11-05（`nest/gate/intake.py`：案の形（書面か自分の記録か・提供元・本人の ID・facts）と引用の点検（空白・改行の違いだけ無視）。原本の指紋は原文から作る。試験 13 件が緑、残り 7 件は N-13〜N-16。台帳 G-46 の (5)） |
| N-13 | 数字の点検：引用に無い数字（日付・回数・金額・年齢・体重など）を足していれば止める | N-11 の該当の例 |  ✅ 2026-11-05（本文に引用に無い数字があれば止める。全角の数字は半角と同じに数える。数字を足さない言い換えは警告して通す。試験 14 件が緑） |
| N-14 | 確度の点検：原文の印の読み方、重なったら弱いほう、印が無ければ記載なし、二段の確度。AI が上げても下げても止める | N-11 の該当の例 |  ✅ 2026-11-05（原文の印【…】の読み方（重なったら弱いほう、印が無ければ Unspecified、知らない印で止める）、書面の二段の確度（受けた側は提供元より強くしない）、自分の記録の一段。上げても下げても止める。試験 17 件が緑。ゲートの側の二段の決まりは N-15 で検証にも入れる） |
| N-15 | 型の点検：型に無い項目・値は直さずに止めて理由を返す。直すのは大文字・小文字と確度の日本語名だけ | snake_case・旧い関係名・riskLevel の別名（「高」など）で止まる |  ✅ 2026-11-05（`nest/gate/validate.py`：正典の JSON で、ラベル・関係・項目・必須・列挙値・型・始点と終点・既にあるノードの ID・二段の確度・後見の類型を検証。直すのは大文字・小文字と確度の日本語名だけで、直したことを返す。snake_case・旧い関係名・riskLevel の別名・埋め込みの項目・ゲートが付ける項目で止まる。入口でも型に無い項目で止まる。`tests/test_gate_validate.py` 48 件。全体 432 passed。台帳 G-47） |
| N-16 | AI 由来は未確定。人は名前で同定しない（参照は ID か候補） | 名前だけで既にある人を指す案で止まる |  ✅ 2026-11-05（入口：話した人は PER の ID・新しい人の名札・本人だけ。名札の形と重複。検証：既にあるノードは {label, id} だけで指し、名前を添えたら止める。AI 由来は Pending、ほかは Active を返す（書き込みは N-20）。N-11 で写した 20 件はすべて緑になり、xfail の印を外し終えた。全体 438 passed） |
| N-17 | Guardian Layer（`lib/schema_validator.py`）の自動補正を外し、書き込みの経路をゲートに切り替える。`test_schema_validator.py` を改める | 自動補正が起きないこと | ✅ 2026-11-05（N-20 を待たずに閉じた。2026-11-05 河原さん）。`register_to_database` は何も直さず書かずに断りを返す。`lib/schema_validator.py` は外した。field-ui の支援記録は 503 を返し、画面に「使わない」の注記。insight-engine の昇格にも同じ注記。N-20 まで書けない。台帳 G-49 |

## 段階 D　DB と書き込み・承認

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-18 | compose を改める：127.0.0.1 だけで待ち受け、新しいデータのフォルダ。資源の Neo4j をもう一つ立てる（D2-2。2026-11-05 承認）。**APOC は既定で入れない**（入れるかは N-05a か N-22 で決める。台帳 G-35 の 3）。`restart: "no"` は N-18a で済み | 起動の後に両方へ接続でき、互いのデータが見えない。前のデータのフォルダを使っていない |  compose を書いた 2026-11-05（起動していない。中身の検査 `tests/test_compose_new.py` 8 件。`docker compose config` で書式を確かめた。台帳 G-48）。✅ 2026-11-05 起動した（河原さんの手順 1〜3。前の `nest-support-neo4j`・`support-db-neo4j` は止まったまま、待ち受けは 127.0.0.1 の 4 つだけ）。接続の試験 `tests/test_db_new_live.py` 9 件（`NEST_LIVE_DB=1` のときだけ動く）。台帳 G-51 |
| **止まる点 3** | ポート番号（tsunagu-net の 17474・17687・27474・27687 と別）を河原さんに見せる。読み込み方は D2-2 で承認済み | | |
| N-19 | スキーマの適用：正典の JSON から一意制約・インデックスを作る | ベクトル索引が 0 件。制約の一覧が JSON と一致 | ✅ 2026-11-05 `nest/schema_apply.py`・`scripts/apply_schema.py`（既定は文を出すだけ）・`nest/connections.py`。個人の側にだけ当てた（制約 19・RANGE 4）。試験 `tests/test_schema_apply.py` 9 件、DB の試験 `tests/test_db_new_live.py` に 1 件 |
| N-20 | ゲートの書き込み：未確定で書き、AuditLog を残す。禁忌と聞いた記録（D5）、食い違いの保留。既にある禁忌に結ぶのは人の指定だけ | 自動でまとめない。結ぶ指定が無ければ新しい禁忌（未確定） | ✅ 2026-11-05 `nest/gate/write.py`（`submit`・`link_evidence`）・`nest/gate/bootstrap.py`。試験 `tests/test_gate_write.py` 16 件、DB の試験 `tests/test_gate_write_live.py` 9 件。台帳 G-52 |
| N-21 | 承認の操作（D9）：書き込みとは別の操作、引用を並べて見せる、AI 由来の一括の承認を拒否、AuditLog | 一括の承認で失敗する。承認の AuditLog が残る | ✅ 2026-11-05 `nest/gate/approve.py`（`approve`・`reject`・`approve_many`・`review_items`）。試験 `tests/test_gate_approve.py` 13 件、DB の試験 `tests/test_gate_approve_live.py` 5 件。台帳 G-53 |
| N-22 | 読み取りだけの MCP の包み（個人の側と資源の側の両方）。**改善の論点（2026-11-06 河原さん。台帳 G-64）：項目名の検査を語の単位にする（今は部分一致。`ADDRESSES` が `address` に当たった）。今は緩めない。****できたら `.mcp.json` に新しい項目として入れ直し、`tests/test_mcp_config.py` を改める**（N-05b で外した。台帳 G-35 の 2）。`apoc.*` の手続きは許可の一覧に入れない。手本は tsunagu-net の枝 `claude/tender-dijkstra-xo3wwc` のコミット `d8e6e2d` の `tsunagu/mcp_resource.py`（main に未収録。main に入ったら参照先を書き換える）。手本から持ち込むもの：(1) EXPLAIN の種類が r でなければ拒否 (2) 種類が r でも計画に LOAD CSV があれば拒否 (3) 手続きの呼び出しは許可の一覧（`db.labels`・`db.relationshipTypes`・`db.propertyKeys`）だけ (4) 計画が読めないときは閉じる側に倒す (5) 返す行数の上限 500 と読み取りのトランザクション。強めるところ（2026-11-05 河原さん）：歯止めは EXPLAIN の判定の側に置き、`routing_="r"` は保険とする。行数は全部を受け取ってから切らず、結果を流しながら 500 行で止める（Cypher に LIMIT を差し込まない）。EXPLAIN・PROFILE つきと空も拒否。個人の側は、同じ形に、実名・かな・電話・住所・生年月日の伏せ字を足したもの（2026-11-05 河原さん）。`.mcp.json` から `neo4j-shared` を外す。注記：手本の (5) は `routing_="r"`（読み取りの経路）で、tsunagu-net G-14 のとおりアクセス制御にはならない。行数は全部を受け取ってから切っている | 書き込み・スキーマの変更・LOAD CSV・許可外の手続き・読めない計画・EXPLAIN つき・空を、実行前に拒否する（手本と同じ例）。行数が 500 を超えない。個人の側の既定の結果に実名・かな・電話・住所・生年月日が無い **`Residence.address` も返さない**（`areaCode` と `since`・`until` は返してよい。正典 v0.5。台帳 G-43・G-44）。**決める論点：台帳 G-42**（引用の伏せ字、呼び名から仮名への入口）。決めたら `docs/external-api.md` の NEXT-02 の行も直す | ✅ 2026-11-05 `nest/mcp_guard.py`・`nest/mcp_personal.py`・`nest/mcp_resource.py`、`.mcp.json` に二つ（`nest-personal`・`nest-resource`）。依存に `mcp==2.3.0`（tsunagu-net と同じ版。Socket の点数 98〜100）。試験 `tests/test_mcp_guard.py` 54 件・`tests/test_mcp_config.py` 2 件、DB の試験 `tests/test_mcp_read_live.py` 37 件。G-42 は決めていない（引用の中の名前は伏せていない）。台帳 G-54。**済みの条件に足した（2026-11-06 河原さん。台帳 G-54 (3)・G-42）**：個人の側の包みは、NEXT-02 の設定と記録がそろうか、架空の印（`NestLiveProbe`）のある DB のときだけ動く。原文全体（`text`）を返さない、引用は `read_quote` でだけ 200 字まで、名前を受け取る道具が無い。✅ 2026-11-06 `tests/test_mcp_personal_gate.py` |
| N-23 | 資源 DB の読み込み（D2）：版と指紋（`MANIFEST.json`）の記録。資源の側への書き込みはこの道具だけ | 指紋が合わない書き出しを拒否する | ✅ 2026-11-05 `nest/resource_load.py`・`scripts/load_resource.py`（既定は手順を出すだけ）。資源の側の MCP に `resource_version`。`~/Dist/tsunagu-net-trial-20261104` の書き出し（2026-11-04-2011、SHA-256 `eeee7511…`、一式の正典 v0.29）を読み込んだ。機関 4,358。試験 `tests/test_resource_load.py` 16 件、DB の試験 `tests/test_resource_load_live.py` 3 件。台帳 G-55。**写しの更新の手順（2026-11-06 河原さん。台帳 G-50）**：(1) tsunagu-net の新しい配布の一式（`MANIFEST.json` と資源 DB の書き出し）を `~/Dist/` に置く (2) `uv run python scripts/load_resource.py --bundle <一式のフォルダ>` で指紋と手順を確かめる（既定は流さない） (3) `--write` を付けて流す。資源の側（`nest-redesign-resource`、38687）だけを止めて置き換え、また起動する。個人の側には触れない (4) 資源の側の MCP の `resource_version` で、読み込んだ版と指紋を確かめる。指紋が合わない書き出しは読み込まない。tsunagu-net の動いている資源 DB（17687）からは取らない |
| N-24 | 機関の候補（D3）：原文の名前から候補を出し、人が `orgId` を選ぶ。選ぶまでは機関未確定 | 名前の一致だけで `orgId` を入れる案で止まる | ✅ 2026-11-05 `nest/org_candidates.py`（`by_name`）。取り込みの案は原文の名前（`providerName`）だけを書き、職員が選んだ機関 ID を `provider_org_id` で渡す。試験 `tests/test_org_candidates.py` 14 件・`tests/test_intake.py` を改めた、DB の試験 `tests/test_org_candidates_live.py` 4 件。台帳 G-56 |
| N-24a | **担当機関の推定**（2026-11-05 河原さん）：語りの「区役所の窓口で」のように機関の名前が無い言及を、本人の住所の区で資源 DB の候補に絞り、Claude が確度 `Inference` で `Involvement` の案を作れるようにする。埋め込みは使わない（文の近さでは区を選べない。選ぶ根拠は住所）。手順：(1) ゲートが本人の住所を 6 桁の団体コード（区）に変える。住所そのものは外に出さない (2) 資源 DB で「その区を担当する機関のうち、種類が障害・高齢・生活困窮などの相談窓口のもの」を `SERVES` と `Area` で引く。担当の根拠の種類（`servesBasis`）を候補に添え、格上げしない（tsunagu-net BRS-23） (3) Claude には候補の一覧（`orgId` と名前。公開情報）だけを渡す。区コードも住所も渡さない。Claude は語りの文脈で候補から選び、確度 `Inference` で案を作る。絞れなければ機関未確定のまま候補を添える (4) 推定は `Pending`。職員が承認して初めて確定する（N-21）。規則（`docs/SEMANTICS.md` に書く）：過去の言及は当時の住所の区で推定する。当時の住所が記録に無ければ今の住所で推定し、その旨を案に書く／窓口の粒度で絞れないときは区役所の単位で止め、窓口は未確定にする。間違った窓口を確定させない。手本：tsunagu-net の枝 `claude/tender-dijkstra-xo3wwc` のコミット `d8e6e2d` の担当地区・担当区域（`SERVES`・`servesBasis`、SEMANTICS BRS-22・23）。読むだけ。本人の住所は `Residence`（正典 v0.4。台帳 G-43）。住所から団体コードを出すのはゲートの登録のとき（手元の総務省の市区町村コードの表と市区町村名の文字列の一致。外に送らない。一致しなければ空にして機関未確定）。表を同梱し、出どころと版を SEMANTICS か README に書く | 候補の一覧に区コード・住所が入らない。担当区域の外の機関が候補に出ない。窓口で絞れないとき窓口を確定しない。過去の言及で当時の住所が無いとき、今の住所で推定した旨が案に入る。推定の案が `Pending` で、確度が `Inference` | ✅ 2026-11-05 `nest/area_code.py`（住所→団体コード。表 `nest/data/area-codes-kitakyushu-2026-10-25.json` は tsunagu-net から写した。指紋を読むたびに確かめる）、ゲートが `Residence.areaCode` を住所から出す（依頼の値が食い違えば止める）、`nest/org_estimate.py`（`residence_for`・`by_area`・`estimate`・`for_claude`）、`intake.check` の `involvements` と `estimate`。規則と表の出どころは `docs/SEMANTICS.md`（SEM-AREA-01〜04。この行で新しく作った）。試験 `tests/test_org_estimate.py`・`tests/test_intake_involvement.py`・`tests/test_gate_write.py` に 5 件、DB の試験 `tests/test_org_estimate_live.py` 5 件。`tests/test_mcp_read_live.py` の架空の住所を表に合う形に直した（`areaCode: 999999` はゲートが止めるようになったため）。台帳 G-57 |
| **止まる点 4** | 架空の語りで、取り込み→点検→未確定→承認→照会を通して見せる | | |

## 段階 E　スキルと文書

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-24b | 任意後見・任意代理を tsunagu-net の BRS-49 に合わせる（2026-11-06 河原さん。台帳 G-62） | 5 つの後見の類型・`AgencyContract`・`Transitioned` が正典にあり、`Transitioned` は受任者の段階と任意代理だけ通る（架空の依頼で両向き） | ✅ 2026-11-06 正典 v0.8、SEMANTICS SEM-GUARD-01・02、`nest/gate/validate.py`、試験 `tests/test_voluntary_guardianship.py` 16 件 |
| N-20a | **確認の記録（Review）をゲートの操作で作る**（2026-11-06 河原さん。止まる点 E-1）：`Review` を作り、`CONFIRMS` で対象の記録に結ぶ。職員の ID・確かめた日・`reviewDomain` を必須にする。人が確かめた記録なので AI 由来にしない。入口の案には入れない | 必須の欠け・AI 由来・案からの作成で止まり、そろえば `Active` で書かれる（DB なしと DB つき） | ✅ 2026-11-06 `write.review_request`・`write.record_review`、validate の `_check_review`。試験 `tests/test_gate_review.py`（DB つきは `test_gate_write_live.py` に。E-2 で流す） |
| N-25 | narrative-extractor の書き直し：書き込みの案（JSON）を出すだけ。Cypher の書き込みと、名前の統合の指示を消す | 案の例がゲートを通る（架空） | ✅ 2026-11-06 SKILL.md を書き直し、架空の例が入口の点検とゲートを通る（全部 Pending）。試験 `tests/test_narrative_extractor_skill.py`。禁忌・推奨ケアの案の道は無い（G-63） |
| N-26 | EXTRACTION_PROMPT の書き直し：原文に無い値で埋める指示を消す | — | ✅ 2026-11-06 埋める指示と前の正典の形を消し、案の形は narrative-extractor の SKILL.md に一本化した。試験 `tests/test_extraction_prompt_doc.py`（計画では試験なしだったが足した） |
| N-27 | 読み取りのスキル（neo4j-support-db・visit-prep・emergency-protocol・data-quality-agent・resilience-checker・onboarding-wizard・ecomap-generator・insight-agent）の照会を新しい正典に合わせる。スキルごとに 1 行に分ける。列挙値の日本語の表示名は `docs/SEMANTICS.md`（N-24a で担当機関の推定の節だけを持って作った。列挙値の節をここで足す。正典 v0.2 §1）から引く。**`SEMANTICS.md` を作ったら、コードの中の日本語名（`nest/gate/validate.py` の `CERTAINTY_JA` など）もそこから読む形に変える**（台帳 G-47。2026-11-05 河原さん） | 照会のテンプレートを正典の JSON と突き合わせる検査 | ✅ 2026-11-06（列挙値の表示名とコードの読み方の部分）`docs/SEMANTICS.md` SEM-ENUM-01・02、`nest/semantics.py`。validate の `CERTAINTY_JA`・intake の `WEAKEST_FIRST` をそこから読む。試験 `tests/test_semantics_enums.py`。スキルは下の 8 行 |
| N-27a | `neo4j-support-db` の照会を新しい正典に合わせる | 照会のテンプレートを正典の JSON と突き合わせる検査（`tests/test_read_skills_canon.py`） | ✅ 2026-11-06 読むだけ・仮名で照会・照会 15 本。`reference/use-cases.md` は外した |
| N-27b | `visit-prep` の照会を新しい正典に合わせる | 照会のテンプレートを正典の JSON と突き合わせる検査（`tests/test_read_skills_canon.py`） | ✅ 2026-11-06 照会 4 本＋資源の側 1 本。電話番号は出せないので連絡網で確かめると書いた |
| N-27c | `emergency-protocol` の照会を新しい正典に合わせる | 照会のテンプレートを正典の JSON と突き合わせる検査（`tests/test_read_skills_canon.py`） | ✅ 2026-11-06 照会 3 本＋資源の側 1 本。氏名・住所・年齢・電話は出せないことを出力の頭に書く |
| N-27d | `data-quality-agent` の照会を新しい正典に合わせる | 照会のテンプレートを正典の JSON と突き合わせる検査（`tests/test_read_skills_canon.py`） | ✅ 2026-11-06 点検 8 種。埋め込みを使う重みの一貫性の点検は外した |
| N-27e | `resilience-checker` の照会を新しい正典に合わせる | 照会のテンプレートを正典の JSON と突き合わせる検査（`tests/test_read_skills_canon.py`） | ✅ 2026-11-06 照会 3 本＋資源の側 1 本。登録の Cypher と事業所の候補探しは外した |
| N-27f | `onboarding-wizard` の照会を新しい正典に合わせる | 照会のテンプレートを正典の JSON と突き合わせる検査（`tests/test_read_skills_canon.py`） | ✅ 2026-11-06 登録の Cypher を外し、聞き取りの案内と登録の状況の照会 2 本にした。本人の作成は Claude の外。確認（Review）を作る手順が無いことを書いた |
| N-27g | `ecomap-generator` の照会を新しい正典に合わせる | 照会のテンプレートを正典の JSON と突き合わせる検査（`tests/test_read_skills_canon.py`） | ✅ 2026-11-06 照会 2 本＋資源の側 1 本。Claude が Mermaid の図にする。D3 の HTML・感情のグラフ・Python の部品（前の DB につながる）と、その試験 2 本は外した |
| N-27h | `insight-agent` の照会を新しい正典に合わせる | 照会のテンプレートを正典の JSON と突き合わせる検査（`tests/test_read_skills_canon.py`） | ✅ 2026-11-06 照会 5 本。感情の推移と、前の分析の部品の呼び出しは外した。閾値は決めず数字を出す |
| N-27i | `provider-search` を資源の側の読み取りの包み（`nest/mcp_resource.py`）を通す形に直す（2026-11-06 河原さん。河原さんは N-27b と書いたが、N-27b は visit-prep に使っていたので i にした） | 照会のテンプレートを資源の側の形と突き合わせる検査 | ✅ 2026-11-06 provider-search を資源の側の読み取りに。口コミ・書き込みを外した。試験 test_read_skills_canon.py（9 本）。台帳 G-65 |
| **止まる点 E-1** | N-27 の後（2026-11-06 河原さん）。スキル 8 本それぞれの「何を消し、何を足したか」を 1 行ずつ報告し、河原さんが全部見る。DB の試験を一度流し（N-18 の条件。終わったら down）、G-63 の候補が Pending で書かれることを確かめる | | |
| N-28 | SOS の中身（D11-3）：LINE には SOS・誰のことか・位置・確かめる先だけ | 送る文に電話と禁忌が無い | ✅ 2026-11-06 LINE の文は SOS・仮名・時刻・位置・確かめる先だけ。DB を読まない。試験 tests/test_sos_message.py（5 件）。external-api v0.7。台帳 G-66 |
| **止まる点 E-2** | N-28 の後。LINE の SOS で送る文の形（架空の例）と external-api の NEXT-05 の直しを見ていただく | | |
| N-29 | 文書を直す：PRIVACY_GUIDELINES（条番号は e-Gov で照合）・CLAUDE.md・README・QUICK_START・SETUP_GUIDE・manifesto の共有層と 7687 の記述（付録の表）。**面談の音声ファイルの置き場所と保存の期間**を運用の文書に書く（DB には持たない。正典 v0.2 §4.2） | — |  ✅ 2026-11-06 行に名前のある文書を今の構成に合わせて書き直した。SETUP_GUIDE.html を外した。音声ファイルの節（保存の期間は【未決】）。条は e-Gov で照合。試験 tests/test_docs_new_setup.py。台帳 G-68 |
| N-30 | `doctor.sh` を新しい構成に合わせる | doctor.sh が新しい構成で全項目を通る |  ✅ 2026-11-06 doctor.sh を新しい構成の点検に（前の DB・待ち受け・設定の権限・.mcp.json・スキルのリンク・正典のずれ）。試験 tests/test_doctor.py（偽の HOME と docker）。台帳 G-69 |
| **止まる点 E-3** | 段階 E の終わり | | |
| N-31（任意） | エコマップの動く図：DB につながず、Claude が出した Mermaid か JSON を読むだけの描画の部品（2026-11-06 河原さん。要るときだけ） | 描画の部品が DB・ネットワークにつながらない | |
| N-32 | 本人のデータの廃棄の手順（2026-11-06 河原さん）。tsunagu-net の保存の判断（`RetentionDecision`。tsunagu-net `docs/SCHEMA.md` v0.29〜0.30、`docs/proposals/2026-11-05-purge-draft.md`、`scripts/retention_due.py`、`tests/test_gate_purge.py`）を手本に読む。廃棄は未確定（Pending）を経ず、人の操作だけで行い、操作の記録（AuditLog）に残す。正典に足すラベル・項目は河原さんの承認を得てから | 架空のデータで：廃棄が AI の案からは通らない・人の操作だけで消える・AuditLog が残る・ほかの本人に触れない | 段階 F の止まる点で決める |
| N-33 | 個人の側の DB のバックアップの手順（2026-11-06 河原さん。河原さんは N-31 と書いたが、N-31 はエコマップの動く図に使っていたので 33 にした）。置き場所は Mac の中、権限 700、Time Machine の対象外。外のサービスには置かない（`docs/external-api.md` に行を足さない） | 架空のデータで、取る・戻すの両方。置き場所の権限が 700、Time Machine の除外が付いている | 段階 F の止まる点で決める |

## 段階 F　決めごとと、前の構成の置き換え（2026-11-06 河原さん承認）

- 順：N-34 → 止まる点 F-1 → N-32・N-33 → N-35 → N-36・N-37 → 止まる点 F-2 → N-38 → 止まる点 F-3。N-31（任意）は段階の外のまま
- F-1 で河原さんが決めること：音声の保存の期間、バックアップの置き場所と周期、廃棄の手順、前の DB の処分（N-05a）と中身を新しい DB へ移すか、正典に足すラベル。N-34 では、それぞれ案を一つに絞って理由を添える
- 前の DB は起動しない。tsunagu-net は変えない（読むだけ）

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-34 | F-1 の材料をそろえる：(1) 音声の保存の期間・バックアップの置き場所と周期・廃棄の手順（tsunagu-net の保存の判断 `RetentionDecision` を読む）・正典に足すラベルの案を、それぞれ一つに絞り理由を添える。(2) N-05a の材料：前の DB（コンテナ・`neo4j_data/`）・`neo4j_backup/`・生活困窮者支援の跡（`neo4j_livelihood_*`）・`.quarantine/`・`~/nest-support-hold/` の .bak・`~/.config/nest/neo4j.env` の一覧と、それぞれ「消す／移す／残す」の案。**中身は開かない**（名前・種類・大きさ・日付だけ）。前の DB の中身を新しい DB へ移すかの案も出す | — | ✅ 2026-11-06 `docs/proposals/2026-11-06-f1-decisions.md`（案を一つずつ、理由と却下した案つき。前の DB の跡は名前・大きさ・日付だけを見た。台帳 G-73） |
| **止まる点 F-1** | N-34 の案を河原さんが決める（音声の保存の期間、バックアップ、廃棄、N-05a、移すか、正典のラベル）。移すと決めたら、ゲートを通る形の行を別に足す | | ✅ 2026-11-06 河原さん：6 項目とも案のとおり、条件つき（台帳 G-74）。前の DB の中身は移さない |
| N-32a | 正典 v0.11：`RetentionDecision`・`DECIDES_ON`（→ Client）・`retentionDecision`（Keep・Delete）・`auditAction` の `Purge`・`AuditLog` の `retentionId`・`purgedCounts`・`keptPersons`。名前は tsunagu-net とそろえる（F-1 承認） | 正典の表と JSON がそろう（check_drift）。§10 にそろえた名前の行 | ✅ 2026-11-06 正典 v0.11（接頭辞 `RTD`、§3・§4・§10・§11・変更履歴）。SEMANTICS に表示名 3 つ。`nest/ids.py` に `RTD`。試験 `tests/test_canon_v011_retention.py`（5 件）。ずれ 0 件 |
| N-32 | 本人のデータの廃棄の手順（F-1 の決定どおり。`docs/proposals/2026-11-06-f1-decisions.md` の 3） | 上の N-32 の行のとおり。加えて：**保存の判断（`RetentionDecision`、値が `Delete`）が本人に結ばれていなければ、試しの実行でも動かない**。**試しの実行で、その本人の記録のうち他の機関から受け取ったもの（`PROVIDED_BY` あり）の件数を出す**（消してよいかは人が見る）。仮名の打ち返し・Administrator だけ・Purge の監査ログ 1 件・ほかの本人にもつながる人は残る | ✅ 2026-11-06 保存の判断はゲート（`write.record_retention`。Human だけ・Administrator だけ・本人一人に DECIDES_ON）。消す道具 `nest/gate/purge.py` と `scripts/purge_client.py`（decide・purge）。試験 `tests/test_purge.py`（11 件）・`tests/test_purge_live.py`（7 件、DB つき 939 passed）。PRIVACY §5 に手順 |
| N-33 | 個人の側の DB のバックアップの手順（F-1 の決定どおり。`~/nest-backup/`、DB を止めてから、4 世代）。`scripts/backup.sh` を置き換える | 上の N-33 の行のとおり。加えて：**戻す試験は架空のデータで、戻した後に正典のずれが 0 件**。**doctor.sh が、`~/nest-backup/` の権限 700・Time Machine の対象外・FileVault が有効（`fdesetup status`）を点検する**（バックアップは要配慮個人情報の写し。外のサービスに置かない） | ✅ 2026-11-06 `nest/backup.py`・`scripts/backup.py`（dump・list・restore）。`scripts/backup.sh` を外した。doctor.sh に [7] FileVault・[8] 置き場所。試験 `tests/test_backup.py`（11 件）・`tests/test_doctor.py`（+5 件）・`tests/test_backup_live.py`（取る→使い捨てのコンテナに戻す→ずれ 0 件。DB つき 957 passed）。試験の途中で、Neo4j が匿名の利用の情報を送っていたのを見つけて止めた（台帳 G-75） |
| N-35 | 認証の部品 `lib/auth.py` を `nest/` に移す | sos・field-ui の認証の試験がそのまま通る | ✅ 2026-11-06。`nest/auth.py` に移し（中身は変えない）、sos・field-ui は `nest.auth` から読む。`tests/test_auth.py` に移した先の試験を足し、`tests/test_service_imports.py` は `nest.` からの読み込みも確かめる |
| N-36 | sos を作り直す：本人の入口は仮名（`displayCode`）だけで受け、名前を返さない。読むのは読み取りの包み | 503 の試験を「仮名だけ・名前を返さない」形に直す。**LINE の送信が NEXT-05 の歯止め（`nest.egress`）を通ること**（今は `egress.ensure("NEXT-05", …)` で通っている。置き換えの後も通ることを試験で固定する） | ✅ 2026-11-06。入口は仮名だけで受け、仮名と「いるか」だけを返す（名前を返さない）。読むのは `lookup_client` で、読み取りの包み（`require_personal_allowed`・`run_read`）を通す。sos は DB に直につながない。アプリは `?name=` を受けず、仮名だけを出す。試験：`tests/test_sos_response.py`（503 の試験を置き換え）・`tests/test_auth.py`・DB つき `tests/test_sos_live.py`。NEXT-05 は `tests/test_egress_line.py` のまま通る。台帳 G-76 |
| N-37 | field-ui を作り直す：読むのは読み取りの包み、登録は書き込みの案をゲートで通す。録音の画面は外部送信の一覧の NEXT-03 の行に合わせる。**音声の置き場所を nest のデータの下に固定し、文字起こしの記録が承認されたら消す・遅くとも 30 日で消す。消しても `Record.documentHash` は消さない**（F-1） | 新しい DB を直に書かない。**doctor.sh が音声の置き場所の権限 700・Time Machine の対象外を点検する**。消す道具が承認済みと 30 日過ぎを消し、`documentHash` を残す。**録音の文字起こしが NEXT-03 の歯止めを通ること**（今は `lib/genai.py` が `egress.authorize("NEXT-03")` で通っている。置き換えの後も通ることを試験で固定する） |✅ 2026-11-06。職員ごとのトークン（`nest/auth.py`・`scripts/staff_token.py`）、読むのは `read_personal`（包み）、支援記録は `submit_to_gate`（origin Human）、ダッシュボードは閉じる（503）。音声は文字起こしの sha256 の名前で `nest_voice_data/`（700・Time Machine の対象外・doctor.sh [9]）、消す道具 `scripts/purge_voice.py`（承認済みと 30 日過ぎ。documentHash は残す）。NEXT-03 は `tests/test_no_structurize.py` で固定。DB つき `tests/test_field_ui_live.py`・`tests/test_voice_live.py`。台帳 G-77 |
| **止まる点 F-2** | sos と field-ui の画面と、送る中身を見ていただく | | |
| N-38 | 前の構成の残りを外す：`lib/` の残り・`setup.sh`・`setup.ps1`・`installer/`・`scripts/rotate_password.py`・`scripts/multi_importer.py`。`lib/genai.py` は `nest/` へ移す（台帳 G-30） | `tests/test_old_db_code_isolated.py` を「無いこと」を確かめる形に変える。**新しい Mac でゼロから動かす手順が `docs/SETUP_GUIDE.md` にあり、`scripts/doctor.sh` がその手順の結果を点検できる**（docker compose と、人が作る `~/.config/nest/` の設定のファイル。権限 600）。配布物（インストーラー）は作らない。要るなら段階 G の論点 | ✅ 2026-11-06：`lib/genai.py` を `nest/genai.py` へ移し、残りの `lib/`・`installer/`・`setup.sh`・`setup.ps1`・`scripts/rotate_password.py`・`scripts/multi_importer.py` を消した。`tests/test_old_db_code_isolated.py` は無いことを確かめる。`docs/SETUP_GUIDE.md` に「0. 新しい Mac でゼロから」（`tests/test_docs_new_setup.py` が順を確かめる）、最初の管理者の入口 `scripts/bootstrap_admin.py`、doctor.sh [3] に `~/.config/nest/` のほかの設定のファイル（あれば 600）。台帳 G-78 |
| **止まる点 F-3** | 段階 F の終わり | | ✅ 2026-11-06 河原さん：段階 F を閉じる。N-38・G-78（条件 2 つ）・G-77 の直し（順を変える）・HANDOVER を承認 |

## 段階 G　実データを入れる前の入口（2026-11-06 河原さん）

- 順：DB つきの試験を一度流す（N-38 の後に流していないため。N-18 の条件どおり、終わったら down）→ N-39 → 止まる点 G-1
- 前の DB は起動しない。tsunagu-net は変えない（読むだけ）

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-39 | 本人を Claude の外で作る入口 `scripts/new_client.py`。職員が手元で打ち、ゲートを通して本人（Client）と住まい（Residence、RESIDES_AT）を作り、仮名（displayCode）を発番して画面に出す。実名・かな・生年月日・住所は DB に入れてよい（包みが返さないだけ）。Claude には何も渡さない。同じ道具で、名前から仮名を引く（台帳 G-42 (2) の「Claude の外の入口」） | 架空のデータで：作る（仮名が出る・ゲートの監査ログが付く）・引く（名前から仮名）・二重登録を止める | ✅ 2026-11-06 `scripts/new_client.py`（add・find）。試験 `tests/test_new_client.py`（DB なし 6 件）・`tests/test_new_client_live.py`（DB つき 6 件）。その前の DB つきの試験 958 passed。台帳 G-79 |
| **止まる点 G-1** | 実データを入れる前の最後の確認：契約の確認の記録・機能の設定・NEXT-02 の歯止め・doctor の FAIL 0 | | ✅ 2026-11-06 河原さん：写し 3 件をコミットしてよい。契約の確認の記録はまだ作らない（台帳 G-80）。N-05a は河原さんが打った |

## 段階 H　運用の始め方（2026-11-06 河原さん）

- 順：N-40 → N-41 → N-42 → 止まる点 H-1
- 文書の行は、doctor との対応表があることなどを試験で確かめる。試験を先に書き、赤を確かめてから緑にする
- 前の DB は起動しない。tsunagu-net は変えない

| # | タスク | 先に書く試験 | 済みの判定 |
|---|---|---|---|
| N-40 | 運用の手順書 `docs/OPERATIONS.md`。相談支援の職員が上から順に読んで動かせる一本の手順：管理者の作成（bootstrap_admin）、職員のトークンの発行（staff_token）、本人の登録（new_client）、支援記録の入力（field-ui）、音声の扱い（録音から文字起こし、purge_voice）、バックアップの周期と戻し方（backup）、本人の廃棄（purge_client）、doctor の流し方と WARN・FAIL の読み方。各段に doctor のどの項目で点検できるかを横に書く。点検できない段は、doctor に項目を足すか「人が確かめる」と書く | 手順書に各段があり、段ごとに doctor の項目か「人が確かめる」が書いてある。書いた doctor の項目が doctor.sh に実在する。書いたコマンドの道具が実在する | ✅ 2026-11-06 `docs/OPERATIONS.md`（9 段と「段と点検の対応」）。試験 `tests/test_docs_operations.py`（13 件）。doctor に項目は足していない。台帳 G-81 |
| N-41 | 契約の確認の記録と機能の設定の作り方 `docs/EXTERNAL_API_SETUP.md`：記録の 5 項目の書式（JSON の鍵と例）、置き場所と権限（`~/.config/nest/`、600）、NEXT の行ごとに分けること、次に確かめる日、機能の設定の書式、doctor での確かめ方、作った後に `egress.authorize` で通ることを確かめる方法。記録の中身（契約の内容）は河原さんが書くので入れない。先頭に「記録を作る前に確かめること」の節を置き、台帳 G-80 の内容を書く | 先頭の節に G-80 の内容がある。手順書の例の JSON を一時の置き場所に置くと `egress.authorize` が通り、鍵が一つ欠けると止まる  | ✅ 2026-11-06 `docs/EXTERNAL_API_SETUP.md`。試験 `tests/test_docs_external_api_setup.py`（8 件）。例は NEXT-03 で、文字の項目は〈…〉、日付は YYYY-MM-DD のままでは通らない。台帳 G-82 |
| N-42 | SEMANTICS の条番号の照合：手帳・受給者証（`certificateType`）と年金・手当（`publicAssistanceType`）の根拠の法令と条番号を e-Gov で照合し【未照合】を外す。照合できなかったものは【未照合】のまま理由を書く | 二つの表に【未照合】が理由なしで残っていない | |
| **止まる点 H-1** | 河原さんが N-40・N-41 の手順書を読む。`redesign/adr-001` を main に合流させるかを河原さんが決める（Mac は合流しない） | | |

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
| `lib/schema_validator.py` | `VALID_NODE_LABELS_7687` などの名前（中身は個人層） | N-17（ファイルごと外した。台帳 G-49） |
| `lib/embedding.py` | agno 由来のベクトル索引名の分岐 | ✅ N-04 でファイルごと外した |
| `lib/db_operations.py`・`scripts/migrate_*.py`・`claude-skills/ecomap-generator/scripts/generate_mermaid.py` | 「`neo4j.env`（共有層 7687）より個人層を優先する」読み込みの順 | N-29（`migrate_*` は外す候補） |
| `sos/.env.example` | `NEO4J_URI=bolt://localhost:7687` | N-28 |
| `scripts/rotate_password.py`・`scripts/backup.sh`・`scripts/doctor.sh` | 共有層 7687 の説明と除外 | N-30 |
| `.env.example`・`README.md`・`docs/QUICK_START.md`・`docs/SETUP_GUIDE.md`・`docs/SETUP_GUIDE.html`・`docs/PRIVACY_GUIDELINES.md`・`CLAUDE.md`・`manifesto/MANIFESTO.md`・`manifesto/protocols/emergency.md`・`onboarding.md`・`docker-compose.yml` の注記 | 共有層・7687・neo4j-agno-agent の記述 | N-29 |
| `tests/test_db_module_consolidation.py` | neo4j-agno-agent のファイルの場所への言及 | N-17 |
| `~/Dev-Work/shared-schema/sync-schema.sh`（リポジトリの外） | `--write-prod` で nest-support の `docs/` に書き込む | 変えない（ADR 未決論点 3） |
