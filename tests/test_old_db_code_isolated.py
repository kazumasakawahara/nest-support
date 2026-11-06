"""前の構成の残り（台帳 G-49）が無いこと。DB を使わない。

N-38（2026-11-06）で外した。前は「置き換えるまでの間、新しい DB を指さないこと」を確かめていた
（2026-11-06 河原さん：「置き換えるまでの間、どれも新しい DB（37687・38687）を指さないことを試験で固定する」）。
置き換えが済んだので、無いこと・戻っていないことを確かめる形に変えた。
"""
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REMOVED = ["lib", "installer", "setup.sh", "setup.ps1", "scripts/rotate_password.py", "scripts/multi_importer.py"]


@pytest.mark.parametrize("path", REMOVED)
def test_the_old_code_is_gone(path):
    tracked = subprocess.run(["git", "ls-files", path], cwd=REPO, capture_output=True, text=True, check=True).stdout
    assert tracked == "", path
    assert not (REPO / path).exists(), path


def test_no_code_imports_lib():
    out = subprocess.run(["git", "grep", "-n", "-E", r"^\s*(from lib(\.| )|import lib(\.|$| ))", "--", "*.py"],
                         cwd=REPO, capture_output=True, text=True).stdout
    assert out == ""


def test_the_import_path_note_no_longer_mentions_lib():
    assert "No module named 'lib'" not in (REPO / "pyproject.toml").read_text(encoding="utf-8")
