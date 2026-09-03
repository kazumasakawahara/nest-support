<!-- AUTO-GENERATED COPY — DO NOT EDIT.
  Synced from ~/Dev-Work/shared-schema/SEMANTIC_MODEL.md
  Edit the master there and run sync-schema.sh. (synced: 20260903-200832) -->

<!--
  ============================================================================
  これは唯一の正典（マスター）です。編集はこのファイル（shared-schema）でのみ行うこと。
  各プロジェクト配下のコピーは sync-schema.sh による read-only 同期物であり、
  直接編集してはなりません。
  ============================================================================
-->

# nest-support 意味・ルールモデル（SEMANTIC MODEL）— 正本 v1.8

> **このドキュメントは、support-db（障害福祉支援DB, port 7687）の「意味とルール」
> （概念の業務的定義・運用原則・指標の計算意図・列挙値の意味・暫定事項）の唯一の正本です。**
>
> **分界**: 命名規則・ノード/リレーション/プロパティの一覧・列挙値の「値の一覧」・
> インデックス・正規化/重複防止の動作仕様は `SCHEMA_CONVENTION.md`（構造と命名の正典）の
> 管轄であり、本書には再掲しません。本書が扱うのは「それが業務上何を意味し、
> どう運用すべきか」です。両正典で同じ事実を二重に記載してはなりません。
>
> **編集ルール**: 本ファイル（`~/Dev-Work/shared-schema/SEMANTIC_MODEL.md`）が唯一の
> 編集点です。各プロジェクト内のコピーは同期物なので編集しないこと。
> **機械検証**: 本書 §6 の JSON ブロックを `nest-support/scripts/check_semantic_drift.py`
> が `lib/schema_validator.py`（Guardian）および `GET /api/narrative/schema`
> （agno 実行時 allowlist。停止時はソース AST 解析）と三者突合します。

---

## 0. 読み方と凡例

- **ID 体系**: `ENT-`（entities: 概念の意味）/ `MET-`（metrics: 指標）/
  `BRS-`（business_rules: 運用原則）/ `ENU-`（enums: 列挙値の意味）＋2桁連番。
  SCHEMA_CONVENTION の節番号（§1〜§12）とは衝突しない。
- **source**: 各項目の典拠（SKILL.md・SCHEMA_CONVENTION §・コード・河原氏決定の日付）。
- **provisional**: 暫定事項に付す。見直しトリガーを必ず明記し、確定したら
  provisional を外して source に昇格させる。
- **values**: その項目が仕える価値（Dignity / Safety / Continuity / Resilience / Advocacy）。
- 対象読者は「非プログラマの支援者」を含む。entities と enums は平易な日本語を優先する。

---

## 1. 前提となる価値と柱

5つの価値と7つのデータの柱の完全な定義は `manifesto/MANIFESTO.md` が正。
本書では各項目に `values:` タグで紐付けのみ行う。

| 価値 | 一言定義 |
|---|---|
| Dignity（尊厳） | 管理対象ではなく、歴史と意思を持つ一人の人間として記録する |
| Safety（安全） | 緊急時に「誰が」「何を」すべきか、迷わせない構造を作る |
| Continuity（継続性） | 支援者が入れ替わっても、ケアの質と文脈を断絶させない |
| Resilience（強靭性） | 親が倒れた際、その機能を即座に代替できる体制を可視化する |
| Advocacy（権利擁護） | 本人の声なき声を拾い上げ、法的な後ろ盾と紐づける |

> **注意**: manifesto の第6柱（MoneyManagement / EconomicRisk）・第7柱
> （SupportOrganization / CollaborationRecord）のノードは**構想段階で未実装**
> （SCHEMA_CONVENTION にも実行時 allowlist にも存在しない）。→ ENT-23 provisional。

---

## 2. entities — 概念の業務的意味

命名・型・プロパティ一覧は SCHEMA_CONVENTION §3 を参照（再掲しない）。
ここでは「その記録が業務上何であり、なぜ大切か」を定める。

### 中心と本人性（第1柱）

- **ENT-01 Client（本人）** — このデータベースの中心。支援の「対象」ではなく、
  自らのことは自らが決める権利を持つ一人の人。すべての記録は本人につながる。
  `values: [Dignity]`
- **ENT-02 LifeHistory（生育歴）** — 本人の人生の物語。「なぜ今の本人があるのか」を
  新しい支援者が理解するための文脈。施設探し等では空き状況だけでなく、
  この物語と特性に適合するかを照合する（BRS-10）。 `values: [Dignity, Continuity]`
- **ENT-03 Wish（願い）** — 本人・家族が言葉にした希望。声なき声の記録であり、
  支援計画が本人不在にならないための錨。 `values: [Dignity, Advocacy]`
- **ENT-04 Identity（仮名化用個人情報）** — 将来の仮名化運用のための分離格納先。
  現状は構造のみ（SCHEMA_CONVENTION §3 の「将来」注記どおり）。 `values: [Dignity]`

### ケアの暗黙知（第2柱）

- **ENT-05 Condition（特性・診断）** — 本人の特性や医学的診断。禁忌や推奨ケアの
  「なぜ」を説明する文脈であり、レッテルではない。 `values: [Safety, Continuity]`
- **ENT-06 NgAction（禁忌事項）** — 本人に対して**絶対にしてはいけないこと**。
  親や前任者が経験から学んだ暗黙知を、緊急時に初対面の支援者でも読める形にしたもの。
  本データベースで最も安全に直結する記録。緊急時は他のどの情報よりも先に提示し
  （BRS-01）、仮名化の対象外（BRS-06）、重複登録は確認必須（SCHEMA_CONVENTION §10.4）。
  `values: [Safety, Continuity]`
- **ENT-07 CarePreference（推奨ケア）** — 「こう関わるとうまくいく」という
  親の頭の中のマニュアルの形式知化。禁忌（してはいけない）と対になる
  「したほうがよい」。仮名化の対象外。 `values: [Safety, Continuity]`

### 危機管理ネットワーク（第3柱）

- **ENT-08 KeyPerson（キーパーソン・緊急連絡先）** — 緊急時に「誰に」連絡するか。
  `rank` は連絡の優先順位で、rank 1 が最優先。順位が曖昧だと緊急時に迷いが生じる
  ため、rank の重複・欠損はデータ品質チェックの対象（MET-09 付随）。
  **「現在のキーパーソン」は HAS_KEY_PERSON が `status = Active` かつ `endDate IS NULL` の
  リレーションで定義する**（BRS-14。2026-09-03 Track A Phase 2）。rank は Active なものの
  間の順位。交代しても旧リレーションは消さない（endDate + Inactive を書いて履歴にする）。 `values: [Safety]`
- **ENT-09 Hospital（医療機関）** / **ENT-10 Doctor（かかりつけ医）** — 本人を
  診てきた医療機関と医師。Doctor は 2026-07 に Hospital の文字列プロパティから
  独立ノードへ昇格（名寄せ済み・複数病院で共有可）。 `values: [Safety]`
- **ENT-11 Guardian（成年後見人等）** — 法定代理権の所在。緊急時の意思決定や
  契約行為で「誰に法的権限があるか」を即答するための記録。 `values: [Safety, Advocacy]`

### 法的基盤（第4柱）

- **ENT-12 Certificate（手帳・受給者証）** — 本人の権利の証明書。**更新期限の管理が
  生命線**（期限切れ＝サービス停止に直結）。期限の緊急度判定は MET-06。
  `values: [Advocacy]`
- **ENT-13 PublicAssistance（公的扶助）** — 受給中の公的扶助。 `values: [Advocacy]`
- **ENT-14 Organization（関係機関）** — 本人が登録されている行政・相談機関。
  `values: [Advocacy, Continuity]`

### 親の機能移行（第5柱）

- **ENT-15 Relative（家族・主たる介護者）** — 親をはじめとする家族。本人を支える
  最大の存在であると同時に、「親なき後」に機能が失われる単一障害点でもある。
  `values: [Resilience]`
- **ENT-16 CareRole（親が担う機能）** — 親が日常的に担っているタスク
  （食事準備・服薬管理・金銭管理等）。「親が何をしているか」を可視化して初めて、
  倒れた時に何を代替すべきかが分かる。レジリエンス診断（MET-07）の単位。
  **登録時は本人・担当者配下スコープで作成すること**——全クライアント共通の
  同名ノードに統合すると、未カバーのタスクが「カバー済み」と誤診断される
  （resilience-checker SKILL.md の事故防止則）。 `values: [Resilience]`

