"""
親亡き後支援データベース - データベース操作モジュール
Neo4j接続、クエリ実行、データ登録処理、監査ログ

仮名化対応:
- クライアントは clientId (UUID) で内部識別
- 氏名は Identity ノードに分離
- 表示時のみ結合（resolve_client で解決）
"""

import os
import sys
from datetime import date, datetime
from typing import Optional
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

# 仮名化スキーマが有効かどうか（マイグレーション後に True に設定）
PSEUDONYMIZATION_ENABLED = os.getenv("PSEUDONYMIZATION_ENABLED", "false").lower() == "true"

# --- ログ出力 ---
def log(message: str, level: str = "INFO"):
    """ログ出力（標準エラー出力）"""
    sys.stderr.write(f"[DB_Operations:{level}] {message}\n")
    sys.stderr.flush()

# --- Neo4j 接続 ---
_driver = None

def get_driver():
    """Neo4jドライバーを取得（シングルトン）"""
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        pwd = os.getenv("NEO4J_PASSWORD")
        if not uri or not user:
            log("NEO4J_URI または NEO4J_USERNAME が未設定です", "ERROR")
            return None
        try:
            _driver = GraphDatabase.driver(uri, auth=(user, pwd))
            _driver.verify_connectivity()
            log(f"Neo4j接続成功: {uri}")
        except Exception as e:
            log(f"Neo4j接続失敗: {e}", "ERROR")
            _driver = None
    return _driver


def is_db_available() -> bool:
    """Neo4jデータベースが利用可能かチェック"""
    try:
        driver = get_driver()
        if driver is None:
            return False
        driver.verify_connectivity()
        return True
    except Exception:
        return False


def run_query(query, params=None):
    """Cypherクエリ実行ヘルパー"""
    try:
        driver = get_driver()
        if driver is None:
            log("ドライバー未初期化のためクエリをスキップ", "WARN")
            return []
        with driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]
    except Exception as e:
        log(f"クエリ実行エラー: {e}", "ERROR")
        return []


# =============================================================================
# 監査ログ機能
# =============================================================================

def create_audit_log(
    user_name: str,
    action: str,
    target_type: str,
    target_name: str,
    details: str = "",
    client_name: str = None
) -> dict:
    """
    監査ログを作成

    Args:
        user_name: 操作を行ったユーザー名
        action: 操作種別（CREATE, UPDATE, DELETE, READ）
        target_type: 対象ノードタイプ（Client, NgAction, CarePreference等）
        target_name: 対象の識別名
        details: 操作の詳細（任意）
        client_name: 関連するクライアント名（任意）

    Returns:
        作成された監査ログ情報
    """
    result = run_query("""
        CREATE (al:AuditLog {
            timestamp: datetime(),
            user: $user_name,
            action: $action,
            targetType: $target_type,
            targetName: $target_name,
            details: $details,
            clientName: $client_name
        })
        RETURN al.timestamp as timestamp, al.action as action
    """, {
        "user_name": user_name,
        "action": action,
        "target_type": target_type,
        "target_name": target_name,
        "details": details,
        "client_name": client_name or ""
    })

    log(f"監査ログ記録: {user_name} - {action} - {target_type}:{target_name}")
    return result[0] if result else {}


def get_audit_logs(
    client_name: str = None,
    user_name: str = None,
    action: str = None,
    limit: int = 50
) -> list:
    """
    監査ログを取得

    Args:
        client_name: クライアント名でフィルタ（任意）
        user_name: ユーザー名でフィルタ（任意）
        action: 操作種別でフィルタ（任意）
        limit: 取得件数（デフォルト50件）

    Returns:
        監査ログのリスト
    """
    return run_query("""
        MATCH (al:AuditLog)
        WHERE ($client_name = '' OR al.clientName CONTAINS $client_name)
          AND ($user_name = '' OR al.user CONTAINS $user_name)
          AND ($action = '' OR al.action = $action)
        RETURN al.timestamp as 日時,
               al.user as 操作者,
               al.action as 操作,
               al.targetType as 対象種別,
               al.targetName as 対象名,
               al.details as 詳細,
               al.clientName as クライアント
        ORDER BY al.timestamp DESC
        LIMIT $limit
    """, {
        "client_name": client_name or "",
        "user_name": user_name or "",
        "action": action or "",
        "limit": limit
    })


