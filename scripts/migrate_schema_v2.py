#!/usr/bin/env python
"""
Neo4j スキーマ改善マイグレーションスクリプト v2

段階的にデータベーススキーマを改善します。
各フェーズは独立して実行可能です。

使用方法:
    cd neo4j-agno-agent

    # 全フェーズを順次実行
    uv run python scripts/migrate_schema_v2.py

    # 特定フェーズのみ実行
    uv run python scripts/migrate_schema_v2.py --phase 0
    uv run python scripts/migrate_schema_v2.py --phase 1

    # ドライラン（変更を適用せずに確認）
    uv run python scripts/migrate_schema_v2.py --dry-run

    # スナップショットのみ取得
    uv run python scripts/migrate_schema_v2.py --snapshot

注意:
    - 実行前に必ず ./scripts/backup.sh でバックアップを取得してください
    - 対象: port 7687（障害福祉DB）のみ
"""

import argparse
import json
import os
import sys
from datetime import datetime

# 親ディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


# =============================================================================
# ユーティリティ
# =============================================================================

def get_driver():
    """Neo4j ドライバーを取得"""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    driver = GraphDatabase.driver(uri, auth=(username, password))
    driver.verify_connectivity()
    return driver


def run_query(driver, query, params=None):
    """クエリを実行して結果を返す"""
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


def run_write(driver, query, params=None):
    """書き込みクエリを実行（トランザクション内）"""
    with driver.session() as session:
        result = session.run(query, params or {})
        summary = result.consume()
        return summary.counters


def print_header(title):
    """セクションヘッダーを表示"""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step, description):
    """ステップ表示"""
    print(f"\n  [{step}] {description}")
    print(f"  {'-' * 50}")


# =============================================================================
# スナップショット
# =============================================================================

