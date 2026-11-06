#!/usr/bin/env bash
# nest-support 環境の点検（計画 N-30。ADR-001 の作り直しの構成）
# 使い方: ./scripts/doctor.sh
#
# 確かめること:
#   1. 前の DB のコンテナが動いていない（前の DB は起動しない）
#   2. 新しい二つのコンテナは、動いていれば 127.0.0.1 だけで待ち受けている（止まっているのは正しい状態）
#   3. 接続の設定のファイルがあり、権限が 600（中身は読まない）
#   4. .mcp.json が nest-personal・nest-resource を持ち、前の MCP（neo4j・neo4j-shared）を持たない
#   5. ~/.claude/skills/ のリンクが、このリポジトリの claude-skills を指している。外したスキルのリンクが残っていない
#   6. 正典のずれが 0 件（scripts/check_drift.py）
#   7. FileVault が有効（N-33）
#   8. バックアップの置き場所 ~/nest-backup/ は、あれば権限 700・Time Machine の対象外（N-33。無ければ知らせるだけ）
#   9. 音声の置き場所 nest_voice_data/ は、あれば権限 700・Time Machine の対象外（N-37。無ければ知らせるだけ）。
#      30 日を過ぎた音声が残っていれば FAIL（遅くとも 30 日で消す約束。消す道具は自動では動かないため。G-77）
#  10. Claude Desktop の設定（知らせるだけ）
#
# 結果は OK / FAIL / INFO で表示する。FAIL が一つでもあれば 1 を返す。

set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${HOME}/.claude/skills"
ENV_FILE="${HOME}/.config/nest/neo4j-redesign.env"
DESKTOP_CONFIG="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
OLD_CONTAINERS=(nest-support-neo4j support-db-neo4j)
NEW_CONTAINERS=(nest-redesign-personal nest-redesign-resource)
REMOVED_SKILLS=(wamnet-provider-sync livelihood-support)

PASS=0
FAIL=0
ok()   { printf "  \033[32mOK\033[0m   %s\n" "$1"; PASS=$((PASS+1)); }
fail() { printf "  \033[31mFAIL\033[0m %s\n" "$1"; FAIL=$((FAIL+1)); }
info() { printf "  \033[33mINFO\033[0m %s\n" "$1"; PASS=$((PASS+1)); }
to_lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

echo "=== nest-support doctor ==="
echo "project: ${PROJECT_DIR}"

RUNNING=""
if command -v docker >/dev/null 2>&1; then
  RUNNING="$(docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null)"
else
  echo ""
  fail "docker が見つからない"
fi
running_line() { printf '%s\n' "${RUNNING}" | awk -v n="$1" '$1 == n'; }

echo ""
echo "[1] 前の DB は動いていない"
for name in "${OLD_CONTAINERS[@]}"; do
  if [ -n "$(running_line "${name}")" ]; then
    fail "${name} が動いている（前の DB は起動しない。docker stop ${name}）"
  else
    ok "${name}: 動いていない"
  fi
done

echo ""
echo "[2] 新しい DB の待ち受け"
for name in "${NEW_CONTAINERS[@]}"; do
  line="$(running_line "${name}")"
  if [ -z "${line}" ]; then
    info "${name}: 止まっている（試験のときだけ起動する）"
  elif printf '%s' "${line}" | awk '{ $1 = ""; print }' | tr ',' '\n' | awk 'NF && $1 !~ /^127\.0\.0\.1:/ { bad = 1 } END { exit bad ? 0 : 1 }'; then
    fail "${name} が 127.0.0.1 の外でも待ち受けている（${line}）"
  else
    ok "${name}: 127.0.0.1 だけで待ち受けている"
  fi
done

echo ""
echo "[3] 接続の設定のファイル（中身は読まない）"
if [ -f "${ENV_FILE}" ]; then
  mode="$(stat -f %Lp "${ENV_FILE}" 2>/dev/null || stat -c %a "${ENV_FILE}" 2>/dev/null)"
  if [ "${mode}" = "600" ]; then
    ok "~/.config/nest/neo4j-redesign.env: 権限 600"
  else
    fail "~/.config/nest/neo4j-redesign.env の権限が ${mode}（600 にする: chmod 600）"
  fi
else
  fail "~/.config/nest/neo4j-redesign.env が無い（docs/SETUP_GUIDE.md の 4）"
fi

echo ""
echo "[4] .mcp.json"
MCP_FILE="${PROJECT_DIR}/.mcp.json"
if [ -f "${MCP_FILE}" ]; then
  for name in nest-personal nest-resource; do
    if grep -q "\"${name}\"" "${MCP_FILE}"; then ok ".mcp.json に ${name} がある"; else fail ".mcp.json に ${name} が無い"; fi
  done
  for name in neo4j neo4j-shared; do
    if grep -q "\"${name}\"" "${MCP_FILE}"; then fail ".mcp.json に前の MCP（${name}）が残っている"; else ok ".mcp.json に前の MCP（${name}）は無い"; fi
  done
else
  fail ".mcp.json が無い"
fi

