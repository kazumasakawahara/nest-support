// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// nest-support デモデータセット（匿名化済み）
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//
// このデータは完全に架空のものです。
// 実在の人物・団体・医療機関とは一切関係ありません。
//
// 用途:
//   - 説明会・研修でのデモンストレーション
//   - 新規導入時の操作練習
//   - システムの動作確認
//
// 実行方法:
//   Neo4j Browser (http://localhost:7474) で実行
//   または Claude に「デモデータを投入して」と依頼
//
// 安全設計（P0-7）:
//   すべてのデモノードは一意な demoId をキーに含めて MERGE する。
//   これにより demoId を持たない「実ノード」には決してマッチせず、
//   実データを汚染しない。削除は demoId IS NOT NULL を基準に行う。
//   リレーション統計は各ノードを demoId で再 MATCH してから張るため、
//   セミコロン区切りで独立実行しても未束縛変数の孤児ノードを作らない。
//
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// === クライアント1: 山本翔太（知的障害・自閉スペクトラム症） ===

MERGE (c1:Client {name: '山本翔太', demoId: 'demo-client-yamamoto'})
SET c1.dob = date('1998-07-22'),
    c1.bloodType = 'A',
    c1.isDemo = true;

// 特性・診断
MERGE (con1:Condition {name: '知的障害（中度）', demoId: 'demo-con-1'})
SET con1.status = 'Active',
    con1.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (con1:Condition {demoId: 'demo-con-1'})
MERGE (c1)-[:HAS_CONDITION]->(con1);

MERGE (con2:Condition {name: '自閉スペクトラム症', demoId: 'demo-con-2'})
SET con2.status = 'Active',
    con2.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (con2:Condition {demoId: 'demo-con-2'})
MERGE (c1)-[:HAS_CONDITION]->(con2);

// 禁忌事項（NgAction）— 安全上の最重要データ
MERGE (ng1:NgAction {action: '突然大きな声で話しかける', demoId: 'demo-ng-1'})
SET ng1.reason = 'パニックを誘発する。特に後方からの不意打ちは激しいパニックになる',
    ng1.riskLevel = 'Panic',
    ng1.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (ng1:NgAction {demoId: 'demo-ng-1'})
MERGE (c1)-[:MUST_AVOID]->(ng1);

MERGE (ng2:NgAction {action: 'エビ・カニを含む食事を提供する', demoId: 'demo-ng-2'})
SET ng2.reason = '甲殻類アレルギー（アナフィラキシーの既往あり）',
    ng2.riskLevel = 'LifeThreatening',
    ng2.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (ng2:NgAction {demoId: 'demo-ng-2'})
MERGE (c1)-[:MUST_AVOID]->(ng2);

MERGE (ng3:NgAction {action: '予告なくスケジュールを変更する', demoId: 'demo-ng-3'})
SET ng3.reason = '見通しが立たなくなりパニックを起こす',
    ng3.riskLevel = 'Panic',
    ng3.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (ng3:NgAction {demoId: 'demo-ng-3'})
MERGE (c1)-[:MUST_AVOID]->(ng3);

// 配慮事項（CarePreference）
MERGE (cp1:CarePreference {category: 'コミュニケーション', instruction: '視覚的な手がかり（絵カード・スケジュール表）を使って伝える', demoId: 'demo-cp-1'})
SET cp1.priority = 'High',
    cp1.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (cp1:CarePreference {demoId: 'demo-cp-1'})
MERGE (c1)-[:REQUIRES]->(cp1);

MERGE (cp2:CarePreference {category: '食事', instruction: '食事前に必ずアレルギー確認。エビ・カニ厳禁。エピペン携帯', demoId: 'demo-cp-2'})
SET cp2.priority = 'Critical',
    cp2.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (cp2:CarePreference {demoId: 'demo-cp-2'})
MERGE (c1)-[:REQUIRES]->(cp2);

MERGE (cp3:CarePreference {category: '移動', instruction: '外出時は事前にルートを説明し、変更がある場合は早めに予告する', demoId: 'demo-cp-3'})
SET cp3.priority = 'Medium',
    cp3.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (cp3:CarePreference {demoId: 'demo-cp-3'})
MERGE (c1)-[:REQUIRES]->(cp3);

