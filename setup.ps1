# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# nest-support セットアップスクリプト（Windows版）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# 使い方:
#   .\setup.ps1              # 全セットアップ（推奨）
#   .\setup.ps1 -Skills      # Skills のみインストール
#   .\setup.ps1 -Neo4j       # Neo4j のみ起動
#   .\setup.ps1 -Uninstall   # Skills のアンインストール
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

param(
    [switch]$Skills,
    [switch]$Neo4j,
    [switch]$Uninstall,
    [switch]$Help
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# プロジェクトルート
$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$SKILLS_SOURCE_DIR = Join-Path $PROJECT_DIR "claude-skills"
$SKILLS_TARGET_DIR = Join-Path $env:USERPROFILE ".claude\skills"

# Skills 一覧（14スキル）
$SKILLS_LIST = @(
    "neo4j-support-db", "livelihood-support", "provider-search",
    "emergency-protocol", "ecomap-generator", "html-to-pdf",
    "inheritance-calculator", "wamnet-provider-sync", "narrative-extractor",
    "data-quality-agent", "onboarding-wizard", "resilience-checker", "visit-prep",
    "insight-agent"
)

# ヘルパー関数
function Write-Info    { param($msg) Write-Host "[INFO] " -ForegroundColor Blue -NoNewline; Write-Host $msg }
function Write-Success { param($msg) Write-Host "[OK] " -ForegroundColor Green -NoNewline; Write-Host $msg }
function Write-Warn    { param($msg) Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline; Write-Host $msg }
function Write-Err     { param($msg) Write-Host "[ERROR] " -ForegroundColor Red -NoNewline; Write-Host $msg }

function Show-Header {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
    Write-Host "  nest-support セットアップ（Windows版）" -ForegroundColor Magenta
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
    Write-Host ""
}

# 前提条件チェック
function Test-Prerequisites {
    Write-Info "前提条件を確認中..."
    $missing = 0

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $dockerVersion = docker --version
        Write-Success "Docker: $dockerVersion"
    } else {
        Write-Err "Docker がインストールされていません"
        $missing++
    }

    if (Get-Command npx -ErrorAction SilentlyContinue) {
        $npxVersion = npx --version 2>$null
        Write-Success "npx: $npxVersion"
    } else {
        Write-Warn "npx が見つかりません（Neo4j MCP に必要）"
    }

    if (Test-Path $SKILLS_SOURCE_DIR) {
        Write-Success "Skills ソース: $SKILLS_SOURCE_DIR"
    } else {
        Write-Err "claude-skills\ ディレクトリが見つかりません"
        $missing++
    }

    if ($missing -gt 0) {
        Write-Err "前提条件が満たされていません。"
        exit 1
    }
    Write-Host ""
}

# Neo4j セットアップ
function Start-Neo4j {
    Write-Info "Neo4j コンテナを起動中..."
    Push-Location $PROJECT_DIR

    docker compose up -d

    # support-db 起動待機
    $maxRetries = 12
    Write-Info "Neo4j (support-db) の起動を待機中（最大60秒）..."
    for ($i = 0; $i -lt $maxRetries; $i++) {
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:7474" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            Write-Success "Neo4j (support-db) が起動しました"
            Write-Host "  ブラウザUI: http://localhost:7474"
            Write-Host "  Bolt接続:  bolt://localhost:7687"
            Write-Host "  認証:      neo4j / password"
            break
        } catch {
            Start-Sleep -Seconds 5
        }
    }

    # livelihood-support 起動待機
    Write-Info "Neo4j (livelihood-support) の起動を待機中（最大60秒）..."
    for ($i = 0; $i -lt $maxRetries; $i++) {
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:7475" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            Write-Success "Neo4j (livelihood-support) が起動しました"
            Write-Host "  ブラウザUI: http://localhost:7475"
            Write-Host "  Bolt接続:  bolt://localhost:7688"
            break
        } catch {
            Start-Sleep -Seconds 5
        }
    }

    Pop-Location
}

