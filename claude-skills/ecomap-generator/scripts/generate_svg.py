"""
エコマップ生成スキル - SVG形式エコマップ生成
Neo4jからデータを取得し、印刷可能なSVGエコマップを生成
"""

import math
from datetime import date
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

# generate_mermaid.pyからデータ取得関数をインポート
from generate_mermaid import fetch_client_data, get_sample_data, HAS_NEO4J


# =============================================================================
# 設定
# =============================================================================

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600
CENTER_X = CANVAS_WIDTH // 2
CENTER_Y = CANVAS_HEIGHT // 2

NODE_COLORS = {
    "Client": {"fill": "#e1f5fe", "stroke": "#01579b", "text": "#01579b"},
    "NgAction": {"fill": "#ffcdd2", "stroke": "#c62828", "text": "#c62828"},
    "CarePreference": {"fill": "#c8e6c9", "stroke": "#2e7d32", "text": "#2e7d32"},
    "KeyPerson": {"fill": "#fff3e0", "stroke": "#e65100", "text": "#e65100"},
    "Guardian": {"fill": "#f3e5f5", "stroke": "#6a1b9a", "text": "#6a1b9a"},
    "Certificate": {"fill": "#e0e0e0", "stroke": "#424242", "text": "#424242"},
    "Hospital": {"fill": "#e3f2fd", "stroke": "#1565c0", "text": "#1565c0"},
    "Condition": {"fill": "#fff8e1", "stroke": "#f57f17", "text": "#f57f17"},
}

NODE_ICONS = {
    "Client": "👤",
    "NgAction": "⛔",
    "CarePreference": "✓",
    "KeyPerson": "📞",
    "Guardian": "⚖️",
    "Certificate": "📄",
    "Hospital": "🏥",
    "Condition": "🔍",
}

LAYER_ORDER = [
    "NgAction",
    "CarePreference",
    "KeyPerson",
    "Guardian",
    "Hospital",
    "Certificate",
    "Condition",
]


# =============================================================================
# データ構造
# =============================================================================

@dataclass
class SvgNode:
    """SVGノード"""
    id: str
    label: str
    node_type: str
    x: float = 0
    y: float = 0
    width: float = 120
    height: float = 40

    @property
    def colors(self) -> Dict[str, str]:
        return NODE_COLORS.get(self.node_type, NODE_COLORS["Client"])

    @property
    def icon(self) -> str:
        return NODE_ICONS.get(self.node_type, "")


@dataclass
class SvgEdge:
    """SVGエッジ"""
    source: SvgNode
    target: SvgNode
    label: str = ""


# =============================================================================
# レイアウト計算
# =============================================================================

def calculate_radial_layout(
    nodes: List[SvgNode],
    center_x: float,
    center_y: float,
    layer_spacing: float = 100
) -> None:
    """放射状レイアウトを計算"""
    groups: Dict[str, List[SvgNode]] = {}

    for node in nodes:
        if node.node_type == "Client":
            node.x = center_x
            node.y = center_y
        else:
            if node.node_type not in groups:
                groups[node.node_type] = []
            groups[node.node_type].append(node)

    layer = 1
    angle_offset = 0

    for node_type in LAYER_ORDER:
        if node_type not in groups:
            continue

        group_nodes = groups[node_type]
        n = len(group_nodes)
        if n == 0:
            continue

        radius = layer_spacing * layer
        angle_step = (2 * math.pi) / max(n, 6)
        start_angle = angle_offset

        for i, node in enumerate(group_nodes):
            angle = start_angle + i * angle_step
            node.x = center_x + radius * math.cos(angle)
            node.y = center_y + radius * math.sin(angle)

        if node_type in ["NgAction", "CarePreference"]:
            layer += 1
            angle_offset += math.pi / 12
        elif node_type in ["KeyPerson", "Guardian"]:
            layer += 0.5
            angle_offset += math.pi / 8


# =============================================================================
# SVG生成
# =============================================================================

