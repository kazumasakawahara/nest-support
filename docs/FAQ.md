# FAQ & トラブルシューティング

- 版：2026-11-06（E-3。台帳 G-71。実務の問いだけ残し、前の構成の問い・手順は消した。手順の正は `docs/SETUP_GUIDE.md`）

---

## よくある質問

### Q: データはどこに保存されますか？

データはすべて**お使いの Mac の中**に保存されます。Docker で動く二つの DB（個人の側・資源の側）が、リポジトリの下の `nest_neo4j_personal_data/`・`nest_neo4j_resource_data/` に置きます（git には入りません）。DB は `127.0.0.1` だけで待ち受け、外からはつながりません。

Claude と会話するとき、入力した内容と、読み取りの包みが返したもの（仮名・禁忌などの項目。実名・電話・住所・生年月日・記録の原文は返さない）は Anthropic 社のサーバーに送られます。何を送るかの一覧は `docs/external-api.md` です。実際の利用者のデータは、契約の確認の記録がそろうまで Claude に渡しません（`docs/PRIVACY_GUIDELINES.md`）。

### Q: Claude の利用料金はいくらですか？

プランと料金は変わることがあるので、Anthropic 社のサイトで確かめてください。組織で使うときは、契約の形（データの扱い）も合わせて確かめます。

### Q: ChatGPT でも使えますか？

**使えません。Claude Desktop か Claude Code が要ります。**

1. **手元の DB に読み取りの包みでつなぐ作りです** — 個人の側の DB は Mac の中の `127.0.0.1` だけで待ち受け、Claude が手元で起こす MCP（`nest-personal`・`nest-resource`）から読みます
2. **スキルは Claude の仕組みです** — 話題に応じて Claude が手順書（`claude-skills/`）を読み込む仕組みを、他の AI チャットで動かす手段がありません
3. **個人情報の設計が崩れます** — 他の AI からつなぐには DB を外に出す必要があり、「データ本体は手元で完結」という設計（`docs/PRIVACY_GUIDELINES.md`）が成り立たなくなります

### Q: 複数の担当者で使えますか？

今の構成では、一台の Mac の中で使います。DB は `127.0.0.1` だけで待ち受けるので、ほかのパソコンからはつながりません。誰が何を書いたかは、ゲートの操作の記録（`AuditLog`）に残ります。複数の担当者で同じ DB を使う形は、まだ決めていません。

### Q: バックアップはどうすればよいですか？

**手順はまだありません**（計画 N-33。段階 F で決める）。置き場所は Mac の中、権限 700、Time Machine の対象外とし、外のサービスには置かない方針です。手順ができるまで、`nest_neo4j_personal_data/` を自分でほかの場所に写さないでください。

### Q: データを別のパソコンに移行できますか？

バックアップの手順（N-33）と一緒に決めます。それまでは移行しません。

### Q: インターネット接続は必要ですか？

最初の準備（Docker のイメージ、Python の環境）と、Claude との会話にはインターネット接続が要ります。DB そのものは手元だけで動きます。

---

## トラブルシューティング

**まず `./scripts/doctor.sh` を流してください。** 前の DB が動いていないこと、新しい DB の待ち受け、接続の設定のファイルの権限、`.mcp.json`、スキルのリンク、正典のずれを確かめ、FAIL の行に直し方を出します。よくあることは `docs/SETUP_GUIDE.md` の「10. うまくいかないとき」にあります。

### Docker が起動しない

**症状**: `docker: command not found` または Docker Desktop が反応しない

**対処法（macOS）**:
1. Docker Desktop アプリが起動しているか確認（メニューバーにクジラのアイコン）
2. 起動していない場合: アプリケーションフォルダから Docker を開く
3. アイコンが表示されるまで1〜2分待つ
4. それでも動かない場合: Docker Desktop を再インストール

```bash
# Docker の状態確認
docker info
```

### DB に接続できない

```bash
# 二つが動いていて、127.0.0.1 だけで待ち受けているか
docker ps --format '{{.Names}} {{.Ports}}'

# 止まっていれば起動する（起動の直後は 30 秒ほど待つ）
docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d

# ログの確認
docker logs nest-redesign-personal
```

接続の設定のファイル（`~/.config/nest/neo4j-redesign.env`）の中身は、画面に出したり人に見せたりしないでください。

### メモリ使用量が多い

**症状**: パソコンの動作が遅くなった

**対処法**:
- Docker Desktop の Settings → Resources で割り当てるメモリを調整
- 使わないときは `docker compose --env-file ~/.config/nest/neo4j-redesign.env down` で止める

---

## サポート・問い合わせ

1. **Claude に聞く**: 「セットアップで困っています」と話しかけてください
2. **GitHub Issues**: バグ報告や機能要望は GitHub の Issues に投稿
