"""本人のデータを消す（N-32。2026-11-06 河原さん。止まる点 F-1、台帳 G-74。正典 v0.11）。

- 対象は、最後の保存の判断（RetentionDecision。決めた日の順、同じ日なら登録の順）が消す（Delete）の本人だけ。
  判断が無い・最後が残す（Keep）なら、試しの実行でも動かない
- 消せるのは Active な Administrator。一人ずつ。試しの実行（write=False）は件数だけを返し、何も書かない
- 消す（write=True）には、仮名（displayCode）の打ち返し（confirm）が要る
- 消すもの：本人と、本人にだけつながるもの（親の辺の先がすべて消えるもの。決まった点まで繰り返す）
- 残すもの：ほかの本人にもつながる人（この本人へのつながりだけ外れる）。職員・機関・監査ログは対象にしない
- 試しの実行で、消す記録のうち他の機関から受け取ったもの（PROVIDED_BY あり）の件数を出す。消してよいかは人が見る
- 本当に消す（DETACH DELETE）。消したら監査ログ（Purge）を 1 件だけ書く：本人の ID・もとにした保存の判断・種類ごとの件数・
  残した人の数。名前・仮名・本文・理由の文は書かない。今までの監査ログは残る（相手が消えるので AUDIT_FOR は外れ、ID の文字だけ残る）
- バックアップは消さない。消した後に新しいバックアップを取り、戻せることを確かめてから、消した日より前のものを人が消す
- Claude はこれを使わない（読み取りの包みは書けない）。人が手元の道具（scripts/purge_client.py）で使う
手本：tsunagu-net の tsunagu/gate/purge.py（読むだけ）。tsunagu-net は世帯、nest-support は本人が単位。
"""
import uuid
from collections import Counter
from datetime import datetime, timezone

from nest import ids

# 子のラベル → 親の辺（型, 子から出る向きか）。子は、親の辺が一つ以上あり、その先がすべて消えるときに消える
PARENTS = {
    "NgAction": {("MUST_AVOID", False)},
    "CarePreference": {("REQUIRES", False)},
    "Condition": {("HAS_CONDITION", False)},
    "Wish": {("HAS_WISH", False)},
    "LifeHistory": {("HAS_HISTORY", False)},
    "Certificate": {("HAS_CERTIFICATE", False)},
    "PublicAssistance": {("RECEIVES", False)},
    "Residence": {("RESIDES_AT", False)},
    "CareRole": {("ROLE_FOR", True)},
    "Record": {("ABOUT", True)},
    "SupportLog": {("ABOUT", True)},
    "Review": {("ABOUT", True), ("CONFIRMS", True)},
    "Involvement": {("CONCERNS", True)},
    "RetentionDecision": {("DECIDES_ON", True)},
    "Person": {("RELATED_TO", True), ("PERFORMS", True), ("HAS_INVOLVEMENT", True), ("CAN_BE_PERFORMED_BY", False),
               ("TOLD_BY", False)},
}


def plan(client, edges):
    """client：鍵（ラベル, ID）。edges：[{child, type, out, parent}]（child・parent は鍵）。
    返り値 {delete（消す鍵の集合）, kept（消えるものにつながるが残す鍵）, keptPersons}。"""
    parents = {}
    for e in edges:
        child = e["child"]
        if (e["type"], e["out"]) in PARENTS.get(child[0], ()):
            parents.setdefault(child, set()).add(e["parent"])
    delete = {client}
    changed = True
    while changed:
        changed = False
        for child, ps in parents.items():
            if child not in delete and ps <= delete:
                delete.add(child)
                changed = True
    kept = {c for c, ps in parents.items() if c not in delete and ps & delete}
    return {"delete": delete, "kept": kept, "keptPersons": sum(1 for k in kept if k[0] == "Person")}


def counts(keys):
    return ["%s:%d" % kv for kv in sorted(Counter(k[0] for k in keys).items())]


def latest_decision(rows):
    """保存の判断のうち最後のもの（決めた日の順、同じ日なら登録の順）。無ければ None。"""
    return max(rows, key=lambda r: (r["decidedOn"], r["registeredAt"]), default=None)


def check(role, exists, decision, display_code, write, confirm):
    errors = []
    if not role or role.get("status") != "Active" or role.get("role") != "Administrator":
        errors.append("消せるのは Active な Administrator だけ")
    if not exists:
        errors.append("本人が無い：%s" % display_code)
    elif decision is None:
        errors.append("保存の判断（RetentionDecision）が本人に結ばれていない。先に Administrator がゲートで判断を書く")
    elif decision.get("decision") != "Delete":
        errors.append("最後の保存の判断が消す（Delete）でない（%s は %s）" % (decision.get("retentionId"), decision.get("decision")))
    if write and confirm != display_code:
        errors.append("仮名の打ち返しが%s（--confirm に同じ仮名を書く）" % ("無い" if not confirm else "合わない"))
    return errors


def audit_props(new_id, now, client_id, retention_id, purged_counts, kept_persons, request_id):
    return {"auditId": new_id("AUD"), "at": now, "action": "Purge", "targetLabel": "Client", "targetId": client_id,
            "requestId": request_id, "retentionId": retention_id, "purgedCounts": list(purged_counts),
            "keptPersons": kept_persons, "registeredAt": now, "status": "Active", "origin": "Human"}


