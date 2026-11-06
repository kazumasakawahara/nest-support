# クイックスタート

- 版：2026-11-06（計画 N-29。ADR-001 の作り直しの構成に合わせて書き直した。Mac で確かめた手順。Windows は確かめていない）
- 詳しい手順は `docs/SETUP_GUIDE.md`

## 要るもの

| ツール | 用途 |
|---|---|
| Docker Desktop | Neo4j を二つ動かす（個人の側・資源の側） |
| uv | Python の環境と試験 |
| Claude Desktop か Claude Code | スキルと読み取りの MCP |

## 手順

```bash
# 1. 取ってきて、環境を作る
git clone https://github.com/kazumasakawahara/nest-support.git
cd nest-support
uv sync

# 2. 接続の設定のファイルを作る（リポジトリの外。中身は自分で書き、人に見せない）
mkdir -p ~/.config/nest
#    ~/.config/nest/neo4j-redesign.env に NEST_PERSONAL_PASSWORD と NEST_RESOURCE_PASSWORD を書き、
chmod 600 ~/.config/nest/neo4j-redesign.env

# 3. DB を起動する（127.0.0.1 だけで待ち受ける）
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d

# 4. 正典の制約を個人の側に作る（既定は流す文を出すだけ）
uv run python scripts/apply_schema.py --write

# 5. 資源の側に tsunagu-net の配布の一式を読み込む（MANIFEST.json の指紋を確かめる）
uv run python scripts/load_resource.py --bundle <配布の一式のフォルダ> --write

# 6. 試験と点検
./scripts/doctor.sh                   # 環境の点検
uv run pytest -q                      # DB を使わない試験
NEST_LIVE_DB=1 uv run pytest -q       # DB を使う試験（架空の事例だけ）

# 7. 使い終わったら止める
docker compose --env-file ~/.config/nest/neo4j-redesign.env down
```

## Claude からつなぐ

- Claude Code：リポジトリの `.mcp.json` に `nest-personal`・`nest-resource` がある。リポジトリで Claude Code を開けば使える
- スキル：`claude-skills/` の中のスキルを `~/.claude/skills/` にリンクする（例：`ln -s "$PWD/claude-skills/neo4j-support-db" ~/.claude/skills/`）
- 個人の側の MCP は、外に送る前の確認（`docs/external-api.md` NEXT-02 の設定と記録）がそろうか、架空の印のある DB のときだけ動く

## 最初に話しかける例（架空）

```
C-ZZZZZZ さんの禁忌を見せて
```

```
次の面談の記録（架空）から、書き込みの案を作って。DB には書かないで。
```
