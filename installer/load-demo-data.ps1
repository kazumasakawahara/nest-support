# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# デモデータの投入・削除スクリプト（Windows版）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# 使い方:
#   .\installer\load-demo-data.ps1          # デモデータを投入
#   .\installer\load-demo-data.ps1 -Remove  # デモデータを削除
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

param(
    [switch]$Remove
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$DEMO_FILE = Join-Path $SCRIPT_DIR "demo-data.cypher"
$NEO4J_URL = "http://localhost:7474/db/neo4j/tx/commit"
$NEO4J_AUTH = "neo4j:password"

# ヘルパー関数
function Write-Info    { param($msg) Write-Host "[情報] " -ForegroundColor Blue -NoNewline; Write-Host $msg }
function Write-Success { param($msg) Write-Host "[完了] " -ForegroundColor Green -NoNewline; Write-Host $msg }
function Write-Warn    { param($msg) Write-Host "[注意] " -ForegroundColor Yellow -NoNewline; Write-Host $msg }
function Write-Err     { param($msg) Write-Host "[エラー] " -ForegroundColor Red -NoNewline; Write-Host $msg }

# Neo4j 接続確認
function Test-Neo4j {
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:7474" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Success "Neo4j 接続確認OK"
        return $true
    } catch {
        Write-Err "Neo4j が起動していません。先に docker compose up -d を実行してください。"
        return $false
    }
}

# Cypher クエリを実行する関数
function Invoke-Cypher {
    param($query)

    $authBytes = [System.Text.Encoding]::UTF8.GetBytes($NEO4J_AUTH)
    $authBase64 = [Convert]::ToBase64String($authBytes)

    $body = @{
        statements = @(
            @{ statement = $query }
        )
    } | ConvertTo-Json -Depth 5

    try {
        $response = Invoke-RestMethod -Uri $NEO4J_URL `
            -Method Post `
            -Headers @{ Authorization = "Basic $authBase64" } `
            -ContentType "application/json; charset=utf-8" `
            -Body $body `
            -ErrorAction Stop

        if ($response.errors -and $response.errors.Count -gt 0) {
            foreach ($err in $response.errors) {
                Write-Err $err.message
            }
            return $false
        }
        return $true
    } catch {
        Write-Err "クエリの実行に失敗しました: $_"
        return $false
    }
}

# スカラー値を返す Cypher クエリを実行する関数（取得できなければ -1 を返す）
function Get-CypherScalar {
    param($query)

    $authBytes = [System.Text.Encoding]::UTF8.GetBytes($NEO4J_AUTH)
    $authBase64 = [Convert]::ToBase64String($authBytes)

    $body = @{
        statements = @(
            @{ statement = $query }
        )
    } | ConvertTo-Json -Depth 5

    try {
        $response = Invoke-RestMethod -Uri $NEO4J_URL `
            -Method Post `
            -Headers @{ Authorization = "Basic $authBase64" } `
            -ContentType "application/json; charset=utf-8" `
            -Body $body `
            -ErrorAction Stop

        if ($response.errors -and $response.errors.Count -gt 0) {
            return -1
        }
        return [int]$response.results[0].data[0].row[0]
    } catch {
        return -1
    }
}

# 投入前ガード: demoId を持たない実ノードが存在する場合は既定で中断する
function Confirm-NoRealData {
    $realCount = Get-CypherScalar "MATCH (n) WHERE n.demoId IS NULL RETURN count(n) AS c"

    if ($realCount -eq -1) {
        Write-Warn "既存ノード数を確認できませんでした（Neo4j 応答の解析に失敗）。"
        $ans = Read-Host "  それでもデモデータを投入しますか？ [y/N]"
        if ($ans -notmatch "^[Yy]$") {
            Write-Info "投入をキャンセルしました。"
            exit 0
        }
        return
    }

    if ($realCount -eq 0) {
        # DB が空、または既存ノードが全て demoId を持つ（＝過去のデモのみ）
        return
    }

    Write-Warn "実データ（demoId を持たないノード）が $realCount 件検出されました。"
    Write-Warn "デモデータ投入は demoId ベースで実データを汚染しませんが、"
    Write-Warn "本番データとデモの混在を避けるため、既定では投入を中断します。"
    $ans = Read-Host "  実データがある状態でデモデータを投入しますか？ [y/N]"
    if ($ans -notmatch "^[Yy]$") {
        Write-Info "投入を中断しました。（デモは空 DB / デモ専用 DB での利用を推奨）"
        exit 0
    }
    Write-Warn "ユーザー確認により、実データがある状態で投入を続行します。"
}

# デモデータ投入
function Load-DemoData {
    Write-Info "デモデータを投入中..."

    if (-not (Test-Path $DEMO_FILE)) {
        Write-Err "デモデータファイルが見つかりません: $DEMO_FILE"
        exit 1
    }

    # 投入前ガード: 実データ（demoId なし）を検出したら既定で中断
    Confirm-NoRealData

    $content = Get-Content $DEMO_FILE -Encoding UTF8
    $currentStmt = ""
    $count = 0

    foreach ($line in $content) {
        # コメント行と空行をスキップ
        if ($line -match "^\s*//" -or $line.Trim() -eq "") { continue }

        $currentStmt += " $line"

        # セミコロンで終わる行でステートメント実行
        if ($line -match ";\s*$") {
            $currentStmt = $currentStmt.TrimEnd().TrimEnd(";").Trim()

            if ($currentStmt -ne "") {
                if (Invoke-Cypher $currentStmt) {
                    $count++
                } else {
                    Write-Warn "ステートメント $count でエラーが発生（続行します）"
                }
            }
            $currentStmt = ""
        }
    }

    Write-Success "デモデータの投入が完了しました（$count ステートメント実行）"
    Write-Host ""
    Write-Host "  Claude Desktop で以下を試してみてください:"
    Write-Host "  「山本翔太さんのプロフィールを見せて」" -ForegroundColor Cyan
    Write-Host "  「鈴木花さんの禁忌事項を教えて」" -ForegroundColor Cyan
    Write-Host "  「データベースの統計情報を表示して」" -ForegroundColor Cyan
    Write-Host ""
}

# デモデータ削除
function Remove-DemoData {
    Write-Warn "デモデータを削除します。"
    $response = Read-Host "  本当に削除しますか？ [y/N]"
    if ($response -notmatch "^[Yy]$") {
        Write-Info "削除をキャンセルしました。"
        exit 0
    }

    Write-Info "デモデータを削除中..."

    # demoId を持つノード（＝デモ由来）のみを削除。実ノードは demoId を
    # 持たないため決して削除対象にならない。SupportLog / AuditLog も網羅される。
    if (Invoke-Cypher "MATCH (n) WHERE n.demoId IS NOT NULL DETACH DELETE n") {
        Write-Success "demoId を持つデモノードを削除しました"
    }

    if (Invoke-Cypher "MATCH (sl:SupportLog) WHERE sl.demoId IS NOT NULL DETACH DELETE sl") {
        Write-Success "デモ支援記録を削除しました"
    }

    if (Invoke-Cypher "MATCH (al:AuditLog) WHERE al.demoId IS NOT NULL DELETE al") {
        Write-Success "デモ監査ログを削除しました"
    }

    Write-Success "デモデータの削除が完了しました"
}

# メイン処理
if (-not (Test-Neo4j)) { exit 1 }

if ($Remove) {
    Remove-DemoData
} else {
    Load-DemoData
}
