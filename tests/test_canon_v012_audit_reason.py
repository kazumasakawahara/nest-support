"""G-91：正典 v0.12（2026-11-06 河原さん承認）。DB を使わない。

AuditLog に reason（文字列。差し戻し Reject のときだけ・任意・一行・名前を書かない。決まりは RetentionDecision.reason と同じ）を足す。
"""
from pathlib import Path

from nest import canon

REPO = Path(__file__).resolve().parents[1]
C = canon.load(REPO / "docs" / "SCHEMA.md")
TEXT = (REPO / "docs" / "SCHEMA.md").read_text(encoding="utf-8")


def test_audit_log_has_an_optional_reason():
    a = C["personal"]["nodes"]["AuditLog"]
    assert "reason" in a["optional"] and "reason" not in a["required"]


def test_the_table_and_history_say_v0_12():
    assert "- v0.12（2026-11-06）" in TEXT
    row = next(l for l in TEXT.splitlines() if l.startswith("| `AuditLog` |"))
    assert "`reason`" in row and "Reject のときだけ" in row and "名前を書かない" in row
