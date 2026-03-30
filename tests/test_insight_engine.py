"""
insight_engine モジュールのユニットテスト
Neo4j接続なしでロジック部分をテストする。
"""

import pytest
from unittest.mock import patch

from lib.insight_engine import (
    detect_emotion_drift,
    detect_cascading_risk,
    detect_staff_overload,
    discover_care_patterns,
    propose_care_promotions,
    generate_risk_assessment,
    NEGATIVE_EMOTIONS,
)


def _mock_run_query(query, params=None):
    """テスト用のクエリモック - クエリ内容に応じてダミーデータを返す"""
    return []


class TestDetectEmotionDrift:
    @patch("lib.insight_engine._run_query")
    def test_no_data(self, mock_query):
        mock_query.return_value = []
        result = detect_emotion_drift("テスト太郎")
        assert result["client_name"] == "テスト太郎"
        assert result["alerts"] == []
        assert result["summary"]["total_logs"] == 0

    @patch("lib.insight_engine._run_query")
    def test_drift_detected(self, mock_query):
        # Baseline: 10件中2件がAnger (20%)
        # Recent: 10件中5件がAnger (50%) → drift = 1.5 (150%増)
        mock_query.return_value = [
            {"triggerTag": "作業中", "emotion": "Calm", "period": "Baseline", "count": 8},
            {"triggerTag": "作業中", "emotion": "Anger", "period": "Baseline", "count": 2},
            {"triggerTag": "作業中", "emotion": "Calm", "period": "Recent", "count": 5},
            {"triggerTag": "作業中", "emotion": "Anger", "period": "Recent", "count": 5},
        ]
        result = detect_emotion_drift("テスト太郎")
        assert len(result["alerts"]) == 1
        alert = result["alerts"][0]
        assert alert["triggerTag"] == "作業中"
        assert alert["severity"] == "high"
        assert alert["drift"] > 0.3

    @patch("lib.insight_engine._run_query")
    def test_no_drift(self, mock_query):
        # Baseline: 10件中2件がAnger (20%)
        # Recent: 10件中2件がAnger (20%) → drift = 0
        mock_query.return_value = [
            {"triggerTag": "食事", "emotion": "Calm", "period": "Baseline", "count": 8},
            {"triggerTag": "食事", "emotion": "Anger", "period": "Baseline", "count": 2},
            {"triggerTag": "食事", "emotion": "Calm", "period": "Recent", "count": 8},
            {"triggerTag": "食事", "emotion": "Anger", "period": "Recent", "count": 2},
        ]
        result = detect_emotion_drift("テスト太郎")
        assert len(result["alerts"]) == 0


class TestDetectCascadingRisk:
    @patch("lib.insight_engine._run_query")
    def test_cascade_detected(self, mock_query):
        mock_query.return_value = [
            {"date": "2026-03-30", "triggerTag": "作業中", "emotion": "Anger", "context": "朝の作業で", "situation": "作業"},
            {"date": "2026-03-29", "triggerTag": "食事", "emotion": "Sadness", "context": "昼食時", "situation": "食事"},
        ]
        result = detect_cascading_risk("テスト太郎")
        assert result["is_cascading"] is True
        assert result["unique_triggers"] == 2
        assert "意欲低下" in result["interpretation"]

    @patch("lib.insight_engine._run_query")
    def test_no_cascade(self, mock_query):
        mock_query.return_value = [
            {"date": "2026-03-30", "triggerTag": "作業中", "emotion": "Anger", "context": "", "situation": "作業"},
        ]
        result = detect_cascading_risk("テスト太郎")
        assert result["is_cascading"] is False

    @patch("lib.insight_engine._run_query")
    def test_no_events(self, mock_query):
        mock_query.return_value = []
        result = detect_cascading_risk("テスト太郎")
        assert result["is_cascading"] is False
        assert "記録されていません" in result["interpretation"]


