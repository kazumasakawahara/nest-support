"""個人の側の読み取りの包み（2026-11-06 河原さんの判断。台帳 G-54 (3)・G-42）。DB を使わない。

- G-54 (3)：NEXT-02 の歯止め（機能の設定と契約の確認の記録）を求める。そろわないときは、つないでいる DB に
  架空の印（G-51 の NestLiveProbe）があるときだけ動き、無ければ拒否する
- G-42 (1)：text（原文全体）は返さない。quote は求められたときだけ（専用の道具）、長さの上限つきで返す
- G-42 (2)：包みには名前を受け取る道具を作らない（名前と仮名の対応を Claude の側に残さない）
"""
import inspect

import pytest

from nest import egress, mcp_guard, mcp_personal


class _Record(dict):
    pass


class FakeDriver:
    """mark の有無を返す。execute_query だけを使う。"""

    def __init__(self, marked):
        self.marked, self.calls = marked, []

    def execute_query(self, query, parameters=None, **kw):
        self.calls.append(query)
        return [_Record(marked=self.marked)], None, None


def _deny(row):
    raise egress.EgressDenied("記録が無い（試験）")


def test_refused_without_next02_and_without_the_fictional_mark(monkeypatch):
    monkeypatch.setattr(egress, "authorize", _deny)
    with pytest.raises(mcp_guard.NotReadOnly) as e:
        mcp_guard.require_personal_allowed(FakeDriver(marked=False))
    assert "NEXT-02" in str(e.value) and "架空" in str(e.value)


def test_runs_on_a_fictional_db_without_next02(monkeypatch):
    monkeypatch.setattr(egress, "authorize", _deny)
    d = FakeDriver(marked=True)
    mcp_guard.require_personal_allowed(d)
    assert any("NestLiveProbe" in q for q in d.calls)


def test_runs_with_next02_without_looking_for_the_mark(monkeypatch):
    seen = []
    monkeypatch.setattr(egress, "authorize", lambda row: seen.append(row))
    d = FakeDriver(marked=False)
    mcp_guard.require_personal_allowed(d)
    assert seen == ["NEXT-02"] and d.calls == []


def test_every_personal_tool_checks_before_reading():
    src = inspect.getsource(mcp_personal)
    for name in ("read_personal_cypher", "read_quote"):
        body = inspect.getsource(getattr(mcp_personal, name))
        assert "require_personal_allowed" in body, name
    assert src.count("require_personal_allowed") >= 2


@pytest.mark.parametrize("query", [
    "MATCH (r:Record) RETURN r.text",
    "MATCH (r:Record) RETURN r.quote",
    "MATCH (r:Record) RETURN r { .quote }",
    "MATCH (r:Record) RETURN r.`text`",
    "MATCH (r:Record) RETURN [x IN collect(r.quote) | x] AS qs",
])
def test_free_cypher_does_not_read_text_or_quote(query):
    class D:
        calls = []

        def execute_query(self, *a, **k):
            self.calls.append(a)
            raise AssertionError("EXPLAIN まで行かない")
    with pytest.raises(mcp_guard.NotReadOnly):
        mcp_guard.check_read_only(D(), query, {}, personal=True)


def test_text_and_quote_are_dropped_from_returned_nodes():
    class N(dict):
        labels = frozenset(["Record"])
    node = N({"recordId": "REC-1", "text": "原文（架空）", "quote": "引用（架空）", "certainty": "Hearsay"})
    assert mcp_guard.to_plain(node, personal=True) == {"_labels": ["Record"], "recordId": "REC-1", "certainty": "Hearsay"}


def test_quote_is_capped():
    long = "あ" * (mcp_guard.QUOTE_MAX + 50)
    out = mcp_guard.cap_quote(long)
    assert out == {"quote": "あ" * mcp_guard.QUOTE_MAX, "truncated": True}
    assert mcp_guard.cap_quote("短い（架空）") == {"quote": "短い（架空）", "truncated": False}


def test_no_tool_takes_a_name():
    for name, fn in inspect.getmembers(mcp_personal, inspect.isfunction):
        if fn.__module__ != mcp_personal.__name__:
            continue
        params = set(inspect.signature(fn).parameters)
        assert not params & {"name", "familyName", "givenName", "clientName", "realName"}, name
