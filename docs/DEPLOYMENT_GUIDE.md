# 本番デプロイ手順書（運用前チェックリスト）

field-ui / sos を本番運用する際の、リバースプロキシ設置・TLS・レート制限・`.env`
設定の手引き。**このファイルに実際の秘密情報（トークン等）を書かないこと。**
値はサーバ上の `.env`（gitignore 済み）にのみ置く。

関連: [`../CLAUDE.md`](../CLAUDE.md) のアーキテクチャ節、[`AUTH_MANUAL_VERIFICATION_2026-07.md`](AUTH_MANUAL_VERIFICATION_2026-07.md)、[`PRIVACY_GUIDELINES.md`](PRIVACY_GUIDELINES.md)。

---

## 全体構成

```
             インターネット（HTTPS）
                     │
          ┌──────────▼───────────┐
          │  リバースプロキシ      │  ← TLS 終端 / レート制限 / 圧縮
          │  (Caddy 推奨 / nginx) │
          └───┬───────────────┬──┘
   127.0.0.1  │               │  127.0.0.1
        :8001 ▼               ▼ :8000
      ┌────────────┐    ┌────────────┐
      │  field-ui  │    │    sos     │  ← どちらも 127.0.0.1 バインド
      │ (認証必須)  │    │ (SOS無認証) │     （BIND_HOST 既定）
      └─────┬──────┘    └─────┬──────┘
            └────────┬─────────┘
                     ▼
                  Neo4j :7687
```

**設計上の要点**
- field-ui / sos は **`127.0.0.1` のみにバインド**（`BIND_HOST` 既定）。外部公開は必ずプロキシ経由。アプリを直接 `0.0.0.0` で晒さない。
- TLS・レート制限・（必要なら Basic 認証）は**プロキシに委譲**する。アプリ内は共有トークン認証で多層防御する。
- **SOS（`/api/sos`）は意図的に無認証**（緊急導線を殺さないため）。認証を足さないこと。代わりに応答は実名を返さず、**レート制限で乱用を抑える**。
- `/api/login` は総当たり対象になり得るので**レート制限必須**。

---

## 1. `.env` チェックリスト

サーバ上の `.env`（プロジェクトルート）に設定する。`.env.example` をコピーして埋める。

| 変数 | 必須 | 本番の推奨値 | 備考 |
|------|:---:|------|------|
| `APP_ACCESS_TOKEN` | ✅ | `openssl rand -base64 48` で生成した長い乱数 | **未設定だと保護APIは 503（fail-closed）**。field-ui のログイン合言葉。 |
| `SESSION_COOKIE_SECURE` | ✅ | `true` | HTTPS 前提。プロキシで TLS 終端するので true。 |
| `BIND_HOST` | ✅ | `127.0.0.1` | 外部公開はプロキシ経由のみ。 |
| `TRUST_PROXY_HEADERS` | ✅ | `false` | 共有トークン運用では false 固定。`X-Authenticated-User` を信頼するのは、外部由来ヘッダを剥がして付与する構成のときだけ。 |
| `CORS_ALLOW_ORIGINS` | ー | 通常は**未設定** | プロキシ配下の同一オリジン運用なら不要。別オリジンの PWA から叩く場合のみカンマ区切りで明示（`*` 不可）。 |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | ✅ | 実接続情報 | Neo4j の資格情報。 |
| `GEMINI_API_KEY` | ー | 設定推奨 | embedding・音声文字起こし・OCR に使用。未設定でも中核機能は動作（検索系がスキップ）。 |
| `LINE_CHANNEL_ACCESS_TOKEN` / `LINE_GROUP_ID` | ー | SOS を使う場合 ✅ | SOS の LINE 通知。未設定だと通知はスキップ。 |
| `PSEUDONYMIZATION_ENABLED` | ー | 用途次第 | 研修・デモで匿名化するとき true。Python 経路のみ有効。 |

トークン生成例:
```bash
openssl rand -base64 48   # APP_ACCESS_TOKEN に貼る（出力はどこにも残さない）
```

**投入後の確認**（`docs/AUTH_MANUAL_VERIFICATION_2026-07.md` と同じ手順）:
未認証で `/api/clients` が 401、`/api/login` に正しい合言葉で 200 + Cookie、Cookie 付きで 200 になること。

---

## 2A. Caddy（推奨・自動 TLS）

