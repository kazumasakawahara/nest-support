// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 緊急時体制エコマップ (emergency)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//
// 用途: 緊急対応時、新規支援者への引き継ぎ初期
//
// 【Safety First】
// 緊急時に必要な情報のみを表示します。
// 禁忌事項（NgAction）を最優先で表示し、
// リスクレベル順にソートされます。
//
// 含まれる情報:
//   - 本人の基本情報
//   - 禁忌事項（NgAction）★最優先
//   - 高優先度の推奨ケア（CarePreference where priority='High'）
//   - キーパーソン（優先順位順）
//   - 後見人（Guardian）
//   - かかりつけ医・医療機関（Hospital）
//
// リスクレベルの順序:
//   1. LifeThreatening（生命に関わる）
//   2. Panic（パニック誘発）
//   3. Discomfort（不快感）
//
// 使い方:
//   'クライアント名' を実際の名前に置き換えて実行してください
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MATCH (c:Client {name: 'クライアント名'})

// 禁忌事項（最重要）
OPTIONAL MATCH (c)-[:PROHIBITED|MUST_AVOID]->(ng:NgAction)

// 高優先度の推奨ケア
OPTIONAL MATCH (c)-[:PREFERS|REQUIRES]->(cp:CarePreference)
WHERE cp.priority = 'High'

// キーパーソン（緊急連絡先）
OPTIONAL MATCH (c)-[kp_rel:EMERGENCY_CONTACT|HAS_KEY_PERSON]->(kp:KeyPerson)

// 後見人
OPTIONAL MATCH (c)-[:HAS_GUARDIAN|HAS_LEGAL_REP]->(g:Guardian)

// 医療機関
OPTIONAL MATCH (c)-[:TREATED_AT]->(h:Hospital)

RETURN c, ng, cp, kp, kp_rel, g, h

ORDER BY
  // 禁忌事項のリスクレベル順
  CASE ng.riskLevel
    WHEN 'LifeThreatening' THEN 1
    WHEN 'Panic' THEN 2
    WHEN 'Discomfort' THEN 3
    ELSE 4
  END,
  // キーパーソンの優先順位順
  coalesce(kp_rel.rank, kp_rel.priority, 99)