### 支援の記録と説明責任

- **ENT-17 Supporter（支援者）** — 記録を作成する支援スタッフ。 `values: [Continuity]`
- **ENT-18 SupportLog（支援記録）** — 日々の観察と対応の記録。situation（何が
  あったか）・action（どう対応したか）・effectiveness（効いたか）に加え、
  emotion / triggerTag / context の感情メタデータを持ち、これが予兆検知
  （MET-01〜03）とケアパターン発見（MET-04）の原料になる。**記録は分析の副産物
  ではなく、支援の質を次の支援者に手渡すための資産**。 `values: [Continuity]`
- **ENT-19 MeetingRecord（音声面談記録）** — 面談音声の文字起こしと記録。
  `values: [Continuity, Dignity]`
- **ENT-20 AuditLog（監査ログ）** — 誰がいつ何を変更したかの記録。要配慮個人情報を
  扱うシステムとしての説明責任の基盤。全書き込みで必須（BRS-11）。 `values: [Advocacy]`
- **ENT-24 Review（確認記録）** — 「ある領域について、いつ、誰に確認したか」の記録。
  **このDBで唯一「無いことを確認した」を表現できる記録**である。
  禁忌0件には二つの意味がある——「確認したうえで無い」と「まだ聞き取れていない」。
  前者は安心してよく、後者は**最優先で埋めるべき欠損**であり、両者は現場での意味が
  正反対にもかかわらず、リレーションの不在としては区別がつかない。Review はこの
  区別を担う（BRS-04 / BRS-12）。
  `source` に**情報源**（母親・本人・主治医・前事業所等）を持つことが要点で、
  「母親に確認して禁忌なし」と「本人にしか聞けていない」は信頼度が異なる。
  加えて、**誰が情報源だったかという記録それ自体が、親なき後に引き継がれるべき
  資産**になる（親の死後、その情報が誰由来だったかは二度と辿れない）。
  追記のみで、更新・削除はしない（確認の履歴は積み上げる）。
  **2026-08-08 拡張（Track A）**: Review は `CONFIRMS` リレーションで**個々の事実**
  （NgAction / CarePreference）を指せるようになった。CONFIRMS を持たない Review は
  従来どおり「領域の0件確認」、持つ Review は「その事実の個別再確認」を意味する
  （BRS-13）。Review ノード自体の構造は不変。
  `source: 2026-07-12 河原氏決定` `values: [Safety, Continuity, Advocacy]`

### 多機関連携（第7柱の実装済み部分）

- **ENT-21 ServiceProvider（事業所）** / **ENT-22 ProviderFeedback(口コミ)** —
  地域の福祉サービス事業所と、支援者による利用実感の記録。代替手段検索
  （MET-07）と事業所選定（MET-08）に使う。 `values: [Resilience, Continuity]`

### 構想段階（未実装）

- **ENT-23 第6・7柱の構想ノード** — MoneyManagement / EconomicRisk（金銭的安全）、
  SupportOrganization / CollaborationRecord（多機関連携）。
  `provisional: manifesto v4.0 の構想であり、SCHEMA_CONVENTION・実行時 allowlist の
  いずれにも存在しない。実装する場合は SCHEMA_CONVENTION への追記（§11.2 の手順）が
  先行条件。見直しトリガー: 第6柱（金銭的安全）機能の実装着手時。`
  `values: [Safety, Advocacy]`

---

## 3. metrics — 指標の定義・意図・限界

Oracle 層（`lib/insight_engine.py`）と各スキル定型クエリの「計算の意図」と
「信頼してよい範囲」を定める。計算式のパラメータ既定値は §6 の機械検証ブロックが
コードとの一致を保証する。

- **MET-01 感情ドリフト（emotion drift）** — 過去30日をベースラインに、直近7日の
  「負の感情の比率」がきっかけタグ（triggerTag）ごとにどれだけ悪化したかを見る。
  増加率 0.3 以上で警告、0.5 以上で重大。ベースラインに存在しない**新規出現タグ**は、
  負の感情を伴えば比較なしで即アラート（新環境・新支援者などの初期兆候を
  見逃さないため）。
  **意図**: 「なんとなく最近調子が悪い」を、どの場面で悪化しているかまで特定する。
  **限界**: triggerTag の**完全一致**で集計するため、表記揺れ（「大きな音」と「騒音」）は
  別タグ扱いになる。記録件数が少ない期間は比率が暴れる。数値は**気づきのきっかけ**
  であり、診断ではない。
  `source: lib/insight_engine.py::detect_emotion_drift / insight-agent SKILL.md`
- **MET-02 負の連鎖（cascading risk）** — 直近3日間の負の感情が **2種類以上**の
  きっかけタグにまたがっているか。特定場面に限定されない不調は、生活全般の
  意欲低下や隠れた体調不良の予兆と解釈する。
  **限界**: 「場面の多様性」の代理指標にすぎず、原因は特定しない。
  `source: lib/insight_engine.py::detect_cascading_risk`
- **MET-03 スタッフ負荷（staff overload）** — 直近7日の記録のうち負の感情ログが
  50% 以上、かつ記録3件以上のスタッフを検出する。
  **意図**: 困難なケースが特定スタッフに偏っていないかへの気づき。
  **限界**: これはスタッフ本人の状態ではなく**担当ケースの困難さの代理指標**。
  人事評価・査定に使ってはならない。 `source: lib/insight_engine.py::detect_staff_overload`
- **MET-04 ケアパターン発見と昇格提案** — effectiveness = Effective の同一対応が
  2回以上で「効果的パターン」として発見、3回以上かつ CarePreference 未登録なら
  昇格候補として提案する。**昇格の実行は必ず人間の承認を経る**（自動登録しない）。
  `source: lib/insight_engine.py::discover_care_patterns / propose_care_promotions`
- **MET-05 総合リスク評価** — High = ドリフト重大＋連鎖あり（emergency-protocol を
  自動連動）、Medium = ドリフト重大 または 連鎖＋3件以上、Low = それ以下。
  **High の自動連動は「緊急対応手順の起動」であって外部への通報ではない。**
  `source: lib/insight_engine.py::generate_risk_assessment / CLAUDE.md ルーティング`
- **MET-06 更新期限の緊急度** — 🔴 30日以内=即時対応（今月中に更新手続き開始）/
  🟡 31〜60日=次回訪問時に書類準備 / 🟢 61〜90日=計画的対応。期限切れ（負の日数）は
  最優先で赤字警告。定期チェックは月次、探索窓は90日。
  **この定義がスキル間（neo4j-support-db / data-quality-agent / visit-prep /
  renewal_check.md）の唯一の正**とする——各所の日数基準はこの MET-06 に従う。
  `source: manifesto/workflows/renewal_check.md / 2026-07-12 正本化`
- **MET-07 レジリエンスカバー率** — 親が担う各 CareRole について
  ✅完全カバー（代替手段1つ以上）/ ⚠️部分カバー（頻度・質に不安）/ 🚨未カバー
  （代替なし）の3値で判定し、カバー率 = 完全カバー数 ÷ 全 CareRole 数。
  **限界**: 「部分カバー」の判定（頻度・質の十分性）は支援者の判断を要する
  主観的評価であり、機械判定は「代替手段の有無」まで。
  `source: resilience-checker SKILL.md / manifesto/workflows/resilience_report.md`
- **MET-08 事業所評価スコア** — 口コミ rating を ◎=4 / ○=3 / △=2 / ×=1 に換算した
  平均値。**限界**: 口コミ母数が小さいうちは参考値にとどめる（母数の明示を必須とする）。
  `source: provider-search SKILL.md`
- **MET-09 意味的一貫性チェック** — embedding 類似度 0.85 以上の禁忌ペアで
  riskLevel の段差を検査（1段差=要確認、2段差=重大不整合）。**自動修正はせず
  推奨提示のみ**（人間確認前提）。embedding の使い方として許容される範囲は BRS-03。
  `source: data-quality-agent SKILL.md Check8`

