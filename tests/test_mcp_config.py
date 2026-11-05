"""N-22：.mcp.json に入れ直したのは、nest-support の読み取りだけの包み二つだけ（台帳 G-35 の 2）。

N-05b では Neo4j の MCP を外していた（前の DB 7688・共有層 7687 を照会して送る経路を残さないため）。
N-22 で、新しい個人の側（37687）と資源の側（38687）に、読み取りだけの包みでつなぐ形で入れ直した。
汎用の Neo4j の MCP（npx・mcp-neo4j-cypher）と neo4j-shared は使わない。パスワードは .mcp.json に書かない
（包みが ~/.config/nest/neo4j-redesign.env から読む）。
"""
import json

from nest import egress

MCP = egress.REPO / ".mcp.json"


def _servers():
    return json.loads(MCP.read_text(encoding="utf-8"))["mcpServers"]


def test_only_the_two_read_only_wrappers():
    servers = _servers()
    assert set(servers) == {"nest-personal", "nest-resource"}
    assert servers["nest-personal"]["args"][-2:] == ["-m", "nest.mcp_personal"]
    assert servers["nest-resource"]["args"][-2:] == ["-m", "nest.mcp_resource"]


def test_no_old_db_generic_server_or_password():
    text = MCP.read_text(encoding="utf-8").lower()
    for word in ("7688", "7687", "neo4j-shared", "npx", "mcp-neo4j", "password", "bolt://"):
        assert word not in text, word
    for s in _servers().values():
        assert "env" not in s
