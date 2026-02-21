# Manifesto: Post-Parent Support & Advocacy Graph
# 親亡き後・親ある内の権利擁護支援マニフェスト

**Version:** 4.0 (Unified Claude Agent Edition)
**Last Updated:** 2026-02-06
**Previous:** v3.0 (2025-12-08)

---

## 0. 理念 (Philosophy)

我々が構築するのは、単なる「障害者情報データベース」ではない。
親たちが長い時間をかけて蓄積してきた**「我が子を守るための暗黙知（Wisdom）」**と**「愛（Care）」**を、親亡き後も機能する**「社会的なシステム」**へと継承するためのデジタル・アーカイブである。
また、クライアントは、尊厳のある個人であって、自らのことは自らが決める権利を有している（もちろん社会性の制約はある）ことを支援に関わる者たちは決して忘れてはならない。

このシステムは**Claude AI**を中核エージェントとし、5つのSkillsと汎用Neo4j MCPを通じてNeo4jグラフデータベースに蓄積された知識を運用する。

---

## 1. 5つの価値 (The 5 Values)

| # | 価値 | 英語 | 定義 |
|---|------|------|------|
| 1 | **尊厳** | Dignity | 管理対象としてではなく、歴史と意思を持つ一人の人間として記録する |
| 2 | **安全** | Safety | 緊急時に「誰が」「何を」すべきか、迷わせない構造を作る |
| 3 | **継続性** | Continuity | 支援者が入れ替わっても、ケアの質と文脈を断絶させない |
| 4 | **強靭性** | Resilience | 親が倒れた際、その機能を即座に代替できるバックアップ体制を可視化する |
| 5 | **権利擁護** | Advocacy | 本人の声なき声を拾い上げ、法的な後ろ盾と紐づける |

---

## 2. データモデルの7本柱 (The 7 Data Pillars)

v4.0では、5つのSkills（neo4j-support-db / livelihood-support / provider-search / emergency-protocol / ecomap-generator）が扱う領域を統一的に整理する。

### 第1の柱：本人性 (Identity & Narrative)
「その人は誰か」を定義する。属性だけでなく、人生の物語を含む。

- **主要ノード:** `:Client`, `:LifeHistory`, `:Wish`
- **マニフェスト価値:** 尊厳 (Dignity)

### 第2の柱：ケアの暗黙知 (Care Instructions)
「どう接すべきか」を定義する。親の頭の中にあったマニュアルを形式知化する。

- **主要ノード:** `:CarePreference`, `:NgAction`, `:Condition`
- **サブカテゴリ:**
  - `EffectiveApproach` - 効果的だった関わり方
  - `NgApproach` - 避けるべき関わり方（二次被害防止）
- **マニフェスト価値:** 安全 (Safety), 継続性 (Continuity)

### 第3の柱：危機管理ネットワーク (Safety Net)
「誰が守るか」を定義する。緊急時の指揮命令系統と法的権限。

- **主要ノード:** `:KeyPerson`, `:Guardian`, `:Hospital`
- **マニフェスト価値:** 安全 (Safety)

### 第4の柱：法的基盤 (Legal Basis)
「何の権利があるか」を定義する。支援を受けるための資格と行政の決定。

- **主要ノード:** `:Certificate`, `:PublicAssistance`, `:Organization`
- **マニフェスト価値:** 権利擁護 (Advocacy)

### 第5の柱：親の機能と移行 (Parental Transition)
「親が担っている機能は何か」を定義し、その移転先を管理する。

- **主要ノード:** `:Relative`, `:CareRole`, `:Service`, `:Supporter`
- **リレーション:**
  - `(:Relative)-[:PERFORMS]->(:CareRole)` 親がその役割を担っている
  - `(:CareRole)-[:CAN_BE_PERFORMED_BY]->(:Service)` 代替サービスがある
  - `(:CareRole)-[:CAN_BE_PERFORMED_BY]->(:Supporter)` 代替人物がいる
- **マニフェスト価値:** 強靭性 (Resilience)

### 第6の柱：金銭的安全 (Financial Safety)
「経済的搾取から守る」を定義する。金銭管理能力と搾取リスクを記録。

- **主要ノード:** `MoneyManagement`, `EconomicRisk`
- **マニフェスト価値:** 権利擁護 (Advocacy), 安全 (Safety)
- **スキル:** livelihood-support（port 7688）

### 第7の柱：多機関連携 (Multi-Agency Collaboration)
「社会全体で支える」を定義する。連携支援機関と協働履歴。

- **主要ノード:** `SupportOrganization`, `CollaborationRecord`
- **マニフェスト価値:** 継続性 (Continuity), 強靭性 (Resilience)
- **スキル:** livelihood-support（port 7688）

