#!/usr/bin/env bash
# Neo4j バックアップスクリプト
#
# 使い方:
#   chmod +x scripts/backup.sh
#   ./scripts/backup.sh
#
# neo4j_backup/ ディレクトリにデータのコピーを作成します。

set -euo pipefail

BACKUP_DIR="$(cd "$(dirname "$0")/.." && pwd)/neo4j_backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}"

echo "Neo4j バックアップを開始します..."
echo "バックアップ先: ${BACKUP_DIR}/${BACKUP_NAME}"

# コンテナが起動しているか確認
if ! docker ps --format '{{.Names}}' | grep -q 'nest-support-neo4j'; then
    echo "エラー: nest-support-neo4j コンテナが起動していません"
    exit 1
fi

# バックアップディレクトリ作成
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# neo4j-admin dump を使用（コンテナ内で実行）
docker exec nest-support-neo4j neo4j-admin database dump neo4j --to-path=/backup/ 2>/dev/null || {
    echo "neo4j-admin dump が失敗しました。ファイルコピーでバックアップします..."
    docker cp nest-support-neo4j:/data "${BACKUP_DIR}/${BACKUP_NAME}/data"
}

echo "バックアップが完了しました: ${BACKUP_DIR}/${BACKUP_NAME}"
echo "復元方法: docker cp ${BACKUP_DIR}/${BACKUP_NAME}/data nest-support-neo4j:/data"
