"""
P0-9: 相続計算の Critical バグ（半血按分・再代襲株分け）の回帰テスト。

民法に基づく正しい法定相続分を検証する。fractions.Fraction ベースで
「相続分合計 = 1」を保証すること。
"""

import importlib.util
from fractions import Fraction
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "claude-skills"
    / "inheritance-calculator"
    / "inheritance_calculator.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("inheritance_calculator", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MOD = _load()


def _shares(input_data):
    """計算結果を {氏名: Fraction(相続分)} に変換して返す。"""
    calc = _MOD.InheritanceCalculator(input_data)
    result = calc.calculate()
    out = {}
    for h in result.get("heirs", []):
        frac = h["inheritance_share_fraction"]
        if "/" in frac:
            n, d = frac.split("/")
            out[h["name"]] = Fraction(int(n), int(d))
        else:
            out[h["name"]] = Fraction(int(frac))
    return out, result


def _assert_sum_one(shares):
    assert sum(shares.values()) == Fraction(1), f"合計が1でない: {shares}"


# ---------------------------------------------------------------------------
# P0-9 バグ1: 半血兄弟姉妹（民法900条4号但書: 半血は全血の1/2）
# ---------------------------------------------------------------------------

def test_half_blood_sibling_split():
    """全血1 + 半血1 → 全血 2/3・半血 1/3。"""
    data = {
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "siblings": [
            {"name": "全血兄", "status": "alive", "blood_relation": "full"},
            {"name": "半血弟", "status": "alive", "blood_relation": "half"},
        ],
    }
    shares, _ = _shares(data)
    assert shares["全血兄"] == Fraction(2, 3)
    assert shares["半血弟"] == Fraction(1, 3)
    _assert_sum_one(shares)


# ---------------------------------------------------------------------------
# P0-9 バグ2: 再代襲の株分け（世代ごとに親の株を分割）
# ---------------------------------------------------------------------------

def test_re_substitution_stirpes():
    """子F生存 + 子A死亡（子C生存・子B死亡, Bの子D,E生存）
    → F=1/2, C=1/4, D=E=1/8。"""
    data = {
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "children": [
            {"name": "F", "status": "alive"},
            {
                "name": "A",
                "status": "deceased",
                "children": [
                    {"name": "C", "status": "alive"},
                    {
                        "name": "B",
                        "status": "deceased",
                        "children": [
                            {"name": "D", "status": "alive"},
                            {"name": "E", "status": "alive"},
                        ],
                    },
                ],
            },
        ],
    }
    shares, _ = _shares(data)
    assert shares["F"] == Fraction(1, 2)
    assert shares["C"] == Fraction(1, 4)
    assert shares["D"] == Fraction(1, 8)
    assert shares["E"] == Fraction(1, 8)
    _assert_sum_one(shares)


# ---------------------------------------------------------------------------
# 正常系の回帰（既存挙動を壊さない）
# ---------------------------------------------------------------------------

def test_spouse_and_two_children():
    """配偶者1/2、子2人で1/2を折半 → 各1/4。"""
    data = {
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "spouse": {"name": "配偶者", "status": "alive"},
        "children": [
            {"name": "子1", "status": "alive"},
            {"name": "子2", "status": "alive"},
        ],
    }
    shares, _ = _shares(data)
    assert shares["配偶者"] == Fraction(1, 2)
    assert shares["子1"] == Fraction(1, 4)
    assert shares["子2"] == Fraction(1, 4)
    _assert_sum_one(shares)


def test_spouse_and_parents():
    """配偶者2/3、直系尊属2人で1/3を折半 → 各1/6。"""
    data = {
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "spouse": {"name": "配偶者", "status": "alive"},
        "parents": [
            {"name": "父", "status": "alive"},
            {"name": "母", "status": "alive"},
        ],
    }
    shares, _ = _shares(data)
    assert shares["配偶者"] == Fraction(2, 3)
    assert shares["父"] == Fraction(1, 6)
    assert shares["母"] == Fraction(1, 6)
    _assert_sum_one(shares)


def test_spouse_and_siblings():
    """配偶者3/4、兄弟姉妹（全血2人）で1/4を折半 → 各1/8。"""
    data = {
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "spouse": {"name": "配偶者", "status": "alive"},
        "siblings": [
            {"name": "兄", "status": "alive", "blood_relation": "full"},
            {"name": "妹", "status": "alive", "blood_relation": "full"},
        ],
    }
    shares, _ = _shares(data)
    assert shares["配偶者"] == Fraction(3, 4)
    assert shares["兄"] == Fraction(1, 8)
    assert shares["妹"] == Fraction(1, 8)
    _assert_sum_one(shares)


