"""
シミュレーションデータを使った insight_engine のシナリオテスト
simulation-emotion-data.cypher のデータパターンを模擬し、
各アラートが期待通りに検知されることを検証する。
"""

import pytest
from unittest.mock import patch

from lib.insight_engine import (
    detect_emotion_drift,
    detect_cascading_risk,
    discover_care_patterns,
    propose_care_promotions,
    generate_risk_assessment,
)


def _build_simulation_emotion_drift_data():
    """simulation-emotion-data.cypher のパターンを再現"""
    rows = []
    # Baseline (3/1-3/14): 作業中 → 5件中1件がAnxiety
    rows.append({"triggerTag": "作業中", "emotion": "Joy", "period": "Baseline", "count": 2})
    rows.append({"triggerTag": "作業中", "emotion": "Calm", "period": "Baseline", "count": 2})
    rows.append({"triggerTag": "作業中", "emotion": "Anxiety", "period": "Baseline", "count": 1})
    # Baseline: 食事 → 3件中0件ネガティブ
    rows.append({"triggerTag": "食事", "emotion": "Calm", "period": "Baseline", "count": 2})
    rows.append({"triggerTag": "食事", "emotion": "Joy", "period": "Baseline", "count": 1})
    # Baseline: 他者交流 → 2件中0件ネガティブ
    rows.append({"triggerTag": "他者交流", "emotion": "Joy", "period": "Baseline", "count": 2})

    # Recent (3/24-3/30): 作業中 → 4件中2件がAnger/Fear
    rows.append({"triggerTag": "作業中", "emotion": "Calm", "period": "Recent", "count": 2})
    rows.append({"triggerTag": "作業中", "emotion": "Anger", "period": "Recent", "count": 1})
    rows.append({"triggerTag": "作業中", "emotion": "Fear", "period": "Recent", "count": 1})
    # Recent: 食事 → 1件Calm
    rows.append({"triggerTag": "食事", "emotion": "Calm", "period": "Recent", "count": 1})
    # Recent: 他者交流 → 2件中1件Anxiety
    rows.append({"triggerTag": "他者交流", "emotion": "Calm", "period": "Recent", "count": 1})
    rows.append({"triggerTag": "他者交流", "emotion": "Anxiety", "period": "Recent", "count": 1})

    return rows


class TestSimulationEmotionDrift:
    """Emotion Drift: 作業中タグで悪化を検知"""

    @patch("lib.insight_engine._run_query")
    def test_work_tag_drift_detected(self, mock_query):
        mock_query.return_value = _build_simulation_emotion_drift_data()
        result = detect_emotion_drift("山本翔太")

        # 作業中タグでアラートが出ること
        work_alerts = [a for a in result["alerts"] if a["triggerTag"] == "作業中"]
        assert len(work_alerts) == 1
        alert = work_alerts[0]

        # Baseline: 1/5 = 20%, Recent: 2/4 = 50% → drift = 1.5 (150%)
        assert alert["baseline_negative_rate"] == 0.2
        assert alert["recent_negative_rate"] == 0.5
        assert alert["drift"] >= 1.0  # 150% increase
        assert alert["severity"] == "high"

    @patch("lib.insight_engine._run_query")
    def test_social_tag_drift_detected(self, mock_query):
        mock_query.return_value = _build_simulation_emotion_drift_data()
        result = detect_emotion_drift("山本翔太")

        # 他者交流タグでもアラートが出ること (0% → 50%)
        social_alerts = [a for a in result["alerts"] if a["triggerTag"] == "他者交流"]
        assert len(social_alerts) == 1
        assert social_alerts[0]["severity"] == "high"

    @patch("lib.insight_engine._run_query")
    def test_food_tag_no_drift(self, mock_query):
        mock_query.return_value = _build_simulation_emotion_drift_data()
        result = detect_emotion_drift("山本翔太")

        # 食事タグはアラートなし (0% → 0%)
        food_alerts = [a for a in result["alerts"] if a["triggerTag"] == "食事"]
        assert len(food_alerts) == 0


class TestSimulationCascadingRisk:
    """Cascading Risk: 複数タグにまたがる負の感情の連鎖"""

    @patch("lib.insight_engine._run_query")
    def test_cascade_detected_multi_tag(self, mock_query):
        mock_query.return_value = [
            {"date": "2026-03-30", "triggerTag": "作業中", "emotion": "Anger", "context": "工事音", "situation": "作業"},
            {"date": "2026-03-29", "triggerTag": "他者交流", "emotion": "Anxiety", "context": "他利用者の声に過敏", "situation": "他者交流"},
            {"date": "2026-03-28", "triggerTag": "作業中", "emotion": "Fear", "context": "工事の破砕音", "situation": "作業"},
        ]
        result = detect_cascading_risk("山本翔太")

        assert result["is_cascading"] is True
        assert result["unique_triggers"] >= 2
        assert "意欲低下" in result["interpretation"]


class TestSimulationCarePatterns:
    """Care Pattern: 「別室に移動」パターンの自動発見"""

    @patch("lib.insight_engine._run_query")
    def test_room_change_pattern(self, mock_query):
        def side_effect(query, params=None):
            if "effectiveness" in query:
                return [
                    {"triggerTag": "作業中", "situation": "作業", "action": "別室に移動して作業", "emotion": "Calm", "frequency": 4},
                ]
            else:
                return []  # 既存CarePreference なし
        mock_query.side_effect = side_effect

        proposals = propose_care_promotions("山本翔太", min_frequency=3)
        assert len(proposals) >= 1
        room_change = [p for p in proposals if "別室" in p["action"]]
        assert len(room_change) == 1
        assert room_change[0]["already_exists"] is False
        assert room_change[0]["frequency"] >= 4


class TestSimulationRiskAssessment:
    """総合リスク評価: High + emergency-protocol 連動"""

    @patch("lib.insight_engine._run_query")
    def test_high_risk_triggers_emergency(self, mock_query):
        call_idx = [0]

        def side_effect(query, params=None):
            call_idx[0] += 1
            # Emotion drift
            if "Baseline" in query:
                return _build_simulation_emotion_drift_data()
            # Cascade
            if "negativeEmotions" in str(params):
                return [
                    {"date": "2026-03-30", "triggerTag": "作業中", "emotion": "Anger", "context": "", "situation": ""},
                    {"date": "2026-03-29", "triggerTag": "他者交流", "emotion": "Anxiety", "context": "", "situation": ""},
                ]
            # Care patterns / existing prefs
            if "effectiveness" in query:
                return [
                    {"triggerTag": "作業中", "situation": "作業", "action": "別室に移動して作業", "emotion": "Calm", "frequency": 4},
                ]
            return []

        mock_query.side_effect = side_effect

        result = generate_risk_assessment("山本翔太")

        assert result["risk_level"] == "high"
        assert result["should_trigger_emergency"] is True
        assert any("emergency-protocol" in a for a in result["recommended_actions"])
        assert len(result["care_promotions"]) >= 1
