// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// nest-support 感情シミュレーションデータ
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//
// 目的:
//   insight-agent の予測アラート（Emotion Drift, Cascading Risk,
//   Staff SOS, Care Pattern Discovery）が正しく機能するか検証する。
//
// シナリオ設計:
//   山本翔太さん（demo-data.cypher で登録済み）に対し、
//   1ヶ月分の感情データを投入する。
//
//   前半2週間（3/1〜3/14）: 安定期（ベースライン）
//     - Calm/Joy が多く、ネガティブは散発的
//   後半2週間（3/15〜3/30）: 悪化期（ドリフト検出対象）
//     - 「作業中」のAnger が急増（Emotion Drift 検出）
//     - 「食事」「他者交流」でもSadness が出現（Cascading Risk 検出）
//     - 「別室に移動」が繰り返し Effective（Care Pattern 検出）
//
// 前提:
//   demo-data.cypher が先に実行されていること
//   （山本翔太、鈴木支援員、田中支援員が存在）
//
// 実行方法:
//   Neo4j Browser (http://localhost:7474) で実行
//   または load-demo-data.sh にオプション追加
//
// 削除方法:
//   MATCH (log:SupportLog) WHERE log.isSimulation = true DETACH DELETE log;
//
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// === 支援者の確認 ===
MERGE (suzuki:Supporter {name: '鈴木'});
MERGE (tanaka:Supporter {name: '田中'});

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ベースライン期間: 3/1 〜 3/14 (安定期)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// --- 3/1 ---
CREATE (log:SupportLog {date: date('2026-03-01'), situation: '食事', action: '通常通り提供', effectiveness: 'Neutral', emotion: 'Calm', triggerTag: '食事', context: '朝食、特に変化なし', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/2 ---
CREATE (log:SupportLog {date: date('2026-03-02'), situation: '作業', action: '折り紙の作業を実施', effectiveness: 'Effective', emotion: 'Joy', triggerTag: '作業中', context: '好きな折り紙で集中していた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/3 ---
CREATE (log:SupportLog {date: date('2026-03-03'), situation: '散歩', action: '近くの公園を散歩', effectiveness: 'Effective', emotion: 'Joy', triggerTag: '外出', context: '天気が良く、公園の花を見て笑顔', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '田中'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/4 ---
CREATE (log:SupportLog {date: date('2026-03-04'), situation: '入浴', action: '声かけ後、スムーズに入浴', effectiveness: 'Effective', emotion: 'Calm', triggerTag: '入浴', context: '特に問題なし', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/5 ---
CREATE (log:SupportLog {date: date('2026-03-05'), situation: '作業', action: '新しい作業に取り組む', effectiveness: 'Neutral', emotion: 'Anxiety', triggerTag: '作業中', context: '新しいビーズ作業に少し不安そうだった', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '田中'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/6 ---
CREATE (log:SupportLog {date: date('2026-03-06'), situation: '食事', action: 'メニュー表を事前に見せた', effectiveness: 'Effective', emotion: 'Calm', triggerTag: '食事', context: '見通しが立ち安心した様子', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/7 ---
CREATE (log:SupportLog {date: date('2026-03-07'), situation: '他者交流', action: '集団活動に参加', effectiveness: 'Effective', emotion: 'Joy', triggerTag: '他者交流', context: '仲の良い利用者と楽しそうに活動', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '田中'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/8 ---
CREATE (log:SupportLog {date: date('2026-03-08'), situation: '作業', action: '折り紙の作業', effectiveness: 'Effective', emotion: 'Calm', triggerTag: '作業中', context: '集中して取り組めた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/9 ---
CREATE (log:SupportLog {date: date('2026-03-09'), situation: '食事', action: '好きなメニューで満足そう', effectiveness: 'Effective', emotion: 'Joy', triggerTag: '食事', context: 'カレーライスの日', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/10 ---
CREATE (log:SupportLog {date: date('2026-03-10'), situation: '作業', action: 'ビーズ作業に慣れてきた', effectiveness: 'Effective', emotion: 'Calm', triggerTag: '作業中', context: '手順を覚えて自分から取り組む', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '田中'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/11 ---
CREATE (log:SupportLog {date: date('2026-03-11'), situation: '入浴', action: '入浴後にリラックス', effectiveness: 'Effective', emotion: 'Calm', triggerTag: '入浴', context: '温かいお湯でリラックスしていた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/12 ---
CREATE (log:SupportLog {date: date('2026-03-12'), situation: '他者交流', action: '少人数で活動', effectiveness: 'Effective', emotion: 'Joy', triggerTag: '他者交流', context: '3人のグループで笑顔が見られた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '田中'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/13 ---
CREATE (log:SupportLog {date: date('2026-03-13'), situation: '散歩', action: '買い物に同行', effectiveness: 'Effective', emotion: 'Joy', triggerTag: '外出', context: 'コンビニでおやつを選んで嬉しそう', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/14 ---
CREATE (log:SupportLog {date: date('2026-03-14'), situation: '作業', action: '折り紙の作品を完成', effectiveness: 'Effective', emotion: 'Joy', triggerTag: '作業中', context: '完成品を誇らしげに見せてくれた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 悪化期間: 3/15 〜 3/30 (ドリフト・連鎖検出対象)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// シナリオ: 隣のフロアで工事が始まり、騒音ストレスが蓄積。
// 作業中のイライラが増加し、食事・他者交流にも波及。

// --- 3/15 ---
CREATE (log:SupportLog {date: date('2026-03-15'), situation: '作業', action: '作業に集中できず中断', effectiveness: 'Ineffective', emotion: 'Anger', triggerTag: '作業中', context: '隣のフロアの工事音が響いていた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/16 ---
CREATE (log:SupportLog {date: date('2026-03-16'), situation: '作業', action: '別室に移動して作業', effectiveness: 'Effective', emotion: 'Calm', triggerTag: '作業中', context: '静かな部屋で落ち着いて取り組めた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/17 ---
CREATE (log:SupportLog {date: date('2026-03-17'), situation: '食事', action: '食事中に立ち上がって歩き回る', effectiveness: 'Ineffective', emotion: 'Anxiety', triggerTag: '食事', context: '食堂にも工事の振動が伝わっていた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '田中'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/18 ---
CREATE (log:SupportLog {date: date('2026-03-18'), situation: '作業', action: '大声を上げて作業道具を投げた', effectiveness: 'Ineffective', emotion: 'Anger', triggerTag: '作業中', context: '工事のドリル音が突然鳴り始めた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/19 ---
CREATE (log:SupportLog {date: date('2026-03-19'), situation: '作業', action: '別室に移動して作業', effectiveness: 'Effective', emotion: 'Calm', triggerTag: '作業中', context: '別室移動後は落ち着いた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/20 ---
CREATE (log:SupportLog {date: date('2026-03-20'), situation: '他者交流', action: '他利用者を押しのけた', effectiveness: 'Ineffective', emotion: 'Anger', triggerTag: '他者交流', context: '順番待ちでイライラ、前日からの不穏が残っている様子', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '田中'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/21 ---
CREATE (log:SupportLog {date: date('2026-03-21'), situation: '食事', action: '食事を途中で残して離席', effectiveness: 'Ineffective', emotion: 'Sadness', triggerTag: '食事', context: '元気がなく食欲も低下している印象', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/22 ---
CREATE (log:SupportLog {date: date('2026-03-22'), situation: '作業', action: '作業拒否、部屋の隅に座り込む', effectiveness: 'Ineffective', emotion: 'Sadness', triggerTag: '作業中', context: '声かけにも反応が薄い。睡眠不足の可能性', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '田中'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/23 ---
CREATE (log:SupportLog {date: date('2026-03-23'), situation: '入浴', action: '入浴拒否', effectiveness: 'Ineffective', emotion: 'Anger', triggerTag: '入浴', context: '脱衣所で大声を出し拒否。無理強いせず別日に', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/24 ---
CREATE (log:SupportLog {date: date('2026-03-24'), situation: '作業', action: '別室に移動して少量の作業', effectiveness: 'Effective', emotion: 'Calm', triggerTag: '作業中', context: '別室で短時間の作業なら取り組めた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/25 ---
CREATE (log:SupportLog {date: date('2026-03-25'), situation: '作業', action: '大きな音で手を耳に当てる', effectiveness: 'Ineffective', emotion: 'Fear', triggerTag: '作業中', context: '工事の破砕音が特に大きかった', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '田中'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/26 ---
CREATE (log:SupportLog {date: date('2026-03-26'), situation: '他者交流', action: '集団活動に参加できず', effectiveness: 'Ineffective', emotion: 'Anxiety', triggerTag: '他者交流', context: '他利用者の声にも過敏になっている', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/27 ---
CREATE (log:SupportLog {date: date('2026-03-27'), situation: '食事', action: '個室で食事を提供', effectiveness: 'Effective', emotion: 'Calm', triggerTag: '食事', context: '静かな環境では落ち着いて食べられた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/28 ---
CREATE (log:SupportLog {date: date('2026-03-28'), situation: '作業', action: '別室に移動して作業', effectiveness: 'Effective', emotion: 'Calm', triggerTag: '作業中', context: '別室移動のルーティンが定着してきた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/29 ---
CREATE (log:SupportLog {date: date('2026-03-29'), situation: '他者交流', action: '1対1の関わりに切り替え', effectiveness: 'Effective', emotion: 'Calm', triggerTag: '他者交流', context: '少人数なら落ち着ける', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '田中'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// --- 3/30 (本日) ---
CREATE (log:SupportLog {date: date('2026-03-30'), situation: '作業', action: '工事音で再びパニック、別室に移動', effectiveness: 'Effective', emotion: 'Anger', triggerTag: '作業中', context: '午前中の工事再開でパニック。別室移動後は落ち着いた', isSimulation: true})
WITH log MATCH (c:Client {name: '山本翔太'}), (s:Supporter {name: '鈴木'})
CREATE (s)-[:LOGGED]->(log)-[:ABOUT]->(c);

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 期待されるアラート検証
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//
// 1. Emotion Drift (感情の波):
//    - 「作業中」タグ:
//      Baseline (3/1-3/14): 5件中1件 Anxiety = 20% ネガティブ
//      Recent (3/24-3/30):  4件中2件 Anger/Fear = 50% ネガティブ
//      → Drift = +150% → severity: high
//
// 2. Cascading Risk (連鎖):
//    - 直近3日 (3/28-3/30) に「作業中」「他者交流」で
//      Anger/Calm が混在 → 連鎖判定はギリギリ
//    - 直近7日 (3/24-3/30) だと「作業中」「他者交流」「食事」の
//      3タグにまたがる → 連鎖あり
//
// 3. Care Pattern Discovery:
//    - 「別室に移動して作業」が4回 Effective
//      → CarePreference 昇格提案
//    - 「個室で食事を提供」が1回 → 回数不足で提案なし
//
// 4. Staff SOS:
//    - 鈴木: 全20件中ネガティブ8件 = 40% → 閾値50%未満
//    - 田中: 全10件中ネガティブ5件 = 50% → 閾値ギリギリ
//
// 検証コマンド:
//   uv run python -c "
//   from lib.insight_engine import generate_risk_assessment
//   import json
//   result = generate_risk_assessment('山本翔太')
//   print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
//   "
