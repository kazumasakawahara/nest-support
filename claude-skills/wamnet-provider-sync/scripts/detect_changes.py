#!/usr/bin/env python3
"""
差分検出ユーティリティ

2つのCSVファイルを比較して差分を検出するスタンドアロンツール。
Neo4jに接続せずにCSVファイル同士の比較が可能。
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ChangeDetector:
    """差分検出クラス"""

    def __init__(self, key_field: str = "事業所番号"):
        """
        初期化
        
        Args:
            key_field: 一意識別子のフィールド名
        """
        self.key_field = key_field
        self.compare_fields = [
            "事業所名", "住所", "電話番号", "定員", "サービス種類"
        ]

    def load_csv(self, csv_path: str) -> Dict[str, Dict]:
        """
        CSVをロードしてDict形式に変換
        
        Args:
            csv_path: CSVファイルパス
        
        Returns:
            key → row のDict
        """
        data = {}
        
        for encoding in ["cp932", "utf-8", "utf-8-sig"]:
            try:
                with open(csv_path, "r", encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        key = row.get(self.key_field, "").strip()
                        if key:
                            data[key] = {k: v.strip() for k, v in row.items()}
                    return data
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"CSVの文字エンコーディングを判定できません: {csv_path}")

    def detect(
        self, 
        old_data: Dict[str, Dict], 
        new_data: Dict[str, Dict]
    ) -> Dict:
        """
        差分を検出
        
        Args:
            old_data: 旧データ
            new_data: 新データ
        
        Returns:
            差分情報
        """
        old_keys = set(old_data.keys())
        new_keys = set(new_data.keys())
        
        # 新規
        added_keys = new_keys - old_keys
        added = [new_data[k] for k in added_keys]
        
        # 廃止
        removed_keys = old_keys - new_keys
        removed = [old_data[k] for k in removed_keys]
        
        # 変更
        common_keys = old_keys & new_keys
        modified = []
        unchanged = []
        
        for key in common_keys:
            old_row = old_data[key]
            new_row = new_data[key]
            
            changes = self._detect_field_changes(old_row, new_row)
            if changes:
                modified.append({
                    "key": key,
                    "old": old_row,
                    "new": new_row,
                    "changes": changes
                })
            else:
                unchanged.append(key)
        
        return {
            "summary": {
                "added": len(added),
                "removed": len(removed),
                "modified": len(modified),
                "unchanged": len(unchanged),
                "total_old": len(old_data),
                "total_new": len(new_data)
            },
            "added": added,
            "removed": removed,
            "modified": modified
        }

    def _detect_field_changes(
        self, 
        old_row: Dict, 
        new_row: Dict
    ) -> List[Dict]:
        """フィールドレベルの変更を検出"""
        changes = []
        
        for field in self.compare_fields:
            old_val = old_row.get(field, "")
            new_val = new_row.get(field, "")
            
            if old_val != new_val:
                changes.append({
                    "field": field,
                    "old": old_val,
                    "new": new_val
                })
        
        return changes

    def generate_report(self, diff: Dict, output_format: str = "markdown") -> str:
        """
        差分レポートを生成
        
        Args:
            diff: detect()の結果
            output_format: 出力形式（markdown/json）
        
        Returns:
            レポート文字列
        """
        if output_format == "json":
            return json.dumps(diff, ensure_ascii=False, indent=2)
        
        # Markdown形式
        lines = []
        lines.append("# WAM NET事業所データ差分レポート\n")
        lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # サマリー
        s = diff["summary"]
        lines.append("## サマリー\n")
        lines.append("| 項目 | 件数 |")
        lines.append("|------|------|")
        lines.append(f"| 旧データ総数 | {s['total_old']} |")
        lines.append(f"| 新データ総数 | {s['total_new']} |")
        lines.append(f"| 🆕 新規 | {s['added']} |")
        lines.append(f"| ❌ 廃止 | {s['removed']} |")
        lines.append(f"| 📝 変更 | {s['modified']} |")
        lines.append(f"| ✅ 変更なし | {s['unchanged']} |")
        lines.append("")
        
        # 新規（抜粋）
        if diff["added"]:
            lines.append("## 新規事業所（最大20件）\n")
            lines.append("| 事業所番号 | 事業所名 | サービス種類 |")
            lines.append("|-----------|---------|-------------|")
            for item in diff["added"][:20]:
                lines.append(
                    f"| {item.get(self.key_field, '')} | "
                    f"{item.get('事業所名', '')} | "
                    f"{item.get('サービス種類', '')} |"
                )
            if len(diff["added"]) > 20:
                lines.append(f"\n... 他 {len(diff['added']) - 20}件")
            lines.append("")
        
        # 廃止（抜粋）
        if diff["removed"]:
            lines.append("## 廃止事業所（最大20件）\n")
            lines.append("| 事業所番号 | 事業所名 | サービス種類 |")
            lines.append("|-----------|---------|-------------|")
            for item in diff["removed"][:20]:
                lines.append(
                    f"| {item.get(self.key_field, '')} | "
                    f"{item.get('事業所名', '')} | "
                    f"{item.get('サービス種類', '')} |"
                )
            if len(diff["removed"]) > 20:
                lines.append(f"\n... 他 {len(diff['removed']) - 20}件")
            lines.append("")
        
        # 変更（抜粋）
        if diff["modified"]:
            lines.append("## 変更事業所（最大20件）\n")
            for item in diff["modified"][:20]:
                lines.append(f"### {item['new'].get('事業所名', item['key'])}")
                lines.append(f"事業所番号: {item['key']}\n")
                lines.append("| 項目 | 変更前 | 変更後 |")
                lines.append("|------|--------|--------|")
                for change in item["changes"]:
                    lines.append(
                        f"| {change['field']} | {change['old']} | {change['new']} |"
                    )
                lines.append("")
            if len(diff["modified"]) > 20:
                lines.append(f"... 他 {len(diff['modified']) - 20}件の変更あり")
        
        return "\n".join(lines)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="2つのWAM NET CSVファイルの差分を検出"
    )
    parser.add_argument(
        "--old", "-o",
        required=True,
        help="旧データCSVファイル"
    )
    parser.add_argument(
        "--new", "-n",
        required=True,
        help="新データCSVファイル"
    )
    parser.add_argument(
        "--key", "-k",
        default="事業所番号",
        help="キーフィールド名（デフォルト: 事業所番号）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json"],
        default="markdown",
        help="出力形式（デフォルト: markdown）"
    )
    parser.add_argument(
        "--output", "-out",
        help="出力ファイル（指定しない場合は標準出力）"
    )
    
    args = parser.parse_args()
    
    detector = ChangeDetector(key_field=args.key)
    
    try:
        print(f"旧データ読み込み: {args.old}")
        old_data = detector.load_csv(args.old)
        print(f"  → {len(old_data)}件")
        
        print(f"新データ読み込み: {args.new}")
        new_data = detector.load_csv(args.new)
        print(f"  → {len(new_data)}件")
        
        print("差分検出中...")
        diff = detector.detect(old_data, new_data)
        
        report = detector.generate_report(diff, args.format)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\n✅ レポートを保存しました: {args.output}")
        else:
            print("\n" + report)
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
