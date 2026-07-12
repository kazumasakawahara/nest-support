"""
スキーマバリデーションモジュール (The Guardian)

SCHEMA_CONVENTION.md に基づき、プロパティ名の camelCase 自動変換、
ノードラベル・リレーションタイプ・列挙値の検証を行う。
LLM が生成した構造化データの品質を担保する「守護神」レイヤー。
"""

import re
import sys


def _log(message: str, level: str = "INFO"):
    sys.stderr.write(f"[SchemaValidator:{level}] {message}\n")
    sys.stderr.flush()


# =============================================================================
# 正式なノードラベル (SCHEMA_CONVENTION.md 準拠)
# =============================================================================

VALID_NODE_LABELS_7687 = frozenset({
    "Client", "Condition", "NgAction", "CarePreference", "KeyPerson",
    "Guardian", "Hospital", "Certificate", "PublicAssistance", "Organization",
    "Supporter", "SupportLog", "MeetingRecord", "AuditLog", "LifeHistory",
    "Wish", "Identity", "ServiceProvider", "ProviderFeedback",
    # 第5の柱（親の機能移行）— SSOT v3.1
    "Relative", "CareRole",
    # かかりつけ医の構造化（P2 / 2026-07）— Hospital.doctor 文字列から昇格
    "Doctor",
})

# 生活困窮者自立支援DB（port 7688）は 2026-05 廃止。7688 用のラベル定義は撤去済み。
VALID_NODE_LABELS = VALID_NODE_LABELS_7687

# =============================================================================
# 正式なリレーションシップタイプ
# =============================================================================

VALID_RELATIONSHIP_TYPES = frozenset({
    # port 7687
    "HAS_CONDITION", "MUST_AVOID", "IN_CONTEXT", "REQUIRES", "ADDRESSES",
    "HAS_KEY_PERSON", "HAS_LEGAL_REP", "HAS_CERTIFICATE", "RECEIVES",
    "REGISTERED_AT", "TREATED_AT", "SUPPORTED_BY", "LOGGED", "RECORDED",
    "ABOUT", "FOLLOWS", "AUDIT_FOR", "HAS_HISTORY", "HAS_WISH",
    "HAS_IDENTITY", "USES_SERVICE", "HAS_FEEDBACK", "WROTE",
    # 第5の柱（親の機能移行）— SSOT v3.1
    "IS_PARENT_OF", "FAMILY_OF", "PERFORMS", "CAN_BE_PERFORMED_BY",
    # かかりつけ医の構造化（P2 / 2026-07）
    "HAS_DOCTOR",
})

# 廃止リレーション → 正式名のマッピング (書き込み時の自動修正用)
# HOLDS は 7688 用ではなく 7687 の旧・手帳リレーション（SCHEMA_CONVENTION §5）。
DEPRECATED_RELATIONSHIPS = {
    "PROHIBITED": "MUST_AVOID",
    "PREFERS": "REQUIRES",
    "EMERGENCY_CONTACT": "HAS_KEY_PERSON",
    "RELATES_TO": "IN_CONTEXT",
    "HAS_GUARDIAN": "HAS_LEGAL_REP",
    "HOLDS": "HAS_CERTIFICATE",
}

# =============================================================================
# 列挙値の定義
# =============================================================================

ENUM_VALUES = {
    "riskLevel": {"LifeThreatening", "Panic", "Discomfort"},
    # 訂正（2026-07-12・DRIFT-05）: 旧定義は High/Medium/Low を含んでいたが、
    # これは priority の値域との混同。effectiveness の正式値は SCHEMA_CONVENTION
    # §7.2 の4値のみ。priority の検証は同時に新設した。
    "effectiveness": {"Effective", "Ineffective", "Neutral", "Unknown"},
    "priority": {"High", "Medium", "Low"},
    "emotion": {"Joy", "Anger", "Sadness", "Fear", "Surprise", "Disgust", "Calm", "Anxiety", "Confusion", "Neutral"},
    # Monitoring: Condition の「経過観察中」など、継続監視状態（P2 / 2026-07 追加）
    "status": {"Active", "Inactive", "Pending", "Completed", "Suspended", "Monitoring"},
}