def test_spouse_only():
    """血族相続人なし → 配偶者が全部。"""
    data = {
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "spouse": {"name": "配偶者", "status": "alive"},
    }
    shares, _ = _shares(data)
    assert shares["配偶者"] == Fraction(1)
    _assert_sum_one(shares)


def test_renunciation_fallthrough_to_next_rank():
    """唯一の子が放棄 → 代襲せず次順位（直系尊属）へ。"""
    data = {
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "children": [
            {"name": "放棄子", "status": "alive", "renounced": True},
        ],
        "parents": [
            {"name": "父", "status": "alive"},
        ],
    }
    shares, result = _shares(data)
    assert "放棄子" not in shares
    assert shares["父"] == Fraction(1)
    _assert_sum_one(shares)


def test_sibling_representation_one_generation():
    """兄弟姉妹の代襲は一代限り（甥姪まで）。死亡兄の甥2人で折半。"""
    data = {
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "siblings": [
            {
                "name": "死亡兄",
                "status": "deceased",
                "blood_relation": "full",
                "children": [
                    {"name": "甥1", "status": "alive"},
                    {"name": "甥2", "status": "alive"},
                ],
            },
        ],
    }
    shares, _ = _shares(data)
    assert shares["甥1"] == Fraction(1, 2)
    assert shares["甥2"] == Fraction(1, 2)
    _assert_sum_one(shares)


def test_no_heirs_at_all():
    """相続人が一人もいない → has_legal_heirs False。"""
    data = {
        "deceased_name": "本人",
        "has_simultaneous_death": False,
    }
    calc = _MOD.InheritanceCalculator(data)
    result = calc.calculate()
    assert result["has_legal_heirs"] is False
    assert result["heirs"] == []


# ---------------------------------------------------------------------------
# P1-22 (a): 配偶者のみ → 100%（"1" と 0.00% の矛盾が無いこと）
# ---------------------------------------------------------------------------

def test_spouse_only_gets_full_share():
    shares, result = _shares({
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "spouse": {"name": "配偶者", "status": "alive"},
    })
    assert shares == {"配偶者": Fraction(1)}
    _assert_sum_one(shares)
    sp = result["heirs"][0]
    assert sp["inheritance_share_fraction"] == "1"
    assert sp["inheritance_share_percentage"] == "100.00%"


# ---------------------------------------------------------------------------
# P1-22 (b): 直系尊属の親等優先（民法889条1項1号）
#   母（1親等）生存＋祖父（2親等）生存 → 母のみが相続（各1/2にならない）
# ---------------------------------------------------------------------------

def test_second_rank_degree_priority():
    shares, _ = _shares({
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "parents": [
            {"name": "母", "status": "alive", "generation": 1},
            {"name": "祖父", "status": "alive", "generation": 2},
        ],
    })
    assert shares == {"母": Fraction(1)}, "親等の遠い祖父まで相続させている"


def test_second_rank_falls_to_grandparent_when_parents_gone():
    shares, _ = _shares({
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "spouse": {"name": "配偶者", "status": "alive"},
        "parents": [
            {"name": "父", "status": "deceased", "generation": 1},
            {"name": "祖母", "status": "alive", "generation": 2},
        ],
    })
    # 1親等が全員死亡 → 2親等（祖母）が第2順位。配偶者2/3・尊属1/3。
    assert shares == {"配偶者": Fraction(2, 3), "祖母": Fraction(1, 3)}
    _assert_sum_one(shares)


# ---------------------------------------------------------------------------
# P1-22 (c): status の明示バリデーション
# ---------------------------------------------------------------------------

def test_invalid_status_raises():
    with pytest.raises(ValueError):
        _MOD.InheritanceCalculator({
            "deceased_name": "本人",
            "has_simultaneous_death": False,
            "children": [{"name": "子", "status": "Alive"}],  # typo（大文字）
        })


def test_unknown_status_warns_but_allowed(capsys):
    calc = _MOD.InheritanceCalculator({
        "deceased_name": "本人",
        "has_simultaneous_death": False,
        "spouse": {"name": "配偶者", "status": "alive"},
        "children": [{"name": "子", "status": "unknown"}],
    })
    captured = capsys.readouterr()
    assert "unknown" in captured.err
    # unknown の子は判定から除外され、配偶者が全部相続
    result = calc.calculate()
    names = {h["name"] for h in result["heirs"]}
    assert names == {"配偶者"}