---

## 3. AI運用プロトコル (AI Operational Protocol)

### ルール1：安全第一 (Safety First)
ユーザーから「パニック」「事故」「急病」を示唆する入力があった場合、AIは直ちに以下の情報を最優先で検索・提示しなければならない。

1. **禁忌事項 (NgAction / NgApproach)** - 二次被害を防ぐため
2. **経済的リスク (EconomicRisk)** - 搾取からの保護
3. **具体的対処 (CarePreference / EffectiveApproach)** - その場を落ち着かせるため
4. **緊急連絡先 (KeyPerson)** - ランク1位の人物
5. **医療機関 (Hospital)** - かかりつけ医

→ 詳細: `protocols/emergency.md`

### ルール2：親の機能不全トリガー (Parent Down Trigger)
「母が入院した」「父が認知症になった」という入力があった場合、AIは直ちに以下を実行すること。

1. その親 (:Relative) が担っていたタスク (:CareRole) を特定する
2. そのタスクに紐づく代替手段 (:Service, :Supporter) を提示する
3. 代替手段が未登録の場合は、「緊急の支援調整が必要です」と警告する

→ 詳細: `protocols/parent_down.md`

### ルール3：文脈の尊重 (Context Awareness)
新しい支援先を探す際、単に「空きがある施設」を探すのではなく、本人の `:LifeHistory`（過去の成功体験・失敗体験）と `:Condition` に適合するかを照合すること。

### ルール4：ケース記録の品質管理
支援記録の中に指導的・支配的な表現（「指導した」「約束させた」等）が含まれる場合、より適切な表現への変換を提案すること。

→ 詳細: `livelihood-support` スキルのCypherテンプレートを参照し、ケース記録内の表現を確認する

---

## 4. Skills & Neo4j MCP 構成

このシステムは5つのSkillsと2つの汎用Neo4j MCPで構成される。

| スキル | 対象業務 | 柱の対応 | Neo4j ポート |
|--------|----------|---------|-------------|
| **neo4j-support-db** | 計画相談支援（障害福祉サービス） | 第1〜5の柱 | 7687 |
| **livelihood-support** | 生活困窮者自立支援 | 第1〜7の柱（第6・7を追加） | 7688 |
| **provider-search** | 事業所検索・口コミ管理 | 第4の柱（法的基盤） | 7687 |
| **emergency-protocol** | 緊急時対応プロトコル | 第2の柱（ケアの暗黙知） | — |
| **ecomap-generator** | 支援ネットワーク可視化 | 第3の柱（危機管理） | — |

**Neo4j MCP:**
- `neo4j`（port 7687）: neo4j-support-db, provider-search スキル用
- `neo4j-livelihood`（port 7688）: livelihood-support スキル用

→ 詳細: `ROUTING.md`

---

## 5. プロトコルとワークフロー

### プロトコル（判断と行動のルール）
| ファイル | 内容 | トリガー |
|---------|------|---------|
| `protocols/emergency.md` | 緊急時対応 | パニック、事故、急病、SOS |
| `protocols/parent_down.md` | 親の機能不全 | 親の入院、死亡、認知症 |
| `protocols/onboarding.md` | 新規クライアント登録 | 新規相談、初回面接 |
| `protocols/handover.md` | 担当者引き継ぎ | 異動、退職、担当変更 |

### ワークフロー（業務手順の定型化）
| ファイル | 内容 | 使用場面 |
|---------|------|---------|
| `workflows/visit_preparation.md` | 訪問前ブリーフィング | 訪問・同行支援の前日〜当日 |
| `workflows/resilience_report.md` | レジリエンス・レポート | 支援計画の策定・見直し |
| `workflows/renewal_check.md` | 更新期限チェック | 月次業務、期限管理 |

---

## 6. v3.0からの変更点

1. **エージェント構成の転換:** Agno/Geminiベースの独立Pythonエージェントを廃止し、Claude + MCPツールを中核に据えた
2. **データモデルの統一:** support-dbの4本柱とlivelihood-support-dbの7本柱をマニフェストレベルで統合（7本柱）
3. **第6の柱（金銭的安全）を追加:** 経済的搾取リスクの管理を正式にマニフェストの柱とした
4. **第7の柱（多機関連携）を追加:** 社会全体で支える仕組みを可視化する領域を追加
5. **プロトコル・ワークフローの外出し:** エージェントのinstructions配列に埋め込まれていた行動ルールを、独立したMarkdownドキュメントに分離
6. **Parent Down Triggerの具体化:** reasoning.logで繰り返し発生していた「親の入院」シナリオを、MCPツール呼び出しシーケンスとして定式化
