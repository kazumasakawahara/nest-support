# Claude Code 指示文書: nest-support セマンティックモデル（意味・ルール層の正本化）

作成日: 2026-07-12
対象リポジトリ: ~/Dev-Work/project/nest-support（Claude Code はここで起動）
関連正典: ~/Dev-Work/shared-schema/SCHEMA_CONVENTION.md（v3.2・命名と構造の正典）

【型の参照】この作業は ~/Obsidian/my-assistant/playbooks/セマンティックモデル拡張の型.md
に従う（4フェーズ・承認ゲート・provisional・訂正注記・完全新規チャットでの検収）。
本文書は nest-support 固有の論点のみ定める。フェーズ1冒頭で必ずプレイブックを読むこと。

【位置づけ】SCHEMA_CONVENTION.md は「構造と命名」の正典として既に完成している。
本作業はそれを置き換えるものではなく、その上の層──「意味とルール」
（概念の定義・運用原則・指標の計算意図・暫定事項）──の正本を作る。
2つの正典の分界を曖昧にしないことが品質の要。

【PII 鉄則（最優先）】support-db は実在クライアントの禁忌・感情・障害情報を含む。
- 全フェーズを通じ、チャット・報告・正本ファイルに実データ（実名・実際の
  禁忌内容・感情記録等）を一切出さない。pii-safe-data-handling スキル準拠
- 調査はスキーマレベル（ラベル・型・件数）に限定。例示はすべて架空の合成例
- 実データの中身を読む必要が生じたら、作業を止めて河原氏に判断を仰ぐ

---

## フェーズ1: 調査と設計提案（ファイル変更禁止）

貼り付け用プロンプト:

```
【タスク】nest-support 意味・ルール層の正本化の準備調査

まず ~/Obsidian/my-assistant/playbooks/セマンティックモデル拡張の型.md と
docs/semantic-model-instruction.md（本文書。特に PII 鉄則）を読んでください。
このフェーズでは調査と提案のみ行います。実データには触れないこと。

1. 読むもの:
   - ~/Dev-Work/shared-schema/SCHEMA_CONVENTION.md（全文。何が既に
     正典化済みかの確定が最初の仕事）
   - lib/schema_validator.py（Guardian が実際に強制しているルールの棚卸し）
   - lib/insight_engine.py（Oracle の指標定義: 感情トレンド・リスク予兆・
     ケアパターンの計算式）
   - claude-skills/ 配下 13 スキルの SKILL.md（各 Cypher テンプレートが
     「何の問いに答えるか」）
   - docs/PRIVACY_GUIDELINES.md・CLAUDE.md・manifesto/（5つの価値の典拠）
   - GET /api/narrative/schema の返す実行時 allowlist（取得可能なら）
2. 【分界の確定】SCHEMA_CONVENTION が既にカバーしている事項の一覧と、
   カバーしていない「意味・ルール」事項の一覧を対で提示すること。
   重複記載は正本の二重化なので絶対に避ける。迷う項目は理由付きで
   どちらに属すべきか提案する
3. 意味・ルール層の候補を4分類で洗い出す:
   - entities: 主要ラベルの業務的意味（Client・NgAction・CarePreference・
     KeyPerson・SupportLog 等。「非プログラマの支援者が読める日本語」で。
     命名や型は SCHEMA_CONVENTION 参照とし再掲しない）
   - metrics: Oracle 層の指標（感情トレンド・リスク予兆・類似度）と
     13 スキルの定型クエリの定義・意図・限界
   - business_rules: 運用原則。特に「緊急時は NgAction 最優先」の
     優先順位規則、Guardian の自動修正（camelCase 変換・廃止リレーション
     修正）の範囲と限界、セマンティック検索（embedding）の結果を
     どこまで信頼してよいか（類似≠事実。禁忌の確認は必ず構造側を正とする、
     等の使い分けルール）、5つの価値との紐付け
   - enums: 列挙値の意味（Guardian が検証している値の日本語定義）
4. 【形式の提案】正本の置き場所と形式を理由付きで提案する。選択肢:
   (a) shared-schema/ に SEMANTIC_MODEL.md を新設し既存の sync-schema.sh
       体制に乗せる（3プロジェクト同期・編集はマスターのみ）
   (b) グラフ内 _Meta ノード方式（Claude が 1 クエリで取得可能・
       schema_validator との整合チェックが書きやすい）
   (c) 両方（文書=人間向け正本、_Meta=機械向け写し。同期スクリプトで一致保証）
   推奨案と、ドリフト検知（文書 vs schema_validator.py vs
   /api/narrative/schema の三者一致チェック）の実現方法を含めること
5. ID 体系は既存正典の節番号と衝突しない案を提案（例: BRS- 接頭辞）。
   暫定事項は provisional 方式。

「分界一覧」「4分類の候補」「形式の提案」をまとめて報告し、承認を
待ってください。報告内の例示はすべて架空の合成例とすること。
```

