"""
エコマップ生成スキル - Cypherクエリテンプレート
4種類のエコマップ用クエリを提供
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class EcomapTemplate:
    """エコマップテンプレート定義"""
    name: str
    description: str
    query: str
    use_case: str


# =============================================================================
# テンプレート定義
# =============================================================================

TEMPLATES: Dict[str, EcomapTemplate] = {

    # -------------------------------------------------------------------------
    # 1. 全体像エコマップ（デフォルト）
    # -------------------------------------------------------------------------
    "full_view": EcomapTemplate(
        name="全体像エコマップ",
        description="クライアントを中心に、すべての関係者・機関を表示",
        use_case="包括的な情報確認、初回面談時の全体把握",
        query="""
MATCH path = (c:Client {name: $client_name})-[*1..2]-()
RETURN path
LIMIT 100
"""
    ),

    # -------------------------------------------------------------------------
    # 2. 支援会議用エコマップ
    # -------------------------------------------------------------------------
    "support_meeting": EcomapTemplate(
        name="支援会議用エコマップ",
        description="ケース会議で使用する、支援関係に焦点を当てたビュー",
        use_case="サービス担当者会議、モニタリング会議",
        query="""
MATCH (c:Client {name: $client_name})
OPTIONAL MATCH (c)-[:PREFERS|REQUIRES]->(cp:CarePreference)
OPTIONAL MATCH (c)-[kp_rel:EMERGENCY_CONTACT|HAS_KEY_PERSON]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(cert:Certificate)
OPTIONAL MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c)
WHERE log.date >= date() - duration({days: 30})
RETURN c, cp, kp, kp_rel, cert, s, log
"""
    ),

    # -------------------------------------------------------------------------
    # 3. 緊急時体制エコマップ
    # -------------------------------------------------------------------------
    "emergency": EcomapTemplate(
        name="緊急時体制エコマップ",
        description="Safety First - 緊急時に必要な情報のみ（禁忌事項最優先）",
        use_case="緊急対応時、新規支援者への引き継ぎ初期",
        query="""
MATCH (c:Client {name: $client_name})
OPTIONAL MATCH (c)-[:PROHIBITED|MUST_AVOID]->(ng:NgAction)
OPTIONAL MATCH (c)-[:PREFERS|REQUIRES]->(cp:CarePreference)
WHERE cp.priority = 'High'
OPTIONAL MATCH (c)-[kp_rel:EMERGENCY_CONTACT|HAS_KEY_PERSON]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:HAS_GUARDIAN|HAS_LEGAL_REP]->(g:Guardian)
OPTIONAL MATCH (c)-[:TREATED_AT]->(h:Hospital)
RETURN c, ng, cp, kp, kp_rel, g, h
ORDER BY
  CASE ng.riskLevel
    WHEN 'LifeThreatening' THEN 1
    WHEN 'Panic' THEN 2
    WHEN 'Discomfort' THEN 3
    ELSE 4
  END,
  coalesce(kp_rel.rank, kp_rel.priority, 99)
"""
    ),

    # -------------------------------------------------------------------------
    # 4. 引き継ぎ用エコマップ
    # -------------------------------------------------------------------------
    "handover": EcomapTemplate(
        name="引き継ぎ用エコマップ",
        description="担当者交代時に使用する包括的情報（履歴含む）",
        use_case="担当者変更、事業所変更時の引き継ぎ",
        query="""
MATCH (c:Client {name: $client_name})
// 基本関係
OPTIONAL MATCH (c)-[:PROHIBITED|MUST_AVOID]->(ng:NgAction)
OPTIONAL MATCH (c)-[:PREFERS|REQUIRES]->(cp:CarePreference)
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(cert:Certificate)
OPTIONAL MATCH (c)-[kp_rel:EMERGENCY_CONTACT|HAS_KEY_PERSON]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:HAS_GUARDIAN|HAS_LEGAL_REP]->(g:Guardian)
OPTIONAL MATCH (c)-[:TREATED_AT]->(h:Hospital)
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(cond:Condition)
OPTIONAL MATCH (c)-[:HAS_HISTORY]->(hist:LifeHistory)
OPTIONAL MATCH (c)-[:HAS_WISH]->(w:Wish)
// 支援記録（直近50件）
OPTIONAL MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c)
WITH c, ng, cp, cert, kp, kp_rel, g, h, cond, hist, w, s, log
ORDER BY log.date DESC
LIMIT 50
RETURN c, ng, cp, cert, kp, kp_rel, g, h, cond, hist, w, s, log
"""
    ),
}


# =============================================================================
# ヘルパー関数
# =============================================================================

def get_template(template_name: str) -> Optional[EcomapTemplate]:
    """
    テンプレートを取得

    Args:
        template_name: テンプレート名（full_view, support_meeting, emergency, handover）

    Returns:
        EcomapTemplateオブジェクト、見つからない場合はNone
    """
    return TEMPLATES.get(template_name)


def get_query(template_name: str, client_name: str) -> Optional[str]:
    """
    クライアント名を埋め込んだクエリを取得

    Args:
        template_name: テンプレート名
        client_name: クライアント名

    Returns:
        実行可能なCypherクエリ文字列
    """
    template = get_template(template_name)
    if not template:
        return None

    # Neo4jブラウザ用にパラメータを直接埋め込んだクエリを生成
    return template.query.replace("$client_name", f"'{client_name}'")


def get_parameterized_query(template_name: str) -> Optional[str]:
    """
    パラメータ付きクエリを取得（プログラムから実行する場合）

    Args:
        template_name: テンプレート名

    Returns:
        パラメータ付きCypherクエリ文字列
    """
    template = get_template(template_name)
    return template.query if template else None


def list_templates() -> Dict[str, str]:
    """
    利用可能なテンプレート一覧を取得

    Returns:
        {テンプレート名: 説明} の辞書
    """
    return {name: t.description for name, t in TEMPLATES.items()}


def get_template_info(template_name: str) -> Optional[Dict]:
    """
    テンプレートの詳細情報を取得

    Args:
        template_name: テンプレート名

    Returns:
        テンプレート情報の辞書
    """
    template = get_template(template_name)
    if not template:
        return None

    return {
        "name": template.name,
        "description": template.description,
        "use_case": template.use_case,
        "query": template.query
    }


# =============================================================================
# 追加クエリ（分析・統計用）
# =============================================================================

ANALYSIS_QUERIES = {

    # リスクレベル別禁忌事項
    "ng_by_risk": """
