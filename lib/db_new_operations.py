"""
親なき後支援データベース - データベース操作モジュール
Neo4j接続、クエリ実行、データ登録処理、監査ログ

仮名化対応:
- クライアントは clientId (UUID) で内部識別
- 氏名は Identity ノードに分離
- 表示時のみ結合（resolve_client で解決）

【更新】
Gemini 2.0 Flash などの LLM からの抽出グラフデータ (nodes, relationships) を
動的にマージするハイブリッド型の register_to_database を実装。
"""

import os
import sys
from datetime import date
from typing import Optional
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

# 仮名化スキーマが有効かどうか（マイグレーション後に True に設定）
PSEUDONYMIZATION_ENABLED = os.getenv("PSEUDONYMIZATION_ENABLED", "false").lower() == "true"

# 仮名化モジュール（遅延インポート）
_pseudonymizer = None

def _get_pseudonymizer():
    """仮名化モジュールを遅延ロードして取得"""
    global _pseudonymizer
    if _pseudonymizer is None:
        try:
            from lib.pseudonymizer import get_pseudonymizer
            _pseudonymizer = get_pseudonymizer()
        except ImportError:
            # pseudonymizer モジュールが見つからない場合はダミーを使用
            from lib.pseudonymizer import Pseudonymizer
            _pseudonymizer = Pseudonymizer(enabled=False)
    return _pseudonymizer


