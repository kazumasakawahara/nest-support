#!/usr/bin/env python3
"""
WAM NET事業所データ同期スクリプト

WAM NETからダウンロードした障害福祉サービス事業所CSVデータを
Neo4jのServiceProviderノードに同期します。

使用方法:
    python sync_providers.py --mode full --csv-file /path/to/data.csv
    python sync_providers.py --mode diff --csv-file /path/to/data.csv --dry-run
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Neo4j接続用
try:
    from neo4j import GraphDatabase
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("必要なパッケージをインストールしてください: pip install neo4j python-dotenv")
    sys.exit(1)


class WAMNetSyncError(Exception):
    """WAM NET同期エラー"""
    pass


class ServiceProviderSync:
    """事業所データ同期クラス"""

    def __init__(self, dry_run: bool = False):
        """
        初期化
        
        Args:
            dry_run: Trueの場合、実際のDB更新を行わない
        """
        self.dry_run = dry_run
        self.driver = None
        self.config_dir = Path(__file__).parent.parent / "config"
        self.service_types = self._load_service_types()
        self.prefectures = self._load_prefectures()
        
        # 統計情報
        self.stats = {
            "new": 0,
            "modified": 0,
            "closed": 0,
            "unchanged": 0,
            "errors": 0
        }
        
        # 変更詳細
        self.changes = {
            "new": [],
            "modified": [],
            "closed": [],
            "affected_clients": []
        }

    def _load_service_types(self) -> Dict:
        """サービス種類マッピングを読み込み"""
        config_path = self.config_dir / "service_types.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"service_types": {}}

    def _load_prefectures(self) -> Dict:
        """都道府県コードを読み込み"""
        config_path = self.config_dir / "prefectures.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"prefectures": {}}

    def connect(self):
        """Neo4jに接続"""
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        
        if not password:
            raise WAMNetSyncError("NEO4J_PASSWORD環境変数が設定されていません")
        
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        # 接続テスト
        with self.driver.session() as session:
            session.run("RETURN 1")
        print(f"✅ Neo4jに接続しました: {uri}")

    def close(self):
        """接続を閉じる"""
        if self.driver:
            self.driver.close()

    def normalize_service_type(self, raw_type: str) -> str:
        """サービス種類を正規化"""
        raw_type = raw_type.strip()
        service_info = self.service_types.get("service_types", {}).get(raw_type)
        if service_info:
            return service_info.get("normalized", raw_type)
        return raw_type

    def normalize_phone(self, phone: str) -> str:
        """電話番号を正規化（ハイフン形式）"""
        if not phone:
            return ""
        # 全角→半角
        phone = phone.translate(str.maketrans("０１２３４５６７８９－", "0123456789-"))
        # 数字とハイフン以外を除去
        phone = "".join(c for c in phone if c.isdigit() or c == "-")
        return phone

    def parse_csv(self, csv_path: str, encoding: str = "cp932") -> List[Dict]:
        """
        CSVファイルを解析してServiceProviderデータに変換
        
        Args:
            csv_path: CSVファイルパス
            encoding: 文字エンコーディング（デフォルト: Shift-JIS/CP932）
        
        Returns:
            ServiceProviderデータのリスト
        """
        providers = []
        
        # エンコーディングを自動検出（cp932 → utf-8 の順で試行）
        for enc in [encoding, "utf-8", "utf-8-sig"]:
            try:
                with open(csv_path, "r", encoding=enc) as f:
                    # ヘッダー行を確認
                    first_line = f.readline()
                    f.seek(0)
                    
                    reader = csv.DictReader(f)
                    
                    for row in reader:
                        provider = self._row_to_provider(row)
                        if provider:
                            providers.append(provider)
                    
                    print(f"✅ CSVを読み込みました: {len(providers)}件 (encoding: {enc})")
                    return providers
                    
            except UnicodeDecodeError:
                continue
            except Exception as e:
                raise WAMNetSyncError(f"CSV読み込みエラー: {e}")
        
        raise WAMNetSyncError(f"CSVの文字エンコーディングを判定できません: {csv_path}")

    def _row_to_provider(self, row: Dict) -> Optional[Dict]:
        """CSV行をServiceProviderデータに変換"""
        try:
            # 事業所番号（必須）
            provider_id = row.get("事業所番号", row.get("jigyosho_no", "")).strip()
            if not provider_id:
                return None
            
            # サービス種類
            service_type_raw = row.get("サービス種類", row.get("service_type", "")).strip()
            service_type = self.normalize_service_type(service_type_raw)
            
            # 一意識別子を生成（事業所番号_サービス種類コード）
            service_code = self.service_types.get("service_types", {}).get(
                service_type_raw, {}
            ).get("code", "00")
            unique_id = f"{provider_id}_{service_code}"
            
            return {
                "providerId": unique_id,
                "wamnetId": provider_id,
                "name": row.get("事業所名", row.get("jigyosho_name", "")).strip(),
                "serviceType": service_type,
                "postalCode": row.get("郵便番号", row.get("zip_code", "")).strip(),
                "prefecture": row.get("都道府県", row.get("prefecture", "")).strip(),
                "city": row.get("市区町村", row.get("city", "")).strip(),
                "address": row.get("住所", row.get("address", "")).strip(),
                "phone": self.normalize_phone(row.get("電話番号", row.get("tel", ""))),
                "fax": self.normalize_phone(row.get("FAX番号", row.get("fax", ""))),
                "capacity": self._parse_int(row.get("定員", row.get("capacity", ""))),
                "corporateName": row.get("法人名", row.get("corporate_name", "")).strip(),
                "designationDate": row.get("指定年月日", row.get("designation_date", "")).strip(),
                "availability": "未確認",
                "updatedAt": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"⚠️ 行変換エラー: {e}")
            return None

    def _parse_int(self, value: str) -> Optional[int]:
        """文字列を整数に変換（エラー時はNone）"""
        if not value:
            return None
        try:
            # 全角数字→半角
            value = value.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
            return int(value)
        except ValueError:
            return None

    def get_existing_providers(self, prefecture: str = "") -> Dict[str, Dict]:
        """
        既存のServiceProviderを取得
        
        Args:
            prefecture: 都道府県でフィルタ（空の場合は全件）
        
        Returns:
            providerId → プロパティのDict
        """
        with self.driver.session() as session:
            if prefecture:
                query = """
                MATCH (sp:ServiceProvider)
                WHERE sp.prefecture CONTAINS $prefecture
                RETURN sp
                """
                result = session.run(query, prefecture=prefecture)
            else:
                query = "MATCH (sp:ServiceProvider) RETURN sp"
                result = session.run(query)
            
            existing = {}
            for record in result:
                node = record["sp"]
                provider_id = node.get("providerId")
                if provider_id:
                    existing[provider_id] = dict(node)
            
            return existing

    def detect_changes(
        self, 
        new_providers: List[Dict], 
        existing_providers: Dict[str, Dict]
    ) -> Tuple[List[Dict], List[Dict], List[str]]:
        """
        差分を検出
        
        Args:
            new_providers: 新しいデータ
            existing_providers: 既存データ
        
        Returns:
            (追加リスト, 更新リスト, 廃止IDリスト)
        """
        to_add = []
        to_update = []
        
        new_ids = set()
        
        for provider in new_providers:
            provider_id = provider["providerId"]
            new_ids.add(provider_id)
            
            if provider_id not in existing_providers:
                # 新規
                to_add.append(provider)
                self.stats["new"] += 1
                self.changes["new"].append({
                    "name": provider["name"],
                    "serviceType": provider["serviceType"],
                    "city": provider["city"]
                })
            else:
                # 既存との比較
                existing = existing_providers[provider_id]
                # Closed 事業所が CSV に再登場した場合は、フィールド無変更でも
                # 復活（Active 化）が必要なので必ず updated に分類する。
                # status を _is_modified の比較対象に入れていないため、ここで明示判定する。
                was_closed = str(existing.get("status", "")) == "Closed"
                if was_closed or self._is_modified(provider, existing):
                    to_update.append(provider)
                    self.stats["modified"] += 1
                    changes = self._get_diff(provider, existing)
                    if was_closed:
                        changes = ["status: Closed → Active（復活）"] + changes
                    self.changes["modified"].append({
                        "name": provider["name"],
                        "serviceType": provider["serviceType"],
                        "changes": changes
                    })
                else:
                    self.stats["unchanged"] += 1
        
        # 廃止検出 — CSV がカバーする範囲（都道府県×サービス種別）に限定する。
        # 部分 CSV（特定県・特定サービスのみ）と全件を単純差分すると、CSV に
        # 含まれないだけの既存事業所を一括で誤って Closed にしてしまう。
        covered_scopes = {
            (p.get("prefecture", ""), p.get("serviceType", "")) for p in new_providers
        }
        in_scope_ids = {
            pid for pid, ex in existing_providers.items()
            if (ex.get("prefecture", ""), ex.get("serviceType", "")) in covered_scopes
        }
        closed_ids = list(in_scope_ids - new_ids)
        self.stats["closed"] = len(closed_ids)

        # 大量廃止の誤爆検知。カバー範囲内の過半数が廃止判定なら CSV の欠落を疑う。
        if in_scope_ids and len(closed_ids) > len(in_scope_ids) * 0.5:
            print(
                f"⚠️ 警告: カバー範囲内 {len(in_scope_ids)} 件のうち {len(closed_ids)} 件が"
                "廃止判定です。CSV の欠落や対象範囲の誤りの可能性があります。"
                "必ず --dry-run で内容を確認してください。"
            )

        for closed_id in closed_ids:
            existing = existing_providers[closed_id]
            self.changes["closed"].append({
                "providerId": closed_id,
                "name": existing.get("name", ""),
                "serviceType": existing.get("serviceType", "")
            })
        
        return to_add, to_update, list(closed_ids)

    def _is_modified(self, new: Dict, existing: Dict) -> bool:
        """変更があるか判定"""
        compare_fields = ["name", "address", "city", "phone", "capacity", "serviceType"]
        for field in compare_fields:
            if str(new.get(field, "")) != str(existing.get(field, "")):
                return True
        return False

    def _get_diff(self, new: Dict, existing: Dict) -> List[str]:
        """変更点を取得"""
        diffs = []
        compare_fields = ["name", "address", "city", "phone", "capacity", "serviceType"]
        for field in compare_fields:
            new_val = str(new.get(field, ""))
            old_val = str(existing.get(field, ""))
            if new_val != old_val:
                diffs.append(f"{field}: {old_val} → {new_val}")
        return diffs

    def check_affected_clients(self, closed_ids: List[str]):
        """廃止事業所を利用中のクライアントを確認"""
        if not closed_ids:
            return
        
        with self.driver.session() as session:
            query = """
            MATCH (c:Client)-[r:USES_SERVICE]->(sp:ServiceProvider)
            WHERE sp.providerId IN $closed_ids
              AND r.status = 'Active'
            RETURN c.name AS clientName, sp.name AS providerName, sp.serviceType AS serviceType
            """
            result = session.run(query, closed_ids=closed_ids)
            
            for record in result:
                self.changes["affected_clients"].append({
                    "clientName": record["clientName"],
                    "providerName": record["providerName"],
                    "serviceType": record["serviceType"]
                })

    def sync_to_neo4j(
        self, 
        to_add: List[Dict], 
        to_update: List[Dict], 
        closed_ids: List[str],
        batch_size: int = 100
    ):
        """
        Neo4jにデータを同期
        
        Args:
            to_add: 追加するデータ
            to_update: 更新するデータ
            closed_ids: 廃止としてマークするID
            batch_size: バッチサイズ
        """
        if self.dry_run:
            print("🔍 ドライランモード: 実際のDB更新は行いません")
            return
        
        with self.driver.session() as session:
            # 新規追加
            for i in range(0, len(to_add), batch_size):
                batch = to_add[i:i + batch_size]
                self._batch_create(session, batch)
                print(f"  追加: {i + len(batch)}/{len(to_add)}")
            
            # 更新
            for i in range(0, len(to_update), batch_size):
                batch = to_update[i:i + batch_size]
                self._batch_update(session, batch)
                print(f"  更新: {i + len(batch)}/{len(to_update)}")
            
            # 廃止マーク
            if closed_ids:
                self._mark_closed(session, closed_ids)
                print(f"  廃止マーク: {len(closed_ids)}件")

    def _batch_create(self, session, providers: List[Dict]):
        """バッチで新規作成（providerId で MERGE し再実行を冪等にする）"""
        # CREATE だと再実行で providerId が重複するため MERGE を使う。
        # CSV に存在する＝現存なので status は Active、廃止マークは除去する。
        query = """
        UNWIND $providers AS p
        MERGE (sp:ServiceProvider {providerId: p.providerId})
        SET sp += p,
            sp.status = 'Active'
        REMOVE sp.closedAt
        """
        session.run(query, providers=providers)

    def _batch_update(self, session, providers: List[Dict]):
        """バッチで更新（CSV 再登場時は Closed から復活させる）"""
        # CSV に再登場した事業所は現存とみなし、status を Active に戻し
        # closedAt を除去する（p には status が含まれないため明示 SET が必要）。
        query = """
        UNWIND $providers AS p
        MATCH (sp:ServiceProvider {providerId: p.providerId})
        SET sp += p,
            sp.status = 'Active'
        REMOVE sp.closedAt
        """
        session.run(query, providers=providers)

    def _mark_closed(self, session, closed_ids: List[str]):
        """廃止としてマーク（既に Closed の事業所の closedAt は上書きしない）"""
        query = """
        MATCH (sp:ServiceProvider)
        WHERE sp.providerId IN $closed_ids
          AND coalesce(sp.status, '') <> 'Closed'
        SET sp.status = 'Closed',
            sp.closedAt = datetime()
        """
        session.run(query, closed_ids=closed_ids)

    def generate_report(self) -> str:
        """更新レポートを生成"""
        report = []
        report.append("# WAM NET事業所データ更新レポート\n")
        report.append(f"## 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if self.dry_run:
            report.append("**⚠️ ドライランモード（実際の更新は行っていません）**\n")
        
        report.append("## 更新結果サマリー\n")
        report.append("| カテゴリ | 件数 |")
        report.append("|---------|------|")
        report.append(f"| 🆕 新規登録 | {self.stats['new']}件 |")
        report.append(f"| 📝 更新 | {self.stats['modified']}件 |")
        report.append(f"| ⚠️ 廃止 | {self.stats['closed']}件 |")
        report.append(f"| ✅ 変更なし | {self.stats['unchanged']}件 |")
        report.append("")
        
        # 影響を受けるクライアント
        if self.changes["affected_clients"]:
            report.append("## ⚠️ 要確認: 廃止事業所を利用中のクライアント\n")
            report.append("| クライアント | 廃止事業所 | サービス種類 |")
            report.append("|-------------|-----------|-------------|")
            for client in self.changes["affected_clients"]:
                report.append(
                    f"| {client['clientName']} | {client['providerName']} | {client['serviceType']} |"
                )
            report.append("")
            report.append("→ **代替事業所の検討が必要です**\n")
        
        # 新規登録（抜粋）
        if self.changes["new"]:
            report.append("## 新規登録事業所（抜粋・最大10件）\n")
            report.append("| 事業所名 | サービス種類 | 市区町村 |")
            report.append("|---------|-------------|---------|")
            for provider in self.changes["new"][:10]:
                report.append(
                    f"| {provider['name']} | {provider['serviceType']} | {provider['city']} |"
                )
            report.append("")
        
        # 廃止事業所
        if self.changes["closed"]:
            report.append("## 廃止事業所\n")
            report.append("| 事業所名 | サービス種類 |")
            report.append("|---------|-------------|")
            for provider in self.changes["closed"]:
                report.append(f"| {provider['name']} | {provider['serviceType']} |")
            report.append("")
        
        return "\n".join(report)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="WAM NET事業所データをNeo4jに同期"
    )
    parser.add_argument(
        "--csv-file", "-f",
        required=True,
        help="WAM NET CSVファイルのパス"
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["full", "diff"],
        default="diff",
        help="同期モード: full=全件置換, diff=差分更新（デフォルト）"
    )
    parser.add_argument(
        "--prefecture", "-p",
        default="",
        help="都道府県でフィルタ（例: 福岡県）"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="ドライラン（実際のDB更新を行わない）"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=100,
        help="バッチサイズ（デフォルト: 100）"
    )
    parser.add_argument(
        "--output", "-o",
        help="レポート出力先（指定しない場合は標準出力）"
    )
    
    args = parser.parse_args()
    
    # CSVファイル存在確認
    if not os.path.exists(args.csv_file):
        print(f"❌ CSVファイルが見つかりません: {args.csv_file}")
        sys.exit(1)
    
    print("=" * 60)
    print("WAM NET事業所データ同期")
    print("=" * 60)
    print(f"CSVファイル: {args.csv_file}")
    print(f"同期モード: {args.mode}")
    print(f"ドライラン: {args.dry_run}")
    print("=" * 60)
    
    sync = ServiceProviderSync(dry_run=args.dry_run)
    
    try:
        # Neo4j接続
        sync.connect()
        
        # CSV読み込み
        new_providers = sync.parse_csv(args.csv_file)
        
        # 都道府県フィルタ
        if args.prefecture:
            new_providers = [
                p for p in new_providers 
                if args.prefecture in p.get("prefecture", "")
            ]
            print(f"📍 都道府県フィルタ適用: {len(new_providers)}件")
        
        if args.mode == "diff":
            # 差分検出
            existing = sync.get_existing_providers(args.prefecture)
            print(f"📊 既存データ: {len(existing)}件")
            
            to_add, to_update, closed_ids = sync.detect_changes(new_providers, existing)
            
            # 影響を受けるクライアント確認
            sync.check_affected_clients(closed_ids)
            
            # 同期実行
            sync.sync_to_neo4j(to_add, to_update, closed_ids, args.batch_size)
            
        else:  # full mode
            print("⚠️ フルモード: 既存データを上書きします")
            # TODO: フルモードの実装
            pass
        
        # レポート生成
        report = sync.generate_report()
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\n📄 レポートを保存しました: {args.output}")
        else:
            print("\n" + report)
        
        print("\n✅ 同期完了")
        
    except WAMNetSyncError as e:
        print(f"\n❌ エラー: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        sync.close()


if __name__ == "__main__":
    main()