class TestDetectStaffOverload:
    @patch("lib.insight_engine._run_query")
    def test_overloaded_staff(self, mock_query):
        mock_query.return_value = [
            {"staffName": "鈴木", "totalLogs": 10, "negativeLogs": 6},
            {"staffName": "佐藤", "totalLogs": 10, "negativeLogs": 2},
        ]
        results = detect_staff_overload()
        assert len(results) == 2
        assert results[0]["alert"] is True  # 鈴木: 60%
        assert results[1]["alert"] is False  # 佐藤: 20%


class TestDiscoverCarePatterns:
    @patch("lib.insight_engine._run_query")
    def test_patterns_found(self, mock_query):
        def side_effect(query, params=None):
            if "effectiveness" in query:
                return [
                    {"triggerTag": "パニック時", "situation": "パニック", "action": "別室に移動", "emotion": "Fear", "frequency": 5},
                ]
            else:
                return [
                    {"category": "食事", "instruction": "スプーンを使用"},
                ]
        mock_query.side_effect = side_effect

        result = discover_care_patterns("テスト太郎")
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["frequency"] == 5
        assert len(result["existing_care_prefs"]) == 1


class TestProposeCarePromotions:
    @patch("lib.insight_engine._run_query")
    def test_new_promotion(self, mock_query):
        def side_effect(query, params=None):
            if "effectiveness" in query:
                return [
                    {"triggerTag": "パニック時", "situation": "パニック", "action": "別室に移動", "emotion": "Fear", "frequency": 5},
                ]
            else:
                return [
                    {"category": "食事", "instruction": "スプーンを使用"},
                ]
        mock_query.side_effect = side_effect

        proposals = propose_care_promotions("テスト太郎", min_frequency=2)
        assert len(proposals) == 1
        assert proposals[0]["already_exists"] is False
        assert proposals[0]["proposed_instruction"] == "別室に移動"

    @patch("lib.insight_engine._run_query")
    def test_already_exists(self, mock_query):
        def side_effect(query, params=None):
            if "effectiveness" in query:
                return [
                    {"triggerTag": "食事", "situation": "食事", "action": "スプーンを使用", "emotion": "Calm", "frequency": 5},
                ]
            else:
                return [
                    {"category": "食事", "instruction": "スプーンを使用"},
                ]
        mock_query.side_effect = side_effect

        proposals = propose_care_promotions("テスト太郎", min_frequency=2)
        assert len(proposals) == 1
        assert proposals[0]["already_exists"] is True


class TestGenerateRiskAssessment:
    @patch("lib.insight_engine._run_query")
    def test_high_risk(self, mock_query):
        call_count = [0]

        def side_effect(query, params=None):
            call_count[0] += 1
            # Emotion drift query
            if "Baseline" in query:
                return [
                    {"triggerTag": "作業中", "emotion": "Calm", "period": "Baseline", "count": 8},
                    {"triggerTag": "作業中", "emotion": "Anger", "period": "Baseline", "count": 2},
                    {"triggerTag": "作業中", "emotion": "Calm", "period": "Recent", "count": 3},
                    {"triggerTag": "作業中", "emotion": "Anger", "period": "Recent", "count": 7},
                ]
            # Cascade query
            if "negativeEmotions" in str(params):
                return [
                    {"date": "2026-03-30", "triggerTag": "作業中", "emotion": "Anger", "context": "", "situation": ""},
                    {"date": "2026-03-29", "triggerTag": "食事", "emotion": "Sadness", "context": "", "situation": ""},
                ]
            # Care patterns / existing prefs
            return []

        mock_query.side_effect = side_effect

        result = generate_risk_assessment("テスト太郎")
        assert result["risk_level"] == "high"
        assert result["should_trigger_emergency"] is True
        assert any("emergency-protocol" in a for a in result["recommended_actions"])

    @patch("lib.insight_engine._run_query")
    def test_low_risk(self, mock_query):
        mock_query.return_value = []
        result = generate_risk_assessment("テスト太郎")
        assert result["risk_level"] == "low"
        assert result["should_trigger_emergency"] is False