# Skills インストール
function Install-NestSkills {
    Write-Info "Claude Skills をインストール中..."

    if (-not (Test-Path $SKILLS_TARGET_DIR)) {
        New-Item -ItemType Directory -Path $SKILLS_TARGET_DIR -Force | Out-Null
    }

    $installed = 0
    $skipped = 0

    foreach ($skill in $SKILLS_LIST) {
        $source = Join-Path $SKILLS_SOURCE_DIR $skill
        $target = Join-Path $SKILLS_TARGET_DIR $skill

        if (-not (Test-Path $source)) {
            Write-Warn "スキップ: $skill（ソースが見つかりません）"
            $skipped++
            continue
        }

        if (Test-Path $target) {
            Remove-Item -Path $target -Recurse -Force -ErrorAction SilentlyContinue
        }

        # シンボリックリンク → ジャンクション → コピー のフォールバック
        try {
            New-Item -ItemType SymbolicLink -Path $target -Target $source -Force -ErrorAction Stop | Out-Null
            Write-Success "インストール (symlink): $skill"
            $installed++
        } catch {
            try {
                cmd /c mklink /J "$target" "$source" 2>$null | Out-Null
                if (Test-Path $target) {
                    Write-Success "インストール (junction): $skill"
                    $installed++
                } else { throw }
            } catch {
                Copy-Item -Path $source -Destination $target -Recurse -Force
                Write-Success "インストール (copy): $skill"
                $installed++
            }
        }
    }

    Write-Host ""
    Write-Info "インストール結果: $installed 成功, $skipped スキップ"
    Write-Host ""

    Write-Info "インストール済み Skills:"
    foreach ($skill in $SKILLS_LIST) {
        $target = Join-Path $SKILLS_TARGET_DIR $skill
        if (Test-Path $target) {
            Write-Host "  ✓ $skill" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $skill" -ForegroundColor Red
        }
    }
}

# Skills アンインストール
function Uninstall-NestSkills {
    Write-Info "Claude Skills をアンインストール中..."
    foreach ($skill in $SKILLS_LIST) {
        $target = Join-Path $SKILLS_TARGET_DIR $skill
        if (Test-Path $target) {
            Remove-Item -Path $target -Recurse -Force
            Write-Success "削除: $skill"
        } else {
            Write-Info "未インストール: $skill"
        }
    }
    Write-Success "アンインストール完了"
}

# 設定ガイダンス
function Show-ConfigGuidance {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
    Write-Host "  次のステップ: Claude Desktop の設定" -ForegroundColor Magenta
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "  自動設定ツール:"
    Write-Host "    .\installer\configure-claude.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  手動設定:"
    Write-Host "    設定ファイル: $env:APPDATA\Claude\claude_desktop_config.json"
    Write-Host "    テンプレート: configs\claude_desktop_config.json"
    Write-Host ""
}

# ヘルプ表示
function Show-HelpText {
    Write-Host "使い方: .\setup.ps1 [オプション]"
    Write-Host ""
    Write-Host "オプション:"
    Write-Host "  (なし)        全セットアップ（Neo4j起動 + Skills インストール）"
    Write-Host "  -Skills       Skills のみインストール"
    Write-Host "  -Neo4j        Neo4j のみ起動"
    Write-Host "  -Uninstall    Skills のアンインストール"
    Write-Host "  -Help         このヘルプを表示"
}

# メイン処理
Show-Header

if ($Help) {
    Show-HelpText
} elseif ($Uninstall) {
    Uninstall-NestSkills
} elseif ($Skills) {
    Test-Prerequisites
    Install-NestSkills
    Show-ConfigGuidance
} elseif ($Neo4j) {
    Test-Prerequisites
    Start-Neo4j
} else {
    # 全セットアップ
    Test-Prerequisites
    Start-Neo4j
    Write-Host ""
    Install-NestSkills
    Show-ConfigGuidance
    Write-Success "セットアップが完了しました！"
}
