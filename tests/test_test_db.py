"""DB を使う試験の専用の DB（2026-11-12 河原さんの決めごと。案 A。台帳 G-103）。DB を使わない（偽の DB）。

b 試験用の DB を空にする処理は、試験用の DB にだけ置く専用の印（NestTestDbProbe）を確かめてからでなければ動かない。
  印が無ければ空にせず止まる。ポート番号だけで見分けない。試走の DB に向けて呼ぶと止まる
c 接続先の切り替えは、決まった二つ（試走・試験用）から選ぶだけ。任意の接続先を外から渡せない
d Claude Desktop の道具と端末の道具は、今までどおり試走の DB に向く（切り替えの指定が無ければ試走）
e DB を使う試験は、試走の DB に向いた状態では動かず止まる
"""
import os
import subprocess
from pathlib import Path

import pytest

from nest import connections
from tests import live_testdb

REPO = Path(__file__).resolve().parents[1]
TRIAL = "bolt://127.0.0.1:37687"
TEST = "bolt://127.0.0.1:36687"


class FakeDriver:
    """印の有無と、ノードの数を返す偽の DB。流した文を残す。"""

    def __init__(self, labels=(), nodes=0):
        self.labels, self.nodes, self.calls = set(labels), nodes, []

    def execute_query(self, query, parameters=None, **kw):
        self.calls.append(query)
        if "count(m) > 0 AS marked" in query:
            label = query.split("(m:")[1].split(")")[0]
            return [{"marked": label in self.labels}], None, None
        if "count(n) AS n" in query:
            return [{"n": self.nodes}], None, None
        return [{"n": 0}], None, None


def _writes(d):
    return [q for q in d.calls if any(w in q for w in ("DELETE", "CREATE", "MERGE", "SET"))]


# ---- c・d 接続先の切り替え ----

def test_the_default_target_is_the_trial_db(monkeypatch):
    monkeypatch.delenv("NEST_DB_TARGET", raising=False)
    assert connections.target() == "trial" and connections.uri("personal") == TRIAL


def test_the_test_target_points_to_the_test_db(monkeypatch):
    monkeypatch.setenv("NEST_DB_TARGET", "test")
    assert connections.uri("personal") == TEST


@pytest.mark.parametrize("value", ["", "Test", "prod", "bolt://127.0.0.1:7687", "bolt://127.0.0.1:36687", "37687"])
def test_any_other_target_stops(monkeypatch, value):
    monkeypatch.setenv("NEST_DB_TARGET", value)
    with pytest.raises(RuntimeError):
        connections.uri("personal")


def test_the_targets_are_fixed_to_two():
    assert connections.TARGETS == {"trial": TRIAL, "test": TEST}


def test_the_resource_side_is_shared(monkeypatch):
    for value in ("trial", "test"):
        monkeypatch.setenv("NEST_DB_TARGET", value)
        assert connections.uri("resource") == "bolt://127.0.0.1:38687"


def test_no_other_variable_sets_the_address(monkeypatch):
    monkeypatch.delenv("NEST_DB_TARGET", raising=False)
    for key in ("NEST_PERSONAL_URI", "NEO4J_URI", "NEST_DB_URI"):
        monkeypatch.setenv(key, "bolt://127.0.0.1:7687")
    assert connections.uri("personal") == TRIAL


def test_only_connections_and_tests_name_the_switch():
    # Desktop の道具（nest-personal・nest-gate）と端末の道具は、切り替えの指定を持たない
    hits = []
    for base in ("nest", "scripts", "sos", "field-ui", "configs"):
        for p in (REPO / base).rglob("*"):
            if p.is_file() and p.suffix in (".py", ".json", ".sh", ".toml") and "NEST_DB_TARGET" in p.read_text(encoding="utf-8", errors="ignore"):
                hits.append(str(p.relative_to(REPO)))
    assert hits == ["nest/connections.py"], hits


# ---- b 空にする処理 ----

def test_clearing_the_trial_db_stops():
    d = FakeDriver(labels={"NestLiveProbe"}, nodes=1000)
    with pytest.raises(RuntimeError):
        live_testdb.clear_test_db(d, TRIAL)
    assert _writes(d) == []


def test_clearing_a_db_without_the_test_mark_stops_even_on_the_test_port():
    d = FakeDriver(labels={"NestLiveProbe"}, nodes=1000)
    with pytest.raises(RuntimeError):
        live_testdb.clear_test_db(d, TEST)
    assert _writes(d) == []


def test_clearing_with_the_test_mark_on_the_trial_port_stops():
    d = FakeDriver(labels={"NestTestDbProbe", "NestLiveProbe"})
    with pytest.raises(RuntimeError):
        live_testdb.clear_test_db(d, TRIAL)
    assert d.calls == []


def test_clearing_the_test_db_keeps_both_marks():
    d = FakeDriver(labels={"NestTestDbProbe", "NestLiveProbe"})
    live_testdb.clear_test_db(d, TEST)
    (q,) = [q for q in d.calls if "DELETE" in q]
    assert "NOT n:NestTestDbProbe" in q and "NOT n:NestLiveProbe" in q


def test_the_test_mark_is_placed_only_on_an_empty_db_on_the_test_port():
    with pytest.raises(RuntimeError):
        live_testdb.place_test_mark(FakeDriver(nodes=0), TRIAL)
    full = FakeDriver(nodes=3)
    with pytest.raises(RuntimeError):
        live_testdb.place_test_mark(full, TEST)
    assert _writes(full) == []
    empty = FakeDriver(nodes=0)
    live_testdb.place_test_mark(empty, TEST)
    (q,) = _writes(empty)
    assert "NestTestDbProbe" in q and "NestLiveProbe" in q and "DELETE" not in q


def test_the_test_mark_is_not_the_trial_mark():
    assert live_testdb.TEST_MARK == "NestTestDbProbe" != "NestLiveProbe"


# ---- e 試走の DB に向いた状態では、DB を使う試験は動かない ----

def test_live_tests_refuse_the_trial_target(monkeypatch):
    monkeypatch.delenv("NEST_DB_TARGET", raising=False)
    with pytest.raises(RuntimeError):
        live_testdb.require_test_target()
    monkeypatch.setenv("NEST_DB_TARGET", "test")
    live_testdb.require_test_target()


def test_a_live_run_aimed_at_the_trial_db_stops_before_any_test():
    # 試験を集めるだけ（--collect-only）でも、始まりで止まる。DB には触れない
    env = {k: v for k, v in os.environ.items() if k != "NEST_DB_TARGET"}
    env["NEST_LIVE_DB"] = "1"
    p = subprocess.run(["uv", "run", "--quiet", "pytest", "-q", "--collect-only", "-p", "no:cacheprovider",
                        "tests/test_relation_live.py"], cwd=REPO, env=env, capture_output=True, text=True)
    assert p.returncode != 0
    assert "試走の DB に向いている" in p.stdout + p.stderr
