# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# nest-support ワンクリックインストーラー（Windows版）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# 使い方:
#   PowerShell を「管理者として実行」で開き:
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   .\installer\install-windows.ps1
#
#   または（リモート実行）:
#   irm https://raw.githubusercontent.com/kazumasakawahara/nest-support/main/installer/install-windows.ps1 | iex
#
# このスクリプトが行うこと:
#   1. 前提条件（Docker Desktop, Node.js）の確認・インストール案内
#   2. nest-support リポジトリのダウンロード
#   3. Neo4j データベースの起動
#   4. Claude Skills のインストール
#   5. Claude Desktop 設定ファイルへの MCP サーバー追加
#   6. デモデータの投入（オプション）
#   7. 接続テストの実行
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 文字コード設定（日本語対応）
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 定数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

$VERSION = "1.0.0"
$REPO_URL = "https://github.com/kazumasakawahara/nest-support.git"
$DEFAULT_INSTALL_DIR = Join-Path $env:USERPROFILE "Documents\nest-support"
$CLAUDE_CONFIG_DIR = Join-Path $env:APPDATA "Claude"
$CLAUDE_CONFIG_FILE = Join-Path $CLAUDE_CONFIG_DIR "claude_desktop_config.json"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ヘルパー関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function Write-Info    { param($msg) Write-Host "[情報] " -ForegroundColor Blue -NoNewline; Write-Host $msg }
function Write-Success { param($msg) Write-Host "[完了] " -ForegroundColor Green -NoNewline; Write-Host $msg }
function Write-Warn    { param($msg) Write-Host "[注意] " -ForegroundColor Yellow -NoNewline; Write-Host $msg }
function Write-Err     { param($msg) Write-Host "[エラー] " -ForegroundColor Red -NoNewline; Write-Host $msg }
function Write-Step    { param($msg) Write-Host "`n━━━ $msg ━━━`n" -ForegroundColor Magenta }

function Ask-YesNo {
    param($prompt)
    $response = Read-Host "$prompt [Y/n]"
    return ($response -eq "" -or $response -match "^[Yy]")
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ウェルカムメッセージ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function Show-Welcome {
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Magenta
    Write-Host "  ║                                              ║" -ForegroundColor Magenta
    Write-Host "  ║   nest-support インストーラー v$VERSION        ║" -ForegroundColor Magenta
    Write-Host "  ║   〜 親亡き後支援データベース 〜              ║" -ForegroundColor Magenta
    Write-Host "  ║            （Windows版）                     ║" -ForegroundColor Magenta
    Write-Host "  ║                                              ║" -ForegroundColor Magenta
    Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "  このスクリプトは、nest-support のセットアップを"
    Write-Host "  対話形式で案内します。"
    Write-Host ""
    Write-Host "  所要時間の目安: 10〜20分"
    Write-Host "  （Docker Desktop が未インストールの場合はもう少しかかります）"
    Write-Host ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 1: 前提条件チェック
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function Check-Windows {
    if ($env:OS -ne "Windows_NT") {
        Write-Err "このインストーラーは Windows 専用です。"
        Write-Err "macOS をお使いの場合は installer/install-mac.sh を使用してください。"
        exit 1
    }

    # Windows バージョン確認
    $osVersion = [System.Environment]::OSVersion.Version
    Write-Success "Windows を確認しました: Windows $($osVersion.Major).$($osVersion.Minor) (Build $($osVersion.Build))"

    # WSL2 の確認（推奨）
    if (Get-Command wsl -ErrorAction SilentlyContinue) {
        Write-Success "WSL が利用可能です"
    } else {
        Write-Warn "WSL がインストールされていません。Docker Desktop は WSL2 バックエンドを推奨しています。"
    }
}

function Check-Docker {
    Write-Step "Step 1/6: Docker Desktop の確認"

    # Docker コマンドの存在確認
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        try {
            $null = docker info 2>$null
            if ($LASTEXITCODE -eq 0) {
                $dockerVersion = docker --version
                Write-Success "Docker Desktop が動作中です: $dockerVersion"
                return
            }
        } catch {}

        # Docker はあるが起動していない
        Write-Warn "Docker はインストールされていますが、起動していません。"
        Write-Host ""
        Write-Host "  Docker Desktop を起動してください:"
        Write-Host "  1. スタートメニューから「Docker Desktop」を検索して開く"
        Write-Host "  2. タスクバーにクジラのアイコンが表示されるまで待つ"
        Write-Host "     （初回起動は1〜2分かかります）"
        Write-Host ""
        Read-Host "  Docker Desktop を起動しましたか？ [Enter で続行]"

        try {
            $null = docker info 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Docker Desktop が起動しました"
                return
            }
        } catch {}

        Write-Err "Docker Desktop がまだ起動していないようです。起動後に再実行してください。"
        exit 1
    }

    # Docker 未インストール
    Write-Warn "Docker Desktop がインストールされていません。"
    Write-Host ""
    Write-Host "  Docker Desktop は、データベースを動かすために必要です。"
    Write-Host ""

    if (Ask-YesNo "winget で Docker Desktop をインストールしますか？") {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Info "Docker Desktop をインストール中..."
            winget install Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
            Write-Host ""
            Write-Host "  Docker Desktop がインストールされました。"
            Write-Host "  パソコンの再起動が必要な場合があります。"
            Write-Host "  再起動後、Docker Desktop を起動してからこのスクリプトを再実行してください。"
            exit 0
        } else {
            Write-Warn "winget が利用できません。"
        }
    }

    Write-Host ""
    Write-Host "  以下の URL から Docker Desktop をダウンロードしてください:"
    Write-Host "  https://www.docker.com/products/docker-desktop/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  インストール・起動後にこのスクリプトを再実行してください。"
    exit 1
}

