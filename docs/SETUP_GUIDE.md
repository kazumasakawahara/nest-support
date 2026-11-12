# nest-support 導入ガイド

- 版：2026-11-06（計画 N-38 で「0. 新しい Mac でゼロから」と最初の管理者・現場の画面の手順を足した。N-29 でADR-001 の作り直しの構成に合わせて書き直した。前の版の「ワンクリックインストーラー」「Node.js の MCP」「二つの層の DB」の手順はやめた）
- 確かめた環境：Mac（Apple シリコン）。Windows の手順は、まだ確かめていない
- この文書を一つの正とする（前にあった HTML の写しは外した）

---

## 0. 新しい Mac でゼロから（順に）

配布物（インストーラー）はありません。次の順に手で進め、最後に `./scripts/doctor.sh` で結果を確かめます。

1. FileVault を有効にする（システム設定 → プライバシーとセキュリティ。DB のデータとバックアップを守る）
2. Docker Desktop・uv・Claude を入れる（2）
3. リポジトリを取り、`uv sync` と DB を使わない試験（3）
4. `~/.config/nest/neo4j-redesign.env` を作り、`chmod 600`（4）
5. `docker compose … up -d` で DB を起動し、127.0.0.1 だけで待ち受けていることを確かめる（5）
6. `uv run python scripts/apply_schema.py --write` で正典の制約、`scripts/load_resource.py` で資源のデータ（6）
7. `uv run python scripts/bootstrap_admin.py --name "…"` で最初の管理者（8）
8. field-ui を使う職員ごとに `uv run python scripts/staff_token.py add STF-…`（8）
9. `claude-skills/` を `~/.claude/skills` にリンクする（7）
10. `./scripts/doctor.sh` が FAIL 0 で終わることを確かめる（10）
11. 現場の画面 `field-ui/server.py` と `sos` を起動して確かめる（8）
12. DB に書いた日の終わりは、DB を止めてから `uv run python scripts/backup.py dump`（5）

---

## 1. 全体の形

```
職員 → Claude Desktop / Claude Code → スキル
          │ 読む（MCP）                         │ 書き込みの案（JSON）
          ▼                                     ▼
   個人の側の Neo4j（127.0.0.1:37687） ←── ゲート（職員が通す）
   資源の側の Neo4j（127.0.0.1:38687。事業所などの公開情報。読むだけ）
```

- Claude は DB に書きません。書くのはゲート（`nest/gate/`）だけで、すべてに操作の記録が付きます
- 本人は仮名（`displayCode`）で呼びます。読み取りの包みは実名・電話・住所・生年月日を返しません
- 外に送る先と中身は `docs/external-api.md` に一覧があり、既定は送りません

---

## 2. 用意するもの

| もの | 用途 | 入れ方 |
|---|---|---|
| Docker Desktop | Neo4j を二つ動かす | https://docs.docker.com/get-docker/ |
| uv | Python の環境 | https://docs.astral.sh/uv/ |
| Claude Desktop か Claude Code | スキルと MCP | https://claude.ai/download |

Docker Desktop は、起動してから次へ進みます。

---

## 3. リポジトリと環境

```bash
git clone https://github.com/kazumasakawahara/nest-support.git
cd nest-support
uv sync
uv run pytest -q                       # DB を使わない試験がすべて通ることを確かめる
uv run python scripts/check_drift.py   # 正典のずれ 0 件
```

---

## 4. 接続の設定のファイル

パスワードはリポジトリにも会話にも書きません。リポジトリの外のファイルに置きます。

```bash
mkdir -p ~/.config/nest
# エディタで ~/.config/nest/neo4j-redesign.env を作り、次の 2 行を書く（値は自分で決める。既定の値は使わない）
#   NEST_PERSONAL_PASSWORD=...
#   NEST_RESOURCE_PASSWORD=...
chmod 600 ~/.config/nest/neo4j-redesign.env
```

---

## 5. DB の起動と止め方

```bash
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d
docker ps --format '{{.Names}} {{.Ports}}'      # 二つとも 127.0.0.1 だけで待ち受けていることを確かめる
docker compose --env-file ~/.config/nest/neo4j-redesign.env down    # 使い終わったら止める
```

試験用の DB を起こした場合は、stop neo4j-test も打つ。down だけでは止まらない（`docker compose --env-file ~/.config/nest/neo4j-redesign.env stop neo4j-test`）。

| コンテナ | 中身 | 待ち受け |
|---|---|---|
| `nest-redesign-personal` | 個人の側（本人・家族・支援の記録） | 127.0.0.1:37687（Bolt）・37474（ブラウザ） |
| `nest-redesign-resource` | 資源の側（事業所などの公開情報） | 127.0.0.1:38687（Bolt）・38474（ブラウザ） |
| `nest-redesign-test` | DB を使う試験の専用（架空の残りだけ。profile "test" なので上の `up -d` では起きない。`docs/OPERATIONS.md` 段 10） | 127.0.0.1:36687（Bolt）・36474（ブラウザ） |

データはリポジトリの下の `nest_neo4j_personal_data/`・`nest_neo4j_resource_data/` に置かれます（git には入りません）。

