# decommissioned/ — 廃止したコンポーネントの退避先

このディレクトリには、**運用を停止したが履歴・復元用に残す**コンポーネントを置く。
`claude-skills/` の外にあるため、`setup.sh` / `doctor.sh` のスキル走査の対象外であり、
`~/.claude/skills/` へ symlink されることもない。

## livelihood-support（生活困窮者自立支援）— 2026-05 廃止

生活困窮者自立支援データベース（port 7688）は今後使用しないため、以下を実施して
誤操作を防止している（すべて可逆）：

| 層 | 措置 |
|----|------|
| MCP 接続 | `.mcp.json` から `livelihood-support-db` を削除（Claude から 7688 へ到達不可） |
| Skill | `claude-skills/livelihood-support` → ここへ退避＋ `~/.claude/skills/` の symlink 削除 |
| Skill 発火 | 退避した `SKILL.md` の description 冒頭に「非運用」警告を付与 |
| Docker | `docker-compose.yml` の `neo4j-livelihood` サービスをコメントアウト |
| コンテナ | `nest-support-neo4j-livelihood` を削除（誤起動防止） |
| 検査 | `scripts/doctor.sh` から 7688 / livelihood のチェックを除外 |

### 再開する場合（手順）

1. `git mv decommissioned/livelihood-support claude-skills/livelihood-support`
2. `SKILL.md` の frontmatter description を元の説明に戻す（先頭の「非運用」警告を除去）
3. `docker-compose.yml` の `neo4j-livelihood` サービスのコメントを解除
4. `.mcp.json` に `livelihood-support-db`（port 7688）を再追加
5. `./setup.sh` を実行（symlink 再作成・コンテナ起動）
6. `scripts/doctor.sh` のチェックを元に戻す

> 注意: port 7688 のデータ実体は存在しない（過去に本データが投入されたことがない）。
> 再開時は新規にデータを投入する前提となる。
