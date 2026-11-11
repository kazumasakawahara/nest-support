"""Pending の承認と却下（N-21。ADR-001 D9）。ゲートの一部。書き込み（write.submit）とは別の操作。

- 承認・却下できるのは Active な職員。対象は Pending のノードだけ。承認で Active、却下で Inactive にする。変えるのは status だけ
- 一人で使う人の自己承認を認める（tsunagu-net の「自分で登録したものは自分で承認できない」とは、ここで分かれる）。
  自分で登録したもの（Create の AuditLog の ACTED_BY が自分）を承認したら、APPROVED と AuditLog に selfApproval: true を残す
- AI 由来のものはまとめて承認しない。approve_many は、2 件以上で AI 由来が一つでもあれば、何も変えずに断る
- 承認の出力には、事実ごとに原文の引用を並べる（review_items も同じ形。本人に直接つながるもの、本人について聞いた記録の話し手、
  本人の事実の根拠の記録、本人についての記録を根拠にした関わり（親など本人以外の人に向けたものを含む。正典 v0.7）を並べる）。関わりには中身（種類・確度・終わり方・推定の根拠・注記・機関）も添える（止まる点 4。台帳 G-59）。引用は、記録ならその記録、
  事実なら根拠（EVIDENCED_BY）の記録、人ならその人から聞いた（TOLD_BY）記録から引く
- 根拠（EVIDENCED_BY の先の記録）が未確定（Pending）なら、対象の承認を止め、先に承認する記録を名指す。根拠を一緒には承認しない
  （正典 §7「一回の操作で一つのノード」）。根拠がすべて差し戻し済み（Inactive）なら止める。差し戻しは止めない（2026-11-11 河原さん）
- 承認は Staff -[:APPROVED {at, selfApproval}]-> 対象 で残す。承認・却下とも AuditLog（Approve／Reject）を残す
- 却下には理由を一行（200 字まで）添えられる（任意）。AuditLog の reason に残す。名前を書かない（正典 v0.12。台帳 G-91）
手本：tsunagu-net の tsunagu/gate/approve.py（読むだけ）。
"""
from datetime import datetime, timezone

from nest import ids
from nest.gate import validate as gv
from nest.gate import write as gw

DECIDABLE = set(ids.LABEL_PREFIX) - gv.GATE_ONLY_LABELS - {"Staff"}
NEW_STATUS = {"Approve": "Active", "Reject": "Inactive"}
REASON_MAX = 200  # 差し戻しの理由の上限。read_quote の上限（nest.mcp_guard.QUOTE_MAX）と同じ（台帳 G-92）
QUOTES = """MATCH (n:%s {%s: $id})
OPTIONAL MATCH (n)-[:EVIDENCED_BY]->(e:Record)
OPTIONAL MATCH (t:Record)-[:TOLD_BY]->(n)
WITH n, collect(DISTINCT e) + collect(DISTINCT t) + CASE WHEN n:Record THEN [n] ELSE [] END AS recs
UNWIND recs AS r
WITH DISTINCT r
RETURN r.recordId AS recordId, r.quote AS quote, r.certainty AS certainty, r.informantKind AS informantKind, r.status AS status
ORDER BY recordId"""
EVIDENCE = "MATCH (t:%s {%s: $id})-[:EVIDENCED_BY]->(e:Record) RETURN e.recordId AS id, e.status AS status ORDER BY id"
PENDING_AROUND = """MATCH (c:Client {clientId: $c})
CALL (c) {
  MATCH (c)--(n) WHERE n.status = 'Pending' RETURN n
  UNION
  MATCH (c)<-[:ABOUT]-(:Record)-[:TOLD_BY]->(n:Person) WHERE n.status = 'Pending' RETURN n
  UNION
  MATCH (c)--()-[:EVIDENCED_BY]->(n:Record) WHERE n.status = 'Pending' RETURN n
  UNION
  MATCH (c)<-[:ABOUT]-(:Record)<-[:EVIDENCED_BY]-(n:Involvement) WHERE n.status = 'Pending' RETURN n
}
RETURN DISTINCT labels(n)[0] AS label, n AS node"""


def _quotes(tx, label, key, target_id):
    return [r.data() for r in tx.run(QUOTES % (label, key), id=target_id)]


def _check(tx, action, actor, label, key, target_id):
    rows = list(tx.run("MATCH (t:%s {%s: $id}) RETURN t.status AS status, t.origin AS origin" % (label, key), id=target_id))
    if not rows or rows[0]["status"] != "Pending":
        return ["%s %s は Pending でない（%s）" % (label, target_id, rows[0]["status"] if rows else "無い")], None
    return [], rows[0]["origin"]