バックアップ：DB に書き込んだ日の作業の終わりに、止めてから `uv run python scripts/backup.py dump`（`~/nest-backup/`、4 世代。`docs/PRIVACY_GUIDELINES.md` §5）。

---

## 6. 正典の制約と資源のデータ

```bash
uv run python scripts/apply_schema.py            # 流す文を見る
uv run python scripts/apply_schema.py --write    # 個人の側に制約・インデックスを作る

uv run python scripts/load_resource.py --bundle <tsunagu-net の配布の一式> --write
```

`load_resource.py` は配布の一式の `MANIFEST.json` の指紋を確かめ、合わなければ読み込みません。個人の側には触れません。

---

## 7. Claude からつなぐ

### MCP（読み取りだけ）

- Claude Code：リポジトリの `.mcp.json` に `nest-personal`（個人の側）と `nest-resource`（資源の側）がある
- Claude Desktop：`configs/claude_desktop_config.json` を写し、`<nest-support のフォルダ>` を自分の場所に直して、Claude Desktop の設定に足す

個人の側の MCP は、外に送る前の確認（`docs/external-api.md` NEXT-02 の設定と契約の確認の記録）がそろうか、架空の印のある DB のときだけ動きます。

### スキル

`claude-skills/` のスキルを `~/.claude/skills/` にリンクします。

```bash
for s in claude-skills/*/; do ln -sfn "$PWD/$s" ~/.claude/skills/"$(basename "$s")"; done
```

---

## 8. 最初の管理者・職員・本人・現場の画面

### 最初の管理者

個人の側に職員が一人もいないときだけ使えます。表示名は呼び名でかまいません。2 人目からは、管理者がゲートで登録します。

```bash
uv run python scripts/bootstrap_admin.py --name "事務局"    # 職員 ID（STF-…）が出る
```

### 職員ごとのトークン（field-ui）

```bash
uv run python scripts/staff_token.py add STF-…    # トークンは一度だけ画面に出る。職員に手で渡す
uv run python scripts/staff_token.py list         # 職員 ID だけ
uv run python scripts/staff_token.py remove STF-…
```

表は `~/.config/nest/field-ui-staff.json`（権限 600。職員 ID とトークンの sha256 だけ）。トークンはリポジトリにも会話にも書きません。

### 現場の画面と SOS を起動する

```bash
uv run python field-ui/server.py          # http://127.0.0.1:8001/  （ほかで使っていれば PORT=… で変える）
cd sos && uv run python api_server.py     # http://127.0.0.1:8000/app/?id=C-……（設定は sos/README.md）
```

- どちらも 127.0.0.1 だけで待ち受けます。DB は読みの包みとゲートを通して使います
- https を通さずに手元で試すときだけ `SESSION_COOKIE_SECURE=false` を付けます
- field-ui の音声は `nest_voice_data/` に置かれます（権限 700・Time Machine の対象外。`scripts/purge_voice.py --write` で消す。`docs/VOICE_RECORDING_GUIDE.md`）

### 本人を作る・書き込む

- 本人（氏名・生年月日・住所）を作るのは、職員が Claude の外の入口（手元のターミナル）で行い、仮名（`displayCode`）を受け取る

```bash
uv run python scripts/new_client.py add --staff STF-… --family 氏 --given 名 --birth YYYY-MM-DD --address "住所" --address-certainty 確度
uv run python scripts/new_client.py find --family 氏 --given 名     # 名前から仮名を引く
```

  この道具の出力（名前と仮名の対応）は、Claude の会話に貼りません。Claude には仮名だけを伝えます。同じ氏名の本人がいて、生年月日が同じか、どちらかに無ければ作りません（二重登録のおそれ）
- 聞いた話は `narrative-extractor` で書き込みの案（JSON）にし、職員が確かめてゲートに通す（`nest/gate/`）。AI が作ったものは未確定で入り、職員が一つずつ承認する
- 「無い」と確かめたことは、職員が確認の記録を作る（`nest.gate.write.record_review`）

---

## 9. 外した前の構成

`lib/`・`setup.sh`・`setup.ps1`・`installer/`・`scripts/rotate_password.py`・`scripts/multi_importer.py` は外しました（計画 N-38）。`field-ui/`・`sos/` は新しい構成に作り直しました（N-36・N-37）。

---

## 10. うまくいかないとき

まず `./scripts/doctor.sh` を流す。前の DB が動いていないこと、新しい DB の待ち受け、`~/.config/nest/` の設定のファイルの権限（あれば 600）、FileVault、バックアップと音声の置き場所、`.mcp.json`、スキルのリンク、正典のずれを確かめ、FAIL の行に直し方を出す。


| こと | 確かめること |
|---|---|
| `NEST_PERSONAL_PASSWORD が設定されていない` | `~/.config/nest/neo4j-redesign.env` の場所と 2 行 |
| DB につながらない | `docker ps` で二つが動いているか。起動の直後は 30 秒ほど待つ |
| 個人の側の MCP が動かない | NEXT-02 の設定と記録、または架空の印（7 の注） |