echo ""
echo "[5] スキルのリンク（-> ${PROJECT_DIR}/claude-skills）"
expected_base="$(to_lower "${PROJECT_DIR}/claude-skills")"
for dir in "${PROJECT_DIR}"/claude-skills/*/; do
  skill="$(basename "${dir}")"
  [ -f "${dir}/SKILL.md" ] || continue
  link="${SKILLS_DIR}/${skill}"
  if [ ! -L "${link}" ]; then fail "${skill}: リンクが無い"; continue; fi
  target="$(readlink "${link}")"
  target="${target%/}"
  if [ "$(to_lower "${target}")" = "${expected_base}/${skill}" ]; then ok "${skill}"; else fail "${skill} -> ${target}"; fi
done
for skill in "${REMOVED_SKILLS[@]}"; do
  if [ -L "${SKILLS_DIR}/${skill}" ] || [ -e "${SKILLS_DIR}/${skill}" ]; then
    fail "${skill} のリンクが残っている（外したスキル。rm \"${SKILLS_DIR}/${skill}\"）"
  else
    ok "${skill}: リンクは無い（外したスキル）"
  fi
done

echo ""
echo "[6] 正典のずれ"
if (cd "${PROJECT_DIR}" && uv run --quiet python scripts/check_drift.py >/dev/null 2>&1); then
  ok "docs/SCHEMA.md: ずれ 0 件"
else
  fail "docs/SCHEMA.md: ずれがある（uv run python scripts/check_drift.py）"
fi

echo ""
echo "[7] FileVault（バックアップと DB のデータを守る。N-33）"
if fdesetup status 2>/dev/null | grep -q "FileVault is On"; then
  ok "FileVault が有効"
else
  fail "FileVault が有効でない（システム設定 → プライバシーとセキュリティ → FileVault）"
fi

echo ""
echo "[8] バックアップの置き場所（~/nest-backup/。要配慮個人情報の写し。N-33）"
BACKUP_DIR="${HOME}/nest-backup"
if [ -d "${BACKUP_DIR}" ]; then
  bmode="$(stat -f %Lp "${BACKUP_DIR}" 2>/dev/null || stat -c %a "${BACKUP_DIR}" 2>/dev/null)"
  if [ "${bmode}" = "700" ]; then ok "~/nest-backup: 権限 700"; else fail "~/nest-backup の権限が ${bmode}（700 にする: chmod 700 ~/nest-backup）"; fi
  if tmutil isexcluded "${BACKUP_DIR}" 2>/dev/null | grep -q "\[Excluded\]"; then
    ok "~/nest-backup: Time Machine の対象外"
  else
    fail "~/nest-backup が Time Machine の対象（tmutil addexclusion ~/nest-backup）"
  fi
else
  info "~/nest-backup はまだ無い（最初のバックアップで作る: uv run python scripts/backup.py dump）"
fi

echo ""
echo "[9] 音声の置き場所（nest_voice_data/。field-ui の録音。N-37）"
# NEST_VOICE_DIR は試験のときだけ使う（tests/test_doctor.py）
VOICE_DIR="${NEST_VOICE_DIR:-${PROJECT_DIR}/nest_voice_data}"
if [ -d "${VOICE_DIR}" ]; then
  vmode="$(stat -f %Lp "${VOICE_DIR}" 2>/dev/null || stat -c %a "${VOICE_DIR}" 2>/dev/null)"
  if [ "${vmode}" = "700" ]; then ok "nest_voice_data: 権限 700"; else fail "nest_voice_data の権限が ${vmode}（700 にする: chmod 700 \"${VOICE_DIR}\"）"; fi
  if tmutil isexcluded "${VOICE_DIR}" 2>/dev/null | grep -q "\[Excluded\]"; then
    ok "nest_voice_data: Time Machine の対象外"
  else
    fail "nest_voice_data が Time Machine の対象（tmutil addexclusion \"${VOICE_DIR}\"）"
  fi
  # 音声の名前は「64 桁の 16 進 ＋ 音声の拡張子」（nest/voice.py の NAME と同じ）
  old="$(find -E "${VOICE_DIR}" -maxdepth 1 -type f -mtime +30 \
    -regex '.*/[0-9a-f]{64}\.(webm|ogg|oga|mp3|m4a|mp4|wav|aac|flac)' 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${old}" = "0" ]; then
    ok "nest_voice_data: 30 日を過ぎた音声は無い"
  else
    fail "警告：30 日を過ぎた音声が ${old} 件残っている（uv run python scripts/purge_voice.py --write で消す）"
  fi
else
  info "nest_voice_data はまだ無い（field-ui の録音で作る）"
fi

echo ""
echo "[10] Claude Desktop の設定（知らせるだけ）"
if [ -f "${DESKTOP_CONFIG}" ]; then
  if grep -q '"nest-personal"' "${DESKTOP_CONFIG}"; then
    info "Desktop の設定に nest-personal がある"
  else
    info "Desktop の設定に nest-personal が無い（Claude Desktop を使うときだけ configs/claude_desktop_config.json を写す）"
  fi
else
  info "Desktop の設定が無い（Claude Code だけなら要らない）"
fi

echo ""
echo "=== Summary: ${PASS} passed, ${FAIL} failed ==="
[ "${FAIL}" -eq 0 ] && exit 0 || exit 1
