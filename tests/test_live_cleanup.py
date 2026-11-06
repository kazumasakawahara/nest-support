"""試験の DB の架空の本人を片づける道具（tests/live_cleanup.py）。DB を使わない部分。

- 架空の印（NestLiveProbe）のある DB でだけ動く。印が無ければ何も消さずに止める
"""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("live_cleanup", Path(__file__).with_name("live_cleanup.py"))
live_cleanup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(live_cleanup)


class _Record(dict):
    pass


class FakeDriver:
    def __init__(self, marked):
        self.marked, self.calls = marked, []

    def execute_query(self, query, parameters=None, **kw):
        self.calls.append(query)
        if "NestLiveProbe" in query:
            return [_Record(marked=self.marked)], None, None
        return [_Record(n=0)], None, None


def test_refuses_without_the_fictional_mark():
    d = FakeDriver(marked=False)
    with pytest.raises(RuntimeError):
        live_cleanup.clear_fictional_clients(d)
    assert not any("DELETE" in q for q in d.calls)


def test_deletes_clients_when_marked():
    d = FakeDriver(marked=True)
    live_cleanup.clear_fictional_clients(d)
    assert any("DETACH DELETE" in q and ":Client" in q for q in d.calls)
