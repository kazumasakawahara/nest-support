# 指示書（2026-07-13 セッション用・この全文を最初のメッセージとして貼り付け）

nest-support の続き作業です。昨日（2026-07-12）、support-db に Review（確認記録）を
導入し、「禁忌0件＝確認済みなのか未聴取なのか」を区別できるようにしました。

## まず最初にやること

1. `~/Dev-Work/project/nest-support/HANDOVER.md` を filesystem MCP で読むこと。
   昨日の全作業・グレーな判断・罠がそこに書いてあります。本指示書より HANDOVER が正。
2. 環境確認（HANDOVER 記載の再開コマンド。必ず `uv run` で）:
   - `./scripts/doctor.sh`（昨日時点: 20 passed）
   - `uv run python scripts/check_semantic_drift.py`（昨日時点: FAIL=0, KNOWN=2）
   - `uv run pytest tests/ -q`（昨日時点: 162 passed）

## 今日のタスク（優先順）

### A-1（最優先・実務）: M・K さんのキーパーソン未確認の解消
- **M・K さんは実在の方**です。緊急連絡先が1件も登録されていません。
- 私（河原）からキーパーソン情報を伝えるので、`neo4j-support-db` スキルの
  テンプレートで登録し、**併せて Review（domain=KeyPerson, source=私が伝える）も登録**
  してください。
- 書き込み前に登録内容を必ず私に確認すること（BRS-08: 氏名は完全一致）。

### A-2（デモ整備）: 平野 駿介さん（合成データ）の禁忌未確認
- 合成データなので実害はありませんが、棚卸しの見本として Review を入れておきます。
- source は「母親」、note に合成データ整備である旨を明記してください。

### B（推奨）: agno allowlist の追従（DRIFT-07 + DRIFT-10 一括）
- `~/Dev-Work/neo4j-agno-agent/lib/db_new_operations.py` に
  ノード6件・リレーション8件を追加（一覧は HANDOVER の「次タスク B」）。
- 完了したら SEMANTIC_MODEL §6 の acceptedDrifts から該当エントリを削除し、
  ドリフト台帳を「解消」に更新 → sync-schema.sh → drift チェックで FAIL=0 を確認。

## 厳守事項（昨日の反省を含む）

- **support-db には実在の方と合成データが混在**しています（実在: M・K さんのみ。
  他5名は合成）。**書き込み・表示の前に、対象が実在かどうかを1件ずつ私に確認**すること。
- 個人紐づけ PII は LightRAG 等の**外部ストアに複製しない**。照会は常に Cypher
  （CLAUDE.md §8 / neo4j-support-db ルール7）。
- **0件を「なし」と表示しない**。Review の有無で「✅ 確認済み(0件)」か「🚨 未確認」を
  区別する（BRS-12）。
- Review は**追記のみ**。source（誰に確認したか）を推測で埋めない。
- 書き込み後は必ず AuditLog を残す（BRS-11）。
- 正典の編集は `~/Dev-Work/shared-schema/` のみ（プロジェクト内 docs/ は同期物）。
  編集後は `sync-schema.sh` を流す。コミットは feature ブランチで。
- Neo4j コンテナ名は **`nest-support-neo4j`**（正典 §0 の `support-db-neo4j` は誤記・未修正）。
- Neo4j は 5.23 未満: `CALL (vars) { ... }` 構文は使えない。
- スクリプト実行は必ず `uv run python`（システム python3 では動かない）。
- osascript のヒアドキュメントは壊れる。複数行スクリプトは filesystem MCP で
  ファイルに書いてから実行。

## 完了したら

- HANDOVER.md を更新（session-handover スキルの型で上書き）
- スキルを変更した場合は skill-sync で claude.ai に同期
- コミット・push（feature ブランチ → main マージ）