def get_client_change_history(client_name: str, limit: int = 20) -> list:
    """
    特定クライアントに関する変更履歴を取得

    Args:
        client_name: クライアント名
        limit: 取得件数

    Returns:
        変更履歴のリスト
    """
    return run_query("""
        MATCH (al:AuditLog)
        WHERE al.clientName CONTAINS $client_name
        RETURN al.timestamp as 日時,
               al.user as 操作者,
               al.action as 操作,
               al.targetType as 対象種別,
               al.targetName as 内容,
               al.details as 詳細
        ORDER BY al.timestamp DESC
        LIMIT $limit
    """, {"client_name": client_name, "limit": limit})


def register_support_log(log_data: dict, client_name: str) -> dict:
    """
    支援記録（SupportLog）をデータベースに登録

    Args:
        log_data: 支援記録データ（supportLogs配列の1要素）
        client_name: クライアント名

    Returns:
        登録結果
    """
    # Supporterノードを作成/取得
    run_query("""
        MERGE (s:Supporter {name: $supporter})
    """, {"supporter": log_data['supporter']})

    # SupportLogノードを作成し、関係を構築
    result = run_query("""
        MATCH (c:Client {name: $client_name})
        MATCH (s:Supporter {name: $supporter})

        CREATE (log:SupportLog {
            date: date($date),
            situation: $situation,
            action: $action,
            effectiveness: $effectiveness,
            note: $note
        })

        CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c)

        RETURN log.date as date, log.situation as situation
    """, {
        "client_name": client_name,
        "supporter": log_data['supporter'],
        "date": log_data['date'],
        "situation": log_data['situation'],
        "action": log_data['action'],
        "effectiveness": log_data['effectiveness'],
        "note": log_data.get('note', '')
    })

    if result:
        return {
            "status": "success",
            "message": f"支援記録を登録: {log_data['situation']}",
            "data": result[0]
        }
    else:
        return {
            "status": "error",
            "message": f"クライアント '{client_name}' が見つかりません"
        }


