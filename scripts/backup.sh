#!/usr/bin/env bash
# Neo4j バックアップスクリプト
#
# 使い方:
#   chmod +x scripts/backup.sh
#   ./scripts/backup.sh
#
# neo4j_backup/backup_<timestamp>/ にタイムスタンプ付きのダンプ（または
# 停止コピー）を作成します。成功報告は、実際に生成されたファイルの存在と
# サイズ（0でないこと）を確認した後にのみ行います。
#
# 注意: オンライン dump に失敗した場合、整合性のあるバックアップを取るため
# 一時的にコンテナを停止→コピー→再起動します（trap で必ず再起動）。

set -euo pipefail

BACKUP_ROOT="$(cd "$(dirname "$0")/.." && pwd)/neo4j_backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}"
BACKUP_DIR="${BACKUP_ROOT}/${BACKUP_NAME}"

echo "Neo4j バックアップを開始します..."

# --- 対象コンテナの解決（port 7687 を提供するコンテナ。doctor.sh と同じ方式）---
# 実データは別名コンテナ（例: support-db-neo4j）が 7687 を提供している構成が
# あるため、固定名ではなく publish=7687 で解決する。
CONTAINER=""
if docker inspect -f '{{.State.Status}}' nest-support-neo4j 2>/dev/null | grep -q running; then
    CONTAINER="nest-support-neo4j"
else
    CONTAINER=$(docker ps --filter publish=7687 --format '{{.Names}}' 2>/dev/null | head -1)
fi

if [ -z "${CONTAINER}" ]; then
    echo "エラー: port 7687 を提供する起動中の Neo4j コンテナが見つかりません" >&2
    exit 1
fi
echo "対象コンテナ: ${CONTAINER}"
echo "バックアップ先: ${BACKUP_DIR}"

mkdir -p "${BACKUP_DIR}"

# 生成物のサイズ検証ヘルパー（0 バイト/不在なら失敗）
verify_nonempty() {
    local path="$1"
    if [ ! -e "${path}" ]; then
        return 1
    fi
    local size
    size=$(du -sk "${path}" 2>/dev/null | cut -f1)
    [ -n "${size}" ] && [ "${size}" -gt 0 ]
}

DUMP_IN_CONTAINER="/tmp/nest-backup"
DUMP_FILE="${BACKUP_DIR}/neo4j.dump"
RESTORE_HINT=""

# --- 1. オンライン dump を試みる ---
online_dump_ok=false
if docker exec "${CONTAINER}" sh -c "rm -rf ${DUMP_IN_CONTAINER} && mkdir -p ${DUMP_IN_CONTAINER} && neo4j-admin database dump neo4j --to-path=${DUMP_IN_CONTAINER} --overwrite-destination=true"; then
    if docker cp "${CONTAINER}:${DUMP_IN_CONTAINER}/neo4j.dump" "${DUMP_FILE}" && verify_nonempty "${DUMP_FILE}"; then
        online_dump_ok=true
        docker exec "${CONTAINER}" rm -rf "${DUMP_IN_CONTAINER}" 2>/dev/null || true
        RESTORE_HINT="docker cp ${DUMP_FILE} ${CONTAINER}:/tmp/neo4j.dump && docker exec ${CONTAINER} neo4j-admin database load neo4j --from-path=/tmp --overwrite-destination=true"
    fi
fi

# --- 2. 失敗時: 停止→コピー→再起動（整合性のあるバックアップ）---
if [ "${online_dump_ok}" != true ]; then
    echo "オンライン dump に失敗しました。コンテナを停止してデータをコピーします..."
    # 何があっても再起動する
    restart_container() { docker start "${CONTAINER}" >/dev/null 2>&1 || true; }
    trap restart_container EXIT

    docker stop "${CONTAINER}" >/dev/null
    docker cp "${CONTAINER}:/data" "${BACKUP_DIR}/data"
    docker start "${CONTAINER}" >/dev/null
    trap - EXIT

    if ! verify_nonempty "${BACKUP_DIR}/data"; then
        echo "エラー: データコピーに失敗しました（生成物が空です）" >&2
        exit 1
    fi
    RESTORE_HINT="docker stop ${CONTAINER} && docker cp ${BACKUP_DIR}/data ${CONTAINER}:/data && docker start ${CONTAINER}"
fi

echo "バックアップが完了しました: ${BACKUP_DIR}"
du -sh "${BACKUP_DIR}" | awk '{print "  サイズ: " $1}'
echo "復元方法: ${RESTORE_HINT}"
