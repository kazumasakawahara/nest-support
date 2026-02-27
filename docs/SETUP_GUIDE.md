# nest-support セットアップガイド

**はじめてパソコンにこのシステムを導入する方のためのガイドです。**

このガイドでは、支援記録データベース「nest-support」を動かすために必要なソフトのインストールから、実際にClaudeに話しかけて使い始めるところまでを、画面の操作に沿って説明します。

所要時間の目安は30〜60分です。途中でわからなくなったら、Claudeに「セットアップで困っています」と相談することもできます。

---

## このシステムの全体像

まず、このシステムが何で構成されているかを簡単に説明します。

```
┌─────────────────────────────────────────────────────┐
│  あなた（支援者）                                      │
│    ↕ 日本語で話しかける                                │
│  Claude Desktop（AIアシスタント）                       │
│    ↕ Skills（業務手順書）を参照して                      │
│  Neo4j（グラフデータベース）                            │
│    └─ 支援記録・禁忌事項・連絡先・手帳情報 などを保管    │
└─────────────────────────────────────────────────────┘
```

必要なソフトは3つだけです。

| ソフト名 | 役割 | 例えるなら |
|---------|------|----------|
| Docker Desktop | データベースを動かす箱 | データベースの「電源」 |
| Claude Desktop | AIアシスタント | 「相談員」。あなたの代わりにDBを操作 |
| Node.js | ClaudeとDBをつなぐ通訳 | 「通訳係」 |

---

## ステップ 0: ファイルのダウンロード

まず、このプロジェクトのファイル一式をパソコンに保存します。

### 方法A: ZIPでダウンロード（かんたん）

1. ブラウザで以下のページを開きます:
   `https://github.com/kazumasakawahara/nest-support`
2. 緑色の「Code」ボタンをクリックします
3. 「Download ZIP」をクリックします
4. ダウンロードしたZIPファイルを展開（解凍）します

**展開先のおすすめ:**

| OS | 保存先 |
|----|-------|
| Windows | `C:\Users\あなたの名前\Documents\nest-support` |
| Mac | `~/Documents/nest-support` |

### 方法B: Gitでクローン（Gitを知っている方）

```bash
git clone https://github.com/kazumasakawahara/nest-support.git
```

---

## ステップ 1: Docker Desktop のインストール

Docker Desktop は、データベース（Neo4j）を動かすために必要です。

### Windows の場合

1. 以下のページにアクセスします:
   `https://www.docker.com/products/docker-desktop/`

2. 「Download for Windows」をクリックしてインストーラをダウンロードします

3. ダウンロードした `Docker Desktop Installer.exe` をダブルクリックして実行します

4. インストール画面が表示されたら、そのまま「OK」や「Next」を押していきます
   - 「Use WSL 2 instead of Hyper-V」にチェックが入っていることを確認してください
   - WSL 2 のインストールを求められた場合は、画面の指示に従います

5. インストールが完了したら「Close and restart」でパソコンを再起動します

6. 再起動後、Docker Desktop が自動的に起動します。画面左下に「Docker Desktop is running」と表示されればOKです

**よくあるトラブル（Windows）:**

- 「WSL 2 が必要です」と表示された場合:
  - スタートメニューで「PowerShell」を右クリック →「管理者として実行」を選びます
  - 開いた画面に `wsl --install` と入力してEnterキーを押します
  - パソコンを再起動します

- 「仮想化が無効です」と表示された場合:
  - パソコンのBIOS設定で仮想化（VT-x / AMD-V）を有効にする必要があります
  - メーカーによって手順が異なるため、「お使いのPC名 BIOS 仮想化 有効」で検索してください

### Mac の場合

1. 以下のページにアクセスします:
   `https://www.docker.com/products/docker-desktop/`