def register_to_database(data: dict, user_name: str = "system") -> dict:
    """
    構造化データをNeo4jに登録（監査ログ付き）

    Args:
        data: AI構造化されたクライアントデータ（dict）
        user_name: 登録を行うユーザー名（デフォルト: "system"）

    Returns:
        登録結果のサマリー
    """
    client_name = data['client']['name']
    registered_items = []

    # 1. クライアント基本情報
    run_query("""
        MERGE (c:Client {name: $name})
        SET c.dob = CASE WHEN $dob IS NOT NULL THEN date($dob) ELSE c.dob END,
            c.bloodType = COALESCE($blood, c.bloodType),
            c.kana = COALESCE($kana, c.kana),
            c.aliases = $aliases
    """, {
        "name": client_name,
        "dob": data['client'].get('dob'),
        "blood": data['client'].get('bloodType'),
        "kana": data['client'].get('kana'),
        "aliases": data['client'].get('aliases', [])
    })

    # 監査ログ: クライアント登録/更新
    create_audit_log(
        user_name=user_name,
        action="CREATE",
        target_type="Client",
        target_name=client_name,
        details=f"基本情報登録/更新",
        client_name=client_name
    )
    registered_items.append("Client")

    # 2. 特性・診断
    for cond in data.get('conditions', []):
        if cond.get('name'):
            run_query("""
                MATCH (c:Client {name: $client})
                MERGE (con:Condition {name: $name})
                SET con.status = $status
                MERGE (c)-[:HAS_CONDITION]->(con)
            """, {"client": client_name, "name": cond['name'], "status": cond.get('status', 'Active')})

    # 3. 禁忌事項（NgAction）- 最重要データのため詳細ログ
    for ng in data.get('ngActions', []):
        if ng.get('action'):
            run_query("""
                MATCH (c:Client {name: $client})
                CREATE (ng:NgAction {action: $action, reason: $reason, riskLevel: $risk})
                CREATE (c)-[:MUST_AVOID]->(ng)
            """, {
                "client": client_name,
                "action": ng['action'],
                "reason": ng.get('reason', ''),
                "risk": ng.get('riskLevel', 'Panic')
            })

            # 監査ログ: 禁忌事項（安全に関わる重要データ）
            create_audit_log(
                user_name=user_name,
                action="CREATE",
                target_type="NgAction",
                target_name=ng['action'],
                details=f"リスクレベル: {ng.get('riskLevel', 'Panic')}, 理由: {ng.get('reason', '')}",
                client_name=client_name
            )
            registered_items.append("NgAction")

            # 関連特性との紐付け
            if ng.get('relatedCondition'):
                run_query("""
                    MATCH (ng:NgAction {action: $action})
                    MATCH (con:Condition {name: $cond})
                    MERGE (ng)-[:IN_CONTEXT]->(con)
                """, {"action": ng['action'], "cond": ng['relatedCondition']})

    # 4. 推奨ケア（CarePreference）
    for cp in data.get('carePreferences', []):
        if cp.get('instruction'):
            run_query("""
                MATCH (c:Client {name: $client})
                CREATE (cp:CarePreference {category: $cat, instruction: $inst, priority: $pri})
                CREATE (c)-[:REQUIRES]->(cp)
            """, {
                "client": client_name,
                "cat": cp.get('category', 'その他'),
                "inst": cp['instruction'],
                "pri": cp.get('priority', 'Medium')
            })

    # 5. 手帳・受給者証（Certificate）
    for cert in data.get('certificates', []):
        if cert.get('type'):
            run_query("""
                MATCH (c:Client {name: $client})
                CREATE (cert:Certificate {
                    type: $type,
                    grade: $grade,
                    nextRenewalDate: CASE WHEN $renewal IS NOT NULL THEN date($renewal) ELSE NULL END
                })
                CREATE (c)-[:HAS_CERTIFICATE]->(cert)
            """, {
                "client": client_name,
                "type": cert['type'],
                "grade": cert.get('grade'),
                "renewal": cert.get('nextRenewalDate')
            })

    # 6. キーパーソン（KeyPerson）
    for kp in data.get('keyPersons', []):
        if kp.get('name'):
            run_query("""
                MATCH (c:Client {name: $client})
                MERGE (kp:KeyPerson {name: $name, phone: $phone})
                SET kp.relationship = $rel, kp.role = $role
                MERGE (c)-[r:HAS_KEY_PERSON]->(kp)
                SET r.rank = $rank
            """, {
                "client": client_name,
                "name": kp['name'],
                "phone": kp.get('phone', ''),
                "rel": kp.get('relationship', ''),
                "role": kp.get('role', '緊急連絡先'),
                "rank": kp.get('rank', 1)
            })

    # 7. 後見人（Guardian）
    for g in data.get('guardians', []):
        if g.get('name'):
            run_query("""
                MATCH (c:Client {name: $client})
                CREATE (g:Guardian {name: $name, type: $type, phone: $phone, organization: $org})
                CREATE (c)-[:HAS_LEGAL_REP]->(g)
            """, {
                "client": client_name,
                "name": g['name'],
                "type": g.get('type', ''),
                "phone": g.get('phone', ''),
                "org": g.get('organization', '')
            })

    # 8. 医療機関（Hospital）
    for h in data.get('hospitals', []):
        if h.get('name'):
            run_query("""
                MATCH (c:Client {name: $client})
                MERGE (h:Hospital {name: $name})
                SET h.specialty = $spec, h.phone = $phone, h.doctor = $doc
                MERGE (c)-[:TREATED_AT]->(h)
            """, {
                "client": client_name,
                "name": h['name'],
                "spec": h.get('specialty', ''),
                "phone": h.get('phone', ''),
                "doc": h.get('doctor', '')
            })

    # 9. 生育歴（LifeHistory）
    for hist in data.get('lifeHistories', []):
        if hist.get('episode'):
            run_query("""
                MATCH (c:Client {name: $client})
                CREATE (h:LifeHistory {era: $era, episode: $episode, emotion: $emotion})
                CREATE (c)-[:HAS_HISTORY]->(h)
            """, {
                "client": client_name,
                "era": hist.get('era', ''),
                "episode": hist['episode'],
                "emotion": hist.get('emotion', '')
            })

    # 10. 願い（Wish）
    for wish in data.get('wishes', []):
        if wish.get('content'):
            run_query("""
                MATCH (c:Client {name: $client})
                CREATE (w:Wish {content: $content, status: 'Active', date: date($date)})
                CREATE (c)-[:HAS_WISH]->(w)
            """, {
                "client": client_name,
                "content": wish['content'],
                "date": wish.get('date', date.today().isoformat())
            })

    # 11. 支援記録（SupportLog）
    for support_log in data.get('supportLogs', []):
        if support_log.get('supporter') and support_log.get('action'):
            register_support_log(support_log, client_name)
            # 監査ログ: 支援記録
            create_audit_log(
                user_name=user_name,
                action="CREATE",
                target_type="SupportLog",
                target_name=f"{support_log.get('situation', '')} - {support_log.get('action', '')}",
                details=f"効果: {support_log.get('effectiveness', '')}",
                client_name=client_name
            )
            registered_items.append("SupportLog")

    # 登録サマリーをログ出力
    log(f"登録完了: {client_name} - 項目数: {len(registered_items)}")

    return {
        "client_name": client_name,
        "registered_count": len(registered_items),
        "registered_types": list(set(registered_items))
    }