### 付録: 13スキルの定型クエリが答える問い（1行索引）

| スキル | 答える問い（代表） |
|---|---|
| neo4j-support-db | 登録充足状況 / 本人プロフィール一括 / DB統計 / 期限接近の手帳 / 直近支援記録 / 効果的ケア / 監査履歴 / 記録の全文検索・時系列 |
| emergency-protocol | 緊急時の安全情報一括（BRS-01 の順序で）/ 禁忌のみ最速 / 状況別絞り込み / 連絡先のみ |
| visit-prep | 訪問前に避けること・推奨ケア・申し送り・効果的な関わり・話すべき期限 |
| insight-agent | MET-01〜05 の各問い＋全クライアント一括スキャン |
| resilience-checker | 親が担うタスクと代替手段 / カバー状態 / 未カバーに対応できる地域事業所 |
| data-quality-agent | 期限切れ・欠損・陳腐化・構造欠損・廃止リレーション・不正列挙値・rank 整合・意味的一貫性 |
| provider-search | 条件に合う事業所 / 利用中・代替事業所 / 口コミと評価 |
| narrative-extractor | 語り・ファイルから何を構造化して登録すべきか |
| onboarding-wizard | 新規登録で何を聞き漏らしていないか（7本柱チェックリスト） |
| ecomap-generator | 支援ネットワークと状態の可視化（計算は insight_engine に委譲） |
| wamnet-provider-sync | 事業所マスタの差分（NEW/MODIFIED/CLOSED）と廃止事業所の利用者警告 |
| inheritance-calculator | 法定相続人・相続分（民法。グラフDB非依存・法的助言ではない旨の免責必須） |
| html-to-pdf | （ユーティリティ。業務の問いなし） |

---

## 4. business_rules — 運用原則

- **BRS-01 緊急時の情報提示順（変更禁止）** — ① 🚫 禁忌事項（NgAction、riskLevel 順）
  → ② ✅ 推奨ケア（CarePreference）→ ③ 📞 緊急連絡先（KeyPerson、rank 順）→
  ④ 🏥 かかりつけ医（Doctor / Hospital）→ ⑤ ⚖️ 法的代理人（Guardian）。
  禁忌を最初に置くのは**二次被害の防止**のため（対応を急ぐ前に「してはいけないこと」を
  知る）。この順序は emergency.md 版を正とする。
  `source: manifesto/protocols/emergency.md / 2026-07-12 河原氏決定`
  `values: [Safety]`
  ※ MANIFESTO.md ルール1の旧順序（経済的リスク入り）は訂正対象（DRIFT-01）。
- **BRS-02 riskLevel の提示順** — LifeThreatening → Panic → Discomfort の順に提示する
  （ENU-01 の重大度順）。 `source: emergency-protocol SKILL.md` `values: [Safety]`
- **BRS-03 embedding（セマンティック検索）の信頼ルール** — 類似は事実ではない。
  - セマンティック検索・類似度分析の結果は**発見の補助**（過去記録の探索、重複候補の
    検出、類似クライアントの参考）に限定する。
  - **禁忌・安全情報の確認は、必ず構造側を正とする**——「この人の禁忌は何か」に
    答えるのは `MUST_AVOID` リレーションの MATCH であって、embedding 検索ではない。
    セマンティック検索がヒットしなくても禁忌が無いことにはならず、ヒットしても
    それだけで禁忌とは扱わない。
  - 登録時の重複ブロック（類似度 0.85 での 409、SCHEMA_CONVENTION §10.4）は
    「登録を止めて人間に確認を求める」安全側の使い方なので許容される。
  - 判断を伴う提示（MET-09 等）は自動修正せず、人間の確認を前提とする。

  **embedding 生成時の外部API送信（許容範囲と禁則）**—— 2026-07-12 確定

  内部ベクトルインデックス（SCHEMA_CONVENTION §8.3 の6本）の生成に **Gemini Embedding 2
  （外部API）を使用することは許容する**。ただし以下を厳守する:

  - **氏名・生年月日は送信しない。** Client 概要の embedding では、実名ではなく
    非識別の `displayCode` / `clientId` を用いる。
  - 送信してよいのは**禁忌・ケア・支援記録の本文**（「禁忌: 大きな音。理由: …」等）であり、
    **個人識別子と紐づかない形**に限る。連絡先・住所等も送らない。
  - この制約の実装は `lib/embedding.py::build_client_summary_text` および
    `scripts/backfill_embeddings.py` の各 `_*_text()` 関数。
    **これらを変更する際は、氏名・生年月日を混入させていないか必ず確認すること**。

  **これは「別ストアへの複製禁止」とは別の論点である**—— support-db 内部のインデックスは
  本項が管轄し、LightRAG 等**外部ストアへの PII 複製は引き続き禁止**（CLAUDE.md §8 /
  neo4j-support-db ルール7）。

  **残存リスクの認識**: 氏名は出ないが、禁忌本文自体は外部APIに出ている。
  クライアント数が少ないうちは、特徴的な内容（例: 稀少なアレルギー）が他情報との
  突き合わせで再識別され得る。API 提供者側に突き合わせ材料がないため実務上の
  リスクは低いと判断しているが、**リスクゼロではないことを明示しておく**。
  `provisional: 見直しトリガー = クライアント数の大幅増加、ローカル embedding モデルへの
  移行が現実的になった時点、または外部APIの利用規約変更時`

  `source: 2026-07-12 河原氏決定（embedding の信頼ルール）/ 2026-07-12 河原氏決定
  （外部API送信の許容範囲——実装に既存していた設計判断を正典に明文化。実装側コメント
  「実名・生年月日は Gemini へ送らない」が根拠）` `values: [Safety, Dignity]`
- **BRS-04 No Fabrication の運用** — 原則は SCHEMA_CONVENTION §11.3。運用として:
  情報の欠損は「登録されていません」と明示し、補完・推測して埋めない。推測を
  述べる場合は推測である旨を必ず明記する。**禁忌0件の表示は「確認したうえで0件」
  なのか「まだ聞き取れていない」のかを区別する**（後者はデータ品質チェックで
  最優先の欠損として扱う）。**この区別の実装機構が Review（ENT-24）であり、
  判定と表示の規則は BRS-12 が定める。**
  `source: narrative-extractor / data-quality-agent SKILL.md`
  `values: [Dignity, Safety]`
- **BRS-05 Guardian 自動修正の範囲と限界** — Guardian Layer（`lib/schema_validator.py`）
  の自動修正は「意味を変えない変換」を原則とする: プロパティ名の camelCase 化、
  廃止リレーション名の正式名への置換。
  **意図的な例外**として、riskLevel の別名補正には段階表現の翻訳
  （高→LifeThreatening / 中→Panic / 低→Discomfort、英語 high/medium/low も同様）を
  含む。これは抽出 LLM が段階表現で出力した場合に**安全側の正規値へ寄せる**ための
  意図的な設計であり、対応表に無い値は補正せず警告する（安全に関わる値を推測で
  捏造しない）。 `source: lib/schema_validator.py::RISK_LEVEL_ALIASES /
  2026-07-12 河原氏決定（現状維持・意図の明文化）` `values: [Safety]`
- **BRS-06 仮名化の安全例外と適用範囲** — NgAction・CarePreference の内容、
  Certificate の種類・等級は**仮名化しない**（緊急時に正確に読める必要があるため。
  氏名は仮名化対象）。SOS 緊急通知は実名必須のため意図的に raw 経路を使う。
  仮名化が効くのは **Python 経路のみ**で、Claude → Neo4j MCP の中核読み取り経路には
  効かない——デモ・研修で確実に匿名化したい場合は Python 経路またはデモデータを
  使うこと。 `source: docs/PRIVACY_GUIDELINES.md / CLAUDE.md` `values: [Dignity, Safety]`
- **BRS-07 新旧リレーションの使い分けの理由** — 書き込みは正式名のみ・読み取りは
  `[:NEW|OLD]` 後方互換（規則は SCHEMA_CONVENTION §5）。**理由**: DB に旧名の
  実データが残存している可能性があり、読み取りで旧名を無視すると**登録済みの禁忌を
  見落とす**。安全情報の読み落とし防止のための規則であり、単なる互換性対応ではない。
  `values: [Safety]`
