"""
インサイトエンジン (The Oracle)

蓄積された SupportLog の感情データ (emotion, triggerTag, context) から
統計的な変化点を検知し、ケアの成功パターンを自動抽出する。

主要機能:
- detect_emotion_drift: 感情の悪化傾向を検知
- detect_cascading_risk: 負の感情の連鎖を検知
- detect_staff_overload: スタッフの負荷増大を検知
- discover_care_patterns: 効果的なケアパターンの自動発見
- propose_care_promotions: CarePreference への昇格提案
- generate_risk_assessment: 総合リスク評価
"""

import sys
from typing import Optional


def _log(message: str, level: str = "INFO"):
    sys.stderr.write(f"[InsightEngine:{level}] {message}\n")
    sys.stderr.flush()


def _run_query(query: str, params: dict | None = None) -> list[dict]:
    from lib.db_operations import run_query
    return run_query(query, params)


# =============================================================================
# 感情の波 (Emotion Drift)
# =============================================================================

NEGATIVE_EMOTIONS = {"Anger", "Sadness", "Fear", "Disgust", "Anxiety"}

# 感情をベースラインとの比較で分析するクエリ
_EMOTION_DRIFT_QUERY = """
MATCH (c:Client {name: $clientName})<-[:ABOUT]-(log:SupportLog)
WHERE log.date >= date() - duration({days: $baselineDays})
  AND log.emotion IS NOT NULL
WITH log,
     CASE WHEN log.date >= date() - duration({days: $recentDays})
          THEN 'Recent' ELSE 'Baseline' END AS period
RETURN log.triggerTag AS triggerTag,
       log.emotion AS emotion,
       period,
       count(*) AS count
ORDER BY triggerTag, period
"""


def detect_emotion_drift(
    client_name: str,
    baseline_days: int = 30,
    recent_days: int = 7,
    threshold: float = 0.3,
) -> dict:
    """
    特定クライアントの感情トレンドを分析し、ベースラインから悪化した項目を検出する。

    Args:
        client_name: クライアント名
        baseline_days: ベースライン期間（日）
        recent_days: 直近期間（日）
        threshold: 悪化率の閾値 (0.3 = 30%増)

    Returns:
        {
            "client_name": str,
            "alerts": [{"triggerTag": str, "baseline_negative_rate": float,
                        "recent_negative_rate": float, "drift": float, "severity": str}],
            "summary": {"total_logs": int, "period": str}
        }
    """
    rows = _run_query(_EMOTION_DRIFT_QUERY, {
        "clientName": client_name,
        "baselineDays": baseline_days,
        "recentDays": recent_days,
    })

    if not rows:
        return {
            "client_name": client_name,
            "alerts": [],
            "summary": {"total_logs": 0, "period": f"過去{baseline_days}日"},
        }

    # タグ × 期間 ごとに集計
    tag_stats: dict[str, dict] = {}
    for row in rows:
        tag = row.get("triggerTag") or "未分類"
        period = row["period"]
        emotion = row["emotion"]
        count = row["count"]

        if tag not in tag_stats:
            tag_stats[tag] = {"Baseline": {"total": 0, "negative": 0}, "Recent": {"total": 0, "negative": 0}}

        tag_stats[tag][period]["total"] += count
        if emotion in NEGATIVE_EMOTIONS:
            tag_stats[tag][period]["negative"] += count

    # 変化点を検出
    alerts = []
    for tag, stats in tag_stats.items():
        b_total = stats["Baseline"]["total"]
        b_neg = stats["Baseline"]["negative"]
        r_total = stats["Recent"]["total"]
        r_neg = stats["Recent"]["negative"]

        if b_total == 0 or r_total == 0:
            continue

        baseline_rate = b_neg / b_total
        recent_rate = r_neg / r_total

        if baseline_rate == 0:
            drift = 1.0 if recent_rate > 0 else 0.0
        else:
            drift = (recent_rate - baseline_rate) / baseline_rate

        if drift >= threshold:
            severity = "high" if drift >= 0.5 else "medium"
            alerts.append({
                "triggerTag": tag,
                "baseline_negative_rate": round(baseline_rate, 3),
                "recent_negative_rate": round(recent_rate, 3),
                "drift": round(drift, 3),
                "severity": severity,
            })

    alerts.sort(key=lambda a: a["drift"], reverse=True)

    total_logs = sum(
        stats[p]["total"] for stats in tag_stats.values() for p in ("Baseline", "Recent")
    )

    return {
        "client_name": client_name,
        "alerts": alerts,
        "summary": {
            "total_logs": total_logs,
            "period": f"過去{baseline_days}日 (直近{recent_days}日との比較)",
        },
    }


# =============================================================================
# 負の連鎖 (Cascading Risk)
# =============================================================================

