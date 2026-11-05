"""書き込みの案の入口（N-12〜N-16。ADR-001 D6、約束 4）。DB を使わない。AI を使わない点検。

Claude が語り・書面・自分の面談記録から作った「書き込みの案」（JSON）を原文と突き合わせて点検し、
通ればゲートへの依頼を作る。手本：tsunagu-net の tsunagu/gate/intake.py（読むだけ）。

案の形：
  {"documentKind": "ProvisionDocument" | "OwnCaseRecord",
   "providerOrgId": "ORG-…"（情報提供の書面のときだけ）,
   "clientId": "CLI-…"（既にいる本人。職員が選ぶ）,
   "receivedOn": "YYYY-MM-DD"（書面を受けた日。任意）,
   "newPeople": [{"ref", "familyName"?, "givenName"?, "familyNameKana"?, "givenNameKana"?}]（任意）,
   "facts": [{"quote", "text"?, "recordKind", "certainty", "providerCertainty"?, "informantKind",
              "aboutDate"?, "heardOn"?, "toldBy"?}]}

点検：
- quote は原文にそのまま有ること（空白・改行の違いだけは無視する）（N-12）
- 原本の指紋（documentHash）は、ここで原文から作る。案に書かせない（N-12）
"""
import copy
import hashlib
import re

from nest import ids

DOC_KINDS = ("ProvisionDocument", "OwnCaseRecord")


def _norm(text):
    return re.sub(r"\s+", "", text or "")


def _in_original(quote, original):
    return _norm(quote) in _norm(original)


def check(proposal, original, actor_staff_id, request_id):
    """返り値 {"ok", "errors", "warnings", "request"}。止めるときは request が None。"""
    p = copy.deepcopy(proposal)
    errors, warnings = [], []
    if not isinstance(p, dict) or not isinstance(original, str) or not original.strip():
        return {"ok": False, "errors": ["案はオブジェクト、原文は空でない文字列"], "warnings": [], "request": None}
    kind = p.get("documentKind")
    if kind not in DOC_KINDS:
        errors.append("documentKind は %s のどれか（%r）" % ("／".join(DOC_KINDS), kind))
    provider = p.get("providerOrgId")
    if kind == "ProvisionDocument" and not ids.is_valid_org_id(provider):
        errors.append("情報提供の書面には提供元の機関 ID（providerOrgId。ORG-…）が要る")
    if kind == "OwnCaseRecord" and provider is not None:
        errors.append("自分の記録に提供元（providerOrgId）を書かない")
    if not ids.is_valid_id(p.get("clientId"), "CLI"):
        errors.append("clientId は既にいる本人の ID（CLI-…）")
    facts = p.get("facts") or []
    if not facts:
        errors.append("事実（facts）が無い")
    for n, f in enumerate(facts, start=1):
        where = "事実 %d" % n
        quote = f.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            errors.append("%s: 原文の該当箇所（引用 quote）が要る" % where)
            continue
        if not _in_original(quote, original):
            errors.append("%s: 引用が原文に無い（%s）" % (where, quote[:30]))
            continue
    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings, "request": None}
    return {"ok": True, "errors": [], "warnings": warnings,
            "request": _request(p, original, actor_staff_id, request_id)}


def _request(p, original, actor_staff_id, request_id):
    doc_hash = hashlib.sha256(original.encode("utf-8")).hexdigest()
    client = {"label": "Client", "id": p["clientId"]}
    staff = {"label": "Staff", "id": actor_staff_id}
    nodes, rels = [], []
    if p["documentKind"] == "ProvisionDocument":
        nodes.append({"ref": "provider", "label": "Organization", "origin": "Human", "properties": {"orgId": p["providerOrgId"]}})
    for person in p.get("newPeople") or []:
        nodes.append({"ref": person["ref"], "label": "Person", "origin": "AiExtracted",
                      "properties": {k: v for k, v in person.items() if k != "ref"}})
    for n, f in enumerate(p["facts"], start=1):
        ref = "fact-%d" % n
        props = {"kind": f.get("recordKind"), "text": f.get("text") or f["quote"], "quote": f["quote"],
                 "certainty": f.get("certainty"), "informantKind": f.get("informantKind"), "documentHash": doc_hash}
        for k in ("aboutDate", "heardOn"):
            if f.get(k):
                props[k] = f[k]
        if p["documentKind"] == "ProvisionDocument":
            props["providerCertainty"] = f.get("providerCertainty")
            if p.get("receivedOn"):
                props["receivedOn"] = p["receivedOn"]
            rels.append({"type": "PROVIDED_BY", "from": ref, "to": "provider"})
        nodes.append({"ref": ref, "label": "Record", "origin": "AiExtracted", "properties": props})
        rels.append({"type": "ABOUT", "from": ref, "to": client})
        rels.append({"type": "AUTHORED_BY", "from": ref, "to": staff})
        told = f.get("toldBy")
        if told == "client":
            rels.append({"type": "TOLD_BY", "from": ref, "to": client})
        elif told:
            rels.append({"type": "TOLD_BY", "from": ref, "to": {"label": "Person", "id": told} if told.startswith("PER-") else told})
    return {"requestId": request_id, "actorStaffId": actor_staff_id, "nodes": nodes, "relationships": rels}
