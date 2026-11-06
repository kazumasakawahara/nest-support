"""N-43：手順書（docs/OPERATIONS.md）の new_staff のコマンドを、起動した個人の側でそのまま流す。NEST_LIVE_DB=1 のときだけ。

- 職員ができ、ゲートの監査ログ（Create）が管理者に結ばれる
- 管理者でない職員が打つと止まる（ゲートが止める）
- 出力の次の行（staff_token の add）を、そのまま staff_token に渡せる
"""
import importlib.util
import os
import re
import shlex
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

REPO = Path(__file__).resolve().parents[1]
STF = re.compile(r"STF-[0-9A-Z]{26}")
_spec = importlib.util.spec_from_file_location("doc_commands", REPO / "tests" / "doc_commands.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


def _q(d, query, **params):
    records, _, _ = d.execute_query(query, params, database_="neo4j")
    return [r.data() for r in records]


@pytest.fixture
def driver():
    from nest import connections
    with connections.driver("personal") as d:
        yield d


@pytest.fixture
def admin(driver):
    return _q(driver, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")[0]["id"]


def test_manual_commands_make_staff(driver, admin, capsys):
    lines = dc.lines("new_staff.py")
    assert lines
    for line in lines:
        assert dc.load("new_staff.py").main(dc.argv(line, {"STF-…": admin}), driver=driver) == 0, line
        out = capsys.readouterr().out
        made = [s for s in STF.findall(out) if s != admin]
        assert made, out
        role = "Administrator" if "--role Administrator" in line else "Staff"
        rows = _q(driver, """MATCH (s:Staff {staffId: $id})<-[:AUDIT_FOR]-(a:AuditLog)-[:ACTED_BY]->(by:Staff)
                             RETURN s.role AS role, s.origin AS origin, a.action AS action, by.staffId AS by""", id=made[0])
        assert rows == [{"role": role, "origin": "Human", "action": "Create", "by": admin}], rows


def test_a_non_admin_is_refused(driver, admin, capsys):
    line = next(l for l in dc.lines("new_staff.py") if "--role" not in l)
    assert dc.load("new_staff.py").main(dc.argv(line, {"STF-…": admin}), driver=driver) == 0
    plain = [s for s in STF.findall(capsys.readouterr().out) if s != admin][0]
    assert dc.load("new_staff.py").main(dc.argv(line, {"STF-…": plain}), driver=driver) == 1
    assert "作らなかった" in capsys.readouterr().out


def test_the_next_line_runs_as_is_with_staff_token(driver, admin, capsys, tmp_path):
    line = next(l for l in dc.lines("new_staff.py") if "--role" not in l)
    assert dc.load("new_staff.py").main(dc.argv(line, {"STF-…": admin}), driver=driver) == 0
    out = capsys.readouterr().out
    nxt = next(l for l in out.splitlines() if "scripts/staff_token.py add" in l)
    cmd = nxt[nxt.index("uv run python"):].strip()
    words = shlex.split(cmd)[4:]
    table = tmp_path / "field-ui-staff.json"
    assert dc.load("staff_token.py").main(words + ["--table", str(table)]) == 0
    assert STF.findall(out)[-1] in table.read_text(encoding="utf-8")
