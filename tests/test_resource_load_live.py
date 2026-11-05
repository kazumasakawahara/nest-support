"""N-23：資源の側に一式の書き出しを読み込んだ後の確かめ。NEST_LIVE_DB=1 のときだけ。

    uv run python scripts/load_resource.py --bundle ~/Dist/tsunagu-net-trial-20261104 --write
    NEST_LIVE_DB=1 uv run pytest -q tests/test_resource_load_live.py

機関の数 4,358 は、tsunagu-net の docs/distribution/README.md の「2026-11-04 の一式」の記載（読むだけ）。
"""
import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

BUNDLE = Path.home() / "Dist" / "tsunagu-net-trial-20261104"


def _read(side, query):
    from nest import connections
    with connections.driver(side) as d:
        records, _, _ = d.execute_query(query, routing_="r", database_="neo4j")
        return [r.data() for r in records]


def test_record_matches_the_bundle_manifest():
    from nest import resource_load as rl
    rec = rl.read_record()
    assert rec, "読み込みの記録が無い"
    manifest = json.loads((BUNDLE / "MANIFEST.json").read_text(encoding="utf-8"))
    want = {f["path"]: f["sha256"] for f in manifest["files"]}[rec["dump"]]
    assert rec["sha256"] == want and rec["schemaVersion"] == "v0.29"


def test_resource_side_has_the_organizations():
    assert _read("resource", "MATCH (o:Organization) RETURN count(o) AS n") == [{"n": 4358}]


def test_personal_side_was_not_touched():
    assert _read("personal", "MATCH (o:Organization) WHERE o.name IS NOT NULL RETURN count(o) AS n") == [{"n": 0}]
    assert _read("personal", "MATCH (s:Staff) RETURN count(s) > 0 AS any") == [{"any": True}]
