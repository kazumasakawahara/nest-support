// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 引き継ぎ用エコマップ (handover)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//
// 用途: 担当者変更、事業所変更時の引き継ぎ
//
// 担当者交代時に使用する包括的な情報ビュー。
// 履歴情報を含め、クライアントの全体像を把握できます。
//
// 含まれる情報:
//   - 本人の基本情報
//   - 禁忌事項（NgAction）
//   - 推奨ケア（CarePreference）
//   - 手帳・受給者証（Certificate）
//   - キーパーソン（KeyPerson）
//   - 後見人（Guardian）
//   - 医療機関（Hospital）
//   - 特性・診断（Condition）
//   - 生育歴（LifeHistory）
//   - 願い（Wish）
//   - 支援記録（SupportLog）直近50件
//
// 使い方:
//   'クライアント名' を実際の名前に置き換えて実行してください
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MATCH (c:Client {name: 'クライアント名'})

// 第2の柱：ケアの暗黙知
OPTIONAL MATCH (c)-[:PROHIBITED|MUST_AVOID]->(ng:NgAction)
OPTIONAL MATCH (c)-[:PREFERS|REQUIRES]->(cp:CarePreference)

// 第3の柱：法的基盤
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(cert:Certificate)

// 第4の柱：危機管理ネットワーク
OPTIONAL MATCH (c)-[kp_rel:EMERGENCY_CONTACT|HAS_KEY_PERSON]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:HAS_GUARDIAN|HAS_LEGAL_REP]->(g:Guardian)
OPTIONAL MATCH (c)-[:TREATED_AT]->(h:Hospital)

// 第1の柱：本人性
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(cond:Condition)
OPTIONAL MATCH (c)-[:HAS_HISTORY]->(hist:LifeHistory)
OPTIONAL MATCH (c)-[:HAS_WISH]->(w:Wish)

// 支援記録（Living Database）
OPTIONAL MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c)

WITH c, ng, cp, cert, kp, kp_rel, g, h, cond, hist, w, s, log
ORDER BY log.date DESC
LIMIT 50

RETURN c, ng, cp, cert, kp, kp_rel, g, h, cond, hist, w, s, log
