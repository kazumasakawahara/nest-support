"""G-64（2026-11-06 河原さん：(b) 名前を変える）。推奨ケア → 特性のリレーションを ADDRESSES から RESPONDS_TO に改める。DB を使わない。

- 正典（表と JSON）に RESPONDS_TO があり、ADDRESSES が無い。版を上げた
- 読み取りの包みは RESPONDS_TO の照会を拒否しない。包みの部分一致の検査は緩めない（ADDRESSES は今も拒否される）
- ゲートは ADDRESSES を書かせない（正典に無いリレーション）
"""
from pathlib import Path

import pytest

from nest import canon, mcp_guard
from nest.gate import validate as gv

REPO = Path(__file__).resolve().parents[1]
TEXT = (REPO / "docs" / "SCHEMA.md").read_text(encoding="utf-8")
C = canon.load(REPO / "docs" / "SCHEMA.md")
STAFF = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"


def test_canon_has_responds_to_and_not_addresses():
    rels = C["personal"]["relationships"]
    assert rels["RESPONDS_TO"]["from"] == ["CarePreference"] and rels["RESPONDS_TO"]["to"] == ["Condition"]
    assert "ADDRESSES" not in rels
    assert "| `RESPONDS_TO` | CarePreference → Condition |" in TEXT
    assert TEXT.startswith("# nest-support スキーマ正典 — v0.10")


def test_wrapper_accepts_responds_to():
    mcp_guard.check_personal_text("MATCH (p:CarePreference)-[:RESPONDS_TO]->(cd:Condition) RETURN cd.name")


def test_wrapper_still_refuses_the_substring():
    with pytest.raises(mcp_guard.NotReadOnly):
        mcp_guard.check_personal_text("MATCH (p:CarePreference)-[:ADDRESSES]->(cd:Condition) RETURN cd.name")


def test_gate_refuses_addresses():
    cp = {"ref": "cp", "label": "CarePreference", "origin": "Human",
          "properties": {"category": "架空", "instruction": "架空"}}
    rep = gv.validate({"requestId": "req-g64", "actorStaffId": STAFF, "nodes": [cp],
                       "relationships": [{"type": "ADDRESSES", "from": "cp",
                                          "to": {"label": "Condition", "id": "CND-01HZZZZZZZZZZZZZZZZZZZZZZZ"}}]})
    assert not rep["ok"] and any("ADDRESSES" in e for e in rep["errors"]), rep["errors"]
