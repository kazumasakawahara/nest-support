#!/usr/bin/env python3
"""
WAM NETオープンデータダウンロードヘルパー

WAM NETからオープンデータをダウンロードする際の案内と、
ダウンロード済みファイルの管理を行います。

※ WAM NETはログイン不要でオープンデータをダウンロード可能ですが、
   自動ダウンロードには対応していないため、手動ダウンロードを案内します。
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


# WAM NETオープンデータのURL（手動ダウンロード用）
WAMNET_OPENDATA_URL = "https://www.wam.go.jp/wamappl/shogaiservice_opendata.html"

# データディレクトリ
DATA_DIR = Path(__file__).parent.parent / "data"
CURRENT_DIR = DATA_DIR / "current"
ARCHIVE_DIR = DATA_DIR / "archive"


def setup_directories():
    """データディレクトリを作成"""
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ データディレクトリを準備しました:")
    print(f"   現在データ: {CURRENT_DIR}")
    print(f"   アーカイブ: {ARCHIVE_DIR}")


def show_download_instructions(prefecture_code: str = "40"):
    """ダウンロード手順を表示"""
    config_path = Path(__file__).parent.parent / "config" / "prefectures.json"
    
    prefecture_name = "福岡県"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            prefecture_name = config.get("prefectures", {}).get(prefecture_code, prefecture_name)
    
    print("\n" + "=" * 60)
    print("WAM NETオープンデータのダウンロード手順")
    print("=" * 60)
    print(f"""
1. 以下のURLにアクセス:
   {WAMNET_OPENDATA_URL}

2. 「障害福祉サービス等情報」セクションを探す

3. 都道府県を選択: {prefecture_name}（コード: {prefecture_code}）

4. CSVファイルをダウンロード
   - ファイル名例: shogai_fukuoka_YYYYMM.csv

5. ダウンロードしたファイルを以下に配置:
   {CURRENT_DIR}/

6. 同期スクリプトを実行:
   python sync_providers.py --csv-file {CURRENT_DIR}/ダウンロードしたファイル.csv

※ WAM NETのデータは年2回（4月・10月頃）更新されます
""")
    print("=" * 60 + "\n")


def archive_current(description: str = ""):
    """現在のデータをアーカイブ"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 現在のデータディレクトリのファイルをアーカイブ
    archived_files = []
    for file in CURRENT_DIR.glob("*.csv"):
        archive_name = f"{file.stem}_{timestamp}{file.suffix}"
        archive_path = ARCHIVE_DIR / archive_name
        shutil.copy2(file, archive_path)
        archived_files.append(archive_name)
    
    if archived_files:
        print(f"✅ {len(archived_files)}ファイルをアーカイブしました:")
        for f in archived_files:
            print(f"   - {f}")
        
        # メタデータを保存
        meta = {
            "archived_at": timestamp,
            "description": description,
            "files": archived_files
        }
        meta_path = ARCHIVE_DIR / f"archive_{timestamp}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    else:
        print("ℹ️ アーカイブするファイルがありません")


def list_archives():
    """アーカイブ一覧を表示"""
    print("\n📁 アーカイブ一覧:\n")
    
    meta_files = sorted(ARCHIVE_DIR.glob("archive_*.json"), reverse=True)
    
    if not meta_files:
        print("  アーカイブはありません")
        return
    
    for meta_path in meta_files[:10]:  # 最新10件
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        
        print(f"  📅 {meta.get('archived_at', 'unknown')}")
        if meta.get("description"):
            print(f"     {meta['description']}")
        for file in meta.get("files", []):
            print(f"     - {file}")
        print()


def list_current():
    """現在のデータファイル一覧を表示"""
    print("\n📂 現在のデータファイル:\n")
    
    csv_files = list(CURRENT_DIR.glob("*.csv"))
    
    if not csv_files:
        print("  データファイルがありません")
        print("  → ダウンロード手順を確認: python download_wamnet.py --instructions")
        return
    
    for file in csv_files:
        stat = file.stat()
        size_kb = stat.st_size / 1024
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  - {file.name}")
        print(f"    サイズ: {size_kb:.1f}KB, 更新: {mtime}")
    print()


def import_file(file_path: str, description: str = ""):
    """外部ファイルをcurrentにインポート"""
    src = Path(file_path)
    if not src.exists():
        print(f"❌ ファイルが見つかりません: {file_path}")
        return False
    
    # 既存ファイルをアーカイブ
    archive_current(f"Import前のバックアップ: {description}")
    
    # ファイルをコピー
    dst = CURRENT_DIR / src.name
    shutil.copy2(src, dst)
    print(f"✅ ファイルをインポートしました: {dst}")
    return True


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="WAM NETオープンデータダウンロードヘルパー"
    )
    subparsers = parser.add_subparsers(dest="command", help="コマンド")
    
    # setup
    setup_parser = subparsers.add_parser("setup", help="データディレクトリを作成")
    
    # instructions
    inst_parser = subparsers.add_parser("instructions", help="ダウンロード手順を表示")
    inst_parser.add_argument(
        "--prefecture", "-p",
        default="40",
        help="都道府県コード（デフォルト: 40=福岡県）"
    )
    
    # archive
    arch_parser = subparsers.add_parser("archive", help="現在のデータをアーカイブ")
    arch_parser.add_argument(
        "--description", "-d",
        default="",
        help="アーカイブの説明"
    )
    
    # list
    list_parser = subparsers.add_parser("list", help="データファイル一覧を表示")
    list_parser.add_argument(
        "--archives", "-a",
        action="store_true",
        help="アーカイブ一覧を表示"
    )
    
    # import
    import_parser = subparsers.add_parser("import", help="外部ファイルをインポート")
    import_parser.add_argument(
        "file",
        help="インポートするファイルパス"
    )
    import_parser.add_argument(
        "--description", "-d",
        default="",
        help="インポートの説明"
    )
    
    args = parser.parse_args()
    
    if args.command == "setup":
        setup_directories()
    elif args.command == "instructions":
        show_download_instructions(args.prefecture)
    elif args.command == "archive":
        setup_directories()
        archive_current(args.description)
    elif args.command == "list":
        setup_directories()
        if args.archives:
            list_archives()
        else:
            list_current()
    elif args.command == "import":
        setup_directories()
        import_file(args.file, args.description)
    else:
        # デフォルト: 手順を表示
        show_download_instructions()


if __name__ == "__main__":
    main()
