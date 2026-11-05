"""N-08: 乖離の検査（正典の表と machine-check JSON の突き合わせ）の試験。

本物の正典 docs/SCHEMA.md を読み、表か JSON の一方だけを書き換えた写しで失敗することを確かめる。
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "docs" / "SCHEMA.md"
SCRIPT = ROOT / "scripts" / "check_drift.py"

sys.path.insert(0, str(ROOT / "scripts"))
import check_drift  # noqa: E402


def _variant(tmp_path, old, new):
    text = SCHEMA.read_text(encoding="utf-8")
    assert text.count(old) == 1, old
    p = tmp_path / "SCHEMA.md"
    p.write_text(text.replace(old, new), encoding="utf-8")
    return p


def test_repository_canon_has_no_drift():
    assert check_drift.check(SCHEMA) == []


# --- 表だけを変えた写し ---

def test_table_property_missing_in_json(tmp_path):
    p = _variant(tmp_path, "| `Wish` | `wishId`✅, `content`✅ |", "| `Wish` | `wishId`✅, `content`✅, `voice` |")
    assert any("Wish" in d for d in check_drift.check(p))


def test_required_mark_differs(tmp_path):
    p = _variant(tmp_path, "| `Wish` | `wishId`✅, `content`✅ |", "| `Wish` | `wishId`✅, `content` |")
    assert any("Wish" in d for d in check_drift.check(p))


def test_label_missing_in_table(tmp_path):
    p = _variant(tmp_path, "| `Wish` | `wishId`✅, `content`✅ | 本人・家族の願い |\n", "")
    assert any("Wish" in d for d in check_drift.check(p))


def test_relationship_end_differs(tmp_path):
    p = _variant(tmp_path, "| `HAS_WISH` | Client → Wish | — |", "| `HAS_WISH` | Person → Wish | — |")
    assert any("HAS_WISH" in d for d in check_drift.check(p))


def test_relationship_property_differs(tmp_path):
    p = _variant(tmp_path, "| `PERFORMS` | Person → CareRole | `since`(Date), `until`(Date) |", "| `PERFORMS` | Person → CareRole | `since`✅(Date), `until`(Date) |")
    assert any("PERFORMS" in d for d in check_drift.check(p))


def test_enum_value_differs(tmp_path):
    p = _variant(tmp_path, "| `linkedBy` | `Gate`, `Human` |", "| `linkedBy` | `Gate`, `Human`, `Machine` |")
    assert any("linkedBy" in d for d in check_drift.check(p))


def test_enum_missing_in_table(tmp_path):
    p = _variant(tmp_path, "| `linkedBy` | `Gate`, `Human` |\n", "")
    assert any("linkedBy" in d for d in check_drift.check(p))


def test_id_prefix_regex_differs(tmp_path):
    p = _variant(tmp_path, "^(CLI|PER|STF|", "^(CLI|PRS|STF|")
    assert any("接頭辞" in d for d in check_drift.check(p))


# --- JSON だけを変えた写し ---

def test_json_enum_value_differs(tmp_path):
    p = _variant(tmp_path, '"linkedBy": ["Gate", "Human"],', '"linkedBy": ["Gate"],')
    assert any("linkedBy" in d for d in check_drift.check(p))


def test_json_relationship_missing(tmp_path):
    p = _variant(tmp_path, '      "HAS_WISH":            {"from": ["Client"], "to": ["Wish"], "required": [], "optional": []},\n', "")
    assert any("HAS_WISH" in d for d in check_drift.check(p))


# --- 検査対象が見つからないときは失敗（未検査を合格にしない） ---

def test_missing_section_fails(tmp_path):
    p = _variant(tmp_path, "### 4.5 列挙値", "### 4.9 列挙値")
    assert check_drift.check(p) != []


def test_broken_canon_fails(tmp_path):
    p = _variant(tmp_path, '"version": "0.3",', '"version": "0.3"')
    assert check_drift.check(p) != []


# --- コマンド ---

@pytest.mark.parametrize("variant, code", [(False, 0), (True, 1)])
def test_command_exit_code(tmp_path, variant, code):
    path = _variant(tmp_path, "| `linkedBy` | `Gate`, `Human` |", "| `linkedBy` | `Gate` |") if variant else SCHEMA
    r = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
    assert r.returncode == code, r.stdout + r.stderr
