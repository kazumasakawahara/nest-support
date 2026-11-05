"""N-27（その 1）：列挙値の日本語の表示名を docs/SEMANTICS.md に置き、コードはそこから読む（台帳 G-47。2026-11-05 河原さん）。DB を使わない。

- 正典の列挙のすべての値に、SEMANTICS の表示名がある（足りない・余る値が無い）
- 原文の確度の印（【推測】など）の表も SEMANTICS にあり、入口の点検はそこから読む
- コードに日本語名の対応表を直に書かない（validate の CERTAINTY_JA・intake の WEAKEST_FIRST は SEMANTICS から作る）
"""
import inspect
from pathlib import Path

from nest import canon, semantics
from nest.gate import intake
from nest.gate import validate as gv

REPO = Path(__file__).resolve().parents[1]
C = canon.load(REPO / "docs" / "SCHEMA.md")


def test_every_canon_enum_value_has_a_japanese_name():
    names = semantics.enum_names()
    assert set(names) == set(C["enums"]), set(names) ^ set(C["enums"])
    for enum, values in C["enums"].items():
        assert set(names[enum]) == set(values), (enum, set(names[enum]) ^ set(values))
        assert all(isinstance(v, str) and v.strip() for v in names[enum].values()), enum


def test_display_names_are_unique_within_an_enum():
    for enum, table in semantics.enum_names().items():
        assert len(set(table.values())) == len(table), enum


def test_certainty_names_match_tsunagu_net():
    assert semantics.enum_names()["certainty"] == {
        "Confirmed": "確認済み", "Hearsay": "伝聞", "SelfReport": "本人の話", "Inference": "推測", "Unspecified": "確度の記載なし"}


def test_original_marks_are_read_from_semantics():
    assert semantics.certainty_marks() == [("推測", "Inference"), ("伝聞", "Hearsay"), ("未確認", "Hearsay"),
                                           ("本人の話", "SelfReport"), ("確認済み", "Confirmed")]
    assert list(intake.WEAKEST_FIRST) == semantics.certainty_marks()


def test_validate_reads_certainty_names_from_semantics():
    assert gv.CERTAINTY_JA == {v: k for k, v in semantics.enum_names()["certainty"].items()}


def test_no_japanese_name_table_written_in_code():
    for mod in (gv, intake):
        src = inspect.getsource(mod)
        assert '"確認済み": "Confirmed"' not in src and '("確認済み", "Confirmed")' not in src, mod.__name__
