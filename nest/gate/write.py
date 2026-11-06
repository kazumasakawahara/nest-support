"""ゲートの書き込み（N-20。ADR-001 D5・D6・D8）。個人の側への書き込みは、ここ（と bootstrap・承認）だけを通す。

流れ：
  1. validate() で検証する。誤りがあれば DB に触れない
  2. ID・Client の displayCode を発番し、共通の項目（registeredAt・status・origin）と Record の sourceHash を付ける。
     AI 由来は Pending（validate が決めた status を使う）
  3. 一つのトランザクションで、前提（職員が Active、職員を登録するなら Administrator、既にあるノード、
     sourceHash の重複）を確かめてから書く。前提が崩れていたら何も書かずに戻す
  4. 書いたノードとリレーションごとに AuditLog を作り、AUDIT_FOR（対象）と ACTED_BY（職員）でつなぐ

書き込みの問い合わせは CREATE だけ。既にあるノードの項目を書き換えない。似たものを自動でまとめない（D5）。
禁忌などの事実と聞いた記録：
  - 依頼の中で作った事実と記録は、依頼の中で EVIDENCED_BY で結べる（linkedBy・at はゲートが付ける）
  - 既にある事実に根拠を結ぶのは人の指定だけ。依頼の中では結ばず、link_evidence で結ぶ（D5）
  - 既にある事実と食い違う話は、新しい記録から CONTRADICTS を足して保留する。事実のほうは変えない（raisedAt はゲートが付ける）
手本：tsunagu-net の tsunagu/gate/write.py（読むだけ）。
"""
import hashlib
import json
import secrets
import unicodedata
from datetime import datetime, timezone

from nest import area_code, ids
from nest.gate import validate as gv

HASHED = ("kind", "aboutDate", "heardOn", "text", "quote", "certainty", "informantKind",
          "documentHash", "providerCertainty", "receivedOn")
ACTION = {"CONTRADICTS": "RaiseContradiction", "EVIDENCED_BY": "LinkEvidence"}
DISPLAY_CODE_LENGTH = 6
AUDIT_QUERY = ("MATCH (t:%s {%s: $id}) MATCH (s:Staff {staffId: $actor}) "
               "CREATE (a:AuditLog) SET a = $props CREATE (a)-[:AUDIT_FOR]->(t), (a)-[:ACTED_BY]->(s)")


class Rejected(Exception):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def new_display_code():
    """表示用の仮名。乱数で作り、名前・生年月日・連番から作らない（D8。連番は実名を引き出す手がかりになる）。"""
    return "C-" + "".join(secrets.choice(ids.DISPLAY_ALPHABET) for _ in range(DISPLAY_CODE_LENGTH))


def key_of(label):
    return gv.EXTERNAL_ID_PROP.get(label) or gv.canon.load(gv.SCHEMA)["personal"]["nodes"][label]["unique"][0]


def source_hash(props, links):
    """Record の二重登録を見分けるハッシュ。内容（HASHED）と、ID が決まっている相手（種類, 向き, label, id）から作る。
    NFC に正規化してから SHA-256 を取る。保存する本文の形は変えない。"""
    payload = {"properties": {k: props.get(k) for k in HASHED}, "links": sorted(list(l) for l in links)}
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=lambda v: v.isoformat())
    return hashlib.sha256(unicodedata.normalize("NFC", text).encode("utf-8")).hexdigest()


def audit_props(new_id, now, action, target_label, target_id, request_id, origin):
    return {"auditId": new_id("AUD"), "at": now, "action": action, "targetLabel": target_label, "targetId": target_id,
            "requestId": request_id, "registeredAt": now, "status": "Active", "origin": origin}


