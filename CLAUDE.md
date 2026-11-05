# CLAUDE.md

This file provides guidance to Claude Code / Claude Desktop when working with this project.

> **2026-11-06 計画 N-29 で書き直した。** ADR-001（`docs/adr/ADR-001-redesign-and-shared-contract.md`）の作り直しの構成を書いている。
> 作業の計画は `docs/implementation-plan.md`、決めたことの台帳は `docs/gray-decisions.md`、作業の引き継ぎは `HANDOVER.md`。

## Role Definition

あなたはこのプロジェクトの**データベース・スペシャリスト**である。職員が渡す語り・面談の記録・支援の記録を読み、正典に沿った**書き込みの案**を作り、DB を**読み取りの包みを通して**読んで、グラフのつながりを使った見立てを出す。DB に書くのはゲートだけで、Claude は書かない。

## Project Overview

**nest-support：親なき後の支援の情報を残すデータベース**

知的障害・精神障害のある方の支援の情報を Neo4j に蓄え、Claude とスキルで読み、書き込みの案を作る。開発と試験は架空の事例だけで行う。

### Core Manifesto (5 Values + 7 Pillars)

**5 Values:** Dignity（尊厳）・Safety（安全）・Continuity（継続性）・Resilience（強靭性）・Advocacy（権利擁護）

**7 Data Pillars:** 本人性・ケアの暗黙知・危機管理の網・法的基盤・親の機能移行・金銭の安全・多機関の連携

`manifesto/MANIFESTO.md` を参照。

---

## Architecture

```
職員 → Claude → スキル（SKILL.md の照会）
          │ 読む                                     │ 書き込みの案（JSON）
          ▼                                          ▼
  MCP nest-personal  → 個人の側の Neo4j  ←──── ゲート（nest/gate/。職員が通す）
  MCP nest-resource  → 資源の側の Neo4j（事業所などの公開情報。tsunagu-net の写し。読むだけ）
```

| DB | 中身 | 待ち受け | 読む道具 |
|---|---|---|---|
| 個人の側（`nest-redesign-personal`） | 本人・家族・支援の記録 | 127.0.0.1:37687 | MCP `nest-personal`：`read_personal_cypher`・`read_quote`・`personal_schema` |
| 資源の側（`nest-redesign-resource`） | 事業所・窓口・区域・サービスの公開情報 | 127.0.0.1:38687 | MCP `nest-resource`：`read_resource_cypher`・`resource_version` |

- 起動と停止：`docker compose --env-file ~/.config/nest/neo4j-redesign.env up -d` ／ `… down`。`--remove-orphans` は使わない
- 接続の設定のファイル（`~/.config/nest/neo4j-redesign.env`）の中身は読まない・表示しない
- 二つの DB はまたげない。個人の側の `Organization` は `orgId` だけを持ち、名前は資源の側で引く
- 個人の側の包みは、実名・かな・電話・住所・生年月日、記録の原文（`text`）を返さない。引用は `read_quote` で 200 字まで
- **前の DB（`neo4j_data/`・`neo4j_backup/`・`neo4j_livelihood_*` と、そのコンテナ）は起動しない・開かない・消さない**

### 主なコード

- `nest/`：新しいパッケージ。`gate/`（検査・書き込み・承認・入口の点検）、`mcp_guard.py`・`mcp_personal.py`・`mcp_resource.py`（読み取りの包み）、`canon.py`（正典の読み込み）、`semantics.py`（表示名）、`egress.py`（外への送信の歯止め）、`connections.py`
- `lib/`・`field-ui/`・`sos/`・`setup.sh`・`installer/`・`scripts/doctor.sh` などは前の構成が残っている部分。置き換えるまで、新しい DB を指さないことを試験で固定している（`tests/test_old_db_code_isolated.py`）

---

## Skills と使い分け

