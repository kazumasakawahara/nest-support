"""N-46 詰まり #8（2026-11-09 河原さん）：段 4.5 (a) は Claude Desktop の設定の JSON を手で編集させていた。
専門職には無理で、間違えても Desktop は何も言わない。道具 scripts/desktop_config.py で、既存の設定を壊さずに足す・
足したか確かめる・パス（このフォルダと uv）を自動で埋める。試験は一時の場所の設定だけを使う（本物の設定に触れない）。
"""
import json
from pathlib import Path

import pytest

from tests import doc_commands
from tests.test_doctor import _run as run_doctor

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def uv(tmp_path):
    f = tmp_path / "bin" / "uv"  # 偽の uv（在るファイル）
    f.parent.mkdir()
    f.write_text("", encoding="utf-8")
    return str(f)


@pytest.fixture
def tool(monkeypatch, uv):
    mod = doc_commands.load("desktop_config.py")
    monkeypatch.setattr(mod, "which", lambda name: uv if name == "uv" else None)
    return mod


def _doc(sub):
    found = [l for l in doc_commands.lines("desktop_config.py") if l.split()[4:5] == [sub]]
    assert found, "手順書に desktop_config.py %s の行が無い" % sub
    return doc_commands.argv(found[0], {})


def _section_a():
    t = (REPO / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    i = t.index("### (a)")
    return t[i:t.index("\n### ", i + 1)]


def test_doc_add_line_creates_the_config_when_absent(tool, tmp_path, uv):
    cfg = tmp_path / "Claude" / "claude_desktop_config.json"
    assert tool.main(_doc("add"), path=cfg) == 0
    servers = json.loads(cfg.read_text(encoding="utf-8"))["mcpServers"]
    for name, module in (("nest-personal", "nest.mcp_personal"), ("nest-resource", "nest.mcp_resource")):
        assert servers[name]["command"] == uv
        args = servers[name]["args"]
        assert args[args.index("--directory") + 1] == str(REPO)
        assert args[-1] == module


def test_add_keeps_other_tools_and_keys(tool, tmp_path):
    cfg = tmp_path / "claude_desktop_config.json"
    other = {"command": "npx", "args": ["other-tool"]}
    cfg.write_text(json.dumps({"mcpServers": {"other": other}, "globalShortcut": "Cmd+K"}), encoding="utf-8")
    assert tool.main(_doc("add"), path=cfg) == 0
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["mcpServers"]["other"] == other and data["globalShortcut"] == "Cmd+K"
    assert {"nest-personal", "nest-resource"} <= set(data["mcpServers"])


def test_add_replaces_an_unfilled_copy_and_is_repeatable(tool, tmp_path):
    cfg = tmp_path / "claude_desktop_config.json"
    cfg.write_text((REPO / "configs" / "claude_desktop_config.json").read_text(encoding="utf-8")
                   .replace("/Users/k-kawahara/Dev-Work/project/nest-support", "<nest-support のフォルダ>"), encoding="utf-8")
    assert tool.main(_doc("add"), path=cfg) == 0
    first = cfg.read_text(encoding="utf-8")
    assert "<nest-support のフォルダ>" not in first
    assert tool.main(_doc("add"), path=cfg) == 0
    assert cfg.read_text(encoding="utf-8") == first


def test_add_stops_on_broken_json_without_writing(tool, tmp_path, capsys):
    cfg = tmp_path / "claude_desktop_config.json"
    cfg.write_text('{"mcpServers": {', encoding="utf-8")
    assert tool.main(_doc("add"), path=cfg) == 1
    assert cfg.read_text(encoding="utf-8") == '{"mcpServers": {'
    assert "止めた" in capsys.readouterr().out


def test_add_stops_when_uv_is_not_found(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "which", lambda name: None)
    cfg = tmp_path / "claude_desktop_config.json"
    assert tool.main(_doc("add"), path=cfg) == 1
    assert not cfg.exists()


def test_add_keeps_a_copy_of_the_previous_config(tool, tmp_path):
    cfg = tmp_path / "claude_desktop_config.json"
    cfg.write_text('{"mcpServers": {}}', encoding="utf-8")
    assert tool.main(_doc("add"), path=cfg) == 0
    assert (tmp_path / "claude_desktop_config.json.bak").read_text(encoding="utf-8") == '{"mcpServers": {}}'


def test_doc_check_line_fails_before_add_and_passes_after(tool, tmp_path, capsys):
    cfg = tmp_path / "claude_desktop_config.json"
    assert tool.main(_doc("check"), path=cfg) == 1
    cfg.write_text('{"mcpServers": {"nest-personal": {"command": "uv", "args": ["--directory", "<nest-support のフォルダ>"]}}}',
                   encoding="utf-8")
    assert tool.main(_doc("check"), path=cfg) == 1
    out = capsys.readouterr().out
    assert "desktop_config.py add" in out
    assert tool.main(_doc("add"), path=cfg) == 0
    assert tool.main(_doc("check"), path=cfg) == 0


def test_section_4_5_a_uses_the_tool_not_hand_editing():
    s = _section_a()
    assert "desktop_config.py add" in s and "desktop_config.py check" in s
    assert "<nest-support のフォルダ>" not in s
    assert "書き換え" not in s


def test_doctor_10_points_to_the_tool(tmp_path):
    out = run_doctor(tmp_path, [])
    line = [l for l in out.stdout.splitlines() if "INFO" in l and "Desktop の設定" in l]
    assert line and "desktop_config.py add" in line[0], out.stdout
