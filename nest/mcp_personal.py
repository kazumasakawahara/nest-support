"""個人の側の読み取りの MCP（N-22）。新しい個人の側（127.0.0.1:37687）にだけつなぐ。

歯止めは nest/mcp_guard.py（読み取り以外・LOAD CSV・許可外の手続き・読めない計画を実行前に拒否。行は 500 行まで）。
個人の側では、実名・かな・電話・住所（Residence.address）・生年月日を返さない。記録の引用の中の名前は台帳 G-42 で決める。
今の個人の側に入っているのは架空のものだけ。実データを入れる前に、ここで NEXT-02 の歯止め（契約の確認の記録）を
求めるかを決める（台帳 G-54）。

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
        return mcp_guard.run_read(d, query, params, personal=True)


@server.tool()
def personal_schema() -> dict:
    """個人の側のスキーマ（正典 docs/SCHEMA.md の machine-check JSON）。"""
    c = canon.load(REPO / "docs" / "SCHEMA.md")
    return {"version": c["version"], "nodes": c["personal"]["nodes"], "relationships": c["personal"]["relationships"],
            "enums": c["enums"], "notReturned": list(mcp_guard.SENSITIVE)}


if __name__ == "__main__":
    server.run()