def get_clients_list():
    """登録済みクライアント一覧を取得"""
    return [r['name'] for r in run_query("MATCH (c:Client) RETURN c.name as name ORDER BY c.name")]


def get_client_stats():
    """クライアント統計情報を取得"""
    client_count = run_query("MATCH (n:Client) RETURN count(n) as c")[0]['c']

    ng_by_client = run_query("""
        MATCH (c:Client)
        OPTIONAL MATCH (c)-[:MUST_AVOID]->(ng:NgAction)
        RETURN c.name as name, count(ng) as ng_count
        ORDER BY c.name
    """)

    return {
        'client_count': client_count,
        'ng_by_client': ng_by_client
    }


def get_support_logs(client_name: str, limit: int = 20):
    """
    特定クライアントの支援記録を取得

    Args:
        client_name: クライアント名
        limit: 取得件数（デフォルト20件）

    Returns:
        支援記録のリスト
    """
    return run_query("""
        MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c:Client {name: $client_name})
        RETURN log.date as 日付,
               s.name as 支援者,
               log.situation as 状況,
               log.action as 対応,
               log.effectiveness as 効果,
               log.note as メモ
        ORDER BY log.date DESC
        LIMIT $limit
    """, {"client_name": client_name, "limit": limit})


def discover_care_patterns(client_name: str, min_frequency: int = 3):
    """
    効果的なケアパターンを発見

    Args:
        client_name: クライアント名
        min_frequency: 最小出現回数

    Returns:
        発見されたパターンのリスト
    """
    return run_query("""
        MATCH (c:Client {name: $client_name})<-[:ABOUT]-(log:SupportLog)
        WHERE log.effectiveness = 'Effective'
        WITH c, log.situation as situation, log.action as action, count(*) as frequency
        WHERE frequency >= $min_frequency
        RETURN situation as 状況,
               action as 対応方法,
               frequency as 効果的だった回数
        ORDER BY frequency DESC
    """, {"client_name": client_name, "min_frequency": min_frequency})


# =============================================================================
# 仮名化対応機能
# =============================================================================

def normalize_identifier(text: str) -> str:
    """
    識別子を正規化する（敬称の削除など）

    Args:
        text: 入力テキスト

    Returns:
        正規化されたテキスト
    """
    if not text:
        return ""

    # 削除するサフィックス
    suffixes = [
        "さん", "くん", "ちゃん", "様", "氏", "殿",
        "San", "-san", "Chan", "-chan", "Kun", "-kun", "Sama", "-sama"
    ]

    normalized = text.strip()
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
            # 一つ削除したら終了（「〇〇さんさん」等は考慮しない）
            break

    return normalized