- **BRS-08 本人の同定は完全一致で** — Client の一意性は name の UNIQUE 制約＋
  name + dob のアプリ層検証（SCHEMA_CONVENTION §8.1）。書き込み時のクライアント
  照合は**完全一致必須**——部分一致で書き込むと、同姓の別人全員に禁忌や記録が
  付与される事故につながる。曖昧なときは書き込まずに確認する。
  `source: neo4j-support-db SKILL.md` `values: [Safety, Dignity]`
- **BRS-09 エスカレーションの連鎖** — 緊急ワード（パニック・SOS・倒れた・救急等）を
  検知したら他の作業に優先して emergency-protocol へ移譲する。insight-agent の
  総合リスクが High（should_trigger_emergency = true）の場合も emergency-protocol を
  自動連動する。親の機能不全の兆候（入院・死亡・認知症等）は parent_down
  プロトコルへ。 `source: CLAUDE.md ルーティング / manifesto/protocols/` `values: [Safety]`
- **BRS-10 文脈に適合させる（安易な当てはめの禁止）** — 施設・事業所探しでは
  「空きがある」だけで提案せず、LifeHistory と Condition への適合を照合する。
  支援記録に指導的・支配的な表現（「指導した」「約束させた」等）が含まれる場合は、
  より適切な表現への変換を提案する。 `source: manifesto/MANIFESTO.md ルール3・4`
  `values: [Dignity]`
- **BRS-11 説明責任（AuditLog）** — すべての書き込み（登録・更新・削除・廃棄）は
  AuditLog に記録する。データ廃棄（退所・保存期間超過）も監査記録を残す。
  ナラティブ由来の書き込みでは、監査記録が**出所（`sourceHash`）と `correlationId`** を持ち、
  API が返す `auditLogId` は**実在の AuditLog ノードへ解決できる**こと（2026-08-11 拡張。
  擬似 ID を返すだけでは説明責任の連鎖が監査側で切れる）。
  **両系（Obsidian Vault ⇔ support-db）突合の正は `AuditLog.sourceHash` とし、事実ノード側の
  `sourceHash` は突合に使わない**——ノード側は経路で意味が異なる（語り経由の注入は raw 原本の
  sha256／CREATE 系ラベルの自動生成は重複検出用の props 自己ハッシュ）（2026-08-11 追記）。
  `source: SCHEMA_CONVENTION §11.1-7 v3.4.1 / docs/PRIVACY_GUIDELINES.md` `values: [Advocacy]`
- **BRS-12 0件の解釈と表示（Review の運用）** — BRS-04 が求める「確認済みの0件」と
  「未確認」の区別を、Review（ENT-24）で実装する。

  **表示の規則**（0件が安全に直結する領域＝ NgAction / CarePreference / KeyPerson /
  Guardian / Certificate / CareRole で必須）:

  | 状態 | 表示 |
  |---|---|
  | 件数 > 0 | 通常どおり内容を提示 |
  | 件数 0・当該 domain の Review **なし** | **「未確認」と表示する。「なし」「該当なし」と表示してはならない** |
  | 件数 0・当該 domain の Review **あり** | 「◯年◯月に◯◯（source）に確認、登録なし」と**情報源つきで**表示 |

  **「禁忌なし」という表示は、Review がある場合にのみ許される。**
  Review が無い0件を「禁忌なし」と表示することは、No Fabrication 違反であり、
  未聴取を確認済みと偽ることに等しい。

  **データ品質上の扱い**: Review の無い0件は、data-quality-agent が**最優先の欠損**
  として検出する（BRS-04）。とりわけ NgAction の未確認は、新規クライアントの
  受け入れ・初回訪問前に解消すべき項目とする。

  **記録は追記のみ**——確認をやり直したら Review を新たに1件追加する（既存を
  上書きしない）。確認の履歴が積み上がることで「いつ・誰に聞いた情報か」が
  親なき後も辿れる（ENT-24）。

  ~~**スコープ外（今回は実装しない）**: `reviewedAt` の古さによる陳腐化判定は行わない~~
  → **2026-08-08 解消**: 陳腐化判定は BRS-13（証拠・鮮度モデル）が事実側の
  `lastConfirmedAt` / `staleAfter` を基準に導入した（Review の reviewedAt 自体を
  閾値判定しない点は不変。判定対象は事実ノードの鮮度）。
  `source: 2026-07-12 河原氏決定 → 2026-08-08 Track A 承認で更新` `values: [Safety, Continuity, Dignity]`
- **BRS-13 証拠・鮮度モデル（Track A Phase 1）** — 「DBの中身は事実ではなく、
  賞味期限つきの観測である」を NgAction / CarePreference に実装する。
  要件書・技術仕様は oya-inai-db/docs/evidence-freshness-{requirements,technical-spec}.md
  （2026-08-08 河原氏承認）。

  **証拠**: 安全系事実は `source`（ENU-17 の語彙）と `sourceDetail` を持つ。
  確信度スコアは導入しない（自己採点は役に立って見える方向に間違える）。

  **鮮度**: `lastConfirmedAt` ＋ `coalesce(staleAfter, freshnessDefaults[label])` で
  期限判定。期限超過は**「要再確認」への降格表示であって、削除も非表示もしない**。
  再確認したら Review ＋ CONFIRMS を追記し lastConfirmedAt を更新（1トランザクション）。

  **二段階承認**: 弱い書き込み経路（AI抽出・MCP直接）からの安全系事実は
  `status: Pending` で作成され、人間の承認で `Active` に昇格する（チャット承認・
  approvedBy 必須・AuditLog 記録。禁忌系の承認は管理者=河原氏のみ〔運用ルール〕）。

  **矛盾の保留**: 情報源が食い違ったら `CONTRADICTS`（新観測→既存事実。追記専用・
  `resolvedAt IS NULL`=未解決）で保持し、人間が裁定するまで「係争中」を表示し続ける。
  上書き・平均・自動裁定はしない。

  **非対称ルール（最重要）**: NgAction の警告は、矛盾・期限超過・Pending の
  いずれでも**自動では決して消えない**。表示停止の唯一の経路は管理者裁定による
  `status: Inactive` 化（AuditLog 必須）。

  **表示経路の網羅性**: `Pending` → チャット承認待ち一覧（禁忌は照会時にも「未確定」
  表示）/ 未解決 CONTRADICTS → 照会時の係争中警告（status 非依存）/ `Active`×期限超過
  → 再確認キュー / `Inactive` → 非表示（管理者裁定のみが到達経路）。この2ラベルの
  status は上記3値に制限されるため、**どのリストにも出ない禁忌は構造的に生じない**。
  `source: 2026-08-08 河原氏承認` `values: [Safety, Continuity, Advocacy]`
- **BRS-14 事実時間軸（Track A Phase 2）** — 「DB の中身は賞味期限つきの観測である」
  （BRS-13）に、「観測と事実の時間は別物である」を加える。BRS-13 の lastConfirmedAt は
  **こちらが知った時間**、本項の validFrom / validTo は**事実が有効だった期間**。後から入った
  訂正で「その時に正しかったこと」と「その時に知っていたこと」が混ざらないよう、2軸を分けて持つ。
  技術仕様は oya-inai-db/docs/valid-time-axis-technical-spec.md（SCHEMA_CONVENTION v3.5 §7.10 と対）。

  **不変の登録日**: `registeredAt` は CREATE 時に自動付与し、以後どの経路でも書き換えない
  （Guardian が更新時に破棄する）。

  **validFrom は任意**: 禁忌の多くは「いつから真だったか」が誰にも分からない。分からないものを
  埋めさせない。照会は `coalesce(validFrom, registeredAt)`。

  **validTo は裁定と同時**: 非対称ルール（BRS-13）を弱めない。validTo が入る唯一の経路は
  管理者裁定による Inactive 化で、AuditLog 必須。期限超過や矛盾から自動では入れない。

  **リレーションの交代は履歴にする**: HAS_KEY_PERSON は張り替えず endDate + Inactive を
  書いて新規追加する（USES_SERVICE と同型）。親なき後に最も変わりやすい関係だからこそ、
  誰がいつまで担っていたかを消さない。
  `source: 2026-09-03 河原氏決定` `values: [Continuity, Safety]`

---

## 5. enums — 列挙値の意味

