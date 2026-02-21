"""
エコマップ生成スキル - Mermaid形式エコマップ生成
Neo4jからデータを取得し、Mermaid記法のエコマップを生成
"""

import os
import sys
from datetime import date
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


# =============================================================================
# Neo4j接続設定
# =============================================================================

# .envファイルを探す順序:
# 1. カレントディレクトリ
# 2. ecomap-generatorディレクトリ
# 3. nest-supportプロジェクトルート
ENV_SEARCH_PATHS = [
    Path.cwd() / ".env",
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent.parent.parent.parent / ".env",
]

for env_path in ENV_SEARCH_PATHS:
    if env_path.exists():
        load_dotenv(env_path)
        break

# Neo4jドライバー（シングルトン）
_driver = None

def get_driver():
    """Neo4jドライバーを取得"""
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        _driver = GraphDatabase.driver(uri, auth=(user, password))
    return _driver


def run_query(query: str, params: dict = None) -> List[dict]:
    """Cypherクエリを実行"""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


# Neo4j接続テスト
HAS_NEO4J = False
try:
    driver = get_driver()
    driver.verify_connectivity()
    HAS_NEO4J = True
    print("✓ Neo4jに接続しました", file=sys.stderr)
except Exception as e:
    print(f"警告: Neo4j接続に失敗: {e}", file=sys.stderr)
    print("サンプルデータで動作します。", file=sys.stderr)


# =============================================================================
# データ構造
# =============================================================================

@dataclass
class EcomapNode:
    """エコマップのノード"""
    id: str
    label: str
    node_type: str
    properties: Dict = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class EcomapEdge:
    """エコマップのエッジ"""
    source_id: str
    target_id: str
    label: str
    properties: Dict = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


# =============================================================================
# ノードタイプ別のスタイル定義
# =============================================================================

NODE_STYLES = {
    "Client": {"shape": "([{label}])", "style": "fill:#e1f5fe,stroke:#01579b"},
    "NgAction": {"shape": "[/{label}/]", "style": "fill:#ffcdd2,stroke:#c62828"},
    "CarePreference": {"shape": "[{label}]", "style": "fill:#c8e6c9,stroke:#2e7d32"},
    "KeyPerson": {"shape": "(({label}))", "style": "fill:#fff3e0,stroke:#e65100"},
    "Guardian": {"shape": "[({label})]", "style": "fill:#f3e5f5,stroke:#6a1b9a"},
    "Certificate": {"shape": "[{label}]", "style": "fill:#e0e0e0,stroke:#424242"},
    "Hospital": {"shape": "[{label}]", "style": "fill:#e3f2fd,stroke:#1565c0"},
    "Condition": {"shape": "{{{label}}}", "style": "fill:#fff8e1,stroke:#f57f17"},
    "SupportLog": {"shape": ">{label}]", "style": "fill:#f1f8e9,stroke:#558b2f"},
    "Supporter": {"shape": "({label})", "style": "fill:#e8eaf6,stroke:#3949ab"},
}

EDGE_LABELS = {
    "PROHIBITED": "⛔禁忌",
    "MUST_AVOID": "⛔禁忌",
    "PREFERS": "✓推奨",
    "REQUIRES": "✓推奨",
    "EMERGENCY_CONTACT": "📞緊急",
    "HAS_KEY_PERSON": "👤キーパーソン",
    "HAS_GUARDIAN": "⚖後見人",
    "HAS_LEGAL_REP": "⚖後見人",
    "HAS_CERTIFICATE": "📄手帳",
    "TREATED_AT": "🏥医療",
    "HAS_CONDITION": "特性",
    "LOGGED": "記録",
    "ABOUT": "対象",
    "HAS_WISH": "💭願い",
    "HAS_HISTORY": "📖履歴",
}


# =============================================================================
# Mermaid生成
# =============================================================================

def sanitize_label(label: str) -> str:
    """Mermaid用にラベルをサニタイズ"""
    label = label.replace('\"', "'")
    label = label.replace("[", "(")
    label = label.replace("]", ")")
    label = label.replace("{", "(")
    label = label.replace("}", ")")
    label = label.replace("<", "＜")
    label = label.replace(">", "＞")
    label = label.replace("|", "｜")
    if len(label) > 30:
        label = label[:27] + "..."
    return label


def generate_node_id(node_type: str, index: int) -> str:
    """ノードIDを生成"""
    prefix = {
        "Client": "C",
        "NgAction": "NG",
        "CarePreference": "CP",
        "KeyPerson": "KP",
        "Guardian": "G",
        "Certificate": "CERT",
        "Hospital": "H",
        "Condition": "COND",
        "SupportLog": "LOG",
        "Supporter": "SUP",
        "Wish": "W",
        "LifeHistory": "HIST",
    }.get(node_type, "N")
    return f"{prefix}{index}"


