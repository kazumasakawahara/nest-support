"""担当機関の推定（N-24a。ADR-001 D3）。機関の名前が無い言及（「区役所の窓口で」）の候補を、本人の住所の区で絞る。読むだけ。

- 住所の区（Residence.areaCode）は個人の側から読む。過去の言及は当時の住所。当時の住所が無い・言及の時期が分からないときは
  今の住所で推定し、その旨を notes に書く。区が分からなければ候補を出さない（機関未確定）
- 候補は資源の側で、その区（と PART_OF の上の市）を SERVES で担当する、相談窓口の種類の機関。種類はいつもの 7 つに、
  言及の時期の本人の年齢で足す（65 歳以上・18 歳未満。生年月日が無い・幅があって決まらないときは両方を出して注記する）。担当の根拠（servesBasis）を
  添え、格上げしない（tsunagu-net BRS-23）。点数づけをしない
- 推定の結果に区コード・住所を入れない。Claude に渡すのは for_claude の {orgId, name} だけ
- 窓口（Window）までは絞らない。window はいつも None（機関の単位で止める。間違った窓口を確定させない）
- 選ぶのは Claude（確度 Inference の案）、確定するのは職員の承認（N-21）
"""
import calendar
from datetime import date, timedelta

# 候補の種類（2026-11-05 河原さんの決定。台帳 G-57。docs/SEMANTICS.md SEM-AREA-03・05）。値は tsunagu-net の orgKind（ENU-14）
ALWAYS_KINDS = (
    "DisabilityDivision", "HardshipSupportDesk", "WelfareOffice", "BasicConsultationCenter", "MentalHealthDesk",
    "SocialWelfareCouncil", "GuardianshipCenter",
)
AGE_65_KINDS = ("ElderlyDivision", "CommunityGeneralSupportCenter")   # 65 歳以上（介護保険法 9 条 1 号の第 1 号被保険者）
UNDER_18_KINDS = ("ChildFamilyCenter",)                                # 18 歳未満（児童福祉法 4 条 1 項の児童）
CONSULTATION_KINDS = ALWAYS_KINDS + AGE_65_KINDS + UNDER_18_KINDS
BIRTH = "MATCH (c:Client {clientId: $id}) RETURN toString(c.birthDate) AS birthDate, c.birthDatePrecision AS birthDatePrecision"
RESIDENCES = """MATCH (c:Client {clientId: $id})-[:RESIDES_AT]->(r:Residence {status: 'Active'})
RETURN r.areaCode AS areaCode, toString(r.since) AS since, toString(r.until) AS until"""
BY_AREA = """MATCH (a:Area {areaCode: $code})-[:PART_OF*0..2]->(x:Area)<-[r:SERVES]-(o:Organization {status: 'Active'})
WHERE o.kind IN $kinds
RETURN DISTINCT o.orgId AS orgId, o.name AS name, o.kind AS kind, r.basis AS servesBasis,
       coalesce(r.partOfArea, false) AS partOfArea, x.areaCode <> $code AS viaParent
ORDER BY viaParent, name, orgId"""
FOR_CLAUDE = ("orgId", "name")


def _reached(age, birth, on):
    """満 age 歳に達したか。誕生日の前日に達する（年齢計算ニ関スル法律による民法 143 条の準用）。応当日が無い（2 月 29 日）年は 3 月 1 日の前日"""
    try:
        anniversary = birth.replace(year=birth.year + age)
    except ValueError:
        anniversary = date(birth.year + age, 3, 1)
    return on >= anniversary - timedelta(days=1)


def _birth_range(birth, precision):
    """生年月日の幅（いちばん早い日・いちばん遅い日）。記録が無ければ None。精度が無ければ日まで分かっているものとして読む"""
    if not birth or precision == "Unknown":
        return None
    b = date.fromisoformat(str(birth)[:10])
    if precision == "Year":
        return date(b.year, 1, 1), date(b.year, 12, 31)
    if precision == "Month":
        return date(b.year, b.month, 1), date(b.year, b.month, calendar.monthrange(b.year, b.month)[1])
    return b, b


def kinds_for(birth, precision, on):
    """本人の年齢で候補の種類を決める（決まった規則。AI を使わない）。返り値 (種類, 注記)。生年月日は返さない"""
    rng = _birth_range(birth, precision)
    if rng is None:
        return ALWAYS_KINDS + AGE_65_KINDS + UNDER_18_KINDS, [
            "年齢の記録なし。65 歳以上の窓口と 18 歳未満の窓口の両方を候補に出した"]
    earliest, latest = rng
    kinds, notes = list(ALWAYS_KINDS), []
    if _reached(65, latest, on):
        kinds += AGE_65_KINDS
    elif _reached(65, earliest, on):
        kinds += AGE_65_KINDS
        notes.append("生年月日が年か年月までで、65 歳の前後が決まらない。65 歳以上の窓口も候補に出した")
    if not _reached(18, earliest, on):
        kinds += UNDER_18_KINDS
    elif not _reached(18, latest, on):
        kinds += UNDER_18_KINDS
        notes.append("生年月日が年か年月までで、18 歳の前後が決まらない。18 歳未満の窓口も候補に出した")
    return tuple(kinds), notes


def by_area(driver, code, kinds=ALWAYS_KINDS, limit=30, database="neo4j"):
    with driver.session(database=database) as s:
        def work(tx):
            out = []
            for record in tx.run(BY_AREA, code=code, kinds=list(kinds)):
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


def estimate(personal_driver, resource_driver, client_id, about_date=None, today=None):
    rows = [dict(r) for r in personal_driver.execute_query(RESIDENCES, {"id": client_id}).records]
    res = residence_for(rows, about_date)
    out = {"basis": res["basis"], "notes": res["notes"], "candidates": [], "truncated": False, "window": None, "chosen": None}
    if res["areaCode"]:
        born = (personal_driver.execute_query(BIRTH, {"id": client_id}).records or [{}])[0]
        on = date.fromisoformat(about_date) if about_date else (today or date.today())
        kinds, age_notes = kinds_for(born.get("birthDate"), born.get("birthDatePrecision"), on)
        out["notes"] = out["notes"] + age_notes
        found = by_area(resource_driver, res["areaCode"], kinds=kinds)
        out.update(candidates=found["candidates"], truncated=found["truncated"])
        if not found["candidates"]:
            out["notes"] = out["notes"] + ["区の担当の機関が資源の側に無い。機関は未確定のまま"]
    return out


def for_claude(est):
    return [{k: c[k] for k in FOR_CLAUDE} for c in est["candidates"]]