2. 「Download for Mac」をクリックします
   - Apple Silicon（M1/M2/M3/M4）の場合は「Apple Silicon」を選択
   - Intel Macの場合は「Intel Chip」を選択
   - どちらかわからない場合: 画面左上のリンゴマーク →「このMacについて」→ チップの欄を確認

3. ダウンロードした `.dmg` ファイルを開き、Docker アイコンを Applications にドラッグします

4. アプリケーションフォルダから Docker を起動します

### 動作確認

Docker Desktop が起動した状態で、以下の手順で確認します。

**Windows:** スタートメニューから「コマンドプロンプト」または「PowerShell」を開きます
**Mac:** 「ターミナル」アプリを開きます

以下を入力してEnterキーを押します:

```
docker --version
```

`Docker version 27.x.x` のような表示が出ればOKです。

---

## ステップ 2: Node.js のインストール

Node.js は、Claude と Neo4j データベースをつなぐために必要です。

### Windows の場合

1. 以下のページにアクセスします:
   `https://nodejs.org/`

2. 「LTS」と書かれたボタン（推奨版）をクリックしてダウンロードします

3. ダウンロードした `.msi` ファイルをダブルクリックして実行します

4. インストール画面では全て「Next」を押していきます
   - 「Automatically install the necessary tools」にチェックを入れると便利です

5. インストール完了後、コマンドプロンプトを**一度閉じて開き直し**てから確認します:

```
node --version
npx --version
```

両方ともバージョン番号が表示されればOKです。

### Mac の場合

1. 以下のページにアクセスします:
   `https://nodejs.org/`

2. 「LTS」版をダウンロードしてインストーラを実行します

3. ターミナルで確認します:

```
node --version
npx --version
```

---

## ステップ 3: Claude Desktop のインストール

### Windows / Mac 共通

1. 以下のページにアクセスします:
   `https://claude.ai/download`

2. お使いのOSに合ったインストーラをダウンロードして実行します

3. Anthropic アカウントでログインします（アカウントがない場合は作成します）

> Claude Desktop は Pro プラン（月額20ドル）以上で利用できます。

---

## ステップ 4: Neo4j データベースの起動

ここからは、ステップ0でダウンロードした nest-support フォルダの中で作業します。

### Windows の場合

1. エクスプローラーで `nest-support` フォルダを開きます

2. フォルダ内の空いている場所で Shiftキーを押しながら右クリック →「PowerShell ウィンドウをここで開く」を選択します
   （または「ターミナルで開く」）

3. 以下のコマンドを入力してEnterキーを押します:

```powershell
docker compose up -d
```

4. 初回は必要なファイルのダウンロードが始まります。数分かかることがあります

5. 完了したら、ブラウザで以下を開いて確認します:
   `http://localhost:7474`

6. ログイン画面が表示されたら以下を入力します:
   - Username: `neo4j`
   - Password: `password`

データベースの管理画面が開けば成功です。

### Mac の場合

1. ターミナルで nest-support フォルダに移動します:

```bash
cd ~/Documents/nest-support   # 保存した場所に合わせて変更
```

2. セットアップスクリプトを実行します:

```bash
chmod +x setup.sh
./setup.sh
```

3. ブラウザで `http://localhost:7474` を開いて確認します

---

## ステップ 5: Claude Desktop と Neo4j をつなぐ（MCP設定）

これが一番大事なステップです。Claude が Neo4j データベースを操作できるように設定します。

### 設定ファイルを開く

**Windows の場合:**

1. キーボードで `Windowsキー + R` を押します
2. 表示された「ファイル名を指定して実行」に以下を貼り付けてOKを押します:

```
notepad %APPDATA%\Claude\claude_desktop_config.json
```

3. もし「ファイルが見つかりません。新しいファイルを作成しますか？」と表示されたら「はい」を押します

**Mac の場合:**

1. ターミナルで以下を実行します:

```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### 設定内容を書き込む

開いたファイルに、以下の内容をそのままコピー＆ペーストします。

**ファイルが空の場合（新規）:**

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "npx",
      "args": ["-y", "@anthropic/neo4j-mcp-server"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password"
      }
    }
  }
}
```

