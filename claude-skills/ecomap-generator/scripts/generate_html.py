"""
nest-support ビジュアル生成エンジン
D3.js 物理シミュレーションを活用したインタラクティブなエコマップ・ダッシュボード生成
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 既存のデータ取得ロジックを活用
from generate_mermaid import fetch_client_data, run_query, HAS_NEO4J

# =============================================================================
# 設定
# =============================================================================

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "d3_dashboard.html"
HYBRID_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "hybrid_insight.html"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"

# ノードタイプ別の色とサイズ
STYLE_CONFIG = {
    "Client": {"color": "#4C8BF5", "r": 40},
    "NgAction": {"color": "#FF5252", "r": 25},
    "CarePreference": {"color": "#43A047", "r": 25},
    "KeyPerson": {"color": "#FB8C00", "r": 25},
    "Guardian": {"color": "#8E24AA", "r": 25},
    "Hospital": {"color": "#1E88E5", "r": 25},
    "Certificate": {"color": "#546E7A", "r": 25},
    "Condition": {"color": "#F9A825", "r": 25},
    "Supporter": {"color": "#5C6BC0", "r": 25},
    "SupportLog": {"color": "#66BB6A", "r": 20},
}

# =============================================================================
# データ変換ロジック
# =============================================================================

def fetch_enhanced_data(client_name: str) -> Dict:
    """既存のデータに加え、最新の支援記録と感情ログを取得"""
    data = fetch_client_data(client_name, template="full_view")
    
    if HAS_NEO4J:
        # 最新の支援記録（感情ログ付き）を5件取得
        data["supportLogs"] = run_query("""
            MATCH (c:Client {name: $name})<-[:ABOUT]-(log:SupportLog)
            RETURN log.situation as situation, log.action as action, 
                   log.emotion as emotion, log.triggerTag as triggerTag,
                   log.date as date, log.context as context
            ORDER BY log.date DESC LIMIT 5
        """, {"name": client_name})
    else:
        data["supportLogs"] = [
            {"situation": "デモ：散歩", "emotion": "Joy", "triggerTag": "Leisure", "date": "2026-03-30"},
            {"situation": "デモ：作業変更", "emotion": "Anger", "triggerTag": "Work", "date": "2026-03-30"}
        ]
    
    return data

def build_d3_graph(client_data: Dict) -> Dict:
    """D3.jsが解釈可能なグラフ構造に変換"""
    nodes = []
    links = []
    
    # 1. クライアントノード
    client_name = client_data["client"]["name"]
    nodes.append({
        "id": "client",
        "label": client_name,
        "type": "Client",
        **STYLE_CONFIG["Client"],
        "properties": client_data["client"]
    })
    
    # 2. 関連ノードの追加ヘルパー
    def add_related_nodes(items, label_key, node_type, rel_type):
        for i, item in enumerate(items):
            node_id = f"{node_type}_{i}"
            nodes.append({
                "id": node_id,
                "label": item.get(label_key, "不明"),
                "type": node_type,
                **STYLE_CONFIG.get(node_type, {"color": "#999", "r": 20}),
                "properties": item
            })
            links.append({
                "source": "client",
                "target": node_id,
                "label": rel_type
            })

    # 各カテゴリの追加
    add_related_nodes(client_data.get("ngActions", []), "action", "NgAction", "禁忌")
    add_related_nodes(client_data.get("carePreferences", []), "instruction", "CarePreference", "推奨")
    add_related_nodes(client_data.get("keyPersons", []), "name", "KeyPerson", "家族")
    add_related_nodes(client_data.get("conditions", []), "name", "Condition", "特性")
    add_related_nodes(client_data.get("supportLogs", []), "situation", "SupportLog", "直近の記録")
    
    return {"nodes": nodes, "links": links}

# =============================================================================
# HTML生成
# =============================================================================

def generate_interactive_ecomap(client_name: str, output_path: Optional[str] = None) -> str:
    """D3テンプレートを使用してインタラクティブなHTMLを生成"""
    
    # データ準備
    raw_data = fetch_enhanced_data(client_name)
    graph_data = build_d3_graph(raw_data)
    
    # テンプレート読み込み
    if not TEMPLATE_PATH.exists():
        return f"エラー: テンプレートが見つかりません ({TEMPLATE_PATH})"
    
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_content = f.read()
    
    # 置換
    title = f"{client_name} の支援インサイト・グラフ"
    html_output = template_content.replace("{{ TITLE }}", title)
    html_output = html_output.replace("{{ GRAPH_DATA }}", json.dumps(graph_data, ensure_ascii=False))
    
    # 保存
    if not output_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = str(OUTPUT_DIR / f"{client_name}_insight_graph.html")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_output)
    
    return output_path

# =============================================================================
# ハイブリッド・インサイト・ビュー (感情時系列 + 物理グラフ + AI相談)
# =============================================================================

def fetch_emotion_timeline(client_name: str, days: int = 30) -> List[Dict]:
    """感情の時系列データを取得"""
    if HAS_NEO4J:
        return run_query("""
            MATCH (c:Client {name: $name})<-[:ABOUT]-(log:SupportLog)
            WHERE log.date >= date() - duration({days: $days})
              AND log.emotion IS NOT NULL
            RETURN toString(log.date) AS date, log.emotion AS emotion,
                   log.triggerTag AS triggerTag, log.situation AS situation,
                   log.context AS context
            ORDER BY log.date
        """, {"name": client_name, "days": days})
    else:
        # デモデータ
        return [
            {"date": "2026-03-25", "emotion": "Calm", "triggerTag": "食事", "situation": "食事", "context": ""},
            {"date": "2026-03-26", "emotion": "Joy", "triggerTag": "作業", "situation": "作業", "context": ""},
            {"date": "2026-03-27", "emotion": "Anger", "triggerTag": "大きな音", "situation": "散歩", "context": "工事の音"},
            {"date": "2026-03-28", "emotion": "Sadness", "triggerTag": "人間関係", "situation": "他者交流", "context": ""},
            {"date": "2026-03-29", "emotion": "Anxiety", "triggerTag": "環境変化", "situation": "入浴", "context": ""},
            {"date": "2026-03-30", "emotion": "Calm", "triggerTag": "食事", "situation": "食事", "context": ""},
        ]


def fetch_insight_data(client_name: str) -> Dict:
    """insight_engine からインサイト情報を取得"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
        from lib.insight_engine import generate_risk_assessment
        return generate_risk_assessment(client_name)
    except Exception as e:
        print(f"[WARN] insight_engine 利用不可: {e}", file=sys.stderr)
        return {
            "risk_level": "low",
            "emotion_drift": {"alerts": []},
            "cascading_risk": {"is_cascading": False, "events": []},
            "care_promotions": [],
            "recommended_actions": [],
            "should_trigger_emergency": False,
        }


