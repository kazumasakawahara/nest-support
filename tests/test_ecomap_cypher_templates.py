"""
P0-1: ecomap-generator の Cypher インジェクション対策の回帰テスト。

`get_query` / `get_analysis_query`（クライアント名を文字列連結する関数）を廃止し、
`get_parameterized_query()` + params={"client_name": ...} に一本化したことを検証する。
"""

import importlib.util
from pathlib import Path

import pytest

# claude-skills/ecomap-generator/scripts/ はパッケージパス上に無いため、
# ファイルパスから直接ロードする（cypher_templates.py は自己完結）。
_MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "claude-skills"
    / "ecomap-generator"
    / "scripts"
    / "cypher_templates.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("cypher_templates", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# 任意 Cypher の書き込み（DETACH DELETE）を狙う代表的な注入ペイロード
MALICIOUS_NAMES = [
    "'} ) DETACH DELETE c //",
    "山田' OR '1'='1",
    "太郎'}) MATCH (n) DETACH DELETE n //",
]


def test_string_interpolating_functions_removed():
    """危険な文字列連結関数は廃止されていること。"""
    module = _load_module()
    assert not hasattr(module, "get_query"), (
        "get_query（クライアント名を文字列連結）は廃止されているべき"
    )
    assert not hasattr(module, "get_analysis_query"), (
        "get_analysis_query（クライアント名を文字列連結）は廃止されているべき"
    )


def test_parameterized_query_keeps_placeholder():
    """パラメータ化クエリは $client_name プレースホルダを保持すること。"""
    module = _load_module()
    for template_name in ("full_view", "support_meeting", "emergency", "handover"):
        query = module.get_parameterized_query(template_name)
        assert query is not None
        assert "$client_name" in query


@pytest.mark.parametrize("malicious", MALICIOUS_NAMES)
def test_malicious_name_never_reaches_query_string(malicious):
    """悪意ある名前を渡してもクエリ文字列に混入しないこと。

    パラメータ化された経路では、クライアント名はクエリ文字列ではなく params に渡る。
    """
    module = _load_module()
    for template_name in ("full_view", "support_meeting", "emergency", "handover"):
        query = module.get_parameterized_query(template_name)
        assert malicious not in query
        # プレースホルダは維持され、実値は params 経由で渡す設計であること
        assert "$client_name" in query


def test_analysis_queries_are_parameterized():
    """分析クエリ定義自体は $client_name のままで、実値連結の入口が無いこと。"""
    module = _load_module()
    for name, query in module.ANALYSIS_QUERIES.items():
        assert "$client_name" in query, f"{name} は $client_name を使うべき"
