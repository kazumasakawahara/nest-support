"""試験の DB を片づける道具（tests/live_cleanup.py）。DB を使わない部分。

- 架空の印（NestLiveProbe）のある DB でだけ動く。印が無ければ何も消さずに止める
- 印のノード以外をすべて消す（合流前の直し 1。2026-11-06 河原さん。台帳 G-87）
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
        if "count(m)" in query:
            return [_Record(marked=self.marked)], None, None
        return [_Record(n=0)], None, None


def test_refuses_without_the_fictional_mark():
    d = FakeDriver(marked=False)
    with pytest.raises(RuntimeError):
        live_cleanup.clear_fictional_db(d)
    assert not any("DELETE" in q for q in d.calls)


def test_deletes_clients_when_marked():
    d = FakeDriver(marked=True)
    live_cleanup.clear_fictional_db(d)
    deletes = [q for q in d.calls if "DETACH DELETE" in q]
    assert deletes and all("NOT n:NestLiveProbe" in q and ":Client" not in q for q in deletes)