def generate_hybrid_insight(client_name: str, output_path: Optional[str] = None) -> str:
    """ハイブリッド・インサイト・ビュー (感情時系列 + 物理グラフ + AI相談) を生成"""

    # データ準備
    raw_data = fetch_enhanced_data(client_name)
    graph_data = build_d3_graph(raw_data)
    emotion_data = fetch_emotion_timeline(client_name)
    insight_data = fetch_insight_data(client_name)

    # テンプレート読み込み
    if not HYBRID_TEMPLATE_PATH.exists():
        return f"エラー: テンプレートが見つかりません ({HYBRID_TEMPLATE_PATH})"

    with open(HYBRID_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_content = f.read()

    # プレースホルダー置換
    title = f"{client_name} — ハイブリッド・インサイト・ビュー"
    html_output = template_content.replace("{{ TITLE }}", title)
    html_output = html_output.replace("{{ GRAPH_DATA }}", json.dumps(graph_data, ensure_ascii=False))
    html_output = html_output.replace("{{ EMOTION_DATA }}", json.dumps(emotion_data, ensure_ascii=False))
    html_output = html_output.replace("{{ INSIGHT_DATA }}", json.dumps(insight_data, ensure_ascii=False, default=str))
    html_output = html_output.replace("{{ CLIENT_NAME }}", json.dumps(client_name, ensure_ascii=False))

    # 保存
    if not output_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = str(OUTPUT_DIR / f"{client_name}_hybrid_insight.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_output)

    return output_path


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "サンプル利用者"
    mode = sys.argv[2] if len(sys.argv) > 2 else "hybrid"

    if mode == "hybrid":
        path = generate_hybrid_insight(name)
    else:
        path = generate_interactive_ecomap(name)

    print(f"生成完了: {path}")