値の一覧・表記規則は SCHEMA_CONVENTION §7 が正。ここでは**各値をどう判定するか**の
日本語定義を定める。

- **ENU-01 NgAction.riskLevel（禁忌の重大度）**
  - `LifeThreatening`（生命に関わる）: 命の危険に直結するもの。アレルギー・誤嚥
    リスク・服薬禁忌など。**1件でもあれば緊急時に最初に読み上げる。**
  - `Panic`（パニック誘発）: 本人が強い混乱状態に陥る引き金。大きな音・特定の
    状況・特定の関わり方など。生命に直結しないが、行動停止・自傷・二次事故に
    つながりうる。
  - `Discomfort`（不快・ストレス）: 本人が嫌がる・強いストレスを受けるもの。
    信頼関係と本人の尊厳のために避ける。
  - 判定に迷う場合は**より重大な側に倒す**（安全側の原則。BRS-05 の段階表現翻訳と
    同じ思想）。
- **ENU-02 SupportLog.effectiveness（対応の効果）**
  - `Effective`: 対応が効いた（落ち着いた・うまくいった）。MET-04 の昇格候補の原料。
  - `Ineffective`: 逆効果・悪化した。**これも貴重な記録**——「してはいけない関わり」
    として引き継ぎで共有する。
  - `Neutral`: 効果の判断がつかない・どちらでもない。
  - `Unknown`: 効果を観察できていない（記録時点で不明）。
  - ※ `Excellent` は正式な値ではない。`High/Medium/Low` も effectiveness の値では
    ない（それは priority の値域）。——旧 SKILL.md の 'excellent' 判定と validator の
    High/Medium/Low 混入は 2026-07-12 に解消済み（DRIFT-03 / DRIFT-05 訂正注記参照）。
- **ENU-03 SupportLog.emotion（本人の感情）** — 10値（SCHEMA_CONVENTION §7.4）。
  記録テキストから**本人の**感情状態を読み取り最も近い値を選ぶ（支援者の感情では
  ない）。明確でない場合は `Neutral`。
  **負の感情**＝ `Anger / Sadness / Fear / Disgust / Anxiety` の5値。この集合が
  MET-01〜03 の分析対象であり、集合の変更は予兆検知の感度を直接変えるため
  河原氏の承認事項とする。
- **ENU-04 SupportLog.type（記録の種別）** — `日常記録`（既定）/ `インシデント`
  （事故・トラブル。振り返りの対象）/ `会議`（ケース会議）/ `引き継ぎ`（担当交代の
  申し送り。handover プロトコルの原料）。
- **ENU-05 status（状態）** — `Active`（現に有効・利用中）/ `Inactive`（終了・
  無効）/ `Pending`（手続き・調整中）/ `Completed`（完了）/ `Suspended`（一時停止）/
  `Monitoring`（経過観察中。例: 術後経過観察の Condition）。
  ※ ワークフロー文書の「手配済み / 調整中 / 緊急対応必要」等の表示ラベルは
  レポート上の表現であって、DB の status 値ではない（混同しない）。
  ※ **NgAction / CarePreference の status は `Active` / `Pending` / `Inactive` の
  3値に制限**（BRS-13。2026-08-08 Track A）。Pending=承認待ち、Inactive=管理者裁定
  による解除のみ。
  ※ **HAS_KEY_PERSON.status は `Active` / `Inactive` の2値に制限**（BRS-14。2026-09-03
  Track A Phase 2）。Inactive には endDate が必須。
- **ENU-06 CarePreference.priority（推奨ケアの優先度）** — `High / Medium / Low`。
  High はケアの成否を左右するもの、Low は「できれば」の配慮。
  ※ Guardian の priority 検証は 2026-07-12 に新設済み（DRIFT-05 解消時）。
  値域の SCHEMA_CONVENTION §7 への正式収載は次回改版（v3.3）の追記候補。

### 未正典化の列挙値（provisional — 値域の正典収載待ち）

以下は各スキルが現に使っている値域だが、SCHEMA_CONVENTION §7 に未収載。
**値域の正式化は CONVENTION 側への追記**（フェーズ3以降）とし、本書は現状の
意味だけを記録する。
`provisional: 見直しトリガー = SCHEMA_CONVENTION 次回改版（v3.3）時に §7 へ収載`

- **ENU-07 ServiceProvider.availability**: `空きあり / 要相談 / 満員 / 未確認`
  （日本語値。検索の優先順は 空きあり→要相談→未確認→満員）。
- **ENU-08 ProviderFeedback.rating**: `◎（良い）/ ○（普通）/ △（課題あり）/ ×（不可）`
  （スコア換算は MET-08）。
- **ENU-09 ProviderFeedback.category**: `行動障害対応 / コミュニケーション / 環境 /
  送迎 / 食事 / 医療連携 / その他`。
- **ENU-10 Certificate.type**: `療育手帳 / 精神障害者保健福祉手帳 / 身体障害者手帳 /
  障害福祉サービス受給者証 / 自立支援医療受給者証`。
- **ENU-11 Guardian.type**: `成年後見 / 保佐 / 補助 / 任意後見`（法定後見3類型＋
  任意後見。権限の範囲が異なるため型の正確な記録が Advocacy の要）。
- **ENU-12 LifeHistory.era**: `幼少期 / 学齢期 / 青年期 / 成人後`。
- **ENU-13 CarePreference.category**: `食事 / 入浴 / パニック時 / 移動 / 睡眠 / 服薬 /
  コミュニケーション / その他`（日本語許容は SCHEMA_CONVENTION §1.4 準拠）。
- **ENU-14 USES_SERVICE.status**: 利用終了は `Inactive` を使用する
  （`source: 2026-07-12 河原氏決定`）。旧値 `Ended` は ENU-05 の値域外の独自値で、
  書き込み禁止・読み取りのみ後方互換（DRIFT-06 訂正注記参照）。
- **ENU-15 CareRole.priority**: 値域未定義（High/Medium/Low か数値か曖昧）。
  レジリエンス診断の並び順に影響するため要決定。

### 確認記録（Review）の列挙値

- **ENU-16 Review.domain（確認した領域）** — どの領域について確認したか。
  対応するノードラベル名をそのまま使う（対応関係を自明にするため）:
  `NgAction` / `CarePreference` / `KeyPerson` / `Guardian` / `Certificate` / `CareRole`。
  この6領域はいずれも**0件が安全・権利に直結する**（禁忌が無い、緊急連絡先が
  無い、手帳が無い、いずれも「本当に無い」のか「聞いていない」のかで意味が
  正反対）。上記以外の domain は使わない。
- **ENU-17 Review.source（情報源）** — **誰に確認したか**。日本語値を許容する
  （支援者が直接読む値のため。SCHEMA_CONVENTION §1.4 の日本語許容例外）:
  `本人` / `母親` / `父親` / `家族・親族` / `主治医` / `前事業所` / `相談支援専門員` /
  `後見人等` / `記録のみ`。
  **この値は信頼度の判断材料であり、欠いてはならない**——「母親に確認して禁忌なし」
  と「本人にしか聞けていない」は、同じ「0件」でも重みが全く違う。
  `記録のみ`（既存文書を見ただけで、人には確認していない）は**最も弱い情報源**であり、
  これだけで「確認済み」とするのは推奨しない（記録の不在は不在の証明ではない）。
  **2026-08-08 拡張（Track A / BRS-13）**: この語彙は Review だけでなく
  **NgAction / CarePreference の `source` プロパティ**と **CONTRADICTS の `source`**
  にもそのまま使う。新語彙は発明しない。既存データの一括初期化では `記録のみ` を入れる。

---

## 6. 機械検証ブロック（四者一致チェック）

以下の JSON は `nest-support/scripts/check_semantic_drift.py` が読み取り、
① 本ブロック（あるべき仕様） ② `lib/schema_validator.py`（Guardian の実装） ③
`GET /api/narrative/schema`（agno 実行時 allowlist。API 停止時は agno ソースの
AST 解析にフォールバック） ④ nest `lib/db_operations.py`（Python 登録経路の
MERGE_KEYS / CLIENT_SCOPED_LABELS。AST 解析）を突合する。既知の不一致は
`acceptedDrifts` に日付・理由付きで登録し、**未登録の不一致のみを FAIL** とする。
（④ は 2026-07-13 追加——DRIFT-12 が機械検出されなかった死角の解消。`nestLib` キーが正値）

