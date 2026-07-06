#!/usr/bin/env bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# デモデータの投入・削除スクリプト
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# 使い方:
#   ./load-demo-data.sh              # デモデータを投入
#   ./load-demo-data.sh --simulation # デモ + シミュレーション感情データを投入
#   ./load-demo-data.sh --remove     # デモデータを削除
#   ./load-demo-data.sh --remove-sim # シミュレーションデータのみ削除
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_FILE="${SCRIPT_DIR}/demo-data.cypher"
SIMULATION_FILE="${SCRIPT_DIR}/simulation-emotion-data.cypher"
NEO4J_URL="http://localhost:7474/db/neo4j/tx/commit"
NEO4J_AUTH="neo4j:password"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[情報]${NC} $1"; }
success() { echo -e "${GREEN}[完了]${NC} $1"; }
warn()    { echo -e "${YELLOW}[注意]${NC} $1"; }
error()   { echo -e "${RED}[エラー]${NC} $1"; }

# Neo4j 接続確認
check_neo4j() {
    if ! curl -s http://localhost:7474 &>/dev/null; then
        error "Neo4j が起動していません。先に docker compose up -d を実行してください。"
        exit 1
    fi
    success "Neo4j 接続確認OK"
}

# Cypher クエリを実行する関数
run_cypher() {
    local query="$1"
    local response
    response=$(curl -s -X POST "${NEO4J_URL}" \
        -H "Content-Type: application/json" \
        -u "${NEO4J_AUTH}" \
        -d "{\"statements\": [{\"statement\": $(echo "$query" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}]}")

    # エラーチェック
    local errors
    errors=$(echo "$response" | python3 -c "import sys,json; r=json.load(sys.stdin); print(len(r.get('errors',[])))" 2>/dev/null || echo "1")
    if [ "$errors" != "0" ]; then
        echo "$response" | python3 -c "import sys,json; r=json.load(sys.stdin); [print(e.get('message','Unknown error')) for e in r.get('errors',[])]" 2>/dev/null
        return 1
    fi
    return 0
}

# スカラー値を返す Cypher クエリを実行する関数（先頭行・先頭列を返す）
# 取得できなかった場合は "-1" を返す
query_scalar() {
    local query="$1"
    local response
    response=$(curl -s -X POST "${NEO4J_URL}" \
        -H "Content-Type: application/json" \
        -u "${NEO4J_AUTH}" \
        -d "{\"statements\": [{\"statement\": $(echo "$query" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}]}")
    echo "$response" | python3 -c "import sys,json
try:
    r = json.load(sys.stdin)
    if r.get('errors'):
        print('-1')
    else:
        print(r['results'][0]['data'][0]['row'][0])
except Exception:
    print('-1')" 2>/dev/null || echo "-1"
}

# 投入前ガード: demoId を持たない実ノードが存在しないか検査する。
# 実データを検出した場合は既定で中断し、明示的な確認でのみ続行を許可する。
guard_against_real_data() {
    local real_count
    real_count=$(query_scalar "MATCH (n) WHERE n.demoId IS NULL RETURN count(n) AS c")

    if [ "$real_count" = "-1" ]; then
        warn "既存ノード数を確認できませんでした（Neo4j 応答の解析に失敗）。"
        echo -ne "  それでもデモデータを投入しますか？ [y/N] "
        read -r ans
        if [[ ! "$ans" =~ ^[Yy]$ ]]; then
            info "投入をキャンセルしました。"
            exit 0
        fi
        return 0
    fi

    if [ "$real_count" = "0" ]; then
        # DB が空、または既存ノードが全て demoId を持つ（＝過去のデモのみ）
        return 0
    fi

    warn "実データ（demoId を持たないノード）が ${real_count} 件検出されました。"
    warn "デモデータ投入は demoId ベースで実データを汚染しませんが、"
    warn "本番データとデモの混在を避けるため、既定では投入を中断します。"
    echo -ne "  実データがある状態でデモデータを投入しますか？ [y/N] "
    read -r ans
    if [[ ! "$ans" =~ ^[Yy]$ ]]; then
        info "投入を中断しました。（デモは空 DB / デモ専用 DB での利用を推奨）"
        exit 0
    fi
    warn "ユーザー確認により、実データがある状態で投入を続行します。"
}