// キーパーソン
MERGE (kp1:KeyPerson {name: '山本美智子', demoId: 'demo-kp-1'})
SET kp1.phone = '090-1234-XXXX',
    kp1.relationship = '母',
    kp1.role = '主たる介護者。翔太のことを最もよく知る人物',
    kp1.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (kp1:KeyPerson {demoId: 'demo-kp-1'})
MERGE (c1)-[:HAS_KEY_PERSON {rank: 1}]->(kp1);

MERGE (kp2:KeyPerson {name: '山本健一', demoId: 'demo-kp-2'})
SET kp2.phone = '090-5678-XXXX',
    kp2.relationship = '父',
    kp2.role = '緊急時の判断・手続き担当',
    kp2.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (kp2:KeyPerson {demoId: 'demo-kp-2'})
MERGE (c1)-[:HAS_KEY_PERSON {rank: 2}]->(kp2);

MERGE (kp3:KeyPerson {name: '木村和子', demoId: 'demo-kp-3'})
SET kp3.phone = '080-9012-XXXX',
    kp3.relationship = '叔母',
    kp3.role = '母が不在時のバックアップ。月に1〜2回面会',
    kp3.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (kp3:KeyPerson {demoId: 'demo-kp-3'})
MERGE (c1)-[:HAS_KEY_PERSON {rank: 3}]->(kp3);

// 医療機関
MERGE (h1:Hospital {name: 'さくら総合病院', demoId: 'demo-hosp-1'})
SET h1.specialty = '精神科・アレルギー科',
    h1.phone = '03-XXXX-XXXX',
    h1.isDemo = true;
// かかりつけ医は Doctor ノードで表現（Hospital.doctor 廃止）
MERGE (doc1:Doctor {demoId: 'demo-doctor-1'}) SET doc1.name = '田村医師', doc1.isDemo = true;
MATCH (h1:Hospital {demoId: 'demo-hosp-1'}), (doc1:Doctor {demoId: 'demo-doctor-1'})
MERGE (h1)-[:HAS_DOCTOR]->(doc1);
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (h1:Hospital {demoId: 'demo-hosp-1'})
MERGE (c1)-[:TREATED_AT]->(h1);

// 手帳
MERGE (cert1:Certificate {type: '療育手帳', grade: 'B1', demoId: 'demo-cert-1'})
SET cert1.nextRenewalDate = date('2027-03-31'),
    cert1.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (cert1:Certificate {demoId: 'demo-cert-1'})
MERGE (c1)-[r1cert:HAS_CERTIFICATE]->(cert1)
SET r1cert.issuedDate = date('2024-04-01'),
    r1cert.status = 'Active';

// 後見人
MERGE (g1:Guardian {name: '佐藤法律事務所 佐藤弁護士', demoId: 'demo-guardian-1'})
SET g1.type = '保佐人',
    g1.phone = '03-XXXX-YYYY',
    g1.organization = '佐藤法律事務所',
    g1.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (g1:Guardian {demoId: 'demo-guardian-1'})
MERGE (c1)-[:HAS_LEGAL_REP]->(g1);

// 生活史
MERGE (lh1:LifeHistory {period: '幼少期', episode: '3歳で自閉スペクトラム症の診断。5歳から療育を開始。音に敏感で運動会が苦手だった', demoId: 'demo-lh-1'})
SET lh1.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (lh1:LifeHistory {demoId: 'demo-lh-1'})
MERGE (c1)-[:HAS_HISTORY]->(lh1);

MERGE (lh2:LifeHistory {period: '学齢期', episode: '特別支援学校に通学。絵を描くことが得意で、校内展覧会で何度も入賞', demoId: 'demo-lh-2'})
SET lh2.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (lh2:LifeHistory {demoId: 'demo-lh-2'})
MERGE (c1)-[:HAS_HISTORY]->(lh2);

// 願い
MERGE (w1:Wish {content: '絵を続けたい。できれば自分の描いた絵を売ってみたい', demoId: 'demo-wish-1'})
SET w1.source = '本人',
    w1.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (w1:Wish {demoId: 'demo-wish-1'})
MERGE (c1)-[:HAS_WISH]->(w1);

MERGE (w2:Wish {content: '翔太が安心して暮らせる場所を見つけたい。私たちがいなくなっても大丈夫なように', demoId: 'demo-wish-2'})
SET w2.source = '母',
    w2.isDemo = true;
