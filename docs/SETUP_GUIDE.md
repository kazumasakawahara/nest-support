# nest-support 導入ガイド

> **パソコンの操作に不慣れな方でも、このガイドの通りに進めれば導入できます。**
>
> 所要時間の目安: **30分〜1時間**（途中で休憩しても大丈夫です）

---

## このガイドの読み方

- 各ステップに **「なぜ必要か」** を添えています。意味がわかると安心して進められます
- `この書体` の部分は、パソコンに入力する文字列です。そのままコピーして貼り付けてください
- 「> こういう囲み」は、Claude に話しかけるときの例文です
- うまくいかないときは、各ステップの末尾にある **「うまくいかないとき」** を確認してください
- このガイドで解決しない場合は [FAQ.md](./FAQ.md) も参照してください

---

## このシステムの全体像

はじめに、「何を使って何ができるのか」を知っておくと、この先の手順が理解しやすくなります。

```
┌───────────────────────────────────────────────────────┐
│                                                       │
│  あなた（支援者）                                      │
│    ↕ 日本語で話しかける                                │
│  Claude Desktop（AIアシスタント）                       │
│    ↕ Skills（業務手順書）を参照して操作                  │
│  Neo4j（グラフデータベース）                            │
│    └─ 支援記録・禁忌事項・連絡先・手帳情報 などを保管    │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**ポイント**: あなたがやることは「Claude に話しかける」だけです。データベースの操作は Claude が代行します。

必要なアプリは **3つだけ** です:

| アプリ名 | 役割 | 日常的に例えると |
|---------|------|----------------|
| **Docker Desktop** | データベースを動かす土台 | データベースの「電源スイッチ」 |
| **Claude Desktop** | AIアシスタント | 何でも相談できる「データベース係」 |
| **Node.js** | Claude とデータベースをつなぐ裏方 | 「通訳」。設定後は意識しなくてOK |

---

## 全体の流れ

```
Step 1  3つのアプリを準備する
  ↓
Step 2  nest-support をダウンロードする
  ↓
Step 3  データベースを起動する
  ↓
Step 4  Claude にデータベースを教える（接続設定）
  ↓
Step 5  Claude に「業務手順書」を渡す（Skills 設定）
  ↓
Step 6  動作確認 — Claude に話しかけてみる
  ↓