MATCH (c:Client {name: $client_name})-[:PROHIBITED|MUST_AVOID]->(ng:NgAction)
RETURN ng.riskLevel as リスクレベル,
       ng.action as 禁忌事項,
       ng.reason as 理由
ORDER BY
  CASE ng.riskLevel
    WHEN 'LifeThreatening' THEN 1
    WHEN 'Panic' THEN 2
    WHEN 'Discomfort' THEN 3
    ELSE 4
  END
""",

    # カテゴリ別推奨ケア
    "care_by_category": """
MATCH (c:Client {name: $client_name})-[:PREFERS|REQUIRES]->(cp:CarePreference)
RETURN cp.category as カテゴリ,
       cp.instruction as 具体的方法,
       cp.priority as 優先度
ORDER BY
  CASE cp.priority
    WHEN 'High' THEN 1
    WHEN 'Medium' THEN 2
    WHEN 'Low' THEN 3
    ELSE 4
  END
""",

    # 優先度順緊急連絡先
    "emergency_contacts": """
MATCH (c:Client {name: $client_name})-[r:EMERGENCY_CONTACT|HAS_KEY_PERSON]->(kp:KeyPerson)
RETURN kp.name as 氏名,
       kp.relationship as 続柄,
       kp.phone as 電話番号,
       coalesce(r.rank, r.priority) as 優先順位
ORDER BY coalesce(r.rank, r.priority, 99)
""",

    # 効果的だった支援パターン
    "effective_patterns": """
MATCH (c:Client {name: $client_name})<-[:ABOUT]-(log:SupportLog)
WHERE log.effectiveness = 'Effective'
WITH log.situation as 状況, log.action as 対応, count(*) as 頻度
WHERE 頻度 >= 2
RETURN 状況, 対応, 頻度
ORDER BY 頻度 DESC
""",

    # 更新期限が近い証明書
    "upcoming_renewals": """
MATCH (c:Client {name: $client_name})-[:HAS_CERTIFICATE]->(cert:Certificate)
WHERE cert.nextRenewalDate <= date() + duration({months: 3})
RETURN cert.type as 種別,
       cert.grade as 等級,
       cert.nextRenewalDate as 更新期限,
       duration.between(date(), cert.nextRenewalDate).days as 残日数
ORDER BY cert.nextRenewalDate
""",
}


def get_analysis_query(query_name: str, client_name: str) -> Optional[str]:
    """
    分析用クエリを取得（クライアント名埋め込み済み）

    Args:
        query_name: クエリ名
        client_name: クライアント名

    Returns:
        実行可能なCypherクエリ文字列
    """
    query = ANALYSIS_QUERIES.get(query_name)
    if not query:
        return None

    return query.replace("$client_name", f"'{client_name}'")


# =============================================================================
# CLI実行
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使用法: python cypher_templates.py <テンプレート名> [クライアント名]")
        print("\n利用可能なテンプレート:")
        for name, desc in list_templates().items():
            print(f"  {name}: {desc}")
        sys.exit(1)

    template_name = sys.argv[1]
    client_name = sys.argv[2] if len(sys.argv) > 2 else "クライアント名"

    query = get_query(template_name, client_name)
    if query:
        info = get_template_info(template_name)
        print(f"# {info['name']}")
        print(f"# 用途: {info['use_case']}")
        print(f"# {info['description']}")
        print()
        print(query)
    else:
        print(f"エラー: テンプレート '{template_name}' が見つかりません")
        sys.exit(1)
