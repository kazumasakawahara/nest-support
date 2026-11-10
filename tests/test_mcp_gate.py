"""書き込み受付の MCP（nest/mcp_gate.py。ADR-002 D1・D2・D6。段階 L の L-1 の最初の一つ）。DB を使わない。

scripts/submit_proposal.py の中身（仮名から本人を引く → 入口の点検 → ゲート）を MCP の道具 submit_proposal にした。
- 照会口（nest-personal）には足さず、別のプロセス（nest-gate）にする。照会口は読むだけのまま（ADR-002 D2）
- 職員の ID は道具の引数で受けない。~/.config/nest/nest-gate.env（中身は Claude に読ませない）か環境変数から読む（D2）
- 照会口と同じ歯止め（require_personal_allowed）を通す。受付に抜け道を作らない（D6）
- 通った案は未確定（Pending）でしか入らない。止まったら理由と「作り直して出し直す」を返し、何も書かない
- 道具の説明に、呼ぶ前に対象の仮名を職員に復唱して確かめることを書く（L-0 の論点 7 (b)）
"""
import inspect

import pytest

from nest import egress, mcp_guard, mcp_personal
from nest.gate import validate as gv
from nest.gate import write as gw

STAFF = "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"
CLIENT = "CLI-01BBBBBBBBBBBBBBBBBBBBBBBB"
CODE = "C-ZZZZZZ"
ORIGINAL = "架空の面談記録\n本人は、音楽を聴くと落ち着くと話した【本人の話】\nこの行は原文にだけある（架空）\n"


def _proposal(**over):
    p = {"documentKind": "OwnCaseRecord",
         "facts": [{"quote": "本人は、音楽を聴くと落ち着くと話した", "recordKind": "Interview",
                    "certainty": "SelfReport", "informantKind": "Self", "toldBy": "client"}]}
    p.update(over)
    return p


class _R(dict):
    pass


class FakeDriver:
    """仮名から clientId を引く照会と、架空の印の照会に答える"""

    def __init__(self, known=True, marked=True):
        self.known, self.marked, self.calls = known, marked, []

    def execute_query(self, query, params=None, **kw):
        self.calls.append(query)
        if "NestLiveProbe" in query:
            return [_R(marked=self.marked)], None, None
        if "displayCode" in query and self.known and (params or {}).get("code") == CODE:
            return [_R(id=CLIENT)], None, None
        return [], None, None


def _mcp():
    from nest import mcp_gate
    return mcp_gate


@pytest.fixture
def sent(monkeypatch):
    got = []

    def fake_submit(req, driver, **kw):
        got.append(req)
        return {"ok": True, "errors": [], "ids": {n["ref"]: "X" for n in req["nodes"]}}
    monkeypatch.setattr(gw, "submit", fake_submit)
    monkeypatch.setenv("NEST_GATE_STAFF_ID", STAFF)
    monkeypatch.setattr(egress, "authorize", lambda row: (_ for _ in ()).throw(egress.EgressDenied("記録が無い（試験）")))
    return got


# ---- 形 ----

def test_the_gate_server_is_separate_and_has_only_the_submit_tool():
    m = _mcp()
    assert m.server.name == "nest-gate"
    tools = [n for n, f in inspect.getmembers(m, inspect.isfunction) if f.__module__ == m.__name__ and not n.startswith("_")]
    assert sorted(tools) == ["staff_id", "submit_proposal"]


def test_the_read_only_wrapper_has_no_write_tool():
    names = [n for n, f in inspect.getmembers(mcp_personal, inspect.isfunction) if f.__module__ == mcp_personal.__name__]
    assert not [n for n in names if "submit" in n or "write" in n or "approve" in n], names


def test_the_tool_does_not_take_a_staff_id_or_a_name():
    params = set(inspect.signature(_mcp().submit_proposal).parameters)
    assert params == {"code", "original", "proposal"}


def test_the_tool_description_says_to_repeat_the_pseudonym_and_remake_on_stop():
    doc = _mcp().submit_proposal.__doc__
    assert "仮名" in doc and "復唱" in doc and "作り直" in doc and "未確定" in doc


