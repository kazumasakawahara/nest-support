#!/usr/bin/env python3
"""
仮名化スキーマ・マイグレーションスクリプト

既存の Client ノードに以下を追加:
  1. clientId (UUID): 内部識別用の一意ID（c-XXXXXXXX 形式）
  2. displayCode (A-001 等): 研修・デモ用の表示コード
  3. Identity ノード: 氏名・生年月日を分離して保管

使い方:
  # ドライラン（変更なし、影響確認のみ）
  uv run python scripts/migrate_pseudonymization.py --dry-run

  # 実行
  uv run python scripts/migrate_pseudonymization.py

  # ロールバック（Identity ノード・追加プロパティを削除）
  uv run python scripts/migrate_pseudonymization.py --rollback

環境変数:
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USERNAME=neo4j
  NEO4J_PASSWORD=password
"""

import os
import sys
import uuid
import argparse
from dotenv import load_dotenv

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


def get_driver():
    """Neo4j ドライバーを取得"""
    from neo4j import GraphDatabase

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD", "password")

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    driver.verify_connectivity()
    return driver


def generate_client_id() -> str:
    """c-XXXXXXXX 形式のクライアントIDを生成"""
    return f"c-{uuid.uuid4().hex[:8]}"


def generate_display_code(index: int) -> str:
    """A-001 形式の表示コードを生成"""
    return f"A-{index:03d}"


def run_migration(driver, dry_run: bool = False):
    """
    仮名化マイグレーションを実行

    1. 全 Client ノードに clientId と displayCode を付与
    2. 各 Client から Identity ノードを分離作成
    3. 監査ログを記録
    """
    print("=" * 60)
    print("仮名化スキーマ・マイグレーション")
    print("=" * 60)

    with driver.session() as session:
        # 現在の Client ノードを取得
        result = session.run("""
            MATCH (c:Client)
            RETURN c.name as name,
                   c.dob as dob,
                   c.clientId as clientId,
                   c.displayCode as displayCode
            ORDER BY c.name
        """)
        clients = [record.data() for record in result]

    print(f"\n対象クライアント数: {len(clients)}")

    if not clients:
        print("マイグレーション対象のクライアントがありません。")
        return

    migrated = 0
    skipped = 0

    for idx, client in enumerate(clients, start=1):
        name = client['name']
        existing_id = client.get('clientId')
        existing_code = client.get('displayCode')

        if existing_id and existing_code:
            print(f"  スキップ: {name} (既に移行済み: {existing_id}, {existing_code})")
            skipped += 1
            continue

        # 新しいID生成
        client_id = existing_id or generate_client_id()
        display_code = existing_code or generate_display_code(idx)
        dob = client.get('dob')

        print(f"  移行: {name} → clientId={client_id}, displayCode={display_code}")

        if not dry_run:
            with driver.session() as session:
                # 1. Client ノードに clientId と displayCode を追加
                session.run("""
                    MATCH (c:Client {name: $name})
                    SET c.clientId = $clientId,
                        c.displayCode = $displayCode
                """, {
                    "name": name,
                    "clientId": client_id,
                    "displayCode": display_code
                })

                # 2. Identity ノードを作成し紐付け
                session.run("""
                    MATCH (c:Client {name: $name})
                    MERGE (i:Identity {clientId: $clientId})
                    SET i.name = $name,
                        i.dob = c.dob
                    MERGE (c)-[:HAS_IDENTITY]->(i)
                """, {
                    "name": name,
                    "clientId": client_id
                })

                # 3. 監査ログ
                session.run("""
                    CREATE (al:AuditLog {
                        timestamp: datetime(),
                        user: 'migration_script',
                        action: 'MIGRATE',
                        targetType: 'Client',
                        targetName: $name,
                        details: 'Pseudonymization migration: added clientId=' + $clientId + ', displayCode=' + $displayCode,
                        clientName: $name
                    })
                """, {
                    "name": name,
                    "clientId": client_id,
                    "displayCode": display_code
                })

        migrated += 1

    # インデックス作成
    if not dry_run and migrated > 0:
        print("\nインデックスを作成中...")
        with driver.session() as session:
            session.run("CREATE INDEX client_clientId IF NOT EXISTS FOR (c:Client) ON (c.clientId)")
            session.run("CREATE INDEX client_displayCode IF NOT EXISTS FOR (c:Client) ON (c.displayCode)")
            session.run("CREATE INDEX identity_clientId IF NOT EXISTS FOR (i:Identity) ON (i.clientId)")
        print("  インデックス作成完了")

    print(f"\n結果: {migrated} 移行, {skipped} スキップ")

    if dry_run:
        print("\n[ドライラン] 実際の変更は行われていません。")
        print("実行するには --dry-run を外してください。")
    else:
        print("\n移行完了。.env に以下を設定してください:")
        print("  PSEUDONYMIZATION_ENABLED=true")


