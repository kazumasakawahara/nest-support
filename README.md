# nest-support

**親なき後の支援の情報を、本人の尊厳と安全のために残すデータベース**

知的障害・精神障害のある方の支援の情報（禁忌・推奨ケア・支える人・関わる機関・支援の記録）を Neo4j に蓄え、Claude Desktop / Claude Code とスキルで読み書きの案を作ります。親が長年かけて蓄えてきた「我が子を守るための暗黙知」を、親なき後も働く形で引き継ぐためのものです。

> **2026-11 の作り直し（ADR-001）について**：この README は、作り直しの枝（`redesign/adr-001`）の状態を書いています。前の構成（共有の DB、埋め込みによる意味検索、Gemini による構造化、口コミ）はやめました。経緯は `docs/adr/ADR-001-redesign-and-shared-contract.md`、作業の計画は `docs/implementation-plan.md`。

---

## 特徴

- **読むのは包みだけ、書くのはゲートだけ**：Claude は読み取りだけの MCP（`nest-personal`・`nest-resource`）で DB を読みます。書き込みはゲート（`nest/gate/`）だけが行い、すべてに操作の記録が付きます
- **名前を Claude に渡さない**：本人は仮名（`displayCode`。`C-` と 6 字）で呼びます。包みは実名・かな・電話・住所・生年月日を返しません
- **根拠のある記録**：禁忌・推奨ケアなどの事実は、聞いた記録（`Record`。原文からの引用と確度）に結びます。AI が作った案は「未確定」で入り、職員が一つずつ承認します
- **「無い」と「聞いていない」を分ける**：「無い」と確かめたことは確認の記録（`Review`）として職員が残します
- **Safety First**：緊急時は禁忌を最初に出します
- **外に送らない**：外の送り先は `docs/external-api.md` の一覧だけで、既定は送りません。支援の情報を埋め込み（ベクトル）にしません

## 5つの価値 (The 5 Values)

| 価値 | 英語 | 定義 |
|------|------|------|
| **尊厳** | Dignity | 管理対象ではなく、歴史と意思を持つ一人の人間として記録する |
| **安全** | Safety | 緊急時に「誰が」「何を」すべきか、迷わせない構造を作る |
| **継続性** | Continuity | 支援者が入れ替わっても、ケアの質と文脈を断絶させない |
| **強靭性** | Resilience | 親が倒れた際、その機能を即座に代替できるバックアップ体制を可視化する |
| **権利擁護** | Advocacy | 本人の声なき声を拾い上げ、法的な後ろ盾と紐づける |

## 構成

```
職員 → Claude Desktop / Claude Code → スキル（SKILL.md の照会）
            │ 読む                                  │ 書き込みの案（JSON）
            ▼                                       ▼
  MCP nest-personal ─→ 個人の側の Neo4j ←── ゲート（nest/gate/。職員が通す）
  MCP nest-resource ─→ 資源の側の Neo4j（事業所などの公開情報。tsunagu-net の写し。読むだけ）
```

- DB は二つとも使う人の Mac の Docker で動き、`127.0.0.1` だけで待ち受けます
- 正典（ノード・リレーション・項目）は `docs/SCHEMA.md`、意味と表示名は `docs/SEMANTICS.md`

## はじめかた

`docs/QUICK_START.md`（手順の要点）と `docs/SETUP_GUIDE.md`（詳しい手順）を読んでください。

```bash
git clone https://github.com/kazumasakawahara/nest-support.git
cd nest-support
uv sync
uv run pytest -q                       # DB を使わない試験
uv run python scripts/check_drift.py   # 正典の表と JSON のずれ
./scripts/doctor.sh                    # 環境の点検（前の DB が動いていない・待ち受け・設定・リンク）
```

## スキル

| スキル | 何をするか |
|---|---|
| `neo4j-support-db` | 本人ごとの禁忌・推奨ケア・支える人・関わり・手帳・支援記録・確認の状況を読む（照会 15 本） |
| `emergency-protocol` | 緊急時に禁忌 → 推奨ケア → 支える人 → 医療 → 後見の順で出す |
| `visit-prep` | 訪問の前の準備 |
| `narrative-extractor` | 語り・面談の記録から書き込みの案（JSON）を作る。DB には書かない |
| `onboarding-wizard` | 初回面接で 7 本の柱に沿って聞き取りを案内する |
| `resilience-checker` | 親が担っている役割の代わりを見る |
| `data-quality-agent` | 欠け・食い違い・期限の点検 |
| `insight-agent` | 支援記録の推移から予兆を見る（数字を出し、判断は職員） |
| `ecomap-generator` | 支援のネットワークの図（Mermaid） |
| `provider-search` | 事業所の公開情報を資源の側から探す |
| `inheritance-calculator` | 法定相続の計算（DB に触れない） |
| `html-to-pdf` | HTML を PDF にする（DB に触れない） |

読み取りのスキルは読むだけで、本人は仮名で呼びます。

## 外した前の構成

現場の画面 `field-ui/` と SOS の通知 `sos/` は、新しい DB を読みの包みとゲートを通して使う形に作り直しました（計画 N-36・N-37）。
前の構成の `lib/`・`setup.sh`・`setup.ps1`・`installer/`・`scripts/rotate_password.py`・`scripts/multi_importer.py` は外しました（N-38）。無いことを試験で固定しています（`tests/test_old_db_code_isolated.py`）。

## 文書

| 文書 | 内容 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Claude 向けの指示（スキルの使い分け、決まり） |
| [docs/QUICK_START.md](docs/QUICK_START.md) | 手順の要点 |
| [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) | 詳しい手順 |
| [docs/SCHEMA.md](docs/SCHEMA.md) | 正典（ノード・リレーション・項目） |
| [docs/SEMANTICS.md](docs/SEMANTICS.md) | 意味・表示名・記録の決まり |
| [docs/external-api.md](docs/external-api.md) | 外に何を送るか |
| [docs/PRIVACY_GUIDELINES.md](docs/PRIVACY_GUIDELINES.md) | プライバシーガイドライン |
| [docs/VOICE_RECORDING_GUIDE.md](docs/VOICE_RECORDING_GUIDE.md) | 声の記録のガイド |
| [manifesto/MANIFESTO.md](manifesto/MANIFESTO.md) | マニフェスト（5 Values + 7 Pillars） |

## 開発背景

このシステムは、知的障害のある方の家族を支援する NPO と協働する弁護士によって開発されました。主介護者が不在になった緊急時に、支援スタッフが重要なケア情報に即座にアクセスできることを最優先に設計されています。

開発と試験は架空の事例だけで行います。実際の利用者のデータをリポジトリに入れません。

## ライセンス

MIT License