# 安全クリティカルな riskLevel の別名 → 正規値（小文字キーで照合）。
# 誤入力による禁忌の優先度低下を防ぐ。ここに無い値は補正せず警告する
# （安全に関わる値を勝手に推測・捏造しない）。
RISK_LEVEL_ALIASES = {
    "lifethreatening": "LifeThreatening",
    "life_threatening": "LifeThreatening",
    "life-threatening": "LifeThreatening",
    "生命に関わる": "LifeThreatening",
    "生命の危険": "LifeThreatening",
    "致命的": "LifeThreatening",
    "critical": "LifeThreatening",
    "panic": "Panic",
    "パニック": "Panic",
    "discomfort": "Discomfort",
    "不快": "Discomfort",
    "ストレス": "Discomfort",
    # 汎用の高/中/低スケール。CLAUDE.md の緊急提示順（LifeThreatening → Panic →
    # Discomfort）に沿って対応づける。narrative-extractor / Gemini が段階表現で
    # 出力した場合に安全側の正規値へ寄せる。ここに無い値は補正せず警告する。
    "高": "LifeThreatening",
    "中": "Panic",
    "低": "Discomfort",
    "high": "LifeThreatening",
    "medium": "Panic",
    "low": "Discomfort",
}


def normalize_risk_level(value: str) -> str:
    """riskLevel の別名を正規値に補正する。既に正規値ならそのまま返す。"""
    if not isinstance(value, str):
        return value
    if value in ENUM_VALUES["riskLevel"]:
        return value
    return RISK_LEVEL_ALIASES.get(value.strip().lower(), value)

# =============================================================================
# プロパティ名変換 (snake_case → camelCase)
# =============================================================================

# ServiceProvider レガシー名 → 正式名
LEGACY_PROPERTY_MAP = {
    "office_name": "name",
    "corp_name": "corporateName",
    "service_type": "serviceType",
    "office_number": "wamnetId",
    "closed_days": "closedDays",
    "hours_weekday": "hoursWeekday",
    "updated_at": "updatedAt",
}

# 汎用 snake_case → camelCase 変換で既知のマッピング
KNOWN_PROPERTY_MAP = {
    "blood_type": "bloodType",
    "risk_level": "riskLevel",
    "next_renewal_date": "nextRenewalDate",
    "client_id": "clientId",
    "display_code": "displayCode",
    "diagnosed_date": "diagnosedDate",
    "diagnosis_date": "diagnosisDate",
    "start_date": "startDate",
    "end_date": "endDate",
    "issued_date": "issuedDate",
    "discovered_date": "discoveredDate",
    "current_status": "currentStatus",
    "case_number": "caseNumber",
    "trigger_tag": "triggerTag",
    "next_action": "nextAction",
    "file_path": "filePath",
    "mime_type": "mimeType",
    "text_embedding": "textEmbedding",
    "summary_embedding": "summaryEmbedding",
    "target_type": "targetType",
    "target_name": "targetName",
    "client_name": "clientName",
    "user_name": "userName",
    "feedback_id": "feedbackId",
    "wamnet_id": "wamnetId",
    "corporate_name": "corporateName",
    "recipient_condition": "recipientCondition",
    "money_management": "moneyManagement",
}

# camelCase として正しいプロパティ名のセット (変換不要)
_CAMEL_CASE_PATTERN = re.compile(r"^[a-z][a-zA-Z0-9]*$")
_SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")


def _snake_to_camel(name: str) -> str:
    """snake_case を camelCase に汎用変換する"""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def normalize_property_name(name: str) -> str:
    """
    プロパティ名を camelCase に正規化する。

    1. LEGACY_PROPERTY_MAP / KNOWN_PROPERTY_MAP に完全一致 → マッピング値を返す
    2. snake_case パターンに一致 → camelCase に自動変換
    3. それ以外 → そのまま返す (name, dob 等の単一語)
    """
    # 既知のマッピング (完全一致)
    if name in LEGACY_PROPERTY_MAP:
        return LEGACY_PROPERTY_MAP[name]
    if name in KNOWN_PROPERTY_MAP:
        return KNOWN_PROPERTY_MAP[name]

    # 既に camelCase or 単一語 → そのまま
    if _CAMEL_CASE_PATTERN.match(name) or not _SNAKE_CASE_PATTERN.match(name):
        return name

    # snake_case → camelCase 汎用変換
    converted = _snake_to_camel(name)
    _log(f"プロパティ名を自動変換: {name} → {converted}")
    return converted


