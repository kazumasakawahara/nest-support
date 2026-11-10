"""試走の DB に架空の印を置く道具（tests/live_mark.py）。DB を使わない部分（N-46 詰まり #2。2026-11-08 河原さん）。

- 接続先が試走の DB（個人の側 bolt://127.0.0.1:37687）でなければ、何もせずに止める
- 37687 なら架空の印（NestLiveProbe）を置く。何度打っても印は一つ（MERGE）
- 印を置くだけで、何も消さない（消すのは tests/live_cleanup.py。置く操作と消す操作を分けたまま）
"""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("live_mark", Path(__file__).with_name("live_mark.py"))
live_mark = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(live_mark)


class FakeDriver:
    def __init__(self):
        self.calls = []

    def execute_query(self, query, parameters=None, **kw):
        self.calls.append(query)
        return [], None, None


@pytest.mark.parametrize("uri", ["bolt://127.0.0.1:7687", "bolt://127.0.0.1:38687", "bolt://127.0.0.1:27687",
                                 "bolt://192.168.0.2:37687", "neo4j://127.0.0.1:37687"])
def test_refuses_unless_the_trial_db(uri):
    d = FakeDriver()
    with pytest.raises(RuntimeError):
        live_mark.place_mark(d, uri)
    assert d.calls == []


def test_places_one_mark_on_the_trial_db():
    d = FakeDriver()
    live_mark.place_mark(d, "bolt://127.0.0.1:37687")
    assert len(d.calls) == 1
    q = d.calls[0]
    assert "MERGE" in q and "NestLiveProbe" in q and "DELETE" not in q


def test_the_trial_db_is_the_personal_side():
    from nest import connections
    assert connections.SETTINGS["personal"][1] == live_mark.TRIAL_URI
