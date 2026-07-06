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


# --- R2-10: riskLevel の 高/中/低 別名と未知値の警告 --------------------------

def test_risk_level_aliases_high_mid_low():
    from lib.schema_validator import normalize_risk_level
    assert normalize_risk_level("高") == "LifeThreatening"
    assert normalize_risk_level("中") == "Panic"
    assert normalize_risk_level("低") == "Discomfort"
    assert normalize_risk_level("high") == "LifeThreatening"
    assert normalize_risk_level("medium") == "Panic"
    assert normalize_risk_level("low") == "Discomfort"


def test_unknown_risk_level_is_flagged():
    from lib.schema_validator import validate_enum_value, normalize_risk_level
    v = normalize_risk_level("なんとなく危険")  # 未知値は補正されない
    assert v == "なんとなく危険"
    ok, msg = validate_enum_value("riskLevel", v)
    assert ok is False
    assert "riskLevel" in msg


# --- R2-13: tx 内 warnings が tx ローカルで累積しない ------------------------

def test_register_graph_tx_warnings_are_tx_local():
    from lib.db_operations import _register_graph_tx

    class _Res:
        def data(self):
            return [{"id": "x"}]

    class _Tx:
        def run(self, q, p=None):
            return _Res()

    nodes = [{"temp_id": "n1", "label": "BogusLabel", "properties": {}}]
    valid_labels = {"Client"}  # BogusLabel は不正
    args = (nodes, [], {}, valid_labels, set())

    _, _, _, w1 = _register_graph_tx(_Tx(), *args)
    _, _, _, w2 = _register_graph_tx(_Tx(), *args)
    # リトライ相当で2回呼んでも、毎回ちょうど1件（共有リストに累積しない）
    assert len(w1) == 1
    assert len(w2) == 1
    assert "BogusLabel" in w1[0]
