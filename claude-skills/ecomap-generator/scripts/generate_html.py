"""
エコマップ生成スキル - HTML形式エコマップ生成
Neo4jからデータを取得し、Neo4j風のインタラクティブなHTMLエコマップを生成
外部CDNに依存せず、純粋なSVGで描画
"""

import math
import html as html_mod
from datetime import date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# generate_mermaid.pyからデータ取得関数をインポート
from generate_mermaid import fetch_client_data, get_sample_data, HAS_NEO4J


# =============================================================================
# 設定
# =============================================================================

CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 900

# Neo4j風カラーテーマ（ダークテーマ）
BG_COLOR = "#101020"
GRID_COLOR = "#1a1a2e"
TEXT_COLOR = "#c0c0d0"
EDGE_COLOR = "#505070"
EDGE_LABEL_COLOR = "#8888aa"

# ノードカテゴリの色定義
CATEGORY_STYLES = {
    "Client": {"bg": "#4C8BF5", "border": "#6CA0FF", "text": "#ffffff", "icon": "👤", "label": "本人"},
    "NgAction": {"bg": "#E53935", "border": "#FF5252", "text": "#ffffff", "icon": "⛔", "label": "禁忌事項"},
    "CarePreference": {"bg": "#43A047", "border": "#66BB6A", "text": "#ffffff", "icon": "✓", "label": "推奨ケア"},
    "KeyPerson": {"bg": "#FB8C00", "border": "#FFA726", "text": "#ffffff", "icon": "📞", "label": "キーパーソン"},
    "Guardian": {"bg": "#8E24AA", "border": "#AB47BC", "text": "#ffffff", "icon": "⚖️", "label": "後見人"},
    "Hospital": {"bg": "#1E88E5", "border": "#42A5F5", "text": "#ffffff", "icon": "🏥", "label": "医療機関"},
    "Certificate": {"bg": "#546E7A", "border": "#78909C", "text": "#ffffff", "icon": "📄", "label": "手帳"},
    "Condition": {"bg": "#F9A825", "border": "#FDD835", "text": "#333333", "icon": "🔍", "label": "特性"},
    "Supporter": {"bg": "#5C6BC0", "border": "#7986CB", "text": "#ffffff", "icon": "🤝", "label": "支援者"},
    "SupportLog": {"bg": "#66BB6A", "border": "#81C784", "text": "#ffffff", "icon": "📝", "label": "支援記録"},
}

EDGE_LABELS = {
    "PROHIBITED": "⛔禁忌",
    "MUST_AVOID": "⛔禁忌",
    "PREFERS": "推奨",
    "REQUIRES": "推奨",
    "EMERGENCY_CONTACT": "緊急連絡",
    "HAS_KEY_PERSON": "キーパーソン",
    "HAS_GUARDIAN": "後見人",
    "HAS_LEGAL_REP": "後見人",
    "HAS_CERTIFICATE": "手帳",
    "TREATED_AT": "医療",
    "HAS_CONDITION": "特性",
    "LOGGED": "記録",
    "ABOUT": "対象",
}

# カテゴリごとの配置セクター（角度範囲）
CATEGORY_SECTORS = {
    "NgAction": (-30, 30),
    "CarePreference": (30, 90),
    "KeyPerson": (90, 150),
    "Guardian": (150, 190),
    "Hospital": (190, 250),
    "Certificate": (250, 290),
    "Condition": (290, 330),
    "Supporter": (150, 210),
    "SupportLog": (210, 270),
}


# =============================================================================
# データ構造
# =============================================================================

@dataclass
class HtmlNode:
    """HTMLエコマップのノード"""
    id: str
    label: str
    node_type: str
    detail: str = ""
    x: float = 0.0
    y: float = 0.0
    radius: float = 28.0

    @property
    def style(self) -> Dict[str, str]:
        return CATEGORY_STYLES.get(self.node_type, CATEGORY_STYLES["Client"])


@dataclass
class HtmlEdge:
    """HTMLエコマップのエッジ"""
    source_id: str
    target_id: str
    label: str = ""
    rel_type: str = ""


# =============================================================================
# レイアウト計算
# =============================================================================

