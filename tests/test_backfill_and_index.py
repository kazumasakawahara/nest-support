"""
P1-8: バックフィルの進捗ゼロ無限ループ防止。
P1-9: セマンティック検索のベクトルインデックス名フォールバック統一。
"""

import lib.embedding as embedding
import scripts.backfill_embeddings as bf


def test_backfill_loop_breaks_on_zero_progress(monkeypatch):
    """P1-8: embedding が全件失敗してもフルバッチを無限取得しない。

    embedding IS NULL のノードが常にフルバッチで返る状況で、埋め込みが
    毎回失敗する（API 障害等）と、進捗ゼロのまま同じバッチを取得し続ける。
    進捗ゼロ検知で 1 バッチ処理後に中断すること。
    """
    fetch_calls = {"n": 0}

    def fake_fetch(bs):
        fetch_calls["n"] += 1
        if fetch_calls["n"] > 3:
            raise AssertionError("無限ループ: 進捗ゼロでも fetch を継続している")
        return [{"id": f"e{i}", "situation": "状況あり"} for i in range(bs)]

    # 埋め込みは常に失敗（None）
    monkeypatch.setattr(embedding, "embed_texts_batch",
                        lambda texts: [None] * len(texts))

    result = bf._backfill_loop(
        label="SupportLog",
        fetch_fn=fake_fetch,
        text_fn=bf._support_log_text,
        batch_size=3,
        dry_run=False,
    )

    assert fetch_calls["n"] == 1, "進捗ゼロなのに2バッチ目を取得している"
    assert result["success"] == 0
    assert result["failed"] == 3


def test_backfill_loop_breaks_on_write_failure(monkeypatch):
    """R2-4: embedding は成功するが DB 書き込みが常に失敗する場合も有限回で停止する。

    付与クエリが run_query（例外握り潰し）だと失敗が成功に数えられ、ノードが
    NULL のまま同一フルバッチを永久再取得する。execute_write 化で失敗を検知し停止。
    """
    import lib.db_operations as dbops

    fetch_calls = {"n": 0}

    def fake_fetch(bs):
        fetch_calls["n"] += 1
        if fetch_calls["n"] > 3:
            raise AssertionError("無限ループ: 書き込み失敗でも fetch を継続している")
        return [{"id": f"e{i}", "situation": "状況あり"} for i in range(bs)]

    # embedding は成功（有効ベクトル）だが、DB 書き込みは常に失敗する
    monkeypatch.setattr(embedding, "embed_texts_batch",
                        lambda texts: [[0.0] * 768 for _ in texts])

    def boom(query, params=None):
        raise RuntimeError("setNodeVectorProperty 失敗（次元不一致）")

    monkeypatch.setattr(dbops, "execute_write", boom)

    result = bf._backfill_loop(
        label="SupportLog",
        fetch_fn=fake_fetch,
        text_fn=bf._support_log_text,
        batch_size=3,
        dry_run=False,
    )

    assert fetch_calls["n"] == 1, "書き込み失敗が成功に数えられ2バッチ目を取得している"
    assert result["success"] == 0
    assert result["failed"] == 3


def _run_query_stub(monkeypatch, captured):
    def stub(query, params=None):
        captured.append((query, params or {}))
        # SHOW INDEXES 応答（resolve_vector_index 用）: 別名インデックスのみ実在
        if "SHOW INDEXES" in query:
            return [{"name": "renamed_index"}]
        # ベクトル検索本体は空で良い
        return []
    monkeypatch.setattr(embedding, "_run_query", stub)
    monkeypatch.setattr(embedding, "embed_text",
                        lambda *a, **k: [0.0] * embedding.DEFAULT_DIMENSIONS)


def test_ng_action_search_uses_resolved_index(monkeypatch):
    """P1-9: search_ng_actions_semantic は resolve_vector_index を通す。"""
    embedding._vector_index_cache.clear()
    captured = []
    _run_query_stub(monkeypatch, captured)

    embedding.search_ng_actions_semantic("大きな音")

    # 検索クエリはインデックス名をパラメータ化し、解決済み名を渡していること
    search_calls = [(q, p) for q, p in captured if "queryNodes" in q]
    assert search_calls, "ベクトル検索が発行されていない"
    q, p = search_calls[0]
    assert "$index_name" in q, "インデックス名が直書きのまま（フォールバック不可）"
    assert p["index_name"] == "renamed_index", "リネーム済みインデックスにフォールバックしていない"


def test_similar_clients_by_text_uses_resolved_index(monkeypatch):
    """P1-9: search_similar_clients_by_text も同様にフォールバック。"""
    embedding._vector_index_cache.clear()
    captured = []
    _run_query_stub(monkeypatch, captured)

    embedding.search_similar_clients_by_text("金銭管理が困難")

    search_calls = [(q, p) for q, p in captured if "queryNodes" in q]
    assert search_calls
    q, p = search_calls[0]
    assert "$index_name" in q
    assert p["index_name"] == "renamed_index"