**既に他の設定がある場合:**

`"mcpServers"` の中に `"neo4j": { ... }` の部分だけを追加します。追加する位置は、他のサーバー設定の後ろ（カンマで区切って）です。

### Windows で npx のパスが通らない場合

Windowsでは、npx のフルパスを指定する必要がある場合があります。

コマンドプロンプトで以下を実行して、npx の場所を確認します:

```
where npx
```

表示されたパス（例: `C:\Program Files\nodejs\npx.cmd`）を設定に使います:

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "C:\\Program Files\\nodejs\\npx.cmd",
      "args": ["-y", "@anthropic/neo4j-mcp-server"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password"
      }
    }
  }
}
```

> パスの `\` は `\\` と2つ重ねて書くのがポイントです。

### 設定を保存して Claude Desktop を再起動

1. ファイルを保存します（Ctrl+S / Cmd+S）
2. Claude Desktop を完全に終了します
   - **Windows:** タスクバーの通知領域（画面右下の `^` マーク）から Claude アイコンを右クリック →「Quit」
   - **Mac:** メニューバーの Claude →「Quit Claude」
3. Claude Desktop を再起動します

---

## ステップ 6: Skills のインストール

Skills は「業務手順書」のようなもので、Claudeが支援業務に特化した対応をするために必要です。

### Windows の場合

1. nest-support フォルダ内の `claude-skills` フォルダをコピーします

2. 以下のフォルダに貼り付けます（フォルダがなければ作成します）:

```
C:\Users\あなたの名前\.claude\skills\
```

> `.claude` フォルダが見えない場合は、エクスプローラーの「表示」タブ →「隠しファイル」にチェックを入れます

具体的には、以下のようなフォルダ構造になればOKです:

```
C:\Users\あなたの名前\.claude\skills\
├── neo4j-support-db\
│   └── SKILL.md
├── visit-prep\
│   └── SKILL.md
├── resilience-checker\
│   └── SKILL.md
├── onboarding-wizard\
│   └── SKILL.md
├── data-quality-agent\
│   └── SKILL.md
├── provider-search\
│   └── SKILL.md
├── ecomap-generator\
│   └── SKILL.md
├── emergency-protocol\
│   └── SKILL.md
├── ... その他のスキル
```

### Mac の場合

セットアップスクリプトが自動でインストール済みです。手動で行う場合:

```bash
cd ~/Documents/nest-support
./setup.sh --skills
```

---

## ステップ 7: 動作確認

すべてのセットアップが完了しました。実際に使ってみましょう。

### 確認 1: Neo4j との接続

Claude Desktop を開いて、以下のように話しかけます:

```
データベースに接続できていますか？
```

Claude がデータベースの状態を返答できれば、接続は成功しています。

### 確認 2: はじめてのデータ登録

以下のように話しかけて、テストデータを登録してみましょう:

```
テスト用のクライアント「テスト太郎」さんを登録してください。
生年月日は1990年4月15日、血液型はA型です。
禁忌事項として「大きな音」（リスクレベル: パニック）を登録してください。
```

### 確認 3: データの検索

登録したデータを確認します:

```
テスト太郎さんの情報を教えてください。
```

禁忌事項を含むクライアント情報が表示されれば、システムは正常に動作しています。

テストが終わったら、テストデータは削除して構いません:

```
テスト太郎さんのデータを削除してください。
```

---

## 日常の使い方

### パソコンを起動したとき

1. **Docker Desktop** が自動起動していることを確認します（タスクバー/メニューバーにクジラのアイコン）
2. 自動起動していない場合は、Docker Desktop を手動で起動します
3. **Claude Desktop** を起動します

> Docker Desktop は「Settings → General → Start Docker Desktop when you sign in」にチェックを入れると自動起動します。

### パソコンをシャットダウンするとき

特別な操作は不要です。次回起動時にデータベースは自動的に復元されます。

### よく使うフレーズ

| やりたいこと | Claudeへの話しかけ方 |
|------------|-------------------|
| クライアント情報の確認 | 「○○さんの情報を教えて」 |
| 禁忌事項の登録 | 「○○さんに禁忌事項を追加して」 |
| 訪問前の確認 | 「明日○○さんを訪問します。ブリーフィングをお願いします」 |
| 緊急時の情報取得 | 「○○さんがパニックを起こしています」 |
| 手帳の更新期限確認 | 「更新期限が近いクライアントを教えて」 |
| データの健全性チェック | 「データ品質チェックをお願いします」 |
| 親亡き後シミュレーション | 「○○さんのレジリエンス診断をして」 |

---

## トラブルシューティング

### 「Neo4j に接続できません」と言われた

**原因 1: Docker Desktop が起動していない**

→ タスクバー（Windows）/ メニューバー（Mac）にクジラのアイコンがあるか確認します。なければ Docker Desktop を起動してください。

**原因 2: Neo4j コンテナが止まっている**

→ コマンドプロンプト / ターミナルで以下を実行します:

```
docker ps
```

`nest-support-neo4j` が表示されていない場合:

```
cd （nest-supportフォルダのパス）
docker compose up -d
```

**原因 3: MCP設定が正しくない**

→ ステップ 5 の設定内容を再確認してください。特に以下の点:
- JSON の括弧 `{ }` やカンマ `,` の対応が正しいか
- Windows の場合、npx のフルパスが必要な場合があります

### Claude が Skills を認識しない

→ Skills フォルダの場所を確認します:
- **Windows:** `C:\Users\あなたの名前\.claude\skills\` の中にスキルのフォルダがあるか
- **Mac:** `~/.claude/skills/` の中にスキルのフォルダがあるか

### 「npx が見つかりません」と表示される

→ Node.js のインストールが完了していないか、パスが通っていない可能性があります:

**Windows:** コマンドプロンプトを閉じて開き直してから `npx --version` を試してください。それでも駄目な場合はパソコンを再起動してください。

**Mac:** ターミナルで `npx --version` を確認してください。

### JSON の書式エラー

Claude Desktop の設定ファイル（JSON）は、カンマや括弧が1つでもずれると動きません。
よくある間違い:

```json
// NG: 最後のカンマが余計
{
  "mcpServers": {
    "neo4j": { ... },   ← この最後のカンマが不要（この後に何もない場合）
  }
}

