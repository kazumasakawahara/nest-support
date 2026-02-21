// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 支援会議用エコマップ (support_meeting)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//
// 用途: サービス担当者会議、モニタリング会議
//
// ケース会議で使用する、支援関係に焦点を当てたビュー。
// 直近30日間の支援記録も表示されます。
//
// 含まれる情報:
//   - 本人の基本情報
//   - 推奨ケア（CarePreference）
//   - キーパーソン（KeyPerson）
//   - 手帳・受給者証（Certificate）
//   - 直近の支援記録（SupportLog）
//
// 使い方:
//   'クライアント名' を実際の名前に置き換えて実行してください
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MATCH (c:Client {name: 'クライアント名'})

// 推奨ケア
OPTIONAL MATCH (c)-[:PREFERS|REQUIRES]->(cp:CarePreference)

// キーパーソン
OPTIONAL MATCH (c)-[kp_rel:EMERGENCY_CONTACT|HAS_KEY_PERSON]->(kp:KeyPerson)

// 手帳・受給者証
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(cert:Certificate)

// 直近30日の支援記録
OPTIONAL MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c)
WHERE log.date >= date() - duration({days: 30})

RETURN c, cp, kp, kp_rel, cert, s, log
