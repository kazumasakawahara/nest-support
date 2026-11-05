"""Round 2 R2-B の小改修テスト（R2-7 / R2-10 / R2-13）。"""


# --- R2-7: detect_cascading_risk のクライアント名仮名化 -----------------------

def test_cascading_risk_masks_client_name(monkeypatch):
    import lib.insight_engine as ie
    import lib.db_operations as dbops

    monkeypatch.setattr(ie, "_run_query", lambda q, p=None: [
        {"date": "2026-07-01", "triggerTag": "入浴", "emotion": "Anger",
         "context": "c", "situation": "s"},
        {"date": "2026-07-02", "triggerTag": "食事", "emotion": "Sadness",
         "context": "c", "situation": "s"},
    ])

    class FakePseudo:
        enabled = True
        def mask_name(self, n):
            return "SECRET"

    monkeypatch.setattr(dbops, "_get_pseudonymizer", lambda: FakePseudo())
    r = ie.detect_cascading_risk("山田太郎")
    assert r["client_name"] == "SECRET"
    assert r["is_cascading"] is True


def test_cascading_risk_unmasked_when_disabled(monkeypatch):
    import lib.insight_engine as ie
    import lib.db_operations as dbops

    monkeypatch.setattr(ie, "_run_query", lambda q, p=None: [])

    class FakePseudo:
        enabled = False
        def mask_name(self, n):
            return "SHOULD_NOT_BE_USED"

    monkeypatch.setattr(dbops, "_get_pseudonymizer", lambda: FakePseudo())
    r = ie.detect_cascading_risk("山田太郎")
    assert r["client_name"] == "山田太郎"


# --- R2-10 / R2-13 は N-17（2026-11-05）で書き換えた ------------------------------
# R2-10（riskLevel の 高/中/低 を直す）と R2-13（_register_graph_tx の警告）は、Guardian Layer と
# 名前で MERGE する書き込みを確かめていた。どちらも外した。いまは「直さずに止める」を
# tests/test_gate_validate.py::test_risk_level_aliases_stop が、「書かない」を
# tests/test_db_operations_integration.py が確かめる。

def test_old_fixers_are_gone():
    import lib.db_operations as dbops
    assert not hasattr(dbops, "_register_graph_tx")
    import importlib.util
    assert importlib.util.find_spec("lib.schema_validator") is None