```json machine-check
{
  "version": "1.0",
  "canonical": {
    "nodeLabels": [
      "Client", "Condition", "NgAction", "CarePreference", "KeyPerson",
      "Guardian", "Hospital", "Doctor", "Certificate", "PublicAssistance",
      "Organization", "Supporter", "SupportLog", "MeetingRecord", "AuditLog",
      "LifeHistory", "Wish", "Identity", "ServiceProvider", "ProviderFeedback",
      "Relative", "CareRole", "Review"
    ],
    "relationshipTypes": [
      "HAS_CONDITION", "MUST_AVOID", "IN_CONTEXT", "REQUIRES", "ADDRESSES",
      "HAS_KEY_PERSON", "HAS_LEGAL_REP", "HAS_CERTIFICATE", "RECEIVES",
      "REGISTERED_AT", "TREATED_AT", "HAS_DOCTOR", "SUPPORTED_BY", "LOGGED",
      "RECORDED", "ABOUT", "FOLLOWS", "AUDIT_FOR", "HAS_HISTORY", "HAS_WISH",
      "HAS_IDENTITY", "USES_SERVICE", "HAS_FEEDBACK", "WROTE",
      "IS_PARENT_OF", "FAMILY_OF", "PERFORMS", "CAN_BE_PERFORMED_BY",
      "REVIEWED",
      "CONTRADICTS", "CONFIRMS"
    ],
    "enums": {
      "riskLevel": ["LifeThreatening", "Panic", "Discomfort"],
      "effectiveness": ["Effective", "Ineffective", "Neutral", "Unknown"],
      "priority": ["High", "Medium", "Low"],
      "emotion": ["Joy", "Anger", "Sadness", "Fear", "Surprise", "Disgust",
                  "Calm", "Anxiety", "Confusion", "Neutral"],
      "status": ["Active", "Inactive", "Pending", "Completed", "Suspended",
                 "Monitoring"],
      "reviewDomain": ["NgAction", "CarePreference", "KeyPerson", "Guardian",
                       "Certificate", "CareRole"]
    },
    "negativeEmotions": ["Anger", "Sadness", "Fear", "Disgust", "Anxiety"]
  },
  "metrics": {
    "emotionDrift": {"baselineDays": 30, "recentDays": 7,
                     "warnThreshold": 0.3, "severeThreshold": 0.5},
    "cascadingRisk": {"days": 3, "minCascade": 2},
    "staffOverload": {"days": 7, "negativeRatioThreshold": 0.5, "minLogs": 3},
    "carePattern": {"discoverMinFrequency": 2, "promoteMinFrequency": 3},
    "renewalUrgency": {"immediateDays": 30, "warningDays": 60, "planningDays": 90}
  },
  "freshnessDefaults": {
    "NgAction": 365,
    "CarePreference": 365,
    "KeyPerson": 180,
    "Doctor": 365,
    "Hospital": 365,
    "_note": "staleAfter の既定日数（BRS-13）。Certificate は nextRenewalDate が正で対象外。ノード個別の staleAfter プロパティが優先（coalesce）。Phase 1 の適用対象は NgAction / CarePreference のみ"
  },
  "requiredProperties": {
    "NgAction": ["source", "status", "lastConfirmedAt", "registeredAt"],
    "CarePreference": ["source", "status", "lastConfirmedAt", "registeredAt"]
  },
  "restrictedStatus": {
    "NgAction": ["Active", "Pending", "Inactive"],
    "CarePreference": ["Active", "Pending", "Inactive"]
  },
  "immutableProperties": {
    "NgAction": ["registeredAt"],
    "CarePreference": ["registeredAt"]
  },
  "conditionalRequired": {
    "NgAction":       {"when": {"status": "Inactive"}, "require": ["validTo"], "forbidWhen": {"status": ["Active", "Pending"]}, "forbid": ["validTo"]},
    "CarePreference": {"when": {"status": "Inactive"}, "require": ["validTo"], "forbidWhen": {"status": ["Active", "Pending"]}, "forbid": ["validTo"]}
  },
  "relationshipProperties": {
    "HAS_KEY_PERSON": {"required": ["rank", "startDate", "status"], "optional": ["endDate"],
                       "status": ["Active", "Inactive"], "requireWhenInactive": ["endDate"]},
    "USES_SERVICE":   {"required": ["startDate", "status"], "optional": ["endDate"]}
  },
  "nestLib": {
    "mergeKeys": {
      "Certificate": ["type", "grade"],
      "Doctor": ["name"],
      "Relative": ["name"],
      "Identity": ["name", "dob"]
    },
    "neverMergeLabels": ["Review", "CareRole", "ProviderFeedback"]
  },
  "acceptedDrifts": []
}
```

> **チェッカーの限界**: insight_engine 内にハードコードされた一部の値
> （severity 判定の 0.5、staff overload の記録3件以上）は関数シグネチャに現れないため
> ソーステキスト照合のみの簡易検証となる。また SKILL.md 内に転記された閾値の
> 検証は対象外（SKILL.md は索引に徹し、数値は本書と insight_engine を正とする）。

---

## 7. 既知ドリフト台帳（2026-07-12 フェーズ1調査で発見・未修正）

フェーズ3（矛盾の解消）の候補一覧。**修正には河原氏承認＋バックアップ確認が先行**
（support-db は本番実データを持つ）。解消したら本台帳に日付入り訂正注記を残す。