# デモデータ投入
load_demo() {
    info "デモデータを投入中..."

    if [ ! -f "${DEMO_FILE}" ]; then
        error "デモデータファイルが見つかりません: ${DEMO_FILE}"
        exit 1
    fi

    # 投入前ガード: 実データ（demoId なし）を検出したら既定で中断
    guard_against_real_data

    # コメント行を除去し、セミコロンでステートメントを分割して実行
    local count=0
    local current_stmt=""

    while IFS= read -r line; do
        # コメント行と空行をスキップ
        [[ "$line" =~ ^[[:space:]]*//.* ]] && continue
        [[ -z "$line" ]] && continue

        current_stmt="${current_stmt} ${line}"

        # セミコロンで終わる行でステートメント実行
        if [[ "$line" =~ \;[[:space:]]*$ ]]; then
            # 末尾のセミコロンを除去
            current_stmt="${current_stmt%;}"
            current_stmt=$(echo "$current_stmt" | sed 's/^[[:space:]]*//')

            if [ -n "$current_stmt" ]; then
                if run_cypher "$current_stmt"; then
                    count=$((count + 1))
                else
                    warn "ステートメント ${count} でエラーが発生（続行します）"
                fi
            fi
            current_stmt=""
        fi
    done < "${DEMO_FILE}"

    success "デモデータの投入が完了しました（${count} ステートメント実行）"
    echo ""
    echo "  Claude Desktop で以下を試してみてください:"
    echo "  「山本翔太さんのプロフィールを見せて」"
    echo "  「鈴木花さんの禁忌事項を教えて」"
    echo "  「データベースの統計情報を表示して」"
    echo ""
}

# デモデータ削除
remove_demo() {
    warn "デモデータを削除します。"
    echo -ne "  本当に削除しますか？ [y/N] "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        info "削除をキャンセルしました。"
        exit 0
    fi

    info "デモデータを削除中..."

    # demoId を持つノード（＝デモ由来）とそのリレーションのみを削除。
    # 実ノードは demoId を持たないため決して削除対象にならない。
    # SupportLog / AuditLog もすべて demoId を持つため、この 1 文で網羅される。
    run_cypher "MATCH (n) WHERE n.demoId IS NOT NULL DETACH DELETE n" && \
        success "demoId を持つデモノードを削除しました"

    # 念のため demoId 基準で SupportLog / AuditLog も個別に掃除（冪等）
    run_cypher "MATCH (sl:SupportLog) WHERE sl.demoId IS NOT NULL DETACH DELETE sl" && \
        success "デモ支援記録を削除しました"

    run_cypher "MATCH (al:AuditLog) WHERE al.demoId IS NOT NULL DELETE al" && \
        success "デモ監査ログを削除しました"

    success "デモデータの削除が完了しました"
}

# シミュレーション感情データ投入
load_simulation() {
    info "シミュレーション感情データを投入中..."

    if [ ! -f "${SIMULATION_FILE}" ]; then
        error "シミュレーションデータファイルが見つかりません: ${SIMULATION_FILE}"
        exit 1
    fi

    local count=0
    local current_stmt=""

    while IFS= read -r line; do
        [[ "$line" =~ ^[[:space:]]*//.* ]] && continue
        [[ -z "$line" ]] && continue
        current_stmt="${current_stmt} ${line}"
        if [[ "$line" =~ \;[[:space:]]*$ ]]; then
            current_stmt="${current_stmt%;}"
            current_stmt=$(echo "$current_stmt" | sed 's/^[[:space:]]*//')
            if [ -n "$current_stmt" ]; then
                if run_cypher "$current_stmt"; then
                    count=$((count + 1))
                else
                    warn "ステートメント ${count} でエラーが発生（続行します）"
                fi
            fi
            current_stmt=""
        fi
    done < "${SIMULATION_FILE}"

    success "シミュレーションデータの投入が完了しました（${count} ステートメント実行）"
    echo ""
    echo "  insight-agent の検証コマンド:"
    echo "  「山本翔太さんの最近の感情トレンドを分析して」"
    echo "  「山本翔太さんのリスク評価を実行して」"
    echo ""
}

# シミュレーションデータ削除
remove_simulation() {
    info "シミュレーション感情データを削除中..."
    run_cypher "MATCH (log:SupportLog) WHERE log.isSimulation = true DETACH DELETE log" && \
        success "シミュレーションデータを削除しました"
}

main() {
    check_neo4j

    case "${1:-load}" in
        --remove|-r)
            remove_demo
            ;;
        --simulation|-s)
            load_demo
            load_simulation
            ;;
        --remove-sim)
            remove_simulation
            ;;
        load|"")
            load_demo
            ;;
        *)
            echo "使い方: $0 [--simulation|--remove|--remove-sim]"
            exit 1
            ;;
    esac
}

main "$@"
