"""書き込み受付（nest-gate）の職員の ID の設定（台帳 G-96 (f)。2026-11-10 河原さん）。DB を使わない（職員の照会は偽の DB）。

- scripts/gate_staff.py set --staff STF-…：~/.config/nest/nest-gate.env を権限 600 で作る（置き換える）。
  形が STF-… でない・個人の側に Active の職員としていない ID は、何も書かずに止める
- check：有る・権限 600・形が正しいかを確かめる。ID そのものは出さない（中身は Claude に読ませない。ADR-002 D2）
- 手順書 4.5 (a) の行を、そのまま道具の引数にできる
"""
import os
import stat

import pytest

from tests import doc_commands

STAFF = "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"


class _R(dict):
    pass


class FakeDriver:
    def __init__(self, active=True):
        self.active = active

    def execute_query(self, query, params=None, **kw):
        if "Staff" in query and self.active and (params or {}).get("id") == STAFF:
            return [_R(id=STAFF)], None, None
        return [], None, None


@pytest.fixture
def tool(tmp_path, monkeypatch):
    mod = doc_commands.load("gate_staff.py")
    monkeypatch.setattr(mod, "CONFIG", tmp_path / "nest" / "nest-gate.env")
    return mod


def _doc(sub):
    found = [l for l in doc_commands.lines("gate_staff.py") if l.split()[4:5] == [sub]]
    assert found, "手順書に gate_staff.py %s の行が無い" % sub
    return doc_commands.argv(found[0], {"STF-…": STAFF})


def test_doc_set_line_writes_the_file_with_mode_600(tool, capsys):
    assert tool.main(_doc("set"), driver=FakeDriver()) == 0
    f = tool.CONFIG
    assert stat.S_IMODE(os.stat(f).st_mode) == 0o600
    assert f.read_text(encoding="utf-8") == "NEST_GATE_STAFF_ID=%s\n" % STAFF
    out = capsys.readouterr().out
    assert "設定した" in out and "起動し直" in out


def test_the_file_is_read_by_the_gate(tool, monkeypatch):
    from nest import mcp_gate
    tool.main(_doc("set"), driver=FakeDriver())
    monkeypatch.delenv("NEST_GATE_STAFF_ID", raising=False)
    monkeypatch.setattr(mcp_gate, "CONFIG", tool.CONFIG)
    assert mcp_gate.staff_id() == STAFF


def test_set_replaces_and_fixes_the_mode(tool):
    tool.CONFIG.parent.mkdir(parents=True)
    tool.CONFIG.write_text("NEST_GATE_STAFF_ID=STF-01CCCCCCCCCCCCCCCCCCCCCCCC\n", encoding="utf-8")
    os.chmod(tool.CONFIG, 0o644)
    assert tool.main(_doc("set"), driver=FakeDriver()) == 0
    assert stat.S_IMODE(os.stat(tool.CONFIG).st_mode) == 0o600
    assert STAFF in tool.CONFIG.read_text(encoding="utf-8")


@pytest.mark.parametrize("bad", ["相談支援専門員A", "STF-1", "CLI-01AAAAAAAAAAAAAAAAAAAAAAAA"])
def test_a_malformed_id_writes_nothing(tool, bad, capsys):
    assert tool.main(["set", "--staff", bad], driver=FakeDriver()) == 1
    assert not tool.CONFIG.exists()
    assert "止めた" in capsys.readouterr().out


def test_an_id_that_is_not_an_active_staff_writes_nothing(tool, capsys):
    assert tool.main(_doc("set"), driver=FakeDriver(active=False)) == 1
    assert not tool.CONFIG.exists()
    out = capsys.readouterr().out
    assert "止めた" in out and "Active" in out


def test_doc_check_line(tool, capsys):
    assert tool.main(_doc("check")) == 1
    assert "gate_staff.py set" in capsys.readouterr().out
    tool.main(_doc("set"), driver=FakeDriver())
    capsys.readouterr()
    assert tool.main(_doc("check")) == 0
    out = capsys.readouterr().out
    assert "設定してある" in out and STAFF not in out
    os.chmod(tool.CONFIG, 0o644)
    assert tool.main(_doc("check")) == 1
    assert "600" in capsys.readouterr().out


def test_check_refuses_a_malformed_file_without_showing_it(tool, capsys):
    tool.CONFIG.parent.mkdir(parents=True)
    tool.CONFIG.write_text("NEST_GATE_STAFF_ID=相談支援専門員A\n", encoding="utf-8")
    os.chmod(tool.CONFIG, 0o600)
    assert tool.main(_doc("check")) == 1
    assert "相談支援専門員A" not in capsys.readouterr().out
