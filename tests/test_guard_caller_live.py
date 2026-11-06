"""判断 2（台帳 G-85）を、起動した個人の側（127.0.0.1:37687）で確かめる。NEST_LIVE_DB=1 のときだけ。架空のデータだけ。

    NEST_LIVE_DB=1 uv run pytest -q tests/test_guard_caller_live.py

記録が無く、架空の印も無いものとして（印の照会を「無い」に差し替える）：
- MCP の経路は拒否する
- 画面（field-ui）の経路は読める。返す本人から実名・かな・生年月日は外れている
"""
import importlib.util
import os
import sys
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

REPO = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def unmarked_without_record(monkeypatch):
    from nest import egress, mcp_guard

    def _deny(row):
        raise egress.EgressDenied("記録が無い（試験）")
    monkeypatch.setattr(egress, "authorize", _deny)
    monkeypatch.setattr(mcp_guard, "FICTIONAL_MARK", "RETURN false AS marked")


@pytest.fixture
def code(capsys):
    from nest import connections
    with connections.driver("personal") as d:
        records, _, _ = d.execute_query(
            "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1",
            database_="neo4j")
        if not records:
            pytest.skip("Administrator がいない（ほかの DB つきの試験を先に流す）")
        nc = _load("new_client_caller", REPO / "scripts" / "new_client.py")
        given = "画面" + uuid.uuid4().hex[:8]
        assert nc.main(["add", "--staff", records[0]["id"], "--family", "架空", "--given", given,
                        "--birth", "1990-04-01"], driver=d) == 0
    out = capsys.readouterr().out
    return out.split("仮名：")[1][:8]


def test_mcp_path_is_refused(unmarked_without_record):
    from nest import connections, mcp_guard
    with connections.driver("personal") as d:
        with pytest.raises(mcp_guard.NotReadOnly):
            mcp_guard.require_personal_allowed(d)


def test_screen_path_reads_but_hides_names(unmarked_without_record, code):
    sys.path.insert(0, str(REPO / "field-ui"))
    ui = _load("field_ui_server_live_caller", REPO / "field-ui" / "server.py")
    rows = ui.read_personal("MATCH (c:Client {displayCode: $code}) RETURN c", {"code": code})
    assert len(rows) == 1
    node = rows[0]["c"]
    assert node.get("displayCode") == code
    for key in ("familyName", "givenName", "familyNameKana", "givenNameKana", "birthDate"):
        assert key not in node, key