def take_snapshot(driver):
    """データベースのスナップショットを取得"""
    print_header("📸 データベーススナップショット")

    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "nodes": {},
        "relationships": {},
        "indexes": [],
        "constraints": [],
    }

    # ノード数
    print("\n  ノード数:")
    nodes = run_query(driver, """
        MATCH (n)
        RETURN labels(n)[0] AS label, count(n) AS count
        ORDER BY label
    """)
    for row in nodes:
        label = row["label"]
        count = row["count"]
        snapshot["nodes"][label] = count
        print(f"    {label}: {count}")

    # リレーション数
    print("\n  リレーション数:")
    rels = run_query(driver, """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(r) AS count
        ORDER BY type
    """)
    for row in rels:
        rel_type = row["type"]
        count = row["count"]
        snapshot["relationships"][rel_type] = count
        print(f"    {rel_type}: {count}")

    # インデックス
    print("\n  インデックス:")
    try:
        indexes = run_query(driver, "SHOW INDEXES YIELD name, type, labelsOrTypes, properties")
        for idx in indexes:
            snapshot["indexes"].append(idx)
            print(f"    {idx['name']}: {idx['type']} on {idx.get('labelsOrTypes', '?')}.{idx.get('properties', '?')}")
        if not indexes:
            print("    (なし)")
    except Exception as e:
        print(f"    ⚠️ インデックス情報の取得に失敗: {e}")

    # 制約
    print("\n  制約:")
    try:
        constraints = run_query(driver, "SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties")
        for c in constraints:
            snapshot["constraints"].append(c)
            print(f"    {c['name']}: {c['type']} on {c.get('labelsOrTypes', '?')}.{c.get('properties', '?')}")
        if not constraints:
            print("    (なし)")
    except Exception as e:
        print(f"    ⚠️ 制約情報の取得に失敗: {e}")

    # スナップショットをファイルに保存
    snapshot_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "neo4j_backup")
    os.makedirs(snapshot_dir, exist_ok=True)
    snapshot_file = os.path.join(snapshot_dir, f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  💾 スナップショット保存: {snapshot_file}")

    return snapshot


# =============================================================================
# フェーズ 0: 旧リレーション名のマイグレーション + ServiceProvider 正規化
# =============================================================================

LEGACY_RELATIONSHIP_MIGRATIONS = [
    {
        "old": "PROHIBITED",
        "new": "MUST_AVOID",
        "source": "Client",
        "target": "NgAction",
        "copy_properties": False,
        "query": """
            MATCH (c:Client)-[old:PROHIBITED]->(ng:NgAction)
            WHERE NOT (c)-[:MUST_AVOID]->(ng)
            CREATE (c)-[:MUST_AVOID]->(ng)
            DELETE old
            RETURN count(*) AS migrated
        """,
    },
    {
        "old": "PREFERS",
        "new": "REQUIRES",
        "source": "Client",
        "target": "CarePreference",
        "copy_properties": False,
        "query": """
            MATCH (c:Client)-[old:PREFERS]->(cp:CarePreference)
            WHERE NOT (c)-[:REQUIRES]->(cp)
            CREATE (c)-[:REQUIRES]->(cp)
            DELETE old
            RETURN count(*) AS migrated
        """,
    },
    {
        "old": "EMERGENCY_CONTACT",
        "new": "HAS_KEY_PERSON",
        "source": "Client",
        "target": "KeyPerson",
        "copy_properties": True,
        "query": """
            MATCH (c:Client)-[old:EMERGENCY_CONTACT]->(kp:KeyPerson)
            WHERE NOT (c)-[:HAS_KEY_PERSON]->(kp)
            CREATE (c)-[r:HAS_KEY_PERSON]->(kp)
            SET r.rank = COALESCE(old.rank, 99)
            DELETE old
            RETURN count(*) AS migrated
        """,
    },
    {
        "old": "RELATES_TO",
        "new": "IN_CONTEXT",
        "source": "NgAction",
        "target": "Condition",
        "copy_properties": False,
        "query": """
            MATCH (ng:NgAction)-[old:RELATES_TO]->(cond:Condition)
            WHERE NOT (ng)-[:IN_CONTEXT]->(cond)
            CREATE (ng)-[:IN_CONTEXT]->(cond)
            DELETE old
            RETURN count(*) AS migrated
        """,
    },
    {
        "old": "HAS_GUARDIAN",
        "new": "HAS_LEGAL_REP",
        "source": "Client",
        "target": "Guardian",
        "copy_properties": False,
        "query": """
            MATCH (c:Client)-[old:HAS_GUARDIAN]->(g:Guardian)
            WHERE NOT (c)-[:HAS_LEGAL_REP]->(g)
            CREATE (c)-[:HAS_LEGAL_REP]->(g)
            DELETE old
            RETURN count(*) AS migrated
        """,
    },
    {
        "old": "HOLDS",
        "new": "HAS_CERTIFICATE",
        "source": "Client",
        "target": "Certificate",
        "copy_properties": False,
        "query": """
            MATCH (c:Client)-[old:HOLDS]->(cert:Certificate)
            WHERE NOT (c)-[:HAS_CERTIFICATE]->(cert)
            CREATE (c)-[:HAS_CERTIFICATE]->(cert)
            DELETE old
            RETURN count(*) AS migrated
        """,
    },
]


def check_legacy_relationships(driver):
    """旧リレーションの残存数を確認"""
    result = run_query(driver, """
        OPTIONAL MATCH ()-[r1:PROHIBITED]->()
        WITH count(r1) AS prohibited
        OPTIONAL MATCH ()-[r2:PREFERS]->()
        WITH prohibited, count(r2) AS prefers
        OPTIONAL MATCH ()-[r3:EMERGENCY_CONTACT]->()
        WITH prohibited, prefers, count(r3) AS emergency
        OPTIONAL MATCH ()-[r4:RELATES_TO]->()
        WITH prohibited, prefers, emergency, count(r4) AS relates
        OPTIONAL MATCH ()-[r5:HAS_GUARDIAN]->()
        WITH prohibited, prefers, emergency, relates, count(r5) AS guardian
        OPTIONAL MATCH ()-[r6:HOLDS]->()
        RETURN prohibited, prefers, emergency, relates, guardian, count(r6) AS holds
    """)

    if not result:
        return {}

    row = result[0]
    legacy = {
        "PROHIBITED": row.get("prohibited", 0),
        "PREFERS": row.get("prefers", 0),
        "EMERGENCY_CONTACT": row.get("emergency", 0),
        "RELATES_TO": row.get("relates", 0),
        "HAS_GUARDIAN": row.get("guardian", 0),
        "HOLDS": row.get("holds", 0),
    }
    return legacy


def phase_0(driver, dry_run=False):
    """フェーズ 0: 旧リレーション名のマイグレーション + ServiceProvider 正規化"""
    print_header("フェーズ 0: 準備（旧リレーション移行 + ServiceProvider 正規化）")

    # 0-1. 旧リレーションの確認
    print_step("0-1", "旧リレーションの残存確認")
    legacy = check_legacy_relationships(driver)
    total_legacy = sum(legacy.values())

    for old_name, count in legacy.items():
        status = "⚠️" if count > 0 else "✅"
        print(f"    {status} {old_name}: {count} 件")

    if total_legacy == 0:
        print("\n    ✅ 旧リレーションは残存していません。")
    else:
        print(f"\n    合計 {total_legacy} 件の旧リレーションを移行します。")

    # 0-2. 旧リレーションの移行
    if total_legacy > 0:
        print_step("0-2", "旧リレーションの移行")

        for migration in LEGACY_RELATIONSHIP_MIGRATIONS:
            old = migration["old"]
            new = migration["new"]
            count = legacy.get(old, 0)

            if count == 0:
                print(f"    ⏭️  {old} → {new}: スキップ（0件）")
                continue

            if dry_run:
                print(f"    🔍 {old} → {new}: {count} 件を移行予定（ドライラン）")
            else:
                result = run_query(driver, migration["query"])
                migrated = result[0]["migrated"] if result else 0
                print(f"    ✅ {old} → {new}: {migrated} 件を移行完了")

        # 移行後の確認
        if not dry_run:
            print_step("0-2b", "移行後の確認")
            remaining = check_legacy_relationships(driver)
            total_remaining = sum(remaining.values())
            if total_remaining == 0:
                print("    ✅ すべての旧リレーションが正常に移行されました。")
            else:
                print(f"    ⚠️ {total_remaining} 件の旧リレーションが残存しています:")
                for name, count in remaining.items():
                    if count > 0:
                        print(f"      {name}: {count} 件")

    # 0-3. ServiceProvider プロパティの正規化
    print_step("0-3", "ServiceProvider プロパティの正規化")

    # 正規化対象の確認
    sp_check = run_query(driver, """
        MATCH (sp:ServiceProvider)
        WHERE sp.office_name IS NOT NULL AND sp.name IS NULL
        RETURN count(sp) AS count
    """)
    sp_count = sp_check[0]["count"] if sp_check else 0

    if sp_count == 0:
        print("    ✅ 正規化対象の ServiceProvider はありません。")
    elif dry_run:
        print(f"    🔍 {sp_count} 件の ServiceProvider を正規化予定（ドライラン）")
    else:
        counters = run_write(driver, """
            MATCH (sp:ServiceProvider)
            WHERE sp.office_name IS NOT NULL AND sp.name IS NULL
            SET sp.name = sp.office_name,
                sp.corporateName = sp.corp_name,
                sp.serviceType = sp.service_type,
                sp.wamnetId = sp.office_number,
                sp.closedDays = sp.closed_days,
                sp.hoursWeekday = sp.hours_weekday,
                sp.updatedAt = sp.updated_at
            REMOVE sp.office_name, sp.corp_name, sp.service_type,
                   sp.office_number, sp.closed_days, sp.hours_weekday,
                   sp.updated_at
        """)
        print(f"    ✅ ServiceProvider 正規化完了: {counters.properties_set} プロパティを更新")

    print("\n  ✅ フェーズ 0 完了")


# =============================================================================
# フェーズ 1: インデックスと制約の追加
# =============================================================================

INDEXES_TO_CREATE = [
    # 検索パフォーマンス向上
    # NOTE: Client.name はUNIQUE制約で自動インデックス化されるため除外
    ("idx_hospital_name", "Hospital", "name"),
    ("idx_supporter_name", "Supporter", "name"),
    ("idx_keyperson_name", "KeyPerson", "name"),
    ("idx_condition_name", "Condition", "name"),
    ("idx_ngaction_risklevel", "NgAction", "riskLevel"),
    ("idx_carepreference_category", "CarePreference", "category"),
    # 日付ベースのクエリ高速化
    ("idx_supportlog_date", "SupportLog", "date"),
    ("idx_certificate_renewal", "Certificate", "nextRenewalDate"),
    # 監査ログクエリ高速化
    ("idx_auditlog_timestamp", "AuditLog", "timestamp"),
    ("idx_auditlog_clientname", "AuditLog", "clientName"),
    ("idx_auditlog_user", "AuditLog", "user"),
]


def phase_1(driver, dry_run=False):
    """フェーズ 1: インデックスと制約の追加"""
    print_header("フェーズ 1: インデックスと制約の追加")

    # 1-1. インデックス追加
    print_step("1-1", "インデックスの追加")

    for idx_name, label, prop in INDEXES_TO_CREATE:
        query = f"CREATE INDEX {idx_name} IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
        if dry_run:
            print(f"    🔍 {idx_name}: {label}.{prop}（ドライラン）")
        else:
            try:
                run_write(driver, query)
                print(f"    ✅ {idx_name}: {label}.{prop}")
            except Exception as e:
                print(f"    ❌ {idx_name}: {e}")

    # 1-2. 一意性制約（Community Edition で利用可能なもの）
    # UNIQUE制約は自動的にインデックスを含むため、同じプロパティに
    # 既存のRANGEインデックスがあると競合する。事前に削除が必要。
    print_step("1-2", "一意性制約の追加")

    uniqueness_constraints = [
        ("constraint_client_name_unique", "Client", "name"),
    ]

    for name, label, prop in uniqueness_constraints:
        if not dry_run:
            # 同じプロパティの既存インデックスを検出・削除（制約との競合回避）
            try:
                existing = run_query(driver, """
                    SHOW INDEXES
                    YIELD name, type, labelsOrTypes, properties
                    WHERE type <> 'LOOKUP'
                      AND $label IN labelsOrTypes
                      AND $prop IN properties
                    RETURN name, type
                """, {"label": label, "prop": prop})
                for idx in existing:
                    idx_name = idx["name"]
                    idx_type = idx["type"]
                    # 既にUNIQUENESS制約のインデックスならスキップ
                    if idx_type == "RANGE":
                        run_write(driver, f"DROP INDEX {idx_name} IF EXISTS")
                        print(f"    🔄 既存インデックス {idx_name} を削除（制約に置換）")
            except Exception as e:
                print(f"    ⚠️ 既存インデックス確認中にエラー: {e}")

        query = f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
        if dry_run:
            print(f"    🔍 {name}: {label}.{prop} UNIQUE（ドライラン）")
        else:
            try:
                run_write(driver, query)
                print(f"    ✅ {name}: {label}.{prop} UNIQUE")
            except Exception as e:
                print(f"    ❌ {name}: {e}")

    # 1-3. NOT NULL 制約（Community Edition での対応確認）
    print_step("1-3", "NOT NULL 制約の追加")

    not_null_constraints = [
        ("constraint_client_name_not_null", "Client", "name"),
        ("constraint_client_dob_not_null", "Client", "dob"),
        ("constraint_supportlog_date_not_null", "SupportLog", "date"),
    ]

    # まずテストクエリで NOT NULL 制約がサポートされているか確認
    not_null_supported = True
    try:
        # 存在しないラベルでテスト（副作用なし）
        run_write(driver, """
            CREATE CONSTRAINT _test_not_null_support IF NOT EXISTS
            FOR (n:_TestNotNullSupport) REQUIRE n._test IS NOT NULL
        """)
        # テスト制約を削除
        run_write(driver, "DROP CONSTRAINT _test_not_null_support IF EXISTS")
    except Exception:
        not_null_supported = False
        print("    ⚠️ NOT NULL 制約は Community Edition ではサポートされていません。")
        print("    → アプリケーションレベルでバリデーションを追加します。")

    if not_null_supported:
        for name, label, prop in not_null_constraints:
            # Certificate.nextRenewalDate は NULL が許容されるケースがあるため除外
            query = f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS NOT NULL"

            # 事前チェック: NULL データが存在しないか確認
            null_check = run_query(driver, f"""
                MATCH (n:{label})
                WHERE n.{prop} IS NULL
                RETURN count(n) AS count
            """)
            null_count = null_check[0]["count"] if null_check else 0

            if null_count > 0:
                print(f"    ⚠️ {name}: {label}.{prop} に NULL が {null_count} 件あるためスキップ")
                continue

            if dry_run:
                print(f"    🔍 {name}: {label}.{prop} NOT NULL（ドライラン）")
            else:
                try:
                    run_write(driver, query)
                    print(f"    ✅ {name}: {label}.{prop} NOT NULL")
                except Exception as e:
                    print(f"    ❌ {name}: {e}")

    print("\n  ✅ フェーズ 1 完了")


# =============================================================================
# フェーズ 2: AuditLog 接続性改善 + リレーションシッププロパティ追加
# =============================================================================

def phase_2(driver, dry_run=False):
    """フェーズ 2: AuditLog 接続性改善 + リレーションシッププロパティ追加"""
    print_header("フェーズ 2: AuditLog 接続性改善 + リレーションシッププロパティ追加")

    # 2-1. AuditLog → Client の AUDIT_FOR リレーション追加
    print_step("2-1", "AuditLog の Client 接続（AUDIT_FOR リレーション）")

    # 対象件数の確認
    audit_check = run_query(driver, """
        MATCH (al:AuditLog)
        WHERE al.clientName IS NOT NULL AND al.clientName <> ''
          AND NOT (al)-[:AUDIT_FOR]->(:Client)
        RETURN count(al) AS unlinked
    """)
    unlinked = audit_check[0]["unlinked"] if audit_check else 0

    if unlinked == 0:
        print("    ✅ すべての AuditLog は既に接続済みです。")
    elif dry_run:
        print(f"    🔍 {unlinked} 件の AuditLog を Client に接続予定（ドライラン）")

        # マッチ率を事前確認
        match_check = run_query(driver, """
            MATCH (al:AuditLog)
            WHERE al.clientName IS NOT NULL AND al.clientName <> ''
              AND NOT (al)-[:AUDIT_FOR]->(:Client)
            OPTIONAL MATCH (c:Client {name: al.clientName})
            RETURN
                count(al) AS total,
                count(c) AS matched,
                count(al) - count(c) AS unmatched
        """)
        if match_check:
            row = match_check[0]
            print(f"    📊 マッチ率: {row['matched']}/{row['total']} "
                  f"（未マッチ: {row['unmatched']} 件）")
    else:
        counters = run_write(driver, """
            MATCH (al:AuditLog)
            WHERE al.clientName IS NOT NULL AND al.clientName <> ''
              AND NOT (al)-[:AUDIT_FOR]->(:Client)
            MATCH (c:Client {name: al.clientName})
            CREATE (al)-[:AUDIT_FOR]->(c)
        """)
        print(f"    ✅ AUDIT_FOR リレーション作成: {counters.relationships_created} 件")

        # 未マッチ件数の確認
        remaining = run_query(driver, """
            MATCH (al:AuditLog)
            WHERE al.clientName IS NOT NULL AND al.clientName <> ''
              AND NOT (al)-[:AUDIT_FOR]->(:Client)
            RETURN count(al) AS count
        """)
        remaining_count = remaining[0]["count"] if remaining else 0
        if remaining_count > 0:
            print(f"    ⚠️ Client 名が一致しない AuditLog: {remaining_count} 件")

    # AUDIT_FOR のインデックス
    if not dry_run:
        try:
            run_write(driver, """
                CREATE INDEX idx_auditlog_audit_for IF NOT EXISTS
                FOR ()-[r:AUDIT_FOR]-() ON (r)
            """)
        except Exception:
            pass  # リレーションインデックスは Community Edition で非対応の場合がある

    # 2-2. リレーションシッププロパティ追加
    print_step("2-2", "リレーションシッププロパティの追加")
    print("    ※ 既存リレーションへの後付けは行わず、新規作成時にのみ適用します。")
    print("    → lib/db_operations.py の register_to_database() を更新してください。")

    rel_properties = [
        ("TREATED_AT", "since (Date), status (String: Active/Ended)"),
        ("SUPPORTED_BY", "since (Date), until (Date)"),
        ("HAS_CONDITION", "diagnosedDate (Date), severity (String)"),
        ("HAS_CERTIFICATE", "issuedDate (Date), status (String: Active/Expired)"),
    ]

    for rel, props in rel_properties:
        print(f"    📋 {rel}: {props}")

    print("\n  ✅ フェーズ 2 完了")


# =============================================================================
# フェーズ 3: SupportLog 構造改善
# =============================================================================

def phase_3(driver, dry_run=False):
    """フェーズ 3: SupportLog 構造改善"""
    print_header("フェーズ 3: SupportLog 構造改善")

    # 3-1. 既存 SupportLog に type のデフォルト値を設定
    print_step("3-1", "既存 SupportLog に type プロパティを追加")

    type_check = run_query(driver, """
        MATCH (log:SupportLog)
        WHERE log.type IS NULL
        RETURN count(log) AS count
    """)
    null_type_count = type_check[0]["count"] if type_check else 0

    if null_type_count == 0:
        print("    ✅ すべての SupportLog に type が設定済みです。")
    elif dry_run:
        print(f"    🔍 {null_type_count} 件の SupportLog に type='日常記録' を設定予定（ドライラン）")
    else:
        counters = run_write(driver, """
            MATCH (log:SupportLog)
            WHERE log.type IS NULL
            SET log.type = '日常記録'
        """)
        print(f"    ✅ {counters.properties_set} 件のプロパティを設定")

    # 3-2. SupportLog 間の FOLLOWS リレーション生成
    print_step("3-2", "SupportLog 間の FOLLOWS リレーション生成")

    # 既存の FOLLOWS 数を確認
    follows_check = run_query(driver, """
        MATCH (:SupportLog)-[f:FOLLOWS]->(:SupportLog)
        RETURN count(f) AS count
    """)
    existing_follows = follows_check[0]["count"] if follows_check else 0

    if existing_follows > 0:
        print(f"    ℹ️ 既存の FOLLOWS リレーション: {existing_follows} 件")

    # クライアントごとに SupportLog チェーンを構築
    clients_with_logs = run_query(driver, """
        MATCH (log:SupportLog)-[:ABOUT]->(c:Client)
        WITH c, count(log) AS logCount
        WHERE logCount >= 2
        RETURN c.name AS clientName, logCount
        ORDER BY c.name
    """)

    if not clients_with_logs:
        print("    ✅ FOLLOWS リレーションの対象がありません。")
    elif dry_run:
        total_logs = sum(c["logCount"] for c in clients_with_logs)
        print(f"    🔍 {len(clients_with_logs)} クライアント、計 {total_logs} 件の"
              f" SupportLog に FOLLOWS を設定予定（ドライラン）")
    else:
        total_created = 0
        for client in clients_with_logs:
            name = client["clientName"]
            # クライアントごとに日付順でチェーン化
            result = run_query(driver, """
                MATCH (log:SupportLog)-[:ABOUT]->(c:Client {name: $name})
                WHERE NOT (log)-[:FOLLOWS]->(:SupportLog)
                WITH c, log ORDER BY log.date DESC
                WITH c, collect(log) AS logs
                UNWIND range(0, size(logs) - 2) AS i
                WITH logs[i] AS newer, logs[i + 1] AS older
                CREATE (newer)-[:FOLLOWS]->(older)
                RETURN count(*) AS created
            """, {"name": name})
            created = result[0]["created"] if result else 0
            total_created += created

        print(f"    ✅ FOLLOWS リレーション作成: {total_created} 件")

    # 3-3. SupportLog インデックス（type 用）
    print_step("3-3", "SupportLog.type インデックスの追加")
    if dry_run:
        print("    🔍 idx_supportlog_type: SupportLog.type（ドライラン）")
    else:
        try:
            run_write(driver, """
                CREATE INDEX idx_supportlog_type IF NOT EXISTS
                FOR (log:SupportLog) ON (log.type)
            """)
            print("    ✅ idx_supportlog_type: SupportLog.type")
        except Exception as e:
            print(f"    ❌ {e}")

    print("\n  ✅ フェーズ 3 完了")


# =============================================================================
# フェーズ 4: 全文検索インデックス
# =============================================================================

def phase_4(driver, dry_run=False):
    """フェーズ 4: 全文検索インデックス"""
    print_header("フェーズ 4: 全文検索インデックス")

    fulltext_indexes = [
        {
            "name": "idx_supportlog_fulltext",
            "label": "SupportLog",
            "properties": ["situation", "action", "note"],
            "query": """
                CREATE FULLTEXT INDEX idx_supportlog_fulltext IF NOT EXISTS
                FOR (n:SupportLog) ON EACH [n.situation, n.action, n.note]
            """,
        },
        {
            "name": "idx_lifehistory_fulltext",
            "label": "LifeHistory",
            "properties": ["episode"],
            "query": """
                CREATE FULLTEXT INDEX idx_lifehistory_fulltext IF NOT EXISTS
                FOR (n:LifeHistory) ON EACH [n.episode]
            """,
        },
    ]

    for idx in fulltext_indexes:
        print_step(f"4-{fulltext_indexes.index(idx) + 1}",
                   f"{idx['label']} 全文検索インデックス")

        if dry_run:
            print(f"    🔍 {idx['name']}: {idx['label']}.{idx['properties']}（ドライラン）")
        else:
            try:
                run_write(driver, idx["query"])
                print(f"    ✅ {idx['name']}: {idx['label']}.{idx['properties']}")
            except Exception as e:
                print(f"    ❌ {idx['name']}: {e}")

    print("\n  ⚠️ 注意: Neo4j の全文検索はデフォルトで英語アナライザーを使用します。")
    print("    日本語テキストの形態素解析には制限があります。")
    print("    CONTAINS との併用を推奨します。")

    print("\n  ✅ フェーズ 4 完了")


# =============================================================================
# メイン処理
# =============================================================================

PHASES = {
    0: ("準備（旧リレーション移行 + ServiceProvider 正規化）", phase_0),
    1: ("インデックスと制約の追加", phase_1),
    2: ("AuditLog 接続性改善 + リレーションシッププロパティ", phase_2),
    3: ("SupportLog 構造改善", phase_3),
    4: ("全文検索インデックス", phase_4),
}


def main():
    parser = argparse.ArgumentParser(
        description="Neo4j スキーマ改善マイグレーション v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--phase", type=int, choices=list(PHASES.keys()),
                        help="特定のフェーズのみ実行（0-4）")
    parser.add_argument("--dry-run", action="store_true",
                        help="ドライラン（変更を適用せずに確認）")
    parser.add_argument("--snapshot", action="store_true",
                        help="スナップショットのみ取得")

    args = parser.parse_args()

    print_header("Neo4j スキーマ改善マイグレーション v2")
    print(f"  日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.dry_run:
        print("  モード: 🔍 ドライラン（変更は適用されません）")

    # Neo4j 接続
    try:
        driver = get_driver()
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        print(f"  Neo4j: {uri}")
    except Exception as e:
        print(f"\n  ❌ Neo4j 接続失敗: {e}")
        sys.exit(1)

    # スナップショット取得
    take_snapshot(driver)

    if args.snapshot:
        driver.close()
        return

    # フェーズ選択
    if args.phase is not None:
        phases_to_run = [args.phase]
    else:
        phases_to_run = sorted(PHASES.keys())

    # 確認プロンプト
    if not args.dry_run:
        print()
        print("  実行予定のフェーズ:")
        for p in phases_to_run:
            print(f"    フェーズ {p}: {PHASES[p][0]}")
        print()
        confirm = input("  実行しますか？ (yes/no): ").strip().lower()
        if confirm != "yes":
            print("  キャンセルしました。")
            driver.close()
            return

    # フェーズ実行
    for phase_num in phases_to_run:
        phase_name, phase_func = PHASES[phase_num]
        try:
            phase_func(driver, dry_run=args.dry_run)
        except Exception as e:
            print(f"\n  ❌ フェーズ {phase_num} でエラー: {e}")
            print("  後続のフェーズはスキップします。")
            break

    # 実行後のスナップショット
    if not args.dry_run and not args.snapshot:
        print()
        print("  --- 実行後のスナップショット ---")
        take_snapshot(driver)

    driver.close()

    print_header("マイグレーション完了")


if __name__ == "__main__":
    main()