_CASCADE_QUERY = """
MATCH (c:Client {name: $clientName})<-[:ABOUT]-(log:SupportLog)
WHERE log.date >= date() - duration({days: $days})
  AND log.emotion IN $negativeEmotions
RETURN log.date AS date,
       log.triggerTag AS triggerTag,
       log.emotion AS emotion,
       log.context AS context,
       log.situation AS situation
ORDER BY log.date DESC
"""


def detect_cascading_risk(
    client_name: str,
    days: int = 3,
    min_cascade: int = 2,
) -> dict:
    """
    直近数日間の負の感情が複数のきっかけタグにまたがっている（連鎖）かを検出する。

    Args:
        client_name: クライアント名
        days: 分析期間（日）
        min_cascade: 連鎖と判定するための最小タグ数

    Returns:
        {
            "client_name": str,
            "is_cascading": bool,
            "unique_triggers": int,
            "events": [...],
            "interpretation": str
        }
    """
    rows = _run_query(_CASCADE_QUERY, {
        "clientName": client_name,
        "days": days,
        "negativeEmotions": list(NEGATIVE_EMOTIONS),
    })

    unique_triggers = set()
    events = []
    for row in rows:
        tag = row.get("triggerTag") or "未分類"
        unique_triggers.add(tag)
        events.append({
            "date": str(row.get("date", "")),
            "triggerTag": tag,
            "emotion": row.get("emotion", ""),
            "context": row.get("context", ""),
            "situation": row.get("situation", ""),
        })

    is_cascading = len(unique_triggers) >= min_cascade

    if is_cascading:
        interpretation = (
            f"直近{days}日間で{len(unique_triggers)}種類の場面"
            f"（{', '.join(sorted(unique_triggers))}）で負の感情が記録されています。"
            "生活全般での意欲低下、または隠れた体調不良の予兆の可能性があります。"
        )
    elif events:
        interpretation = f"直近{days}日間で負の感情が{len(events)}件記録されていますが、特定場面に限定されています。"
    else:
        interpretation = f"直近{days}日間で負の感情は記録されていません。"

    return {
        "client_name": client_name,
        "is_cascading": is_cascading,
        "unique_triggers": len(unique_triggers),
        "events": events,
        "interpretation": interpretation,
    }


# =============================================================================
# スタッフ負荷 (Staff SOS)
# =============================================================================

_STAFF_LOAD_QUERY = """
MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)
WHERE log.date >= date() - duration({days: $days})
WITH s.name AS staffName,
     count(log) AS totalLogs,
     count(CASE WHEN log.emotion IN $negativeEmotions THEN 1 END) AS negativeLogs
RETURN staffName, totalLogs, negativeLogs
ORDER BY negativeLogs DESC
"""


def detect_staff_overload(
    days: int = 7,
    negative_ratio_threshold: float = 0.5,
) -> list[dict]:
    """
    スタッフごとの記録に占める負の感情ログの割合が閾値を超えるスタッフを検出する。

    Returns:
        [{"staffName": str, "totalLogs": int, "negativeLogs": int,
          "negativeRatio": float, "alert": bool}]
    """
    rows = _run_query(_STAFF_LOAD_QUERY, {
        "days": days,
        "negativeEmotions": list(NEGATIVE_EMOTIONS),
    })

    results = []
    for row in rows:
        total = row.get("totalLogs", 0)
        negative = row.get("negativeLogs", 0)
        ratio = negative / total if total > 0 else 0.0
        results.append({
            "staffName": row.get("staffName", ""),
            "totalLogs": total,
            "negativeLogs": negative,
            "negativeRatio": round(ratio, 3),
            "alert": ratio >= negative_ratio_threshold and total >= 3,
        })

    return results


# =============================================================================
# ケアパターン発見 (Care Pattern Discovery)
# =============================================================================

_CARE_PATTERN_QUERY = """
MATCH (c:Client {name: $clientName})<-[:ABOUT]-(log:SupportLog)
WHERE log.effectiveness IN ['Effective', 'High']
  AND log.action IS NOT NULL
  AND log.action <> ''
WITH log.triggerTag AS triggerTag,
     log.situation AS situation,
     log.action AS action,
     log.emotion AS emotion,
     count(*) AS frequency
WHERE frequency >= $minFrequency
RETURN triggerTag, situation, action, emotion,
       frequency
ORDER BY frequency DESC
LIMIT $limit
"""

_EXISTING_CARE_PREFS_QUERY = """
MATCH (c:Client {name: $clientName})-[:REQUIRES|PREFERS]->(cp:CarePreference)
RETURN cp.category AS category, cp.instruction AS instruction
"""


