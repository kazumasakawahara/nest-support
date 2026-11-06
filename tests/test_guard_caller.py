"""止まる点 H-1 の判断 2（2026-11-06 河原さん。台帳 G-85）：読み取りの包みに呼び出し元を持たせる。

- NEXT-02 の歯止め（機能の設定と記録、または架空の印）は Claude へ送る経路（MCP の包み）のため。MCP からは今までどおり通す
- field-ui と SOS（外に送らない画面）からは歯止めを通さず、伏せ字（実名・かな・電話・住所・生年月日を返さない）だけを当てる
- 知らない呼び出し元は拒否する（閉じる側）
- SOS の LINE への送信は NEXT-05 の歯止めのまま
DB を使う確かめ（画面の経路でも実名が返らない）は tests/test_guard_caller_live.py。
"""
import contextlib
import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

from nest import connections, egress, mcp_guard, mcp_personal

REPO = Path(__file__).resolve().parents[1]


class _Record(dict):
    pass


class FakeDriver:
    def __init__(self, marked=False):
        self.marked, self.calls = marked, []

    def execute_query(self, query, parameters=None, **kw):
        self.calls.append(query)
        return [_Record(marked=self.marked)], None, None

    def session(self, **kw):
        raise AssertionError("問い合わせの点検より前に DB を読んだ")


@pytest.fixture
def no_record(monkeypatch):
    seen = []

    def _deny(row):
        seen.append(row)
        raise egress.EgressDenied("記録が無い（試験）")
    monkeypatch.setattr(egress, "authorize", _deny)
    return seen


def test_mcp_path_is_refused_without_a_record(no_record):
    with pytest.raises(mcp_guard.NotReadOnly):
        mcp_guard.require_personal_allowed(FakeDriver(marked=False), caller="mcp")
    assert no_record == ["NEXT-02"]


def test_default_caller_is_the_mcp_path(no_record):
    with pytest.raises(mcp_guard.NotReadOnly):
        mcp_guard.require_personal_allowed(FakeDriver(marked=False))


def test_screen_path_reads_without_a_record(no_record):
    d = FakeDriver(marked=False)
    mcp_guard.require_personal_allowed(d, caller="screen")
    assert no_record == [] and d.calls == []


def test_unknown_caller_is_refused(no_record):
    with pytest.raises(mcp_guard.NotReadOnly):
        mcp_guard.require_personal_allowed(FakeDriver(marked=True), caller="other")


def test_screen_path_still_refuses_to_ask_for_real_names(no_record):
    d = FakeDriver(marked=False)
    mcp_guard.require_personal_allowed(d, caller="screen")
    with pytest.raises(mcp_guard.NotReadOnly):
        mcp_guard.run_read(d, "MATCH (c:Client) RETURN c.familyName AS f", {}, personal=True)


def test_mcp_tools_use_the_mcp_path():
    for name in ("read_personal_cypher", "read_quote"):
        body = inspect.getsource(getattr(mcp_personal, name))
        assert "require_personal_allowed(d)" in body or 'caller="mcp"' in body, name
        assert 'caller="screen"' not in body, name


def _field_ui():
    sys.path.insert(0, str(REPO / "field-ui"))
    spec = importlib.util.spec_from_file_location("field_ui_server_caller", REPO / "field-ui" / "server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _capture(monkeypatch):
    seen = {}

    @contextlib.contextmanager
    def _driver(side):
        yield "fake-driver"
    monkeypatch.setattr(connections, "driver", _driver)
    monkeypatch.setattr(mcp_guard, "require_personal_allowed", lambda d, caller="mcp": seen.setdefault("caller", caller))
    monkeypatch.setattr(mcp_guard, "run_read", lambda d, q, p, personal: seen.update(personal=personal) or [{"n": 1}])
    return seen


def test_field_ui_reads_on_the_screen_path(monkeypatch):
    seen = _capture(monkeypatch)
    _field_ui().read_personal("MATCH (c:Client) RETURN count(c) AS n")
    assert seen == {"caller": "screen", "personal": True}


def test_sos_reads_on_the_screen_path(monkeypatch):
    sys.path.insert(0, str(REPO / "sos"))
    import api_server as sos
    seen = _capture(monkeypatch)
    sos.lookup_client("C-ZZZZZZ")
    assert seen == {"caller": "screen", "personal": True}


def test_sos_line_send_keeps_next05():
    text = (REPO / "sos" / "api_server.py").read_text(encoding="utf-8")
    assert 'egress.ensure("NEXT-05", url)' in text
