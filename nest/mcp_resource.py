"""資源の側の読み取りの MCP（N-22）。新しい資源の側（127.0.0.1:38687。tsunagu-net の書き出しの写し）にだけつなぐ。

歯止めは nest/mcp_guard.py。資源の側は公開情報なので伏せ字はしない。nest-support は資源の側に書かない（読み込みは N-23 の道具だけ）。

起動（.mcp.json から）：uv run --quiet python -m nest.mcp_resource
"""
from mcp.server import MCPServer

from nest import mcp_guard

server = MCPServer("nest-resource")


@server.tool()
def read_resource_cypher(query: str, params: dict | None = None) -> list[dict]:
    """資源の側（公開情報）に読み取りの Cypher を流す。読み取り以外は拒否する。最大 500 行。"""
    from nest import connections
    with connections.driver("resource") as d:
        return mcp_guard.run_read(d, query, params, personal=False)


@server.tool()
def resource_version() -> dict:
    """資源の側に読み込んだ一式の版と指紋（N-23 の記録）。照会の結果に添えて示す。読み込んでいなければ loaded: false。"""
    from nest import resource_load
    return resource_load.read_record() or {"loaded": False}


if __name__ == "__main__":
    server.run()
