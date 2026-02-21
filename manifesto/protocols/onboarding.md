# 新規クライアント登録プロトコル (Onboarding Protocol)

**マニフェスト価値:** 尊厳 (Dignity), 継続性 (Continuity)
**優先度:** 通常

---

## トリガー条件

- 新規相談の受付
- 初回面接、インテーク
- 「新しい利用者さんを登録したい」

---

## 実行手順

### ステップ1：既存登録の確認

まず、既に登録済みでないか確認する。

→ `neo4j-support-db` スキルのテンプレート1（クライアント一覧）を `neo4j` MCP の `read_neo4j_cypher` で実行。

名前の類似（漢字違い、旧姓等）にも注意する。

### ステップ2：7本柱に沿った情報収集

マニフェストの7本柱に沿って、段階的に情報を収集する。全ての情報が初回で揃う必要はない。優先度の高い柱から登録する。

#### 優先度：最高 - 初回に必ず確認

**第1の柱：本人性 (Identity & Narrative)**
- 氏名、生年月日、血液型
- 生育歴のキーエピソード
- 本人・家族の願い

**第2の柱：ケアの暗黙知 (Care Instructions)**
- 禁忌事項（NgAction） ← 最重要。安全に直結
- 配慮事項（CarePreference）
- 特性・診断名（Condition）

**第3の柱：危機管理ネットワーク (Safety Net)**
- キーパーソン（優先順位付き）
- かかりつけ医

#### 優先度：高 - 初回または2回目の面接

**第4の柱：法的基盤 (Legal Basis)**
- 手帳の種類と等級、更新日
- 受給者証の情報
- 後見人の有無

**第5の柱：親の機能と移行 (Parental Transition)**
- 親（主たる介護者）の基本情報と健康状態
- 親が担っているタスク（CareRole）の洗い出し
- 各タスクの代替手段の確認

#### 優先度：通常 - 支援開始後に順次

**第6の柱：金銭的安全 (Financial Safety)** ※livelihood-supportスキル
- 金銭管理の状況
- 経済的リスクの有無

**第7の柱：多機関連携 (Multi-Agency Collaboration)** ※livelihood-supportスキル
- 連携している支援機関の情報

### ステップ3：データ登録

収集した情報をSkillのCypherテンプレートを参考に、`neo4j` MCP の `write_neo4j_cypher` で登録する。

**基本情報（port 7687）:**
```cypher
MERGE (c:Client {name: '氏名'})
SET c.dob = date('YYYY-MM-DD'),
    c.bloodType = '血液型',
    c.gender = '性別'
RETURN c
```

**禁忌事項の登録:**
```cypher
MATCH (c:Client {name: '氏名'})
MERGE (ng:NgAction {action: '具体的な禁忌行動'})
SET ng.reason = '理由', ng.riskLevel = 'リスクレベル'
MERGE (c)-[:MUST_AVOID]->(ng)
```

**キーパーソンの登録:**
```cypher
MATCH (c:Client {name: '氏名'})
MERGE (kp:KeyPerson {name: '連絡先氏名'})
SET kp.phone = '電話番号', kp.relationship = '続柄', kp.role = '役割'
MERGE (c)-[:HAS_KEY_PERSON {rank: 1}]->(kp)
```

→ 上記は `neo4j` MCP の `write_neo4j_cypher` で実行する。

**livelihood-supportスキル固有の情報（port 7688）:**
以下の情報は `livelihood-support` スキルのCypherテンプレートを参考に、`neo4j-livelihood` MCP の `write_neo4j_cypher` で登録する。
- NgApproach（避けるべき関わり方）→ テンプレート5
- EffectiveApproach（効果的な関わり方）→ テンプレート6
- EconomicRisk（経済的リスク）→ テンプレート7
- MoneyManagement（金銭管理状況）→ テンプレート8
- SupportOrg（連携支援機関）→ テンプレート11

### ステップ4：登録内容の確認

登録した内容を確認する。

→ `neo4j-support-db` スキルのテンプレート2（クライアントプロフィール）を `neo4j` MCP の `read_neo4j_cypher` で実行。

不足している情報を一覧で提示し、次回の面接で確認すべき項目をリストアップする。

### ステップ5：初期ケアプランの提案

登録された情報に基づき、以下を提案する。

- 緊急時の対応フロー
- 推奨される福祉サービス
- 親のCareRoleのバックアップ体制（第5の柱）

---

## 情報収集のコツ：ナラティブからの抽出

親や支援者の語りから、構造化データを自動抽出する。

**例：親からの聞き取り**
```
入力: 「息子は大きな音が苦手で、パニックになると自分の頭を叩きます。
その時は静かな部屋で背中をさすると落ち着きます。
現在は私が全ての食事を作っていますが、来月から入院の予定があります。」

→ 抽出されるデータ:
- NgAction: 大きな音を出す → パニック・自傷行為
- CarePreference: パニック時は静かな部屋で背中をさする
- CareRole: 食事準備（母が担当）
- 緊急フラグ: 母の入院予定あり → Parent Down Trigger の事前準備
```

支援記録の登録には `neo4j-support-db` スキルのテンプレート（支援記録登録）を参考に、`neo4j` MCP の `write_neo4j_cypher` で登録し、AIによる自動抽出を活用する。

---

## チェックリスト：最低限の登録確認

初回登録完了時に以下が登録されていることを確認する：

- [ ] 氏名・生年月日
- [ ] 禁忌事項（NgAction）が1件以上
- [ ] キーパーソンが1名以上（rank 1）
- [ ] かかりつけ医
- [ ] 主たる介護者（親）の情報
- [ ] 手帳・受給者証の種類と更新日