def get_node_shape(node_type: str, label: str) -> str:
    """ノードタイプに応じた形状を返す"""
    style = NODE_STYLES.get(node_type, {"shape": "[{label}]"})
    return style["shape"].format(label=sanitize_label(label))


def get_edge_label(rel_type: str) -> str:
    """リレーションタイプに応じたラベルを返す"""
    return EDGE_LABELS.get(rel_type, rel_type)


class MermaidEcomapGenerator:
    """Mermaid形式のエコマップを生成するクラス"""

    def __init__(self):
        self.nodes: Dict[str, EcomapNode] = {}
        self.edges: List[EcomapEdge] = []
        self.node_counter: Dict[str, int] = {}

    def add_node(self, node_type: str, label: str, properties: Dict = None) -> str:
        """ノードを追加し、IDを返す"""
        for node_id, node in self.nodes.items():
            if node.label == label and node.node_type == node_type:
                return node_id

        self.node_counter[node_type] = self.node_counter.get(node_type, 0) + 1
        node_id = generate_node_id(node_type, self.node_counter[node_type])
        self.nodes[node_id] = EcomapNode(
            id=node_id,
            label=label,
            node_type=node_type,
            properties=properties or {}
        )
        return node_id

    def add_edge(self, source_id: str, target_id: str, rel_type: str, properties: Dict = None):
        """エッジを追加"""
        for edge in self.edges:
            if edge.source_id == source_id and edge.target_id == target_id:
                return

        self.edges.append(EcomapEdge(
            source_id=source_id,
            target_id=target_id,
            label=get_edge_label(rel_type),
            properties=properties or {}
        ))

    def generate(self, title: str = "エコマップ", direction: str = "TD") -> str:
        """Mermaid形式の文字列を生成"""
        lines = [f"graph {direction}"]

        for node_id, node in self.nodes.items():
            shape = get_node_shape(node.node_type, node.label)
            lines.append(f"    {node_id}{shape}")

        for edge in self.edges:
            if edge.label:
                lines.append(f"    {edge.source_id} -->|{edge.label}| {edge.target_id}")
            else:
                lines.append(f"    {edge.source_id} --> {edge.target_id}")

        lines.append("")
        lines.append("    %% スタイル定義")
        for node_id, node in self.nodes.items():
            style_info = NODE_STYLES.get(node.node_type)
            if style_info:
                lines.append(f"    style {node_id} {style_info['style']}")

        return "\n".join(lines)


# =============================================================================
# Neo4jからデータ取得
# =============================================================================

def fetch_client_data(client_name: str, template: str = "full_view") -> Dict:
    """Neo4jからクライアントデータを取得"""
    if not HAS_NEO4J:
        return get_sample_data(client_name)

    data = {
        "client": {"name": client_name},
        "ngActions": [],
        "carePreferences": [],
        "keyPersons": [],
        "guardians": [],
        "certificates": [],
        "hospitals": [],
        "conditions": [],
    }

    # 基本情報
    client_result = run_query("""
        MATCH (c:Client {name: $name})
        RETURN c.name as name, c.dob as dob, c.bloodType as bloodType
    """, {"name": client_name})

    if not client_result:
        print(f"警告: クライアント '{client_name}' が見つかりません", file=sys.stderr)
        return get_sample_data(client_name)

    data["client"] = client_result[0]

    # 禁忌事項
    data["ngActions"] = run_query("""
        MATCH (c:Client {name: $name})-[:PROHIBITED|MUST_AVOID]->(ng:NgAction)
        RETURN ng.action as action, ng.reason as reason, ng.riskLevel as riskLevel
        ORDER BY CASE ng.riskLevel
            WHEN 'LifeThreatening' THEN 1
            WHEN 'Panic' THEN 2
            ELSE 3 END
    """, {"name": client_name})

    # 推奨ケア
    data["carePreferences"] = run_query("""
        MATCH (c:Client {name: $name})-[:PREFERS|REQUIRES]->(cp:CarePreference)
        RETURN cp.category as category, cp.instruction as instruction, cp.priority as priority
    """, {"name": client_name})

    # キーパーソン
    data["keyPersons"] = run_query("""
        MATCH (c:Client {name: $name})-[r:EMERGENCY_CONTACT|HAS_KEY_PERSON]->(kp:KeyPerson)
        RETURN kp.name as name, kp.relationship as relationship, kp.phone as phone,
               coalesce(r.rank, r.priority) as priority
        ORDER BY coalesce(r.rank, r.priority, 99)
    """, {"name": client_name})

    # 後見人
    data["guardians"] = run_query("""
        MATCH (c:Client {name: $name})-[:HAS_GUARDIAN|HAS_LEGAL_REP]->(g:Guardian)
        RETURN g.name as name, g.type as type, g.phone as phone
    """, {"name": client_name})

    # 手帳
    data["certificates"] = run_query("""
        MATCH (c:Client {name: $name})-[:HAS_CERTIFICATE]->(cert:Certificate)
        RETURN cert.type as type, cert.grade as grade
    """, {"name": client_name})

    # 医療機関
    data["hospitals"] = run_query("""
        MATCH (c:Client {name: $name})-[:TREATED_AT]->(h:Hospital)
        RETURN h.name as name, h.specialty as specialty
    """, {"name": client_name})

    # 特性
    data["conditions"] = run_query("""
        MATCH (c:Client {name: $name})-[:HAS_CONDITION]->(cond:Condition)
        RETURN cond.name as name
    """, {"name": client_name})

    return data


