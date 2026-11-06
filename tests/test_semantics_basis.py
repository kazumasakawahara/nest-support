"""N-42：手帳・受給者証（certificateType）と年金・手当（publicAssistanceType）の根拠の法令と条番号（2026-11-06 河原さん）。

- SEMANTICS の SEM-ENUM-03 に、Other を除く値ごとに一行ある
- 根拠は「法令の名前（法令番号）第…条」で書き、e-Gov で照合した。照合できないものは【未照合：理由】と理由を書く
- 「まだ書いていない【未照合】」の一行は外す
"""
import re
from pathlib import Path

from nest import semantics

REPO = Path(__file__).resolve().parents[1]
TEXT = (REPO / "docs" / "SEMANTICS.md").read_text(encoding="utf-8")


def _rows():
    sec = semantics._section("SEM-ENUM-03")
    out = {}
    for line in sec.splitlines():
        m = re.match(r"^\|\s*`(\w+)`\s*\|\s*`(\w+)`\s*\|\s*(.+?)\s*\|\s*$", line)
        if m:
            out[(m.group(1), m.group(2))] = m.group(3)
    return out


def _values(enum):
    return set(semantics.enum_names()[enum]) - {"Other"}


def test_every_value_has_a_basis_row():
    have = set(_rows())
    for enum in ("certificateType", "publicAssistanceType"):
        want = {(enum, v) for v in _values(enum)}
        assert want and want <= have, want - have


def test_each_basis_cites_a_law_and_article_or_says_why_not():
    for key, basis in _rows().items():
        if "未照合" in basis:
            assert re.search(r"【未照合：.+】", basis), key
        else:
            assert re.search(r"（(昭和|平成|令和)\d+年法律第\d+号）第 ?[0-9０-９一二三四五六七八九十百条の]+", basis), (key, basis)


def test_the_old_unverified_line_is_gone():
    assert "根拠の条番号は、まだ書いていない【未照合】" not in TEXT
