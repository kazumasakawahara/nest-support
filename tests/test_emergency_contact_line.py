"""2026-11-06 河原さん：emergency-protocol は、連絡先をどこで確かめるかを具体的に一行で書く。「出せない」だけで終わらせない。DB を使わない。"""
import re
from pathlib import Path

TEXT = (Path(__file__).resolve().parents[1] / "claude-skills" / "emergency-protocol" / "SKILL.md").read_text(encoding="utf-8")


def test_output_template_names_where_to_confirm_contacts():
    blocks = re.findall(r"```text\n(.*?)```", TEXT, re.S)
    assert blocks, "出力の形が無い"
    lines = [l for b in blocks for l in b.splitlines() if "手元の緊急連絡カード" in l and "SOS の画面" in l]
    assert lines, "出力の形に、手元の緊急連絡カードと SOS の画面を一行で書く"
