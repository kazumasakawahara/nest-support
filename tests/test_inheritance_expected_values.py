#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inheritance_calculator.py の結果を、条文から手で導いた期待値の表と照らす（unittest で書いてあり、pytest でも走る）。

表は tests/inheritance_expected_cases.json。各件の expected は、スクリプトを動かして得た値ではなく、
民法 887条・889条・890条・900条・901条・939条から手で計算した値（式は各件の basis）。
「相続分の合計が 1」のような不変条件だけでは見つからない誤り（順位の入替え、半血の扱い、
親等の近い尊属の優先、代襲の株分け）を、相続人の集合と各相続分の完全一致で見つける。

実行方法（リポジトリの直下で）:
    uv run pytest tests/test_inheritance_expected_values.py
    /usr/bin/python3 -m unittest tests/test_inheritance_expected_values.py   （pytest 無しでも可）

人物名はすべて架空（甲・乙・子A など）。ネットワーク・ファイル書き込みは行わない。

期待値とスクリプトの結果が食い違ったら、どちらも直す前に条文を読み直す。
"""

import contextlib
import copy
import importlib.util
import io
import json
import unittest
from fractions import Fraction
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_MODULE_PATH = (
    _TESTS_DIR.parent
    / "claude-skills"
    / "inheritance-calculator"
    / "inheritance_calculator.py"
)
_CASES_PATH = _TESTS_DIR / "inheritance_expected_cases.json"

_spec = importlib.util.spec_from_file_location("inheritance_calculator", _MODULE_PATH)
ic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ic)

with open(str(_CASES_PATH), encoding="utf-8") as _f:
    _TABLE = json.load(_f)
_CASES = _TABLE["cases"]


def _run(data):
    """入力 dict を計算して結果 dict を返す（標準エラーの警告は捨てる）。"""
    with contextlib.redirect_stderr(io.StringIO()):
        return ic.InheritanceCalculator(copy.deepcopy(data)).calculate()


class TestExpectedTableIsWellFormed(unittest.TestCase):
    """表そのものの形（計算の前提）。"""

    def test_has_fictional_mark(self):
        note = _TABLE.get("_fictional")
        self.assertTrue(isinstance(note, str) and note.strip())

    def test_ids_are_unique(self):
        ids = [c["id"] for c in _CASES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_case_has_all_fields(self):
        for case in _CASES:
            with self.subTest(id=case.get("id")):
                for key in ("id", "description", "input", "expected", "basis"):
                    self.assertTrue(case.get(key), "%s が空" % key)

    def test_expected_shares_sum_to_one(self):
        """手計算の検算: 各件の期待値の合計は 1。"""
        for case in _CASES:
            with self.subTest(id=case["id"]):
                total = sum(
                    (Fraction(v) for v in case["expected"].values()), Fraction(0)
                )
                self.assertEqual(total, Fraction(1))


class TestExpectedValues(unittest.TestCase):
    """表の 1 件につきテストを 1 つ作る（下の _add_case_tests）。落ちたテストの名前で id が分かる。"""

    maxDiff = None

    def _check(self, case):
        result = _run(case["input"])
        names = [h["name"] for h in result["heirs"]]
        self.assertEqual(
            len(names), len(set(names)),
            "%s: 同じ相続人が二度出ている: %s" % (case["id"], names),
        )
        actual = {
            h["name"]: Fraction(h["inheritance_share_fraction"])
            for h in result["heirs"]
        }
        expected = {
            name: Fraction(share) for name, share in case["expected"].items()
        }
        self.assertEqual(
            set(actual), set(expected),
            "%s: 相続人の集合が違う（%s）" % (case["id"], case["description"]),
        )
        self.assertEqual(
            actual, expected,
            "%s: 相続分が違う（%s）根拠: %s"
            % (case["id"], case["description"], case["basis"]),
        )


def _add_case_tests():
    for case in _CASES:
        def test(self, case=case):
            self._check(case)
        test.__doc__ = "%s: %s" % (case["id"], case["description"])
        setattr(TestExpectedValues, "test_%s" % case["id"], test)


_add_case_tests()


if __name__ == "__main__":
    unittest.main()
