"""
nest-support データベース操作モジュール
汎用グラフ登録エンジン (LLM構造化データ対応) + 監査ログ + 仮名化対応

このモジュールは、Gemini等で構造化された情報をNeo4jに登録する際の「守護神」として機能し、
スキーマの整合性とデータの質を担保します。
"""

import os
import sys
from datetime import date
from typing import Optional
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

# 仮名化スキーマ設定
PSEUDONYMIZATION_ENABLED = os.getenv("PSEUDONYMIZATION_ENABLED", "false").lower() == "true"
_pseudonymizer = None

def _get_pseudonymizer():
    global _pseudonymizer
    if _pseudonymizer is None:
        try:
            from lib.pseudonymizer import get_pseudonymizer
            _pseudonymizer = get_pseudonymizer()
        except ImportError:
            from lib.pseudonymizer import Pseudonymizer
            _pseudonymizer = Pseudonymizer(enabled=False)
    return _pseudonymizer

def _mask_output(records: list[dict], field_rules: dict = None) -> list[dict]:
    if not PSEUDONYMIZATION_ENABLED:
        return records
    p = _get_pseudonymizer()
    return p.mask_records(records, field_rules)

def log(message: str, level: str = "INFO"):
    sys.stderr.write(f"[DB_Ops:{level}] {message}\n")
    sys.stderr.flush()

# --- Neo4j 接続 ---
_driver = None

def get_driver():
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        pwd = os.getenv("NEO4J_PASSWORD", "")
        if not uri or not user:
            log("Neo4j環境変数が未設定です", "ERROR")
            return None
        try:
            _driver = GraphDatabase.driver(uri, auth=(user, pwd))
            _driver.verify_connectivity()
        except Exception as e:
            log(f"Neo4j接続失敗: {e}", "ERROR")
            _driver = None
    return _driver

def run_query(query, params=None):
    try:
        driver = get_driver()
        if driver is None: return []
        with driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]
    except Exception as e:
        log(f"クエリ実行エラー: {e}", "ERROR")
        return []

# =============================================================================
# 登録エンジン構成
# =============================================================================

# MERGE用の一致キー定義
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

# Embedding生成用のテキスト構築ルール（感情・タグ・文脈を包含）
_EMBEDDING_TEXT_BUILDERS = {
    "SupportLog": lambda p: "。".join(filter(None, [
        f"感情: {p.get('emotion')}" if p.get("emotion") else None,
        f"きっかけ: {p.get('triggerTag')}" if p.get("triggerTag") else None,
        f"状況: {p.get('situation')}" if p.get("situation") else None,
        f"対応: {p.get('action')}" if p.get("action") else None,
        f"文脈: {p.get('context')}" if p.get("context") else None,
        f"メモ: {p.get('note')}" if p.get("note") else None,
        f"効果: {p.get('effectiveness')}" if p.get("effectiveness") else None,
    ])),
    "NgAction": lambda p: "。".join(filter(None, [
        f"禁忌: {p.get('action')}" if p.get('action') else None,
        f"理由: {p.get('reason')}" if p.get('reason') else None,
        f"リスク: {p.get('riskLevel')}" if p.get('riskLevel') else None,
    ])),
    "CarePreference": lambda p: "。".join(filter(None, [
        f"カテゴリ: {p.get('category')}" if p.get('category') else None,
        f"指示: {p.get('instruction')}" if p.get('instruction') else None,
    ])),
}

# =============================================================================
# 汎用グラフ登録メイン関数
# =============================================================================

def register_to_database(extracted_graph: dict, user_name: str = "system") -> dict:
    """
    LLMが抽出したグラフ構造を検証・登録し、監査ログとEmbeddingを付与する。
    Guardian Layer: スキーマバリデーション（camelCase変換・ラベル検証・廃止リレーション修正）を自動適用。
    """
    if 'nodes' not in extracted_graph:
        log("無効なグラフ形式です。'nodes' キーが必要です。", "ERROR")
        return {"status": "error", "message": "Invalid graph format"}

    # Guardian Layer: スキーマバリデーション＆正規化
    from lib.schema_validator import validate_and_normalize_graph
    extracted_graph, validation_warnings = validate_and_normalize_graph(extracted_graph)
    if validation_warnings:
        log(f"スキーマ検証警告 ({len(validation_warnings)}件): {'; '.join(validation_warnings[:3])}", "WARN")

    temp_id_map = {}
    registered_labels = []
    client_name_context = "Unknown"

    # クライアント名の特定（コンテキスト把握）
    for node in extracted_graph.get("nodes", []):
        if node.get("label") == "Client":
            client_name_context = node.get("properties", {}).get("name", "Unknown")
            break

    # 1. ノードの処理
    for node in extracted_graph.get("nodes", []):
        temp_id = node.get("temp_id")
        label = node.get("label")
        props = node.get("properties", {})

        if not temp_id or not label: continue

        internal_id = None
        action_type = "CREATE"

        if label in MERGE_KEYS:
            match_props = {k: props[k] for k in MERGE_KEYS[label] if k in props}
            if match_props:
                match_clause = ", ".join([f"{k}: ${k}" for k in match_props.keys()])
                cypher = f"MERGE (n:{label} {{{match_clause}}}) SET n += $props RETURN elementId(n) AS id"
                params = {**match_props, "props": props}
                result = run_query(cypher, params)
                if result: internal_id = result[0]['id']
                action_type = "MERGE/UPDATE"
        
        if not internal_id:
            cypher = f"CREATE (n:{label}) SET n = $props RETURN elementId(n) AS id"
            result = run_query(cypher, {"props": props})
            if result: internal_id = result[0]['id']

        if internal_id:
            temp_id_map[temp_id] = internal_id
            registered_labels.append(label)
            _audit_node_creation(user_name, label, props, action_type, client_name_context)

    # 2. リレーションシップの処理
    for rel in extracted_graph.get("relationships", []):
        source_id = temp_id_map.get(rel.get("source_temp_id"))
        target_id = temp_id_map.get(rel.get("target_temp_id"))
        if source_id and target_id and rel.get("type"):
            run_query(f"""
                MATCH (s) WHERE elementId(s) = $sid
                MATCH (t) WHERE elementId(t) = $tid
                MERGE (s)-[r:{rel['type']}]->(t)
                SET r += $props
            """, {"sid": source_id, "tid": target_id, "props": rel.get("properties", {})})

    # 3. 事後処理 (チェーン構築・Embedding)
    if "SupportLog" in registered_labels:
        _rebuild_support_log_chain(client_name_context)
    
    _attach_embeddings_batch(temp_id_map, extracted_graph.get("nodes", []))
    _try_attach_client_summary(client_name_context, registered_labels)

    return {
        "status": "success",
        "client_name": client_name_context,
        "count": len(registered_labels),
        "types": list(set(registered_labels))
    }

