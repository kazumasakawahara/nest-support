#!/usr/bin/env python3
"""
更新レポート生成スクリプト

同期実行後の結果をMarkdownまたはHTML形式で出力します。
"""

import argparse
import json
import os
import sys
import html as _html
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def _esc(value) -> str:
    """DB/CSV 由来の文字列を HTML エスケープする（レポートXSS対策）。"""
    return _html.escape("" if value is None else str(value))

# Neo4j接続用
try:
    from neo4j import GraphDatabase
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("必要なパッケージをインストールしてください: pip install neo4j python-dotenv")
    sys.exit(1)


class ReportGenerator:
    """レポート生成クラス"""

    def __init__(self):
        self.driver = None

    def connect(self):
        """Neo4jに接続"""
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        """接続を閉じる"""
        if self.driver:
            self.driver.close()

    def get_statistics(self, prefecture: str = "") -> Dict:
        """ServiceProviderの統計情報を取得"""
        with self.driver.session() as session:
            # 総数
            total_query = """
            MATCH (sp:ServiceProvider)
            WHERE $prefecture = '' OR sp.prefecture CONTAINS $prefecture
            RETURN count(sp) AS total
            """
            total = session.run(total_query, prefecture=prefecture).single()["total"]
            
            # サービス種類別
            by_type_query = """
            MATCH (sp:ServiceProvider)
            WHERE $prefecture = '' OR sp.prefecture CONTAINS $prefecture
            RETURN sp.serviceType AS serviceType, count(*) AS count
            ORDER BY count DESC
            """
            by_type = [
                {"serviceType": r["serviceType"], "count": r["count"]}
                for r in session.run(by_type_query, prefecture=prefecture)
            ]
            
            # 市区町村別
            by_city_query = """
            MATCH (sp:ServiceProvider)
            WHERE $prefecture = '' OR sp.prefecture CONTAINS $prefecture
            RETURN sp.city AS city, count(*) AS count
            ORDER BY count DESC
            LIMIT 20
            """
            by_city = [
                {"city": r["city"], "count": r["count"]}
                for r in session.run(by_city_query, prefecture=prefecture)
            ]
            
            # 空き状況別
            by_avail_query = """
            MATCH (sp:ServiceProvider)
            WHERE $prefecture = '' OR sp.prefecture CONTAINS $prefecture
            RETURN sp.availability AS availability, count(*) AS count
            ORDER BY count DESC
            """
            by_avail = [
                {"availability": r["availability"] or "未確認", "count": r["count"]}
                for r in session.run(by_avail_query, prefecture=prefecture)
            ]
            
            # 最近追加された事業所
            recent_query = """
            MATCH (sp:ServiceProvider)
            WHERE $prefecture = '' OR sp.prefecture CONTAINS $prefecture
            RETURN sp.name AS name, sp.serviceType AS serviceType, sp.city AS city, sp.updatedAt AS updatedAt
            ORDER BY sp.updatedAt DESC
            LIMIT 10
            """
            recent = [
                {
                    "name": r["name"],
                    "serviceType": r["serviceType"],
                    "city": r["city"],
                    "updatedAt": str(r["updatedAt"]) if r["updatedAt"] else ""
                }
                for r in session.run(recent_query, prefecture=prefecture)
            ]
            
            # 廃止された事業所
            closed_query = """
            MATCH (sp:ServiceProvider)
            WHERE sp.status = 'Closed'
              AND ($prefecture = '' OR sp.prefecture CONTAINS $prefecture)
            RETURN sp.name AS name, sp.serviceType AS serviceType, sp.closedAt AS closedAt
            ORDER BY sp.closedAt DESC
            LIMIT 10
            """
            closed = [
                {
                    "name": r["name"],
                    "serviceType": r["serviceType"],
                    "closedAt": str(r["closedAt"]) if r["closedAt"] else ""
                }
                for r in session.run(closed_query, prefecture=prefecture)
            ]
            
            return {
                "total": total,
                "by_type": by_type,
                "by_city": by_city,
                "by_availability": by_avail,
                "recent": recent,
                "closed": closed
            }

    def get_affected_clients(self) -> List[Dict]:
        """廃止事業所を利用中のクライアントを取得"""
        with self.driver.session() as session:
            query = """
            MATCH (c:Client)-[r:USES_SERVICE]->(sp:ServiceProvider)
            WHERE sp.status = 'Closed'
              AND r.status = 'Active'
            RETURN c.name AS clientName, 
                   sp.name AS providerName, 
                   sp.serviceType AS serviceType,
                   sp.closedAt AS closedAt
            ORDER BY sp.closedAt DESC
            """
            return [
                {
                    "clientName": r["clientName"],
                    "providerName": r["providerName"],
                    "serviceType": r["serviceType"],
                    "closedAt": str(r["closedAt"]) if r["closedAt"] else ""
                }
                for r in session.run(query)
            ]

    def generate_markdown(self, stats: Dict, affected: List[Dict], prefecture: str = "") -> str:
        """Markdown形式のレポートを生成"""
        lines = []
        
        lines.append("# 障害福祉サービス事業所データレポート\n")
        lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if prefecture:
            lines.append(f"対象地域: {prefecture}")
        lines.append("")
        
        # 概要
        lines.append("## 📊 概要\n")
        lines.append(f"**登録事業所総数: {stats['total']:,}件**\n")
        
        # サービス種類別
        lines.append("## 🏢 サービス種類別\n")
        lines.append("| サービス種類 | 件数 |")
        lines.append("|-------------|------|")
        for item in stats["by_type"]:
            lines.append(f"| {item['serviceType']} | {item['count']:,} |")
        lines.append("")
        
        # 市区町村別（上位）
        lines.append("## 📍 市区町村別（上位20）\n")
        lines.append("| 市区町村 | 件数 |")
        lines.append("|---------|------|")
        for item in stats["by_city"]:
            lines.append(f"| {item['city']} | {item['count']:,} |")
        lines.append("")
        
        # 空き状況
        lines.append("## 🔄 空き状況\n")
        lines.append("| 空き状況 | 件数 |")
        lines.append("|---------|------|")
        for item in stats["by_availability"]:
            avail = item["availability"]
            icon = "🟢" if avail == "空きあり" else "🟡" if avail == "要相談" else "🔴" if avail == "満員" else "❓"
            lines.append(f"| {icon} {avail} | {item['count']:,} |")
        lines.append("")
        
        # 最近追加された事業所
        if stats["recent"]:
            lines.append("## 🆕 最近追加された事業所\n")
            lines.append("| 事業所名 | サービス種類 | 市区町村 |")
            lines.append("|---------|-------------|---------|")
            for item in stats["recent"]:
                lines.append(f"| {item['name']} | {item['serviceType']} | {item['city']} |")
            lines.append("")
        
        # 廃止された事業所
        if stats["closed"]:
            lines.append("## ⚠️ 廃止された事業所\n")
            lines.append("| 事業所名 | サービス種類 | 廃止日 |")
            lines.append("|---------|-------------|--------|")
            for item in stats["closed"]:
                lines.append(f"| {item['name']} | {item['serviceType']} | {item['closedAt'][:10] if item['closedAt'] else ''} |")
            lines.append("")
        
        # 影響を受けるクライアント
        if affected:
            lines.append("## 🚨 要対応: 廃止事業所を利用中のクライアント\n")
            lines.append("以下のクライアントは廃止された事業所を利用中です。代替事業所の検討が必要です。\n")
            lines.append("| クライアント | 廃止事業所 | サービス種類 |")
            lines.append("|-------------|-----------|-------------|")
            for item in affected:
                lines.append(f"| {item['clientName']} | {item['providerName']} | {item['serviceType']} |")
            lines.append("")
        
        # 次回更新案内
        lines.append("## ℹ️ 次回更新予定\n")
        lines.append("WAM NETのデータは年2回（4月・10月頃）更新されます。")
        lines.append("最新データは以下からダウンロードできます:")
        lines.append("https://www.wam.go.jp/wamappl/shogaiservice_opendata.html")
        lines.append("")
        
        return "\n".join(lines)

    def generate_html(self, stats: Dict, affected: List[Dict], prefecture: str = "") -> str:
        """HTML形式のレポートを生成"""
        # MarkdownをHTMLに変換（簡易版）
        md = self.generate_markdown(stats, affected, prefecture)
        
        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>障害福祉サービス事業所データレポート</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{ background: #f8f9fa; }}
        tr:hover {{ background: #f5f5f5; }}
        .stat-box {{
            display: inline-block;
            background: #e3f2fd;
            padding: 15px 25px;
            border-radius: 8px;
            margin: 10px 5px;
        }}
        .stat-number {{ font-size: 24px; font-weight: bold; color: #1976D2; }}
        .warning {{ background: #fff3e0; padding: 15px; border-left: 4px solid #ff9800; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏢 障害福祉サービス事業所データレポート</h1>
        <p>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        {f'<p>対象地域: {_esc(prefecture)}</p>' if prefecture else ''}
        
        <h2>📊 概要</h2>
        <div class="stat-box">
            <div class="stat-number">{stats['total']:,}</div>
            <div>登録事業所総数</div>
        </div>
        
        <h2>🏢 サービス種類別</h2>
        <table>
            <tr><th>サービス種類</th><th>件数</th></tr>
            {''.join(f'<tr><td>{_esc(item["serviceType"])}</td><td>{item["count"]:,}</td></tr>' for item in stats["by_type"])}
        </table>
        
        <h2>📍 市区町村別（上位20）</h2>
        <table>
            <tr><th>市区町村</th><th>件数</th></tr>
            {''.join(f'<tr><td>{_esc(item["city"])}</td><td>{item["count"]:,}</td></tr>' for item in stats["by_city"])}
        </table>
        
        {f'''
        <h2>🚨 要対応: 廃止事業所を利用中のクライアント</h2>
        <div class="warning">
            以下のクライアントは廃止された事業所を利用中です。代替事業所の検討が必要です。
        </div>
        <table>
            <tr><th>クライアント</th><th>廃止事業所</th><th>サービス種類</th></tr>
            {''.join(f'<tr><td>{_esc(item["clientName"])}</td><td>{_esc(item["providerName"])}</td><td>{_esc(item["serviceType"])}</td></tr>' for item in affected)}
        </table>
        ''' if affected else ''}
        
        <h2>ℹ️ 次回更新予定</h2>
        <p>WAM NETのデータは年2回（4月・10月頃）更新されます。</p>
        <p>最新データは<a href="https://www.wam.go.jp/wamappl/shogaiservice_opendata.html">こちら</a>からダウンロードできます。</p>
    </div>
</body>
</html>
"""
        return html


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="障害福祉サービス事業所データレポートを生成"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "html", "json"],
        default="markdown",
        help="出力形式（デフォルト: markdown）"
    )
    parser.add_argument(
        "--prefecture", "-p",
        default="",
        help="都道府県でフィルタ"
    )
    parser.add_argument(
        "--output", "-o",
        help="出力ファイル（指定しない場合は標準出力）"
    )
    
    args = parser.parse_args()
    
    generator = ReportGenerator()
    
    try:
        generator.connect()
        print("📊 データ収集中...")
        
        stats = generator.get_statistics(args.prefecture)
        affected = generator.get_affected_clients()
        
        if args.format == "markdown":
            report = generator.generate_markdown(stats, affected, args.prefecture)
        elif args.format == "html":
            report = generator.generate_html(stats, affected, args.prefecture)
        else:  # json
            report = json.dumps({
                "generated_at": datetime.now().isoformat(),
                "prefecture": args.prefecture,
                "statistics": stats,
                "affected_clients": affected
            }, ensure_ascii=False, indent=2)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"✅ レポートを保存しました: {args.output}")
        else:
            print(report)
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        generator.close()


if __name__ == "__main__":
    main()