def calculate_layout(
    nodes: List[HtmlNode],
    center_x: float,
    center_y: float,
    base_radius: float = 200
) -> None:
    """カテゴリ別セクターに放射状配置"""
    # クライアントノードを中心に
    groups: Dict[str, List[HtmlNode]] = {}
    for node in nodes:
        if node.node_type == "Client":
            node.x = center_x
            node.y = center_y
            node.radius = 45
        else:
            groups.setdefault(node.node_type, []).append(node)

    # 各グループをセクターに配置
    for node_type, group_nodes in groups.items():
        sector = CATEGORY_SECTORS.get(node_type, (0, 360))
        n = len(group_nodes)
        if n == 0:
            continue

        start_deg, end_deg = sector
        # ノード数に応じてレイヤー（半径）を調整
        layer_count = math.ceil(n / 4)

        for i, node in enumerate(group_nodes):
            layer = i // 4
            idx_in_layer = i % 4
            nodes_in_this_layer = min(4, n - layer * 4)

            radius = base_radius + layer * 100

            if nodes_in_this_layer == 1:
                angle_deg = (start_deg + end_deg) / 2
            else:
                span = end_deg - start_deg
                margin = span * 0.1
                step = (span - 2 * margin) / max(nodes_in_this_layer - 1, 1)
                angle_deg = start_deg + margin + idx_in_layer * step

            angle_rad = math.radians(angle_deg)
            node.x = center_x + radius * math.cos(angle_rad)
            node.y = center_y + radius * math.sin(angle_rad)


# =============================================================================
# HTML/SVG生成
# =============================================================================

def escape(text: str) -> str:
    """HTML特殊文字をエスケープ"""
    return html_mod.escape(str(text)) if text else ""


def truncate(text: str, max_len: int = 20) -> str:
    """テキストを切り詰め"""
    if not text:
        return ""
    if len(text) > max_len:
        return text[:max_len - 2] + ".."
    return text


