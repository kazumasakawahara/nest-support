"""G-67（2026-11-06 河原さん承認）：neo4j-support-db の照会 15 が拾う範囲は「本人と直接つながるノードの操作まで」。
二つ先（事実の根拠の Record など）は拾わない。この範囲を照会 15 の説明に一行で書く。DB を使わない。"""
import re
from pathlib import Path

TEXT = (Path(__file__).resolve().parents[1] / "claude-skills" / "neo4j-support-db" / "SKILL.md").read_text(encoding="utf-8")


def test_query15_states_its_scope():
    section = re.search(r"### 15\.[^\n]*\n(.*?)(?=\n### |\n## )", TEXT, re.S).group(1)
    prose = re.sub(r"```.*?```", "", section, flags=re.S)
    assert "直接つながるノード" in prose and "二つ先" in prose, prose


def test_query15_reads_one_hop_only():
    section = re.search(r"### 15\.[^\n]*\n(.*?)(?=\n### |\n## )", TEXT, re.S).group(1)
    assert "(c)--(t)" in section and "*" not in section.split("```cypher", 1)[1].split("```", 1)[0]
