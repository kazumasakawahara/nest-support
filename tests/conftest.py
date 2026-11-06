"""DB つきの試験（NEST_LIVE_DB=1）の前提：個人の側に Active な Administrator が一人いること。

試験の DB を片づけの道具（tests/live_cleanup.py）で空にした後でも、Administrator が要る試験が skip しないように、
いなければゲートの最初の管理者の入口（nest.gate.bootstrap）で架空の管理者を一人作る（合流前の直し。台帳 G-87）。
NEST_LIVE_DB が無いときは何もしない。
"""
import os
import uuid

import pytest


@pytest.fixture(scope="session", autouse=True)
def _live_admin():
    if os.environ.get("NEST_LIVE_DB") != "1":
        return
    from nest import connections
    from nest.gate import bootstrap
    with connections.driver("personal") as d:
        records, _, _ = d.execute_query("MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN count(s) AS n",
                                        database_="neo4j")
        if records[0]["n"] == 0:
            out = bootstrap.bootstrap_admin(d, "架空の管理者", "req-bootstrap-" + uuid.uuid4().hex)
            assert out["ok"], out["errors"]
