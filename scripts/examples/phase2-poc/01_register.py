"""Phase 2 concept-verification: narrative → structured → Neo4j register.

This script replays the Cypher templates defined in
claude-skills/narrative-extractor/SKILL.md, using the same parametrised
queries that the neo4j MCP would execute. One-off use for the Phase 2 demo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")

DATA = {
    "client": {
        "name": "テスト太郎",
        "dob": None,
        "bloodType": None,
        "kana": None,
        "aliases": ["太郎"],
    },
    "conditions": [
        {"name": "知的障害（中度）", "status": "Active"},
        {"name": "自閉スペクトラム症", "status": "Active"},
    ],
    "ngActions": [
        {
            "action": "救急車のサイレンや花火など大きな音を聞かせる",
            "reason": "パニックとなり頭を壁に打ちつける自傷行動に繋がる",
            "riskLevel": "LifeThreatening",
            "relatedCondition": "自閉スペクトラム症",
        },
        {
            "action": "エビ・カニを含む食品を提供する",
            "reason": "食物アレルギーで過去に誤食により救急搬送歴あり",
            "riskLevel": "LifeThreatening",
            "relatedCondition": None,
        },
    ],
    "carePreferences": [
        {
            "category": "移動",
            "instruction": "毎朝7時の散歩を欠かさない",
            "priority": "High",
            "relatedCondition": "自閉スペクトラム症",
        },
        {
            "category": "睡眠",
            "instruction": "夕方に鉄道図鑑を読む時間を確保する（これが無いと夜眠れなくなる）",
            "priority": "High",
            "relatedCondition": "自閉スペクトラム症",
        },
    ],
    "supportLogs": [
        {
            "date": "2026-04-17",
            "supporter": "山本美保",
            "situation": "自宅訪問。母より太郎の状態と生活ルーチンの聴き取り",
            "action": "面談（1時間半）、禁忌事項・推奨ケア・緊急連絡先・通院情報を確認",
            "effectiveness": "Effective",
            "note": "母の介護負担が増している。将来の後見制度検討が必要。",
        }
    ],
    "certificates": [
        {"type": "療育手帳", "grade": "B1", "nextRenewalDate": None},
        {"type": "精神障害者保健福祉手帳", "grade": "2級", "nextRenewalDate": None},
    ],
    "keyPersons": [
        {
            "name": "佐藤花子",
            "relationship": "母",
            "phone": None,
            "role": "緊急連絡先（最優先）",
            "rank": 1,
        },
        {
            "name": "佐藤太一",
            "relationship": "父",
            "phone": None,
            "role": "緊急連絡先",
            "rank": 2,
        },
        {
            "name": "佐藤次郎",
            "relationship": "弟",
            "phone": None,
            "role": "緊急連絡先（母父が不在時）",
            "rank": 3,
        },
    ],
    "hospitals": [
        {
            "name": "博多総合病院",
            "specialty": "精神科",
            "phone": None,
            "doctor": "山田医師",
        }
    ],
    "wishes": [{"content": "鉄道の仕事に関わりたい", "date": "2026-04-17"}],
}

USER = "narrative-extractor (Phase2 demo)"


def uniqueness_check(tx, name: str) -> int:
    rec = tx.run("MATCH (c:Client {name:$n}) RETURN count(c) AS c", n=name).single()
    return rec["c"]


def register(tx, data: dict) -> list[str]:
    audit_lines: list[str] = []
    c = data["client"]

    # 1. Client (MERGE by name; dob unknown so uniqueness only by name here)
    tx.run(
        """
        MERGE (c:Client {name:$name})
        SET c.dob = CASE WHEN $dob IS NOT NULL THEN date($dob) ELSE c.dob END,
            c.bloodType = COALESCE($blood, c.bloodType),
            c.kana = COALESCE($kana, c.kana),
            c.aliases = $aliases
        """,
        name=c["name"],
        dob=c["dob"],
        blood=c["bloodType"],
        kana=c["kana"],
        aliases=c["aliases"],
    )
    audit_lines.append(f"Client:{c['name']}")

    # 2. Conditions
    for cond in data["conditions"]:
        tx.run(
            """
            MATCH (c:Client {name:$client})
            MERGE (con:Condition {name:$name})
            SET con.status = $status
            MERGE (c)-[:HAS_CONDITION]->(con)
            """,
            client=c["name"],
            name=cond["name"],
            status=cond["status"],
        )
        audit_lines.append(f"Condition:{cond['name']}")

    # 3. NgActions (with optional IN_CONTEXT to related Condition)
    for ng in data["ngActions"]:
        tx.run(
            """
            MATCH (c:Client {name:$client})
            CREATE (ng:NgAction {action:$action, reason:$reason, riskLevel:$risk})
            CREATE (c)-[:MUST_AVOID]->(ng)
            WITH ng
            OPTIONAL MATCH (con:Condition {name:$cond})
            FOREACH (_ IN CASE WHEN con IS NOT NULL THEN [1] ELSE [] END |
                CREATE (ng)-[:IN_CONTEXT]->(con))
            """,
            client=c["name"],
            action=ng["action"],
            reason=ng["reason"],
            risk=ng["riskLevel"],
            cond=ng["relatedCondition"],
        )
        audit_lines.append(f"NgAction({ng['riskLevel']}):{ng['action'][:20]}…")

    # 4. CarePreferences
    for cp in data["carePreferences"]:
        tx.run(
            """
            MATCH (c:Client {name:$client})
            CREATE (cp:CarePreference {category:$cat, instruction:$inst, priority:$pri})
            CREATE (c)-[:REQUIRES]->(cp)
            WITH cp
            OPTIONAL MATCH (con:Condition {name:$cond})
            FOREACH (_ IN CASE WHEN con IS NOT NULL THEN [1] ELSE [] END |
                CREATE (cp)-[:IN_CONTEXT]->(con))
            """,
            client=c["name"],
            cat=cp["category"],
            inst=cp["instruction"],
            pri=cp["priority"],
            cond=cp.get("relatedCondition"),
        )
        audit_lines.append(f"CarePreference:{cp['category']}")

    # 5. Certificates
    for cert in data["certificates"]:
        tx.run(
            """
            MATCH (c:Client {name:$client})
            CREATE (cert:Certificate {
                type:$type, grade:$grade,
                nextRenewalDate: CASE WHEN $renewal IS NOT NULL THEN date($renewal) ELSE null END,
                status: 'Active'
            })
            CREATE (c)-[:HAS_CERTIFICATE]->(cert)
            """,
            client=c["name"],
            type=cert["type"],
            grade=cert["grade"],
            renewal=cert["nextRenewalDate"],
        )
        audit_lines.append(f"Certificate:{cert['type']} {cert['grade']}")

    # 6. KeyPersons with rank
    for kp in data["keyPersons"]:
        tx.run(
            """
            MATCH (c:Client {name:$client})
            MERGE (kp:KeyPerson {name:$name})
            SET kp.phone = COALESCE($phone, kp.phone),
                kp.relationship = $rel,
                kp.role = $role
            MERGE (c)-[r:HAS_KEY_PERSON]->(kp)
            SET r.rank = $rank
            """,
            client=c["name"],
            name=kp["name"],
            phone=kp["phone"],
            rel=kp["relationship"],
            role=kp["role"],
            rank=kp["rank"],
        )
        audit_lines.append(f"KeyPerson(rank{kp['rank']}):{kp['name']}")

    # 7. Hospitals
    for h in data["hospitals"]:
        tx.run(
            """
            MATCH (c:Client {name:$client})
            MERGE (h:Hospital {name:$name})
            SET h.specialty = $spec, h.phone = $phone, h.doctor = $doc
            MERGE (c)-[:TREATED_AT]->(h)
            """,
            client=c["name"],
            name=h["name"],
            spec=h["specialty"],
            phone=h["phone"],
            doc=h["doctor"],
        )
        audit_lines.append(f"Hospital:{h['name']}")

    # 8. Wishes
    for w in data["wishes"]:
        tx.run(
            """
            MATCH (c:Client {name:$client})
            CREATE (wi:Wish {content:$content, status:'Active', date:date($date)})
            CREATE (c)-[:HAS_WISH]->(wi)
            """,
            client=c["name"],
            content=w["content"],
            date=w["date"],
        )
        audit_lines.append(f"Wish:{w['content'][:20]}…")

    # 9. Supporter + SupportLog
    for log in data["supportLogs"]:
        tx.run(
            """
            MERGE (s:Supporter {name:$supporter})
            WITH s
            MATCH (c:Client {name:$client})
            CREATE (lg:SupportLog {
                date: date($date),
                situation: $situation,
                action: $action,
                effectiveness: $effectiveness,
                note: $note
            })
            CREATE (s)-[:LOGGED]->(lg)-[:ABOUT]->(c)
            """,
            supporter=log["supporter"],
            client=c["name"],
            date=log["date"],
            situation=log["situation"],
            action=log["action"],
            effectiveness=log["effectiveness"],
            note=log["note"],
        )
        audit_lines.append(f"SupportLog:{log['date']}")

    # 10. AuditLog (single, summarising)
    tx.run(
        """
        MATCH (c:Client {name:$client})
        CREATE (al:AuditLog {
            timestamp: datetime(),
            user: $user,
            action: 'CREATE',
            targetType: 'Client+RelatedEntities',
            targetName: $client,
            details: $details,
            clientName: $client
        })
        CREATE (al)-[:AUDIT_FOR]->(c)
        """,
        client=c["name"],
        user=USER,
        details=" | ".join(audit_lines),
    )

    return audit_lines


def main() -> int:
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session() as s:
            existing = s.execute_read(uniqueness_check, DATA["client"]["name"])
            if existing > 0:
                print(f"⚠️ Client '{DATA['client']['name']}' already exists ({existing} node(s)). Aborting to avoid duplicate.")
                return 1
            print(f"✅ uniqueness check passed (0 existing '{DATA['client']['name']}')")

            audit = s.execute_write(register, DATA)
            print("\n=== 登録完了（AuditLog 詳細） ===")
            for line in audit:
                print("  •", line)
            print(f"\n合計 {len(audit)} エンティティを登録しました。")
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