Step 7  練習用データを入れてみる（やらなくてもOK）
```

> **時間の目安**:
> - Step 1（アプリの準備）: 10〜20分
> - Step 2〜5（設定）: 10〜20分
> - Step 6〜7（動作確認）: 5〜10分

---

## Step 1: 3つのアプリを準備する

すでにインストール済みのアプリは飛ばしてください。

---

### 1-1. Docker Desktop を入れる

**なぜ必要？** — クライアントの情報を保存するデータベース（Neo4j）を動かすための土台です。

#### ダウンロードとインストール

1. ブラウザで以下のページを開きます:
   https://www.docker.com/products/docker-desktop/

2. お使いのパソコンに合ったボタンをクリックしてダウンロードします
   - **Mac** の方: 「Download for Mac」
     - Apple Silicon（M1/M2/M3/M4）か Intel かを聞かれた場合:
       画面左上のリンゴマーク →「この Mac について」→「チップ」の欄を確認
   - **Windows** の方: 「Download for Windows」

3. ダウンロードしたファイルを開きます
   - **Mac**: `.dmg` ファイルを開き、Docker のアイコンを「アプリケーション」フォルダにドラッグ
   - **Windows**: `.exe` ファイルを開き、画面の指示に従って進めます
     - 「Use WSL 2 instead of Hyper-V」にチェックが入っていることを確認
     - インストール完了後「Close and restart」でパソコンを再起動

4. Docker Desktop を起動します
   - **Mac**: アプリケーションフォルダから「Docker」を開く
   - **Windows**: スタートメニューから「Docker Desktop」を検索して開く

5. 画面上部（Mac）またはタスクバー右下（Windows）に **クジラのアイコン** が表示されたら準備完了です

> **確認方法**: クジラのアイコンが出ていれば OK。初回は起動に1〜2分かかることがあります。

#### うまくいかないとき

| 症状 | 対処法 |
|------|--------|
| Windows で「WSL 2 が必要です」と出る | PowerShell を「管理者として実行」→ `wsl --install` と入力 → パソコン再起動 |
| Windows で「仮想化が無効です」と出る | 「お使いのPC名 BIOS 仮想化 有効」で検索して設定を変更 |
| Mac で「システム拡張がブロックされました」| 「システム設定」→「プライバシーとセキュリティ」で許可 |
| クジラのアイコンが出てこない | パソコンを再起動してからもう一度 Docker Desktop を開く |

---

### 1-2. Claude Desktop を入れる

**なぜ必要？** — このシステムの操作はすべて Claude（AI アシスタント）に日本語で話しかけて行います。

#### ダウンロードとインストール

1. ブラウザで以下のページを開きます:
   https://claude.ai/download

2. お使いの OS 版をダウンロードしてインストールします

3. Anthropic アカウントでログインします
   - アカウントがない場合は、画面の指示に従って作成できます（メールアドレスが必要）

#### 料金について

Claude Desktop の **Pro プラン（月額 約3,000円）** が必要です。
無料プランでは Claude との会話はできますが、データベースへの接続機能が使えません。

> **補助金のご案内**: ICT導入支援事業の補助金（補助率10/10）が活用できる場合があります。お住まいの自治体にお問い合わせください。

#### うまくいかないとき

| 症状 | 対処法 |
|------|--------|
| ログインできない | メールアドレスとパスワードを確認。「パスワードを忘れた場合」からリセット |
| アプリが開かない | パソコンを再起動してから試す |

---

### 1-3. Node.js を入れる

**なぜ必要？** — Claude Desktop とデータベースを橋渡しする裏方のプログラムです。一度入れたら、あとは意識する必要はありません。

#### ダウンロードとインストール

1. ブラウザで以下のページを開きます:
   https://nodejs.org/

2. **「LTS」と書かれた緑色のボタン** をクリック（「推奨版」という意味です）

3. ダウンロードしたファイルを開いてインストールします
   - すべてデフォルトのまま「Next」→「Next」→「Install」で OK です
   - Windows で「Automatically install the necessary tools」と出たらチェックを入れておくと便利です

4. **インストール後、パソコンを再起動してください**（再起動しないと反映されない場合があります）

#### 確認方法（やらなくても大丈夫ですが、心配な方向け）

Mac の方は「ターミナル」、Windows の方は「PowerShell」を開いて以下を入力:

```
node --version
```

`v20.xx.x` のようなバージョン番号が表示されれば OK です。

#### うまくいかないとき

| 症状 | 対処法 |
|------|--------|
| `command not found` と表示される | パソコンを再起動してからもう一度試す |
| どのバージョンか迷う | 必ず **LTS（推奨版）** を選ぶ |

---

## Step 2: nest-support をダウンロードする

**なぜ必要？** — nest-support のプログラム一式（データベースの設定・Claude への業務手順書など）をパソコンに取り込みます。

### 方法 A: ワンクリックインストーラーを使う（Step 2〜5 をまとめて実行）

**こちらがおすすめです。** Step 2 から Step 5 までの作業を自動で行ってくれます。

#### Mac の方

1. 「ターミナル」アプリを開きます
   - 見つけ方: Launchpad（ロケットのアイコン）→ 検索欄に「ターミナル」と入力
   - または: キーボードで `Command + スペース` →「ターミナル」と入力

2. 以下の1行をコピーして、ターミナルに貼り付けて、Enter キーを押します:

```bash
curl -sL https://raw.githubusercontent.com/kazumasakawahara/nest-support/main/installer/install-mac.sh | bash
```

3. 画面に質問が表示されたら「Y」を入力して Enter（「はい」という意味です）

4. 「セットアップが完了しました！」と表示されたら → **Step 6 に進んでください**

#### Windows の方

1. 「PowerShell」を **管理者として** 開きます
   - 見つけ方: スタートメニュー(画面左下)で「PowerShell」と検索
   - 検索結果の「Windows PowerShell」を**右クリック** →「管理者として実行」

2. 以下の2行をコピーして貼り付け、Enter キーを押します:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
irm https://raw.githubusercontent.com/kazumasakawahara/nest-support/main/installer/install-windows.ps1 | iex
```