def _evidence_errors(tx, label, key, target_id):
    """承認の前に、根拠の記録の状態を確かめる。根拠の無い対象（記録・人など）は確かめることが無い。"""
    rows = list(tx.run(EVIDENCE % (label, key), id=target_id))
    pending = [r["id"] for r in rows if r["status"] == "Pending"]
    if pending:
        return ["%s %s の根拠の記録が未確定（%s）。先に根拠の記録を一件ずつ承認してから、この対象を承認する"
                "（根拠が未確定のまま有効にしない。正典 §7）" % (label, target_id, "・".join(pending))]
    if rows and not any(r["status"] == "Active" for r in rows):
        return ["%s %s の根拠の記録がすべて差し戻し済み（%s）。この対象は承認できない。差し戻すか、新しい根拠で出し直す"
                % (label, target_id, "・".join(r["id"] for r in rows))]
    return []


def _self(tx, actor, label, target_id):
    rows = list(tx.run("MATCH (a:AuditLog {action: 'Create', targetLabel: $label, targetId: $id})-[:ACTED_BY]->"
                       "(:Staff {staffId: $actor}) RETURN count(a) AS n", label=label, id=target_id, actor=actor))
    return bool(rows and rows[0]["n"])


def _change(tx, action, actor, label, key, target_id, request_id, now, new_id, reason=None):
    done = list(tx.run("MATCH (t:%s {%s: $id}) WHERE t.status = 'Pending' SET t.status = '%s' RETURN count(t) AS n"
                       % (label, key, NEW_STATUS[action]), id=target_id))
    if not done or done[0]["n"] != 1:
        raise gw.Rejected(["%s %s の状態を変えられなかった（同時に他の操作があった可能性）" % (label, target_id)])
    props = gw.audit_props(new_id, now, action, label, target_id, request_id, "Human")
    self_approval = None
    if action == "Approve":
        self_approval = _self(tx, actor, label, target_id)
        tx.run("MATCH (s:Staff {staffId: $actor}) MATCH (t:%s {%s: $id}) CREATE (s)-[:APPROVED {at: $at, selfApproval: $selfApproval}]->(t)"
               % (label, key), actor=actor, id=target_id, at=now, selfApproval=self_approval)
        props["selfApproval"] = self_approval
    if reason is not None:
        props["reason"] = reason
    tx.run(gw.AUDIT_QUERY % (label, key), id=target_id, actor=actor, props=props)
    return self_approval


def _decide_all(tx, action, actor, targets, request_id, now, new_id, reason=None):
    """全件を先に確かめ、一件でもだめなら何も変えない。"""
    errors = []
    gw.actor_role(tx, actor, errors)
    origins = []
    if not errors:
        for label, key, target_id in targets:
            errs, origin = _check(tx, action, actor, label, key, target_id)
            if not errs and action == "Approve":
                errs = _evidence_errors(tx, label, key, target_id)
            errors.extend(errs)
            origins.append(origin)
    if not errors and len(targets) > 1 and "AiExtracted" in origins:
        errors.append("AI 由来のものはまとめて承認・却下しない。一件ずつ、原文の引用と照らして決める（D9）")
    if errors:
        raise gw.Rejected(errors)
    shown, selfs = [], []
    for label, key, target_id in targets:
        shown.extend(_quotes(tx, label, key, target_id))
        selfs.append(_change(tx, action, actor, label, key, target_id, request_id, now, new_id, reason))
    return shown, selfs


def _targets(raw, out):
    targets, seen = [], set()
    for t in raw:
        if not isinstance(t, dict) or set(t) != {"label", "id"}:
            out["errors"].append("対象は {label, id} だけで指す（%r）" % (t,))
            continue
        label, target_id = t["label"], t["id"]
        if label not in DECIDABLE:
            out["errors"].append("%r は承認・却下の対象にならない" % (label,))
        elif not ids.is_valid_id(target_id, ids.LABEL_PREFIX[label]):
            out["errors"].append("%s の ID %r が正しくない" % (label, target_id))
        elif (label, target_id) in seen:
            out["errors"].append("%s %s が重複している" % (label, target_id))
        else:
            seen.add((label, target_id))
            targets.append((label, gw.key_of(label), target_id))
    return targets