def build_plan(rep, req, now, new_id, new_code):
    """検証済みの依頼から、書く内容を決める。DB に触れない。"""
    errors = []
    actor = req.get("actorStaffId")
    if not ids.is_valid_id(actor, "STF"):
        errors.append("actorStaffId %r は職員の ID（STF-…）でなければならない" % (actor,))

    ref_ids, origins, nodes = {}, {}, []
    for node in rep["nodes"]:
        label, props = node["label"], dict(node["properties"])
        key = key_of(label)
        if label in gv.EXTERNAL_ID_PROP:
            props["linkedAt"] = now
        else:
            props[key] = new_id(ids.LABEL_PREFIX[label])
        if label == "Client":
            props["displayCode"] = new_code()
        if label == "Residence":  # 区はゲートが手元の表で住所から出す（N-24a）。依頼の値が食い違えば止める
            derived = area_code.from_address(props.get("address"))
            if props.get("areaCode", derived) != derived:
                errors.append("%s: areaCode %r が住所から出した値（%r）と違う" % (node["ref"], props["areaCode"], derived or "一致なし"))
            props.pop("areaCode", None)
            if derived:
                props["areaCode"] = derived
        props.update(registeredAt=now, origin=node["origin"], status=node["status"])
        if label == "Staff" and node["origin"] != "Human":
            errors.append("職員は人が登録する（origin は Human。%s は %s）" % (node["ref"], node["origin"]))
        ref_ids[node["ref"]] = props[key]
        origins[node["ref"]] = node["origin"]
        nodes.append({"ref": node["ref"], "label": label, "key": key, "props": props})

    labels = {n["ref"]: n["label"] for n in nodes}
    known = {n["ref"] for n in nodes if n["label"] in gv.EXTERNAL_ID_PROP}

    def end(value):
        if isinstance(value, dict):
            return value["label"], key_of(value["label"]), value["id"]
        return labels[value], key_of(labels[value]), ref_ids[value]

    rels, existing = [], set()
    for rel in rep["relationships"]:
        if rel["type"] == "EVIDENCED_BY" and isinstance(rel["from"], dict):
            errors.append("既にある %s %s に根拠を結ぶのは人の指定だけ。依頼の中では結ばない（link_evidence で結ぶ。D5）"
                          % (rel["from"]["label"], rel["from"]["id"]))
            continue
        a, b = end(rel["from"]), end(rel["to"])
        for side in (rel["from"], rel["to"]):
            if isinstance(side, dict):
                existing.add((side["label"], side["id"]))
        origin = next((origins[s] for s in (rel["from"], rel["to"]) if not isinstance(s, dict)), "Human")
        props = dict(rel["properties"])
        if rel["type"] == "EVIDENCED_BY":
            props.update(linkedBy=actor, at=now)
        if rel["type"] == "CONTRADICTS":
            props["raisedAt"] = now
        rels.append({"type": rel["type"], "from": a, "to": b, "props": props, "origin": origin})

    hashes = {}
    for n in nodes:
        if n["label"] != "Record":
            continue
        links = []
        for rel in rep["relationships"]:
            for mine, other, side in (("from", "to", "to"), ("to", "from", "from")):
                o = rel[other]
                if rel[mine] == n["ref"] and (isinstance(o, dict) or o in known):
                    lbl, _, oid = end(o)
                    links.append((rel["type"], side, lbl, oid))
        h = source_hash(n["props"], links)
        if h in hashes:
            errors.append("二重登録：依頼の中の記録 %s と %s が同じ内容（sourceHash %s…）" % (hashes[h], n["ref"], h[:12]))
        hashes[h] = n["ref"]
        n["props"]["sourceHash"] = h

    # ノードの監査はそのノードを指す。リレーションには ID が無いので、targetLabel に種類を、targetId と AUDIT_FOR に始点を置く
    targets = [(n["ref"], n["label"], n["key"], n["props"][n["key"]], n["label"], n["props"]["origin"]) for n in nodes]
    targets += [(None, r["from"][0], r["from"][1], r["from"][2], r["type"], r["origin"]) for r in rels]
    audits = [{"ref": ref, "label": label, "key": key, "id": tid, "actor": actor,
               "props": audit_props(new_id, now, ACTION.get(tlabel, "Create"), tlabel, tid, req.get("requestId"), origin)}
              for ref, label, key, tid, tlabel, origin in targets]
    return {"errors": errors, "actor": actor, "nodes": nodes, "relationships": rels, "existing": sorted(existing),
            "hashes": hashes, "audits": audits, "ids": ref_ids}


def actor_role(tx, staff_id, errors):
    """書く・決める職員が Active でいることを確かめ、役割を返す。だめなら errors に足して None を返す。"""
    rows = list(tx.run("MATCH (s:Staff {staffId: $id}) RETURN s.status AS status, s.role AS role", id=staff_id))
    if not rows or rows[0]["status"] != "Active":
        errors.append("職員 %s が無いか、Active でない（%s）" % (staff_id, rows[0]["status"] if rows else "無い"))
        return None
    return rows[0]["role"]


