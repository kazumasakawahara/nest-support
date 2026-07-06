# P2 マイグレーション適用記録（2026-07-06）

P2 バックログのスキーマ整合マイグレーションを実 DB（`nest-support-neo4j` / port 7687）に適用した記録。ユーザー承認のうえ、バックアップ取得後に実行。

## 事前バックアップ

- `scripts/backup.sh` を実行。オンライン dump は "database is in use" で失敗し、オフライン方式（コンテナ停止 → `./neo4j_data` コピー）で完了。
- 出力: `neo4j_backup/backup_20260706_191006`（522M）。
- 副作用: オフライン化で stale PID ロックが残り `nest-support-neo4j` が再起動ループ。`docker compose up -d --force-recreate`（データは bind mount `./neo4j_data` で保持）で復旧。データ健全性（Client 6 / Condition 11 / Hospital 13）を確認後に適用。

## C-1: Condition.status ケース正規化

- スクリプト: `scripts/migrate_condition_status_case.py --apply`
- 変更: `status='active'` × 5 → `'Active'`（既存 `'Active'` × 6 は不変）
- 適用後: `Condition.status` は全 11 件 `'Active'`、小文字 `'active'` は 0 件。

## C-2: Hospital.doctor → Doctor ノード昇格

- スクリプト: `scripts/migrate_hospital_doctor_to_node.py --apply`
- 変更: `doctor` 文字列を持つ 8 病院を `(:Hospital)-[:HAS_DOCTOR]->(:Doctor {name})` に昇格し、`Hospital.doctor` プロパティを除去。
- 名寄せ: 8 病院 → 7 名の Doctor（`安澤医師` が `安澤医院` と `のぞえの丘病院` で 1 ノードに収斂）。
- 適用後: Doctor ノード 7 / HAS_DOCTOR 関係 8 / `Hospital.doctor` 残存 0。

## スキーマ定義の更新（コード側）

- `lib/schema_validator.py`: status 列挙に `Monitoring` 追加、`Doctor` ラベル・`HAS_DOCTOR` リレーション登録。
- `CLAUDE.md`（スキーマ SSOT）: 主要ノードラベルに `Doctor`、主要リレーションに `(:Hospital)-[:HAS_DOCTOR]->(:Doctor)` を追記。
- `docs/SCHEMA_CONVENTION.md`（下流の同期コピー）は意図的に未編集。

## 冪等性

両スクリプトを再 dry-run し、対象 0 件を確認（再実行しても二重適用されない）。

## 検証

- `uv run pytest tests/` → 162 passed（P2 テスト `tests/test_p2_schema.py` 込み）。