def discover_care_patterns(
    client_name: str,
    min_frequency: int = 2,
    limit: int = 10,
) -> dict:
    """
    効果的だった対応パターンを自動発見する。

    Returns:
        {
            "client_name": str,
            "patterns": [{"triggerTag": str, "situation": str, "action": str,
                          "emotion": str, "frequency": int}],
            "existing_care_prefs": [{"category": str, "instruction": str}]
        }
    """
    patterns = _run_query(_CARE_PATTERN_QUERY, {
        "clientName": client_name,
        "minFrequency": min_frequency,
        "limit": limit,
    })

    existing = _run_query(_EXISTING_CARE_PREFS_QUERY, {
        "clientName": client_name,
    })

    return {
        "client_name": client_name,
        "patterns": patterns,
        "existing_care_prefs": existing,
    }


# =============================================================================
# CarePreference 昇格提案
# =============================================================================

def propose_care_promotions(client_name: str, min_frequency: int = 3) -> list[dict]:
    """
    discover_care_patterns で発見された有効パターンのうち、
    まだ CarePreference に登録されていないものを昇格候補として提案する。

    Returns:
        [{"triggerTag": str, "action": str, "frequency": int,
          "proposed_category": str, "proposed_instruction": str,
          "already_exists": bool}]
    """
    discovery = discover_care_patterns(client_name, min_frequency=min_frequency)
    patterns = discovery["patterns"]
    existing = discovery["existing_care_prefs"]

    # 既存の CarePreference を instruction でインデックス化
    existing_instructions = {
        cp.get("instruction", "").strip().lower() for cp in existing if cp.get("instruction")
    }

    proposals = []
    for p in patterns:
        action = p.get("action", "")
        trigger = p.get("triggerTag") or p.get("situation") or "一般"

        already_exists = action.strip().lower() in existing_instructions

        proposals.append({
            "triggerTag": trigger,
            "action": action,
            "frequency": p.get("frequency", 0),
            "proposed_category": trigger,
            "proposed_instruction": action,
            "already_exists": already_exists,
        })

    return proposals


def promote_to_care_preference(
    client_name: str,
    category: str,
    instruction: str,
    user_name: str = "insight_engine",
) -> dict:
    """
    効果的なケアパターンを CarePreference ノードとして正式登録する。

    Returns:
        登録結果
    """
    from lib.db_operations import register_to_database

    graph = {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {"name": client_name}},
            {"temp_id": "cp1", "label": "CarePreference", "properties": {
                "category": category,
                "instruction": instruction,
                "priority": "Medium",
                "source": "auto_promoted",
            }},
        ],
        "relationships": [
            {"source_temp_id": "c1", "target_temp_id": "cp1",
             "type": "REQUIRES", "properties": {}},
        ],
    }

    return register_to_database(graph, user_name=user_name)


# =============================================================================
# 総合リスク評価
# =============================================================================

def generate_risk_assessment(
    client_name: str,
    baseline_days: int = 30,
    recent_days: int = 7,
) -> dict:
    """
    クライアントの総合リスク評価を生成する。
    emotion_drift + cascading_risk + care_patterns を統合。

    Returns:
        {
            "client_name": str,
            "risk_level": "high" | "medium" | "low",
            "emotion_drift": {...},
            "cascading_risk": {...},
            "care_promotions": [...],
            "recommended_actions": [str],
            "should_trigger_emergency": bool
        }
    """
    drift = detect_emotion_drift(client_name, baseline_days, recent_days)
    cascade = detect_cascading_risk(client_name)
    promotions = propose_care_promotions(client_name)

    # リスクレベルの判定
    high_alerts = [a for a in drift["alerts"] if a["severity"] == "high"]
    medium_alerts = [a for a in drift["alerts"] if a["severity"] == "medium"]

    risk_level = "low"
    should_trigger_emergency = False
    recommended_actions = []

    if high_alerts and cascade["is_cascading"]:
        risk_level = "high"
        should_trigger_emergency = True
        recommended_actions.append(
            "emergency-protocol を即時起動し、管理者に報告してください。"
        )
        recommended_actions.append(
            f"特に「{high_alerts[0]['triggerTag']}」場面での対応を重点的に見直してください。"
        )
    elif high_alerts or (cascade["is_cascading"] and len(cascade["events"]) >= 3):
        risk_level = "medium"
        recommended_actions.append("ケース会議での議題に追加してください。")
        if high_alerts:
            recommended_actions.append(
                f"「{high_alerts[0]['triggerTag']}」場面でのネガティブ感情が急増しています。"
            )
    elif medium_alerts:
        risk_level = "low"
        recommended_actions.append("経過観察を継続してください。")

    # 昇格提案がある場合
    new_promotions = [p for p in promotions if not p["already_exists"]]
    if new_promotions:
        recommended_actions.append(
            f"効果的なケアパターンが{len(new_promotions)}件発見されています。CarePreference への登録を検討してください。"
        )

    return {
        "client_name": client_name,
        "risk_level": risk_level,
        "emotion_drift": drift,
        "cascading_risk": cascade,
        "care_promotions": new_promotions,
        "recommended_actions": recommended_actions,
        "should_trigger_emergency": should_trigger_emergency,
    }
