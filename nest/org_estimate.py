"""担当機関の推定（N-24a。ADR-001 D3）。機関の名前が無い言及（「区役所の窓口で」）の候補を、本人の住所の区で絞る。読むだけ。

- 住所の区（Residence.areaCode）は個人の側から読む。過去の言及は当時の住所。当時の住所が無い・言及の時期が分からないときは
  今の住所で推定し、その旨を notes に書く。区が分からなければ候補を出さない（機関未確定）
- 候補は資源の側で、その区（と PART_OF の上の市）を SERVES で担当する、相談窓口の種類の機関。担当の根拠（servesBasis）を
  添え、格上げしない（tsunagu-net BRS-23）。点数づけをしない
- 推定の結果に区コード・住所を入れない。Claude に渡すのは for_claude の {orgId, name} だけ
- 窓口（Window）までは絞らない。window はいつも None（機関の単位で止める。間違った窓口を確定させない）
- 選ぶのは Claude（確度 Inference の案）、確定するのは職員の承認（N-21）
"""
CONSULTATION_KINDS = (
    "DisabilityDivision", "ElderlyDivision", "CommunityGeneralSupportCenter", "HardshipSupportDesk",
    "WelfareOffice", "BasicConsultationCenter", "CareInsuranceDivision", "MentalHealthDesk",
)
RESIDENCES = """MATCH (c:Client {clientId: $id})-[:RESIDES_AT]->(r:Residence {status: 'Active'})
RETURN r.areaCode AS areaCode, toString(r.since) AS since, toString(r.until) AS until"""
BY_AREA = """MATCH (a:Area {areaCode: $code})-[:PART_OF*0..2]->(x:Area)<-[r:SERVES]-(o:Organization {status: 'Active'})
WHERE o.kind IN $kinds
RETURN DISTINCT o.orgId AS orgId, o.name AS name, o.kind AS kind, r.basis AS servesBasis,
       coalesce(r.partOfArea, false) AS partOfArea, x.areaCode <> $code AS viaParent
ORDER BY viaParent, name, orgId"""
FOR_CLAUDE = ("orgId", "name")


def by_area(driver, code, limit=30, database="neo4j"):
    with driver.session(database=database) as s:
        def work(tx):
            out = []
            for record in tx.run(BY_AREA, code=code, kinds=list(CONSULTATION_KINDS)):
                out.append(dict(record))
                if len(out) > limit:
                    break
            return out
        rows = s.execute_read(work)
    return {"candidates": rows[:limit], "truncated": len(rows) > limit}


def residence_for(residences, about_date):
    """推定に使う区。返り値 {areaCode, basis（AtTheTime／CurrentFallback／None）, notes}。"""
    notes = []
    if about_date:
        at = [r for r in residences if r.get("since") and r["since"] <= about_date
              and (not r.get("until") or about_date < r["until"])]
        if len(at) == 1 and at[0].get("areaCode"):
            return {"areaCode": at[0]["areaCode"], "basis": "AtTheTime", "notes": []}
        notes.append("言及の当時（%s）の住所が記録に無いので、今の住所で推定した" % about_date)
    else:
        notes.append("言及の時期が分からないので、今の住所で推定した")
    current = [r for r in residences if not r.get("until")]
    if len(current) == 1 and current[0].get("areaCode"):
        return {"areaCode": current[0]["areaCode"], "basis": "CurrentFallback", "notes": notes}
    return {"areaCode": None, "basis": None,
            "notes": ["住所の区が分からない（今の住所が無い・二つある・区が出ていない）。機関は未確定のまま"]}


def estimate(personal_driver, resource_driver, client_id, about_date=None):
    rows = [dict(r) for r in personal_driver.execute_query(RESIDENCES, {"id": client_id}).records]
    res = residence_for(rows, about_date)
    out = {"basis": res["basis"], "notes": res["notes"], "candidates": [], "truncated": False, "window": None, "chosen": None}
    if res["areaCode"]:
        found = by_area(resource_driver, res["areaCode"])
        out.update(candidates=found["candidates"], truncated=found["truncated"])
        if not found["candidates"]:
            out["notes"] = out["notes"] + ["区の担当の機関が資源の側に無い。機関は未確定のまま"]
    return out


def for_claude(est):
    return [{k: c[k] for k in FOR_CLAUDE} for c in est["candidates"]]
