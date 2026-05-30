#!/usr/bin/env bash
# nest-support 環境整合性チェック
# 使い方: ./scripts/doctor.sh
#
# 確認項目:
#   1. Docker コンテナ (nest-support-neo4j / port 7687) が起動中か
#      （別名コンテナが 7687 を提供する現状維持構成も許容）
#   2. Neo4j Bolt (7687) に接続できるか
#   3. ~/.claude/skills/ の 13 skills が nest-support を指しているか
#   4. .mcp.json が存在し neo4j を定義しているか（livelihood-support-db は 2026-05 廃止・除去済み）
#   5. Claude Desktop config に neo4j があるか
#
# 注: 生活困窮者自立支援（livelihood-support / port 7688）は 2026-05 に廃止したため
#     チェック対象外。詳細は decommissioned/README.md を参照。
#
# 結果は OK / FAIL / INFO で表示。最後に総合判定。

set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$HOME/.claude/skills"
DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

EXPECTED_SKILLS=(
  data-quality-agent ecomap-generator emergency-protocol html-to-pdf
  inheritance-calculator insight-agent narrative-extractor
  neo4j-support-db onboarding-wizard provider-search resilience-checker
  visit-prep wamnet-provider-sync
)

PASS=0
FAIL=0
ok()   { printf "  \033[32mOK\033[0m   %s\n" "$1"; PASS=$((PASS+1)); }
fail() { printf "  \033[31mFAIL\033[0m %s\n" "$1"; FAIL=$((FAIL+1)); }
info() { printf "  \033[33mINFO\033[0m %s\n" "$1"; PASS=$((PASS+1)); }

echo "=== nest-support doctor ==="
echo "project: $PROJECT_DIR"
echo ""

# 1. Docker containers (障害福祉DB / port 7687。生活困窮DB=7688 は廃止のためチェックしない)
echo "[1] Docker containers (障害福祉DB / port 7687)"
status=$(docker inspect -f '{{.State.Status}}' nest-support-neo4j 2>/dev/null || echo "missing")
if [ "$status" = "running" ]; then
  ok "nest-support-neo4j: running"
else
  alt=$(docker ps --filter publish=7687 --format '{{.Names}}' 2>/dev/null | head -1)
  if [ -n "$alt" ]; then
    info "nest-support-neo4j は $status だが、port 7687 は '$alt' が提供中（現状維持構成・機能上OK）"
  else
    fail "nest-support-neo4j: $status（port 7687 を提供するコンテナがありません）"
  fi
fi

# 2. Bolt connectivity (7687 のみ。7688 は廃止)
echo ""
echo "[2] Neo4j Bolt connectivity"
if nc -z localhost 7687 2>/dev/null; then ok "localhost:7687 reachable"; else fail "localhost:7687 unreachable"; fi

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
# 廃止済み livelihood-support の symlink が残っていないことを確認
if [ -L "$SKILLS_DIR/livelihood-support" ]; then
  fail "livelihood-support の symlink が残っています（廃止済み。削除してください）"
else
  ok "livelihood-support: 廃止・symlink 除去済み"
fi

# 4. Project .mcp.json
echo ""
echo "[4] Project .mcp.json"
MCP_FILE="$PROJECT_DIR/.mcp.json"
if [ -f "$MCP_FILE" ]; then
  if grep -q '"neo4j"' "$MCP_FILE"; then
    ok ".mcp.json defines neo4j (port 7687)"
  else
    fail ".mcp.json missing neo4j"
  fi
  if grep -q "7687" "$MCP_FILE"; then
    ok ".mcp.json uses port 7687"
  else
    fail ".mcp.json port is not 7687"
  fi
  # 生活困窮DBは廃止済み: livelihood-support-db が残っていないことを確認
  if grep -q "livelihood-support-db" "$MCP_FILE"; then
    fail ".mcp.json に廃止済みの livelihood-support-db が残っています（削除してください）"
  else
    ok "livelihood-support-db は .mcp.json から除去済み（廃止）"
  fi
else
  fail ".mcp.json not found"
fi

# 5. Claude Desktop config (optional — informational)
echo ""
echo "[5] Claude Desktop config (informational)"
if [ -f "$DESKTOP_CONFIG" ]; then
  if grep -q '"neo4j"' "$DESKTOP_CONFIG"; then
    ok "Desktop config defines neo4j"
  else
    info "Desktop config missing neo4j (Claude Desktop を使う場合のみ追加＋再起動が必要)"
  fi
else
  echo "  skip (config not found at $DESKTOP_CONFIG)"
fi

echo ""
echo "=== Summary: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
