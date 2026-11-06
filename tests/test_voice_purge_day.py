"""N-45：音声を消す日（2026-11-06 河原さん）。バックアップの日と同じ日（週に一度）に purge_voice を流す。

- 手順書（docs/OPERATIONS.md）の 7 の最初の枠で、DB を起こす → purge_voice（数える → 消す）→ DB を止める → バックアップ、の順
- その枠の purge_voice の行を、そのまま流す（置き場所だけ一時の場所に。DB は偽物）と、承認済みと 30 日過ぎを消し、新しいものを残す
- 6 に「週に一度・バックアップの日」が書いてあり、「決めていません」が残っていない
"""
import re
from pathlib import Path

from test_purge_voice_script import Driver, _put

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "OPERATIONS.md"
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("doc_commands", REPO / "tests" / "doc_commands.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


def _section(n):
    t = DOC.read_text(encoding="utf-8")
    start = t.index("\n## %d. " % n)
    return t[start:t.index("\n## ", start + 1)]


def _first_block(n):
    return re.search(r"```bash\n(.*?)```", _section(n), re.S).group(1)


def test_backup_block_runs_purge_voice_between_up_and_down():
    cmds = [l.split("  #")[0].strip() for l in _first_block(7).splitlines()]
    at = lambda s: next(i for i, c in enumerate(cmds) if c.endswith(s))  # noqa: E731
    assert at("up -d") < at("scripts/purge_voice.py") < at("scripts/purge_voice.py --write") < at(" down") < at("backup.py dump")


def test_backup_block_purge_lines_run_as_written(tmp_path, capsys):
    root = tmp_path / "v"
    a, old, new = _put(root, "承認", 1), _put(root, "古い", 31), _put(root, "新しい", 1)
    lines = [l for l in dc.lines("purge_voice.py") if l in _first_block(7)]
    assert len(lines) == 2
    m = dc.load("purge_voice.py")
    for line in lines:
        assert m.main(dc.argv(line, {}) + ["--root", str(root)], driver=Driver({a.name[:64]})) == 0
    assert not a.exists() and not old.exists() and new.exists()


def test_step6_names_the_day():
    s = _section(6)
    assert "週に一度" in s and "バックアップ" in s
    assert "まだ決めていません" not in s


def test_purge_day_no_longer_open():
    t = DOC.read_text(encoding="utf-8")
    assert "音声を消す日" not in t[t.index("## 道具がまだ無いこと"):]
