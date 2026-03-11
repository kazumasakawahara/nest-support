"""
親亡き後支援データベース - マルチモーダルEmbeddingモジュール
Gemini Embedding 2 による テキスト/画像/PDF のembedding生成、
Neo4j ベクトルインデックスを利用したセマンティック検索

Dependencies:
    google-genai >= 1.55.0  (既存依存)
    neo4j >= 6.0.3          (既存依存)
"""

import os
import sys
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# 定数
# =============================================================================

# Gemini Embedding 2 モデル名（Public Preview）
EMBEDDING_MODEL = "gemini-embedding-2-preview"

# デフォルト出力次元数
# 768: ストレージ効率優先（本番推奨）
# 1536: バランス型
# 3072: 最大精度
DEFAULT_DIMENSIONS = 768

# Neo4j ベクトルインデックス定義
VECTOR_INDEXES = {
    "support_log_embedding": {
        "label": "SupportLog",
        "property": "embedding",
        "dimensions": DEFAULT_DIMENSIONS,
    },
    "care_preference_embedding": {
        "label": "CarePreference",
        "property": "embedding",
        "dimensions": DEFAULT_DIMENSIONS,
    },
    "ng_action_embedding": {
        "label": "NgAction",
        "property": "embedding",
        "dimensions": DEFAULT_DIMENSIONS,
    },
    "client_summary_embedding": {
        "label": "Client",
        "property": "summaryEmbedding",
        "dimensions": DEFAULT_DIMENSIONS,
    },
}


# =============================================================================
# ログ出力
# =============================================================================

def log(message: str, level: str = "INFO"):
    """ログ出力（標準エラー出力）"""
    sys.stderr.write(f"[Embedding:{level}] {message}\n")
    sys.stderr.flush()


# =============================================================================
# Gemini クライアント（シングルトン）
# =============================================================================

_genai_client = None


def get_genai_client():
    """google-genai クライアントを取得（シングルトン）"""
    global _genai_client
    if _genai_client is None:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            log("GEMINI_API_KEY が未設定です", "ERROR")
            return None
        _genai_client = genai.Client(api_key=api_key)
        log("Gemini クライアント初期化完了")
    return _genai_client


# =============================================================================
# Embedding 生成
# =============================================================================

def embed_text(
    text: str,
    task_type: str = "RETRIEVAL_DOCUMENT",
    dimensions: int = DEFAULT_DIMENSIONS,
) -> Optional[list[float]]:
    """
    テキストからembeddingベクトルを生成

    Args:
        text: 埋め込むテキスト（最大8192トークン）
        task_type: タスクタイプ
            - "RETRIEVAL_DOCUMENT": ドキュメント登録時
            - "RETRIEVAL_QUERY": 検索クエリ時
            - "SEMANTIC_SIMILARITY": 類似度比較
            - "CLUSTERING": クラスタリング
        dimensions: 出力次元数 (768, 1536, 3072)

    Returns:
        float のリスト（embeddingベクトル）、失敗時は None
    """
    client = get_genai_client()
    if client is None:
        return None

    from google.genai import types

    try:
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=dimensions,
            ),
        )
        values = response.embeddings[0].values
        log(f"テキストembedding生成完了: {len(values)}次元, {len(text)}文字")
        return list(values)
    except Exception as e:
        log(f"テキストembedding生成エラー: {e}", "ERROR")
        return None


def embed_image(
    image_path: str,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> Optional[list[float]]:
    """
    画像ファイルからembeddingベクトルを生成

    Args:
        image_path: 画像ファイルパス（PNG, JPEG, WebP, HEIC）
        dimensions: 出力次元数

    Returns:
        float のリスト（embeddingベクトル）、失敗時は None
    """
    client = get_genai_client()
    if client is None:
        return None

    from google.genai import types
    import mimetypes

    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/png"

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
            config=types.EmbedContentConfig(
                output_dimensionality=dimensions,
            ),
        )
        values = response.embeddings[0].values
        log(f"画像embedding生成完了: {len(values)}次元, {image_path}")
        return list(values)
    except Exception as e:
        log(f"画像embedding生成エラー: {e}", "ERROR")
        return None