ROLE = "MATCH (s:Staff {staffId: $id}) RETURN s.status AS status, s.role AS role"
CLIENT = "MATCH (c:Client {displayCode: $code}) RETURN elementId(c) AS eid, c.clientId AS id"
DECISIONS = """MATCH (rd:RetentionDecision)-[:DECIDES_ON]->(:Client {displayCode: $code}) WHERE rd.status = 'Active'
RETURN rd.retentionId AS retentionId, rd.decision AS decision, rd.decidedOn AS decidedOn, rd.registeredAt AS registeredAt"""
NEAR = """UNWIND $eids AS eid MATCH (p) WHERE elementId(p) = eid
MATCH (c)-[]-(p) WHERE any(l IN labels(c) WHERE l IN $labels)
RETURN DISTINCT elementId(c) AS eid"""
EDGES = """UNWIND $eids AS eid MATCH (c) WHERE elementId(c) = eid
MATCH (c)-[r]-(p)
RETURN eid AS child, labels(c)[0] AS label, type(r) AS type, startNode(r) = c AS out, elementId(p) AS parent, labels(p)[0] AS plabel"""
CUT = """MATCH (n)-[r]-(m) WHERE elementId(n) IN $del AND NOT elementId(m) IN $del
RETURN count(DISTINCT CASE WHEN m:AuditLog THEN m END) AS auditLogs, count(DISTINCT CASE WHEN NOT m:AuditLog THEN r END) AS links"""
PROVIDED = """MATCH (r:Record)-[:PROVIDED_BY]->(:Organization) WHERE elementId(r) IN $del RETURN count(DISTINCT r) AS n"""
DELETE = "MATCH (n) WHERE elementId(n) IN $del DETACH DELETE n"
AUDIT = "MATCH (s:Staff {staffId: $actor}) CREATE (a:AuditLog) SET a = $props CREATE (a)-[:ACTED_BY]->(s)"


def _collect(tx, client_eid):
    """消える見込みの節から子をたどり、親の辺を集める。消えるものが増えなくなるまで。"""
    labels = sorted(PARENTS)
    edges, seen, label_of = [], set(), {client_eid: "Client"}
    deleted = frontier = {client_eid}
    p = plan(("Client", client_eid), [])
    while frontier:
        found = {r["eid"] for r in tx.run(NEAR, eids=sorted(frontier), labels=labels)} - seen
        seen |= found
        for r in tx.run(EDGES, eids=sorted(found)):
            label_of[r["child"]], label_of[r["parent"]] = r["label"], r["plabel"]
            edges.append({"child": r["child"], "type": r["type"], "out": r["out"], "parent": r["parent"]})
        key = lambda eid: (label_of.get(eid, "?"), eid)  # noqa: E731
        p = plan(key(client_eid), [dict(e, child=key(e["child"]), parent=key(e["parent"])) for e in edges])
        now_deleted = {k[1] for k in p["delete"]}
        frontier = now_deleted - deleted
        deleted = now_deleted
    return p


def _run(tx, staff_id, display_code, write, confirm, now, new_id, request_id):
    rows = list(tx.run(ROLE, id=staff_id))
    role = dict(rows[0]) if rows else None
    c = list(tx.run(CLIENT, code=display_code))
    decision = latest_decision([dict(r) for r in tx.run(DECISIONS, code=display_code)]) if c else None
    errors = check(role, bool(c), decision, display_code, write, confirm)
    out = {"ok": not errors, "errors": errors, "displayCode": display_code, "written": False}
    if errors:
        return out
    p = _collect(tx, c[0]["eid"])
    dele = sorted(k[1] for k in p["delete"])
    cut = tx.run(CUT, **{"del": dele}).single()
    out.update({"purgedCounts": counts(p["delete"]), "keptPersons": p["keptPersons"], "keptLinked": counts(p["kept"]),
                "cutLinks": cut["links"], "auditLogsKept": cut["auditLogs"], "retentionId": decision["retentionId"],
                "providedRecords": tx.run(PROVIDED, **{"del": dele}).single()["n"]})
    if write:
        tx.run(DELETE, **{"del": dele})
        props = audit_props(new_id, now, c[0]["id"], decision["retentionId"], out["purgedCounts"], p["keptPersons"], request_id)
        tx.run(AUDIT, actor=staff_id, props=props)
        out.update({"written": True, "auditId": props["auditId"]})
    return out


def purge(driver, staff_id, display_code, write=False, confirm=None, now=None, new_id=ids.new_id, request_id=None,
          database="neo4j"):
    """試しの実行（write=False）は件数だけ。write=True で消す（confirm に同じ仮名が要る）。"""
    now = now or datetime.now(timezone.utc)
    request_id = request_id or "req-purge-" + uuid.uuid4().hex
    with driver.session(database=database) as s:
        run = s.execute_write if write else s.execute_read
        return run(_run, staff_id, display_code, write, confirm, now, new_id, request_id)
