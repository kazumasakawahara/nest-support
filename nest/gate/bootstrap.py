"""最初の職員（Administrator）の登録（N-20）。個人の側に職員が一人もいないときだけ使える。

2 人目からは、Administrator がゲート（write.submit）で登録する。
最初の管理者の AuditLog は、本人を ACTED_BY に置く（ほかに職員がいないため）。
手本：tsunagu-net の tsunagu/gate/bootstrap.py（読むだけ）。
"""
from datetime import datetime, timezone

from nest import ids
from nest.gate import write as gw


def _create(tx, props, request_id, now, new_id):
    n = list(tx.run("MATCH (s:Staff) RETURN count(s) AS n"))[0]["n"]
    if n:
        admins = [r["staffId"] for r in tx.run(
            "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS staffId ORDER BY staffId")]
        raise gw.Rejected(["既に職員が %d 人いる。2 人目からは Administrator がゲートで登録する（今の Administrator：%s）"
                           % (n, "、".join(admins) or "いない")])
    tx.run("CREATE (n:Staff) SET n = $props", props=props)
    tx.run(gw.AUDIT_QUERY % ("Staff", "staffId"), id=props["staffId"], actor=props["staffId"],
           props=gw.audit_props(new_id, now, "Create", "Staff", props["staffId"], request_id, "Human"))


def bootstrap_admin(driver, display_name, request_id, now=None, new_id=ids.new_id, database="neo4j"):
    out = {"ok": False, "errors": [], "requestId": request_id, "staffId": None}
    if not (display_name or "").strip():
        out["errors"].append("displayName が無い")
    if not request_id:
        out["errors"].append("requestId が無い")
    if out["errors"]:
        return out
    now = now or datetime.now(timezone.utc)
    props = {"staffId": new_id("STF"), "displayName": display_name.strip(), "role": "Administrator",
             "registeredAt": now, "status": "Active", "origin": "Human"}
    try:
        with driver.session(database=database) as s:
            s.execute_write(_create, props, request_id, now, new_id)
    except gw.Rejected as e:
        out["errors"] = e.errors
        return out
    out.update(ok=True, staffId=props["staffId"])
    return out