▶ 河原の確認ポイント:
  - 分界一覧に納得できるか（SCHEMA_CONVENTION との二重化がないか）
  - 「embedding の類似結果は参考、禁忌の確認は構造が正」という使い分けが
    支援哲学（安全・尊厳）と整合するか──ここは河原氏にしか判断できない
  - Guardian の自動修正の範囲が「善意の変換」に留まっているか
    （意味を変える自動修正が紛れていないか）

## フェーズ2: 正本の作成

フェーズ1で承認した形式・分界で作成。チェック機構（三者一致）も同時に作る。
コミットせず全文提示で止める。sync-schema.sh 体制に乗せる場合はマスター側
（shared-schema）に書き、同期の実行はフェーズ4で。

## フェーズ3（必要時のみ）: 矛盾の解消

フェーズ1〜2で validator・スキル・文書間の矛盾が見つかった場合のみ。
日付入り訂正注記の前例に従う。support-db は本番実データを持つため、
スキーマ変更を伴う修正は必ず影響範囲の報告→河原氏承認→バックアップ
確認（neo4j_backup/）→適用の順とする。

## フェーズ4: 記録・コミット・同期・検収

- nest-support 側と shared-schema 側それぞれで git commit
  （shared-schema がリポジトリでない場合はその旨報告し扱いを提案）
- sync-schema.sh で 3 プロジェクトへ同期（対象に oyagami-local・
  neo4j-agno-agent が含まれることを確認）
- 本指示文書もコミットに含める（作業記録の前例）
- 検収は完全新規チャットで。質問例には必ず以下を含める:
  「クライアントの禁忌事項をセマンティック検索で調べてもいい？」
  （→ 構造側が正・embedding は参考、と答え分けられるか）

---

## フェーズ1完了記録（決定事項をここに追記して固定する）

実施日: 2026-07-12（調査・報告・承認まで同日）

### 河原氏決定（2026-07-12）

1. **Guardian 自動修正の範囲**: `RISK_LEVEL_ALIASES` の段階表現→リスク類型変換
   （高→LifeThreatening / 中→Panic / 低→Discomfort）は**現状維持**とし、
   正本に「意図的な安全側翻訳」であることを明記する（→ BRS-05）。
2. **緊急時の情報提示順の正**: emergency.md 版（禁忌→推奨ケア→緊急連絡先
   (rank順)→かかりつけ医→法的代理人）を正とする（→ BRS-01）。
   MANIFESTO.md ルール1（EconomicRisk 入りの順序）は訂正対象（フェーズ3候補）。
3. **BRS-03（embedding は参考・禁忌の確認は構造が正）**の定式化を承認。
4. **形式は (a)**: shared-schema に SEMANTIC_MODEL.md を新設し sync-schema.sh
   体制に乗せる。未実装の第6・7柱ノード（MoneyManagement / EconomicRisk /
   SupportOrganization / CollaborationRecord）は provisional として entities に
   載せる。_Meta ノード方式（b/c）は provisional の将来検討事項に留める。
5. **manifesto 内の氏名入りシナリオ（reasoning.log パターン節）は合成例**と確認。

### 確定した設計

- ID 体系: `ENT-` / `MET-` / `BRS-` / `ENU-` ＋2桁連番（CONVENTION の§番号と不衝突）
- 機械検証: 正本内の JSON コードブロック（PyYAML 非依存・標準ライブラリのみ）を
  `scripts/check_semantic_drift.py` が lib/schema_validator.py・
  GET /api/narrative/schema（停止時は agno ソースを AST 解析）と三者突合する
- 分界: 命名・型・値一覧・インデックス・重複防止の動作仕様は SCHEMA_CONVENTION の
  管轄のまま。意味・ルール層は業務的意味／運用原則／指標の意図と限界／列挙値の
  日本語定義のみを持ち、再掲しない

### フェーズ1で発見した既知ドリフト（フェーズ3候補・未修正）

正本 SEMANTIC_MODEL.md「既知ドリフト」節に一覧を固定（提示順の二重定義、
manifesto の旧スキーマ残存、effectiveness 'Excellent' 参照、data-quality-agent の
Unknown 欠落、schema_validator の effectiveness への High/Medium/Low 混入と
priority 検証欠如、Certificate MERGE キー不一致、agno 実行時 allowlist の
v3.1/v3.2 未追従、呼称揺れ等）。
