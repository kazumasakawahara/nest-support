---
name: html-to-pdf
description: HTMLファイルをPDFに変換するスキル。Chromeの印刷機能を使用してHTMLをPDFに変換する。「HTMLをPDFに変換」「HTMLからPDF作成」「PDFとして保存」などのリクエストで使用。Mac環境でAppleScriptとChromeを使用。
---

# HTML to PDF 変換スキル

MacのChromeブラウザを使ってHTMLファイルをPDFに変換する。

## 前提条件

- macOS環境
- Google Chromeがインストールされていること
- `Control your Mac:osascript` ツールが利用可能であること

## 変換手順

### ステップ1: ChromeでHTMLファイルを開く

```applescript
tell application "Google Chrome"
    activate
    open location "file://{HTMLファイルのフルパス}"
end tell
```

または `Control Chrome:open_url` ツールを使用:
```
url: file:///Users/k-kawahara/path/to/file.html
```

### ステップ2: 印刷ダイアログを開く

```applescript
tell application "Google Chrome"
    activate
end tell

delay 0.5

tell application "System Events"
    tell process "Google Chrome"
        keystroke "p" using command down
    end tell
end tell
```

### ステップ3: ユーザーに操作を依頼

印刷ダイアログが開いたら、ユーザーに以下の操作を依頼:

1. **「送信先」** で **「PDFに保存」** を選択
2. **「保存」** をクリック
3. 保存先フォルダを選択
4. ファイル名を入力して保存

## 実装例

ClaudeがAppleScriptを実行する場合:

```
Control your Mac:osascript で以下を実行:

tell application "Google Chrome"
    activate
    open location "file:///Users/k-kawahara/Downloads/example.html"
end tell

delay 1

tell application "System Events"
    tell process "Google Chrome"
        keystroke "p" using command down
    end tell
end tell
```

## 注意事項

- PDF保存時の「送信先」選択と保存先指定はユーザーが手動で行う
- ファイルパスにスペースや日本語が含まれる場合はURLエンコードが必要な場合あり
- Chromeが起動していない場合は `delay` を長めに設定
