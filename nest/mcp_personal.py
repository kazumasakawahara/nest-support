"""個人の側の読み取りの MCP（N-22）。新しい個人の側（127.0.0.1:37687）にだけつなぐ。

歯止めは nest/mcp_guard.py（読み取り以外・LOAD CSV・許可外の手続き・読めない計画を実行前に拒否。行は 500 行まで）。
個人の側では、実名・かな・電話・住所（Residence.address）・生年月日と、記録の原文（text）を返さない。
引用（quote）は read_quote で求めたときだけ、上限の字数まで返す（台帳 G-42 (1)）。
どの道具も、NEXT-02 の歯止めがそろうか、架空の印のある DB のときだけ動く（台帳 G-54 (3)）。
名前を受け取る道具は作らない。名前から仮名を引くのは Claude の外で行う（台帳 G-42 (2)）。

起動（.mcp.json から）：uv run --quiet python -m nest.mcp_personal
"""
from pathlib import Path

from mcp.server import MCPServer

from nest import canon, mcp_guard

REPO = Path(__file__).resolve().parents[1]
server = MCPServer("nest-personal")


@server.tool()
def read_personal_cypher(query: str, params: dict | None = None) -> list[dict]:
    """個人の側に読み取りの Cypher を流す。読み取り以外は拒否する。実名・かな・電話・住所・生年月日は返さない。最大 500 行。"""
    from nest import connections
    with connections.driver("personal") as d:
        mcp_guard.require_personal_allowed(d)
        return mcp_guard.run_read(d, query, params, personal=True)


@server.tool()
def read_quote(record_id: str) -> dict:
    """記録（Record）の引用を、上限の字数までで返す。原文全体（text）は返さない。実名と同じ文字列は伏せる。"""
    from nest import connections
    with connections.driver("personal") as d:
        mcp_guard.require_personal_allowed(d)

        def work(tx):
            rows = list(tx.run("MATCH (r:Record {recordId: $id}) RETURN r.quote AS q", id=record_id))
            values = frozenset(list(tx.run(mcp_guard.SENSITIVE_VALUES, names=list(mcp_guard.SENSITIVE)))[0]["vs"])
            return rows, values
        with d.session(database="neo4j") as s:
            rows, values = s.execute_read(work)
    if not rows:
        return {"recordId": record_id, "found": False}
    out = mcp_guard.cap_quote(rows[0]["q"])
    out["quote"] = mcp_guard.to_plain(out["quote"], True, values)
    return {"recordId": record_id, "found": True, **out}


@server.tool()
def personal_schema() -> dict:
    """個人の側のスキーマ（正典 docs/SCHEMA.md の machine-check JSON）。"""
    c = canon.load(REPO / "docs" / "SCHEMA.md")
    return {"version": c["version"], "nodes": c["personal"]["nodes"], "relationships": c["personal"]["relationships"],
            "enums": c["enums"], "notReturned": list(mcp_guard.SENSITIVE)}


if __name__ == "__main__":
    server.run()