def normalize_properties(props: dict, label: str | None = None) -> dict:
    """
    プロパティ辞書のキーを camelCase に正規化する。
    値が変わることはない。キーの重複が発生した場合は新しい値で上書き。
    """
    normalized = {}
    for key, value in props.items():
        new_key = normalize_property_name(key)
        if new_key != key:
            _log(f"[{label or '?'}] プロパティ変換: {key} → {new_key}")
        normalized[new_key] = value
    return normalized


# =============================================================================
# バリデーション関数
# =============================================================================

def validate_node_label(label: str) -> tuple[bool, str]:
    """
    ノードラベルが正式なラベル一覧に含まれるか検証する。

    Returns:
        (is_valid, message)
    """
    if label in VALID_NODE_LABELS:
        return True, ""
    return False, f"未知のノードラベル: '{label}'. 正式なラベル一覧に存在しません。"


def validate_relationship_type(rel_type: str) -> tuple[bool, str, str]:
    """
    リレーションタイプを検証し、廃止名は正式名に自動修正する。

    Returns:
        (is_valid, message, corrected_type)
    """
    if rel_type in VALID_RELATIONSHIP_TYPES:
        return True, "", rel_type

    if rel_type in DEPRECATED_RELATIONSHIPS:
        corrected = DEPRECATED_RELATIONSHIPS[rel_type]
        _log(f"廃止リレーションを自動修正: {rel_type} → {corrected}")
        return True, f"廃止リレーション '{rel_type}' を '{corrected}' に修正", corrected

    return False, f"未知のリレーションタイプ: '{rel_type}'", rel_type


def validate_enum_value(prop_name: str, value: str) -> tuple[bool, str]:
    """
    列挙値プロパティの値を検証する。

    Returns:
        (is_valid, message)
    """
    if prop_name not in ENUM_VALUES:
        return True, ""

    valid_values = ENUM_VALUES[prop_name]
    if value in valid_values:
        return True, ""

    return False, (
        f"'{prop_name}' の値 '{value}' は不正です。"
        f" 有効な値: {sorted(valid_values)}"
    )


def validate_and_normalize_graph(extracted_graph: dict) -> tuple[dict, list[str]]:
    """
    LLM が生成したグラフ構造全体を検証・正規化する。

    - ノードラベルの検証
    - プロパティ名の camelCase 変換
    - リレーションタイプの検証 (廃止名の自動修正含む)
    - 列挙値の検証

    Returns:
        (normalized_graph, warnings)
        warnings にはバリデーション警告メッセージのリストが入る。
        致命的エラー (未知のラベル等) も warnings に含まれるが、処理は続行する。
    """
    warnings = []
    normalized = {
        "nodes": [],
        "relationships": [],
    }

    # --- ノードの検証・正規化 ---
    for node in extracted_graph.get("nodes", []):
        label = node.get("label", "")
        props = node.get("properties", {})

        # ラベル検証
        is_valid, msg = validate_node_label(label)
        if not is_valid:
            warnings.append(msg)

        # プロパティ名の camelCase 正規化
        normalized_props = normalize_properties(props, label)

        # 安全クリティカルな riskLevel は別名を正規値へ補正してから検証する
        if isinstance(normalized_props.get("riskLevel"), str):
            corrected_risk = normalize_risk_level(normalized_props["riskLevel"])
            if corrected_risk != normalized_props["riskLevel"]:
                _log(f"riskLevel を補正: {normalized_props['riskLevel']} → {corrected_risk}")
                normalized_props["riskLevel"] = corrected_risk

        # 列挙値の検証
        for prop_name, value in normalized_props.items():
            if isinstance(value, str):
                is_valid, msg = validate_enum_value(prop_name, value)
                if not is_valid:
                    warnings.append(msg)

        normalized["nodes"].append({
            **node,
            "properties": normalized_props,
        })

    # --- リレーションシップの検証・正規化 ---
    for rel in extracted_graph.get("relationships", []):
        rel_type = rel.get("type", "")

        # リレーションタイプの検証 (廃止名の自動修正)
        is_valid, msg, corrected = validate_relationship_type(rel_type)
        if msg:
            warnings.append(msg)

        # リレーションプロパティの camelCase 正規化
        rel_props = rel.get("properties", {})
        normalized_props = normalize_properties(rel_props, f"rel:{corrected}")

        normalized["relationships"].append({
            **rel,
            "type": corrected,
            "properties": normalized_props,
        })

    if warnings:
        for w in warnings:
            _log(w, "WARN")

    return normalized, warnings