def generate_html_ecomap(
    client_name: str,
    template: str = "full_view",
    output_path: Optional[str] = None
) -> str:
    """クライアントのエコマップをHTML形式で生成"""
    data = fetch_client_data(client_name, template)

    nodes: List[HtmlNode] = []
    edges: List[HtmlEdge] = []
    node_map: Dict[str, HtmlNode] = {}
    node_counter = 0

    def add_node(node_type: str, label: str, detail: str = "") -> str:
        nonlocal node_counter
        node_id = f"n{node_counter}"
        node_counter += 1
        node = HtmlNode(id=node_id, label=label, node_type=node_type, detail=detail)
        nodes.append(node)
        node_map[node_id] = node
        return node_id

    def add_edge(source_id: str, target_id: str, rel_type: str):
        label = EDGE_LABELS.get(rel_type, rel_type)
        edges.append(HtmlEdge(source_id=source_id, target_id=target_id, label=label, rel_type=rel_type))

    # --- クライアントノード ---
    client_info = data.get("client", {})
    client_detail = f"名前: {client_info.get('name', client_name)}"
    if client_info.get("dob"):
        client_detail += f"\n生年月日: {client_info['dob']}"
    if client_info.get("bloodType"):
        client_detail += f"\n血液型: {client_info['bloodType']}"

    client_id = add_node("Client", client_info.get("name", client_name), client_detail)

    # --- 禁忌事項 ---
    if template in ["full_view", "emergency", "handover"]:
        for ng in data.get("ngActions", []):
            action = ng.get("action", "")
            if not action:
                continue
            risk = ng.get("riskLevel", "")
            reason = ng.get("reason", "")
            detail = f"禁忌: {action}"
            if risk:
                detail += f"\nリスク: {risk}"
            if reason:
                detail += f"\n理由: {reason}"
            nid = add_node("NgAction", truncate(action), detail)
            add_edge(client_id, nid, "MUST_AVOID")

    # --- 推奨ケア ---
    if template in ["full_view", "support_meeting", "emergency", "handover"]:
        care_prefs = data.get("carePreferences", [])
        if template == "emergency":
            care_prefs = [cp for cp in care_prefs if cp.get("priority") == "High"]
        for cp in care_prefs:
            cat = cp.get("category", "")
            instr = cp.get("instruction", "")
            if not (cat or instr):
                continue
            label = truncate(f"{cat}: {instr}" if cat else instr)
            detail = f"カテゴリ: {cat}\n指示: {instr}"
            if cp.get("priority"):
                detail += f"\n優先度: {cp['priority']}"
            nid = add_node("CarePreference", label, detail)
            add_edge(client_id, nid, "REQUIRES")

    # --- キーパーソン ---
    if template in ["full_view", "support_meeting", "emergency", "handover"]:
        for kp in data.get("keyPersons", []):
            name = kp.get("name", "")
            if not name:
                continue
            rel = kp.get("relationship", "")
            label = f"{name}({rel})" if rel else name
            detail = f"名前: {name}"
            if rel:
                detail += f"\n関係: {rel}"
            if kp.get("phone"):
                detail += f"\n電話: {kp['phone']}"
            if kp.get("priority"):
                detail += f"\n優先順位: {kp['priority']}"
            nid = add_node("KeyPerson", truncate(label), detail)
            add_edge(client_id, nid, "HAS_KEY_PERSON")

    # --- 後見人 ---
    if template in ["full_view", "emergency", "handover"]:
        for g in data.get("guardians", []):
            name = g.get("name", "")
            if not name:
                continue
            detail = f"名前: {name}"
            if g.get("type"):
                detail += f"\n種類: {g['type']}"
            if g.get("phone"):
                detail += f"\n電話: {g['phone']}"
            nid = add_node("Guardian", truncate(name), detail)
            add_edge(client_id, nid, "HAS_LEGAL_REP")

    # --- 医療機関 ---
    if template in ["full_view", "emergency", "handover"]:
        for h in data.get("hospitals", []):
            name = h.get("name", "")
            if not name:
                continue
            detail = f"医療機関: {name}"
            if h.get("specialty"):
                detail += f"\n診療科: {h['specialty']}"
            nid = add_node("Hospital", truncate(name), detail)
            add_edge(client_id, nid, "TREATED_AT")

    # --- 手帳 ---
    if template in ["full_view", "support_meeting", "handover"]:
        for cert in data.get("certificates", []):
            cert_type = cert.get("type", "")
            grade = cert.get("grade", "")
            if not (cert_type or grade):
                continue
            label = f"{cert_type} {grade}".strip()
            detail = f"種類: {cert_type}\n等級: {grade}"
            nid = add_node("Certificate", truncate(label), detail)
            add_edge(client_id, nid, "HAS_CERTIFICATE")

    # --- 特性 ---
    if template in ["full_view", "handover"]:
        for cond in data.get("conditions", []):
            name = cond.get("name", "")
            if not name:
                continue
            nid = add_node("Condition", truncate(name), f"特性: {name}")
            add_edge(client_id, nid, "HAS_CONDITION")

    # --- レイアウト計算 ---
    cx = CANVAS_WIDTH / 2
    cy = CANVAS_HEIGHT / 2
    calculate_layout(nodes, cx, cy)

    # --- テンプレート名 ---
    template_names = {
        "full_view": "全体像",
        "support_meeting": "支援会議用",
        "emergency": "緊急時体制",
        "handover": "引き継ぎ用",
    }
    title = f"{client_name}のエコマップ（{template_names.get(template, template)}）"

    # --- HTML生成 ---
    html_content = _build_html(title, nodes, edges, node_map, cx, cy)

    # ファイル保存
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"保存しました: {output_path}")

    return html_content


