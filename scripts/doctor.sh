#!/usr/bin/env bash
# nest-support 環境整合性チェック
# 使い方: ./scripts/doctor.sh
#
# 確認項目:
#   1. Docker コンテナ (nest-support-neo4j, nest-support-neo4j-livelihood) が起動中か
#   2. Neo4j Bolt (7687, 7688) に接続できるか
#   3. ~/.claude/skills/ の 14 skills が nest-support を指しているか
#   4. .mcp.json が存在し neo4j / livelihood-support-db を定義しているか
#   5. Claude Desktop config に neo4j / livelihood-support-db があるか
#
# 結果は OK / FAIL で表示。最後に総合判定。

set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$HOME/.claude/skills"
DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

EXPECTED_SKILLS=(
  data-quality-agent ecomap-generator emergency-protocol html-to-pdf
  inheritance-calculator insight-agent livelihood-support narrative-extractor
  neo4j-support-db onboarding-wizard provider-search resilience-checker
  visit-prep wamnet-provider-sync
)

PASS=0
FAIL=0
ok()   { printf "  \033[32mOK\033[0m   %s\n" "$1"; PASS=$((PASS+1)); }
fail() { printf "  \033[31mFAIL\033[0m %s\n" "$1"; FAIL=$((FAIL+1)); }

echo "=== nest-support doctor ==="
echo "project: $PROJECT_DIR"
echo ""

# 1. Docker containers
echo "[1] Docker containers"
for c in nest-support-neo4j nest-support-neo4j-livelihood; do
  status=$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || echo "missing")
  if [ "$status" = "running" ]; then ok "$c: running"; else fail "$c: $status"; fi
done

# 2. Bolt connectivity
echo ""
echo "[2] Neo4j Bolt connectivity"
for port in 7687 7688; do
  if nc -z localhost "$port" 2>/dev/null; then ok "localhost:$port reachable"; else fail "localhost:$port unreachable"; fi
done

# 3. Skills symlinks
# macOS はデフォルトで大文字小文字を区別しないファイルシステム (APFS case-insensitive)
# のため、パス文字列の case 差異は同一ディレクトリを指す。比較は lowercase で行う。
to_lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }
echo ""
echo "[3] Skills symlinks (expect -> nest-support/claude-skills)"
expected_base=$(to_lower "$PROJECT_DIR/claude-skills")
for skill in "${EXPECTED_SKILLS[@]}"; do
  link="$SKILLS_DIR/$skill"
  if [ ! -L "$link" ]; then fail "$skill: not a symlink"; continue; fi
  target=$(readlink "$link")
  target_lower=$(to_lower "$target")
  if [ "$target_lower" = "$expected_base/$skill" ]; then
    ok "$skill"
  else
    fail "$skill -> $target"
  fi
done

# 4. Project .mcp.json
echo ""
echo "[4] Project .mcp.json"
MCP_FILE="$PROJECT_DIR/.mcp.json"
if [ -f "$MCP_FILE" ]; then
  if grep -q '"neo4j"' "$MCP_FILE" && grep -q '"livelihood-support-db"' "$MCP_FILE"; then
    ok ".mcp.json defines neo4j and livelihood-support-db"
  else
    fail ".mcp.json missing neo4j or livelihood-support-db"
  fi
  if grep -q "7687" "$MCP_FILE" && grep -q "7688" "$MCP_FILE"; then
    ok ".mcp.json uses ports 7687/7688"
  else
    fail ".mcp.json ports are not 7687/7688"
  fi
else
  fail ".mcp.json not found"
fi

# 5. Claude Desktop config (optional — warn only)
echo ""
echo "[5] Claude Desktop config (informational)"
if [ -f "$DESKTOP_CONFIG" ]; then
  if grep -q '"neo4j"' "$DESKTOP_CONFIG" && grep -q '"livelihood-support-db"' "$DESKTOP_CONFIG"; then
    ok "Desktop config defines neo4j and livelihood-support-db"
  else
    fail "Desktop config missing neo4j or livelihood-support-db (Desktop restart required after edits)"
  fi
else
  echo "  skip (config not found at $DESKTOP_CONFIG)"
fi

echo ""
echo "=== Summary: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
