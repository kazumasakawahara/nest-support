"""N-05b：.mcp.json に Neo4j の MCP を置かない（台帳 G-35 の 2。external-api NEXT-11 の前倒し）。

前の DB（7688）や共有層（7687）を、Claude が照会して Anthropic に送る経路を残さない。
N-22 の読み取りだけの包みができたら、新しい項目として入れ直す（この試験もそのときに改める）。
"""
import json

from nest import egress


def test_mcp_json_has_no_neo4j_server():
    data = json.loads((egress.REPO / ".mcp.json").read_text(encoding="utf-8"))
    text = json.dumps(data, ensure_ascii=False).lower()
    for word in ("neo4j", "7688", "7687", "bolt://", "npx"):
        assert word not in text, word
