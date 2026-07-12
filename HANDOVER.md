# HANDOVER — 2026-07-13 main（DRIFT-07/10 解消・棚卸し2件の処置 / セッション3）

> NEXT_SESSION.md（2026-07-13 用指示書）に基づくセッション。タスク B（agno allowlist 追従）
> と C-4/C-5 は完了。A-1 は河原氏決定により中止、A-2 は**書き込み権限待ちで未完**（下記）。
> 前セッション（Review 導入）の内容は git 履歴の 2026-07-12 時点 HANDOVER を参照。

## 再開コマンド（コピペで動く・本セッションで検証済み）

```bash
cd ~/Dev-Work/project/nest-support
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

./scripts/doctor.sh                              # 環境整合（検証済み: 20 passed / 0 failed）
uv run python scripts/check_semantic_drift.py    # 三者一致（検証済み: OK=21 KNOWN=0 FAIL=0 WARN=1）
uv run pytest tests/ -q                          # 全テスト（検証済み: 162 passed）
```

Neo4j（support-db, port 7687）は稼働中。コンテナ名は `nest-support-neo4j`
（正典 §0 の誤記は 2026-07-13 に修正済み）。

---

## 現在地

- 目標: NEXT_SESSION.md の A-1（M・K キーパーソン）/ A-2（平野 駿介 Review）/
  B（agno allowlist 追従）/ C（軽微整備）

### 進捗

- [x] **B: agno allowlist 追従（DRIFT-07 + DRIFT-10 解消）**
  - agno の **2ファイル**を更新: `lib/db_new_operations.py`（drift チェッカーの AST 対象）と
    `api/app/lib/db_operations.py`（**実行時の門番**・`/api/narrative/schema` の出典。
    NEXT_SESSION は前者のみ指示だったが、後者を放置すると実行時に通らないため両方更新）
  - ノード6件・リレーション8件を追加（API 側は Doctor / HAS_DOCTOR が v3.2 で反映済みだった）
  - `sync_narrative_intake_schema.py --apply` でスキル側 JSON 3本も再生成
  - 正典更新: SEMANTIC_MODEL **v1.4**（acceptedDrifts 空・台帳 DRIFT-07/10 解消）、
    SCHEMA_CONVENTION **v3.3.1**（§0 コンテナ名訂正）→ sync-schema.sh 済み
  - 検証: agno pytest 79 passed / nest pytest 162 passed / drift **FAIL=0 KNOWN=0**
  - コミット・push 済み: shared-schema `5353a56` / agno `7f07e56` / nest（本コミット）
- [x] **C-4**: 正典 §0 のコンテナ名 `support-db-neo4j` → `nest-support-neo4j`（訂正注記付き）
- [x] **C-5**: `.gitignore` に `docs/*.bak-*` を追加
- [ ] **A-1: 中止（2026-07-13 河原氏決定）** — M・K さんの緊急連絡先は**入手しておらず、
  今後も入手予定なし**。よって登録も Review も**書かない**（確認行為が行われていない以上、
  Review を書くことこそ捏造になる。BRS-04）。KeyPerson 領域の「🚨 未確認」表示が
  **正しい現状**としてダッシュボードに残り続ける——これは仕様どおりの挙動。
- [ ] **A-2: 仕掛かり（書き込み権限待ち）** — 平野 駿介さん（合成）の Review 登録。
  クエリ・パラメータは確定済み（下記「未決論点」）。`neo4j:execute_query` での CREATE が
  **Claude Code の auto mode classifier に拒否され**、DB 書き込みが実行できていない。
- [ ] **C-6（未着手）**: narrative-extractor が語りから「確認した」旨を拾う対応

## グレーな判断（次セッション冒頭で承認確認を）

1. **agno の編集範囲を指示書の1ファイルから2ファイルへ拡大した。**
   `api/app/lib/db_operations.py` が実行時の門番（`/api/narrative/schema` の出典）であり、
   `lib/db_new_operations.py` だけ直しても実行時ドリフトが残るため。
2. **新ラベルの MERGE キー設計を裁量で決めた**（正典に明文の無い部分）:
   Doctor / Relative = `name`（名寄せ正規化あり）、Identity = `name`+`dob`（正典 §3 の主要キー）、
   **CareRole / ProviderFeedback / Review = MERGE せず常時 CREATE**
   （CareRole は ENT-16 の per-client 則、Review は ENT-24 の追記のみ則。
   ProviderFeedback は feedbackId が語り抽出に含まれない場合に登録ごと落ちるのを避けた）。
