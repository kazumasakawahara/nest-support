"""N-29：利用者向けの文書を新しい構成に直す（2026-11-06）。DB を使わない。

- 前の構成（ポート 7687・7688・7474・7475、共有層、neo4j-agno-agent、neo4j-shared、前のコンテナ名、mcp__neo4j、
  execute_query、埋め込み）を書かない。記録の文書（HANDOVER・台帳・計画・ADR・MIGRATION_LOG・SUMMARY）は対象にしない
- 面談の音声ファイルの置き場所と保存の期間を運用の文書に書く（DB とリポジトリには置かない。正典 §4.2）
- PRIVACY_GUIDELINES の条番号は e-Gov で照合した印か【未照合】を付ける
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOCS = ["CLAUDE.md", "README.md", "docs/QUICK_START.md", "docs/SETUP_GUIDE.md", "docs/PRIVACY_GUIDELINES.md",
        "manifesto/MANIFESTO.md", "manifesto/protocols/emergency.md", "manifesto/protocols/onboarding.md",
        "docs/VOICE_RECORDING_GUIDE.md"]
OLD_PORT = re.compile(r"(?<!\d)(7687|7688|7474|7475)(?!\d)")
OLD = ("neo4j-shared", "neo4j-agno-agent", "共有層", "support-db-neo4j", "nest-support-neo4j", "mcp__neo4j",
       "execute_query", "embedding", "Embedding", "semantic_search", "neo4j.env", "neo4j-personal.env")


@pytest.mark.parametrize("path", DOCS)
def test_doc_has_no_old_setup(path):
    text = (REPO / path).read_text(encoding="utf-8")
    hits = [w for w in OLD if w in text] + OLD_PORT.findall(text)
    assert not hits, hits


def test_compose_notes_have_no_shared_layer():
    """compose の ":7687" はコンテナの中のポートなので見ない。前の DB を起動しない注記は残してよい"""
    text = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    assert not [w for w in ("neo4j-shared", "neo4j-agno-agent", "共有層", "support-db-neo4j") if w in text]


def test_setup_guide_html_copy_is_gone():
    """HTML の写しは前の構成のまま残りやすいので持たない。SETUP_GUIDE.md を一つの正とする"""
    assert not (REPO / "docs" / "SETUP_GUIDE.html").exists()


def test_voice_files_place_and_period_are_written():
    text = (REPO / "docs" / "VOICE_RECORDING_GUIDE.md").read_text(encoding="utf-8")
    assert "## 音声ファイルの置き場所と保存の期間" in text
    section = text.split("## 音声ファイルの置き場所と保存の期間", 1)[1].split("\n## ", 1)[0]
    assert "DB" in section and "リポジトリ" in section and "保存の期間" in section


def test_privacy_article_numbers_are_checked_or_marked():
    text = (REPO / "docs" / "PRIVACY_GUIDELINES.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if re.search(r"第\s*[0-9０-９一二三四五六七八九十百]+\s*条", line):
            assert "e-Gov で照合" in line or "【未照合】" in line, line
