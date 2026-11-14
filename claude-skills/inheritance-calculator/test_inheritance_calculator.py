#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inheritance_calculator.py のテスト（標準ライブラリの unittest のみ）。

実行方法（このフォルダで）:
    /usr/bin/python3 -m unittest test_inheritance_calculator -v

人物名はすべて架空（太郎・花子・A・B・C など）。
ネットワーク・ファイル書き込みは行わない。

(C) の期待値は、コードの出力を写したものではなく、民法の条文から導いた値。
各テストの直前の「導出:」コメントに根拠を書く。
"""

import contextlib
import copy
import io
import json
import sys
import unittest
from fractions import Fraction
from unittest import mock

import inheritance_calculator as ic


def _run(data):
    """入力 dict を計算して結果 dict を返す（標準エラーの警告は捨てる）。"""
    with contextlib.redirect_stderr(io.StringIO()):
        return ic.InheritanceCalculator(copy.deepcopy(data)).calculate()


def _shares(result):
    """結果から {氏名: Fraction} を作る。"""
    return {
        h["name"]: Fraction(h["inheritance_share_fraction"])
        for h in result["heirs"]
    }


def _run_cli(data):
    """main() を標準入力経由で動かし、(終了コード, 標準出力, 標準エラー) を返す。"""
    stdin = io.StringIO(json.dumps(data, ensure_ascii=False))
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch.object(sys, "argv", ["inheritance_calculator.py", "--stdin"]), \
            mock.patch.object(sys, "stdin", stdin), \
            contextlib.redirect_stdout(stdout), \
            contextlib.redirect_stderr(stderr):
        try:
            ic.main()
            code = 0
        except SystemExit as e:
            code = e.code
    return code, stdout.getvalue(), stderr.getvalue()


def _person(name, status="alive", **extra):
    p = {"name": name, "status": status, "renounced": False}
    p.update(extra)
    return p


# ===================================================================
# (A) renounced は真偽値のみ。それ以外はエラーにする
# ===================================================================

NON_BOOLEAN_VALUES = ["false", "true", 0, 1, None]


def _full_family():
    """全ての位置に人物がいる入力（renounced の差し込み先）。"""
    return {
        "deceased_name": "太郎",
        "has_simultaneous_death": False,
        "spouse": _person("花子"),
        "children": [
            _person("A"),
            _person("B", "deceased", children=[
                _person("B1"),
                _person("B2", "deceased", children=[_person("B2a")]),
            ]),
        ],
        "parents": [_person("父", generation=1)],
        "siblings": [
            _person("C", blood_relation="full"),
            _person("D", "deceased", blood_relation="full",
                    children=[_person("D1")]),
        ],
    }


# 位置の名前 → その人物の dict を取り出す関数
POSITIONS = {
    "配偶者": lambda d: d["spouse"],
    "子": lambda d: d["children"][0],
    "代襲者（孫）": lambda d: d["children"][1]["children"][0],
    "再代襲者（ひ孫）": lambda d: d["children"][1]["children"][1]["children"][0],
    "直系尊属": lambda d: d["parents"][0],
    "兄弟姉妹": lambda d: d["siblings"][0],
    "兄弟姉妹の代襲者（甥姪）": lambda d: d["siblings"][1]["children"][0],
}


class TestRenouncedMustBeBoolean(unittest.TestCase):
    """(A) renounced に真偽値でない値が入っていたら、黙って計算しない。"""

    def _assert_rejected(self, position, value):
        data = _full_family()
        POSITIONS[position](data)["renounced"] = value
        with self.assertRaises(ValueError) as ctx:
            _run(data)
        self.assertIn("renounced", str(ctx.exception))

    def test_spouse(self):
        for value in NON_BOOLEAN_VALUES:
            with self.subTest(value=value):
                self._assert_rejected("配偶者", value)

    def test_child(self):
        for value in NON_BOOLEAN_VALUES:
            with self.subTest(value=value):
                self._assert_rejected("子", value)

    def test_substitute_grandchild(self):
        for value in NON_BOOLEAN_VALUES:
            with self.subTest(value=value):
                self._assert_rejected("代襲者（孫）", value)

    def test_substitute_great_grandchild(self):
        for value in NON_BOOLEAN_VALUES:
            with self.subTest(value=value):
                self._assert_rejected("再代襲者（ひ孫）", value)

    def test_parent(self):
        for value in NON_BOOLEAN_VALUES:
            with self.subTest(value=value):
                self._assert_rejected("直系尊属", value)

    def test_sibling(self):
        for value in NON_BOOLEAN_VALUES:
            with self.subTest(value=value):
                self._assert_rejected("兄弟姉妹", value)

    def test_nephew(self):
        for value in NON_BOOLEAN_VALUES:
            with self.subTest(value=value):
                self._assert_rejected("兄弟姉妹の代襲者（甥姪）", value)

    def test_string_false_does_not_silently_promote_next_rank(self):
        """調査で見つかった事象そのもの: "false" の子が外れて父母が繰り上がってはならない。"""
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "children": [{"name": "A", "status": "alive", "renounced": "false"}],
            "parents": [_person("父", generation=1)],
        }
        with self.assertRaises(ValueError):
            _run(data)

    def test_cli_reports_error_and_prints_no_result(self):
        """CLI でも終了コード 1、標準出力に結果を出さない。"""
        data = _full_family()
        data["children"][0]["renounced"] = "false"
        code, out, err = _run_cli(data)
        self.assertEqual(code, 1)
        self.assertEqual(out.strip(), "")
        self.assertIn("renounced", err)


class TestRenouncedBooleanStillAccepted(unittest.TestCase):
    """真偽値と省略は従来どおり受け付ける（(A) の修正で壊さないことの確認）。"""

    def test_true_false_and_omitted_are_accepted(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": {"name": "花子", "status": "alive"},  # renounced 省略
            "children": [
                {"name": "A", "status": "alive", "renounced": False},
                {"name": "B", "status": "alive", "renounced": True},
            ],
        }
        # 導出: Bは放棄で初めから相続人でない（939条）。配偶者1/2・子1/2（900条1号）、子はAのみ。
        self.assertEqual(
            _shares(_run(data)),
            {"花子": Fraction(1, 2), "A": Fraction(1, 2)},
        )


# ===================================================================
# (B) status: unknown の人物がいる事実が、結果の JSON に出る
# ===================================================================

class TestUnknownStatusSurfacedInResult(unittest.TestCase):

    def _input_with_unknown_child(self):
        return {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "children": [_person("A", "unknown")],
            "parents": [_person("父", generation=1)],
        }

    def test_unknown_child_is_listed_and_result_is_provisional(self):
        result = _run(self._input_with_unknown_child())
        self.assertIs(result["is_provisional"], True)
        self.assertEqual(
            result["unknown_status_persons"],
            [{"role": "子", "name": "A"}],
        )

    def test_unknown_visible_on_stdout_alone(self):
        """標準出力の JSON だけで、誰が不明か・結果が確定でないことが分かる。"""
        code, out, _err = _run_cli(self._input_with_unknown_child())
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertIs(result["is_provisional"], True)
        self.assertIn("A", [p["name"] for p in result["unknown_status_persons"]])

    def test_unknown_in_every_position_is_listed(self):
        data = _full_family()
        for getter in POSITIONS.values():
            getter(data)["status"] = "unknown"
        result = _run(data)
        self.assertIs(result["is_provisional"], True)
        self.assertEqual(
            sorted(p["name"] for p in result["unknown_status_persons"]),
            sorted(["花子", "A", "B1", "B2a", "父", "C", "D1"]),
        )

    def test_omitted_status_is_listed_too(self):
        """status の省略は既存コードで unknown と同じ扱い（相続判定から除外）なので、同じく出す。"""
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "children": [{"name": "A"}, _person("B")],
        }
        result = _run(data)
        self.assertIs(result["is_provisional"], True)
        self.assertEqual(
            result["unknown_status_persons"],
            [{"role": "子", "name": "A"}],
        )

    def test_unknown_listed_even_when_no_heirs(self):
        """相続人なしの結果（国庫帰属の案内）にも出る。不明者がいるのに「相続人なし」と読ませない。"""
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "children": [_person("A", "unknown")],
        }
        result = _run(data)
        self.assertIs(result["has_legal_heirs"], False)
        self.assertIs(result["is_provisional"], True)
        self.assertEqual(
            result["unknown_status_persons"],
            [{"role": "子", "name": "A"}],
        )

    def test_no_unknown_means_not_provisional(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "children": [_person("A")],
        }
        result = _run(data)
        self.assertIs(result["is_provisional"], False)
        self.assertEqual(result["unknown_status_persons"], [])


# ===================================================================
# (C) 既存の正しい挙動（期待値は条文から導出）
# ===================================================================

class TestBasicStatutoryShares(unittest.TestCase):

    def test_spouse_and_two_children(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "children": [_person("A"), _person("B")],
            "parents": [_person("父", generation=1)],
            "siblings": [_person("C", blood_relation="full")],
        }
        # 導出: 子がいれば尊属・兄弟姉妹は相続人でない（889条1項）。配偶者1/2・子1/2（900条1号）、子は均等（900条4号本文）→ 各1/4。
        self.assertEqual(
            _shares(_run(data)),
            {"花子": Fraction(1, 2), "A": Fraction(1, 4), "B": Fraction(1, 4)},
        )

    def test_spouse_and_both_parents(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "parents": [_person("父", generation=1), _person("母", generation=1)],
            "siblings": [_person("C", blood_relation="full")],
        }
        # 導出: 子なし→直系尊属（889条1項1号）。配偶者2/3・尊属1/3（900条2号）、父母は均等（900条4号本文）→ 各1/6。
        self.assertEqual(
            _shares(_run(data)),
            {"花子": Fraction(2, 3), "父": Fraction(1, 6), "母": Fraction(1, 6)},
        )

    def test_nearer_ascendant_excludes_farther(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "parents": [
                _person("父", "deceased", generation=1),
                _person("母", generation=1),
                _person("祖父", generation=2),
            ],
        }
        # 導出: 親等の異なる尊属では近い者が先（889条1項1号但書）→ 母のみ。配偶者2/3・母1/3（900条2号）。
        self.assertEqual(
            _shares(_run(data)),
            {"花子": Fraction(2, 3), "母": Fraction(1, 3)},
        )

    def test_spouse_and_two_full_siblings(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "parents": [_person("父", "deceased", generation=1)],
            "siblings": [
                _person("C", blood_relation="full"),
                _person("D", blood_relation="full"),
            ],
        }
        # 導出: 子・尊属なし→兄弟姉妹（889条1項2号）。配偶者3/4・兄弟姉妹1/4（900条3号）、均等（900条4号本文）→ 各1/8。
        self.assertEqual(
            _shares(_run(data)),
            {"花子": Fraction(3, 4), "C": Fraction(1, 8), "D": Fraction(1, 8)},
        )

    def test_half_blood_sibling_gets_half_of_full_blood(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "siblings": [
                _person("C", blood_relation="full"),
                _person("D", blood_relation="half"),
            ],
        }
        # 導出: 兄弟姉妹全体1/4（900条3号）。半血は全血の1/2（900条4号但書）→ 2:1 で按分、C=1/4×2/3=1/6、D=1/4×1/3=1/12。
        self.assertEqual(
            _shares(_run(data)),
            {"花子": Fraction(3, 4), "C": Fraction(1, 6), "D": Fraction(1, 12)},
        )

    def test_children_only_no_spouse(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "children": [_person("A"), _person("B"), _person("C")],
        }
        # 導出: 配偶者なし→子のみで全部（887条1項）。均等（900条4号本文）→ 各1/3。
        self.assertEqual(
            _shares(_run(data)),
            {"A": Fraction(1, 3), "B": Fraction(1, 3), "C": Fraction(1, 3)},
        )


class TestSubstitution(unittest.TestCase):

    def test_grandchildren_substitute_for_predeceased_child(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "children": [
                _person("A"),
                _person("B", "deceased", children=[_person("B1"), _person("B2")]),
            ],
        }
        # 導出: 配偶者1/2、子全体1/2を A・B の2株で各1/4（900条1号・4号）。Bは先に死亡→孫が代襲（887条2項）し、Bの分1/4を均等（901条1項）→ 各1/8。
        result = _run(data)
        self.assertEqual(
            _shares(result),
            {
                "花子": Fraction(1, 2),
                "A": Fraction(1, 4),
                "B1": Fraction(1, 8),
                "B2": Fraction(1, 8),
            },
        )
        by_name = {h["name"]: h for h in result["heirs"]}
        self.assertIs(by_name["B1"]["is_substitute"], True)
        self.assertEqual(by_name["B1"]["original_heir"], "B")
        self.assertIs(by_name["A"]["is_substitute"], False)

    def test_great_grandchild_re_substitutes(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "children": [
                _person("A"),
                _person("B", "deceased", children=[
                    _person("B1", "deceased", children=[_person("B1a")]),
                ]),
            ],
        }
        # 導出: 子 A・B の2株で各1/2（900条4号）。B も代襲者 B1 も先に死亡→ひ孫が再代襲（887条3項）し、Bの分1/2をそのまま受ける（901条1項）。
        self.assertEqual(
            _shares(_run(data)),
            {"A": Fraction(1, 2), "B1a": Fraction(1, 2)},
        )

    def test_child_of_renouncing_child_does_not_substitute(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "children": [
                _person("A"),
                {"name": "B", "status": "alive", "renounced": True,
                 "children": [_person("B1")]},
            ],
        }
        # 導出: 放棄者は初めから相続人でない（939条）。代襲原因は死亡・欠格・廃除のみで放棄を含まない（887条2項）→ B1は相続しない。子はAのみ: 配偶者1/2・A 1/2（900条1号）。
        self.assertEqual(
            _shares(_run(data)),
            {"花子": Fraction(1, 2), "A": Fraction(1, 2)},
        )

    def test_only_child_renounces_then_parents_inherit(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "children": [
                {"name": "A", "status": "alive", "renounced": True,
                 "children": [_person("A1")]},
            ],
            "parents": [_person("母", generation=1)],
        }
        # 導出: 唯一の子が放棄（939条）、孫は代襲しない（887条2項）→ 第1順位なし→直系尊属（889条1項1号）。配偶者2/3・母1/3（900条2号）。
        self.assertEqual(
            _shares(_run(data)),
            {"花子": Fraction(2, 3), "母": Fraction(1, 3)},
        )

    def test_nephews_substitute_for_predeceased_sibling(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "siblings": [
                _person("C", blood_relation="full"),
                _person("D", "deceased", blood_relation="full",
                        children=[_person("D1"), _person("D2")]),
            ],
        }
        # 導出: 配偶者3/4、兄弟姉妹全体1/4を C・D の2株で各1/8（900条3号・4号）。Dは先に死亡→甥姪が代襲（889条2項・887条2項）、Dの分1/8を均等（901条2項・1項）→ 各1/16。
        self.assertEqual(
            _shares(_run(data)),
            {
                "花子": Fraction(3, 4),
                "C": Fraction(1, 8),
                "D1": Fraction(1, 16),
                "D2": Fraction(1, 16),
            },
        )

    def test_no_re_substitution_for_siblings(self):
        data = {
            "deceased_name": "太郎",
            "has_simultaneous_death": False,
            "spouse": _person("花子"),
            "siblings": [
                _person("C", blood_relation="full"),
                _person("D", "deceased", blood_relation="full", children=[
                    _person("D1", "deceased", children=[_person("D1a")]),
                ]),
            ],
        }
        # 導出: 889条2項が準用するのは887条2項のみで3項（再代襲）は準用しない→甥姪の子 D1a は相続しない。兄弟姉妹はCのみ: 配偶者3/4・C 1/4（900条3号）。
        self.assertEqual(
            _shares(_run(data)),
            {"花子": Fraction(3, 4), "C": Fraction(1, 4)},
        )


if __name__ == "__main__":
    unittest.main()