def run_rollback(driver, dry_run: bool = False):
    """
    仮名化マイグレーションをロールバック

    1. Identity ノードと HAS_IDENTITY リレーションを削除
    2. Client ノードから clientId と displayCode を削除
    3. 監査ログを記録
    """
    print("=" * 60)
    print("仮名化スキーマ・ロールバック")
    print("=" * 60)

    with driver.session() as session:
        # 影響確認
        identity_count = session.run("MATCH (i:Identity) RETURN count(i) as c").single()['c']
        client_count = session.run(
            "MATCH (c:Client) WHERE c.clientId IS NOT NULL RETURN count(c) as c"
        ).single()['c']

    print(f"\n対象:")
    print(f"  Identity ノード: {identity_count}")
    print(f"  clientId 付き Client: {client_count}")

    if identity_count == 0 and client_count == 0:
        print("ロールバック対象がありません。")
        return

    if not dry_run:
        with driver.session() as session:
            # 1. Identity ノードと関連リレーションを削除
            session.run("MATCH (i:Identity) DETACH DELETE i")
            print("  Identity ノードを削除しました")

            # 2. Client の clientId と displayCode を削除
            session.run("""
                MATCH (c:Client)
                WHERE c.clientId IS NOT NULL
                REMOVE c.clientId, c.displayCode
            """)
            print("  clientId, displayCode を削除しました")

            # 3. インデックス削除
            try:
                session.run("DROP INDEX client_clientId IF EXISTS")
                session.run("DROP INDEX client_displayCode IF EXISTS")
                session.run("DROP INDEX identity_clientId IF EXISTS")
                print("  インデックスを削除しました")
            except Exception:
                pass  # インデックスが存在しない場合は無視

            # 4. 監査ログ
            session.run("""
                CREATE (al:AuditLog {
                    timestamp: datetime(),
                    user: 'migration_script',
                    action: 'ROLLBACK',
                    targetType: 'Schema',
                    targetName: 'pseudonymization',
                    details: 'Rolled back pseudonymization migration',
                    clientName: ''
                })
            """)

        print("\nロールバック完了。.env の設定:")
        print("  PSEUDONYMIZATION_ENABLED=false")
    else:
        print("\n[ドライラン] 実際の変更は行われていません。")


def main():
    parser = argparse.ArgumentParser(
        description="仮名化スキーマ・マイグレーションスクリプト"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（変更なし、影響確認のみ）"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="マイグレーションをロールバック"
    )
    args = parser.parse_args()

    try:
        driver = get_driver()
        print("Neo4j 接続成功")
    except Exception as e:
        print(f"Neo4j 接続失敗: {e}")
        print("  NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD を確認してください。")
        sys.exit(1)

    try:
        if args.rollback:
            run_rollback(driver, dry_run=args.dry_run)
        else:
            run_migration(driver, dry_run=args.dry_run)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