def resolve_client(identifier: str) -> Optional[dict]:
    """
    様々な識別子からクライアント情報を解決

    対応する識別子:
    - clientId (c-xxxx) : 仮名化後の内部ID
    - displayCode (A-001) : 表示用コード
    - name (山田健太, 山田健太さん) : 氏名
    - kana (やまだけんた) : ふりがな
    - aliases (ニックネーム) : 通称

    Args:
        identifier: クライアント識別子

    Returns:
        クライアント情報dict または None
    """
    # 正規化（敬称削除）
    clean_identifier = normalize_identifier(identifier)

    # clientId で検索
    if clean_identifier.startswith("c-"):
        result = run_query("""
            MATCH (c:Client {clientId: $id})
            OPTIONAL MATCH (c)-[:HAS_IDENTITY]->(i:Identity)
            RETURN c.clientId as clientId,
                   c.displayCode as displayCode,
                   c.bloodType as bloodType,
                   c.kana as kana,
                   c.aliases as aliases,
                   COALESCE(i.name, c.name) as name,
                   COALESCE(i.dob, c.dob) as dob
        """, {"id": clean_identifier})
        if result:
            return result[0]

    # displayCode で検索
    if clean_identifier.startswith("A-"):
        result = run_query("""
            MATCH (c:Client {displayCode: $code})
            OPTIONAL MATCH (c)-[:HAS_IDENTITY]->(i:Identity)
            RETURN c.clientId as clientId,
                   c.displayCode as displayCode,
                   c.bloodType as bloodType,
                   c.kana as kana,
                   c.aliases as aliases,
                   COALESCE(i.name, c.name) as name,
                   COALESCE(i.dob, c.dob) as dob
        """, {"code": clean_identifier})
        if result:
            return result[0]

    # 氏名またはふりがな、または通称で検索（完全一致）
    # 入力自体または正規化後の両方を試す
    # NOTE: OPTIONAL MATCHはWHEREの後に配置する（クエリ実行順序の問題回避）
    result = run_query("""
        MATCH (c:Client)
        WHERE c.name IN [$raw, $clean]
           OR c.kana IN [$raw, $clean]
           OR ANY(alias IN COALESCE(c.aliases, []) WHERE alias IN [$raw, $clean])
        OPTIONAL MATCH (c)-[:HAS_IDENTITY]->(i:Identity)
        RETURN c.clientId as clientId,
               c.displayCode as displayCode,
               c.bloodType as bloodType,
               c.kana as kana,
               c.aliases as aliases,
               COALESCE(i.name, c.name) as name,
               COALESCE(i.dob, c.dob) as dob
        LIMIT 1
    """, {"raw": identifier, "clean": clean_identifier})

    if result:
        return result[0]

    # 部分一致検索（フォールバック）
    # DBの名前が入力を含む場合 OR *入力がDBの名前を含む場合* (双方向)
    result = run_query("""
        MATCH (c:Client)
        WHERE (c.name CONTAINS $clean OR $clean CONTAINS c.name)
           OR (c.kana IS NOT NULL AND (c.kana CONTAINS $clean OR $clean CONTAINS c.kana))
           OR ANY(alias IN COALESCE(c.aliases, []) WHERE alias CONTAINS $clean OR $clean CONTAINS alias)
        OPTIONAL MATCH (c)-[:HAS_IDENTITY]->(i:Identity)
        RETURN c.clientId as clientId,
               c.displayCode as displayCode,
               c.bloodType as bloodType,
               c.kana as kana,
               c.aliases as aliases,
               COALESCE(i.name, c.name) as name,
               COALESCE(i.dob, c.dob) as dob
        LIMIT 1
    """, {"clean": clean_identifier})

    return result[0] if result else None


