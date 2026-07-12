# HANDOVER — 2026-07-12 main（Review「0件問題」の解消 / セッション2・完）

> 本日2本目のセッション。午前の「意味・ルール層の正本化」（旧 HANDOVER）の続きで、
> そこで**未実装のまま残っていた BRS-04 の要請**を構造として実装し、運用まで開始した。
> 旧 HANDOVER の内容は git 履歴（`a0f2042` 時点）を参照。

## 再開コマンド（コピペで動く・本セッション末に検証済み）

```bash
cd ~/Dev-Work/project/nest-support
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

./scripts/doctor.sh                              # 環境整合（検証済み: 20 passed / 0 failed）
uv run python scripts/check_semantic_drift.py    # 三者一致（検証済み: OK=19 KNOWN=2 FAIL=0 WARN=1）
uv run pytest tests/ -q                          # 全テスト（検証済み: 162 passed）
```

Neo4j（support-db, port 7687）は稼働中。**コンテナ名は `nest-support-neo4j`**。

```bash
docker ps --filter name=nest-support-neo4j        # 起動確認
```

> ⚠️ `SCHEMA_CONVENTION.md §0` はコンテナ名を `support-db-neo4j` と記載しているが**誤り**。
> 同名の旧コンテナは3ヶ月前に停止済み（Exited）。→ 「既知の罠」参照。

---

## 現在地

- 目標: **「0件問題」の解消** —— 禁忌0件が「確認したうえで無い」のか
  「まだ聞き取れていない」のかを、DB として区別できるようにする。
- 背景: `BRS-04` は以前から**この区別を命じていた**が、区別を表現できる構造が
  存在せず、**ルールが構造的に遵守不能な状態だった**。本セッションはその穴を埋めた。

### 進捗

- [x] **正典2本**（`~/Dev-Work/shared-schema/` が正・sync 済み・**GitHub プライベートリポ化済み**）
  - `SEMANTIC_MODEL.md` **v1.3** — v1.2（ENT-24 / BRS-12 / ENU-16・17）に加え、
    **BRS-03 に「embedding 生成時の外部API送信」の許容範囲を明文化（DRIFT-11 解消）**
  - `SCHEMA_CONVENTION.md` v3.3 — §3 `Review` / §4 `REVIEWED` / §7.7・7.8 値域
- [x] **Guardian**（`lib/schema_validator.py`）— Review / REVIEWED / `LABEL_SCOPED_ENUM_VALUES`
- [x] **スキル5本**（claude.ai 同期済み）
  - `neo4j-support-db` / `data-quality-agent` / `emergency-protocol` / `visit-prep`（セッション前半）
  - `onboarding-wizard` — **B-2 完了**。聞き取りガイド（「無い」も記録）・Review 登録
    テンプレート・Phase 4 の3値判定・Phase 5 チェックリストの3値化。
    **旧チェックリストの「禁忌1件以上が必須」という欠陥を修正**（聞いたうえで
    本当に無い人が永久に未完了になる設計だった）
- [x] **C-1 棚卸し実施**（禁忌＋キーパーソン）— 未確認2件を検出。
    テスト Review で状態遷移（🚨→✅→0件のまま）を実証後、テストデータは削除済み
    （削除も AuditLog に記録）
- [x] **DRIFT-11 解消** — 実装調査の結果、**氏名・生年月日は意図的に送信されていない**
    ことが判明（`build_client_summary_text` は `displayCode` 使用）。BRS-03 に明文化し、
    `lib/embedding.py` のコメントを正典参照に格上げ
- [x] 検証: doctor 20 passed / pytest 162 passed / drift FAIL=0（KNOWN=2＝DRIFT-07+10）

### DB マイグレーションは「不要」（意図的）

既存クライアントに Review を遡って作る術はなく、作るべきでもない。
**Review の不在＝未確認**が、まさに検出したい正しい状態。
ここで「とりあえず全員に確認済みを立てる」backfill をやると、仕組みの目的を破壊する。
インデックスも不要（Client から辿るため）。

---

## グレーな判断（次セッション冒頭で承認確認を）

1. **`Review.source`（情報源）を必須設計に含めた。**
   BRS-04 を満たすだけなら `reviewedAt` だけで足りるが、「母親に確認して禁忌なし」と
   「本人にしか聞けていない」は信頼度が違う。かつ**誰が情報源だったかの記録自体が、
   親なき後に引き継がれる資産**になると判断した。過剰なら削れる。

2. **`result`（確認の結果）プロパティは意図的に持たせていない。**
   件数はグラフから引けるので冗長であり、実データとズレる余地を作るため。

3. **Guardian に `LABEL_SCOPED_ENUM_VALUES` という新機構を追加した。**
   既存の `ENUM_VALUES` はプロパティ名だけで引くため、`source` を素直に登録すると
   **他ノードの `source` に誤検知が出る**（例: `ServiceProvider.source='WAMNET'`）。
   ラベル限定の検証関数（`validate_label_scoped_enum`）を約20行で新設した。
   「外科的な変更」の原則からはやや踏み込んでいるので、要確認。

4. **`emergency-protocol` の既存規定を否定・削除した。**（下記「発見」参照）
   旧規定は明示的に書かれていたものなので、独断で消してよかったか確認されたい。

