# HANDOVER — 2026-07-13 main（DRIFT-12 解消・チェッカー四者化 / セッション4・完）

> NEXT_SESSION.md（DRIFT-12 修正・承認付き指示書）に基づくセッション。
> タスク A（lib 修正）・B（チェッカーの死角解消）完了、C-6 は指示どおり**設計案のみ**（下記）。
> DB への書き込みは一切していない（指示書 §1 厳守・検証は pytest で完結）。
> 指示書は役目を終えたため削除済み（古い指示書の再実行事故防止）。
> 前セッション（DRIFT-07/10 解消・A-1/A-2 の Review 登録）は git 履歴の HANDOVER を参照。

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

- 目標: DRIFT-12（nest `lib/db_operations.py` の正典未追従）の修正と、
  それが機械検出されなかった drift チェッカーの死角解消。

### 進捗

- [x] **A: DRIFT-12 修正（`lib/db_operations.py`）**
  - `MERGE_KEYS["Certificate"]` を `["type","grade"]` に修正（正典 §10.3）。
    grade 未指定は登録時に「不明」を補完（複合キーの欠落防止。agno・スキル前例と同じ）
  - `Doctor: ["name"]` / `Relative: ["name"]` / `Identity: ["name","dob"]` を追加
  - CareRole / Review / ProviderFeedback は**意図して MERGE_KEYS に入れない**
    （理由コメント付き。ENT-16 / ENT-24 / feedbackId 欠落時の登録喪失回避）
  - **Relative の逆向きスコープ対応を実装**（指示書 §2-3 の最善案を採用。下記「グレーな判断1」）
  - 正典台帳: DRIFT-12 を「✅ 解消（2026-07-13）」で登録、変更履歴 **v1.5**
- [x] **A: テスト** — `tests/test_merge_keys_canon.py` 新設（正典整合＋「無いことが正しい」の表明）、
  `tests/test_merge_scoping.py` に逆向きスコープ・複合キー・grade 補完の振る舞いテストを追加。
  **162 → 173 passed**（+11）
- [x] **B: drift チェッカーの死角解消** — `check_semantic_drift.py` に
  **④ nest lib の AST 照合**を追加（三者→四者）。正典 §6 に `nestLib` 正値ブロックを新設
  （mergeKeys 4件＋neverMergeLabels 3件）。**OK は 21 → 29 に増加**、KNOWN=0 / FAIL=0 /
  WARN=1（既知の Review.domain/source ラベル限定検証、従来どおり）
- [x] **C-6: 設計案の作成（実装はしていない）** — 下記「C-6 設計案」参照
- [ ] DRIFT-09（呼称揺れ・旧関数名残存）— 今回も見送り（裁量範囲だが独立作業のため）

## グレーな判断（次セッション冒頭で承認確認を）

1. **Relative のスコープ方式: 逆向きリレーション対応を実装する側を選んだ**
   （指示書 §2-3 は「小さく実装できるならそれが最善／膨らむなら常時 CREATE」の二択）。
   実装は小さく収まった: `_build_parent_link()`（新設ヘルパー・両方向解決）＋
   `_register_graph_tx` の向き復元と MERGE パターンの分岐、計 約25行。
   これにより Relative は client スコープの MERGE になり、
   **別クライアントの同姓同名家族の収斂を防ぎつつ再登録の冪等性も確保**
   （両方をテストで固定済み）。
2. **Certificate の grade「不明」補完を lib 登録経路にも実装した**（指示書 §2-2 に明示は
   なかったが、正典 §10.3 の「grade 未指定は "不明"」の一部であり、補完なしでは
   複合キーが type 単独に退化して修正の意味が薄れるため）。
3. **正典 §6 の機械検証ブロックに `nestLib` キーを新設し、名称を「三者一致」→
   「四者一致」に変更した**（チェッカーが正値をハードコードせず正本から読むため。
   `nestLib` が無い旧正本でも WARN 報告で後方互換）。

## C-6 設計案（実装禁止・河原氏の承認後に着手）

**目的**: 語りの中の「確認したが無かった」（例:「お母さんに聞いたけど特にないって」）を
narrative-extractor が拾い、**Review 登録を提案する**（自動登録は絶対にしない）。

- **検出**: 「情報源（母/父/本人/主治医/前事業所…）＋確認動詞（聞いた/確認した/尋ねた）＋
  否定（特にない/無いとのこと/思い当たらない）」の共起パターン。対象領域は Review.domain の
  6領域に限定し、どの領域の話かを文脈から候補提示する
- **フロー**: 抽出 → **人間確認ゲート必須**（domain / source / reviewedAt / 対象クライアントを
  提示し、明示承認後にのみスキルの Review テンプレートで登録＋AuditLog）
- **source の扱い**: 語りから明確に取れる場合のみ候補として埋める。曖昧なら**空欄で提示**し
  推測で埋めない（ENU-17。「後で聞く」を許容する）
- **最大リスク**: 実在の方への捏造 Review（=「未確認」を「確認済み」に見せる事故）。
  対策は (a) 自動登録禁止・確認ゲート必須、(b) 導入時は合成データで試行、
  (c) 否定パターンの過検出（「ない」の意味の取り違え）を評価してから実データに適用

## 既知の罠・注意

- **NEXT_SESSION.md 方式の罠**: 古い指示書が残ると処理済みタスクが再実行されかける
  （実績あり）。指示書は処理完了時に削除する運用が確立した（本セッションも削除済み）
- **auto mode classifier が Neo4j への CREATE を拒否する**。読み取りは通る。
  書き込みセッションでは権限モード/許可ルールを先に確認（前セッションの実障害）
- **`_build_parent_link` は Client と直接つながるノードのみ解決する**。
  CareRole（親が Relative）はスコープ機構に乗らない——常時 CREATE が正であり、
  MERGE_KEYS に追加してはならない（`test_merge_keys_canon.py` が不在を固定している）
- drift チェックの WARN=1 は既知（Review.domain/source はラベル限定検証のため
  チェッカーの汎用照合対象外）
- rtk が git 出力を圧縮する。マージ・push の検証は
  `rtk proxy git log --format="%h parents:%p"` で行う
- 本セッションと**無関係な未コミット変更**が作業ツリーに残っている:
  `docs/FAQ.md`（M）、`docs/COMPLETE_MANUAL.md/.html`・`docs/review-report-2026-05.html`・
  `docs/semantic-model-instruction.md`・`docs/家族聴き取りマニュアル.docx`（未追跡）。
  由来確認が済むまでコミットに巻き込まないこと

## 次タスク（優先度順）

### A: 必須
1. **グレーな判断1〜3の承認確認**（特に Relative の逆向きスコープ実装）
### B: 推奨
2. **C-6 の設計案レビュー** — 承認されれば narrative-extractor へ実装
   （合成データでの試行から）
### C: 余裕があれば
3. DRIFT-09（呼称揺れ・旧関数名残存）の文書整理
4. 実 DB での統合検証（Relative/Certificate の新 MERGE 挙動）——**実行前に河原氏確認**
   （本セッションはユニットテストのみ。既存データに grade 無し Certificate があれば
   「不明」ノードとの整合を確認してから）
