"""合流前の直し 2（2026-11-06 河原さん。台帳 G-87）：MCP の照会の道具は、行の一覧と別に truncated と上限の値を返す。
neo4j-support-db の SKILL.md に、truncated のときの書き方を一行置く。DB を使わない。"""
import contextlib
from pathlib import Path

from nest import connections, mcp_guard, mcp_personal, mcp_resource

REPO = Path(__file__).resolve().parents[1]
OUT = {"rows": [{"i": 1}], "truncated": True, "maxRows": 500}


def _fake(monkeypatch):
    @contextlib.contextmanager
    def _driver(side):
        yield "fake-driver"
    monkeypatch.setattr(connections, "driver", _driver)
    monkeypatch.setattr(mcp_guard, "require_personal_allowed", lambda d, caller="mcp": None)
    monkeypatch.setattr(mcp_guard, "run_read_meta", lambda d, q, p, personal: OUT)


def test_personal_tool_returns_rows_and_the_cut_mark(monkeypatch):
    _fake(monkeypatch)
    assert mcp_personal.read_personal_cypher("MATCH (n) RETURN n") == OUT


def test_resource_tool_returns_rows_and_the_cut_mark(monkeypatch):
    _fake(monkeypatch)
    assert mcp_resource.read_resource_cypher("MATCH (n) RETURN n") == OUT


def test_skill_says_what_to_do_when_cut():
    text = (REPO / "claude-skills" / "neo4j-support-db" / "SKILL.md").read_text(encoding="utf-8")
    assert "truncated" in text and "絞り直す" in text