def _run(action, driver, actor, raw_targets, request_id, now, new_id, database, out, reason=None):
    if not ids.is_valid_id(actor, "STF"):
        out["errors"].append("actorStaffId %r は職員の ID（STF-…）でなければならない" % (actor,))
    if not request_id:
        out["errors"].append("requestId が無い")
    if not raw_targets:
        out["errors"].append("対象が無い")
    targets = _targets(raw_targets or [], out)
    if out["errors"]:
        return out
    try:
        with driver.session(database=database) as s:
            shown, selfs = s.execute_write(_decide_all, action, actor, targets, request_id,
                                           now or datetime.now(timezone.utc), new_id, reason)
    except gw.Rejected as e:
        out["errors"] = e.errors
        return out
    out.update(ok=True, shown=shown, count=len(targets))
    if action == "Approve":
        out["selfApproval"] = selfs[0] if len(selfs) == 1 else selfs
    return out


def approve(driver, actor_staff_id, target, request_id, now=None, new_id=ids.new_id, database="neo4j"):
    """一件を承認する。出力の shown に、その事実の原文の引用を並べる。"""
    out = {"ok": False, "errors": [], "requestId": request_id, "action": "Approve", "target": target}
    if not isinstance(target, dict):
        out["errors"].append("承認は一件ずつ（{label, id}）。一覧は渡せない")
        return out
    return _run("Approve", driver, actor_staff_id, [target], request_id, now, new_id, database, out)


def reject(driver, actor_staff_id, target, request_id, now=None, new_id=ids.new_id, database="neo4j", reason=None):
    """一件を却下（差し戻し）する。reason は任意の一行（AuditLog の reason。名前を書かない）。"""
    out = {"ok": False, "errors": [], "requestId": request_id, "action": "Reject", "target": target}
    if reason is not None and (not isinstance(reason, str) or not reason.strip() or "\n" in reason or "\r" in reason):
        out["errors"].append("差し戻しの理由は一行の文字列で書く（空・改行は不可）")
        return out
    if reason is not None and len(reason) > REASON_MAX:
        out["errors"].append("差し戻しの理由は %d 字まで（%d 字）" % (REASON_MAX, len(reason)))
        return out
    if not isinstance(target, dict):
        out["errors"].append("却下は一件ずつ（{label, id}）。一覧は渡せない")
        return out
    return _run("Reject", driver, actor_staff_id, [target], request_id, now, new_id, database, out, reason)


def approve_many(driver, actor_staff_id, targets, request_id, now=None, new_id=ids.new_id, database="neo4j"):
    """まとめての承認。2 件以上で AI 由来が一つでもあれば、何も変えずに断る（D9）。"""
    out = {"ok": False, "errors": [], "requestId": request_id, "action": "Approve", "count": 0}
    return _run("Approve", driver, actor_staff_id, list(targets or []), request_id, now, new_id, database, out)


INVOLVEMENT_ORGS = """MATCH (o:Organization)-[:HAS_INVOLVEMENT]->(:Involvement {involvementId: $id})
RETURN o.orgId AS orgId ORDER BY orgId"""
ORG_NAMES = "MATCH (o:Organization) WHERE o.orgId IN $ids RETURN o.orgId AS orgId, o.name AS name"


def involvement_content(props, org_ids, names):
    """承認の前に見せる関わりの中身（止まる点 4。台帳 G-59）。機関の名前は資源の側から引いたもの（無ければ None）。"""
    names = names or {}
    return {"kind": props.get("kind"), "certainty": props.get("certainty"), "howEnded": props.get("howEnded"),
            "inferenceBasis": props.get("inferenceBasis"), "note": props.get("note"),
            "organizations": [{"orgId": o, "name": names.get(o)} for o in org_ids], "organizationUndecided": not org_ids}


def _org_names(resource_driver, org_ids):
    if resource_driver is None or not org_ids:
        return {}
    rows = resource_driver.execute_query(ORG_NAMES, {"ids": sorted(org_ids)}).records
    return {r["orgId"]: r["name"] for r in rows}


def review_items(driver, client_id, database="neo4j", resource_driver=None):
    """本人のまわりの Pending を、事実ごとに原文の引用を添えて返す（読むだけ）。
    関わりには中身（content：種類・確度・終わり方・推定の根拠・注記・機関）を添える。resource_driver を渡せば機関の名前も引く。"""
    items = []
    with driver.session(database=database) as s:
        for row in s.execute_read(lambda tx: list(tx.run(PENDING_AROUND, c=client_id))):
            label, node = row["label"], row["node"]
            if label not in DECIDABLE:
                continue
            key = gw.key_of(label)
            quotes = s.execute_read(_quotes, label, key, node[key])
            item = {"label": label, "id": node[key], "origin": node.get("origin"), "quotes": quotes}
            if label == "Involvement":
                orgs = [r["orgId"] for r in s.execute_read(lambda tx: list(tx.run(INVOLVEMENT_ORGS, id=node[key])))]
                item["content"] = involvement_content(dict(node), orgs, _org_names(resource_driver, orgs))
            items.append(item)
    return items
