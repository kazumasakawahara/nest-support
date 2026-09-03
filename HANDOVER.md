# HANDOVER — 2026-07-13 main（grade=不明 検出の追加 / セッション5・完）

> NEXT_SESSION.md（grade=不明 検出・2026-07-13 発行）に基づく小規模セッション。
> タスク A（正典 §10.3 の明文化）・B（data-quality-agent への検出追加＋実DB読み取り検証）・
> C（claude.ai への skill-sync）すべて完了。DB への書き込みなし（読み取りのみ）。
> 指示書は役目を終えたため削除済み。
> 前セッション（DRIFT-12 解消・チェッカー四者化）は git 履歴の HANDOVER を参照。

## 再開コマンド（コピペで動く・本セッション末に検証済み）

```bash
cd ~/Dev-Work/project/nest-support
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

./scripts/doctor.sh                              # 環境整合（検証済み: 20 passed / 0 failed）
uv run python scripts/check_semantic_drift.py    # 四者一致（検証済み: OK=29 KNOWN=0 FAIL=0 WARN=1）
uv run pytest tests/ -q                          # 全テスト（検証済み: 173 passed）
```

Neo4j（support-db, port 7687）は稼働中。コンテナ名は `nest-support-neo4j`。

---

## 現在地

- 目標: DRIFT-12 で入った「grade 未指定→"不明" 補完」の構造的副作用
  （実等級判明後に "不明" ノードが残骸として残る）を data-quality-agent が検出できるようにする。

### 進捗

- [x] **A: 正典 §10.3 の記載検証と明文化** — 検証結果:「grade 未指定は "不明"」の一言は
  **実在した**が、補完の意図・意味・検出の記載は無かったため追記。
  SCHEMA_CONVENTION **v3.3.2**: (1) 補完の意図＝複合 MERGE キーの欠落防止、
  (2) "不明"＝「等級を把握していない」であって「等級が無い」ではない（BRS-04）、
  (3) data-quality-agent が欠損として検出する旨。→ sync-schema.sh 済み・drift green 維持
- [x] **B: data-quality-agent に Check 1b を追加**（期限アラート Check 1 の直後に配置）
  - (a) 等級未把握（Warning）: grade="不明" の Certificate 列挙。
    表示原則「**等級なし」と書かない**——「等級未把握——本人・家族・手帳現物で確認を」
  - (b) 残骸候補（Warning）: 同一クライアント・同一 type で "不明" と具体的等級の併存を検出。
    **検出と提案まで**（削除は河原氏の承認と AuditLog を伴う手動作業へ誘導。自動削除なし）
  - 診断項目一覧の表にもカテゴリ行を追加
- [x] **B: 実DB読み取り検証（2026-07-13・nest-support-neo4j）**
  - 構文: 両クエリとも EXPLAIN 通過（読み取りのみ・書き込みなし）
  - 該当件数: **(a) 0件・(b) 0件（機構は今後の発生を監視）**。
    参考: Certificate は全8ノード・すべて等級設定済み・grade IS NULL も0件
    ——既存データに移行負債は無く、検出は「今後 "不明" 補完が使われた時」に効く
- [x] **C: claude.ai へ skill-sync 完了** — 置き換えアップロード成功。
  一覧の最終更新日が 2026/07/13 になったことに加え、**中身**（詳細画面の DOM に
  「Check 1b」「等級未把握」「残骸候補」が存在）で新版を確認済み

## グレーな判断（次セッション冒頭で承認確認を）

1. **新チェックの番号を「Check 1b」とした**（指示書は配置裁量あり）。既存 Check 2〜7 の
   番号を動かさず、期限アラート（Check 1）の直後という文脈も保てるため。
2. **実DB検証は「EXPLAIN（構文）＋集計クエリ（件数）」の形式で行い、テンプレート
   そのままの実行（実名が返る形）はしなかった**。指示書の「読み取り実行して構文と挙動を
   確認」は満たしつつ、実在の方の氏名をチャット文脈に載せないため（pii-safe の出力規律）。
