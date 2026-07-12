# HANDOVER — 次セッションへの引き継ぎ

最終更新: 2026-07-12（意味・ルール層の正本化 フェーズ1〜4 完了時）

## 直近で完了した作業（2026-07-12）

**nest-support 意味・ルール層の正本化**（指示文書: `docs/semantic-model-instruction.md`、
型: `~/Obsidian/my-assistant/playbooks/セマンティックモデル拡張の型.md`）

- `~/Dev-Work/shared-schema/SEMANTIC_MODEL.md` **v1.1** を新設（SCHEMA_CONVENTION の
  上の「意味とルール」正本。entities 23 / metrics 9 / business_rules 11 / enums 15）。
  sync-schema.sh で3プロジェクト（nest-support / oyagami-local / neo4j-agno-agent）へ
  配布済み
- 三者一致チェッカー `scripts/check_semantic_drift.py` 新設
  （正本 JSON ブロック × lib/schema_validator.py × agno allowlist。
  現状: OK=19 / KNOWN=2 / FAIL=0。KNOWN は DRIFT-07a/b のみ）
- 既知ドリフト DRIFT-01〜06・08 を解消（日付入り訂正注記の前例に従う）。
  詳細は SEMANTIC_MODEL.md §7 の台帳
- 河原氏決定（2026-07-12）: 緊急時提示順は emergency.md 版が正 /
  RISK_LEVEL_ALIASES の段階表現翻訳は「意図的な安全側翻訳」として現状維持 /
  embedding は参考・禁忌の確認は構造が正（BRS-03）/ USES_SERVICE の利用終了は
  `Inactive`（旧 Ended は書き込み禁止・読み取りのみ後方互換）
- grade 未設定の Certificate は 0件と確認済み（2026-07-12。DRIFT-10 は不要）

## 未消化タスク（推奨順）

1. **DRIFT-07: agno 実行時 allowlist の v3.1/v3.2 追従**（次セッション送り・
   2026-07-12 河原氏決定）。不足: ラベル Doctor / Relative / CareRole /
   ProviderFeedback / Identity、リレーション HAS_DOCTOR / IS_PARENT_OF /
   FAMILY_OF / PERFORMS / CAN_BE_PERFORMED_BY / HAS_FEEDBACK / WROTE。
   **4層伝播手順**（shared-schema → nest → agno allowlist → oyagami）に従い、
   agno 側 `lib/db_new_operations.py` の MERGE_KEYS / ALLOWED_CREATE_LABELS /
   ALLOWED_REL_TYPES を更新 → 完了後に SEMANTIC_MODEL.md §6 の acceptedDrifts
   から DRIFT-07a/b を削除し、`check_semantic_drift.py --strict` green を確認
2. **検収（未実施）**: 完全新規チャットで実施。質問例は
   `docs/semantic-model-instruction.md` フェーズ4 参照
3. **横断セマンティックレイヤー**（nest-system の利用者 ↔ nest-support の
   クライアントの横断ID対応と用語の橋渡し。対応表自体が高度な PII のため
   pii-safe-data-handling 適用で設計すること）
4. DRIFT-09（軽微）: 「4本柱/7本柱」呼称揺れ・manifesto 内の旧関数名残存・
   wamnet-provider-sync の日付表記混在。文書整理時にまとめて
5. SCHEMA_CONVENTION v3.3 改版時: 未正典化列挙値（SEMANTIC_MODEL ENU-07〜15）の
   §7 収載、priority 値域の正式化

## 注意事項

- **shared-schema はリモートなしのローカル運用**（2026-07-12 確認。バックアップは
  各プロジェクトへの同期コピーと nest-support 等の push 済みリポジトリが実質的に担う）
- SEMANTIC_MODEL.md / SCHEMA_CONVENTION.md の各プロジェクト内コピーは
  **read-only 同期物**。編集は shared-schema のマスターのみ
- oyagami-local / neo4j-agno-agent 側の同期コピーは配布済みだが**未コミット**
  （両リポジトリでのコミットは次回作業時に）
- `docs/FAQ.md` に本作業と無関係の未コミット変更あり（2026-07-12 以前から）。
  docs/COMPLETE_MANUAL.* / review-report / 家族聴き取りマニュアル.docx も
  未コミットのまま残置