def get_sample_data(client_name: str) -> Dict:
    """サンプルデータを返す"""
    return {
        "client": {"name": client_name},
        "ngActions": [
            {"action": "後ろから急に声をかける", "reason": "パニックを誘発", "riskLevel": "Panic"},
            {"action": "大きな音を出す", "reason": "聴覚過敏", "riskLevel": "Discomfort"},
        ],
        "carePreferences": [
            {"category": "パニック時", "instruction": "静かに見守り5分待つ", "priority": "High"},
        ],
        "keyPersons": [
            {"name": "山田花子", "relationship": "母", "priority": 1},
            {"name": "山田一郎", "relationship": "叔父", "priority": 2},
        ],
        "guardians": [],
        "certificates": [],
        "hospitals": [
            {"name": "〇〇病院", "specialty": "精神科"},
        ],
        "conditions": [],
    }


def generate_mermaid_ecomap(
    client_name: str,
    template: str = "full_view",
    direction: str = "TD"
) -> str:
    """クライアントのエコマップをMermaid形式で生成"""
    data = fetch_client_data(client_name, template)

    generator = MermaidEcomapGenerator()

    # クライアント（中心ノード）
    client_id = generator.add_node("Client", data["client"]["name"])

    # 禁忌事項
    if template in ["full_view", "emergency", "handover"]:
        for ng in data.get("ngActions", []):
            risk_label = {"LifeThreatening": "⚠️", "Panic": "🔴", "Discomfort": "🟡"}.get(ng.get("riskLevel"), "")
            label = f"{risk_label}{ng['action']}"
            ng_id = generator.add_node("NgAction", label)
            generator.add_edge(client_id, ng_id, "PROHIBITED")

    # 推奨ケア
    if template in ["full_view", "support_meeting", "emergency", "handover"]:
        for cp in data.get("carePreferences", []):
            if template == "emergency" and cp.get("priority") != "High":
                continue
            label = f"{cp.get('category', '')}: {cp['instruction']}"
            cp_id = generator.add_node("CarePreference", label)
            generator.add_edge(client_id, cp_id, "PREFERS")

    # キーパーソン
    if template in ["full_view", "support_meeting", "emergency", "handover"]:
        for kp in data.get("keyPersons", []):
            label = f"{kp['name']}({kp.get('relationship', '')})"
            kp_id = generator.add_node("KeyPerson", label)
            generator.add_edge(client_id, kp_id, "HAS_KEY_PERSON")

    # 後見人
    if template in ["full_view", "emergency", "handover"]:
        for g in data.get("guardians", []):
            label = f"{g['name']}({g.get('type', '後見人')})"
            g_id = generator.add_node("Guardian", label)
            generator.add_edge(client_id, g_id, "HAS_GUARDIAN")

    # 手帳
    if template in ["full_view", "support_meeting", "handover"]:
        for cert in data.get("certificates", []):
            label = f"{cert['type']} {cert.get('grade', '')}"
            cert_id = generator.add_node("Certificate", label)
            generator.add_edge(client_id, cert_id, "HAS_CERTIFICATE")

    # 医療機関
    if template in ["full_view", "emergency", "handover"]:
        for h in data.get("hospitals", []):
            label = f"{h['name']}({h.get('specialty', '')})"
            h_id = generator.add_node("Hospital", label)
            generator.add_edge(client_id, h_id, "TREATED_AT")

    # 特性
    if template in ["full_view", "handover"]:
        for cond in data.get("conditions", []):
            cond_id = generator.add_node("Condition", cond["name"])
            generator.add_edge(client_id, cond_id, "HAS_CONDITION")

    return generator.generate(direction=direction)


# =============================================================================
# CLI実行
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mermaid形式のエコマップを生成")
    parser.add_argument("client_name", help="クライアント名")
    parser.add_argument("-t", "--template", default="full_view",
                        choices=["full_view", "support_meeting", "emergency", "handover"],
                        help="テンプレート名")
    parser.add_argument("-d", "--direction", default="TD",
                        choices=["TD", "LR", "BT", "RL"],
                        help="グラフの方向")
    parser.add_argument("-o", "--output", help="出力ファイルパス")

    args = parser.parse_args()

    mermaid_content = generate_mermaid_ecomap(
        args.client_name,
        template=args.template,
        direction=args.direction
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(mermaid_content)
        print(f"保存しました: {args.output}")
    else:
        print(mermaid_content)