5. **`Review.domain` を6領域に限定**（NgAction / CarePreference / KeyPerson /
   Guardian / Certificate / CareRole）。「0件が安全・権利に直結する」ものだけを対象とした。

---

## 本セッションの発見（重要）

### データ環境に実在の方が混在している

**support-db は完全な合成データ環境ではない。「M・K」は実在の方**（2026-07-12 河原氏確認）。
他の5名（平野駿介・テスト太郎・山田健太・田中大輝・鈴木美咲）は合成。
**今後の書き込み・表示では、対象が実在かどうかを1件ごとに確認すること**
（本セッションで「全部合成」と誤認してテスト書き込みに進んだ反省から）。

### `emergency-protocol` に危険な規定が入っていた（前半で発見・廃止済み）

旧版はこう規定していた:

> **禁忌事項が0件の場合も「禁忌事項: 登録なし」と明示する**（確認済みであることを示す）

**最も安全に直結するスキルが、未聴取を「確認済み」と示せと命じていた。**
BRS-04（No Fabrication）違反であり、支援者が「なし」と読んで行動すれば事故になり得る
（アレルギーが未登録なだけの人に、「禁忌なし」を根拠に食品を提供する等）。
Review ベースに置き換え、**なぜ危険だったかを注記として残した**（同じ判断が再発しないように）。

`data-quality-agent` の Check 2 も同様に「禁忌事項なし」を出力していた。修正済み。

### `check_semantic_drift.py` の仕様（罠）

`accepted()` は **`(target, kind)` の最初の1件しか見ない**。
同一 target に acceptedDrift を2エントリ置くと、後発が無視されて FAIL になる。
→ DRIFT-07 と DRIFT-10 を **1エントリに統合**した（`DRIFT-07a+10a` / `DRIFT-07b+10b`）。
今後、同じ target にドリフトを足すときは既存エントリの `values` に追記すること。

---

## 未決論点（河原氏の判断が要る）

### 1. 再確認の推奨間隔（陳腐化判定）

本セッションでは**スコープ外**とした（2026-07-12 河原氏決定）。
`reviewedAt` は記録するが、古さによる警告は出さない。
BRS-12 に `provisional` で見直しトリガーを記載済み。

（DRIFT-11 は本セッション後半で**解消済み**——実装調査により氏名・生年月日は
意図的に送信されていないことが判明し、BRS-03 に明文化した。未決ではなくなった）

---

## 既知の罠・注意

- **Neo4j のバージョンが古い**: `CALL (c, domain) { ... }` 形式のスコープ付きサブクエリは
  **構文エラーになる**（5.23 未満）。`CALL { WITH c ... }` か、サブクエリを使わない形で書く。
  実際に一度踏んだ。テンプレート11 は検証済みの形に書き直してある。
- **コンテナ名**: 実体は `nest-support-neo4j`。正典 §0 の `support-db-neo4j` は誤り（未修正）。
- **システム python3 では動かない**: `check_semantic_drift.py` は `X | None` 構文を使うため
  3.10+ が必要。必ず `uv run python` で実行する。
- **osascript のヒアドキュメント**は壊れる。複数行スクリプトは filesystem MCP でファイルに
  書いてから実行すること（本セッションで再確認）。
- **agno 経路では Review を書き込めない**（allowlist 未追従・DRIFT-07+10）。
  現状の書き込み経路は Claude Skills（neo4j MCP 直叩き）と nest の Python 経路のみ。
- 本セッションと**無関係な未コミット変更**が作業ツリーに混じっている:
  `docs/FAQ.md`（M）、`docs/COMPLETE_MANUAL.md` / `.html`（未追跡）。
  由来不明のため触っていない。コミット時に巻き込まないこと。
- `sync-schema.sh` が `docs/*.bak-*` を生成する。コミット対象から外す。

---

## 次タスク（優先度順）

### A: 必須

1. **M・K さん（実在）のキーパーソン未確認の解消**。これは技術ではなく実務——
   緊急時の連絡先が登録されていない状態。確認できたら Review も登録する。
2. **平野駿介さん（合成）の禁忌未確認** — 合成データなので実害はないが、
   デモデータとして整備するなら Review を入れておく（棚卸しの見本になる）

### B: 推奨

3. **agno allowlist の追従**（DRIFT-07 + DRIFT-10 を一括）。
   `~/Dev-Work/neo4j-agno-agent/lib/db_new_operations.py` に
   ノード6件（Doctor / Relative / CareRole / ProviderFeedback / Identity / **Review**）と
   リレーション8件（HAS_DOCTOR / IS_PARENT_OF / FAMILY_OF / PERFORMS /
   CAN_BE_PERFORMED_BY / HAS_FEEDBACK / WROTE / **REVIEWED**）を追加。
   → 完了したら SEMANTIC_MODEL §6 の acceptedDrifts から該当エントリを削除し、
     ドリフト台帳の DRIFT-07 / DRIFT-10 を「解消」に更新する。

### C: 余裕があれば

4. 正典 §0 のコンテナ名を `nest-support-neo4j` に修正（DRIFT-09 とまとめて）。
5. `.gitignore` に `docs/*.bak-*` を追加（sync-schema.sh の副産物がたまる）。
6. `narrative-extractor` が語りから「確認した」旨を拾えるようにするか検討
   （例:「お母さんに聞いたけど特にないって」→ Review 登録の提案）。