3. browser-harness が **0.1.4 → 0.1.5 の更新可能**を表示している。更新は skill-sync
   SKILL.md 記載の正規手順（stash→rebase→pop→再インストール→MCP側sync）が必要なため
   本セッションでは実施せず（同期作業自体は 0.1.4 で問題なく完了）。

## 未決論点（河原氏の判断が要る）

- 残骸候補 (b) が実際に検出された場合の**標準対応手順**（プロパティ引き継ぎ→不明ノード
  削除→AuditLog）を neo4j-support-db 側にテンプレート化するか。現状は data-quality-agent の
  誘導文のみ。発生実績が出てから設計でよい（0件のうちは急がない）。

## 既知の罠・注意

- **NEXT_SESSION.md 方式の罠**: 古い指示書が残ると処理済みタスクが再実行されかける。
  処理完了時に削除する運用（本セッションも削除済み）
- **auto mode classifier が Neo4j への CREATE を拒否する**。読み取り（EXPLAIN 含む）は通る
- **skill-sync の座標クリック**: claude.ai のスキル一覧で「追加」ボタンは DOM テキスト
  一致で拾えないことがある（テキストにアイコンが混じる）。スクリーンショット→座標クリック
  （viewport 座標 = スクリーンショット原寸の 1/2）が確実
- drift チェックの WARN=1 は既知（Review.domain/source はラベル限定検証のため対象外）
- rtk が git 出力を圧縮する。検証は `rtk proxy git log --format="%h parents:%p"`
- 本セッションと**無関係な未コミット変更**が作業ツリーに残っている:
  `docs/FAQ.md`（M）、`docs/COMPLETE_MANUAL.md/.html`・`docs/review-report-2026-05.html`・
  `docs/semantic-model-instruction.md`・`docs/家族聴き取りマニュアル.docx`（未追跡）。
  由来確認が済むまでコミットに巻き込まないこと

## 次タスク（優先度順）

### A: 必須
1. **前セッションのグレーな判断の承認確認**（Relative 逆向きスコープ実装・grade 補完・
   `nestLib` ブロック——セッション4）＋本セッションの判断1〜3
### B: 推奨
2. **C-6 の設計案レビュー**（narrative-extractor の「確認した」検出。セッション4 の
   HANDOVER に設計案あり——git 履歴 `ff52cc8` 時点を参照）。承認されれば合成データで試行
### C: 余裕があれば
3. DRIFT-09（呼称揺れ・旧関数名残存）の文書整理
4. browser-harness 0.1.5 への更新（正規手順で。CLI と MCP の2か所）

## Neo4j 認証の置き場（2026-09-04）

- Neo4j 認証の正典は `~/.config/nest/neo4j.env`（`NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` の3行、chmod 600）。各リポジトリの `.env` にはもう書かない（`NEO4J_LIVELIHOOD_*` は対象外で従来どおり `.env`）。
- `~/.zshrc` が `set -a` で読み込むので、シェルから起動するプロセスと `docker compose` の `${NEO4J_USERNAME}` / `${NEO4J_PASSWORD}` 展開はこれで賄う。未設定のまま `docker compose` を実行すると `:?` で止まる（`see ~/.config/nest/neo4j.env`）。
- パスワード変更は `project/nest-support/scripts/rotate_password.py`（`uv run python scripts/rotate_password.py`）。DB 側の `ALTER CURRENT USER SET PASSWORD` と正典ファイルの書き換えを一括で行い、値は表示しない。実行後は開いているシェルで `source ~/.config/nest/neo4j.env` し直す。
- compose の `NEO4J_AUTH` は初回起動時（データディレクトリが空のとき）にしか効かない。既存データの DB のパスワードは compose ではなく rotate_password.py で変える。