def _mask_output(records: list[dict], field_rules: dict = None) -> list[dict]:
    """
    クエリ結果に仮名化マスクを適用する出力フィルター

    PSEUDONYMIZATION_ENABLED=true の場合のみ動作。
    Neo4j 内のデータは変更せず、表示時にのみマスク。
    """
    if not PSEUDONYMIZATION_ENABLED:
        return records
    p = _get_pseudonymizer()
    return p.mask_records(records, field_rules)

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
        pwd = os.getenv("NEO4J_PASSWORD", "")
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
    client_name: Optional[str] = None
) -> dict:
    """監査ログを作成"""
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
        WITH al
        OPTIONAL MATCH (c:Client {name: $client_name})
        WHERE $client_name <> ''
        FOREACH (_ IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
            CREATE (al)-[:AUDIT_FOR]->(c)
        )
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
    client_name: Optional[str] = None,
    user_name: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 50
) -> list:
    """監査ログを取得"""
    results = run_query("""
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
    return _mask_output(results)


def get_client_change_history(client_name: str, limit: int = 20) -> list:
    """特定クライアントに関する変更履歴を取得"""
    results = run_query("""
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
    return _mask_output(results)


# =============================================================================
# データ登録処理（ハイブリッド・グラフ汎用抽出対応版）
# =============================================================================

# 重複を防ぐための識別キー（MERGE用）の定義
MERGE_KEYS = {
    "Client": ["name"],
    "Supporter": ["name"],
    "NgAction": ["action"],
    "CarePreference": ["category", "instruction"],
    "Condition": ["name"],
    "KeyPerson": ["name"],
    "Organization": ["name"],
    "ServiceProvider": ["name"],
    "Hospital": ["name"],
    "Guardian": ["name"],
    "Certificate": ["type"]
}

def register_to_database(extracted_graph: dict, user_name: str = "system") -> dict:
    """
    LLMが抽出したフラットなグラフ構造(nodes, relationships)を読み込み、
    適切な登録処理にルーティングする。

    Args:
        extracted_graph: AI構造化されたグラフデータ (nodes, relationships を含むdict)
        user_name: 登録を行うユーザー名（デフォルト: "system"）

    Returns:
        登録結果のサマリー
    """
    # 従来形式のツリー型JSONが渡された場合のフォールバック（下位互換性確保）
    if 'client' in extracted_graph and 'nodes' not in extracted_graph:
        log("旧形式(ツリー型)のデータが渡されました。エラーを防ぐため登録をスキップします。", "WARN")
        return {"status": "error", "message": "旧形式のJSON構造はサポートされていません。"}

    # Guardian Layer: スキーマバリデーション＆正規化
    from lib.schema_validator import validate_and_normalize_graph
    extracted_graph, validation_warnings = validate_and_normalize_graph(extracted_graph)
    if validation_warnings:
        log(f"スキーマ検証警告 ({len(validation_warnings)}件): {'; '.join(validation_warnings[:3])}", "WARN")

    temp_id_map = {}
    registered_items = []
    client_name_context = "Unknown"

    # コンテキスト（主となるクライアント名）を取得（監査ログ用）
    for node in extracted_graph.get("nodes", []):
        if node.get("label") == "Client":
            client_name_context = node.get("properties", {}).get("name", "Unknown")
            break

    # ---------------------------------------------------------
    # 1. ノードの処理 (Nodes)
    # ---------------------------------------------------------
    for node in extracted_graph.get("nodes", []):
        temp_id = node.get("temp_id")
        label = node.get("label")
        props = node.get("properties", {})

        if not temp_id or not label:
            continue

        internal_id = None
        action_type = "CREATE"

        # MERGE (重複更新) か CREATE (新規作成) かの判定
        if label in MERGE_KEYS:
            match_props = {k: props[k] for k in MERGE_KEYS[label] if k in props}
            if match_props:
                # 動的にMERGEクエリを構築
                match_clause = ", ".join([f"{k}: ${k}" for k in match_props.keys()])
                cypher = f"""
                MERGE (n:{label} {{{match_clause}}})
                SET n += $props
                RETURN elementId(n) AS internal_id
                """
                params = match_props.copy()
                params["props"] = props
                result = run_query(cypher, params)

                if result:
                    internal_id = result[0]['internal_id']
                action_type = "MERGE/UPDATE"
            else:
                log(f"MERGEキーが不足しているためスキップ: {label} - {props}", "WARN")
        else:
            # SupportLog, LifeHistory などは常に新規作成
            cypher = f"""
            CREATE (n:{label})
            SET n = $props
            RETURN elementId(n) AS internal_id
            """
            result = run_query(cypher, {"props": props})
            if result:
                internal_id = result[0]['internal_id']

        if internal_id:
            temp_id_map[temp_id] = internal_id
            registered_items.append(label)

            # --- ビジネスロジックのフック（重要な監査ログの記録） ---
            if label == "NgAction":
                create_audit_log(
                    user_name=user_name, action="CREATE", target_type="NgAction",
                    target_name=props.get('action', ''),
                    details=f"リスクレベル: {props.get('riskLevel', 'Panic')}, 理由: {props.get('reason', '')}",
                    client_name=client_name_context
                )
            elif label == "SupportLog":
                create_audit_log(
                    user_name=user_name, action="CREATE", target_type="SupportLog",
                    target_name=f"{props.get('situation', '')} - {props.get('action', '')}",
                    details=f"効果: {props.get('effectiveness', '')}",
                    client_name=client_name_context
                )
            elif label == "Client":
                create_audit_log(
                    user_name=user_name, action=action_type, target_type="Client",
                    target_name=props.get('name', ''), details="基本情報登録/更新",
                    client_name=client_name_context
                )

    # ---------------------------------------------------------
    # 2. リレーションシップの処理 (Relationships)
    # ---------------------------------------------------------
    for rel in extracted_graph.get("relationships", []):
        source_temp = rel.get("source_temp_id")
        target_temp = rel.get("target_temp_id")
        rel_type = rel.get("type")
        rel_props = rel.get("properties", {})

        source_id = temp_id_map.get(source_temp)
        target_id = temp_id_map.get(target_temp)

        if source_id and target_id and rel_type:
            # elementId() を使って特定のノード同士を安全に結ぶ
            cypher = f"""
            MATCH (source) WHERE elementId(source) = $source_id
            MATCH (target) WHERE elementId(target) = $target_id
            MERGE (source)-[r:{rel_type}]->(target)
            SET r += $rel_props
            """
            run_query(cypher, {
                "source_id": source_id,
                "target_id": target_id,
                "rel_props": rel_props
            })

    # ---------------------------------------------------------
    # 3. 事後処理フック（時系列チェーンの自動構築）
    # ---------------------------------------------------------
    if "SupportLog" in registered_items and client_name_context != "Unknown":
        _rebuild_support_log_chain(client_name_context)

    # ---------------------------------------------------------
    # 4. Embedding自動付与（ベストエフォート）
    # ---------------------------------------------------------
    _attach_embeddings(
        temp_id_map=temp_id_map,
        nodes=extracted_graph.get("nodes", []),
        registered_items=registered_items,
    )

    # ---------------------------------------------------------
    # 5. Client summaryEmbedding 自動付与（ベストエフォート）
    # ---------------------------------------------------------
    _try_attach_client_summary_embedding(registered_items, client_name_context)

    log(f"汎用グラフ登録完了: {client_name_context} - 項目数: {len(registered_items)}")

    return {
        "status": "success",
        "client_name": client_name_context,
        "registered_count": len(registered_items),
        "registered_types": list(set(registered_items))
    }

# =============================================================================
# Embedding自動付与（ベストエフォート）
# =============================================================================

# embeddingを生成する対象ノードラベルと、テキスト表現の構築ルール
_EMBEDDING_TEXT_BUILDERS = {
    "SupportLog": lambda p: "。".join(filter(None, [
        f"状況: {p['situation']}" if p.get("situation") else None,
        f"対応: {p['action']}" if p.get("action") else None,
        f"メモ: {p['note']}" if p.get("note") else None,
        f"効果: {p['effectiveness']}" if p.get("effectiveness") else None,
    ])),
    "NgAction": lambda p: "。".join(filter(None, [
        f"禁忌: {p['action']}" if p.get("action") else None,
        f"理由: {p['reason']}" if p.get("reason") else None,
        f"リスク: {p['riskLevel']}" if p.get("riskLevel") else None,
    ])),
    "CarePreference": lambda p: "。".join(filter(None, [
        f"カテゴリ: {p['category']}" if p.get("category") else None,
        f"指示: {p['instruction']}" if p.get("instruction") else None,
    ])),
}


def _attach_embeddings(
    temp_id_map: dict,
    nodes: list[dict],
    registered_items: list[str],
) -> None:
    """
    register_to_database() で登録されたノードにembeddingを一括付与する。
    GEMINI_API_KEY 未設定やAPI障害時は静かにスキップ。
    """
    # embedding対象のノードを抽出
    targets = []
    for node in nodes:
        label = node.get("label")
        temp_id = node.get("temp_id")
        props = node.get("properties", {})
        if label not in _EMBEDDING_TEXT_BUILDERS:
            continue
        element_id = temp_id_map.get(temp_id)
        if not element_id:
            continue
        text = _EMBEDDING_TEXT_BUILDERS[label](props)
        if text:
            targets.append({"element_id": element_id, "text": text})

    if not targets:
        return

    try:
        from lib.embedding import embed_texts_batch
    except ImportError:
        log("lib.embedding が利用できないためembedding付与をスキップ", "WARN")
        return

    try:
        texts = [t["text"] for t in targets]
        embeddings = embed_texts_batch(texts)

        success = 0
        for target, emb in zip(targets, embeddings):
            if emb is None:
                continue
            try:
                run_query(
                    """
                    MATCH (n) WHERE elementId(n) = $id
                    CALL db.create.setNodeVectorProperty(n, 'embedding', $embedding)
                    """,
                    {"id": target["element_id"], "embedding": emb},
                )
                success += 1
            except Exception as e:
                log(f"embedding付与失敗 (node {target['element_id']}): {e}", "WARN")

        if success > 0:
            log(f"Embedding自動付与: {success}/{len(targets)} ノード")
    except Exception as e:
        log(f"Embedding一括生成スキップ: {e}", "WARN")


def _try_attach_client_summary_embedding(
    registered_items: list[str], client_name: str | None
) -> None:
    """Client の summaryEmbedding を自動付与（ベストエフォート）"""
    if not client_name:
        return

    # Client 関連の登録があった場合のみ実行
    client_related = {"Client", "Condition", "NgAction", "CarePreference"}
    if not any(item in client_related for item in registered_items):
        return

    try:
        from lib.embedding import embed_client_summary

        embed_client_summary(client_name)
    except Exception as e:
        log(f"Client summaryEmbedding 自動付与スキップ: {e}", "WARN")


def _attach_support_log_embedding(log_data: dict, element_id: str | None = None) -> None:
    """
    register_support_log() で登録されたSupportLogにembeddingを付与する。
    elementId で直接特定するため、同一日・同一状況の重複ログがあっても安全。
    """
    text = _EMBEDDING_TEXT_BUILDERS["SupportLog"](log_data)
    if not text or not element_id:
        return

    try:
        from lib.embedding import embed_text
    except ImportError:
        return

    try:
        embedding = embed_text(text)
        if embedding is None:
            return
        run_query(
            """
            MATCH (n) WHERE elementId(n) = $id
            CALL db.create.setNodeVectorProperty(n, 'embedding', $embedding)
            """,
            {"id": element_id, "embedding": embedding},
        )
        log("SupportLog embedding自動付与完了")
    except Exception as e:
        log(f"SupportLog embedding付与スキップ: {e}", "WARN")


def _rebuild_support_log_chain(client_name: str):
    """
    特定クライアントのSupportLog間にFOLLOWSリレーションを自動構築する。
    （AIがリレーションの抽出を漏らした場合でも、時系列チェーンを担保するフェイルセーフ）
    """
    run_query("""
        MATCH (log:SupportLog)-[:ABOUT]->(c:Client {name: $client_name})
        WITH log, c ORDER BY log.date DESC
        // 最新のものを除く過去のログと、その直前のログを結びつける
        MATCH (current:SupportLog)-[:ABOUT]->(c)
        OPTIONAL MATCH (prev:SupportLog)-[:ABOUT]->(c)
        WHERE prev <> current AND prev.date <= current.date
          AND NOT (current)-[:FOLLOWS]->()
        WITH current, prev ORDER BY prev.date DESC
        // collectの先頭（直近の過去）だけを取得してFOLLOWSで繋ぐ
        WITH current, collect(prev)[0] AS immediate_prev
        WHERE immediate_prev IS NOT NULL
        MERGE (current)-[:FOLLOWS]->(immediate_prev)
    """, {"client_name": client_name})


def register_support_log(log_data: dict, client_name: str) -> dict:
    """
    【後方互換性用】
    手動フォーム入力などで、AI抽出を経由せずに支援記録を直接登録するための関数。
    """
    run_query("MERGE (s:Supporter {name: $supporter})", {"supporter": log_data['supporter']})

    result = run_query("""
        MATCH (c:Client {name: $client_name})
        MATCH (s:Supporter {name: $supporter})

        CREATE (log:SupportLog {
            date: date($date),
            situation: $situation,
            action: $action,
            effectiveness: $effectiveness,
            note: $note,
            type: $type,
            duration: $duration,
            nextAction: $nextAction
        })

        CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c)

        WITH log, c
        OPTIONAL MATCH (prevLog:SupportLog)-[:ABOUT]->(c)
        WHERE prevLog <> log AND prevLog.date <= log.date
        WITH log, prevLog ORDER BY prevLog.date DESC LIMIT 1
        FOREACH (_ IN CASE WHEN prevLog IS NOT NULL THEN [1] ELSE [] END |
            CREATE (log)-[:FOLLOWS]->(prevLog)
        )

        RETURN log.date as date, log.situation as situation, elementId(log) as elementId
    """, {
        "client_name": client_name,
        "supporter": log_data['supporter'],
        "date": log_data['date'],
        "situation": log_data['situation'],
        "action": log_data['action'],
        "effectiveness": log_data.get('effectiveness', ''),
        "note": log_data.get('note', ''),
        "type": log_data.get('type', '日常記録'),
        "duration": log_data.get('duration'),
        "nextAction": log_data.get('nextAction')
    })

    if result:
        # Embedding自動付与（ベストエフォート）
        _attach_support_log_embedding(log_data, element_id=result[0].get("elementId"))
        return {"status": "success", "message": f"支援記録を登録: {log_data['situation']}", "data": result[0]}
    else:
        return {"status": "error", "message": f"クライアント '{client_name}' が見つかりません"}


# =============================================================================
# 取得・検索機能 (Read Operations)
# =============================================================================

def get_clients_list():
    """登録済みクライアント一覧を取得"""
    results = run_query("MATCH (c:Client) RETURN c.name as name ORDER BY c.name")
    if PSEUDONYMIZATION_ENABLED:
        p = _get_pseudonymizer()
        return [p.mask_name(r['name']) for r in results]
    return [r['name'] for r in results]


def get_client_stats():
    """クライアント統計情報を取得"""
    client_count = run_query("MATCH (n:Client) RETURN count(n) as c")[0]['c']
    ng_by_client = run_query("""
        MATCH (c:Client)
        OPTIONAL MATCH (c)-[:MUST_AVOID]->(ng:NgAction)
        RETURN c.name as name, count(ng) as ng_count
        ORDER BY c.name
    """)
    return {'client_count': client_count, 'ng_by_client': _mask_output(ng_by_client)}


def get_support_logs(client_name: str, limit: int = 20):
    """特定クライアントの支援記録を取得"""
    results = run_query("""
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
    return _mask_output(results)


def discover_care_patterns(client_name: str, min_frequency: int = 3):
    """効果的なケアパターンを発見"""
    results = run_query("""
        MATCH (c:Client {name: $client_name})<-[:ABOUT]-(log:SupportLog)
        WHERE log.effectiveness = 'Effective'
        WITH c, log.situation as situation, log.action as action, count(*) as frequency
        WHERE frequency >= $min_frequency
        RETURN situation as 状況,
               action as 対応方法,
               frequency as 効果的だった回数
        ORDER BY frequency DESC
    """, {"client_name": client_name, "min_frequency": min_frequency})
    return _mask_output(results)


def search_support_logs(keyword: str, client_name: str = None, limit: int = 20) -> list:
    """全文検索で支援記録を検索"""
    results = run_query("""
        CALL db.index.fulltext.queryNodes('idx_supportlog_fulltext', $keyword)
        YIELD node, score
        MATCH (s:Supporter)-[:LOGGED]->(node)-[:ABOUT]->(c:Client)
        WHERE $client_name = '' OR c.name CONTAINS $client_name
        RETURN node.date as 日付,
               s.name as 支援者,
               c.name as クライアント,
               node.situation as 状況,
               node.action as 対応,
               node.effectiveness as 効果,
               score as スコア
        ORDER BY score DESC
        LIMIT $limit
    """, {"keyword": keyword, "client_name": client_name or "", "limit": limit})
    return _mask_output(results)


def validate_client_uniqueness(name: str, dob: str) -> bool:
    """クライアントの複合一意性をチェック（name + dob）"""
    result = run_query("""
        MATCH (c:Client {name: $name})
        WHERE c.dob = date($dob)
        RETURN count(c) AS count
    """, {"name": name, "dob": dob})
    return result[0]["count"] == 0 if result else True


# =============================================================================
# 仮名化対応機能
# =============================================================================

def normalize_identifier(text: str) -> str:
    """識別子を正規化する（敬称の削除など）"""
    if not text:
        return ""
    suffixes = [
        "さん", "くん", "ちゃん", "様", "氏", "殿",
        "San", "-san", "Chan", "-chan", "Kun", "-kun", "Sama", "-sama"
    ]
    normalized = text.strip()
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
            break
    return normalized


def resolve_client(identifier: str) -> Optional[dict]:
    """様々な識別子からクライアント情報を解決"""
    clean_identifier = normalize_identifier(identifier)

    # clientId で検索
    if clean_identifier.startswith("c-"):
        result = run_query("""
            MATCH (c:Client {clientId: $id})
            OPTIONAL MATCH (c)-[:HAS_IDENTITY]->(i:Identity)
            RETURN c.clientId as clientId, c.displayCode as displayCode,
                   c.bloodType as bloodType, c.kana as kana, c.aliases as aliases,
                   COALESCE(i.name, c.name) as name, COALESCE(i.dob, c.dob) as dob
        """, {"id": clean_identifier})
        if result: return result[0]

    # displayCode で検索
    if clean_identifier.startswith("A-"):
        result = run_query("""
            MATCH (c:Client {displayCode: $code})
            OPTIONAL MATCH (c)-[:HAS_IDENTITY]->(i:Identity)
            RETURN c.clientId as clientId, c.displayCode as displayCode,
                   c.bloodType as bloodType, c.kana as kana, c.aliases as aliases,
                   COALESCE(i.name, c.name) as name, COALESCE(i.dob, c.dob) as dob
        """, {"code": clean_identifier})
        if result: return result[0]

    # 氏名またはふりがな、または通称で検索（完全一致）
    result = run_query("""
        MATCH (c:Client)
        WHERE c.name IN [$raw, $clean] OR c.kana IN [$raw, $clean]
           OR ANY(alias IN COALESCE(c.aliases, []) WHERE alias IN [$raw, $clean])
        OPTIONAL MATCH (c)-[:HAS_IDENTITY]->(i:Identity)
        RETURN c.clientId as clientId, c.displayCode as displayCode,
               c.bloodType as bloodType, c.kana as kana, c.aliases as aliases,
               COALESCE(i.name, c.name) as name, COALESCE(i.dob, c.dob) as dob
        LIMIT 1
    """, {"raw": identifier, "clean": clean_identifier})
    if result: return result[0]

    # 部分一致検索（フォールバック）
    result = run_query("""
        MATCH (c:Client)
        WHERE (c.name CONTAINS $clean OR $clean CONTAINS c.name)
           OR (c.kana IS NOT NULL AND (c.kana CONTAINS $clean OR $clean CONTAINS c.kana))
           OR ANY(alias IN COALESCE(c.aliases, []) WHERE alias CONTAINS $clean OR $clean CONTAINS alias)
        OPTIONAL MATCH (c)-[:HAS_IDENTITY]->(i:Identity)
        RETURN c.clientId as clientId, c.displayCode as displayCode,
               c.bloodType as bloodType, c.kana as kana, c.aliases as aliases,
               COALESCE(i.name, c.name) as name, COALESCE(i.dob, c.dob) as dob
        LIMIT 1
    """, {"clean": clean_identifier})
    return result[0] if result else None


def get_clients_list_extended(include_pii: bool = True) -> list:
    """クライアント一覧を取得（仮名化対応版）"""
    if include_pii:
        return run_query("""
            MATCH (c:Client)
            OPTIONAL MATCH (c)-[:HAS_IDENTITY]->(i:Identity)
            RETURN c.clientId as clientId, c.displayCode as displayCode,
                   c.kana as kana, c.aliases as aliases, COALESCE(i.name, c.name) as name
            ORDER BY COALESCE(c.displayCode, c.name)
        """)
    else:
        return run_query("""
            MATCH (c:Client)
            RETURN c.clientId as clientId, c.displayCode as displayCode
            ORDER BY c.displayCode
        """)


def get_client_by_identifier(identifier: str) -> Optional[str]:
    """識別子から内部で使用するクライアント識別子を取得"""
    client = resolve_client(identifier)
    if client: return client.get('clientId') or client.get('name')
    return None


def match_client_clause(identifier: str) -> tuple[str, dict]:
    """クライアントをマッチするための Cypher 句を生成"""
    client = resolve_client(identifier)
    if not client: return "MATCH (c:Client {name: $name})", {"name": identifier}
    if client.get('clientId'):
        return "MATCH (c:Client {clientId: $clientId})", {"clientId": client['clientId']}
    else:
        return "MATCH (c:Client {name: $name})", {"name": client.get('name', identifier)}


def is_pseudonymization_enabled() -> bool:
    """仮名化スキーマが有効かどうかを確認"""
    result = run_query("MATCH (i:Identity) RETURN count(i) as count LIMIT 1")
    return result[0]['count'] > 0 if result else False


def get_display_name(identifier: str, fallback: str = "不明") -> str:
    """識別子から表示用の名前を取得"""
    client = resolve_client(identifier)
    if client: return client.get('name') or client.get('displayCode') or fallback
    return fallback


# =============================================================================
# ダッシュボード用関数
# =============================================================================

def get_dashboard_stats():
    """ダッシュボード用統計情報を取得"""
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
    """期限が近い証明書の一覧を取得"""
    try:
        results = run_query("""
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
        return _mask_output(results)
    except Exception as e:
        log(f"期限一覧取得エラー: {e}", "WARN")
        return []


def get_client_detail(client_name: str) -> dict:
    """クライアント詳細情報を一括取得（展開カード用）"""
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

    try:
        ng_actions = run_query("""
            MATCH (c:Client {name: $name})-[:MUST_AVOID]->(ng:NgAction)
            RETURN ng.action as action, ng.reason as reason, ng.riskLevel as risk
        """, {"name": client_name})
    except Exception as e:
        log(f"禁忌事項取得エラー ({client_name}): {e}", "WARN")
        ng_actions = []

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
        'basic': _mask_output(basic)[0] if basic else {},
        'ng_actions': ng_actions,
        'care_prefs': care_prefs,
        'key_persons': _mask_output(key_persons),
        'recent_logs': _mask_output(recent_logs)
    }
