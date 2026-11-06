"""合流前の直し 2（台帳 G-87）を、起動した二つの DB で確かめる。NEST_LIVE_DB=1 のときだけ。

上限（試験では 3 行）より多い行を返す照会で、truncated が true になり、上限の値が付く。
"""
import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")


@pytest.mark.parametrize("side,personal", [("personal", True), ("resource", False)])
def test_more_rows_than_the_limit_are_marked(side, personal, monkeypatch):
    from nest import connections, mcp_guard
    monkeypatch.setattr(mcp_guard, "MAX_ROWS", 3)
    with connections.driver(side) as d:
        out = mcp_guard.run_read_meta(d, "UNWIND range(1, 10) AS i RETURN i", {}, personal=personal)
        assert out == {"rows": [{"i": 1}, {"i": 2}, {"i": 3}], "truncated": True, "maxRows": 3}
        out = mcp_guard.run_read_meta(d, "UNWIND range(1, 3) AS i RETURN i", {}, personal=personal)
        assert out["truncated"] is False
