"""P2（2026-07）スキーマ拡張とマイグレーションのテスト。"""

from lib import schema_validator as sv


# --- B / C-1: status 列挙に Monitoring 追加、ケース正規化 ----------------------

def test_monitoring_is_valid_status():
    ok, _ = sv.validate_enum_value("status", "Monitoring")
    assert ok is True


def test_status_case_normalization():
    from scripts.migrate_condition_status_case import normalize_status_case
    assert normalize_status_case("active") == ("Active", True)
    assert normalize_status_case("MONITORING") == ("Monitoring", True)
    assert normalize_status_case("Active") == ("Active", False)  # 既に正規形
    # 未知値は変更しない
    val, changed = normalize_status_case("なんとなく")
    assert val == "なんとなく" and changed is False


def test_lowercase_active_is_flagged_before_migration():
    # 移行前の 'active' は列挙違反として検出される（だから移行が要る）
    ok, msg = sv.validate_enum_value("status", "active")
    assert ok is False
    assert "status" in msg


# --- C-2: Doctor ラベル / HAS_DOCTOR リレーション ----------------------------

def test_doctor_label_is_valid():
    ok, _ = sv.validate_node_label("Doctor")
    assert ok is True


def test_has_doctor_relationship_is_valid():
    ok, _, corrected = sv.validate_relationship_type("HAS_DOCTOR")
    assert ok is True
    assert corrected == "HAS_DOCTOR"