def exists(tx, label, oid):
    return list(tx.run("MATCH (n:%s {%s: $id}) RETURN count(n) AS n" % (label, key_of(label)), id=oid))[0]["n"] == 1


def _apply(tx, plan):
    errors = []
    role = actor_role(tx, plan["actor"], errors)
    if role and role != "Administrator" and any(n["label"] == "Staff" for n in plan["nodes"]):
        errors.append("職員を登録できるのは Administrator だけ（%s は %s）" % (plan["actor"], role))
    if role and role != "Administrator" and any(n["label"] == "RetentionDecision" for n in plan["nodes"]):
        errors.append("保存の判断を書けるのは Administrator だけ（%s は %s。N-32）" % (plan["actor"], role))
    for label, oid in plan["existing"]:
        if not exists(tx, label, oid):
            errors.append("既にあるはずの %s %s が無い" % (label, oid))
    skip = {n["ref"] for n in plan["nodes"] if n["label"] in gv.EXTERNAL_ID_PROP and exists(tx, n["label"], n["props"][n["key"]])}
    if plan["hashes"]:
        for row in tx.run("MATCH (r:Record) WHERE r.sourceHash IN $hashes RETURN r.sourceHash AS h, r.recordId AS id",
                          hashes=sorted(plan["hashes"])):
            errors.append("二重登録：依頼の記録 %s は既にある記録 %s と同じ内容（sourceHash %s…）"
                          % (plan["hashes"][row["h"]], row["id"], row["h"][:12]))
    if errors:
        raise Rejected(errors)
    for node in plan["nodes"]:
        if node["ref"] not in skip:
            tx.run("CREATE (n:%s) SET n = $props" % node["label"], props=node["props"])
    for rel in plan["relationships"]:
        _create_rel(tx, rel["type"], rel["from"], rel["to"], rel["props"])
    for row in plan["audits"]:
        if row["ref"] not in skip:
            tx.run(AUDIT_QUERY % (row["label"], row["key"]), id=row["id"], actor=row["actor"], props=row["props"])
    return {}


def _create_rel(tx, rtype, frm, to, props):
    (la, ka, ia), (lb, kb, ib) = frm, to
    q = ("MATCH (a:%s {%s: $a}) MATCH (b:%s {%s: $b}) CREATE (a)-[r:%s]->(b) SET r = $props RETURN count(r) AS n"
         % (la, ka, lb, kb, rtype))
    if list(tx.run(q, a=ia, b=ib, props=props))[0]["n"] != 1:
        raise Rejected(["リレーション %s（%s → %s）を作れなかった" % (rtype, ia, ib)])


def submit(req, driver, now=None, new_id=ids.new_id, new_code=new_display_code, database="neo4j"):
    """依頼を検証し、通れば一つのトランザクションで書く。返り値の ok が偽なら何も書いていない。"""
    rep = gv.validate(req)
    out = {"ok": False, "errors": list(rep["errors"]), "corrections": rep["corrections"],
           "requestId": req.get("requestId"), "ids": {}}
    if rep["errors"]:
        return out
    plan = build_plan(rep, req, now or datetime.now(timezone.utc), new_id, new_code)
    if plan["errors"]:
        out["errors"] = plan["errors"]
        return out
    try:
        with driver.session(database=database) as s:
            s.execute_write(_apply, plan)
    except Rejected as e:
        out["errors"] = e.errors
        return out
    out.update(ok=True, ids=plan["ids"])
    return out


def _link(tx, actor, fact, record_id, request_id, now, new_id):
    errors = []
    actor_role(tx, actor, errors)
    if not exists(tx, fact["label"], fact["id"]):
        errors.append("%s %s が無い" % (fact["label"], fact["id"]))
    if not exists(tx, "Record", record_id):
        errors.append("記録 %s が無い" % record_id)
    key = key_of(fact["label"])
    q = "MATCH (:%s {%s: $f})-[e:EVIDENCED_BY]->(:Record {recordId: $r}) RETURN count(e) AS n" % (fact["label"], key)
    if not errors and list(tx.run(q, f=fact["id"], r=record_id))[0]["n"]:
        errors.append("%s %s と記録 %s は既に結ばれている" % (fact["label"], fact["id"], record_id))
    if errors:
        raise Rejected(errors)
    _create_rel(tx, "EVIDENCED_BY", (fact["label"], key, fact["id"]), ("Record", "recordId", record_id),
                {"linkedBy": actor, "at": now})
    tx.run(AUDIT_QUERY % (fact["label"], key), id=fact["id"], actor=actor,
           props=audit_props(new_id, now, "LinkEvidence", "EVIDENCED_BY", fact["id"], request_id, "Human"))