3. 画面に質問が表示されたら「Y」を入力して Enter

4. 「セットアップが完了しました！」と表示されたら → **Step 6 に進んでください**

#### うまくいかないとき

| 症状 | 対処法 |
|------|--------|
| 「permission denied」| Mac: ターミナルで `chmod +x` をつけて実行 / Windows: 管理者で PowerShell を開く |
| ダウンロードが途中で止まる | インターネット接続を確認してもう一度実行 |
| 「Docker が起動していません」| Docker Desktop を起動してから再実行（Step 1-1 参照）|

---

### 方法 B: 手動でダウンロードする（方法 A がうまくいかない場合）

1. ブラウザで以下のページを開きます:
   https://github.com/kazumasakawahara/nest-support

2. 緑色の **「Code」ボタン** → **「Download ZIP」** をクリック

3. ダウンロードした ZIP ファイルを展開（解凍）します
   - Windows: ZIPファイルを右クリック →「すべて展開」
   - Mac: ZIPファイルをダブルクリック

4. 展開したフォルダを **「書類（Documents）」フォルダ** に移動します
   - 最終的に以下の場所にあれば OK:
     - Mac: `~/Documents/nest-support/`
     - Windows: `C:\Users\あなたの名前\Documents\nest-support\`

> **フォルダ名に注意**: 展開すると `nest-support-main` というフォルダ名になる場合があります。`nest-support` にリネームしてください。

方法 B の場合は、続けて Step 3 に進みます。

---

## Step 3: データベースを起動する

> **方法 A（ワンクリックインストーラー）を使った方は、この Step は完了済みです。Step 6 に進んでください。**

**なぜ必要？** — クライアントの情報を保存するデータベース（Neo4j）を起動します。

#### Mac の方

1. ターミナルを開きます
2. 以下を入力して Enter:

```bash
cd ~/Documents/nest-support
chmod +x setup.sh
./setup.sh
```

3. 「セットアップが完了しました！」と表示されるまで待ちます（初回は3〜5分かかることがあります）

#### Windows の方

1. PowerShell を管理者として開きます
2. 以下を入力して Enter:

```powershell
cd $env:USERPROFILE\Documents\nest-support
Set-ExecutionPolicy Bypass -Scope Process -Force
.\setup.ps1
```

3. 「セットアップが完了しました！」と表示されるまで待ちます

#### 確認方法

ブラウザで以下のアドレスを開いてみてください:

http://localhost:7474

ログイン画面が表示されたら成功です:
- ユーザー名: `neo4j`
- パスワード: `password`

> このログイン画面は「データベースの管理画面」です。普段使う必要はありません。
> データの操作は Claude を通じて行います。

#### うまくいかないとき

| 症状 | 対処法 |
|------|--------|
| 「docker: command not found」| Docker Desktop が起動しているか確認（Step 1-1）|
| 「port is already allocated」| Docker Desktop の画面で他のコンテナが動いていないか確認。動いていれば停止してからやり直す |
| ページが表示されない | 1〜2分待ってからもう一度アクセス。初回はデータベースの起動に時間がかかります |

---

## Step 4: Claude にデータベースの場所を教える（MCP 設定）

> **方法 A（ワンクリックインストーラー）を使った方は、この Step は完了済みです。Step 6 に進んでください。**

**なぜ必要？** — Claude Desktop に「データベースはここにありますよ」と教えてあげる設定です。

### 方法 A: 自動設定ツールを使う（推奨）

**Mac の方:**
```bash
cd ~/Documents/nest-support
chmod +x installer/configure-claude.sh
./installer/configure-claude.sh
```

**Windows の方:**
```powershell
cd $env:USERPROFILE\Documents\nest-support
.\installer\configure-claude.ps1
```

「完了」と表示されたら → Step 5 に進みます。

---

### 方法 B: 手動で設定する

自動設定がうまくいかない場合はこちら。

#### 4-B-1. 設定ファイルを開く

**Mac の方:**
1. Finder（ファイル管理）を開きます
2. メニューバーの「移動」→「フォルダへ移動」をクリック
3. 以下を入力して Enter:
   ```
   ~/Library/Application Support/Claude/
   ```
4. フォルダの中にある `claude_desktop_config.json` をダブルクリックで開きます
   - ファイルがない場合は、「テキストエディット」を開いて新しい空のファイルを作ります

**Windows の方:**
1. キーボードで `Windows キー + R` を押します（「ファイル名を指定して実行」が開きます）
2. 以下を貼り付けて OK:
   ```
   notepad %APPDATA%\Claude\claude_desktop_config.json
   ```
3. 「ファイルが見つかりません。新しく作成しますか？」と表示されたら「はい」を押します

#### 4-B-2. 設定内容を貼り付ける

ファイルの中身を **すべて消して**、以下を **丸ごとコピーして** 貼り付けてください:

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "npx",
      "args": ["-y", "@alanse/mcp-neo4j-server"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password"
      }
    },
    "livelihood-support-db": {
      "command": "npx",
      "args": ["-y", "@alanse/mcp-neo4j-server"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7688",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password"
      }
    }
  }
}
```