def get_clients_list_extended(include_pii: bool = True) -> list:
    """
    クライアント一覧を取得（仮名化対応版）

    Args:
        include_pii: True の場合は氏名を含む、False の場合は displayCode のみ

    Returns:
        [
            {"clientId": "c-xxx", "displayCode": "A-001", "name": "山田健太", "kana": "やまだけんた", "aliases": [...]},
            ...
        ]
    """
    if include_pii:
        return run_query("""
            MATCH (c:Client)
            OPTIONAL MATCH (c)-[:HAS_IDENTITY]->(i:Identity)
            RETURN c.clientId as clientId,
                   c.displayCode as displayCode,
                   c.kana as kana,
                   c.aliases as aliases,
                   COALESCE(i.name, c.name) as name
            ORDER BY COALESCE(c.displayCode, c.name)
        """)
    else:
        return run_query("""
            MATCH (c:Client)
            RETURN c.clientId as clientId,
                   c.displayCode as displayCode
            ORDER BY c.displayCode
        """)


def get_client_by_identifier(identifier: str) -> Optional[str]:
    """
    識別子から内部で使用するクライアント識別子を取得

    仮名化スキーマ移行中は、clientId があれば clientId を、
    なければ name を返す（後方互換性）

    Args:
        identifier: 任意の識別子（clientId, displayCode, name）

    Returns:
        内部識別子（clientId または name）
    """
    client = resolve_client(identifier)
    if client:
        # clientId があればそれを使用、なければ name（後方互換）
        return client.get('clientId') or client.get('name')
    return None


def match_client_clause(identifier: str) -> tuple[str, dict]:
    """
    クライアントをマッチするための Cypher 句を生成

    仮名化スキーマ対応:
    - clientId がある場合: MATCH (c:Client {clientId: $clientId})
    - ない場合: MATCH (c:Client {name: $name})

    Args:
        identifier: クライアント識別子

    Returns:
        (cypher_clause, params)
    """
    client = resolve_client(identifier)

    if not client:
        # 見つからない場合は名前でマッチを試みる
        return "MATCH (c:Client {name: $name})", {"name": identifier}

    if client.get('clientId'):
        return "MATCH (c:Client {clientId: $clientId})", {"clientId": client['clientId']}
    else:
        return "MATCH (c:Client {name: $name})", {"name": client.get('name', identifier)}


def is_pseudonymization_enabled() -> bool:
    """仮名化スキーマが有効かどうかを確認"""
    # Identity ノードが存在するかで判定
    result = run_query("MATCH (i:Identity) RETURN count(i) as count LIMIT 1")
    return result[0]['count'] > 0 if result else False


def get_display_name(identifier: str, fallback: str = "不明") -> str:
    """
    識別子から表示用の名前を取得

    Args:
        identifier: クライアント識別子
        fallback: 見つからない場合のデフォルト値

    Returns:
        表示用名前（氏名または displayCode）
    """
    client = resolve_client(identifier)
    if client:
        return client.get('name') or client.get('displayCode') or fallback
    return fallback


# =============================================================================
# ダッシュボード用関数
# =============================================================================

def get_dashboard_stats():
    """
    ダッシュボード用統計情報を取得

    Returns:
        dict: {
            'monthly_logs': 今月の支援記録数,
            'upcoming_renewals': 30日以内の期限数,
            'total_ng_actions': 禁忌事項の総数
        }
    """
    try:
        monthly_logs = run_query("""
            MATCH (log:SupportLog)
            WHERE log.date >= date({year: date().year, month: date().month, day: 1})
            RETURN count(log) as count
        """)[0]['count']
    except Exception as e:
        log(f"月次ログ取得エラー: {e}", "WARN")
        monthly_logs = 0

    try:
        upcoming_renewals = run_query("""
            MATCH (c:Client)-[:HAS_CERTIFICATE]->(cert:Certificate)
            WHERE cert.nextRenewalDate IS NOT NULL
              AND cert.nextRenewalDate <= date() + duration({days: 30})
              AND cert.nextRenewalDate >= date()
            RETURN count(cert) as count
        """)[0]['count']
    except Exception as e:
        log(f"期限チェック取得エラー: {e}", "WARN")
        upcoming_renewals = 0

    try:
        total_ng = run_query("""
            MATCH (:Client)-[:MUST_AVOID]->(ng:NgAction)
            RETURN count(ng) as count
        """)[0]['count']
    except Exception as e:
        log(f"禁忌事項取得エラー: {e}", "WARN")
        total_ng = 0

    return {
        'monthly_logs': monthly_logs,
        'upcoming_renewals': upcoming_renewals,
        'total_ng_actions': total_ng
    }