MATCH (c1:Client {demoId: 'demo-client-yamamoto'}), (w2:Wish {demoId: 'demo-wish-2'})
MERGE (c1)-[:HAS_WISH]->(w2);


// === クライアント2: 鈴木花（ダウン症） ===

MERGE (c2:Client {name: '鈴木花', demoId: 'demo-client-suzuki'})
SET c2.dob = date('2005-11-03'),
    c2.bloodType = 'O',
    c2.isDemo = true;

MERGE (con3:Condition {name: 'ダウン症候群', demoId: 'demo-con-3'})
SET con3.status = 'Active',
    con3.isDemo = true;
MATCH (c2:Client {demoId: 'demo-client-suzuki'}), (con3:Condition {demoId: 'demo-con-3'})
MERGE (c2)-[:HAS_CONDITION]->(con3);

MERGE (con4:Condition {name: '先天性心疾患（術後経過観察中）', demoId: 'demo-con-4'})
SET con4.status = 'Monitoring',
    con4.isDemo = true;
MATCH (c2:Client {demoId: 'demo-client-suzuki'}), (con4:Condition {demoId: 'demo-con-4'})
MERGE (c2)-[:HAS_CONDITION]->(con4);

// 禁忌事項
MERGE (ng4:NgAction {action: '激しい運動（長距離走、水泳の長時間練習等）', demoId: 'demo-ng-4'})
SET ng4.reason = '先天性心疾患の術後で、心臓への負荷を避ける必要がある',
    ng4.riskLevel = 'LifeThreatening',
    ng4.isDemo = true;
MATCH (c2:Client {demoId: 'demo-client-suzuki'}), (ng4:NgAction {demoId: 'demo-ng-4'})
MERGE (c2)-[:MUST_AVOID]->(ng4);

MERGE (ng5:NgAction {action: '否定的な言葉かけ（「ダメ」「できない」等）', demoId: 'demo-ng-5'})
SET ng5.reason = '自己肯定感が下がり、活動への意欲を失う',
    ng5.riskLevel = 'Discomfort',
    ng5.isDemo = true;
MATCH (c2:Client {demoId: 'demo-client-suzuki'}), (ng5:NgAction {demoId: 'demo-ng-5'})
MERGE (c2)-[:MUST_AVOID]->(ng5);

// 配慮事項
MERGE (cp4:CarePreference {category: '運動', instruction: '軽い運動は可。心拍数が120を超えないように注意。定期的に休憩を入れる', demoId: 'demo-cp-4'})
SET cp4.priority = 'Critical',
    cp4.isDemo = true;
MATCH (c2:Client {demoId: 'demo-client-suzuki'}), (cp4:CarePreference {demoId: 'demo-cp-4'})
MERGE (c2)-[:REQUIRES]->(cp4);

MERGE (cp5:CarePreference {category: 'コミュニケーション', instruction: '肯定的な声かけを心がける。できたことを具体的に褒める', demoId: 'demo-cp-5'})
SET cp5.priority = 'High',
    cp5.isDemo = true;
MATCH (c2:Client {demoId: 'demo-client-suzuki'}), (cp5:CarePreference {demoId: 'demo-cp-5'})
MERGE (c2)-[:REQUIRES]->(cp5);

// キーパーソン
MERGE (kp4:KeyPerson {name: '鈴木恵子', demoId: 'demo-kp-4'})
SET kp4.phone = '080-3456-XXXX',
    kp4.relationship = '母',
    kp4.role = '主たる介護者',
    kp4.isDemo = true;
MATCH (c2:Client {demoId: 'demo-client-suzuki'}), (kp4:KeyPerson {demoId: 'demo-kp-4'})
MERGE (c2)-[:HAS_KEY_PERSON {rank: 1}]->(kp4);

// 医療機関
MERGE (h2:Hospital {name: 'あおぞら小児科クリニック', demoId: 'demo-hosp-2'})
SET h2.specialty = '小児循環器科',
    h2.phone = '06-XXXX-XXXX',
    h2.isDemo = true;
