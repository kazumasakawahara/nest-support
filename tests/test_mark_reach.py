"""確度の印は、そのすぐ前で終わる引用だけに掛かる（2026-11-12 河原さんの気づき。SEMANTICS SEM-ENUM-02「引用の直後（同じ行）の【…】」）。
DB を使わない。

Claude Desktop が毎回「【伝聞】の印が行末にあり、前の一文にも当たるかもしれない。入口で止まるかもしれない」とことわっていた。
入口の点検の動き（同じ行の前の一文には印が掛からず、Unspecified）を試験で固定し、narrative-extractor に文で書く。
"""
from pathlib import Path

from nest.gate import intake

REPO = Path(__file__).resolve().parents[1]
ORIGINAL = "架空の面接記録\n2026-11-12 電話\n母から電話。本人は最近よく眠れているとのこと。【伝聞】\n"


def test_the_mark_reaches_only_the_quote_right_before_it():
    assert intake.mark_of("本人は最近よく眠れているとのこと。", ORIGINAL) == "Hearsay"
    assert intake.mark_of("母から電話。", ORIGINAL) == "Unspecified"


def test_a_quote_spanning_both_sentences_takes_the_mark():
    assert intake.mark_of("母から電話。本人は最近よく眠れているとのこと。", ORIGINAL) == "Hearsay"


def test_the_skill_says_so_in_a_sentence():
    skill = (REPO / "claude-skills" / "narrative-extractor" / "SKILL.md").read_text(encoding="utf-8")
    assert "印は、そのすぐ前で終わる引用だけに掛かる" in skill
    assert "同じ行の前の文を別の事実にしたら、その事実には印が無いので `Unspecified` と書く（入口はそれで止まらない）" in skill
