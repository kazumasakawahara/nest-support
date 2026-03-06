# FAQ & トラブルシューティング

---

## よくある質問

### Q: データはどこに保存されますか？

データはすべて**お使いのパソコン内**に保存されます。具体的には `nest-support/neo4j_data/` フォルダ内のDockerボリュームに格納されます。クラウドには送信されません。

ただし、Claude Desktop を通じて会話する際、入力内容は Anthropic 社のサーバーに送信されます。個人情報を含むデータを入力する場合は、組織の個人情報保護規程と照らし合わせて運用してください。

### Q: Claude Desktop の利用料金はいくらですか？

Claude Desktop は無料版でも基本的な操作が可能ですが、MCP（Neo4j接続）を使用するには Pro プラン（月額 $20 程度）が必要です。組織単位での契約については Anthropic 社のサイトをご確認ください。

ICT導入支援事業の補助金（補助率10/10）が活用できる場合があります。

### Q: 複数の担当者で使えますか？

はい。Neo4j データベースは同じネットワーク内の複数のパソコンからアクセスできます。ただし、現在のバージョンではユーザー管理機能（誰がどの操作をしたかの厳密な追跡）は Claude の会話ログに依存しています。

### Q: バックアップはどうすればよいですか？

```bash
# Neo4j データのバックアップ
docker compose stop
cp -r neo4j_data neo4j_data_backup_$(date +%Y%m%d)
cp -r neo4j_livelihood_data neo4j_livelihood_data_backup_$(date +%Y%m%d)
docker compose start
```

定期的なバックアップを推奨します。

### Q: データを別のパソコンに移行できますか？

はい。`neo4j_data/` と `neo4j_livelihood_data/` フォルダをコピーすることで移行できます。

### Q: インターネット接続は必要ですか？

初回セットアップ時にはインターネット接続が必要です（Docker イメージのダウンロード、Node.js パッケージの取得）。セットアップ後は、Claude Desktop の利用時にインターネット接続が必要ですが、Neo4j データベース自体はオフラインで動作します。

---

## トラブルシューティング

### Docker が起動しない

**症状**: `docker: command not found` または Docker Desktop が反応しない

**対処法（macOS）**:
1. Docker Desktop アプリが起動しているか確認（メニューバーにクジラのアイコン）
2. 起動していない場合: アプリケーションフォルダから Docker を開く
3. アイコンが表示されるまで1〜2分待つ
4. それでも動かない場合: Docker Desktop を再インストール

**対処法（Windows）**:
1. タスクバー右下の通知領域にクジラのアイコンがあるか確認
2. 起動していない場合: スタートメニューから「Docker Desktop」を検索して起動
3. 「Docker Desktop is starting...」が消えるまで待つ（初回は数分かかることがあります）
4. WSL2 バックエンドが有効か確認（Docker Desktop → Settings → General → Use the WSL 2 based engine）

```bash
# Docker の状態確認
docker info
```

### Neo4j に接続できない

**症状**: `curl: (7) Failed to connect to localhost port 7474`

**対処法**:
```bash
# コンテナの状態確認
docker ps | grep neo4j

# コンテナが停止している場合、再起動
docker compose up -d

# ログの確認
docker logs nest-support-neo4j
docker logs nest-support-neo4j-livelihood
```

**よくある原因**:
- Docker Desktop が起動していない
- ポートが他のアプリケーションに使われている（`lsof -i :7474` で確認）
- メモリ不足（Docker Desktop の Settings → Resources でメモリを4GB以上に設定）

### Claude Desktop で MCP ツールが表示されない

**症状**: ツールアイコンに neo4j が表示されない

**対処法（macOS）**:
1. 設定ファイルの確認:
```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

2. JSON の書式が正しいか確認（カンマの過不足に注意）

3. 自動設定ツールで修復:
```bash
cd nest-support
./installer/configure-claude.sh
```

4. Claude Desktop を完全に終了して再起動（メニューバーから Quit → 再度開く）

**対処法（Windows）**:
1. 設定ファイルの確認:
```powershell
Get-Content "$env:APPDATA\Claude\claude_desktop_config.json"
```

2. JSON の書式が正しいか確認（カンマの過不足に注意）

3. 自動設定ツールで修復:
```powershell
cd nest-support
.\installer\configure-claude.ps1
```

4. Claude Desktop を完全に終了して再起動（タスクトレイから右クリック → Quit → 再度起動）

**共通の確認事項**:

5. npx の動作確認:
```bash
npx -y @anthropic/neo4j-mcp-server --help
```

### Skills が認識されない

**症状**: Claude が Skills の機能を使ってくれない

**対処法（macOS）**:
```bash
# シンボリックリンクの確認
ls -la ~/.claude/skills/

