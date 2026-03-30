# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Claude Desktop 設定自動化スクリプト（Windows版）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# 使い方:
#   .\installer\configure-claude.ps1
#
# このスクリプトが行うこと:
#   1. Claude Desktop 設定ファイルの存在確認
#   2. 既存設定のバックアップ
#   3. Neo4j MCP サーバーの設定追加（既存設定とマージ）
#   4. 接続テストの実行
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# ヘルパー関数
function Write-Info    { param($msg) Write-Host "[情報] " -ForegroundColor Blue -NoNewline; Write-Host $msg }
function Write-Success { param($msg) Write-Host "[完了] " -ForegroundColor Green -NoNewline; Write-Host $msg }
function Write-Warn    { param($msg) Write-Host "[注意] " -ForegroundColor Yellow -NoNewline; Write-Host $msg }
function Write-Err     { param($msg) Write-Host "[エラー] " -ForegroundColor Red -NoNewline; Write-Host $msg }

# Claude Desktop 設定パス
$CLAUDE_CONFIG_DIR = Join-Path $env:APPDATA "Claude"
$CLAUDE_CONFIG_FILE = Join-Path $CLAUDE_CONFIG_DIR "claude_desktop_config.json"

Write-Host ""
Write-Host "━━━ Claude Desktop 設定ツール（Windows版）━━━" -ForegroundColor Magenta
Write-Host ""

# 1. 設定ディレクトリの確認
if (-not (Test-Path $CLAUDE_CONFIG_DIR)) {
    Write-Info "設定ディレクトリを作成します: $CLAUDE_CONFIG_DIR"
    New-Item -ItemType Directory -Path $CLAUDE_CONFIG_DIR -Force | Out-Null
}

# 2. 既存設定のバックアップ
if (Test-Path $CLAUDE_CONFIG_FILE) {
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $backupFile = "$CLAUDE_CONFIG_FILE.backup.$timestamp"
    Copy-Item $CLAUDE_CONFIG_FILE $backupFile
    Write-Success "バックアップ作成: $(Split-Path $backupFile -Leaf)"

    # 既に neo4j MCP が設定されているかチェック
    $configContent = Get-Content $CLAUDE_CONFIG_FILE -Raw
    if ($configContent -match '"neo4j"') {
        Write-Warn "既に neo4j MCP が設定されています。"
        $response = Read-Host "  上書きしますか？ [y/N]"
        if ($response -notmatch "^[Yy]$") {
            Write-Info "既存の設定を維持します。"

            # 接続テスト
            Write-Host ""
            Write-Info "接続テスト..."
            try {
                $null = Invoke-WebRequest -Uri "http://localhost:7474" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
                Write-Success "Neo4j (port 7687): 接続OK"
            } catch {
                Write-Warn "Neo4j (port 7687): 未接続（Docker が起動していない可能性があります）"
            }
            exit 0
        }
    }
}

# 3. MCP 設定の生成
$mcpConfig = @{
    mcpServers = @{
        neo4j = @{
            command = "npx"
            args    = @("-y", "@alanse/mcp-neo4j-server")
            env     = @{
                NEO4J_URI      = "bolt://localhost:7687"
                NEO4J_USERNAME = "neo4j"
                NEO4J_PASSWORD = "password"
            }
        }
        "livelihood-support-db" = @{
            command = "npx"
            args    = @("-y", "@alanse/mcp-neo4j-server")
            env     = @{
                NEO4J_URI      = "bolt://localhost:7688"
                NEO4J_USERNAME = "neo4j"
                NEO4J_PASSWORD = "password"
            }
        }
    }
}

if (Test-Path $CLAUDE_CONFIG_FILE) {
    # 既存設定にマージ
    Write-Info "既存の設定に Neo4j MCP を追加中..."
    try {
        $existingConfig = Get-Content $CLAUDE_CONFIG_FILE -Raw | ConvertFrom-Json

        if (-not $existingConfig.mcpServers) {
            $existingConfig | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue @{} -Force
        }

        $existingConfig.mcpServers | Add-Member -NotePropertyName "neo4j" -NotePropertyValue $mcpConfig.mcpServers.neo4j -Force
        $existingConfig.mcpServers | Add-Member -NotePropertyName "livelihood-support-db" -NotePropertyValue $mcpConfig.mcpServers."livelihood-support-db" -Force

        $existingConfig | ConvertTo-Json -Depth 10 | Set-Content $CLAUDE_CONFIG_FILE -Encoding UTF8
        Write-Success "Neo4j MCP を既存の設定にマージしました"
    } catch {
        Write-Warn "マージに失敗しました。設定ファイルを新規作成します。"
        $mcpConfig | ConvertTo-Json -Depth 10 | Set-Content $CLAUDE_CONFIG_FILE -Encoding UTF8
        Write-Success "設定ファイルを作成しました"
    }
} else {
    # 新規作成
    Write-Info "設定ファイルを新規作成します..."
    $mcpConfig | ConvertTo-Json -Depth 10 | Set-Content $CLAUDE_CONFIG_FILE -Encoding UTF8
    Write-Success "設定ファイルを作成しました: $CLAUDE_CONFIG_FILE"
}

# 4. 接続テスト
Write-Host ""
Write-Info "接続テスト..."

try {
    $null = Invoke-WebRequest -Uri "http://localhost:7474" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Success "Neo4j (port 7687): 接続OK"
} catch {
    Write-Warn "Neo4j (port 7687): 未接続"
    Write-Host "  → docker compose up -d で Neo4j を起動してください"
}

try {
    $null = Invoke-WebRequest -Uri "http://localhost:7475" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Success "Neo4j (port 7688): 接続OK"
} catch {
    Write-Warn "Neo4j (port 7688): 未接続"
}

Write-Host ""
Write-Host "  設定が完了しました。Claude Desktop を再起動してください。" -ForegroundColor Green
Write-Host ""
