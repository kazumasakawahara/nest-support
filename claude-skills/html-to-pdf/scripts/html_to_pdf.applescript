#!/usr/bin/osascript
-- HTML to PDF 変換スクリプト
-- 使用方法: osascript html_to_pdf.applescript "/path/to/file.html"

on run argv
    if (count of argv) < 1 then
        return "使用方法: osascript html_to_pdf.applescript \"/path/to/file.html\""
    end if
    
    set htmlPath to item 1 of argv
    
    -- HTMLファイルをChromeで開く
    tell application "Google Chrome"
        activate
        open location "file://" & htmlPath
    end tell
    
    -- ページの読み込みを待つ
    delay 1.5
    
    -- 印刷ダイアログを開く (Cmd+P)
    tell application "System Events"
        tell process "Google Chrome"
            keystroke "p" using command down
        end tell
    end tell
    
    return "印刷ダイアログを開きました。「送信先」で「PDFに保存」を選択してください。"
end run