// かかりつけ医は Doctor ノードで表現（Hospital.doctor 廃止）
MERGE (doc2:Doctor {demoId: 'demo-doctor-2'}) SET doc2.name = '中村医師', doc2.isDemo = true;
MATCH (h2:Hospital {demoId: 'demo-hosp-2'}), (doc2:Doctor {demoId: 'demo-doctor-2'})
MERGE (h2)-[:HAS_DOCTOR]->(doc2);
MATCH (c2:Client {demoId: 'demo-client-suzuki'}), (h2:Hospital {demoId: 'demo-hosp-2'})
MERGE (c2)-[:TREATED_AT]->(h2);

// 手帳
MERGE (cert2:Certificate {type: '療育手帳', grade: 'B2', demoId: 'demo-cert-2'})
SET cert2.nextRenewalDate = date('2026-08-31'),
    cert2.isDemo = true;
MATCH (c2:Client {demoId: 'demo-client-suzuki'}), (cert2:Certificate {demoId: 'demo-cert-2'})
MERGE (c2)-[r2cert:HAS_CERTIFICATE]->(cert2)
SET r2cert.issuedDate = date('2023-09-01'),
    r2cert.status = 'Active';

// 願い
MERGE (w3:Wish {content: 'パン屋さんで働きたい。パンを作るのが好き', demoId: 'demo-wish-3'})
SET w3.source = '本人',
    w3.isDemo = true;
MATCH (c2:Client {demoId: 'demo-client-suzuki'}), (w3:Wish {demoId: 'demo-wish-3'})
MERGE (c2)-[:HAS_WISH]->(w3);


// === 支援記録（SupportLog）のサンプル ===

MERGE (sup1:Supporter {name: 'デモ支援者A', demoId: 'demo-sup-1'})
SET sup1.role = '計画相談支援専門員',
    sup1.isDemo = true;

MERGE (sl1:SupportLog {demoId: 'demo-sl-1'})
SET sl1.date = date('2026-02-15'),
    sl1.content = '訪問時、翔太さんが新しい絵を見せてくれた。水彩画で季節の花を描いており、とても丁寧な仕上がり。母によると、毎日2時間ほど集中して描いているとのこと。作業所のアート活動への参加を検討。',
    sl1.effectiveness = 'Effective',
    sl1.isDemo = true
WITH sl1
MATCH (sup1:Supporter {demoId: 'demo-sup-1'})
MATCH (c1:Client {demoId: 'demo-client-yamamoto'})
MERGE (sup1)-[:LOGGED]->(sl1)
MERGE (sl1)-[:ABOUT]->(c1);

MERGE (sl2:SupportLog {demoId: 'demo-sl-2'})
SET sl2.date = date('2026-02-20'),
    sl2.content = '電話対応。母から相談：翔太が昨日パニックを起こした。原因は隣の部屋の工事音。イヤーマフを使用したところ15分で落ち着いた。今後、騒音が予想される場合は事前にイヤーマフを準備することを確認。',
    sl2.effectiveness = 'Effective',
    sl2.isDemo = true
WITH sl2
MATCH (sup1:Supporter {demoId: 'demo-sup-1'})
MATCH (c1:Client {demoId: 'demo-client-yamamoto'})
MERGE (sup1)-[:LOGGED]->(sl2)
MERGE (sl2)-[:ABOUT]->(c1);

MERGE (sl3:SupportLog {demoId: 'demo-sl-3'})
SET sl3.date = date('2026-03-01'),
    sl3.content = '花さんの作業所見学に同行。パン工房「ひまわり」を見学。花さんは積極的にスタッフに質問し、とても意欲的だった。体験利用を来月から開始予定。',
    sl3.effectiveness = 'Effective',
    sl3.isDemo = true
WITH sl3
MATCH (sup1:Supporter {demoId: 'demo-sup-1'})
MATCH (c2:Client {demoId: 'demo-client-suzuki'})
MERGE (sup1)-[:LOGGED]->(sl3)
MERGE (sl3)-[:ABOUT]->(c2);


// === 監査ログ ===

MERGE (al:AuditLog {demoId: 'demo-audit-1'})
SET al.timestamp = datetime(),
    al.user = 'installer',
    al.action = 'DEMO_DATA_LOAD',
    al.targetType = 'System',
    al.targetName = 'demo-data',
    al.details = 'デモデータセットを投入しました（匿名化済み架空データ）',
    al.clientName = 'ALL',
    al.isDemo = true;
