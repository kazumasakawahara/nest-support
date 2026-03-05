#!/usr/bin/env bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# nest-support ワンクリックインストーラー（macOS版）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# 使い方:
#   curl -sL https://raw.githubusercontent.com/kazumasakawahara/nest-support/main/installer/install-mac.sh | bash
#   または:
#   chmod +x install-mac.sh && ./install-mac.sh
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

set -euo pipefail

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 定数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VERSION="1.0.0"
REPO_URL="https://github.com/kazumasakawahara/nest-support.git"
DEFAULT_INSTALL_DIR="${HOME}/Documents/nest-support"
CLAUDE_CONFIG_DIR="${HOME}/Library/Application Support/Claude"
CLAUDE_CONFIG_FILE="${CLAUDE_CONFIG_DIR}/claude_desktop_config.json"

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ヘルパー関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

info()    { echo -e "${BLUE}[情報]${NC} $1"; }
success() { echo -e "${GREEN}[完了]${NC} $1"; }
warn()    { echo -e "${YELLOW}[注意]${NC} $1"; }
error()   { echo -e "${RED}[エラー]${NC} $1"; }
step()    { echo -e "\n${PURPLE}${BOLD}━━━ $1 ━━━${NC}\n"; }

# ユーザーに Y/N で質問する
# 使い方: ask "質問?" && echo "Yes" || echo "No"
ask() {
    local prompt="$1"
    local response
    echo -ne "${CYAN}[確認]${NC} ${prompt} [Y/n] "
    read -r response
    [[ "$response" =~ ^[Yy]?$ ]]
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ウェルカムメッセージ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_welcome() {
    echo ""
    echo -e "${PURPLE}${BOLD}"
    echo "  ╔══════════════════════════════════════════════╗"
    echo "  ║                                              ║"
    echo "  ║   nest-support インストーラー v${VERSION}        ║"
    echo "  ║   〜 親亡き後支援データベース 〜              ║"
    echo "  ║                                              ║"
    echo "  ╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "  このスクリプトは、nest-support のセットアップを"
    echo "  対話形式で案内します。"
    echo ""
    echo "  所要時間の目安: 10〜20分"
    echo "  （Docker Desktop が未インストールの場合はもう少しかかります）"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 1: 前提条件チェック
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

check_macos() {
    if [[ "$(uname)" != "Darwin" ]]; then
        error "このインストーラーは macOS 専用です。"
        error "Windows をお使いの場合は installer/install-win.ps1 を使用してください。"
        exit 1
    fi
    success "macOS を確認しました: $(sw_vers -productVersion)"
}

check_docker() {
    step "Step 1/6: Docker Desktop の確認"

    if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
        success "Docker Desktop が動作中です: $(docker --version | head -1)"
        return 0
    fi

    if command -v docker &>/dev/null; then
        warn "Docker はインストールされていますが、起動していません。"
        echo ""
        echo "  Docker Desktop を起動してください:"
        echo "  1. Launchpad または アプリケーションフォルダから「Docker」を開く"
        echo "  2. メニューバーにクジラのアイコンが表示されるまで待つ"
        echo ""
        echo -ne "${CYAN}[確認]${NC} Docker Desktop を起動しましたか？ [Enter で続行] "
        read -r
        if docker info &>/dev/null 2>&1; then
            success "Docker Desktop が起動しました"
            return 0
        else
            error "Docker Desktop がまだ起動していないようです。起動後に再実行してください。"
            exit 1
        fi
    fi

    # Docker未インストール
    warn "Docker Desktop がインストールされていません。"
    echo ""
    echo "  Docker Desktop は、データベースを動かすために必要です。"
    echo ""

    if ask "Homebrew で Docker Desktop をインストールしますか？"; then
        if command -v brew &>/dev/null; then
            info "Docker Desktop をインストール中..."
            brew install --cask docker
            echo ""
            echo "  Docker Desktop がインストールされました。"
            echo "  アプリケーションフォルダから「Docker」を起動してください。"
            echo ""
            echo -ne "${CYAN}[確認]${NC} Docker Desktop を起動しましたか？ [Enter で続行] "
            read -r
        else
            warn "Homebrew がインストールされていません。"
            echo ""
            echo "  以下のURLから Docker Desktop をダウンロードしてください:"
            echo "  ${BOLD}https://www.docker.com/products/docker-desktop/${NC}"
            echo ""
            echo "  インストール・起動後にこのスクリプトを再実行してください。"
            exit 1
        fi
    else
        echo ""
        echo "  以下のURLから Docker Desktop をダウンロードしてください:"
        echo "  ${BOLD}https://www.docker.com/products/docker-desktop/${NC}"
        echo ""
        echo "  インストール・起動後にこのスクリプトを再実行してください。"
        exit 1
    fi

    if docker info &>/dev/null 2>&1; then
        success "Docker Desktop が動作中です"
    else
        error "Docker Desktop がまだ起動していないようです。起動後に再実行してください。"
        exit 1
    fi
}

check_node() {
    step "Step 2/6: Node.js の確認"

    if command -v npx &>/dev/null; then
        success "Node.js がインストール済みです: $(node --version 2>/dev/null || echo 'available')"
        return 0
    fi

    warn "Node.js がインストールされていません。"
    echo ""
    echo "  Node.js は、Claude Desktop とデータベースをつなぐために必要です。"
    echo ""

    if ask "Homebrew で Node.js をインストールしますか？"; then
        if command -v brew &>/dev/null; then
            info "Node.js をインストール中..."
            brew install node
            success "Node.js がインストールされました: $(node --version)"
        else
            echo ""
            echo "  以下のURLから Node.js をダウンロードしてください:"
            echo "  ${BOLD}https://nodejs.org/${NC}"
            echo "  （LTS版を推奨）"
            echo ""
            echo "  インストール後にこのスクリプトを再実行してください。"
            exit 1
        fi
    else
        echo ""
        echo "  以下のURLから Node.js をダウンロードしてください:"
        echo "  ${BOLD}https://nodejs.org/${NC}"
        echo ""
        exit 1
    fi
}

check_claude_desktop() {
    # Claude Desktop のインストール確認
    if [ -d "/Applications/Claude.app" ] || [ -d "${HOME}/Applications/Claude.app" ]; then
        success "Claude Desktop がインストール済みです"
        return 0
    fi

    warn "Claude Desktop が見つかりません。"
    echo ""
    echo "  以下のURLからダウンロード・インストールしてください:"
    echo "  ${BOLD}https://claude.ai/download${NC}"
    echo ""
    echo "  ※ インストールは後でも大丈夫です。先にデータベースのセットアップを進めます。"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 3: プロジェクトのダウンロード
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

download_project() {
    step "Step 3/6: プロジェクトファイルのダウンロード"

    # 既にプロジェクトディレクトリ内から実行されている場合
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local parent_dir
    parent_dir="$(dirname "$script_dir")"

    if [ -f "${parent_dir}/setup.sh" ] && [ -d "${parent_dir}/claude-skills" ]; then
        INSTALL_DIR="${parent_dir}"
        success "プロジェクトディレクトリを検出: ${INSTALL_DIR}"
        return 0
    fi

    # ダウンロードが必要
    echo "  プロジェクトファイルをダウンロードします。"
    echo ""
    echo "  インストール先: ${DEFAULT_INSTALL_DIR}"
    echo ""

    if [ -d "${DEFAULT_INSTALL_DIR}" ]; then
        warn "既にディレクトリが存在します: ${DEFAULT_INSTALL_DIR}"
        if ask "上書き（更新）しますか？"; then
            INSTALL_DIR="${DEFAULT_INSTALL_DIR}"
        else
            echo -ne "  別のインストール先を入力してください: "
            read -r INSTALL_DIR
            INSTALL_DIR="${INSTALL_DIR:-${DEFAULT_INSTALL_DIR}}"
        fi
    else
        INSTALL_DIR="${DEFAULT_INSTALL_DIR}"
    fi

    if command -v git &>/dev/null; then
        info "Git でダウンロード中..."
        if [ -d "${INSTALL_DIR}/.git" ]; then
            cd "${INSTALL_DIR}" && git pull
        else
            git clone "${REPO_URL}" "${INSTALL_DIR}"
        fi
    else
        info "ZIP でダウンロード中..."
        local zip_url="https://github.com/kazumasakawahara/nest-support/archive/refs/heads/main.zip"
        local tmp_zip="/tmp/nest-support.zip"
        curl -sL "${zip_url}" -o "${tmp_zip}"
        mkdir -p "$(dirname "${INSTALL_DIR}")"
        unzip -qo "${tmp_zip}" -d /tmp/
        if [ -d "${INSTALL_DIR}" ]; then
            cp -R /tmp/nest-support-main/* "${INSTALL_DIR}/"
        else
            mv /tmp/nest-support-main "${INSTALL_DIR}"
        fi
        rm -f "${tmp_zip}"
        rm -rf /tmp/nest-support-main
    fi

    success "ダウンロード完了: ${INSTALL_DIR}"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 4: Neo4j の起動
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

setup_database() {
    step "Step 4/6: データベースの起動"

    cd "${INSTALL_DIR}"

    info "Neo4j データベースを起動しています..."
    info "（初回は Docker イメージのダウンロードに数分かかります）"
    echo ""

    if docker compose version &>/dev/null 2>&1; then
        docker compose up -d 2>&1 | while read -r line; do
            echo "  ${line}"
        done
    else
        docker-compose up -d 2>&1 | while read -r line; do
            echo "  ${line}"
        done
    fi

    # 起動待機
    local retries=0
    local max_retries=24  # 最大2分

    info "データベースの起動を待っています..."
    while [ $retries -lt $max_retries ]; do
        if curl -s http://localhost:7474 &>/dev/null; then
            success "障害福祉データベース（port 7687）が起動しました"
            break
        fi
        retries=$((retries + 1))
        echo -ne "  待機中... (${retries}/${max_retries})\r"
        sleep 5
    done
    if [ $retries -eq $max_retries ]; then
        warn "障害福祉データベースの起動確認がタイムアウトしました。docker logs で確認してください。"
    fi

    # livelihood-support の待機
    retries=0
    while [ $retries -lt $max_retries ]; do
        if curl -s http://localhost:7475 &>/dev/null; then
            success "生活困窮者自立支援データベース（port 7688）が起動しました"
            break
        fi
        retries=$((retries + 1))
        echo -ne "  待機中... (${retries}/${max_retries})\r"
        sleep 5
    done
    if [ $retries -eq $max_retries ]; then
        warn "生活困窮者自立支援データベースの起動確認がタイムアウトしました。"
    fi

    echo ""
    echo "  データベースの管理画面:"
    echo "    障害福祉:     ${BOLD}http://localhost:7474${NC}"
    echo "    生活困窮者支援: ${BOLD}http://localhost:7475${NC}"
    echo "    認証情報:     neo4j / password"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 5: Skills のインストール
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

install_skills() {
    step "Step 5/6: Claude Skills のインストール"

    cd "${INSTALL_DIR}"
    chmod +x setup.sh
    # setup.sh の --skills オプションで Skills のみインストール
    ./setup.sh --skills 2>&1 | while read -r line; do
        echo "  ${line}"
    done

    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 6: Claude Desktop 設定
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

configure_claude_desktop() {
    step "Step 6/6: Claude Desktop の設定"

    # Claude Desktop の設定ディレクトリ確認
    if [ ! -d "${CLAUDE_CONFIG_DIR}" ]; then
        warn "Claude Desktop の設定ディレクトリが見つかりません。"
        echo "  Claude Desktop がインストールされていない可能性があります。"
        echo "  インストール後に以下のコマンドで設定を追加できます:"
        echo ""
        echo "    ${BOLD}cd ${INSTALL_DIR} && bash installer/configure-claude.sh${NC}"
        echo ""
        return 0
    fi

    # 既存設定のバックアップ
    if [ -f "${CLAUDE_CONFIG_FILE}" ]; then
        local backup_file="${CLAUDE_CONFIG_FILE}.backup.$(date +%Y%m%d%H%M%S)"
        cp "${CLAUDE_CONFIG_FILE}" "${backup_file}"
        info "既存の設定をバックアップしました: $(basename "${backup_file}")"
    fi

    # 設定ファイルの生成・マージ
    if [ -f "${CLAUDE_CONFIG_FILE}" ]; then
        # 既存の設定ファイルに MCP サーバーを追加
        info "既存の Claude Desktop 設定に Neo4j MCP を追加します..."

        # jq が利用可能かチェック
        if command -v jq &>/dev/null; then
            local neo4j_config
            neo4j_config=$(cat "${INSTALL_DIR}/configs/claude_desktop_config.json")

            # 既存設定にマージ
            jq --argjson new_servers "$(echo "$neo4j_config" | jq '.mcpServers')" \
                '.mcpServers += $new_servers' \
                "${CLAUDE_CONFIG_FILE}" > "${CLAUDE_CONFIG_FILE}.tmp" \
                && mv "${CLAUDE_CONFIG_FILE}.tmp" "${CLAUDE_CONFIG_FILE}"

            success "Neo4j MCP サーバーを追加しました"
        else
            # jq がない場合は手動案内
            warn "設定の自動マージには jq が必要です。"
            echo ""
            echo "  以下の内容を Claude Desktop の設定ファイルに追加してください:"
            echo "  ファイル: ${CLAUDE_CONFIG_FILE}"
            echo ""
            echo "  mcpServers に以下を追加:"
            echo '    "neo4j": {'
            echo '      "command": "npx",'
            echo '      "args": ["-y", "@anthropic/neo4j-mcp-server"],'
            echo '      "env": {'
            echo '        "NEO4J_URI": "bolt://localhost:7687",'
            echo '        "NEO4J_USERNAME": "neo4j",'
            echo '        "NEO4J_PASSWORD": "password"'
            echo '      }'
            echo '    },'
            echo '    "livelihood-support-db": {'
            echo '      "command": "npx",'
            echo '      "args": ["-y", "@anthropic/neo4j-mcp-server"],'
            echo '      "env": {'
            echo '        "NEO4J_URI": "bolt://localhost:7688",'
            echo '        "NEO4J_USERNAME": "neo4j",'
            echo '        "NEO4J_PASSWORD": "password"'
            echo '      }'
            echo '    }'
            echo ""
        fi
    else
        # 設定ファイルが存在しない: テンプレートをコピー
        mkdir -p "${CLAUDE_CONFIG_DIR}"
        cp "${INSTALL_DIR}/configs/claude_desktop_config.json" "${CLAUDE_CONFIG_FILE}"
        success "Claude Desktop 設定ファイルを作成しました"
    fi

    echo ""
    echo "  ${BOLD}重要: Claude Desktop を再起動してください。${NC}"
    echo "  メニューバーの Claude アイコン → 「Quit Claude」→ 再度起動"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 接続テスト
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

run_connection_test() {
    echo ""
    info "接続テストを実行中..."

    local all_ok=true

    # Neo4j support-db テスト
    if curl -s http://localhost:7474 &>/dev/null; then
        success "障害福祉データベース (port 7687): 接続OK"
    else
        error "障害福祉データベース (port 7687): 接続失敗"
        all_ok=false
    fi

    # Neo4j livelihood-support テスト
    if curl -s http://localhost:7475 &>/dev/null; then
        success "生活困窮者支援データベース (port 7688): 接続OK"
    else
        error "生活困窮者支援データベース (port 7688): 接続失敗"
        all_ok=false
    fi

    # Skills テスト
    local skills_count=0
    local skills_dir="${HOME}/.claude/skills"
    if [ -d "${skills_dir}" ]; then
        skills_count=$(find "${skills_dir}" -maxdepth 1 -type l 2>/dev/null | wc -l | tr -d ' ')
    fi
    if [ "$skills_count" -ge 10 ]; then
        success "Claude Skills: ${skills_count} 個インストール済み"
    else
        warn "Claude Skills: ${skills_count} 個（期待: 13個）"
        all_ok=false
    fi

    # Claude Desktop 設定テスト
    if [ -f "${CLAUDE_CONFIG_FILE}" ]; then
        if grep -q "neo4j" "${CLAUDE_CONFIG_FILE}" 2>/dev/null; then
            success "Claude Desktop 設定: Neo4j MCP が設定済み"
        else
            warn "Claude Desktop 設定: Neo4j MCP が未設定"
            all_ok=false
        fi
    else
        warn "Claude Desktop 設定: ファイルが見つかりません"
        all_ok=false
    fi

    echo ""
    if $all_ok; then
        success "すべてのテストに合格しました！"
    else
        warn "一部のテストが不合格です。上記のメッセージを確認してください。"
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 完了メッセージ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_completion() {
    echo ""
    echo -e "${GREEN}${BOLD}"
    echo "  ╔══════════════════════════════════════════════╗"
    echo "  ║                                              ║"
    echo "  ║   セットアップが完了しました！                ║"
    echo "  ║                                              ║"
    echo "  ╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    echo "  ${BOLD}次のステップ:${NC}"
    echo ""
    echo "  1. Claude Desktop を再起動"
    echo "  2. Claude に話しかけてみましょう:"
    echo ""
    echo "     ${CYAN}「データベースの統計情報を教えて」${NC}"
    echo "     ${CYAN}「テスト用のクライアントを登録して」${NC}"
    echo ""
    echo "  ${BOLD}ドキュメント:${NC}"
    echo "    クイックスタート:  ${INSTALL_DIR}/docs/QUICK_START.md"
    echo "    セットアップ詳細: ${INSTALL_DIR}/docs/SETUP_GUIDE.md"
    echo "    使い方ガイド:     ${INSTALL_DIR}/docs/ADVANCED_USAGE.md"
    echo ""
    echo "  ${BOLD}データベース管理画面:${NC}"
    echo "    http://localhost:7474 （認証: neo4j / password）"
    echo ""
    echo "  ${BOLD}困ったときは:${NC}"
    echo "    ${INSTALL_DIR}/docs/FAQ.md を参照してください。"
    echo "    または Claude に「セットアップで困っています」と相談できます。"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン処理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main() {
    show_welcome
    check_macos
    check_docker
    check_node
    check_claude_desktop
    download_project
    setup_database
    install_skills
    configure_claude_desktop
    run_connection_test
    show_completion
}

main "$@"
