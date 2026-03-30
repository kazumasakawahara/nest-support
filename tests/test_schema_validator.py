"""
schema_validator モジュールのユニットテスト
"""

import pytest
from lib.schema_validator import (
    normalize_property_name,
    normalize_properties,
    validate_node_label,
    validate_relationship_type,
    validate_enum_value,
    validate_and_normalize_graph,
)


class TestNormalizePropertyName:
    def test_already_camel_case(self):
        assert normalize_property_name("riskLevel") == "riskLevel"
        assert normalize_property_name("bloodType") == "bloodType"
        assert normalize_property_name("nextRenewalDate") == "nextRenewalDate"

    def test_single_word(self):
        assert normalize_property_name("name") == "name"
        assert normalize_property_name("dob") == "dob"
        assert normalize_property_name("status") == "status"

    def test_snake_case_known_mapping(self):
        assert normalize_property_name("risk_level") == "riskLevel"
        assert normalize_property_name("blood_type") == "bloodType"
        assert normalize_property_name("next_renewal_date") == "nextRenewalDate"
        assert normalize_property_name("client_id") == "clientId"
        assert normalize_property_name("trigger_tag") == "triggerTag"

    def test_snake_case_generic_conversion(self):
        assert normalize_property_name("some_new_field") == "someNewField"
        assert normalize_property_name("created_at") == "createdAt"

    def test_legacy_service_provider_properties(self):
        assert normalize_property_name("office_name") == "name"
        assert normalize_property_name("corp_name") == "corporateName"
        assert normalize_property_name("service_type") == "serviceType"
        assert normalize_property_name("office_number") == "wamnetId"


class TestNormalizeProperties:
    def test_mixed_properties(self):
        props = {
            "name": "テスト太郎",
            "blood_type": "A",
            "risk_level": "Panic",
            "dob": "1990-01-01",
        }
        result = normalize_properties(props, "Client")
        assert result == {
            "name": "テスト太郎",
            "bloodType": "A",
            "riskLevel": "Panic",
            "dob": "1990-01-01",
        }

    def test_no_changes_needed(self):
        props = {"name": "太郎", "bloodType": "B", "status": "Active"}
        result = normalize_properties(props)
        assert result == props


class TestValidateNodeLabel:
    def test_valid_labels(self):
        for label in ["Client", "NgAction", "SupportLog", "CarePreference", "Recipient"]:
            is_valid, _ = validate_node_label(label)
            assert is_valid, f"{label} should be valid"

    def test_invalid_label(self):
        is_valid, msg = validate_node_label("UnknownLabel")
        assert not is_valid
        assert "未知のノードラベル" in msg


class TestValidateRelationshipType:
    def test_valid_types(self):
        is_valid, _, corrected = validate_relationship_type("MUST_AVOID")
        assert is_valid
        assert corrected == "MUST_AVOID"

    def test_deprecated_auto_correction(self):
        is_valid, msg, corrected = validate_relationship_type("PROHIBITED")
        assert is_valid
        assert corrected == "MUST_AVOID"
        assert "廃止" in msg

        is_valid, _, corrected = validate_relationship_type("PREFERS")
        assert corrected == "REQUIRES"

        is_valid, _, corrected = validate_relationship_type("EMERGENCY_CONTACT")
        assert corrected == "HAS_KEY_PERSON"

    def test_invalid_type(self):
        is_valid, msg, _ = validate_relationship_type("UNKNOWN_REL")
        assert not is_valid
        assert "未知のリレーションタイプ" in msg


class TestValidateEnumValue:
    def test_valid_risk_level(self):
        for val in ["LifeThreatening", "Panic", "Discomfort"]:
            is_valid, _ = validate_enum_value("riskLevel", val)
            assert is_valid

    def test_invalid_risk_level(self):
        is_valid, msg = validate_enum_value("riskLevel", "high")
        assert not is_valid
        assert "有効な値" in msg

    def test_non_enum_property(self):
        is_valid, _ = validate_enum_value("name", "anything")
        assert is_valid


class TestValidateAndNormalizeGraph:
    def test_full_normalization(self):
        graph = {
            "nodes": [
                {
                    "temp_id": "c1",
                    "label": "Client",
                    "properties": {"name": "田中太郎", "blood_type": "A"},
                },
                {
                    "temp_id": "ng1",
                    "label": "NgAction",
                    "properties": {
                        "action": "大きな音",
                        "risk_level": "Panic",
                        "reason": "パニック発作",
                    },
                },
            ],
            "relationships": [
                {
                    "source_temp_id": "c1",
                    "target_temp_id": "ng1",
                    "type": "PROHIBITED",
                    "properties": {},
                },
            ],
        }

        normalized, warnings = validate_and_normalize_graph(graph)

        # プロパティが camelCase に変換されている
        assert normalized["nodes"][0]["properties"]["bloodType"] == "A"
        assert "blood_type" not in normalized["nodes"][0]["properties"]

        assert normalized["nodes"][1]["properties"]["riskLevel"] == "Panic"
        assert "risk_level" not in normalized["nodes"][1]["properties"]

        # 廃止リレーションが修正されている
        assert normalized["relationships"][0]["type"] == "MUST_AVOID"

        # 警告が出ている
        assert any("廃止" in w for w in warnings)

    def test_already_clean_graph(self):
        graph = {
            "nodes": [
                {
                    "temp_id": "c1",
                    "label": "Client",
                    "properties": {"name": "テスト", "bloodType": "O"},
                },
            ],
            "relationships": [],
        }

        normalized, warnings = validate_and_normalize_graph(graph)
        assert len(warnings) == 0
        assert normalized["nodes"][0]["properties"]["bloodType"] == "O"
