"""
親亡き後支援データベース - マルチモーダルEmbeddingモジュール
Gemini Embedding 2 による テキスト/画像/PDF/音声 のembedding生成、
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
    "meeting_record_embedding": {
        "label": "MeetingRecord",
        "property": "embedding",
        "dimensions": DEFAULT_DIMENSIONS,
    },
    "meeting_record_text_embedding": {
        "label": "MeetingRecord",
        "property": "textEmbedding",
        "dimensions": DEFAULT_DIMENSIONS,
    },
}

# 音声MIME タイプのフォールバック用マッピング
_AUDIO_MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
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


def embed_audio(
    audio_path: str,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> Optional[list[float]]:
    """
    音声ファイルからembeddingベクトルを生成（文字起こし不要）

    Args:
        audio_path: 音声ファイルパス（MP3, WAV 等。最大80秒）
        dimensions: 出力次元数

    Returns:
        float のリスト（embeddingベクトル）、失敗時は None
    """
    client = get_genai_client()
    if client is None:
        return None

    from google.genai import types
    import mimetypes

    mime_type, _ = mimetypes.guess_type(audio_path)
    if mime_type is None:
        ext = os.path.splitext(audio_path)[1].lower()
        mime_type = _AUDIO_MIME_TYPES.get(ext)
        if mime_type is None:
            log(f"未対応の音声形式: {audio_path}", "ERROR")
            return None

    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
            config=types.EmbedContentConfig(
                output_dimensionality=dimensions,
            ),
        )
        values = response.embeddings[0].values
        log(f"音声embedding生成完了: {len(values)}次元, {audio_path}")
        return list(values)
    except Exception as e:
        log(f"音声embedding生成エラー: {e}", "ERROR")
        return None


def transcribe_audio(
    audio_path: str,
    instruction: str = "この音声を正確に文字起こししてください。話者が複数いる場合は区別してください。",
) -> Optional[str]:
    """
    Gemini 2.0 Flash で音声をテキストに文字起こし

    Args:
        audio_path: 音声ファイルパス
        instruction: 文字起こし指示

    Returns:
        文字起こしテキスト、失敗時は None
    """
    client = get_genai_client()
    if client is None:
        return None

    from google.genai import types
    import mimetypes

    mime_type, _ = mimetypes.guess_type(audio_path)
    if mime_type is None:
        ext = os.path.splitext(audio_path)[1].lower()
        mime_type = _AUDIO_MIME_TYPES.get(ext, "audio/mpeg")

    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                instruction,
            ],
        )
        text = response.text
        log(f"音声文字起こし完了: {len(text)}文字, {audio_path}")
        return text
    except Exception as e:
        log(f"音声文字起こしエラー: {e}", "ERROR")
        return None


def _get_audio_duration(path: str) -> float:
    """ffprobe で音声の長さ（秒）を取得。ffprobe がなければ -1 を返す"""
    import subprocess
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return -1  # 不明の場合はembedding試行に任せる


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


def search_meeting_records_semantic(
    query_text: str,
    top_k: int = 10,
    client_name: Optional[str] = None,
    index_name: str = "meeting_record_text_embedding",
) -> list[dict]:
    """
    面談記録のセマンティック検索

    Args:
        query_text: 検索クエリ（例: "服薬の飲み忘れ"）
        top_k: 返す結果の最大数
        client_name: クライアント名でフィルタ（オプション）
        index_name: 使用するインデックス
            - "meeting_record_text_embedding": テキスト（transcript/note）ベースの検索
            - "meeting_record_embedding": 音声ネイティブembeddingベースの検索

    Returns:
        面談記録のリスト（スコア付き）
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
            CALL db.index.vector.queryNodes($index_name, $top_k, $query_embedding)
            YIELD node, score
            MATCH (s:Supporter)-[:RECORDED]->(node)-[:ABOUT]->(c:Client)
            WHERE c.name CONTAINS $client_name
            RETURN node.date AS 日付,
                   node.title AS タイトル,
                   node.duration AS 秒数,
                   node.filePath AS ファイルパス,
                   s.name AS 記録者,
                   c.name AS クライアント,
                   node.note AS メモ,
                   COALESCE(left(node.transcript, 100), '') AS 文字起こし抜粋,
                   score AS スコア
            ORDER BY score DESC
            """,
            {
                "index_name": index_name,
                "top_k": top_k * 3,
                "query_embedding": query_embedding,
                "client_name": client_name,
            },
        )
    else:
        results = _run_query(
            """
            CALL db.index.vector.queryNodes($index_name, $top_k, $query_embedding)
            YIELD node, score
            MATCH (s:Supporter)-[:RECORDED]->(node)-[:ABOUT]->(c:Client)
            RETURN node.date AS 日付,
                   node.title AS タイトル,
                   node.duration AS 秒数,
                   node.filePath AS ファイルパス,
                   s.name AS 記録者,
                   c.name AS クライアント,
                   node.note AS メモ,
                   COALESCE(left(node.transcript, 100), '') AS 文字起こし抜粋,
                   score AS スコア
            ORDER BY score DESC
            """,
            {
                "index_name": index_name,
                "top_k": top_k,
                "query_embedding": query_embedding,
            },
        )

    log(f"面談記録セマンティック検索: '{query_text}' → {len(results)}件")
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


def register_meeting_record(
    audio_path: str,
    client_name: str,
    supporter_name: str,
    date: str,
    title: str = "",
    note: str = "",
    auto_transcribe: bool = True,
) -> dict:
    """
    音声ファイルから面談記録を登録

    1. 音声ファイルの長さチェック（80秒超はembeddingスキップ）
    2. 音声ファイルを embed_audio() でネイティブembedding
    3. auto_transcribe=True なら transcribe_audio() で文字起こし
    4. transcript/note のテキストを embed_text() でテキストembedding
    5. MeetingRecord ノードを作成
    6. Supporter→RECORDED→MeetingRecord→ABOUT→Client のリレーションを作成

    Returns:
        {"status": "success", "transcript": str, ...} または {"status": "error", ...}
    """
    if not os.path.exists(audio_path):
        return {"status": "error", "message": f"音声ファイルが見つかりません: {audio_path}"}

    abs_path = os.path.abspath(audio_path)

    # MIMEタイプ判定
    import mimetypes
    mime_type, _ = mimetypes.guess_type(audio_path)
    if mime_type is None:
        ext = os.path.splitext(audio_path)[1].lower()
        mime_type = _AUDIO_MIME_TYPES.get(ext, "audio/mpeg")

    # 音声の長さチェック
    duration = _get_audio_duration(audio_path)
    audio_embedding = None
    if duration <= 80 or duration < 0:
        # 80秒以下、または長さ不明の場合はembeddingを試行
        audio_embedding = embed_audio(audio_path)
        if audio_embedding is None:
            log("音声embedding生成失敗（テキストembeddingのみで続行）", "WARN")
    else:
        log(f"音声が80秒超 ({duration:.1f}秒) のためembeddingスキップ", "WARN")

    # 文字起こし
    transcript = None
    if auto_transcribe:
        transcript = transcribe_audio(audio_path)

    # テキストembedding（transcript + note を結合）
    text_parts = []
    if transcript:
        text_parts.append(transcript)
    if note:
        text_parts.append(note)
    text_for_embedding = "\n".join(text_parts) if text_parts else None

    text_embedding = None
    if text_for_embedding:
        text_embedding = embed_text(text_for_embedding, task_type="RETRIEVAL_DOCUMENT")

    # Neo4j に登録
    try:
        duration_int = int(duration) if duration > 0 else None
        _run_query(
            """
            MERGE (c:Client {name: $client_name})
            MERGE (s:Supporter {name: $supporter_name})
            CREATE (m:MeetingRecord {
                date: date($date),
                title: $title,
                duration: $duration,
                filePath: $file_path,
                mimeType: $mime_type,
                transcript: $transcript,
                note: $note
            })
            CREATE (s)-[:RECORDED]->(m)
            CREATE (m)-[:ABOUT]->(c)
            WITH m
            CALL { WITH m
                WITH m WHERE $audio_embedding IS NOT NULL
                CALL db.create.setNodeVectorProperty(m, 'embedding', $audio_embedding)
            }
            CALL { WITH m
                WITH m WHERE $text_embedding IS NOT NULL
                CALL db.create.setNodeVectorProperty(m, 'textEmbedding', $text_embedding)
            }
            RETURN elementId(m) AS id
            """,
            {
                "client_name": client_name,
                "supporter_name": supporter_name,
                "date": date,
                "title": title or f"面談記録 {date}",
                "duration": duration_int,
                "file_path": abs_path,
                "mime_type": mime_type,
                "transcript": transcript,
                "note": note or None,
                "audio_embedding": audio_embedding,
                "text_embedding": text_embedding,
            },
        )
        log(f"面談記録登録完了: {client_name} ({date})")
        return {
            "status": "success",
            "client_name": client_name,
            "date": date,
            "transcript": transcript,
            "audio_embedding": audio_embedding is not None,
            "text_embedding": text_embedding is not None,
        }
    except Exception as e:
        log(f"面談記録登録エラー: {e}", "ERROR")
        return {"status": "error", "message": str(e)}


# =============================================================================
# クライアント類似度分析
# =============================================================================

def build_client_summary_text(client_name: str) -> Optional[str]:
    """
    Neo4j から Client の関連情報を集約し、embedding用の概要テキストを構築

    Args:
        client_name: クライアント名

    Returns:
        構築された概要テキスト、データ不足の場合は None
    """
    results = _run_query(
        """
        MATCH (c:Client {name: $client_name})
        OPTIONAL MATCH (c)-[:HAS_CONDITION]->(con:Condition)
        OPTIONAL MATCH (c)-[:MUST_AVOID]->(ng:NgAction)
        OPTIONAL MATCH (c)-[:REQUIRES]->(cp:CarePreference)
        WITH c,
             collect(DISTINCT con.name) AS conditions,
             collect(DISTINCT ng.action) AS ngActions,
             collect(DISTINCT cp.instruction) AS careInstructions
        OPTIONAL MATCH (log:SupportLog)-[:ABOUT]->(c)
        WITH c, conditions, ngActions, careInstructions, log
        ORDER BY log.date DESC
        LIMIT 5
        WITH c, conditions, ngActions, careInstructions,
             collect(log.situation + '→' + COALESCE(log.action, '')) AS recentLogs
        RETURN c.name AS name,
               c.dob AS dob,
               c.bloodType AS bloodType,
               conditions,
               ngActions,
               careInstructions,
               recentLogs
        """,
        {"client_name": client_name},
    )

    if not results:
        log(f"クライアントが見つかりません: {client_name}", "WARN")
        return None

    r = results[0]
    parts = []

    # 基本情報
    basic = r.get("name", "")
    if r.get("dob"):
        basic += f"、{r['dob']}"
    if r.get("bloodType"):
        basic += f"、血液型{r['bloodType']}"
    parts.append(f"[基本情報] {basic}")

    # 障害・疾患
    conditions = [c for c in r.get("conditions", []) if c]
    if conditions:
        parts.append(f"[障害・疾患] {', '.join(conditions)}")

    # 禁忌事項
    ng_actions = [a for a in r.get("ngActions", []) if a]
    if ng_actions:
        parts.append(f"[禁忌事項] {', '.join(ng_actions)}")

    # ケアの要点
    care = [c for c in r.get("careInstructions", []) if c]
    if care:
        parts.append(f"[ケアの要点] {', '.join(care)}")

    # 主な支援状況
    logs = [entry for entry in r.get("recentLogs", []) if entry]
    if logs:
        parts.append(f"[主な支援状況] {'; '.join(logs)}")

    # 基本情報だけでは類似度分析に不十分
    if len(parts) <= 1:
        log(f"クライアント概要テキストの情報不足: {client_name}", "WARN")
        return None

    text = "\n".join(parts)
    log(f"クライアント概要テキスト構築完了: {client_name} ({len(text)}文字)")
    return text


def embed_client_summary(
    client_name: str,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> bool:
    """
    特定クライアントの summaryEmbedding を生成・付与

    1. build_client_summary_text() で概要テキスト構築
    2. embed_text(text, task_type="CLUSTERING") でembedding生成
    3. Neo4j の Client ノードに summaryEmbedding を付与

    Args:
        client_name: クライアント名
        dimensions: 出力次元数

    Returns:
        成功なら True
    """
    text = build_client_summary_text(client_name)
    if not text:
        return False

    embedding = embed_text(text, task_type="CLUSTERING", dimensions=dimensions)
    if embedding is None:
        log(f"Client summaryEmbedding 生成失敗: {client_name}", "ERROR")
        return False

    try:
        _run_query(
            """
            MATCH (c:Client {name: $name})
            CALL db.create.setNodeVectorProperty(c, 'summaryEmbedding', $embedding)
            """,
            {"name": client_name, "embedding": embedding},
        )
        log(f"Client summaryEmbedding 付与完了: {client_name}")
        return True
    except Exception as e:
        log(f"Client summaryEmbedding 付与エラー ({client_name}): {e}", "ERROR")
        return False


def find_similar_clients(
    client_name: str,
    top_k: int = 5,
    exclude_self: bool = True,
) -> list[dict]:
    """
    指定クライアントに支援特性が似ているクライアントを検索

    Args:
        client_name: 基準となるクライアント名
        top_k: 返す結果の最大数
        exclude_self: 自分自身を除外するか

    Returns:
        [{"name": str, "スコア": float, "conditions": list, ...}, ...]
    """
    base = _run_query(
        """
        MATCH (c:Client {name: $client_name})
        WHERE c.summaryEmbedding IS NOT NULL
        RETURN c.summaryEmbedding AS embedding
        """,
        {"client_name": client_name},
    )

    if not base:
        log(f"summaryEmbedding が未付与です: {client_name}", "WARN")
        return []

    query_vec = base[0]["embedding"]
    top_k_plus = top_k + (1 if exclude_self else 0)

    results = _run_query(
        """
        CALL db.index.vector.queryNodes('client_summary_embedding', $top_k_plus, $query_vec)
        YIELD node, score
        WHERE ($exclude_self = false OR node.name <> $client_name)
        OPTIONAL MATCH (node)-[:HAS_CONDITION]->(con:Condition)
        RETURN node.name AS name,
               node.dob AS dob,
               collect(DISTINCT con.name) AS conditions,
               score AS スコア
        ORDER BY score DESC
        LIMIT $top_k
        """,
        {
            "top_k_plus": top_k_plus,
            "query_vec": query_vec,
            "client_name": client_name,
            "exclude_self": exclude_self,
            "top_k": top_k,
        },
    )
    log(f"類似クライアント検索: {client_name} → {len(results)}件")
    return results


def search_similar_clients_by_text(
    description: str,
    top_k: int = 5,
) -> list[dict]:
    """
    テキスト説明から類似クライアントを検索

    新規利用者の特徴を入力し、既存クライアントから類似ケースを探す。

    Args:
        description: 支援特性の説明（例: "金銭管理が困難、訪問販売の被害歴あり"）
        top_k: 返す結果の最大数

    Returns:
        類似クライアントのリスト（スコア付き）
    """
    query_embedding = embed_text(
        description,
        task_type="RETRIEVAL_QUERY",
        dimensions=DEFAULT_DIMENSIONS,
    )
    if query_embedding is None:
        return []

    results = _run_query(
        """
        CALL db.index.vector.queryNodes('client_summary_embedding', $top_k, $query_embedding)
        YIELD node, score
        OPTIONAL MATCH (node)-[:HAS_CONDITION]->(con:Condition)
        RETURN node.name AS name,
               node.dob AS dob,
               collect(DISTINCT con.name) AS conditions,
               score AS スコア
        ORDER BY score DESC
        """,
        {
            "top_k": top_k,
            "query_embedding": query_embedding,
        },
    )
    log(f"テキストベース類似クライアント検索: '{description[:30]}...' → {len(results)}件")
    return results