> **既に他の設定がある場合**: 上書きせず、`"mcpServers"` の中に `"neo4j"` と `"livelihood-support-db"` の部分だけを追加してください。不安な場合は、元のファイルをコピーしてバックアップしてから編集すると安心です。

#### 4-B-3. ファイルを保存する

- **Mac**: `Command + S`
- **Windows**: `Ctrl + S`

> **注意**: Windows のメモ帳で保存するとき、ファイル名が `claude_desktop_config.json.txt` のように `.txt` が付いてしまうことがあります。「ファイルの種類」を「すべてのファイル」にして、ファイル名の末尾が `.json` で終わるようにしてください。

#### Windows で「npx が見つからない」と言われる場合

Windows では、npx の場所を直接指定する必要があることがあります:

1. PowerShell を開いて以下を入力:
   ```
   where npx
   ```
2. 表示されたパス（例: `C:\Program Files\nodejs\npx.cmd`）を設定の `"command"` に使います:
   ```json
   "command": "C:\\Program Files\\nodejs\\npx.cmd",
   ```
   > パスの `\` は `\\` と2つ重ねて書くのがポイントです。

---

## Step 5: Claude に業務手順書を渡す（Skills の設定）

> **方法 A（ワンクリックインストーラー）を使った方は、この Step は完了済みです。Step 6 に進んでください。**

**なぜ必要？** — Skills（スキル）は、Claude に「このデータベースではこういう操作ができるよ」と教えるための業務手順書です。これがないと Claude はデータベースの使い方がわかりません。

#### Mac の方（setup.sh を実行済みなら完了しています）

Step 3 で `./setup.sh` を実行した場合、Skills は自動でインストールされています。
手動で再インストールする場合:

```bash
cd ~/Documents/nest-support
./setup.sh --skills
```

#### Windows の方

Skills のフォルダを手動でコピーします:

1. nest-support フォルダ内の `claude-skills` フォルダを開きます

2. 中にあるフォルダ（`neo4j-support-db`, `emergency-protocol` など13個）を**すべてコピー**します

3. 以下の場所に貼り付けます:
   ```
   C:\Users\あなたの名前\.claude\skills\
   ```

   > `.claude` フォルダが見えない場合:
   > エクスプローラーの上部メニュー「表示」→「隠しファイル」にチェックを入れてください
   >
   > `skills` フォルダがない場合:
   > `.claude` フォルダの中に `skills` という名前で新しいフォルダを作ってください

4. 以下のようなフォルダ構造になっていれば OK:
   ```
   C:\Users\あなたの名前\.claude\skills\
   ├── neo4j-support-db\         ← 障害福祉クライアント管理
   ├── livelihood-support\       ← 生活困窮者自立支援
   ├── provider-search\          ← 事業所検索
   ├── emergency-protocol\       ← 緊急時対応
   ├── ecomap-generator\         ← エコマップ生成
   ├── narrative-extractor\      ← テキスト→構造化データ
   ├── onboarding-wizard\        ← 新規登録ウィザード
   ├── visit-prep\               ← 訪問準備
   ├── resilience-checker\       ← レジリエンス診断
   ├── data-quality-agent\       ← データ品質チェック
   ├── html-to-pdf\              ← PDF変換
   ├── inheritance-calculator\   ← 相続計算
   └── wamnet-provider-sync\     ← WAM NET同期
   ```

---

### Claude Desktop を再起動する

**ここまでの設定を反映するため、Claude Desktop を一度完全に終了して開き直します。**

**Mac の方:**
1. 画面上部のメニューバーにある Claude のアイコンをクリック
2. 「Quit Claude」をクリック
3. アプリケーションフォルダから Claude を再度開く

**Windows の方:**
1. 画面右下のタスクバー通知領域（`∧` マーク）にある Claude のアイコンを右クリック
2. 「Quit」をクリック
3. スタートメニューから Claude Desktop を再度開く

> **注意**: ウィンドウの「×」ボタンだけではバックグラウンドで動いたままの場合があります。必ず「Quit」で完全終了してください。

### 接続成功の確認

Claude Desktop を開き直したとき、チャット入力欄のあたりに **ハンマーのようなアイコンと数字** が表示されていれば、データベースとの接続が成功しています。

---

## Step 6: 動作確認 — Claude に話しかけてみる

いよいよ、セットアップがうまくいったか確認します。

### テスト 1: データベースの接続確認

Claude Desktop を開いて、以下のように話しかけます:

> データベースの統計情報を教えて

Claude がデータベースにアクセスし、「クライアント数: 0」のような統計情報を返してくれたら **接続成功** です。

### テスト 2: はじめてのデータ登録

以下を Claude に入力してみましょう:

> 以下の情報をデータベースに登録してください。
>
> 名前: テスト太郎
> 生年月日: 1990年4月1日
> 血液型: A型
> 特性: 自閉スペクトラム症
> 禁忌事項: 後ろから急に声をかけないこと。パニックになる。
> 推奨ケア: 声をかけるときは正面から、ゆっくり話す。

Claude が情報を整理して確認してから、データベースに登録してくれます。

### テスト 3: 登録した情報を確認する

> テスト太郎さんのプロフィールを見せて

先ほど登録した情報が表示されれば、**セットアップは完了です！おめでとうございます！**

### テストデータの削除

動作確認が済んだら、テスト用のデータは削除しておきましょう:

> テスト太郎さんのデータをすべて削除してください

#### うまくいかないとき

| 症状 | 対処法 |
|------|--------|
| 「データベースに接続できません」| Docker Desktop が起動しているか確認。停止していれば起動してから Claude Desktop を再起動 |
| ツールアイコンに数字が出ない | Step 4 の設定ファイルを確認。カンマ（`,`）の過不足が原因のことが多い |
| 「npx: command not found」| Node.js がインストールされていない（Step 1-3 をやり直す）|
| Claude が Skills を使ってくれない | Step 5 の Skills フォルダが正しい場所にあるか確認 |

---

## Step 7: 練習用のデモデータを入れる（やらなくても OK）

操作に慣れるため、架空のデモデータで練習してみたい場合:

**Mac の方:**
```bash
cd ~/Documents/nest-support
chmod +x installer/load-demo-data.sh
./installer/load-demo-data.sh
```

**Windows の方:**
```powershell
cd $env:USERPROFILE\Documents\nest-support
.\installer\load-demo-data.ps1
```

デモデータ投入後、以下のように試せます:

> 山本翔太さんの緊急情報を教えて

> 鈴木花さんの禁忌事項を教えて

> 更新期限が近い手帳・受給者証を確認して

**感情シミュレーションデータも入れる場合（予兆検知の練習用）:**
```bash
# Mac — デモデータ + 1ヶ月分の感情データ
./installer/load-demo-data.sh --simulation

