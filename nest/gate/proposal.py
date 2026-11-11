"""書き込みの案（narrative-extractor が作った JSON）を、仮名で指した本人について入口の点検とゲートに通す。

書き込み受付の MCP（nest/mcp_gate.py）と、管理者の予備の道具（scripts/submit_proposal.py）が同じこれを呼ぶ（N-46 #7・台帳 G-94 の中身を移した）。
- 本人は仮名（code）で指す。個人の側から clientId を引いて案に入れる（案の clientId が空か「CLI-…」のままなら入れ、別の本人の ID なら止める）
- 入口の点検（intake.check）→ ゲート（write.submit）の順。どこかで止まれば理由を返し、何も書かない
- 通った案は AI 由来なので、未確定（Pending）で入る
- 原文は引用の照合と原本の指紋（documentHash）にだけ使う。原文そのものは DB に入れない
- 今は自分の記録（OwnCaseRecord）だけを受ける。情報提供の書面（ProvisionDocument）は止める
- 通ったら、orgName のある関わりごとに機関の候補（nest.org_candidates.for_involvement。資源の側を読むだけ）を orgChoices で返す。
  候補が 0 件でも、候補を引けなくても、書いたことは変わらない（関わりは機関未確定のまま入っている。2026-11-11 河原さん）
"""
import uuid
from collections import Counter

from nest import ids, org_candidates
from nest.gate import intake
from nest.gate import write as gw

CLIENT_OF = "MATCH (c:Client {displayCode: $code}) RETURN c.clientId AS id"


def _stop(stage, errors, warnings=()):
    return {"ok": False, "stage": stage, "errors": list(errors), "warnings": list(warnings)}


def _choices(resource_driver, proposal, made_ids):
    out = []
    for n, inv in enumerate(proposal.get("involvements") or [], start=1):
        name = inv.get("orgName")
        if not name:
            continue
        item = {"involvementId": made_ids.get("involvement-%d" % n), "orgName": name}
        try:
            found = org_candidates.for_involvement(resource_driver, name)
            item.update(candidates=found["candidates"], truncated=found["truncated"])
            if not found["candidates"]:
                item["note"] = "候補が無い。関わりは機関未確定のまま入っている"
        except Exception as e:  # 書いた後なので、候補を引けなくても止めない（書いたことを隠さない）
            item.update(candidates=[], truncated=False,
                        note="候補を引けなかった（資源の側：%s）。関わりは機関未確定のまま入っている" % type(e).__name__)
        out.append(item)
    return out


def submit(driver, staff_id, code, original, proposal, resource_driver=None):
    """返り値：通れば {"ok": True, "pending", "counts", "ids", "warnings"}、止まれば {"ok": False, "stage", "errors", "warnings"}。
    stage は input（案の形・本人の指定）・intake（入口の点検）・gate（ゲート）のどれか。"""
    if not isinstance(proposal, dict):
        return _stop("input", ["案は JSON のオブジェクト"])
    if proposal.get("documentKind") != "OwnCaseRecord":
        return _stop("input", ["今は自分の記録（OwnCaseRecord）だけを受ける（書面は段階 L で）"])
    records, _, _ = driver.execute_query(CLIENT_OF, {"code": code}, database_="neo4j")
    if not records:
        return _stop("input", ["仮名 %s の本人がいない" % code])
    client_id = records[0]["id"]
    written = proposal.get("clientId")
    if ids.is_valid_id(written, "CLI") and written != client_id:
        return _stop("input", ["案の clientId が仮名 %s の本人と違う" % code])
    proposal = dict(proposal, clientId=client_id)
    checked = intake.check(proposal, original, staff_id, "req-proposal-" + uuid.uuid4().hex)
    if not checked["ok"]:
        return _stop("intake", checked["errors"], checked["warnings"])
    out = gw.submit(checked["request"], driver)
    if not out["ok"]:
        return _stop("gate", out["errors"], checked["warnings"])
    made = [n for n in checked["request"]["nodes"] if n["origin"] == "AiExtracted"]
    return {"ok": True, "pending": len(made), "counts": dict(Counter(n["label"] for n in made)),
            "ids": out.get("ids", {}), "warnings": checked["warnings"],
            "orgChoices": _choices(resource_driver, proposal, out.get("ids", {}))}