function Check-Node {
    Write-Step "Step 2/6: Node.js の確認"

    if (Get-Command npx -ErrorAction SilentlyContinue) {
        $nodeVersion = node --version 2>$null
        Write-Success "Node.js がインストール済みです: $nodeVersion"
        return
    }

    Write-Warn "Node.js がインストールされていません。"
    Write-Host ""
    Write-Host "  Node.js は、Claude Desktop とデータベースをつなぐために必要です。"
    Write-Host ""

    if (Ask-YesNo "winget で Node.js をインストールしますか？") {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Info "Node.js をインストール中..."
            winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
            # PATH の更新
            $env:PATH = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
            if (Get-Command npx -ErrorAction SilentlyContinue) {
                Write-Success "Node.js がインストールされました"
                return
            } else {
                Write-Warn "Node.js のインストールは完了しましたが、PATH の反映にはターミナルの再起動が必要です。"
                Write-Host "  PowerShell を閉じて開き直し、再実行してください。"
                exit 0
            }
        }
    }

    Write-Host ""
    Write-Host "  以下の URL から Node.js をダウンロードしてください:"
    Write-Host "  https://nodejs.org/ （LTS版を推奨）" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

function Check-ClaudeDesktop {
    # Claude Desktop のインストール確認
    $claudePaths = @(
        "$env:LOCALAPPDATA\Programs\claude-desktop\Claude.exe",
        "$env:LOCALAPPDATA\Claude\Claude.exe",
        "$env:ProgramFiles\Claude\Claude.exe"
    )

    $found = $false
    foreach ($path in $claudePaths) {
        if (Test-Path $path) {
            Write-Success "Claude Desktop がインストール済みです"
            $found = $true
            break
        }
    }

    if (-not $found) {
        Write-Warn "Claude Desktop が見つかりません。"
        Write-Host ""
        Write-Host "  以下の URL からダウンロード・インストールしてください:"
        Write-Host "  https://claude.ai/download" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  ※ インストールは後でも大丈夫です。先にデータベースのセットアップを進めます。"
        Write-Host ""
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 3: プロジェクトのダウンロード
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function Download-Project {
    Write-Step "Step 3/6: プロジェクトファイルのダウンロード"

    # 既にプロジェクトディレクトリ内から実行されている場合
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    $parentDir = Split-Path -Parent $scriptDir

    if ((Test-Path (Join-Path $parentDir "setup.sh")) -and (Test-Path (Join-Path $parentDir "claude-skills"))) {
        $script:INSTALL_DIR = $parentDir
        Write-Success "プロジェクトディレクトリを検出: $($script:INSTALL_DIR)"
        return
    }

    # ダウンロードが必要
    Write-Host "  プロジェクトファイルをダウンロードします。"
    Write-Host ""
    Write-Host "  インストール先: $DEFAULT_INSTALL_DIR"
    Write-Host ""

    if (Test-Path $DEFAULT_INSTALL_DIR) {
        Write-Warn "既にディレクトリが存在します: $DEFAULT_INSTALL_DIR"
        if (Ask-YesNo "上書き（更新）しますか？") {
            $script:INSTALL_DIR = $DEFAULT_INSTALL_DIR
        } else {
            $customPath = Read-Host "  別のインストール先を入力してください"
            $script:INSTALL_DIR = if ($customPath) { $customPath } else { $DEFAULT_INSTALL_DIR }
        }
    } else {
        $script:INSTALL_DIR = $DEFAULT_INSTALL_DIR
    }

    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Info "Git でダウンロード中..."
        if (Test-Path (Join-Path $script:INSTALL_DIR ".git")) {
            Push-Location $script:INSTALL_DIR
            git pull
            Pop-Location
        } else {
            git clone $REPO_URL $script:INSTALL_DIR
        }
    } else {
        Write-Info "ZIP でダウンロード中..."
        $zipUrl = "https://github.com/kazumasakawahara/nest-support/archive/refs/heads/main.zip"
        $tmpZip = Join-Path $env:TEMP "nest-support.zip"
        $tmpDir = Join-Path $env:TEMP "nest-support-main"

        Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip -UseBasicParsing
        Expand-Archive -Path $tmpZip -DestinationPath $env:TEMP -Force

        if (Test-Path $script:INSTALL_DIR) {
            Copy-Item -Path "$tmpDir\*" -Destination $script:INSTALL_DIR -Recurse -Force
        } else {
            New-Item -ItemType Directory -Path (Split-Path $script:INSTALL_DIR -Parent) -Force | Out-Null
            Move-Item -Path $tmpDir -Destination $script:INSTALL_DIR
        }

        Remove-Item -Path $tmpZip -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    Write-Success "ダウンロード完了: $($script:INSTALL_DIR)"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 4: Neo4j の起動
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function Setup-Database {
    Write-Step "Step 4/6: データベースの起動"

    Push-Location $script:INSTALL_DIR

    Write-Info "Neo4j データベースを起動しています..."
    Write-Info "（初回は Docker イメージのダウンロードに数分かかります）"
    Write-Host ""

    docker compose up -d

    # 起動待機: support-db
    $maxRetries = 24
    $retries = 0
    Write-Info "データベースの起動を待っています..."

    while ($retries -lt $maxRetries) {
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:7474" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            Write-Success "障害福祉データベース（port 7687）が起動しました"
            break
        } catch {
            $retries++
            Write-Host "  待機中... ($retries/$maxRetries)" -NoNewline
            Write-Host "`r" -NoNewline
            Start-Sleep -Seconds 5
        }
    }
    if ($retries -eq $maxRetries) {
        Write-Warn "障害福祉データベースの起動確認がタイムアウトしました。docker logs で確認してください。"
    }

    # 起動待機: livelihood-support
    $retries = 0
    while ($retries -lt $maxRetries) {
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:7475" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            Write-Success "生活困窮者自立支援データベース（port 7688）が起動しました"
            break
        } catch {
            $retries++
            Start-Sleep -Seconds 5
        }
    }
    if ($retries -eq $maxRetries) {
        Write-Warn "生活困窮者自立支援データベースの起動確認がタイムアウトしました。"
    }

    Pop-Location

    Write-Host ""
    Write-Host "  データベースの管理画面:"
    Write-Host "    障害福祉:       http://localhost:7474" -ForegroundColor Cyan
    Write-Host "    生活困窮者支援: http://localhost:7475" -ForegroundColor Cyan
    Write-Host "    認証情報:       neo4j / password"
    Write-Host ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 5: Skills のインストール
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function Install-Skills {
    Write-Step "Step 5/6: Claude Skills のインストール"

    $skillsSource = Join-Path $script:INSTALL_DIR "claude-skills"
    $skillsTarget = Join-Path $env:USERPROFILE ".claude\skills"

    # Skills ディレクトリの作成
    if (-not (Test-Path $skillsTarget)) {
        New-Item -ItemType Directory -Path $skillsTarget -Force | Out-Null
    }

    $skills = @(
        "neo4j-support-db", "livelihood-support", "provider-search",
        "emergency-protocol", "ecomap-generator", "html-to-pdf",
        "inheritance-calculator", "wamnet-provider-sync", "narrative-extractor",
        "data-quality-agent", "onboarding-wizard", "resilience-checker", "visit-prep"
    )

    $installed = 0
    $skipped = 0

    foreach ($skill in $skills) {
        $source = Join-Path $skillsSource $skill
        $target = Join-Path $skillsTarget $skill

        if (-not (Test-Path $source)) {
            Write-Warn "スキップ: $skill（ソースが見つかりません）"
            $skipped++
            continue
        }

        if (Test-Path $target) {
            # 既にある場合は削除して再作成
            Remove-Item -Path $target -Recurse -Force -ErrorAction SilentlyContinue
        }

        # Windows ではシンボリックリンクに管理者権限が必要な場合がある
        # まずシンボリックリンクを試み、失敗したらジャンクション → コピーにフォールバック
        try {
            New-Item -ItemType SymbolicLink -Path $target -Target $source -Force -ErrorAction Stop | Out-Null
            Write-Success "インストール (symlink): $skill"
            $installed++
        } catch {
            try {
                # ジャンクションリンク（管理者権限不要）
                cmd /c mklink /J "$target" "$source" 2>$null | Out-Null
                if (Test-Path $target) {
                    Write-Success "インストール (junction): $skill"
                    $installed++
                } else {
                    throw "Junction failed"
                }
            } catch {
                # フォールバック: コピー
                Copy-Item -Path $source -Destination $target -Recurse -Force
                Write-Success "インストール (copy): $skill"
                $installed++
            }
        }
    }

    Write-Host ""
    Write-Info "インストール結果: $installed 成功, $skipped スキップ"
    Write-Host ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 6: Claude Desktop 設定
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function Configure-ClaudeDesktop {
    Write-Step "Step 6/6: Claude Desktop の設定"

    if (-not (Test-Path $CLAUDE_CONFIG_DIR)) {
        Write-Warn "Claude Desktop の設定ディレクトリが見つかりません。"
        Write-Host "  Claude Desktop がインストールされていない可能性があります。"
        Write-Host "  インストール後に以下のコマンドで設定を追加できます:"
        Write-Host ""
        Write-Host "    .\installer\configure-claude.ps1" -ForegroundColor Cyan
        Write-Host ""
        return
    }

    # 既存設定のバックアップ
    if (Test-Path $CLAUDE_CONFIG_FILE) {
        $timestamp = Get-Date -Format "yyyyMMddHHmmss"
        $backupFile = "$CLAUDE_CONFIG_FILE.backup.$timestamp"
        Copy-Item $CLAUDE_CONFIG_FILE $backupFile
        Write-Info "既存の設定をバックアップしました: $(Split-Path $backupFile -Leaf)"
    }

    # MCP 設定の生成
    $mcpConfig = @{
        mcpServers = @{
            neo4j = @{
                command = "npx"
                args    = @("-y", "@anthropic/neo4j-mcp-server")
                env     = @{
                    NEO4J_URI      = "bolt://localhost:7687"
                    NEO4J_USERNAME = "neo4j"
                    NEO4J_PASSWORD = "password"
                }
            }
            "livelihood-support-db" = @{
                command = "npx"
                args    = @("-y", "@anthropic/neo4j-mcp-server")
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
        Write-Info "既存の Claude Desktop 設定に Neo4j MCP を追加します..."
        try {
            $existingConfig = Get-Content $CLAUDE_CONFIG_FILE -Raw | ConvertFrom-Json

            # mcpServers が無い場合は作成
            if (-not $existingConfig.mcpServers) {
                $existingConfig | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue @{} -Force
            }

            # neo4j サーバーを追加
            $existingConfig.mcpServers | Add-Member -NotePropertyName "neo4j" -NotePropertyValue $mcpConfig.mcpServers.neo4j -Force
            $existingConfig.mcpServers | Add-Member -NotePropertyName "livelihood-support-db" -NotePropertyValue $mcpConfig.mcpServers."livelihood-support-db" -Force

            $existingConfig | ConvertTo-Json -Depth 10 | Set-Content $CLAUDE_CONFIG_FILE -Encoding UTF8
            Write-Success "Neo4j MCP サーバーを追加しました"
        } catch {
            Write-Warn "設定のマージに失敗しました。新規作成します。"
            $mcpConfig | ConvertTo-Json -Depth 10 | Set-Content $CLAUDE_CONFIG_FILE -Encoding UTF8
            Write-Success "設定ファイルを新規作成しました"
        }
    } else {
        # 新規作成
        New-Item -ItemType Directory -Path $CLAUDE_CONFIG_DIR -Force | Out-Null
        $mcpConfig | ConvertTo-Json -Depth 10 | Set-Content $CLAUDE_CONFIG_FILE -Encoding UTF8
        Write-Success "Claude Desktop 設定ファイルを作成しました"
    }

    Write-Host ""
    Write-Host "  重要: Claude Desktop を再起動してください。" -ForegroundColor Yellow
    Write-Host "  タスクトレイの Claude アイコンを右クリック → 「Quit」→ 再度起動"
    Write-Host ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 接続テスト
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function Test-Connection {
    Write-Host ""
    Write-Info "接続テストを実行中..."

    $allOk = $true

    # Neo4j support-db テスト
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:7474" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Success "障害福祉データベース (port 7687): 接続OK"
    } catch {
        Write-Err "障害福祉データベース (port 7687): 接続失敗"
        $allOk = $false
    }

    # Neo4j livelihood-support テスト
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:7475" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Success "生活困窮者支援データベース (port 7688): 接続OK"
    } catch {
        Write-Err "生活困窮者支援データベース (port 7688): 接続失敗"
        $allOk = $false
    }

    # Skills テスト
    $skillsDir = Join-Path $env:USERPROFILE ".claude\skills"
    $skillsCount = 0
    if (Test-Path $skillsDir) {
        $skillsCount = (Get-ChildItem $skillsDir -Directory | Measure-Object).Count
    }
    if ($skillsCount -ge 10) {
        Write-Success "Claude Skills: $skillsCount 個インストール済み"
    } else {
        Write-Warn "Claude Skills: $skillsCount 個（期待: 13個）"
        $allOk = $false
    }

    # Claude Desktop 設定テスト
    if (Test-Path $CLAUDE_CONFIG_FILE) {
        $configContent = Get-Content $CLAUDE_CONFIG_FILE -Raw
        if ($configContent -match "neo4j") {
            Write-Success "Claude Desktop 設定: Neo4j MCP が設定済み"
        } else {
            Write-Warn "Claude Desktop 設定: Neo4j MCP が未設定"
            $allOk = $false
        }
    } else {
        Write-Warn "Claude Desktop 設定: ファイルが見つかりません"
        $allOk = $false
    }

    Write-Host ""
    if ($allOk) {
        Write-Success "すべてのテストに合格しました！"
    } else {
        Write-Warn "一部のテストが不合格です。上記のメッセージを確認してください。"
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 完了メッセージ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function Show-Completion {
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "  ║                                              ║" -ForegroundColor Green
    Write-Host "  ║   セットアップが完了しました！                ║" -ForegroundColor Green
    Write-Host "  ║                                              ║" -ForegroundColor Green
    Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "  次のステップ:" -ForegroundColor White
    Write-Host ""
    Write-Host "  1. Claude Desktop を再起動"
    Write-Host "  2. Claude に話しかけてみましょう:"
    Write-Host ""
    Write-Host "     「データベースの統計情報を教えて」" -ForegroundColor Cyan
    Write-Host "     「テスト用のクライアントを登録して」" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  ドキュメント:"
    Write-Host "    クイックスタート:  $($script:INSTALL_DIR)\docs\QUICK_START.md"
    Write-Host "    使い方ガイド:     $($script:INSTALL_DIR)\docs\ADVANCED_USAGE.md"
    Write-Host ""
    Write-Host "  データベース管理画面:"
    Write-Host "    http://localhost:7474 （認証: neo4j / password）" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  困ったときは:"
    Write-Host "    $($script:INSTALL_DIR)\docs\FAQ.md を参照してください。"
    Write-Host "    または Claude に「セットアップで困っています」と相談できます。"
    Write-Host ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン処理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Show-Welcome
Check-Windows
Check-Docker
Check-Node
Check-ClaudeDesktop
Download-Project
Setup-Database
Install-Skills
Configure-ClaudeDesktop
Test-Connection
Show-Completion