def generate_svg_node(node: SvgNode) -> str:
    """ノードのSVG要素を生成"""
    colors = node.colors
    icon = node.icon

    label = node.label
    if len(label) > 15:
        label = label[:12] + "..."

    if node.node_type == "Client":
        rx, ry = 60, 40
        font_size = 16
    else:
        rx, ry = node.width / 2, node.height / 2
        font_size = 11

    return f'''
    <g transform="translate({node.x}, {node.y})">
        <ellipse rx="{rx}" ry="{ry}"
                 fill="{colors['fill']}"
                 stroke="{colors['stroke']}"
                 stroke-width="2"/>
        <text y="-5" text-anchor="middle"
              fill="{colors['text']}"
              font-size="{font_size}"
              font-family="sans-serif">
            {icon} {label}
        </text>
        <text y="12" text-anchor="middle"
              fill="#666"
              font-size="9"
              font-family="sans-serif">
            {node.node_type}
        </text>
    </g>'''


def generate_svg_edge(edge: SvgEdge) -> str:
    """エッジのSVG要素を生成"""
    x1, y1 = edge.source.x, edge.source.y
    x2, y2 = edge.target.x, edge.target.y

    angle = math.atan2(y2 - y1, x2 - x1)

    r1 = 50 if edge.source.node_type == "Client" else 40
    r2 = 40

    x1_adj = x1 + r1 * math.cos(angle)
    y1_adj = y1 + r1 * math.sin(angle)
    x2_adj = x2 - r2 * math.cos(angle)
    y2_adj = y2 - r2 * math.sin(angle)

    mid_x = (x1_adj + x2_adj) / 2
    mid_y = (y1_adj + y2_adj) / 2

    edge_svg = f'''
    <line x1="{x1_adj}" y1="{y1_adj}"
          x2="{x2_adj}" y2="{y2_adj}"
          stroke="#999" stroke-width="1.5"
          marker-end="url(#arrowhead)"/>'''

    if edge.label:
        edge_svg += f'''
    <text x="{mid_x}" y="{mid_y - 5}"
          text-anchor="middle"
          fill="#666"
          font-size="9"
          font-family="sans-serif">
        {edge.label}
    </text>'''

    return edge_svg


def generate_legend() -> str:
    """凡例を生成"""
    legend_items = [
        ("NgAction", "禁忌事項"),
        ("CarePreference", "推奨ケア"),
        ("KeyPerson", "キーパーソン"),
        ("Guardian", "後見人"),
        ("Hospital", "医療機関"),
        ("Certificate", "手帳"),
        ("Condition", "特性"),
    ]

    legend_svg = '<g transform="translate(20, 20)">'
    legend_svg += '<text x="0" y="0" font-size="12" font-weight="bold" fill="#333">凡例</text>'

    for i, (node_type, label) in enumerate(legend_items):
        y = 20 + i * 20
        colors = NODE_COLORS.get(node_type, NODE_COLORS["Client"])
        icon = NODE_ICONS.get(node_type, "")

        legend_svg += f'''
        <rect x="0" y="{y - 10}" width="15" height="15"
              fill="{colors['fill']}" stroke="{colors['stroke']}" stroke-width="1"/>
        <text x="20" y="{y}" font-size="10" fill="#333">{icon} {label}</text>'''

    legend_svg += '</g>'
    return legend_svg


def generate_svg(
    title: str,
    nodes: List[SvgNode],
    edges: List[SvgEdge],
    include_legend: bool = True
) -> str:
    """完全なSVGドキュメントを生成"""
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}"
     width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}">

    <defs>
        <marker id="arrowhead" markerWidth="10" markerHeight="7"
                refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#999"/>
        </marker>
    </defs>

    <rect width="100%" height="100%" fill="#fafafa"/>

    <text x="{CANVAS_WIDTH / 2}" y="30"
          text-anchor="middle"
          font-size="18"
          font-weight="bold"
          fill="#333"
          font-family="sans-serif">
        {title}
    </text>

    <text x="{CANVAS_WIDTH - 20}" y="{CANVAS_HEIGHT - 10}"
          text-anchor="end"
          font-size="9"
          fill="#999"
          font-family="sans-serif">
        生成日: {date.today().isoformat()}
    </text>
