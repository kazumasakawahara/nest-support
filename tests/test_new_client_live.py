"""N-39：本人を Claude の外で作る入口（scripts/new_client.py）を、試験用の DB（127.0.0.1:36687）で確かめる。
NEST_LIVE_DB=1 のときだけ。架空のデータだけ。

    NEST_LIVE_DB=1 uv run pytest -q tests/test_new_client_live.py

- 作る：仮名が画面に出る。本人・住まい・RESIDES_AT ができ、ゲートの監査ログ（Create）が職員に結ばれる
- 引く：名前から仮名が出る
- 二重登録を止める：同じ氏名・生年月日の本人がいれば作らない。生年月日がどちらかに無ければ、氏名だけで止める
"""
import importlib.util
import os
import re
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

REPO = Path(__file__).resolve().parents[1]
CODE = re.compile(r"C-[0-9A-Z]{6}")


def _script():
    spec = importlib.util.spec_from_file_location("new_client", REPO / "scripts" / "new_client.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    rows = _q(driver, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")
    if not rows:
        pytest.skip("Administrator がいない（ほかの DB つきの試験を先に流す）")
    return rows[0]["id"]


def _add(admin, given, *extra, driver):
    return _script().main(["add", "--staff", admin, "--family", "架空", "--given", given, *extra], driver=driver)


def test_add_creates_client_and_residence_and_prints_the_code(driver, admin, capsys):
    given = "花子" + uuid.uuid4().hex[:8]
    assert _add(admin, given, "--birth", "1990-04-01", "--address", "福岡県北九州市小倉北区架空町1-2-3", "--address-certainty", "Confirmed", driver=driver) == 0
    out = capsys.readouterr().out
    codes = CODE.findall(out)
    assert len(codes) == 1
    rows = _q(driver, """MATCH (c:Client {displayCode: $code})-[:RESIDES_AT]->(r:Residence)
                         RETURN c.familyName AS f, c.givenName AS g, toString(c.birthDate) AS b, c.origin AS o,
                                r.address AS a, r.areaCode AS area""", code=codes[0])
    assert rows == [{"f": "架空", "g": given, "b": "1990-04-01", "o": "Human", "a": "福岡県北九州市小倉北区架空町1-2-3",
                     "area": "401064"}]
    audits = _q(driver, """MATCH (c:Client {displayCode: $code})<-[:AUDIT_FOR]-(a:AuditLog)-[:ACTED_BY]->(s:Staff)
                           RETURN a.action AS action, s.staffId AS s ORDER BY action""", code=codes[0])
    assert {a["action"] for a in audits} == {"Create"} and {a["s"] for a in audits} == {admin}


def test_find_returns_the_code_from_the_name(driver, admin, capsys):
    given = "次郎" + uuid.uuid4().hex[:8]
    assert _add(admin, given, driver=driver) == 0
    code = CODE.findall(capsys.readouterr().out)[0]
    assert _script().main(["find", "--family", "架空", "--given", given], driver=driver) == 0
    assert CODE.findall(capsys.readouterr().out) == [code]


def test_find_with_no_match_says_so(driver, capsys):
    assert _script().main(["find", "--family", "架空", "--given", "無い" + uuid.uuid4().hex[:8]], driver=driver) == 1
    assert "見つからない" in capsys.readouterr().out


def test_same_name_and_birth_date_is_refused(driver, admin, capsys):
    given = "三郎" + uuid.uuid4().hex[:8]
    assert _add(admin, given, "--birth", "1985-01-02", driver=driver) == 0
    first = CODE.findall(capsys.readouterr().out)[0]
    assert _add(admin, given, "--birth", "1985-01-02", driver=driver) == 1
    out = capsys.readouterr().out
    assert "二重登録" in out and first in out
    assert _q(driver, "MATCH (c:Client {familyName: '架空', givenName: $g}) RETURN count(c) AS n", g=given) == [{"n": 1}]


def test_same_name_without_a_birth_date_is_refused(driver, admin, capsys):
    given = "四郎" + uuid.uuid4().hex[:8]
    assert _add(admin, given, "--birth", "1985-01-02", driver=driver) == 0
    capsys.readouterr()
    assert _add(admin, given, driver=driver) == 1
    assert "二重登録" in capsys.readouterr().out


def test_same_name_with_a_different_birth_date_is_allowed(driver, admin, capsys):
    given = "五郎" + uuid.uuid4().hex[:8]
    assert _add(admin, given, "--birth", "1985-01-02", driver=driver) == 0
    assert _add(admin, given, "--birth", "1999-12-31", driver=driver) == 0
    assert len(set(CODE.findall(capsys.readouterr().out))) == 2
