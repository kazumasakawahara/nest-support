"""P2（2026-07）のマイグレーションのテスト。

N-17（2026-11-05）で書き換えた：lib/schema_validator.py（Guardian Layer）を外したので、
その列挙・ラベル・リレーションの許可（Monitoring・Doctor・HAS_DOCTOR、'active' を違反と見る）を
確かめていた 4 本を外した。新しい規範の名前は tests/test_canon.py と tests/test_gate_validate.py が確かめる。
ゲートは列挙の大小文字だけを直して報告する（tests/test_gate_validate.py::test_case_of_enum_value_is_fixed_and_reported）。
"""


def test_status_case_normalization():
    from scripts.migrate_condition_status_case import normalize_status_case
    assert normalize_status_case("active") == ("Active", True)
    assert normalize_status_case("MONITORING") == ("Monitoring", True)
    assert normalize_status_case("Active") == ("Active", False)  # 既に正規形
    # 未知値は変更しない
    val, changed = normalize_status_case("なんとなく")
    assert val == "なんとなく" and changed is False
