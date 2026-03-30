#!/usr/bin/env bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Claude Desktop 設定自動化スクリプト（Phase A-3）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# 使い方:
#   chmod +x configure-claude.sh && ./configure-claude.sh
#
# このスクリプトが行うこと:
#   1. Claude Desktop 設定ファイルの存在確認
#   2. 既存設定のバックアップ
#   3. Neo4j MCP サーバーの設定追加（既存設定とマージ）
#   4. 接続テストの実行
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}[情報]${NC} $1"; }
success() { echo -e "${GREEN}[完了]${NC} $1"; }
warn()    { echo -e "${YELLOW}[注意]${NC} $1"; }
error()   { echo -e "${RED}[エラー]${NC} $1"; }

# プロジェクトルート検出
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

# OS判定
detect_claude_config() {
    case "$(uname)" in
        Darwin)
            CLAUDE_CONFIG_DIR="${HOME}/Library/Application Support/Claude"
            ;;
        Linux)
            CLAUDE_CONFIG_DIR="${HOME}/.config/Claude"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            CLAUDE_CONFIG_DIR="${APPDATA}/Claude"
            ;;
        *)
            error "未対応のOS: $(uname)"
            exit 1
            ;;
    esac
    CLAUDE_CONFIG_FILE="${CLAUDE_CONFIG_DIR}/claude_desktop_config.json"
}

# MCP設定テンプレートの生成
# Neo4jのパスワードをカスタマイズ可能
generate_mcp_config() {
    local neo4j_pass="${1:-password}"

    cat <<EOJSON
{
  "mcpServers": {
    "neo4j": {
      "command": "npx",
      "args": ["-y", "@alanse/mcp-neo4j-server"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "${neo4j_pass}"
      }
    },
    "livelihood-support-db": {
      "command": "npx",
      "args": ["-y", "@alanse/mcp-neo4j-server"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7688",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "${neo4j_pass}"
      }
    }
  }
}
EOJSON
}

main() {
    echo ""
    echo -e "${PURPLE}${BOLD}━━━ Claude Desktop 設定ツール ━━━${NC}"
    echo ""

    detect_claude_config

    # 1. 設定ディレクトリの確認
    if [ ! -d "${CLAUDE_CONFIG_DIR}" ]; then
        info "設定ディレクトリを作成します: ${CLAUDE_CONFIG_DIR}"
        mkdir -p "${CLAUDE_CONFIG_DIR}"
    fi

    # 2. 既存設定のバックアップ
    if [ -f "${CLAUDE_CONFIG_FILE}" ]; then
        local backup_file="${CLAUDE_CONFIG_FILE}.backup.$(date +%Y%m%d%H%M%S)"
        cp "${CLAUDE_CONFIG_FILE}" "${backup_file}"
        success "バックアップ作成: $(basename "${backup_file}")"

        # 既に neo4j MCP が設定されているかチェック
        if grep -q '"neo4j"' "${CLAUDE_CONFIG_FILE}" 2>/dev/null; then
            warn "既に neo4j MCP が設定されています。"
            echo ""
            echo -ne "  上書きしますか？ [y/N] "
            read -r response
            if [[ ! "$response" =~ ^[Yy]$ ]]; then
                info "既存の設定を維持します。"

                # 接続テスト
                echo ""
                info "接続テストを実行..."
                if command -v npx &>/dev/null; then
                    if curl -s http://localhost:7474 &>/dev/null; then
                        success "Neo4j (port 7687): 接続OK"
                    else
                        warn "Neo4j (port 7687): 未接続（Docker が起動していない可能性があります）"
                    fi
                fi
                exit 0
            fi
        fi

        # jq でマージ
        if command -v jq &>/dev/null; then
            info "既存の設定に Neo4j MCP を追加中..."
            local new_servers
            new_servers=$(generate_mcp_config | jq '.mcpServers')

            jq --argjson new_servers "$new_servers" \
                '.mcpServers = (.mcpServers // {}) + $new_servers' \
                "${CLAUDE_CONFIG_FILE}" > "${CLAUDE_CONFIG_FILE}.tmp" \
                && mv "${CLAUDE_CONFIG_FILE}.tmp" "${CLAUDE_CONFIG_FILE}"

            success "Neo4j MCP を既存の設定にマージしました"
        else
            warn "jq が見つかりません。設定ファイルを新規作成します（既存の他のMCP設定は保持できません）。"
            echo -ne "  続行しますか？ [y/N] "
            read -r response
            if [[ ! "$response" =~ ^[Yy]$ ]]; then
                echo ""
                echo "  手動で以下を ${CLAUDE_CONFIG_FILE} に追加してください:"
                generate_mcp_config
                exit 0
            fi
            generate_mcp_config > "${CLAUDE_CONFIG_FILE}"
            success "設定ファイルを作成しました"
        fi
    else
        # 新規作成
        info "設定ファイルを新規作成します..."
        generate_mcp_config > "${CLAUDE_CONFIG_FILE}"
        success "設定ファイルを作成しました: ${CLAUDE_CONFIG_FILE}"
    fi

    # 3. 接続テスト
    echo ""
    info "接続テスト..."
    if curl -s http://localhost:7474 &>/dev/null; then
        success "Neo4j (port 7687): 接続OK"
    else
        warn "Neo4j (port 7687): 未接続"
        echo "  → docker compose up -d で Neo4j を起動してください"
    fi
    if curl -s http://localhost:7475 &>/dev/null; then
        success "Neo4j (port 7688): 接続OK"
    else
        warn "Neo4j (port 7688): 未接続"
    fi

    echo ""
    echo -e "${GREEN}${BOLD}  設定が完了しました。Claude Desktop を再起動してください。${NC}"
    echo ""
}

main "$@"
