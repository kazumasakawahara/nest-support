# WAM NETデータディレクトリ

このディレクトリはWAM NETからダウンロードしたCSVファイルを格納します。

## ディレクトリ構成

```
data/
├── current/     # 現在のデータファイル
│   └── *.csv    # WAM NETからダウンロードしたCSV
└── archive/     # アーカイブ（過去のデータ）
    ├── *.csv    # 日時付きでバックアップされたCSV
    └── archive_YYYYMMDD_HHMMSS.json  # アーカイブメタデータ
```

## 使い方

1. WAM NETからCSVをダウンロード
   ```bash
   python scripts/download_wamnet.py instructions
   ```

2. ダウンロードしたファイルを`current/`に配置

3. 同期スクリプトを実行
   ```bash
   python scripts/sync_providers.py --csv-file data/current/downloaded_file.csv
   ```

## 注意事項

- CSVファイルはgit管理対象外です（.gitignore設定済み）
- 同期前に自動的にアーカイブが作成されます
- アーカイブのメタデータ（.json）はgit管理対象です