// OK
{
  "mcpServers": {
    "neo4j": { ... }
  }
}
```

JSONの書式に自信がない場合は、設定ファイルの内容をClaude（claude.ai）に貼り付けて「このJSONに間違いがないか確認して」と聞くこともできます。

---

## データのバックアップ

支援データは大切な情報です。定期的なバックアップを推奨します。

### 手動バックアップ

nest-support フォルダ内の `neo4j_data` フォルダをコピーするだけです。

**Windows:**

1. Docker Desktop でコンテナを停止します（左側メニューの「Containers」→ `nest-support-neo4j` の停止ボタン）
2. `neo4j_data` フォルダをコピーして、安全な場所に保存します
3. コンテナを再度起動します

**Mac:**

```bash
cd （nest-supportフォルダのパス）
docker compose stop
cp -r neo4j_data neo4j_data_backup_$(date +%Y%m%d)
docker compose up -d
```

> バックアップは少なくとも月に1回、または重要なデータを登録した後に行うことをお勧めします。

---

## 困ったときは

- **システムの使い方がわからない**: Claude Desktop で「〇〇の使い方を教えて」と聞いてみてください
- **エラーが出た**: エラーメッセージをそのまま Claude に伝えると、解決策を提案してくれます
- **インストールで詰まった**: IT担当の方や、このシステムの管理者に相談してください