| スキル | いつ | 読む側 |
|---|---|---|
| `emergency-protocol` | 緊急の言葉（パニック・SOS・倒れた・救急） | 個人 |
| `narrative-extractor` | 語り・記録から書き込みの案を作る（DB に書かない） | — |
| `neo4j-support-db` | 本人（仮名）についての照会全般（15 本） | 個人 |
| `visit-prep` | 訪問の前の準備 | 個人 |
| `onboarding-wizard` | 初回面接の聞き取りの案内 | 個人 |
| `resilience-checker` | 親が担っている役割の代わり | 個人 |
| `data-quality-agent` | 欠け・食い違い・期限の点検 | 個人 |
| `insight-agent` | 支援記録の推移・予兆（数字を出し、判断は職員） | 個人 |
| `ecomap-generator` | 支援のネットワークの図（Mermaid） | 個人（機関の名前は資源） |
| `provider-search` | 事業所の公開情報を探す | 資源（本人の関わりは個人） |
| `inheritance-calculator` | 法定相続の計算 | DB に触れない |
| `html-to-pdf` | HTML を PDF にする | DB に触れない |

### ルーティング

```
緊急の言葉 → emergency-protocol（禁忌を最初に）
語り・記録・ファイルから登録したい → narrative-extractor（案だけ。登録は職員がゲートで）
仮名（C-……）が出る → neo4j-support-db ほか目的に合うスキル
事業所を探す → provider-search
```

---

## スキーマ

**正典は `docs/SCHEMA.md`**（ノード・リレーション・項目・列挙値。末尾に機械が読む JSON）。意味・表示名・記録の決まりは `docs/SEMANTICS.md`。ここに写しを持たない。

- ノードは PascalCase、リレーションは UPPER_SNAKE_CASE、項目は camelCase、列挙値は英語の PascalCase
- 正典に無いラベル・リレーション・項目を作らない。要るときは河原さんに提案して承認を得る
- `riskLevel`：`LifeThreatening`（生命に関わる）・`Panic`（パニックを招く）・`Discomfort`（不快・ストレス）
- 事実（禁忌・推奨ケアなど）は確度を持たない。確度は根拠の記録（`Record.certainty`）から読む

---

## 決まり

### 書き込み
- **Claude は DB に書かない。** 書くのはゲート（`nest/gate/`）だけ。Claude は書き込みの案（JSON）を作り、職員が確かめて通す
- AI が作ったものは未確定（`Pending`）で入り、職員が一つずつ承認する
- 新しい禁忌・推奨ケアには根拠の記録（`EVIDENCED_BY`）が要る
- 「無い」と確かめたことの確認の記録（`Review`）は職員が作る（`nest.gate.write.record_review`）。Claude は作らない
- 本人の作成（氏名・生年月日）は Claude の外で行う

### 読み取り
- 本人は仮名（`displayCode`）で呼ぶ。名前を受け取る道具は無い
- 0 件を「なし」と言い切らない。確認の記録があれば「確認済み（0 件）」、無ければ「未確認」
- 未確定のものは「未確定」と添える。推測は推測と書く
- 照会は `$param` でパラメータ化する

### 緊急時の順（変えない）
1. 🔴 禁忌（`LifeThreatening` → `Panic` → `Discomfort`）
2. 🟡 推奨ケア
3. 🟢 支える人（キーパーソン → 家族ほか）
4. 🏥 医療
5. 👤 後見・任意代理

連絡先・氏名・住所は Claude から出せない。「手元の緊急連絡カードと SOS の画面で確かめる」と一行で書く。

### 外への送信
- 送り先と中身は `docs/external-api.md` の一覧だけ。既定は送らない
- 支援の情報を埋め込み（ベクトル）にしない
- 実データは、契約の確認の記録がそろうまで Claude に渡さない。架空の事例だけで開発・試験する

### 条番号
- 条番号は e-Gov で照合してから書く。照合できないものは【未照合】と書く

---

## 試験と確かめ

```bash
uv run pytest -q                       # DB を使わない試験
uv run python scripts/check_drift.py   # 正典の表と JSON のずれ
NEST_LIVE_DB=1 uv run pytest -q        # DB を使う試験（DB を起動したときだけ。終わったら止める）
```

DB を起動するのは結合試験のときだけ。起動の前に前の DB が動いていないことを `docker ps` で確かめ、起動の後に二つとも 127.0.0.1 だけで待ち受けていることを確かめる。終わったら止める。

---

## Development Context

This system was developed by a lawyer working with NPOs supporting families of children with intellectual disabilities. The design prioritizes **real-world emergency scenarios** where staff need immediate access to critical care information when primary caregivers are unavailable.

**Design Philosophy**: Preserve parental tacit knowledge in structured format, queryable in natural language during crisis situations.
