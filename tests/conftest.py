"""DB つきの試験（NEST_LIVE_DB=1）の前提。

- 向き先が試験用の DB（NEST_DB_TARGET=test。127.0.0.1:36687）でなければ、始まりで止める。試走の DB（37687）では
  DB つきの試験を動かさない（2026-11-12 河原さんの決めごと。案 A。台帳 G-103）
- 試験用の DB に専用の印（NestTestDbProbe）が無ければ止める（印は tests/live_testdb.py mark で、空の DB にだけ置ける）
- 印があれば、始まりで試験用の DB を空にし（二つの印は残す）、正典の制約・索引を作る
- 個人の側に Active な Administrator がいなければ、ゲートの最初の管理者の入口（nest.gate.bootstrap）で架空の管理者を一人作る
  （合流前の直し。台帳 G-87）
NEST_LIVE_DB が無いときは何もしない。
"""
import os
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def pytest_sessionstart(session):
    if os.environ.get("NEST_LIVE_DB") != "1":
        return
    from tests import live_testdb
    try:
        live_testdb.require_test_target()
    except RuntimeError as e:
        pytest.exit(str(e), returncode=2)


@pytest.fixture(scope="session", autouse=True)
def _live_admin():
    if os.environ.get("NEST_LIVE_DB") != "1":
        return
    from nest import canon, connections, schema_apply
    from nest.gate import bootstrap
    from tests import live_testdb
    with connections.driver("personal") as d:
        try:
            removed = live_testdb.clear_test_db(d, connections.uri("personal"))
        except RuntimeError as e:
            pytest.exit("%s（初めの一度：NEST_DB_TARGET=test uv run python tests/live_testdb.py mark）" % e, returncode=2)
        print("試験用の DB を空にした：%d 件（印は残した）" % removed)
        schema_apply.apply(d, canon.load(REPO / "docs" / "SCHEMA.md"))
        records, _, _ = d.execute_query("MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN count(s) AS n",
                                        database_="neo4j")
        if records[0]["n"] == 0:
            out = bootstrap.bootstrap_admin(d, "架空の管理者", "req-bootstrap-" + uuid.uuid4().hex)
            assert out["ok"], out["errors"]
