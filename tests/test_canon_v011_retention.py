"""N-32a：正典 v0.11（2026-11-06 河原さん。止まる点 F-1。台帳 G-74）。DB を使わない。

廃棄のために、tsunagu-net の正典 v0.29〜v0.30 と同じ名前で次だけを足す：
保存の判断 RetentionDecision・DECIDES_ON（→ Client。nest-support は本人が中心）・retentionDecision（Keep・Delete）・
auditAction の Purge・AuditLog の retentionId・purgedCounts・keptPersons。
"""
from pathlib import Path

from nest import canon

REPO = Path(__file__).resolve().parents[1]
C = canon.load(REPO / "docs" / "SCHEMA.md")
NODES = C["personal"]["nodes"]
RELS = C["personal"]["relationships"]


def test_retention_decision_node_has_the_tsunagu_net_names():
    rd = NODES["RetentionDecision"]
    assert rd["required"] == ["retentionId", "decidedOn", "decision", "reason"]
    assert rd["optional"] == ["nextReviewOn"]
    assert rd["unique"] == ["retentionId"]
    assert C["idPrefixes"]["RetentionDecision"] == "RTD"
    assert C["types"]["RetentionDecision.decidedOn"] == "Date"
    assert C["types"]["RetentionDecision.nextReviewOn"] == "Date"


def test_decides_on_points_at_the_client():
    assert RELS["DECIDES_ON"]["from"] == ["RetentionDecision"]
    assert RELS["DECIDES_ON"]["to"] == ["Client"]


def test_retention_decision_enum_is_keep_or_delete():
    assert C["enums"]["retentionDecision"] == ["Keep", "Delete"]
    assert C["enumBindings"]["RetentionDecision.decision"] == "retentionDecision"


def test_purge_is_an_audit_action_with_counts_only():
    assert "Purge" in C["enums"]["auditAction"]
    assert NODES["AuditLog"]["optional"] == ["selfApproval", "retentionId", "purgedCounts", "keptPersons"]
    assert C["types"]["AuditLog.purgedCounts"] == "List"
    assert C["types"]["AuditLog.keptPersons"] == "Integer"


def test_the_table_and_history_say_v0_11():
    text = (REPO / "docs" / "SCHEMA.md").read_text(encoding="utf-8")
    assert text.startswith("# nest-support スキーマ正典 — v0.11")
    assert "| `RetentionDecision` |" in text and "| `DECIDES_ON` | RetentionDecision → Client |" in text
    assert "- v0.11（2026-11-06）" in text