| ID | 状態 | 内容 | 処置 |
|---|---|---|---|
| DRIFT-01 | ✅ 解消（2026-07-12） | MANIFESTO.md ルール1 の緊急時提示順（EconomicRisk 入り）が BRS-01 と食い違っていた | MANIFESTO ルール1 を BRS-01（emergency.md 版）へ整合。旧順序は訂正注記として MANIFESTO 内に残置 |
| DRIFT-02 | ✅ 解消（2026-07-12） | manifesto がかかりつけ医を Hospital 表現のまま（Doctor / HAS_DOCTOR 未反映） | MANIFESTO 第3柱に `:Doctor` を追加、emergency.md ステップ2-4 を「かかりつけ医（Doctor / Hospital）」へ修正（各訂正注記付き） |
| DRIFT-03 | ✅ 解消（2026-07-12） | neo4j-support-db T6 と visit-prep が `effectiveness STARTS WITH 'excellent'` を判定に使用していた | 両 SKILL.md から 'excellent' 判定を削除（訂正注記付き） |
| DRIFT-04 | ✅ 解消（2026-07-12） | data-quality-agent の effectiveness 検証セットに `Unknown` が欠落していた | 検証セットへ Unknown を追加（訂正注記付き） |
| DRIFT-05 | ✅ 解消（2026-07-12） | schema_validator の ENUM_VALUES.effectiveness に High/Medium/Low が混入・priority 検証が不存在だった | effectiveness を正式4値に修正し priority 検証を新設（コード内訂正注記付き）。§6 acceptedDrifts から削除済み |
| DRIFT-06 | ✅ 解消（2026-07-12 河原氏決定） | provider-search の USES_SERVICE.status に `Ended`（ENU-05 値域外） | 利用終了は `Inactive` へ統一。書き込みは Inactive のみ・読み取りは旧 Ended に後方互換（ENU-14 参照） |
| DRIFT-07 | ✅ 解消（2026-07-13） | agno 実行時 allowlist が v3.1/v3.2 未追従。HAS_IDENTITY は許可済みなのに Identity ラベル不在という不整合も | agno の `lib/db_new_operations.py` と `api/app/lib/db_operations.py`（実行時の門番・`/api/narrative/schema` の出典）の両方へノード5件（Doctor/Relative/CareRole/ProviderFeedback/Identity）・リレーション7件を追加し、`sync_narrative_intake_schema.py --apply` でスキル側 JSON も再生成。CareRole は ENT-16 に従い MERGE ではなく常時 CREATE（per-client スコープ） |
| DRIFT-08 | ✅ 解消（2026-07-12） | Certificate の MERGE キーがスキル3本で type のみ（正典 §10.3 は type+grade 複合キー） | neo4j-support-db / onboarding-wizard / narrative-extractor の MERGE を複合キー（grade 未指定は '不明'）へ修正（各訂正注記付き） |
| DRIFT-09 | ⏳ 残置 | 「4本柱」「7本柱」の呼称揺れ、manifesto 内の旧関数名（search_emergency_info 等）残存、wamnet-provider-sync の日付表記混在 | 軽微。文書整理時にまとめて修正 |
| DRIFT-10 | ✅ 解消（2026-07-13） | Review / REVIEWED を 2026-07-12 新設したが、**agno 実行時 allowlist が未追従**だった。Guardian（schema_validator.py）は 2026-07-12 に反映済み（Review / REVIEWED / LABEL_SCOPED_ENUM_VALUES） | DRIFT-07 と一括で agno allowlist（2ファイル＋スキル JSON）へ Review / REVIEWED を追加。Review は ENT-24（追記のみ）に従い常時 CREATE。acceptedDrifts の DRIFT-07a+10a / 07b+10b を削除 |
| DRIFT-12 | ✅ 解消（2026-07-13） | nest `lib/db_operations.py`（Python 登録経路）が正典未追従だった。(a) `MERGE_KEYS["Certificate"]` が `["type"]` のみ（正典 §10.3 は type+grade。同一人の療育手帳 A と B が1ノードに潰れる実バグ候補）、(b) Doctor / Relative / Identity が MERGE_KEYS 不在。`check_semantic_drift.py` が nest lib を検査対象にしていなかったため機械検出されなかった | (1) MERGE_KEYS を正典整合に修正（Certificate=type+grade・grade 未指定は「不明」補完、Doctor/Relative=name、Identity=name+dob）。CareRole / Review / ProviderFeedback は**意図して MERGE しない**（ENT-16 / ENT-24 / feedbackId 欠落時の登録喪失回避）——不在が正しいことをテストで固定。(2) Relative は逆向きリレーション（Relative→Client）のため既存スコープ機構の死角だった——`_build_parent_link` を双方向解決に拡張し client スコープ化（同姓同名家族の収斂防止）。(3) チェッカーに ④ nest lib の AST 照合を追加し、§6 に `nestLib` 正値ブロックを新設（死角の恒久解消） |
| DRIFT-11 | ✅ 解消（2026-07-12） | (a) 本日追加した PII ルールの文言が、**既存の support-db 内ベクトルインデックス（Gemini Embedding 2 で生成）をも禁止してしまっていた**。(b) そもそも embedding 生成で外部APIに何を送っているのかが正典に記録されていなかった | (a) 禁止対象を「別ストア（LightRAG 等）への複製」に限定し、内部 embedding は BRS-03 の管轄として適用外と明記（CLAUDE.md §8 / neo4j-support-db ルール7）。(b) **実装を調査した結果、氏名・生年月日は意図的に送信されていないことが判明**（`build_client_summary_text` は `displayCode` を使用し、コードコメントにも明記）。この設計判断を BRS-03 に明文化し、残存リスク（禁忌本文自体は外部に出ている）も provisional で記録 |
| DRIFT-14 | ✅ 解消（2026-08-11） | `/api/narrative/intake` の schemas docstring（`narrative_intake.py`）が「mergeKey は MERGE 対象ラベルのみ必須」と読める記述のまま、実装（`narrative_intake_service.py` の検証器）は **MERGE キーの値を `properties` 側に要求**していた。**実装が正しく docstring が古い**——mergeKey フィールドはメタ情報であり、検証・書き込みとも properties を正とする（スキル層 E-5 で `merge_key_missing` の実測により発見） | docstring を実装に合わせて修正（正典・実装の変更なし）。利用側（oya-inai-neo4j スキル）にも「キー値は properties 側に必ず入れる」を明記済み |
| DRIFT-13 | ✅ 解消（2026-08-10） | v1.6（2026-08-08）で正典収載した `CONFIRMS` / `CONTRADICTS` に、**実装3か所すべてが未追随**だった（② `lib/schema_validator.py`、③ API 門番の `ALLOWED_REL_TYPES`、④ nest lib）。`POST /api/narrative/intake` に CONFIRMS を含めると `rel_type_not_allowed` で reject され、**証拠・鮮度モデルの中核（Review＋CONFIRMS＋lastConfirmedAt）が正規の書き込み経路から実行不能**だった。さらに `check_semantic_drift.py` が oya-inai-db では**③を外部リポジトリ（~/Dev-Work/neo4j-agno-agent）・④を存在しない配置のパスに向けており恒久 WARN**——carve-out 以降、同リポジトリの実装は一度も四者一致チェックを受けていなかった。DRIFT-07／DRIFT-10 と同型の再発を、検出器の死角が許した形 | (1) 許可リスト3か所に CONFIRMS / CONTRADICTS を追加。RED から書いたテストで `rel_type_not_allowed` の再現を確認後に修正し、追記専用（`MERGE_KEYS` 不在＋`ALLOWED_CREATE_LABELS` 収載）を DRIFT-12 様式でテスト固定。(2) **チェッカーの検査対象を当該リポジトリ内へ付け替え**、②は `importlib` のファイル直読みで `lib/__init__.py` の dotenv／streamlit 連鎖を回避（素の `python3` でも完走）。(3) 結果 FAIL 0 ＝ **carve-out 後の oya-inai-db にとって最初の本物の四者一致検証**。oya-inai-db main e5ed2a6（55a40da・46787b0 をマージ）。**発見の経緯**: oya-inai-wiki 側「単一インテーク・二系統仕分け」の検証で Guardian 検査をかけた際に露見 |


> **DRIFT-13 から得た恒久策（2026-08-10）**
> 1. **カーブアウト時のチェッカー移植を手順化する。** 根因は「原型のパスを引き継いだまま配置が変わった」こと。検査対象のパスは**リポジトリ相対（`REPO_ROOT` 基準）で解決する**ことを標準にする。
> 2. **「検査対象ファイルが見つからない」を WARN から FAIL へ昇格させる。** 見つからないものは検査できておらず、**未検査を合格と区別できない**——これは BRS-12 が Review で解決した「0件の二義性」と同じ構造の問題である。検査側にも同じ原則を適用する。

### 7-2. 登録済み同期点（機械配布・手コピー禁止）

正典から写しへの配布は機械同期に限り、同期点は本台帳に登録する（DRIFT-13 の教訓の一般化。
写しは AUTO-GENERATED バナー付きの生成物であり直接編集禁止）。新しい写しを作るときは、
手コピーせず同期手段を用意してここに1行足すこと。

| # | 正典 | 写し | 同期手段 |
|---|---|---|---|
| SP-1 | shared-schema `SCHEMA_CONVENTION.md` / `SEMANTIC_MODEL.md` | 4リポジトリの docs/ コピー（対象は script 内 TARGETS が正） | `shared-schema/sync-schema.sh` |
| SP-2 | oya-inai-wiki `docs/dual-intake-routing.md`（単一インテークの仕分け判断規則・正本表22行） | `oya-inai-db/claude-skills/oya-inai-intake/reference/dual-intake-routing.md` | `oya-inai-db/scripts/sync_skill_refs.py`（2026-08-11 登録） |
| SP-3 | oya-inai-wiki `CLAUDE.md` §1 の raw/ 8棚構成 | `oya-inai-db/claude-skills/oya-inai-intake/SKILL.md` Step 2 の8棚表 | 同スクリプト（コピーでなく**集合一致の検査**。乖離・0件・過不足は FAIL）（2026-08-11 登録） |

**SP-1 の適用状況（2026-09-03 記録）**: v1.8 / SCHEMA_CONVENTION v3.5 を sync-schema.sh で
4配布先すべて（oya-inai-db / neo4j-agno-agent / oyagami-local / nest-support＝`--write-prod`・河原氏承認）
へ同期済み。同日、事実時間軸の移行 Cypher を oya-inai-db スタックと nest-support 本番 DB の両方に適用
（記録は oya-inai-db/docs/MIGRATION_LOG_valid-time-axis.md）。
なお v1.8 の**実装追従（Guardian・書き込み経路・検出器）は oya-inai-db のみ**。他配布先の
Guardian 相当は未追従（技術仕様 §4-3 の後続課題）。**未登録の乖離は DRIFT-13 と同じ条件**のため
ここに残す。全配布先の実装が揃った時点でこの注記を削除する。
---

