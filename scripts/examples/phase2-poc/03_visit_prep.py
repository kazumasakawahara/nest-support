"""Phase 2 finale: visit-prep Skill の Cypher を実行し、ブリーフィングシートを生成する。"""
from datetime import date
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")

CLIENT = "テスト太郎"
VISIT_DATE = "2026-04-18"
VISIT_PURPOSE = "定期モニタリング訪問（月次）"


Q_SAFETY = """
MATCH (c:Client) WHERE c.name CONTAINS $clientName
OPTIONAL MATCH (c)-[:MUST_AVOID|PROHIBITED]->(ng:NgAction)
OPTIONAL MATCH (ng)-[:IN_CONTEXT|RELATES_TO]->(ngCon:Condition)
OPTIONAL MATCH (c)-[:REQUIRES|PREFERS]->(cp:CarePreference)
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(con:Condition)
RETURN c.name AS name, c.dob AS dob, c.bloodType AS blood,
    collect(DISTINCT {action:ng.action, reason:ng.reason, riskLevel:ng.riskLevel, context:ngCon.name}) AS ngs,
    collect(DISTINCT {category:cp.category, instruction:cp.instruction, priority:cp.priority}) AS cps,
    collect(DISTINCT {name:con.name, status:con.status}) AS conds
"""

Q_CONTACT = """
MATCH (c:Client)-[kpRel:HAS_KEY_PERSON|EMERGENCY_CONTACT]->(kp:KeyPerson)
WHERE c.name CONTAINS $clientName
OPTIONAL MATCH (c2:Client)-[:TREATED_AT]->(hosp:Hospital) WHERE c2.name CONTAINS $clientName
RETURN
    collect(DISTINCT {rank:kpRel.rank, name:kp.name, relationship:kp.relationship, phone:kp.phone, role:kp.role}) AS kps,
    collect(DISTINCT {name:hosp.name, specialty:hosp.specialty, phone:hosp.phone, doctor:hosp.doctor}) AS hosps
"""

Q_LOGS = """
MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c:Client)
WHERE c.name CONTAINS $clientName
RETURN log.date AS date, s.name AS supporter, log.situation AS sit,
       log.action AS action, log.effectiveness AS eff, log.note AS note
ORDER BY log.date DESC LIMIT 5
"""

Q_PATTERNS = """
MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c:Client)
WHERE c.name CONTAINS $clientName
  AND (toLower(toString(log.effectiveness)) STARTS WITH 'effective'
       OR toLower(toString(log.effectiveness)) STARTS WITH 'excellent'
       OR toString(log.effectiveness) CONTAINS '効果')
WITH log.action AS action, count(*) AS c, collect(DISTINCT log.situation) AS sits
WHERE c >= 2
RETURN action, c, sits ORDER BY c DESC
"""

Q_RENEWAL = """
MATCH (c:Client)-[:HAS_CERTIFICATE]->(cert:Certificate)
WHERE c.name CONTAINS $clientName AND cert.nextRenewalDate IS NOT NULL
WITH cert, duration.inDays(date(), cert.nextRenewalDate).days AS days
WHERE days <= 90 AND days >= 0
RETURN cert.type AS type, cert.grade AS grade, cert.nextRenewalDate AS next, days AS days
ORDER BY days ASC
"""


def clean(items):
    return [x for x in items if any(v not in (None, "", []) for v in x.values())]


RISK_ORDER = {"LifeThreatening": 0, "Panic": 1, "Discomfort": 2}


def main():
    d = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with d.session() as s:
            safety = s.run(Q_SAFETY, clientName=CLIENT).single()
            contact = s.run(Q_CONTACT, clientName=CLIENT).single()
            logs = list(s.run(Q_LOGS, clientName=CLIENT))
            patterns = list(s.run(Q_PATTERNS, clientName=CLIENT))
            renewals = list(s.run(Q_RENEWAL, clientName=CLIENT))

        # Render the briefing sheet
        lines: list[str] = []
        p = lines.append
        age = ""
        if safety["dob"]:
            today = date.today()
            dob = safety["dob"]
            age = f"（{today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))}歳）"
        p("━" * 66)
        p("# 訪問前ブリーフィング")
        p("━" * 66)
        p(f"**対象:** {safety['name']}{age}")
        p(f"**訪問日:** {VISIT_DATE}")
        p(f"**訪問目的:** {VISIT_PURPOSE}")
        p("")

        ngs = sorted(clean(safety["ngs"]), key=lambda x: RISK_ORDER.get(x["riskLevel"], 9))
        p("## 🚫 絶対に避けること（NgAction — 最優先）")
        if ngs:
            for n in ngs:
                ctx = f" / 関連: {n['context']}" if n["context"] else ""
                p(f"- 🔴 **[{n['riskLevel']}]** {n['action']}")
                p(f"    └ 理由: {n['reason']}{ctx}")
        else:
            p("- （登録なし）")
        p("")

        p("## 💚 効果的な関わり方（CarePreference）")
        cps = sorted(clean(safety["cps"]), key=lambda x: {"High":0,"Medium":1,"Low":2}.get(x["priority"],9))
        if cps:
            for cp in cps:
                p(f"- **[{cp['priority']}][{cp['category']}]** {cp['instruction']}")
        else:
            p("- （登録なし）")
        if patterns:
            p("")
            p("### 📈 効果実証済みパターン（2回以上 Effective）")
            for r in patterns:
                p(f"- 「{r['action']}」× {r['c']}回 (状況: {', '.join(r['sits'])})")
        else:
            p("- （繰り返しパターンはまだ蓄積されていません — 記録数 < 2）")
        p("")

        p("## 🩺 特性・診断")
        for c in clean(safety["conds"]):
            p(f"- {c['name']} ({c['status']})")
        p("")

        p("## 🚨 緊急時の連絡先")
        kps = sorted(clean(contact["kps"]), key=lambda x: x["rank"] or 99)
        for kp in kps:
            phone = kp["phone"] or "（電話未登録）"
            p(f"{kp['rank']}. {kp['name']}（{kp['relationship']}）TEL: {phone}")
            p(f"    役割: {kp['role']}")
        for h in clean(contact["hosps"]):
            phone = h["phone"] or "（電話未登録）"
            p(f"   かかりつけ: {h['name']}（{h['specialty']} 担当:{h['doctor']}）TEL: {phone}")
        p("")

        p("## 📝 前回からの申し送り（直近支援記録 上位5件）")
        if logs:
            for log in logs:
                p(f"- [{log['date']}] {log['supporter']} / 効果: {log['eff']}")
                p(f"    状況: {log['sit']}")
                p(f"    対応: {log['action']}")
                if log["note"]:
                    p(f"    メモ: {log['note']}")
        else:
            p("- （記録なし）")
        p("")

        p("## ⏰ 確認すべき更新期限（90日以内）")
        if renewals:
            for r in renewals:
                flag = "🔴" if r["days"] <= 30 else ("🟡" if r["days"] <= 60 else "🟢")
                p(f"- {flag} {r['type']} {r['grade']} — 期限 {r['next']} / 残り {r['days']}日")
        else:
            p("- （90日以内に期限切れを迎える手帳・証明書はありません）")
        p("")
        p("━" * 66)

        print("\n".join(lines))
    finally:
        d.close()


if __name__ == "__main__":
    main()
