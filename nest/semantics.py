"""意味の文書（docs/SEMANTICS.md）の表を読む（N-27。台帳 G-47）。列挙値と項目の日本語の表示名と、原文の確度の印。

コードに日本語名の対応表を直に書かず、ここから読む。
"""
import functools
import re
from pathlib import Path

SEMANTICS = Path(__file__).resolve().parents[1] / "docs" / "SEMANTICS.md"
ROW = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")
MARK_ROW = re.compile(r"^\|\s*(.+?)\s*\|\s*`(\w+)`\s*\|\s*$")


def _section(title):
    text = SEMANTICS.read_text(encoding="utf-8")
    start = text.index("### " + title)
    end = text.find("\n#", start + 1)
    return text[start:] if end < 0 else text[start:end]


@functools.cache
def _enum_names():
    out = {}
    for line in _section("SEM-ENUM-01").splitlines():
        m = ROW.match(line)
        if not m or not m.group(1).startswith("`"):
            continue
        enum, value, name = m.group(1).strip("`"), m.group(2).strip("`"), m.group(3)
        out.setdefault(enum, {})[value] = name
    return out


def enum_names():
    """{列挙の名前: {値: 表示名}}。"""
    return {k: dict(v) for k, v in _enum_names().items()}


@functools.cache
def _field_names():
    out = {}
    for line in _section("SEM-FIELD-01").splitlines():
        m = ROW.match(line)
        if not m or not m.group(1).startswith("`"):
            continue
        out.setdefault(m.group(1).strip("`"), {})[m.group(2).strip("`")] = m.group(3)
    return out


def field_names():
    """{ラベル: {項目: 表示名}}（SEM-FIELD-01。2026-11-11 河原さん）。"""
    return {k: dict(v) for k, v in _field_names().items()}


def certainty_marks():
    """[(印の語, 確度), …]。弱い順。"""
    return [(m.group(1), m.group(2)) for m in map(MARK_ROW.match, _section("SEM-ENUM-02").splitlines())
            if m and m.group(1) != "印"]


WORD_ROW = re.compile(r"^\|\s*(`\w+`|（続柄にしない語）)\s*\|\s*(.+?)\s*\|\s*$")
NEUTRAL = "（続柄にしない語）"


@functools.cache
def _relation_words():
    values, neutral = {}, []
    for m in map(WORD_ROW.match, _section("SEM-REC-06").splitlines()):
        if not m:
            continue
        words = [w for w in m.group(2).split("・") if w]
        if m.group(1) == NEUTRAL:
            neutral = words
        else:
            values[m.group(1).strip("`")] = words
    return values, neutral


def relation_words():
    """{続柄の値: [語, …]}（SEM-REC-06 の語の一覧。2026-11-12 河原さん。台帳 G-102）。"""
    return {k: list(v) for k, v in _relation_words()[0].items()}


def neutral_relation_words():
    """続柄の語を含むが続柄にしない語（「大丈夫」の「夫」、「母方」の「母」など）。"""
    return list(_relation_words()[1])