# =============================================================================
# 内部ユーティリティ
# =============================================================================

def _audit_node_creation(user, label, props, action, client):
    """特定のラベルに対して重要な監査ログを生成"""
    if label == "NgAction":
        create_audit_log(user, action, label, props.get('action', ''), 
                         f"Risk: {props.get('riskLevel')}", client)
    elif label == "SupportLog":
        create_audit_log(user, action, label, 
                         f"{props.get('emotion', '不明')}-{props.get('triggerTag', '不明')}", 
                         f"Context: {props.get('context', '')}", client)
    elif label == "Client":
        create_audit_log(user, action, label, props.get('name', ''), "Basic Info", client)

def create_audit_log(user, action, target_type, target_name, details="", client_name=None):
    run_query("""
        CREATE (al:AuditLog {
            timestamp: datetime(), user: $user, action: $action,
            targetType: $type, targetName: $name, details: $details, clientName: $client
        })
        WITH al OPTIONAL MATCH (c:Client {name: $client})
        WHERE $client IS NOT NULL AND $client <> ''
        FOREACH (_ IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END | CREATE (al)-[:AUDIT_FOR]->(c))
    """, {"user": user, "action": action, "type": target_type, "name": target_name, 
          "details": details, "client": client_name or ""})

def _rebuild_support_log_chain(client_name):
    run_query("""
        MATCH (log:SupportLog)-[:ABOUT]->(c:Client {name: $name})
        WITH log ORDER BY log.date DESC
        MATCH (current:SupportLog)-[:ABOUT]->(c:Client {name: $name})
        WHERE NOT (current)-[:FOLLOWS]->()
        OPTIONAL MATCH (prev:SupportLog)-[:ABOUT]->(c)
        WHERE prev <> current AND prev.date <= current.date
        WITH current, prev ORDER BY prev.date DESC
        WITH current, collect(prev)[0] AS imm_prev
        WHERE imm_prev IS NOT NULL
        MERGE (current)-[:FOLLOWS]->(imm_prev)
    """, {"name": client_name})

def _attach_embeddings_batch(temp_id_map, nodes):
    targets = []
    for node in nodes:
        label = node.get("label")
        if label in _EMBEDDING_TEXT_BUILDERS:
            eid = temp_id_map.get(node.get("temp_id"))
            text = _EMBEDDING_TEXT_BUILDERS[label](node.get("properties", {}))
            if eid and text: targets.append({"id": eid, "text": text})
    
    if not targets: return
    try:
        from lib.embedding import embed_texts_batch
        embeddings = embed_texts_batch([t["text"] for t in targets])
        for t, emb in zip(targets, embeddings):
            if emb: run_query("MATCH (n) WHERE elementId(n) = $id CALL db.create.setNodeVectorProperty(n, 'embedding', $emb)",
                             {"id": t["id"], "emb": emb})
    except Exception as e: log(f"Embedding付与失敗: {e}", "WARN")

def _try_attach_client_summary(name, labels):
    if name == "Unknown" or not any(l in {"Client", "NgAction", "CarePreference"} for l in labels): return
    try:
        from lib.embedding import embed_client_summary
        embed_client_summary(name)
    except: pass

# =============================================================================
# 取得系（互換性維持）
# =============================================================================

def resolve_client(identifier: str) -> Optional[dict]:
    # 旧db_operationsの高度な解決ロジック（clientId/displayCode対応）を維持
    clean = identifier.replace("さん", "").replace("くん", "").strip()
    res = run_query("""
        MATCH (c:Client)
        WHERE c.name = $id OR c.clientId = $id OR c.displayCode = $id OR c.kana = $id
           OR ANY(a IN COALESCE(c.aliases, []) WHERE a = $id)
        RETURN c.name as name, c.clientId as clientId, c.displayCode as displayCode
        LIMIT 1
    """, {"id": clean})
    return res[0] if res else None

def get_clients_list():
    res = run_query("MATCH (c:Client) RETURN c.name as name ORDER BY c.name")
    return [r['name'] for r in res]