def _build_html(
    title: str,
    nodes: List[HtmlNode],
    edges: List[HtmlEdge],
    node_map: Dict[str, HtmlNode],
    center_x: float = 600,
    center_y: float = 450
) -> str:
    """HTML文書全体を構築"""

    # ノードデータをJavaScript用に変換
    nodes_js = []
    for node in nodes:
        style = node.style
        nodes_js.append(
            f'{{id:"{node.id}",x:{node.x:.1f},y:{node.y:.1f},r:{node.radius:.0f},'
            f'label:"{escape(node.label)}",type:"{node.node_type}",'
            f'bg:"{style["bg"]}",border:"{style["border"]}",textColor:"{style["text"]}",'
            f'icon:"{style["icon"]}",detail:`{escape(node.detail)}`}}'
        )

    edges_js = []
    for edge in edges:
        edges_js.append(
            f'{{source:"{edge.source_id}",target:"{edge.target_id}",'
            f'label:"{escape(edge.label)}"}}'
        )

    # 凡例データ
    used_types = sorted(set(n.node_type for n in nodes if n.node_type != "Client"))
    legend_items = []
    for t in used_types:
        s = CATEGORY_STYLES.get(t, {})
        legend_items.append(f'{{type:"{t}",bg:"{s.get("bg","")}",icon:"{s.get("icon","")}",label:"{s.get("label","")}"}}')

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>{escape(title)}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:{BG_COLOR}; color:{TEXT_COLOR}; font-family:'Segoe UI',system-ui,sans-serif; overflow:hidden; }}
#canvas {{ width:100vw; height:100vh; cursor:grab; }}
#canvas.dragging {{ cursor:grabbing; }}
#info {{ position:fixed; top:20px; right:20px; background:rgba(20,20,40,0.95); border:1px solid #333;
         border-radius:8px; padding:16px; max-width:300px; display:none; font-size:13px;
         white-space:pre-wrap; line-height:1.6; box-shadow:0 4px 12px rgba(0,0,0,0.5); }}
#info .close {{ position:absolute; top:6px; right:10px; cursor:pointer; font-size:18px; color:#888; }}
#info .close:hover {{ color:#fff; }}
#info h3 {{ color:#fff; margin-bottom:8px; font-size:15px; }}
#legend {{ position:fixed; bottom:20px; left:20px; background:rgba(20,20,40,0.9); border:1px solid #333;
           border-radius:8px; padding:12px 16px; font-size:12px; }}
#legend h4 {{ margin-bottom:8px; color:#aaa; }}
.legend-item {{ display:flex; align-items:center; gap:8px; margin:4px 0; }}
.legend-dot {{ width:12px; height:12px; border-radius:50%; }}
#title {{ position:fixed; top:16px; left:50%; transform:translateX(-50%); font-size:20px;
          font-weight:bold; color:#fff; text-shadow:0 2px 4px rgba(0,0,0,0.5); pointer-events:none; }}
#date {{ position:fixed; bottom:16px; right:20px; font-size:11px; color:#555; }}
#zoom-controls {{ position:fixed; bottom:20px; right:80px; display:flex; gap:4px; }}
#zoom-controls button {{ background:rgba(40,40,60,0.9); border:1px solid #444; color:#aaa;
                          width:32px; height:32px; border-radius:4px; cursor:pointer; font-size:16px; }}
#zoom-controls button:hover {{ background:rgba(60,60,80,0.9); color:#fff; }}
</style>
</head>
<body>
<div id="title">{escape(title)}</div>
<svg id="canvas" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
      <path d="M0,0 L8,3 L0,6" fill="{EDGE_COLOR}" opacity="0.6"/>
    </marker>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <g id="viewport">
    <g id="grid"></g>
    <g id="edges-layer"></g>
    <g id="nodes-layer"></g>
  </g>
</svg>
<div id="info"><span class="close" onclick="document.getElementById('info').style.display='none'">&times;</span><h3 id="info-title"></h3><div id="info-body"></div></div>
<div id="legend"><h4>凡例</h4><div id="legend-items"></div></div>
<div id="date">生成日: {date.today().isoformat()}</div>
<div id="zoom-controls">
  <button onclick="zoomIn()">+</button>
  <button onclick="zoomOut()">&minus;</button>
  <button onclick="resetView()">⟲</button>
</div>

<script>
// === データ ===
const NODES = [{",".join(nodes_js)}];
const EDGES = [{",".join(edges_js)}];
const LEGEND = [{",".join(legend_items)}];

// === 状態 ===
let scale = 1, panX = 0, panY = 0;
let isDragging = false, dragTarget = null;
let lastMouse = {{x:0, y:0}};
const svg = document.getElementById('canvas');
const viewport = document.getElementById('viewport');
const nodeMap = {{}};