def embed_multimodal(
    text: str,
    image_path: str,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> Optional[list[float]]:
    """
    テキスト＋画像のマルチモーダルembeddingを生成
    （1つのcontentエントリに複数モダリティ → 統合ベクトル）

    Args:
        text: テキスト説明
        image_path: 画像ファイルパス
        dimensions: 出力次元数

    Returns:
        float のリスト（統合embeddingベクトル）、失敗時は None
    """
    client = get_genai_client()
    if client is None:
        return None

    from google.genai import types
    import mimetypes

    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/png"

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[
                text,
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
            config=types.EmbedContentConfig(
                output_dimensionality=dimensions,
            ),
        )
        values = response.embeddings[0].values
        log(f"マルチモーダルembedding生成完了: {len(values)}次元")
        return list(values)
    except Exception as e:
        log(f"マルチモーダルembedding生成エラー: {e}", "ERROR")
        return None


def embed_texts_batch(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
    dimensions: int = DEFAULT_DIMENSIONS,
) -> list[Optional[list[float]]]:
    """
    複数テキストのembeddingを一括生成

    Args:
        texts: テキストのリスト
        task_type: タスクタイプ
        dimensions: 出力次元数

    Returns:
        embeddingベクトルのリスト（各要素は float リストまたは None）
    """
    client = get_genai_client()
    if client is None:
        return [None] * len(texts)

    from google.genai import types

    try:
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=dimensions,
            ),
        )
        results = [list(emb.values) for emb in response.embeddings]
        log(f"バッチembedding生成完了: {len(results)}件, {dimensions}次元")
        return results
    except Exception as e:
        log(f"バッチembedding生成エラー: {e}", "ERROR")
        return [None] * len(texts)


# =============================================================================
# 手書きPDF / スキャン画像 OCR（Gemini 2.0 Flash）
# =============================================================================

def ocr_with_gemini(
    file_path: str,
    instruction: str = "この文書のすべてのテキストを正確に抽出してください。手書き部分も含めて読み取ってください。",
) -> Optional[str]:
    """
    Gemini 2.0 Flash でスキャンPDF/手書き画像からテキストを抽出

    Args:
        file_path: PDF または画像ファイルのパス
        instruction: OCR 指示テキスト

    Returns:
        抽出されたテキスト、失敗時は None
    """
    client = get_genai_client()
    if client is None:
        return None

    from google.genai import types
    import mimetypes

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        if file_path.lower().endswith(".pdf"):
            mime_type = "application/pdf"
        else:
            mime_type = "image/png"

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                instruction,
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            ],
        )
        text = response.text
        log(f"OCR完了: {len(text)}文字抽出, {file_path}")
        return text
    except Exception as e:
        log(f"OCRエラー: {e}", "ERROR")
        return None