# リンク先が正しいか確認
readlink ~/.claude/skills/neo4j-support-db

# 再インストール
cd nest-support
./setup.sh --skills
```

**対処法（Windows）**:
```powershell
# Skills ディレクトリの確認
dir $env:USERPROFILE\.claude\skills\

# 再インストール
cd nest-support
.\setup.ps1 -Skills
```

> **Windows の注意**: シンボリックリンク作成に管理者権限が必要な場合、自動的にジャンクションリンクまたはコピーにフォールバックします。

### 「エラー: Neo4j connection refused」と言われる

**症状**: Claude が「Neo4j に接続できません」と返す

**対処法**:
1. Docker コンテナが起動しているか確認: `docker ps`
2. ブラウザで http://localhost:7474 にアクセスできるか確認
3. MCP 設定のポート番号が正しいか確認（7687 / 7688）
4. Docker Desktop のリソース設定でメモリを確認（4GB以上推奨）

### デモデータの投入でエラーが出る

**症状**: `load-demo-data.sh` 実行時にエラー

**対処法**:
```bash
# Neo4j が起動しているか確認
curl -s http://localhost:7474

# 認証情報の確認（デフォルト: neo4j / password）
curl -u neo4j:password http://localhost:7474/db/neo4j/tx/commit \
  -H "Content-Type: application/json" \
  -d '{"statements": [{"statement": "RETURN 1"}]}'
```

初回起動時は Neo4j のパスワード設定に時間がかかることがあります。1〜2分待ってから再実行してください。

### Mac で「開発元を確認できない」と言われる

**症状**: スクリプト実行時にセキュリティ警告

**対処法**:
```bash
# ファイルの実行権限を確認・付与
chmod +x installer/install-mac.sh
chmod +x installer/configure-claude.sh
chmod +x setup.sh
```

### Windows で「スクリプトの実行が無効」と言われる

**症状**: `.ps1` ファイルを実行すると「このシステムではスクリプトの実行が無効になっています」と表示される

**対処法**:
```powershell
# 現在のセッションのみ実行を許可（推奨）
Set-ExecutionPolicy Bypass -Scope Process -Force

# その後スクリプトを実行
.\setup.ps1
```

> **注意**: `Set-ExecutionPolicy Bypass -Scope Process` は現在のPowerShellウィンドウのみに適用され、ウィンドウを閉じれば元に戻ります。システム全体の設定は変更しません。

### Windows で Docker のメモリが不足する

**症状**: Neo4j コンテナが起動後すぐに停止する、または「out of memory」エラー

**対処法**:
1. Docker Desktop → Settings → Resources → WSL Integration
2. メモリを 4GB 以上に設定
3. または `.wslconfig` で設定:

```
# %USERPROFILE%\.wslconfig に以下を記述
[wsl2]
memory=4GB
```

4. WSL を再起動: `wsl --shutdown` → Docker Desktop を再起動

### Windows でポートが使用中と表示される

**症状**: `docker compose up` で「port is already allocated」エラー

**対処法**:
```powershell
# 使用中のポートを確認
netstat -ano | findstr :7474
netstat -ano | findstr :7687

# 該当プロセスを確認（PID は上記コマンドの最後の列）
tasklist | findstr <PID>
```

ポートを使用しているプロセスを終了するか、`docker-compose.yml` のポート番号を変更してください。

### メモリ使用量が多い

**症状**: パソコンの動作が遅くなった

**対処法**:
- Docker Desktop の Settings → Resources で Neo4j に割り当てるメモリを調整
- `docker-compose.yml` の `NEO4J_server_memory_heap_max__size` を `256M` に下げる
- 使わないときは `docker compose stop` でコンテナを停止

---

## サポート・問い合わせ

困ったことがあれば、以下の方法でサポートを受けられます:

1. **Claude に聞く**: 「セットアップで困っています」と話しかけてください
2. **GitHub Issues**: バグ報告や機能要望は GitHub の Issues に投稿
3. **ユーザーコミュニティ**: 他の利用者と情報交換（準備中）