Let's Encrypt による証明書自動取得・更新が標準で付く。レート制限は
[`caddy-ratelimit`](https://github.com/mholt/caddy-ratelimit) プラグインを組み込んだ
バイナリが必要（`xcaddy build --with github.com/mholt/caddy-ratelimit`）。

`Caddyfile` の例（`example.org` は実ドメインに置換）:

```caddyfile
{
    # レート制限プラグイン利用時のみ有効化
    order rate_limit before reverse_proxy
}

field.example.org {
    encode gzip

    # ログイン総当たり対策（IP あたり 5 回 / 分）
    @login path /api/login
    rate_limit @login {
        zone login_zone {
            key    {remote_host}
            events 5
            window 1m
        }
    }

    reverse_proxy 127.0.0.1:8001
}

sos.example.org {
    encode gzip

    # 無認証 SOS の乱用抑制（IP あたり 10 回 / 分）。緊急導線なので過度に絞らない。
    @sos path /api/sos
    rate_limit @sos {
        zone sos_zone {
            key    {remote_host}
            events 10
            window 1m
        }
    }

    reverse_proxy 127.0.0.1:8000
}
```

起動:
```bash
sudo caddy run --config /etc/caddy/Caddyfile
# または systemd 経由（caddy パッケージ標準の caddy.service）
```

> レート制限プラグインを入れない場合は `rate_limit` ブロックを削除し、レート制限は
> nginx（2B）か WAF/前段で行う。

---

## 2B. nginx（レート制限がビルトイン）

証明書は certbot（Let's Encrypt）で取得済みとする。

```nginx
# /etc/nginx/conf.d/nest-support.conf

# レート制限ゾーン（http ブロックに置く）
limit_req_zone $binary_remote_addr zone=login_zone:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=sos_zone:10m   rate=10r/m;

server {
    listen 443 ssl http2;
    server_name field.example.org;

    ssl_certificate     /etc/letsencrypt/live/field.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/field.example.org/privkey.pem;

    # ログイン総当たり対策
    location = /api/login {
        limit_req zone=login_zone burst=3 nodelay;
        proxy_pass http://127.0.0.1:8001;
        include proxy_params;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        include proxy_params;
    }
}

server {
    listen 443 ssl http2;
    server_name sos.example.org;

    ssl_certificate     /etc/letsencrypt/live/sos.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sos.example.org/privkey.pem;

    # 無認証 SOS の乱用抑制（緊急導線なので burst に余裕を持たせる）
    location = /api/sos {
        limit_req zone=sos_zone burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        include proxy_params;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        include proxy_params;
    }
}

# HTTP → HTTPS リダイレクト
server {
    listen 80;
    server_name field.example.org sos.example.org;
    return 301 https://$host$request_uri;
}
```

`/etc/nginx/proxy_params`（無ければ作成）:
```nginx
proxy_set_header Host              $host;
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $proto;
# 重要: 外部から来た X-Authenticated-User は必ず剥がす（なりすまし防止）。
# TRUST_PROXY_HEADERS=true にする場合のみ、ここで剥がした上でプロキシが再付与する。
proxy_set_header X-Authenticated-User "";
```

---

## 3. アプリの起動（systemd 例）

`127.0.0.1` バインドで常駐させる。`.env` はプロジェクトルートから読まれる。

```ini
# /etc/systemd/system/nest-field-ui.service
[Unit]
Description=nest-support field-ui
After=network.target

[Service]
WorkingDirectory=/opt/nest-support
Environment=PORT=8001
ExecStart=/usr/bin/uv run python field-ui/server.py
Restart=on-failure
User=nest

[Install]
WantedBy=multi-user.target
```

sos も同様に `PORT=8000` で別ユニットにする。

```bash
sudo systemctl enable --now nest-field-ui nest-sos
```

---

## 4. 運用前の最終チェック

- [ ] `.env` に `APP_ACCESS_TOKEN`（長い乱数）を設定した
- [ ] `SESSION_COOKIE_SECURE=true` / `BIND_HOST=127.0.0.1` / `TRUST_PROXY_HEADERS=false`
- [ ] プロキシで TLS 終端・HTTP→HTTPS リダイレクトが効く
- [ ] `/api/login` と `/api/sos` にレート制限が効く
- [ ] 外部からの `X-Authenticated-User` をプロキシが剥がしている
- [ ] `./scripts/doctor.sh` が All PASS（Neo4j 疎通・Skills・MCP）
- [ ] 認証フローの手動確認（未認証 401 →ログイン→ 200）を本番ドメインで実施
- [ ] SOS 送信が無認証で通り、応答に実名が含まれないことを確認
- [ ] Neo4j のバックアップ（`scripts/backup.sh`）を cron 等に登録した