def ocr_and_embed(
    file_path: str,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> Optional[dict]:
    """
    スキャンPDF/手書き画像からテキスト抽出 → embedding生成の一括パイプライン

    Args:
        file_path: PDF または画像ファイルのパス
        dimensions: 出力次元数

    Returns:
        {"text": str, "embedding": list[float]} または None
    """
    extracted_text = ocr_with_gemini(file_path)
    if not extracted_text:
        return None

    embedding = embed_text(extracted_text, dimensions=dimensions)
    if embedding is None:
        return None

    log(f"OCR+Embedding パイプライン完了: {file_path}")
    return {"text": extracted_text, "embedding": embedding}


# =============================================================================
# Neo4j ベクトルインデックス管理
# =============================================================================

def _run_query(query: str, params: dict = None) -> list:
    """Neo4j クエリ実行（db_new_operations を遅延インポート）"""
    from lib.db_new_operations import run_query
    return run_query(query, params)


def ensure_vector_indexes() -> dict:
    """
    必要なベクトルインデックスをすべて作成する（冪等操作）

    Returns:
        {"created": [...], "skipped": [...], "errors": [...]}
    """
    result = {"created": [], "skipped": [], "errors": []}

    # 既存インデックスの確認
    existing = _run_query("SHOW VECTOR INDEXES")
    existing_names = {idx.get("name") for idx in existing}

    for index_name, config in VECTOR_INDEXES.items():
        if index_name in existing_names:
            result["skipped"].append(index_name)
            continue

        try:
            # CREATE VECTOR INDEX はパラメータ化できないため文字列構築
            # ただし全値がこのモジュールの定数から来るためインジェクションリスクなし
            _run_query(f"""
                CREATE VECTOR INDEX `{index_name}` IF NOT EXISTS
                FOR (n:{config['label']}) ON (n.{config['property']})
                OPTIONS {{
                    indexConfig: {{
                        `vector.dimensions`: {config['dimensions']},
                        `vector.similarity_function`: 'cosine'
                    }}
                }}
            """)
            result["created"].append(index_name)
            log(f"ベクトルインデックス作成: {index_name}")
        except Exception as e:
            result["errors"].append({"index": index_name, "error": str(e)})
            log(f"ベクトルインデックス作成エラー: {index_name} - {e}", "ERROR")

    return result


def show_vector_indexes() -> list:
    """現在のベクトルインデックス一覧を取得"""
    return _run_query("SHOW VECTOR INDEXES")


# =============================================================================
# ノードへのembedding付与
# =============================================================================

def set_node_embedding(
    label: str,
    match_props: dict,
    text_for_embedding: str,
    embedding_property: str = "embedding",
    dimensions: int = DEFAULT_DIMENSIONS,
) -> bool:
    """
    既存ノードにembeddingを付与

    Args:
        label: ノードラベル (例: "SupportLog")
        match_props: ノードを特定するプロパティ (例: {"date": "2026-03-09", "situation": "食事"})
        text_for_embedding: embedding化するテキスト
        embedding_property: embedding を格納するプロパティ名
        dimensions: 出力次元数

    Returns:
        成功なら True
    """
    embedding = embed_text(text_for_embedding, dimensions=dimensions)
    if embedding is None:
        return False

    # match条件を動的に構築（プロパティキーのバリデーション付き）
    import re
    safe_keys = [k for k in match_props if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', k)]
    if not safe_keys:
        log("有効なマッチプロパティがありません", "ERROR")
        return False

    match_clause = ", ".join([f"{k}: $match_{k}" for k in safe_keys])
    params = {f"match_{k}": match_props[k] for k in safe_keys}
    params["embedding"] = embedding

    result = _run_query(
        f"""
        MATCH (n:{label} {{{match_clause}}})
        CALL db.create.setNodeVectorProperty(n, '{embedding_property}', $embedding)
        RETURN elementId(n) AS id
        """,
        params,
    )
    if result:
        log(f"ノードembedding付与完了: {label} {match_props}")
        return True
    else:
        log(f"ノードが見つかりません: {label} {match_props}", "WARN")
        return False


def embed_support_log(log_data: dict) -> bool:
    """
    SupportLog ノードにembeddingを付与するヘルパー

    Args:
        log_data: {"date": "2026-03-09", "situation": "食事", "action": "静かな別室に移動"}

    Returns:
        成功なら True
    """
    # SupportLog のテキスト表現を構築
    parts = []
    if log_data.get("situation"):
        parts.append(f"状況: {log_data['situation']}")
    if log_data.get("action"):
        parts.append(f"対応: {log_data['action']}")
    if log_data.get("note"):
        parts.append(f"メモ: {log_data['note']}")
    if log_data.get("effectiveness"):
        parts.append(f"効果: {log_data['effectiveness']}")

    text = "。".join(parts)
    if not text:
        log("SupportLog テキストが空のためスキップ", "WARN")
        return False

    match_props = {}
    if log_data.get("date"):
        match_props["date"] = log_data["date"]
    if log_data.get("situation"):
        match_props["situation"] = log_data["situation"]

    return set_node_embedding("SupportLog", match_props, text)


# =============================================================================
# セマンティック検索
# =============================================================================

def semantic_search(
    query_text: str,
    index_name: str = "support_log_embedding",
    top_k: int = 10,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> list[dict]:
    """
    テキストクエリによるセマンティック検索

    Args:
        query_text: 検索クエリテキスト
        index_name: 検索対象のベクトルインデックス名
        top_k: 返す結果の最大数
        dimensions: クエリembeddingの次元数

    Returns:
        [{"node": {...}, "score": float}, ...] スコア降順
    """
    query_embedding = embed_text(
        query_text,
        task_type="RETRIEVAL_QUERY",
        dimensions=dimensions,
    )
    if query_embedding is None:
        return []

    results = _run_query(
        """
        CALL db.index.vector.queryNodes($index_name, $top_k, $query_embedding)
        YIELD node, score
        RETURN node, score
        ORDER BY score DESC
        """,
        {
            "index_name": index_name,
            "top_k": top_k,
            "query_embedding": query_embedding,
        },
    )
    log(f"セマンティック検索完了: '{query_text}' → {len(results)}件")
    return results


def search_support_logs_semantic(
    query_text: str,
    top_k: int = 10,
    client_name: Optional[str] = None,
) -> list[dict]:
    """
    支援記録のセマンティック検索（クライアント名でフィルタ可能）

    Args:
        query_text: 検索クエリ（例: "金銭管理に不安がある"）
        top_k: 返す結果の最大数
        client_name: 特定クライアントに絞る場合

    Returns:
        支援記録のリスト（スコア付き）
    """
    query_embedding = embed_text(
        query_text,
        task_type="RETRIEVAL_QUERY",
        dimensions=DEFAULT_DIMENSIONS,
    )
    if query_embedding is None:
        return []

    if client_name:
        results = _run_query(
            """
            CALL db.index.vector.queryNodes('support_log_embedding', $top_k, $query_embedding)
            YIELD node, score
            MATCH (s:Supporter)-[:LOGGED]->(node)-[:ABOUT]->(c:Client)
            WHERE c.name CONTAINS $client_name
            RETURN node.date AS 日付,
                   s.name AS 支援者,
                   c.name AS クライアント,
                   node.situation AS 状況,
                   node.action AS 対応,
                   node.effectiveness AS 効果,
                   node.note AS メモ,
                   score AS スコア
            ORDER BY score DESC
            """,
            {
                "top_k": top_k * 3,  # フィルタ前に多めに取得
                "query_embedding": query_embedding,
                "client_name": client_name,
            },
        )
    else:
        results = _run_query(
            """
            CALL db.index.vector.queryNodes('support_log_embedding', $top_k, $query_embedding)
            YIELD node, score
            MATCH (s:Supporter)-[:LOGGED]->(node)-[:ABOUT]->(c:Client)
            RETURN node.date AS 日付,
                   s.name AS 支援者,
                   c.name AS クライアント,
                   node.situation AS 状況,
                   node.action AS 対応,
                   node.effectiveness AS 効果,
                   node.note AS メモ,
                   score AS スコア
            ORDER BY score DESC
            """,
            {
                "top_k": top_k,
                "query_embedding": query_embedding,
            },
        )

    log(f"支援記録セマンティック検索: '{query_text}' → {len(results)}件")
    return results


def search_ng_actions_semantic(
    query_text: str,
    top_k: int = 5,
) -> list[dict]:
    """
    禁忌事項のセマンティック検索

    Args:
        query_text: 検索クエリ（例: "大きな音"）
        top_k: 返す結果の最大数

    Returns:
        禁忌事項のリスト（スコア付き）
    """
    query_embedding = embed_text(
        query_text,
        task_type="RETRIEVAL_QUERY",
        dimensions=DEFAULT_DIMENSIONS,
    )
    if query_embedding is None:
        return []

    results = _run_query(
        """
        CALL db.index.vector.queryNodes('ng_action_embedding', $top_k, $query_embedding)
        YIELD node, score
        MATCH (c:Client)-[:MUST_AVOID]->(node)
        RETURN c.name AS クライアント,
               node.action AS 禁忌事項,
               node.reason AS 理由,
               node.riskLevel AS リスクレベル,
               score AS スコア
        ORDER BY score DESC
        """,
        {"top_k": top_k, "query_embedding": query_embedding},
    )
    log(f"禁忌事項セマンティック検索: '{query_text}' → {len(results)}件")
    return results


# =============================================================================
# バッチembedding付与（既存ノードの一括更新）
# =============================================================================

def backfill_support_log_embeddings(
    client_name: Optional[str] = None,
    batch_size: int = 20,
) -> dict:
    """
    既存の SupportLog ノードにembeddingを一括付与（バックフィル）

    Args:
        client_name: 特定クライアントに絞る場合（None で全件）
        batch_size: 一度に処理するノード数

    Returns:
        {"processed": int, "success": int, "failed": int}
    """
    if client_name:
        nodes = _run_query(
            """
            MATCH (log:SupportLog)-[:ABOUT]->(c:Client)
            WHERE c.name CONTAINS $client_name
              AND log.embedding IS NULL
            RETURN elementId(log) AS id,
                   log.situation AS situation,
                   log.action AS action,
                   log.note AS note,
                   log.effectiveness AS effectiveness
            LIMIT $batch_size
            """,
            {"client_name": client_name, "batch_size": batch_size},
        )
    else:
        nodes = _run_query(
            """
            MATCH (log:SupportLog)
            WHERE log.embedding IS NULL
            RETURN elementId(log) AS id,
                   log.situation AS situation,
                   log.action AS action,
                   log.note AS note,
                   log.effectiveness AS effectiveness
            LIMIT $batch_size
            """,
            {"batch_size": batch_size},
        )

    if not nodes:
        log("embedding未付与のSupportLogがありません")
        return {"processed": 0, "success": 0, "failed": 0}

    # テキスト表現を構築
    texts = []
    for node in nodes:
        parts = []
        if node.get("situation"):
            parts.append(f"状況: {node['situation']}")
        if node.get("action"):
            parts.append(f"対応: {node['action']}")
        if node.get("note"):
            parts.append(f"メモ: {node['note']}")
        if node.get("effectiveness"):
            parts.append(f"効果: {node['effectiveness']}")
        texts.append("。".join(parts) if parts else "記録なし")

    # バッチembedding生成
    embeddings = embed_texts_batch(texts)

    success = 0
    failed = 0
    for node, emb in zip(nodes, embeddings):
        if emb is None:
            failed += 1
            continue
        try:
            _run_query(
                """
                MATCH (n) WHERE elementId(n) = $id
                CALL db.create.setNodeVectorProperty(n, 'embedding', $embedding)
                """,
                {"id": node["id"], "embedding": emb},
            )
            success += 1
        except Exception as e:
            log(f"embedding付与失敗: {node['id']} - {e}", "ERROR")
            failed += 1

    log(f"SupportLog バックフィル完了: {success}/{len(nodes)} 成功")
    return {"processed": len(nodes), "success": success, "failed": failed}


def backfill_ng_action_embeddings(batch_size: int = 50) -> dict:
    """
    既存の NgAction ノードにembeddingを一括付与

    Returns:
        {"processed": int, "success": int, "failed": int}
    """
    nodes = _run_query(
        """
        MATCH (ng:NgAction)
        WHERE ng.embedding IS NULL
        RETURN elementId(ng) AS id,
               ng.action AS action,
               ng.reason AS reason,
               ng.riskLevel AS riskLevel
        LIMIT $batch_size
        """,
        {"batch_size": batch_size},
    )

    if not nodes:
        log("embedding未付与のNgActionがありません")
        return {"processed": 0, "success": 0, "failed": 0}

    texts = []
    for node in nodes:
        parts = [f"禁忌: {node.get('action', '')}"]
        if node.get("reason"):
            parts.append(f"理由: {node['reason']}")
        if node.get("riskLevel"):
            parts.append(f"リスク: {node['riskLevel']}")
        texts.append("。".join(parts))

    embeddings = embed_texts_batch(texts)

    success = 0
    failed = 0
    for node, emb in zip(nodes, embeddings):
        if emb is None:
            failed += 1
            continue
        try:
            _run_query(
                """
                MATCH (n) WHERE elementId(n) = $id
                CALL db.create.setNodeVectorProperty(n, 'embedding', $embedding)
                """,
                {"id": node["id"], "embedding": emb},
            )
            success += 1
        except Exception as e:
            log(f"embedding付与失敗: {node['id']} - {e}", "ERROR")
            failed += 1

    log(f"NgAction バックフィル完了: {success}/{len(nodes)} 成功")
    return {"processed": len(nodes), "success": success, "failed": failed}


# =============================================================================
# ユーティリティ
# =============================================================================

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """2つのベクトル間のコサイン類似度を計算（NumPy不要版）"""
    if len(a) != len(b):
        raise ValueError(f"ベクトル次元が不一致: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_embedding_stats() -> dict:
    """embedding付与状況の統計情報を取得"""
    stats = {}
    for index_name, config in VECTOR_INDEXES.items():
        label = config["label"]
        prop = config["property"]
        total = _run_query(f"MATCH (n:{label}) RETURN count(n) AS c")
        embedded = _run_query(
            f"MATCH (n:{label}) WHERE n.{prop} IS NOT NULL RETURN count(n) AS c"
        )
        stats[label] = {
            "total": total[0]["c"] if total else 0,
            "embedded": embedded[0]["c"] if embedded else 0,
        }
    return stats