3. **SCHEMA_CONVENTION に v3.3.1 の変更履歴行を追加**（軽微訂正だが日付入り記録の文化に合わせた）。
4. **agno の `docs/SEMANTIC_MODEL.md` を新規に git 管理へ追加**（同期コピーが未トラックだった）。

## 未決論点（河原氏の判断が要る）

### 1. A-2 の書き込み経路（最優先・これだけで完了する）

登録内容は確定済み・全て合成データ:

- Client: `平野 駿介`（**姓と名の間に半角スペースあり**——スペース無しの完全一致は0件になる）
- Review: `domain: NgAction` / `reviewedAt: 2026-07-13` / `source: 母親` /
  `note: 合成データ整備（棚卸しの見本）。デモ環境の Review 運用例として登録`
- Supporter: `河原` / 登録後に AuditLog（targetType: Review）

選択肢:
- **(a)** neo4j MCP の書き込みを許可して再実行（設定でルール許可 or 権限モード変更）
- **(b)** nest の Python 経路で実行することを明示承認
  （`lib/db_operations.py::register_to_database` は Guardian 検証＋AuditLog 統合済みで、
  Review は CREATE フォールバックで通ることを確認済み）

### 2. M・K さんの「入手不能」を将来どう記録するか（急がない）

Review は「確認した」記録なので、「確認を試みたが得られなかった」は表現できない
（`source` に該当値も無い）。当面は「🚨 未確認」のままが正——ただしダッシュボードで
恒久的に警告が出続けるので、運用上ノイズになったら表現の設計（例: note 運用や新列挙値）を
正典側で検討する。**勝手に値を増やさないこと**（スキーマの不可侵性）。

## 既知の罠・注意

- **auto mode classifier が Neo4j への CREATE を拒否する**（本セッションの実障害）。
  読み取りは通る。書き込みセッションでは権限モード/許可ルールを先に確認すること。
- **「平野 駿介」は姓名間にスペースあり**。BRS-08 の完全一致照合前に、表示可能な
  合成データなら CONTAINS で正確な氏名を確定してから書くこと（実在の方には使わない）。
- **nest 自身の `lib/db_operations.py` にドリフト候補（DRIFT-12 候補・未登録）**:
  (a) `MERGE_KEYS["Certificate"]` が `["type"]` のみ（正典 §10.3 は `["type","grade"]`。
  client スコープなので他人との収斂は無いが、同一人の療育手帳AとBが1ノードに潰れる）、
  (b) Doctor / Relative / CareRole / ProviderFeedback / Identity が MERGE_KEYS に無い
  （非 MERGE ラベルは Guardian 検証つき CREATE にフォールバックするため書き込み自体は
  可能——Review が通るのはこの仕組み）。`check_semantic_drift.py` は nest lib を
  見ていないため機械検出されない。台帳登録と修正は次セッションで要承認。
- drift チェックの WARN=1 は既知（Review.domain/source はラベル限定検証のため
  チェッカーの汎用照合対象外）。
- rtk が git 出力を圧縮する。マージ・push の検証は
  `rtk proxy git log --format="%h parents:%p"` で行う（本セッションも使用）。
- 本セッションと**無関係な未コミット変更**が作業ツリーに残っている:
  `docs/FAQ.md`（M）、`docs/COMPLETE_MANUAL.md/.html`・`docs/review-report-2026-05.html`・
  `docs/semantic-model-instruction.md`・`docs/家族聴き取りマニュアル.docx`（未追跡）。
  由来確認が済むまでコミットに巻き込まないこと。

## 次タスク（優先度順）

### A: 必須
1. **A-2 の完了** — 上記「未決論点1」の経路を河原氏が選択 → Review + AuditLog 登録 →
   テンプレート11 で `✅ 確認済み（0件）` 表示を検収
### B: 推奨
2. **nest lib のドリフト台帳登録（DRIFT-12）と修正の承認取り** — Certificate 複合キー化
   ＋新ラベルの MERGE キー追加（agno と同じ設計判断を流用できる）
### C: 余裕があれば
3. C-6: narrative-extractor の「確認した」検出（→ Review 登録の提案）
4. DRIFT-09（呼称揺れ・旧関数名残存）の文書整理
