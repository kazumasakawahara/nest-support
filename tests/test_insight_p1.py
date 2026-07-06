"""
P1-6 / P1-7: insight_engine の日付比較の型堅牢化と新規 triggerTag 検知。
"""

import lib.insight_engine as insight


def test_date_comparison_coerces_type():
    """P1-6: 日付比較は date(log.date) で型に依存しない（String/Date 両対応）。

    SupportLog.date は field-ui では String、demo では Date で書かれ得る。
    生の `log.date >= date()-duration` は String 側で null になり沈黙故障する。
    """
    for q in (insight._EMOTION_DRIFT_QUERY, insight._CASCADE_QUERY, insight._STAFF_LOAD_QUERY):
        assert "date(log.date) >=" in q, f"date(log.date) 強制が入っていない:\n{q}"
        # 生の裸比較が残っていないこと
        assert "\n  AND log.emotion" not in q or "date(log.date)" in q


def test_new_trigger_tag_is_alerted(monkeypatch):
    """P1-7: ベースライン期間に存在しない新規 triggerTag の負感情は別枠アラート。"""
    # 「新環境」タグは Recent にのみ登場（Baseline に無い）。負感情 Fear。
    rows = [
        {"triggerTag": "新環境", "emotion": "Fear", "period": "Recent", "count": 3},
        {"triggerTag": "食事", "emotion": "Calm", "period": "Baseline", "count": 5},
        {"triggerTag": "食事", "emotion": "Calm", "period": "Recent", "count": 2},
    ]
    monkeypatch.setattr(insight, "_run_query", lambda q, p=None: rows)

    result = insight.detect_emotion_drift("テスト太郎")
    tags = [a["triggerTag"] for a in result["alerts"]]
    assert "新環境" in tags, "新規出現の triggerTag がアラートされていない"
    new_alert = next(a for a in result["alerts"] if a["triggerTag"] == "新環境")
    assert new_alert.get("new_appearance") is True


def test_new_trigger_tag_without_negative_no_alert(monkeypatch):
    """新規タグでも負感情が無ければアラートしない。"""
    rows = [
        {"triggerTag": "新環境", "emotion": "Joy", "period": "Recent", "count": 3},
    ]
    monkeypatch.setattr(insight, "_run_query", lambda q, p=None: rows)
    result = insight.detect_emotion_drift("テスト太郎")
    assert all(a["triggerTag"] != "新環境" for a in result["alerts"])
