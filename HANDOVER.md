# HANDOVER — 2026-07-12 main（意味・ルール層の正本化 完了時）

## 再開コマンド（コピペで動く・本日検証済み)

```bash
cd ~/Dev-Work/project/nest-support
./scripts/doctor.sh                                # 環境整合（本日 20 passed / 0 failed）
uv run python scripts/check_semantic_drift.py      # 三者一致（健全: FAIL=0・KNOWN=2=DRIFT-07a/b のみ）
uv run pytest tests/ -q                            # 全162テスト（本日 all pass）
```

## 現在地

- 目標: **nest-support 意味・ルール層の正本化**（指示文書:
  `docs/semantic-model-instruction.md`、型: my-assistant プレイブック
  「セマンティックモデル拡張の型」）
- 進捗:
  - [x] フェーズ1 調査・分界・4分類・形式提案（河原氏決定5点は指示文書の完了記録に固定）
  - [x] フェーズ2 正本作成: `~/Dev-Work/shared-schema/SEMANTIC_MODEL.md`（v1.1）＋
        `scripts/check_semantic_drift.py`（三者一致チェッカー）
  - [x] フェーズ3 矛盾解消（限定スコープ）: DRIFT-01〜06・08 解消、
        すべて日付入り訂正注記付き
  - [x] フェーズ4 コミット・push・sync-schema.sh 3プロジェクト配布・
        grade未設定 Certificate 0件確認（DRIFT-10 不要）
  - [x] 検収（完全新規チャット）→ 指摘対応: 6スキル SKILL.md 冒頭に正本参照ルール追記
  - [x] 検収再診断 → skill-sync で claude.ai へ 7スキル再同期
        （6スキル＋skill-sync 自身。一覧の最終更新日 2026/07/12 を検証済み）
- 主要コミット（nest-support main, push 済み）: `2f428eb`（正本化マージ）→
  `cd9c22d` → `0e4c03b`（参照ルール）→ `a0f2042`（配布チェックリスト）。
  shared-schema はローカルのみ `49a1efa`

## グレーな判断（次セッション冒頭で承認確認を）

- skill-sync の SKILL.md 修正時、依頼された heredoc 訂正に加えて
  「Chrome リモートデバッグ未許可時の CDP handshake タイムアウト」の
  対処1項目を**追加で書き足した**（本日の実障害。過剰なら削除可）
- provider-search の読み取りソートに旧値 `Ended` の後方互換行を残した
  （BRS-07 の思想に合わせた設計判断。DB内の Ended 残存件数は未確認）
- Certificate 複合キー化に伴い「等級未設定の既存ノードは grade='不明' の
  新ノードとマッチしない」旨を注記したが、既存8ノードは全て grade 設定済みの
  ため実害なしと判断（マイグレーションは組んでいない）

## 未決論点

- **DRIFT-07**: agno 実行時 allowlist の v3.1/v3.2 追従（次セッション送り・
  河原氏決定）。4層伝播（shared-schema→nest→agno→oyagami）で
  `~/Dev-Work/neo4j-agno-agent/lib/db_new_operations.py` の
  MERGE_KEYS / ALLOWED_CREATE_LABELS / ALLOWED_REL_TYPES を更新 →
  SEMANTIC_MODEL §6 acceptedDrifts から DRIFT-07a/b を削除 →
  `check_semantic_drift.py --strict` green 化。**agno 側の変更は要承認**
- **BRS-04 強化「積極的陰性の記録」**（検収Q2 起点）: 「確認したうえで禁忌なし」を
  `contraindicationReviewedAt` / `reviewedBy` 相当で記録可能にする。
  スキーマ追加＝SCHEMA_CONVENTION 追記＋4層伝播＋河原氏承認が前提
- ENU-15: CareRole.priority の値域が未定義（High/Medium/Low か数値か）
- USES_SERVICE の旧値 `Ended` の DB 残存件数（読み取り互換で実害はないが未計測）

## 既知の罠・注意

- **配布4層チェックリスト**: shared-schema（正本編集）→ sync-schema.sh
  （3プロジェクト配布）→ ~/.claude/skills symlink（Claude Code は即時有効）→
  **skill-sync（claude.ai へ ZIP 再アップロード）。スキルを直したら skill-sync
  までがワンセット**（検収再診断 2026-07-12 の教訓）
- **shared-schema はリモートなしのローカル運用**（2026-07-12 確認。保全は
  同期コピー＋push 済みリポジトリが実質的に担う）
- SEMANTIC_MODEL.md / SCHEMA_CONVENTION.md の各プロジェクト内コピーは
  **read-only 同期物**。編集は shared-schema のマスターのみ。
  `sync-schema.sh --check` はバナーのタイムスタンプ差で常に DIFF 表示になる（仕様）
- rtk が git log 等の出力を圧縮・欠落させることがある。**マージやpushの検証は
  `rtk proxy git log --format="%h parents:%p"` の素の出力で行う**
- oyagami-local / neo4j-agno-agent 側の同期コピーは配布済みだが**未コミット**
- `docs/FAQ.md`・docs/COMPLETE_MANUAL.* 等の未コミット変更/未追跡ファイルは
  本作業と無関係のまま残置（コミット時に混入させない）
- 検収は**必ず完全新規チャット**で（古いスナップショット誤診の防止）

## 次タスク（優先度順）

- **A: DRIFT-07 の agno 4層伝播**（上記未決論点の手順。これで既知ドリフトの
  機械検証がゼロになる）
- **B: BRS-04 強化の設計承認とり**／**横断セマンティックレイヤー**
  （nest-system 利用者 ↔ nest-support クライアントの橋渡し。対応表は高度PIIのため
  pii-safe-data-handling 適用で設計）
- **C**: DRIFT-09（呼称揺れ・旧関数名の文書整理）、SCHEMA_CONVENTION v3.3 で
  未正典化列挙値（ENU-07〜15）の §7 収載、Ended 残存件数の計測
