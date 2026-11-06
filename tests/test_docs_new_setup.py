"""N-29：利用者向けの文書を新しい構成に直す（2026-11-06）。DB を使わない。

- 前の構成（ポート 7687・7688・7474・7475、共有層、neo4j-agno-agent、neo4j-shared、前のコンテナ名、mcp__neo4j、
  execute_query、埋め込み）を書かない。記録の文書（HANDOVER・台帳・計画・ADR・MIGRATION_LOG・SUMMARY）は対象にしない
- 面談の音声ファイルの置き場所と保存の期間を運用の文書に書く（DB とリポジトリには置かない。正典 §4.2）
- PRIVACY_GUIDELINES の条番号は e-Gov で照合した印か【未照合】を付ける
"""
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOCS = ["CLAUDE.md", "README.md", "docs/QUICK_START.md", "docs/SETUP_GUIDE.md", "docs/PRIVACY_GUIDELINES.md",
        "manifesto/MANIFESTO.md", "manifesto/protocols/emergency.md", "manifesto/protocols/onboarding.md",
        "docs/VOICE_RECORDING_GUIDE.md",
        # E-3（2026-11-06 河原さん。台帳 G-71）：支援の実務の文書は DB・名前に触れる箇所を直す。FAQ は実務の問いだけ残す
        "manifesto/protocols/handover.md", "manifesto/protocols/parent_down.md",
        "manifesto/workflows/renewal_check.md", "manifesto/workflows/resilience_report.md",
        "manifesto/workflows/visit_preparation.md", "docs/FAQ.md"]
# 前の配布物の導入・配布の手順は外した（要るときは新しい構成で書き直す。台帳 G-71）
REMOVED_DOCS = ["docs/DEPLOYMENT_GUIDE.md", "docs/DISTRIBUTION_PLAN.md", "docs/USER_MANUAL_WINDOWS.md",
                "docs/VIDEO_SCRIPTS.md", "docs/ADVANCED_USAGE.md"]
OLD_PORT = re.compile(r"(?<!\d)(7687|7688|7474|7475)(?!\d)")
OLD = ("neo4j-shared", "neo4j-agno-agent", "共有層", "support-db-neo4j", "nest-support-neo4j", "mcp__neo4j",
       "execute_query", "embedding", "Embedding", "semantic_search", "neo4j.env", "neo4j-personal.env",
       "{name:", "MERGE ", "CREATE (", "SET c.", "KeyPerson {", "Supporter", "ServiceProvider")


@pytest.mark.parametrize("path", DOCS)
def test_doc_has_no_old_setup(path):
    text = (REPO / path).read_text(encoding="utf-8")
    hits = [w for w in OLD if w in text] + OLD_PORT.findall(text)
    assert not hits, hits


@pytest.mark.parametrize("path", REMOVED_DOCS)
def test_old_distribution_docs_are_gone(path):
    assert not (REPO / path).exists()


def test_no_link_points_at_a_removed_doc():
    out = subprocess.run(["git", "grep", "-l", "-E", "|".join(Path(p).name for p in REMOVED_DOCS)],
                         cwd=REPO, capture_output=True, text=True).stdout.split()
    keep = ("docs/gray-decisions.md", "docs/implementation-plan.md", "HANDOVER.md", "tests/test_docs_new_setup.py")
    # installer/ は前の構成のまま残しているコード（置き換えるまで。tests/test_old_db_code_isolated.py）
    assert [p for p in out if p not in keep and not p.startswith(("docs/adr/", "decommissioned/", "docs/SUMMARY_",
                                                                     "installer/"))] == []


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