def review_request(actor, client_id, domain, reviewed_at, informant_kind, record_ids, request_id, note=None):
    """N-20a。確認の記録（Review）を作る依頼。人が確かめた記録なので origin は Human。
    reviewed_at は確かめた日時（時差つき）、domain は reviewDomain、record_ids は確かめた対象の記録（REC-…）。
    検証は validate が行う（欠けていれば止める。こちらで補わない）。"""
    props = {"domain": domain, "reviewedAt": reviewed_at, "informantKind": informant_kind}
    if note is not None:
        props["note"] = note
    props = {k: v for k, v in props.items() if v is not None}
    rels = [{"type": "REVIEWED", "from": {"label": "Staff", "id": actor}, "to": "review"},
            {"type": "ABOUT", "from": "review", "to": {"label": "Client", "id": client_id}}]
    rels += [{"type": "CONFIRMS", "from": "review", "to": {"label": "Record", "id": rid}} for rid in record_ids]
    return {"requestId": request_id, "actorStaffId": actor,
            "nodes": [{"ref": "review", "label": "Review", "origin": "Human", "properties": props}],
            "relationships": rels}


def record_review(driver, actor, client_id, domain, reviewed_at, informant_kind, record_ids, request_id, note=None,
                  now=None, database="neo4j"):
    """N-20a。確認の記録を作り、CONFIRMS で対象の記録に結ぶ（ゲートの submit を通す）。"""
    req = review_request(actor, client_id, domain, reviewed_at, informant_kind, record_ids, request_id, note)
    return submit(req, driver, now=now, database=database)


def retention_request(actor, client_id, decided_on, decision, reason, request_id, next_review_on=None):
    """N-32。保存の判断（RetentionDecision）を書く依頼。人の判断なので origin は Human（未確定を経ない）。
    decision は Keep か Delete。reason に名前を書かない。消すのは nest.gate.purge（判断を書くだけでは消えない）。"""
    props = {"decidedOn": decided_on, "decision": decision, "reason": reason}
    if next_review_on is not None:
        props["nextReviewOn"] = next_review_on
    return {"requestId": request_id, "actorStaffId": actor,
            "nodes": [{"ref": "rd", "label": "RetentionDecision", "origin": "Human", "properties": props}],
            "relationships": [{"type": "DECIDES_ON", "from": "rd", "to": {"label": "Client", "id": client_id}, "properties": {}}]}


def record_retention(driver, actor, client_id, decided_on, decision, reason, request_id, next_review_on=None,
                     now=None, database="neo4j"):
    """N-32。保存の判断を書く（ゲートの submit を通す。Administrator だけ）。"""
    req = retention_request(actor, client_id, decided_on, decision, reason, request_id, next_review_on)
    return submit(req, driver, now=now, database=database)


def link_evidence(driver, actor, fact, record_id, request_id, now=None, new_id=ids.new_id, database="neo4j"):
    """人の指定で、既にある事実（禁忌など）に聞いた記録を根拠として結ぶ（D5）。自動では呼ばない。"""
    allowed = gv.canon.load(gv.SCHEMA)["personal"]["relationships"]["EVIDENCED_BY"]["from"]
    out = {"ok": False, "errors": [], "requestId": request_id}
    if not isinstance(fact, dict) or set(fact) != {"label", "id"} or fact.get("label") not in allowed \
            or not gv.existing_id_ok(fact["label"], fact["id"]):
        out["errors"].append("結ぶ先は既にある事実の {label, id}（%s のどれか）" % "／".join(allowed))
    if not ids.is_valid_id(record_id, "REC"):
        out["errors"].append("記録の ID（REC-…）が正しくない（%r）" % (record_id,))
    if not ids.is_valid_id(actor, "STF"):
        out["errors"].append("actor %r は職員の ID（STF-…）でなければならない" % (actor,))
    if not request_id:
        out["errors"].append("requestId が無い")
    if out["errors"]:
        return out
    try:
        with driver.session(database=database) as s:
            s.execute_write(_link, actor, fact, record_id, request_id, now or datetime.now(timezone.utc), new_id)
    except Rejected as e:
        out["errors"] = e.errors
        return out
    out["ok"] = True
    return out
