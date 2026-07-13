# HANDOVER — 2026-07-13 main（DRIFT-07/10 解消・棚卸し2件の処置 / セッション3・完）

> NEXT_SESSION.md（2026-07-13 用指示書）に基づくセッション。タスク B（agno allowlist 追従）
> と A-2・C-4/C-5 は完了。A-1 はいったん中止された後、同日の続行作業で**本人確認による
> Review 登録として解消**（本文の A-1 参照）。NEXT_SESSION.md は役目を終えたため削除済み。
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
- [x] **A-1: 解消（2026-07-13・本人確認による Review 登録）** — 経緯は2段階。
  ① 当初「入手しておらず今後も予定なし」との指示で中止（確認行為がない以上 Review を
  書くこと自体が捏造になるため。BRS-04）。途中、ダミー連絡先で警報を消す案も検討されたが却下
  （緊急時に存在しない連絡先を提示するのは未確認より悪い）。
  ② その後、**本人に確認済み（2026-07-12）で緊急連絡先となり得る家族・親族等が
  存在しないことが判明**。これは「確認したうえで0件」そのものなので、
  Review（domain=KeyPerson / reviewedAt=2026-07-12 / source=本人 / 登録者=河原）を登録。
  AuditLog も登録済み。検収: kpCount=0 / 状態「✅ 確認済み(0件)」（DATE 型で既存と整合）。
  **正典変更は不要だった**（既存の ENU-17 `本人` で表現できた）。
- [x] **A-2: 完了** — 平野 駿介さん（合成）の Review 登録。
  `neo4j:execute_query` での CREATE が auto mode classifier に拒否されたため、
  **河原氏の承認を得て nest の Python 経路**（`register_to_database`＝Guardian 検証＋
  監査統合）で実行。domain=NgAction / reviewedAt=2026-07-13 / source=母親 /
  note に合成データ整備の旨。AuditLog（targetType=Review）も明示登録
  （Review は `_audit_node_creation` のフック対象外のため）。
  検収: ngCount=0 / reviewCount=1 / source=母親 → 「✅ 確認済み（0件）」状態を確認済み。
- [ ] **C-6（未着手）**: narrative-extractor が語りから「確認した」旨を拾う対応

## グレーな判断（次セッション冒頭で承認確認を）

0. **（A-1 登録時・2026-07-13）実在の方への Review 書き込みで、`register_to_database`
   ではなく、Guardian 検証を明示実行したうえでスキルの正規 Cypher を直接実行した。**
   理由: `register_to_database` は登録後に `embed_client_summary` を呼び、実在の方の
   概要テキストを Gemini に新規送信する副作用がある（BRS-03 上は許容だが、
   Review 1件の登録に不要な送信は避けた）。完全一致1件チェック・Guardian enum 検証・
   AuditLog は維持。同じ状況（実在の方への少量書き込み）ではこの形を推奨。

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

現在なし。（旧・論点1「M・K さんの入手不能をどう記録するか」は **2026-07-13 に解消**——
本人確認により「確認したうえで0件」と判明し、既存の Review（source=本人）で表現できた。
なお「確認を試みたが得られなかった」を表現する器は依然として存在しないが、
具体の需要が出るまで設計しない。**勝手に値を増やさないこと**）

次の判断事項は DRIFT-12（下記「既知の罠」参照）の修正承認。

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
1. **nest lib のドリフト台帳登録（DRIFT-12）と修正の承認取り** — Certificate 複合キー化
   ＋新ラベルの MERGE キー追加（agno と同じ設計判断を流用できる）
### C: 余裕があれば
2. C-6: narrative-extractor の「確認した」検出（→ Review 登録の提案）
3. DRIFT-09（呼称揺れ・旧関数名残存）の文書整理
