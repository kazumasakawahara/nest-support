"""
P1-19: エコマップ生成が DB 未接続/クライアント不在で架空データを出さない。
P1-21: HTML/SVG 生成の出力エスケープ（</script> 脱出・XML エスケープ）。
"""

import importlib
import sys
from pathlib import Path

import pytest

_SCRIPTS = (
    Path(__file__).resolve().parent.parent
    / "claude-skills" / "ecomap-generator" / "scripts"
)


@pytest.fixture(scope="module")
def mods():
    sys.path.insert(0, str(_SCRIPTS))
    gm = importlib.import_module("generate_mermaid")
    gh = importlib.import_module("generate_html")
    gs = importlib.import_module("generate_svg")
    yield gm, gh, gs


# --- P1-19 ---

def test_no_neo4j_raises_not_fabricates(mods, monkeypatch):
    gm, _, _ = mods
    monkeypatch.setattr(gm, "HAS_NEO4J", False)
    with pytest.raises(RuntimeError):
        gm.fetch_client_data("実在太郎", demo=False)


def test_demo_flag_returns_sample_marked_demo(mods):
    gm, _, _ = mods
    data = gm.fetch_client_data("架空太郎", demo=True)
    assert data.get("is_demo") is True
    assert data["ngActions"], "デモデータにサンプルが含まれる"


def test_mermaid_demo_output_has_banner(mods):
    gm, _, _ = mods
    out = gm.generate_mermaid_ecomap("架空太郎", demo=True)
    assert "デモデータ" in out


def test_client_not_found_raises(mods, monkeypatch):
    gm, _, _ = mods
    monkeypatch.setattr(gm, "HAS_NEO4J", True)
    monkeypatch.setattr(gm, "run_query", lambda q, p=None: [])  # 該当なし
    with pytest.raises(ValueError):
        gm.fetch_client_data("居ない花子", demo=False)


# --- P1-21 ---

def test_json_for_script_escapes_closing_tag(mods):
    _, gh, _ = mods
    payload = {"name": "</script><img src=x onerror=alert(1)>"}
    out = gh._json_for_script(payload)
    assert "</script>" not in out
    assert "<\\/script>" in out


def test_svg_node_label_is_xml_escaped(mods):
    _, _, gs = mods
    node = gs.SvgNode(id="n1", label="<script>&", node_type="NgAction")
    svg = gs.generate_svg_node(node)
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg or "&lt;scr" in svg  # 切り詰め後もエスケープされる


def test_svg_title_is_xml_escaped(mods):
    _, _, gs = mods
    svg = gs.generate_svg("<b>タイトル</b>", nodes=[], edges=[], include_legend=False)
    assert "<b>タイトル</b>" not in svg
    assert "&lt;b&gt;" in svg