## 変更履歴

| 日付 | バージョン | 変更内容 |
|---|---|---|
| 2026-09-03 | **v1.8** | **事実時間軸（Track A Phase 2）の正本化**（河原氏決定 2026-09-03。技術仕様は oya-inai-db/docs/valid-time-axis-technical-spec.md）。**BRS-14 新設**（知得時間と事実時間の2軸・不変の registeredAt・validFrom 任意・validTo は裁定と同時・HAS_KEY_PERSON の交代は履歴にする）。ENT-08 に「現在のキーパーソン」の定義（status=Active かつ endDate IS NULL）、ENU-05 に HAS_KEY_PERSON.status の2値制限を追記。§6 machine-check に `requiredProperties` の registeredAt 追加、`immutableProperties` / `conditionalRequired` / `relationshipProperties` を新設（既存キーは不変）。SCHEMA_CONVENTION v3.5 と対 |
| 2026-08-11 | v1.7a | **v1.7 の適用状況を §7-2 に登録**（同期済みは oya-inai-db のみ・他3配布先は v1.6 のまま。追加的変更で実害はないが、未登録の乖離は DRIFT-13 と同じ条件のため既知化）。**BRS-11 に突合の正を1行追記**: 両系突合の正は `AuditLog.sourceHash` とし、事実ノード側の `sourceHash`（語り経由の raw 原本ハッシュと CREATE 系の重複検出用自己ハッシュで意味が二重）は突合に使わない。表題の版数を v1.6 のまま更新し忘れていたのも修正 |
| 2026-08-11 | **v1.7** | **BRS-11 を拡張**（スキル層 Phase E 発見1・河原氏裁定 (a) 案）: ナラティブ由来の監査記録は `sourceHash` と `correlationId` を持ち、API の `auditLogId` が実在ノードへ解決できること（SCHEMA_CONVENTION v3.4.1 と対）。事実ノードへの出所スカラー付与（(b) 案）は不採用——MERGE ノードのスカラーは後の語りが先の出所を上書きする（§0-6(b) と同型）。「事実ごとの出所を Review／CONFIRMS 側に持たせるか」は dual-intake ADR 未決論点9へ。**DRIFT-14 を台帳に登録（解消済み）**: intake schemas の docstring が古く実装（mergeKey 値は properties 側必須）が正 |
| 2026-08-11 | v1.6b | **§7-2「登録済み同期点」を新設（SP-1〜3）**。スキル層実装（oya-inai-db claude-skills/）で oya-inai-wiki 正典の写し（仕分け判断規則）と派生表（8棚表）が生じたため、手コピー禁止・機械配布の同期点として登録。同期手段は `oya-inai-db/scripts/sync_skill_refs.py`（--check で乖離を FAIL 検出）。**正典の内容そのものは無変更** |
| 2026-08-10 | v1.6a | **DRIFT-13 を台帳に登録（解消済み）**。v1.6 で収載した CONFIRMS / CONTRADICTS に実装3か所が未追随だった問題と、四者一致チェッカーが carve-out 先で誤った対象を検査していた死角を記録。恒久策2件（検査対象パスのリポジトリ相対解決／「対象ファイル不在」の WARN→FAIL 昇格）も併記。**正典の内容そのものは無変更** |
| 2026-08-08 | **v1.6** | **証拠・鮮度モデル（Track A Phase 1）の正本化**（河原氏承認 2026-08-08。要件書・技術仕様は oya-inai-db/docs/evidence-freshness-{requirements,technical-spec}.md）。**BRS-13 新設**（証拠=source/sourceDetail・鮮度=lastConfirmedAt/staleAfter・二段階承認 Pending・矛盾の保留 CONTRADICTS・**非対称ルール**=禁忌の警告は自動で消えない・表示経路の網羅性）。ENT-24 に CONFIRMS 拡張（0件確認と個別確認の区別）、BRS-12 の陳腐化スコープ外を解消、ENU-05 に NgAction/CarePreference の status 3値制限、ENU-17 を事実側 source に再利用。§6 machine-check に `CONTRADICTS`/`CONFIRMS`・`freshnessDefaults`・`requiredProperties`・`restrictedStatus` を追加。SCHEMA_CONVENTION v3.4 と対 |
| 2026-07-13 | **v1.5** | **DRIFT-12 解消（nest Python 登録経路の正典追従）＋検査の死角解消**。nest `lib/db_operations.py` の MERGE_KEYS を正典整合に修正（Certificate 複合キー・Doctor/Relative/Identity 追加）。Relative は逆向きリレーションのためスコープ機構を双方向対応に拡張して client スコープ化。CareRole / Review / ProviderFeedback は意図的に MERGE しない（不在をテストで固定）。§6 を「四者一致」に拡張——`nestLib` 正値ブロックを追加し、チェッカーが nest lib も AST 照合するようにした（DRIFT-12 が機械検出されなかった原因の恒久対策） |
| 2026-07-13 | **v1.4** | **DRIFT-07 / DRIFT-10 解消（agno allowlist 追従）**。agno の実行時 allowlist 2ファイル（`lib/db_new_operations.py` / `api/app/lib/db_operations.py`）へノード6件（Doctor / Relative / CareRole / ProviderFeedback / Identity / Review。API 側は Doctor 反映済みだったため実質5件）とリレーション8件（HAS_DOCTOR / IS_PARENT_OF / FAMILY_OF / PERFORMS / CAN_BE_PERFORMED_BY / HAS_FEEDBACK / WROTE / REVIEWED。API 側は HAS_DOCTOR 反映済み）を追加。MERGE キーは正典 §3 に整合（Doctor/Relative=name・名寄せ、Identity=name+dob）。**CareRole と Review は MERGE ではなく常時 CREATE**（ENT-16 の per-client スコープ則・ENT-24 の追記のみ則）。§6 acceptedDrifts から DRIFT-07a+10a / 07b+10b を削除 |
| 2026-07-12 | **v1.3** | **BRS-03 に「embedding 生成時の外部API送信」の許容範囲を明文化（DRIFT-11 解消）**。内部ベクトルインデックスの生成に Gemini Embedding 2 を使うことは許容するが、**氏名・生年月日は送信しない**（`displayCode` 等の非識別コードに置換）。これは新規の制限ではなく、**実装（`lib/embedding.py::build_client_summary_text`）に既存していた設計判断を正典に引き上げたもの**——コードコメントの1行だけが防波堤になっていた状態を解消した。残存リスク（禁忌本文自体は外部APIに出ている）も provisional で明示 |
| 2026-07-12 | **v1.2** | **Review（確認記録）の新設——「0件問題」の解消**。BRS-04 は以前から「確認済みの0件」と「未確認」の区別を命じていたが、**その区別を表現できる構造が存在せず、ルールが構造的に遵守不能だった**。ENT-24（Review）・BRS-12（0件の解釈と表示）・ENU-16/17（domain / source）を新設し、§6 機械検証ブロックに Review / REVIEWED / reviewDomain を反映。陳腐化判定はスコープ外（2026-07-12 河原氏決定）。DRIFT-10（agno/Guardian 未追従）・DRIFT-11（PII ルールの文言が内部 embedding まで禁止している問題）を台帳に登録 |
| 2026-07-12 | **v1.1** | **フェーズ3（矛盾の解消・限定スコープ）反映**。DRIFT-01〜06・08 を解消し台帳を状態列付きに更新（DRIFT-07 は次セッション送り、DRIFT-09 は残置——いずれも 2026-07-12 河原氏決定）。ENU-14 を「利用終了は `Inactive`」の決定で確定。§6 機械検証ブロックに `priority` を追加し acceptedDrifts から DRIFT-05 を削除 |
| 2026-07-12 | **v1.0** | 初版。フェーズ1調査（13スキル・manifesto・Guardian/Oracle 実装・agno allowlist の棚卸し）に基づき、entities 23 / metrics 9 / business_rules 11 / enums 15 を正本化。河原氏決定5点（Guardian 段階表現翻訳の現状維持と意図明文化・緊急時提示順は emergency.md 版・embedding 信頼ルール・形式(a)・manifesto 例示は合成例）を反映。機械検証ブロックと既知ドリフト台帳（DRIFT-01〜09）を併設 |
