---
name: html-to-pdf
description: HTMLファイルをPDFに変換するスキル。ヘッドレスChromeの --print-to-pdf で全自動変換する（ユーザー操作不要）。「HTMLをPDFに変換」「HTMLからPDF作成」「PDFとして保存」などのリクエストで使用。Mac環境でGoogle Chromeを使用。
---

# HTML to PDF 変換スキル

MacのChromeをヘッドレスモードで使い、HTMLファイルをPDFに**全自動**で変換する。
印刷ダイアログやユーザーの手動操作は不要。

## 前提条件

- macOS環境
- Google Chromeがインストールされていること（`/Applications/Google Chrome.app`）

## 変換手順（推奨: ヘッドレス全自動）

Bashツール（またはシェル実行手段）で以下を実行するだけで完了する。

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu \
  --no-pdf-header-footer \
  --print-to-pdf="/path/to/output.pdf" \
  "file:///path/to/input.html"
```

- 入力はフルパスの `file://` URL で指定する（スペース・日本語を含む場合はURLエンコード）
- 出力先 `--print-to-pdf=` もフルパスで指定する
- ユーザーのChromeが起動中でも干渉しない（ヘッドレスは別プロセスで動く）
- 日本語・絵文字のレンダリングは検証済み（文字化けしない）

### 実行後の確認

```bash
file /path/to/output.pdf   # "PDF document" と表示されればOK
```

生成された PDF のパスをユーザーに提示する。

### オプション

| フラグ | 用途 |
|--------|------|
| `--no-pdf-header-footer` | ヘッダー（日時・URL）とフッターを消す。レポート出力では基本付ける |
| `--print-to-pdf-no-header` | 旧バージョンのChrome用の同等フラグ |
| `--virtual-time-budget=5000` | JS描画（グラフ等）の完了を最大5秒待ってから印刷する |

### 印刷スタイルの調整

用紙サイズや余白はコマンドではなくHTML側のCSSで制御する:

```css
@page { size: A4; margin: 12mm; }
@media print { .no-print { display: none; } }
```

## トラブルシューティング

- **プロファイルロックのエラーが出る場合**: `--user-data-dir=$(mktemp -d)` を追加して一時プロファイルで実行する
- **`task_policy_set ... invalid argument` という stderr 出力**: macOSの無害なノイズ。PDFが生成されていれば無視してよい
- **D3.js等の動的描画が空白になる**: `--virtual-time-budget=5000` を追加する

## 代替手順（手動: 印刷ダイアログを使いたい場合）

ユーザーが用紙設定等を自分で調整したい場合のみ、従来のAppleScript方式を使う。
`Control your Mac:osascript`（またはosascript実行手段）で:

```applescript
tell application "Google Chrome"
    activate
    open location "file:///Users/k-kawahara/path/to/file.html"
end tell

delay 1

tell application "System Events"
    tell process "Google Chrome"
        keystroke "p" using command down
    end tell
end tell
```

印刷ダイアログが開いたら、ユーザーに「送信先 →『PDFに保存』→ 保存」の操作を依頼する。
