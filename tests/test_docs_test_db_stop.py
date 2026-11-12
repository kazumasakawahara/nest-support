"""ふだんの down では試験用の DB（neo4j-test）が止まらない（2026-11-12 河原さん）。三か所に一行ずつ書く。DB を使わない。"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LINE = "試験用の DB を起こした場合は、stop neo4j-test も打つ。down だけでは止まらない"


def test_the_three_places_say_down_does_not_stop_the_test_db():
    for name in ("CLAUDE.md", "docs/SETUP_GUIDE.md"):
        assert LINE in (REPO / name).read_text(encoding="utf-8"), name
    head = (REPO / "docker-compose.yml").read_text(encoding="utf-8").split("\nname:", 1)[0]
    assert LINE in head