# Windows（PowerShell）
.\installer\load-demo-data.ps1 -Simulation
```

シミュレーションデータ投入後、以下も試せます:

> 山本翔太さんの最近の感情トレンドを分析して

> 山本翔太さんのリスク評価を実行して

**デモデータを削除する場合:**
```bash
# Mac
./installer/load-demo-data.sh --remove

# Windows（PowerShell）
.\installer\load-demo-data.ps1 -Remove
```

---

## セットアップ完了！ ここからの使い方

おめでとうございます！セットアップが完了しました。

### まず試してほしい 5 つの操作

詳しくは [FIRST_5_OPERATIONS.md](./FIRST_5_OPERATIONS.md) をご覧ください。

| やりたいこと | Claude にこう話しかける |
|-------------|----------------------|
| クライアントを登録する | 「新しいクライアントを登録したい」 |
| 緊急情報を確認する | 「〇〇さんの緊急情報を教えて」 |
| 訪問前の準備をする | 「〇〇さんの訪問準備をして」 |
| 支援記録を残す | 「〇〇さんの支援記録を追加:（内容）」 |
| 更新期限を確認する | 「更新期限が近い手帳を確認して」 |

### さらに使いこなしたい方

| やりたいこと | Claude にこう話しかける |
|-------------|----------------------|
| 意味で検索する | 「入浴を嫌がるケースを検索して」（「お風呂拒否」もヒット）|
| エコマップを作る | 「〇〇さんのエコマップを作成して」 |
| 事業所を探す | 「北九州市の生活介護で空きのある事業所を検索して」 |
| データの健全性を確認 | 「データ品質チェックをお願いします」 |
| 親なき後の備えを診断 | 「〇〇さんのレジリエンス診断をして」 |
| 感情トレンドを分析する | 「〇〇さんの最近の変化を分析して」 |
| 声で記録を残す | 音声ファイルを添付して「〇〇さんの支援記録として登録して」 |

### Gemini API の設定（音声・画像からの登録に必要）

音声ファイルの文字起こしや手書きメモの読み取りには、Google の Gemini API が必要です。

1. [Google AI Studio](https://aistudio.google.com/apikey) にアクセスして API キーを取得（無料）
2. プロジェクトフォルダの `.env` ファイルに追記:
   ```
   GEMINI_API_KEY=取得したキーをここに貼り付け
   ```

> **Note**: Gemini API キーがなくても、テキスト入力での登録やデータ閲覧は問題なく使えます。

詳しい録音の仕方は [VOICE_RECORDING_GUIDE.md](./VOICE_RECORDING_GUIDE.md) を参照してください。

> Claude は「わからないことはわからない」と正直に答えます。「使い方がわからない」「どんなことができるか一覧を見せて」と聞いても大丈夫です。

---

## 日常の起動手順（毎日やること）

セットアップは最初の1回だけです。普段は以下の手順だけで使えます:

```
1. パソコンを起動する
2. Docker Desktop が起動していることを確認（クジラのアイコン）
3. Claude Desktop を開く
4. 話しかける
```

> **便利な設定**: Docker Desktop を「ログイン時に自動起動」にしておくと、手順 2 を省略できます。
> Docker Desktop → Settings（歯車アイコン）→ General → 「Start Docker Desktop when you sign in」にチェック

### パソコンをシャットダウンするとき

特別な操作は不要です。次にパソコンを起動したとき、データは自動的に復元されます。

---

## データのバックアップ

クライアントの情報は大切な資産です。**月に1回はバックアップ**することをお勧めします。

### Mac の方

```bash
cd ~/Documents/nest-support
docker compose stop
cp -r neo4j_data neo4j_data_backup_$(date +%Y%m%d)
cp -r neo4j_livelihood_data neo4j_livelihood_data_backup_$(date +%Y%m%d)
docker compose start
```

### Windows の方

```powershell
cd $env:USERPROFILE\Documents\nest-support
docker compose stop
Copy-Item -Recurse neo4j_data "neo4j_data_backup_$(Get-Date -Format yyyyMMdd)"
Copy-Item -Recurse neo4j_livelihood_data "neo4j_livelihood_data_backup_$(Get-Date -Format yyyyMMdd)"
docker compose start
```

> ターミナル操作が不安な方は、Docker Desktop を停止してから、`neo4j_data` フォルダと `neo4j_livelihood_data` フォルダをそのままコピーして別の場所に保存するだけでも OK です。

---

## プライバシーについて

### データの保存場所

クライアントの情報は **すべてお使いのパソコンの中** に保存されます。外部のサーバーには送信されません。

ただし、Claude Desktop を通じて会話するとき、**入力した内容は Anthropic 社のサーバーに送信されます**。

個人情報を含むデータを入力する場合は、組織の個人情報保護方針と照らし合わせてご判断ください。

> 詳しくは [PRIVACY_GUIDELINES.md](./PRIVACY_GUIDELINES.md) をご確認ください。

### 仮名化機能

研修やデモの場面で個人情報を表示したくない場合、「仮名化」機能があります。
環境変数 `PSEUDONYMIZATION_ENABLED=true` を設定すると、表示時に名前が自動的にマスク（例: 山田→山●●）されます。データベース内の実データは変更されません。

---

## 用語集

| 用語 | やさしい説明 |
|------|-------------|
| **Docker Desktop** | データベースを動かすためのアプリ。「箱の中でデータベースを安全に動かす」イメージ |
| **Neo4j** | 人と人のつながりを記録するのが得意なデータベース。支援者・クライアント・医療機関の関係を自然に表現できる |
| **Claude Desktop** | Anthropic 社の AI アシスタント。日本語で話しかけるだけでデータベースを操作してくれる |
| **Node.js / npx** | Claude とデータベースをつなぐ裏方プログラム。一度設定したら意識不要 |
| **MCP** | Claude がデータベースなどの外部ツールと連携するための仕組み（Model Context Protocol の略）|
| **Skills** | Claude に業務の手順を教える説明書ファイル。14種類が用意されている |
| **ターミナル（Mac）** | パソコンに直接命令を入力するアプリ。Launchpad で「ターミナル」と検索すると見つかる |
| **PowerShell（Windows）** | Windows 版のターミナル。スタートメニューで「PowerShell」と検索すると見つかる |
| **ポート** | パソコン内の通信口の番号。nest-support は 7474, 7475, 7687, 7688 を使用 |
| **JSON** | 設定ファイルの書き方のルール。カンマや波かっこの位置が1つでもずれると動かない |
| **セマンティック検索** | キーワードの一致ではなく「意味」で検索する機能。「入浴拒否」で検索すると「お風呂を嫌がる」もヒットする |
| **embedding** | 文章を数値（ベクトル）に変換したもの。セマンティック検索の裏側で使われている技術 |

---

## 困ったときは

### まず Claude に聞いてみる

Claude Desktop で以下のように話しかけてください:

> セットアップで困っています

> 〇〇というエラーが出ました（エラーメッセージをそのまま伝える）

Claude がトラブルの内容を分析して、解決策を提案してくれます。

### よくあるつまずきと解決法

| 症状 | よくある原因 | 解決法 |
|------|------------|--------|
| Docker Desktop が起動しない | インストールが完了していない | パソコンを再起動 → Docker Desktop を開く |
| 「port is already allocated」 | 前回のデータベースが残っている | Docker Desktop でコンテナを停止 → 再起動 |
| Claude がデータベースにつながらない | 設定ファイルの記述ミス | Step 4-B-2 の内容を丸ごとコピーし直す |
| ツールアイコンに数字が出ない | Claude Desktop を再起動していない | Quit → 開き直し（×ボタンではなく Quit）|
| 「npx: command not found」 | Node.js 未インストール or 再起動していない | Step 1-3 をやり直す → パソコン再起動 |
| JSON の書式エラー | カンマの過不足 | Claude（claude.ai）に JSON を見せて「間違いがないか確認して」と聞く |

### それでも解決しない場合

- [FAQ.md](./FAQ.md) — よくある質問と詳しいトラブルシューティング
- IT担当の方やシステム管理者にご相談ください
- GitHub Issues: https://github.com/kazumasakawahara/nest-support/issues