def get_upcoming_renewals(days_ahead: int = 90, limit: int = 10) -> list:
    """
    期限が近い証明書の一覧を取得

    Args:
        days_ahead: 何日先までチェックするか
        limit: 取得件数

    Returns:
        証明書のリスト（期限が近い順）
    """
    try:
        return run_query("""
            MATCH (c:Client)-[:HAS_CERTIFICATE]->(cert:Certificate)
            WHERE cert.nextRenewalDate IS NOT NULL
              AND cert.nextRenewalDate <= date() + duration({days: $days})
              AND cert.nextRenewalDate >= date()
            RETURN c.name as client_name,
                   cert.type as cert_type,
                   cert.grade as grade,
                   cert.nextRenewalDate as renewal_date,
                   duration.inDays(date(), cert.nextRenewalDate).days as days_left
            ORDER BY cert.nextRenewalDate ASC
            LIMIT $limit
        """, {"days": days_ahead, "limit": limit})
    except Exception as e:
        log(f"期限一覧取得エラー: {e}", "WARN")
        return []


def get_client_detail(client_name: str) -> dict:
    """
    クライアント詳細情報を一括取得（展開カード用）

    Args:
        client_name: クライアント名

    Returns:
        dict: 基本情報、禁忌、効果的ケア、緊急連絡先、最近の記録
    """
    # 基本情報
    try:
        basic = run_query("""
            MATCH (c:Client {name: $name})
            OPTIONAL MATCH (c)-[:HAS_CONDITION]->(con:Condition)
            OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(cert:Certificate)
            RETURN c.name as name, c.dob as dob, c.bloodType as bloodType,
                   collect(DISTINCT con.name) as conditions,
                   collect(DISTINCT {
                       type: cert.type, grade: cert.grade,
                       renewal: cert.nextRenewalDate
                   }) as certificates
        """, {"name": client_name})
    except Exception as e:
        log(f"基本情報取得エラー ({client_name}): {e}", "WARN")
        basic = []

    # 禁忌事項
    try:
        ng_actions = run_query("""
            MATCH (c:Client {name: $name})-[:MUST_AVOID]->(ng:NgAction)
            RETURN ng.action as action, ng.reason as reason, ng.riskLevel as risk
        """, {"name": client_name})
    except Exception as e:
        log(f"禁忌事項取得エラー ({client_name}): {e}", "WARN")
        ng_actions = []

    # 効果的ケア
    try:
        care_prefs = run_query("""
            MATCH (c:Client {name: $name})-[:REQUIRES]->(cp:CarePreference)
            RETURN cp.category as category, cp.instruction as instruction
            ORDER BY cp.priority DESC
            LIMIT 5
        """, {"name": client_name})
    except Exception as e:
        log(f"ケア情報取得エラー ({client_name}): {e}", "WARN")
        care_prefs = []

    # 緊急連絡先
    try:
        key_persons = run_query("""
            MATCH (c:Client {name: $name})-[r:HAS_KEY_PERSON]->(kp:KeyPerson)
            RETURN kp.name as name, kp.phone as phone,
                   kp.relationship as relationship, r.rank as rank
            ORDER BY r.rank ASC
            LIMIT 3
        """, {"name": client_name})
    except Exception as e:
        log(f"緊急連絡先取得エラー ({client_name}): {e}", "WARN")
        key_persons = []

    # 最近の支援記録
    try:
        recent_logs = run_query("""
            MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c:Client {name: $name})
            RETURN log.date as date, log.situation as situation,
                   log.effectiveness as effectiveness, s.name as supporter
            ORDER BY log.date DESC
            LIMIT 5
        """, {"name": client_name})
    except Exception as e:
        log(f"支援記録取得エラー ({client_name}): {e}", "WARN")
        recent_logs = []

    return {
        'basic': basic[0] if basic else {},
        'ng_actions': ng_actions,
        'care_prefs': care_prefs,
        'key_persons': key_persons,
        'recent_logs': recent_logs
    }
