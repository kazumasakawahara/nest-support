"""Phase 2 verification: run the neo4j-support-db Skill's read templates."""
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")

TEMPLATE_2_PROFILE = """
MATCH (c:Client)
WHERE c.name CONTAINS $clientName
OPTIONAL MATCH (c)-[:HAS_HISTORY]->(h:LifeHistory)
OPTIONAL MATCH (c)-[:HAS_WISH]->(w:Wish)
OPTIONAL MATCH (c)-[:HAS_CONDITION]->(con:Condition)
OPTIONAL MATCH (c)-[:REQUIRES]->(cp:CarePreference)
OPTIONAL MATCH (c)-[:MUST_AVOID]->(ng:NgAction)
OPTIONAL MATCH (c)-[:HAS_CERTIFICATE]->(cert:Certificate)
OPTIONAL MATCH (c)-[:RECEIVES]->(pa:PublicAssistance)
OPTIONAL MATCH (c)-[kpRel:HAS_KEY_PERSON]->(kp:KeyPerson)
OPTIONAL MATCH (c)-[:HAS_LEGAL_REP]->(g:Guardian)
OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(s:Supporter)
OPTIONAL MATCH (c)-[:TREATED_AT]->(hosp:Hospital)
RETURN
    c.name AS name, c.dob AS dob, c.bloodType AS blood, c.aliases AS aliases,
    collect(DISTINCT {era:h.era, episode:h.episode}) AS histories,
    collect(DISTINCT {content:w.content, status:w.status}) AS wishes,
    collect(DISTINCT {name:con.name, status:con.status}) AS conditions,
    collect(DISTINCT {category:cp.category, instruction:cp.instruction, priority:cp.priority}) AS cares,
    collect(DISTINCT {action:ng.action, reason:ng.reason, riskLevel:ng.riskLevel}) AS ngs,
    collect(DISTINCT {type:cert.type, grade:cert.grade, next:cert.nextRenewalDate}) AS certs,
    collect(DISTINCT {rank:kpRel.rank, name:kp.name, relationship:kp.relationship, phone:kp.phone, role:kp.role}) AS kps,
    collect(DISTINCT {name:g.name, type:g.type}) AS guardians,
    collect(DISTINCT {name:s.name, role:s.role}) AS supporters,
    collect(DISTINCT {name:hosp.name, specialty:hosp.specialty, doctor:hosp.doctor}) AS hospitals
"""

TEMPLATE_5_SUPPORTLOG = """
MATCH (s:Supporter)-[:LOGGED]->(log:SupportLog)-[:ABOUT]->(c:Client)
WHERE c.name CONTAINS $clientName
RETURN log.date AS date, s.name AS supporter, log.situation AS sit,
       log.action AS action, log.effectiveness AS eff, log.note AS note
ORDER BY log.date DESC LIMIT 10
"""

TEMPLATE_7_AUDIT = """
MATCH (al:AuditLog)
WHERE al.clientName CONTAINS $clientName
RETURN al.timestamp AS ts, al.user AS user, al.action AS action,
       al.targetType AS ttype, al.targetName AS tname, al.details AS details
ORDER BY al.timestamp DESC LIMIT 5
"""

def _clean(items):
    return [x for x in items if any(v not in (None, "", []) for v in x.values())]

def main():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session() as s:
            rec = s.run(TEMPLATE_2_PROFILE, clientName="テスト太郎").single()
            if not rec or not rec["name"]:
                print("Not found")
                return
            print("━" * 60)
            print(f"【基本情報】{rec['name']}  /  dob: {rec['dob']}  /  blood: {rec['blood']}  /  aliases: {rec['aliases']}")
            print("━" * 60)

            ngs = sorted(_clean(rec["ngs"]), key=lambda x: {"LifeThreatening":0,"Panic":1,"Discomfort":2}.get(x["riskLevel"],9))
            print("\n🚫【第2の柱: 禁忌事項 (NgAction)】 ★最優先★")
            for n in ngs:
                print(f"  🔴 [{n['riskLevel']}] {n['action']}")
                print(f"     理由: {n['reason']}")

            print("\n💚【第2の柱: 推奨ケア (CarePreference)】")
            for cp in _clean(rec["cares"]):
                print(f"  [{cp['priority']}][{cp['category']}] {cp['instruction']}")

            print("\n🩺【第2の柱: 特性・診断】")
            for c in _clean(rec["conditions"]):
                print(f"  • {c['name']} ({c['status']})")

            print("\n🏥【第4の柱: 医療機関】")
            for h in _clean(rec["hospitals"]):
                print(f"  • {h['name']} / {h['specialty']} / 担当: {h['doctor']}")

            print("\n📜【第3の柱: 手帳・受給者証】")
            for c in _clean(rec["certs"]):
                next_ = c["next"] or "未登録"
                print(f"  • {c['type']} {c['grade']} (次回更新: {next_})")

            print("\n👥【第4の柱: キーパーソン】 (rank昇順)")
            kps = sorted(_clean(rec["kps"]), key=lambda x: x["rank"] if x["rank"] is not None else 99)
            for kp in kps:
                print(f"  rank{kp['rank']}: {kp['name']} ({kp['relationship']}) / 役割: {kp['role']}")

            print("\n💭【第1の柱: 願い】")
            for w in _clean(rec["wishes"]):
                print(f"  • {w['content']} ({w['status']})")

            print("\n" + "━" * 60)
            print("📝 Template 5: 支援記録")
            print("━" * 60)
            for r in s.run(TEMPLATE_5_SUPPORTLOG, clientName="テスト太郎"):
                print(f"  [{r['date']}] {r['supporter']} / 効果:{r['eff']}")
                print(f"    状況: {r['sit']}")
                print(f"    対応: {r['action']}")
                print(f"    メモ: {r['note']}")

            print("\n" + "━" * 60)
            print("📋 Template 7: 監査ログ")
            print("━" * 60)
            for r in s.run(TEMPLATE_7_AUDIT, clientName="テスト太郎"):
                print(f"  {r['ts']} / {r['user']} / {r['action']}")
                print(f"    {r['ttype']}: {r['tname']}")
                print(f"    詳細: {r['details']}")
    finally:
        driver.close()

if __name__ == "__main__":
    main()