// === 初期化 ===
function init() {{
    drawGrid();
    EDGES.forEach(drawEdge);
    NODES.forEach(n => {{ nodeMap[n.id] = n; drawNode(n); }});
    drawLegend();
    // 初期ビューを中央に合わせる
    const svgRect = svg.getBoundingClientRect();
    panX = svgRect.width / 2 - {center_x:.0f};
    panY = svgRect.height / 2 - {center_y:.0f};
    updateViewport();
}}

function drawGrid() {{
    const g = document.getElementById('grid');
    for (let x = 0; x < {CANVAS_WIDTH}; x += 50) {{
        const line = createSVG('line', {{x1:x, y1:0, x2:x, y2:{CANVAS_HEIGHT}, stroke:'{GRID_COLOR}', 'stroke-width':0.5}});
        g.appendChild(line);
    }}
    for (let y = 0; y < {CANVAS_HEIGHT}; y += 50) {{
        const line = createSVG('line', {{x1:0, y1:y, x2:{CANVAS_WIDTH}, y2:y, stroke:'{GRID_COLOR}', 'stroke-width':0.5}});
        g.appendChild(line);
    }}
}}

function drawNode(n) {{
    const g = createSVG('g', {{'transform': `translate(${{n.x}},${{n.y}})`, 'data-id': n.id, 'class': 'node-group', 'style': 'cursor:pointer'}});

    // 影
    g.appendChild(createSVG('circle', {{r: n.r + 2, fill: 'rgba(0,0,0,0.3)', cx: 2, cy: 2}}));
    // 本体
    g.appendChild(createSVG('circle', {{r: n.r, fill: n.bg, stroke: n.border, 'stroke-width': 2.5}}));
    // アイコン
    const iconSize = n.type === 'Client' ? 20 : 14;
    g.appendChild(createSVG('text', {{y: -4, 'text-anchor': 'middle', 'font-size': iconSize, fill: n.textColor}}, n.icon));
    // ラベル
    const fontSize = n.type === 'Client' ? 13 : 10;
    g.appendChild(createSVG('text', {{y: n.type === 'Client' ? 16 : 12, 'text-anchor': 'middle', 'font-size': fontSize, fill: n.textColor, 'font-weight': n.type === 'Client' ? 'bold' : 'normal'}}, n.label));

    // イベント
    g.addEventListener('mousedown', e => {{ dragTarget = n; e.stopPropagation(); }});
    g.addEventListener('click', e => {{ if (!isDragging) showInfo(n); }});

    document.getElementById('nodes-layer').appendChild(g);
}}

function drawEdge(e) {{
    const s = NODES.find(n => n.id === e.source);
    const t = NODES.find(n => n.id === e.target);
    if (!s || !t) return;

    const g = createSVG('g', {{'class': 'edge-group', 'data-source': e.source, 'data-target': e.target}});

    // エッジ線
    const dx = t.x - s.x, dy = t.y - s.y;
    const dist = Math.sqrt(dx*dx + dy*dy) || 1;
    const ux = dx/dist, uy = dy/dist;
    const x1 = s.x + ux * (s.r + 4), y1 = s.y + uy * (s.r + 4);
    const x2 = t.x - ux * (t.r + 8), y2 = t.y - uy * (t.r + 8);

    g.appendChild(createSVG('line', {{
        x1:x1, y1:y1, x2:x2, y2:y2,
        stroke: '{EDGE_COLOR}', 'stroke-width': 1.5, opacity: 0.6,
        'marker-end': 'url(#arrow)'
    }}));

    // ラベル
    if (e.label) {{
        const mx = (x1+x2)/2, my = (y1+y2)/2;
        g.appendChild(createSVG('text', {{
            x: mx, y: my - 6, 'text-anchor': 'middle',
            'font-size': 9, fill: '{EDGE_LABEL_COLOR}', opacity: 0.8
        }}, e.label));
    }}

    document.getElementById('edges-layer').appendChild(g);
}}

function drawLegend() {{
    const container = document.getElementById('legend-items');
    LEGEND.forEach(item => {{
        const div = document.createElement('div');
        div.className = 'legend-item';
        div.innerHTML = `<span class="legend-dot" style="background:${{item.bg}}"></span>${{item.icon}} ${{item.label}}`;
        container.appendChild(div);
    }});
}}

