# Phase 2 PoC（概念実証）スクリプト

2026-04-17 に実施した「narrative テキスト → 構造化 → Neo4j 登録 → 照会 → 訪問準備シート生成」の一気通貫を Claude + Skills + Neo4j MCP（等価: Python ドライバ）で完走できることを実証したサンプル。

## 位置づけ

- **デモ／参照用**：本番運用時は Claude Desktop/Code が Skills のガイドに従い Neo4j MCP を直接呼び出す
- 本スクリプトは MCP が未接続な環境でも同じ Cypher を Python ドライバで実行し、挙動を再現するためのもの
- 架空データ（テスト太郎）を使っており、実在の人物とは無関係

## スクリプト一覧

| ファイル | 対応 Skill | 役割 |
|---------|-----------|------|
| `01_register.py` | narrative-extractor | 架空の面談記録から抽出した JSON を Cypher テンプレートで Neo4j へ登録 |
| `02_verify.py` | neo4j-support-db | Template 2（4本柱プロフィール）/ 5（支援記録）/ 7（監査ログ）で登録を照会 |
| `03_visit_prep.py` | visit-prep | 訪問前ブリーフィングシート生成（安全情報最優先） |

## 実行順

```bash
# Neo4j (port 7687) が稼働している前提。未稼働なら：
./scripts/doctor.sh   # 状況確認

uv run python scripts/examples/phase2-poc/01_register.py
uv run python scripts/examples/phase2-poc/02_verify.py
uv run python scripts/examples/phase2-poc/03_visit_prep.py
```

`01_register.py` は重複登録防止のため既存の `Client {name:"テスト太郎"}` があると abort する。再実行したい場合は対象 Client を削除してから実行すること。

## 設計メモ

- Cypher は `claude-skills/<skill>/SKILL.md` の公開テンプレートを **そのまま** パラメータ化して使用（スキーマ規約: PascalCase ノード / camelCase プロパティ / UPPER_SNAKE_CASE リレーション）
- 廃止リレーション名（`PROHIBITED` 等）は書き込まない。読み取りのみ `[:NEW|OLD]` 構文で後方互換を保つ
- 登録と監査ログは同一トランザクション（`session.execute_write`）で作成
