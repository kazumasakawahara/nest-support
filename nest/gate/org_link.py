"""関わりを、職員が候補から選んだ資源の側の機関に結ぶ（2026-11-11 河原さん。L-1 の残り）。ゲートの一部。

- 選ぶのは案を出した人。Claude は候補を番号つきで見せて尋ねるだけで、自分で選ばない
- 関わりは未確定（Pending）のまま機関に結ぶ。確定は関わりの承認（review_proposals）
- 止める：関わりが無い／その本人のものでない／未確定でない／すでに機関が結ばれている／名前が根拠の記録の引用に無い／
  機関 ID がその名前の候補（nest.org_candidates.for_involvement）に無い
- 書くのはゲート（write.submit）だけ。機関の写し（Organization {orgId}）と HAS_INVOLVEMENT を作り、AuditLog が残る。
  機関の写しがすでにあれば作り直さない（write の決まり）。資源の側には書かない
"""
import re
import uuid

from nest import ids, org_candidates
from nest.gate import write as gw

FACTS = """MATCH (i:Involvement {involvementId: $id})
OPTIONAL MATCH (i)-[:CONCERNS]->(c:Client {displayCode: $code})
OPTIONAL MATCH (i)-[:EVIDENCED_BY]->(r:Record)
OPTIONAL MATCH (r)-[:ABOUT]->(rc:Client {displayCode: $code})
OPTIONAL MATCH (o:Organization)-[:HAS_INVOLVEMENT]->(i)
RETURN i.status AS status, count(DISTINCT c) + count(DISTINCT rc) > 0 AS mine,
       [q IN collect(DISTINCT r.quote) WHERE q IS NOT NULL] AS quotes, count(DISTINCT o) AS orgs"""
CODE = re.compile(r"^C-[%s]{6}$" % ids.DISPLAY_ALPHABET)


def _norm(text):
    return re.sub(r"\s+", "", text or "")


def _facts(driver, code, involvement_id):
    records, _, _ = driver.execute_query(FACTS, {"id": involvement_id, "code": code}, database_="neo4j")
    return dict(records[0]) if records else None


def input_errors(code, involvement_id, org_name, org_id):
    errors = []
    if not isinstance(code, str) or not CODE.match(code):
        errors.append("仮名 %r は本人の仮名（C-と 6 字）の形でない" % (code,))
    if not ids.is_valid_id(involvement_id, "INV"):
        errors.append("関わりの ID %r は INV-… の形でない" % (involvement_id,))
    if not isinstance(org_name, str) or len(_norm(org_name)) < org_candidates.MIN_LENGTH:
        errors.append("原文の名前 %r は %d 字以上の文字列" % (org_name, org_candidates.MIN_LENGTH))
    if not ids.is_valid_org_id(org_id):
        errors.append("機関 ID %r は資源の側の機関 ID（ORG-…）の形でない" % (org_id,))
    return errors


def link_errors(facts, code, involvement_id, org_name, org_id, candidates):
    """DB から読んだ事実と候補で、結んでよいかを決める。止める理由の一覧を返す（空なら結んでよい）。"""
    if facts is None or facts.get("status") is None:
        return ["関わり %s が無い" % involvement_id]
    errors = []
    if not facts["mine"]:
        errors.append("関わり %s は %s の本人のものでない" % (involvement_id, code))
    if facts["status"] != "Pending":
        errors.append("関わり %s は未確定でない（%s）。機関を結ぶのは承認の前だけ" % (involvement_id, facts["status"]))
    if facts["orgs"]:
        errors.append("関わり %s にはすでに機関が結ばれている（付け替えはしない）" % involvement_id)
    if not any(_norm(org_name) in _norm(q) for q in facts["quotes"]):
        errors.append("名前 %r が関わり %s の根拠の記録の引用に無い（引用に書かれた名前だけで引く）" % (org_name, involvement_id))
    if org_id not in {c["orgId"] for c in candidates["candidates"]}:
        errors.append("機関 ID %s は %r の候補に無い（候補の中から職員が選んだ ID だけを結ぶ）" % (org_id, org_name))
    return errors


def link_request(staff_id, involvement_id, org_id, request_id):
    return {"requestId": request_id, "actorStaffId": staff_id,
            "nodes": [{"ref": "org", "label": "Organization", "origin": "Human", "properties": {"orgId": org_id}}],
            "relationships": [{"type": "HAS_INVOLVEMENT", "from": "org", "to": {"label": "Involvement", "id": involvement_id},
                               "properties": {}}]}


def link(driver, resource_driver, staff_id, code, involvement_id, org_name, org_id):
    """返り値：結べば {"ok": True, "involvementId", "orgId", "name", "kind", "areas", "serviceTypes"}、止まれば {"ok": False, "errors"}。"""
    errors = input_errors(code, involvement_id, org_name, org_id)
    if errors:
        return {"ok": False, "errors": errors}
    facts = _facts(driver, code, involvement_id)
    candidates = org_candidates.for_involvement(resource_driver, org_name)
    errors = link_errors(facts, code, involvement_id, org_name, org_id, candidates)
    if errors:
        return {"ok": False, "errors": errors}
    out = gw.submit(link_request(staff_id, involvement_id, org_id, "req-link-org-" + uuid.uuid4().hex), driver)
    if not out["ok"]:
        return {"ok": False, "errors": out["errors"]}
    chosen = next(c for c in candidates["candidates"] if c["orgId"] == org_id)
    return {"ok": True, "involvementId": involvement_id, "orgId": org_id, "name": chosen["name"], "kind": chosen["kind"],
            "areas": chosen["areas"], "serviceTypes": chosen["serviceTypes"]}
