"""G-65（2026-11-06 河原さん）：inheritance-calculator は残す。例の氏名が架空であることを、フィクスチャの規則（G-21）と
同じ印で示す（.md は先頭 10 行以内に「架空」）。DB を使わない。"""
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "claude-skills" / "inheritance-calculator" / "SKILL.md"


def test_skill_md_has_fictional_mark_in_first_ten_lines():
    head = SKILL.read_text(encoding="utf-8").splitlines()[:10]
    assert any("架空" in line for line in head), head