def test_the_tool_checks_the_guard_before_anything():
    body = inspect.getsource(_mcp()._submit)
    assert body.index("require_personal_allowed") < body.index("proposal.submit")


# ---- 職員の ID ----

def test_staff_id_comes_from_the_environment_or_the_config_file(tmp_path, monkeypatch):
    m = _mcp()
    monkeypatch.delenv("NEST_GATE_STAFF_ID", raising=False)
    conf = tmp_path / "nest-gate.env"
    monkeypatch.setattr(m, "CONFIG", conf)
    with pytest.raises(RuntimeError) as e:
        m.staff_id()
    assert "nest-gate.env" in str(e.value) and "管理者" in str(e.value)
    conf.write_text("NEST_GATE_STAFF_ID=%s\n" % STAFF, encoding="utf-8")
    assert m.staff_id() == STAFF
    monkeypatch.setenv("NEST_GATE_STAFF_ID", "STF-01CCCCCCCCCCCCCCCCCCCCCCCC")
    assert m.staff_id() == "STF-01CCCCCCCCCCCCCCCCCCCCCCCC"


def test_a_malformed_staff_id_is_refused(monkeypatch):
    monkeypatch.setenv("NEST_GATE_STAFF_ID", "相談支援専門員A")
    with pytest.raises(RuntimeError) as e:
        _mcp().staff_id()
    assert "STF-" in str(e.value) and "相談支援専門員A" not in str(e.value)


# ---- 振る舞い ----

def test_a_passed_proposal_goes_in_as_pending_under_the_configured_staff(sent):
    out = _mcp()._submit(FakeDriver(), CODE, ORIGINAL, _proposal())
    assert out["ok"] and out["code"] == CODE and out["pending"] == 1 and out["counts"] == {"Record": 1}
    (req,) = sent
    assert req["actorStaffId"] == STAFF
    rep = gv.validate(req)
    assert rep["ok"] and all(n["status"] == "Pending" for n in rep["nodes"])
    assert "未確定" in out["next"]
    assert "clientId" not in out and CLIENT not in str(out)


def test_an_intake_stop_returns_the_reasons_and_writes_nothing(sent):
    bad = _proposal(facts=[{"quote": "本人は、ジャズを聴くと落ち着くと話した", "recordKind": "Interview",
                            "certainty": "SelfReport", "informantKind": "Self"}])
    out = _mcp()._submit(FakeDriver(), CODE, ORIGINAL, bad)
    assert not out["ok"] and out["stage"] == "intake" and sent == []
    assert any("原文に無い" in e for e in out["errors"])
    assert "何も書いていない" in out["next"] and "作り直" in out["next"]


def test_a_gate_stop_returns_the_reasons(sent, monkeypatch):
    monkeypatch.setattr(gw, "submit", lambda req, driver, **kw: {"ok": False, "errors": ["職員は Active でない"], "ids": {}})
    out = _mcp()._submit(FakeDriver(), CODE, ORIGINAL, _proposal())
    assert not out["ok"] and out["stage"] == "gate" and out["errors"] == ["職員は Active でない"]


def test_an_unknown_pseudonym_is_stopped(sent):
    out = _mcp()._submit(FakeDriver(known=False), CODE, ORIGINAL, _proposal())
    assert not out["ok"] and out["stage"] == "input" and sent == []
    assert any(CODE in e for e in out["errors"])


def test_a_different_client_id_in_the_proposal_is_stopped(sent):
    out = _mcp()._submit(FakeDriver(), CODE, ORIGINAL, _proposal(clientId="CLI-01CCCCCCCCCCCCCCCCCCCCCCCC"))
    assert not out["ok"] and out["stage"] == "input" and sent == []


def test_refused_without_next02_and_without_the_fictional_mark(sent):
    with pytest.raises(mcp_guard.NotReadOnly):
        _mcp()._submit(FakeDriver(marked=False), CODE, ORIGINAL, _proposal())
    assert sent == []


def test_the_script_and_the_tool_share_the_same_core():
    from doc_commands import load
    script = load("submit_proposal.py")
    assert "proposal.submit(" in inspect.getsource(script._run)
    assert not hasattr(script, "intake") and not hasattr(script, "gw")