'''

    for edge in edges:
        svg_content += generate_svg_edge(edge)

    for node in nodes:
        svg_content += generate_svg_node(node)

    if include_legend:
        svg_content += generate_legend()

    svg_content += '\n</svg>'

    return svg_content


# =============================================================================
# メイン処理
# =============================================================================

def generate_svg_ecomap(
    client_name: str,
    template: str = "full_view",
    include_legend: bool = True,
    output_path: Optional[str] = None
) -> str:
    """クライアントのエコマップをSVG形式で生成"""
    data = fetch_client_data(client_name, template)

    nodes: List[SvgNode] = []
    edges: List[SvgEdge] = []

    # クライアントノード（中心）
    client_node = SvgNode(
        id="client",
        label=data["client"]["name"],
        node_type="Client"
    )
    nodes.append(client_node)

    node_id = 0

    def add_nodes(data_key: str, node_type: str, label_func, edge_label: str = ""):
        nonlocal node_id
        items = data.get(data_key, [])

        for item in items:
            label = label_func(item)
            if not label:
                continue

            node = SvgNode(
                id=f"{node_type}_{node_id}",
                label=label,
                node_type=node_type
            )
            nodes.append(node)
            edges.append(SvgEdge(source=client_node, target=node, label=edge_label))
            node_id += 1

    # 禁忌事項
    if template in ["full_view", "emergency", "handover"]:
        add_nodes("ngActions", "NgAction", lambda x: x.get("action", ""), "禁忌")

    # 推奨ケア
    if template in ["full_view", "support_meeting", "emergency", "handover"]:
        if template == "emergency":
            filtered = [cp for cp in data.get("carePreferences", []) if cp.get("priority") == "High"]
            data["carePreferences_filtered"] = filtered
            add_nodes("carePreferences_filtered", "CarePreference",
                     lambda x: f"{x.get('category', '')}: {x.get('instruction', '')}"[:30], "推奨")
        else:
            add_nodes("carePreferences", "CarePreference",
                     lambda x: f"{x.get('category', '')}: {x.get('instruction', '')}"[:30], "推奨")

    # キーパーソン
    if template in ["full_view", "support_meeting", "emergency", "handover"]:
        add_nodes("keyPersons", "KeyPerson",
                 lambda x: f"{x.get('name', '')}({x.get('relationship', '')})", "連絡")

    # 後見人
    if template in ["full_view", "emergency", "handover"]:
        add_nodes("guardians", "Guardian", lambda x: x.get("name", ""), "後見")

    # 手帳
    if template in ["full_view", "support_meeting", "handover"]:
        add_nodes("certificates", "Certificate",
                 lambda x: f"{x.get('type', '')} {x.get('grade', '')}", "手帳")

    # 医療機関
    if template in ["full_view", "emergency", "handover"]:
        add_nodes("hospitals", "Hospital", lambda x: x.get("name", ""), "医療")

    # 特性
    if template in ["full_view", "handover"]:
        add_nodes("conditions", "Condition", lambda x: x.get("name", ""), "特性")

    # レイアウト計算
    calculate_radial_layout(nodes, CENTER_X, CENTER_Y)

    # タイトル
    template_names = {
        "full_view": "全体像",
        "support_meeting": "支援会議用",
        "emergency": "緊急時体制",
        "handover": "引き継ぎ用",
    }
    title = f"{client_name}のエコマップ（{template_names.get(template, template)}）"

    # SVG生成
    svg_content = generate_svg(title, nodes, edges, include_legend)

    # ファイル保存
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"保存しました: {output_path}")

    return svg_content


# =============================================================================
# CLI実行
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SVG形式のエコマップを生成")
    parser.add_argument("client_name", help="クライアント名")
    parser.add_argument("-t", "--template", default="full_view",
                        choices=["full_view", "support_meeting", "emergency", "handover"],
                        help="テンプレート名")
    parser.add_argument("-o", "--output", help="出力ファイルパス")
    parser.add_argument("--no-legend", action="store_true", help="凡例を非表示")

    args = parser.parse_args()

    output_path = args.output
    if not output_path:
        output_dir = Path(__file__).parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / f"{args.client_name}_ecomap_{args.template}.svg")

    generate_svg_ecomap(
        args.client_name,
        template=args.template,
        include_legend=not args.no_legend,
        output_path=output_path
    )