// === インタラクション ===
function showInfo(n) {{
    const panel = document.getElementById('info');
    document.getElementById('info-title').textContent = `${{n.icon}} ${{n.label}}`;
    document.getElementById('info-body').textContent = n.detail;
    panel.style.display = 'block';
}}

function updateViewport() {{
    viewport.setAttribute('transform', `translate(${{panX}},${{panY}}) scale(${{scale}})`);
}}

function updateEdges() {{
    document.querySelectorAll('.edge-group').forEach(g => {{
        const sid = g.getAttribute('data-source');
        const tid = g.getAttribute('data-target');
        const s = nodeMap[sid], t = nodeMap[tid];
        if (!s || !t) return;

        const line = g.querySelector('line');
        const text = g.querySelector('text');
        const dx = t.x - s.x, dy = t.y - s.y;
        const dist = Math.sqrt(dx*dx + dy*dy) || 1;
        const ux = dx/dist, uy = dy/dist;
        const x1 = s.x + ux * (s.r + 4), y1 = s.y + uy * (s.r + 4);
        const x2 = t.x - ux * (t.r + 8), y2 = t.y - uy * (t.r + 8);

        line.setAttribute('x1', x1); line.setAttribute('y1', y1);
        line.setAttribute('x2', x2); line.setAttribute('y2', y2);
        if (text) {{
            text.setAttribute('x', (x1+x2)/2);
            text.setAttribute('y', (y1+y2)/2 - 6);
        }}
    }});
}}

// === マウスイベント ===
svg.addEventListener('mousedown', e => {{
    if (!dragTarget) {{
        isDragging = false;
        svg.classList.add('dragging');
    }}
    lastMouse = {{x: e.clientX, y: e.clientY}};
}});

svg.addEventListener('mousemove', e => {{
    const dx = e.clientX - lastMouse.x, dy = e.clientY - lastMouse.y;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) isDragging = true;

    if (dragTarget) {{
        dragTarget.x += dx / scale;
        dragTarget.y += dy / scale;
        const g = document.querySelector(`[data-id="${{dragTarget.id}}"]`);
        if (g) g.setAttribute('transform', `translate(${{dragTarget.x}},${{dragTarget.y}})`);
        updateEdges();
    }} else if (e.buttons === 1) {{
        panX += dx; panY += dy;
        updateViewport();
    }}
    lastMouse = {{x: e.clientX, y: e.clientY}};
}});

svg.addEventListener('mouseup', () => {{
    dragTarget = null;
    svg.classList.remove('dragging');
    setTimeout(() => isDragging = false, 50);
}});

svg.addEventListener('wheel', e => {{
    e.preventDefault();
    const rect = svg.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.3, Math.min(3, scale * delta));

    panX = mx - (mx - panX) * (newScale / scale);
    panY = my - (my - panY) * (newScale / scale);
    scale = newScale;
    updateViewport();
}});

function zoomIn() {{ scale = Math.min(3, scale * 1.2); updateViewport(); }}
function zoomOut() {{ scale = Math.max(0.3, scale / 1.2); updateViewport(); }}
function resetView() {{
    scale = 1;
    const r = svg.getBoundingClientRect();
    panX = r.width/2 - {center_x:.0f}; panY = r.height/2 - {center_y:.0f};
    updateViewport();
}}

// === ユーティリティ ===
function createSVG(tag, attrs, text) {{
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [k, v] of Object.entries(attrs || {{}})) el.setAttribute(k, v);
    if (text) el.textContent = text;
    return el;
}}

// === 起動 ===
init();
</script>
</body>
</html>'''


# =============================================================================
# CLI実行
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HTML形式のインタラクティブエコマップを生成")
    parser.add_argument("client_name", help="クライアント名")
    parser.add_argument("-t", "--template", default="full_view",
                        choices=["full_view", "support_meeting", "emergency", "handover"],
                        help="テンプレート名")
    parser.add_argument("-o", "--output", help="出力ファイルパス")

    args = parser.parse_args()

    output_path = args.output
    if not output_path:
        output_dir = Path(__file__).parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / f"{args.client_name}_ecomap_{args.template}.html")

    generate_html_ecomap(
        args.client_name,
        template=args.template,
        output_path=output_path
    )
