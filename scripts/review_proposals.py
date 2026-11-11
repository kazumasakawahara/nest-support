"""書き込みの案（未確定のもの）を点検し、一つずつ承認・差し戻しする（計画 N-44。2026-11-06 河原さん）。職員が手元で打つ。

- list：未確定（Pending）の一覧を古い順（registeredAt）に出す。本人は仮名（displayCode）で出す。実名は出さない。
  --code C-…… で本人に絞る。本人「―」は、どの本人にも結ばれていないもの（2026-11-11 河原さん）
- show：一件の中身を「対象の項目（正典の順。項目は SEMANTICS SEM-FIELD-01 の表示名、列挙値は表示名を添える）→ 根拠の引用（記録の quote）」の順に出す。
  伏せる項目（実名・かな・電話・住所・生年月日）と、ゲートが付ける項目（ID・状態・由来・登録日時・指紋）は出さない。
  関わりには、結ばれた機関の名前（資源の側から引く。無ければ「機関未確定」）も出す（2026-11-11 河原さん）
- list --rejected：差し戻したものを、差し戻した順に理由と出す（台帳 G-91）
- approve・reject：一件ずつ承認（Active）・差し戻し（Inactive）する。差し戻しには理由を一行添えられる（--reason。AuditLog の reason。名前を書かない）。ゲートの承認（nest.gate.approve）を通すので、
  AuditLog（Approve・Reject）が残る。自分で登録したものを承認したら selfApproval が付く（自己承認）
- まとめての承認はしない。ID の形から種類（ラベル）を決め、承認の対象でない ID は DB に触れる前に止める

使い方:
  uv run python scripts/review_proposals.py list
  uv run python scripts/review_proposals.py list --code C-……
  uv run python scripts/review_proposals.py show --id REC-…
  uv run python scripts/review_proposals.py approve --staff STF-… --id REC-…
  uv run python scripts/review_proposals.py reject --staff STF-… --id REC-… [--reason "…"]
  uv run python scripts/review_proposals.py list --rejected
"""
import argparse
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest import canon, ids, mcp_guard, semantics  # noqa: E402
from nest.gate import approve as ap  # noqa: E402
from nest.gate import write as gw  # noqa: E402

PENDING = """MATCH (n) WHERE n.status = 'Pending' AND labels(n)[0] IN $labels
OPTIONAL MATCH (n)--(c:Client)
OPTIONAL MATCH (n)<-[:TOLD_BY]-(:Record)-[:ABOUT]->(t:Client)
OPTIONAL MATCH (n)-[:HAS_INVOLVEMENT]-(:Involvement)-[:CONCERNS]->(v:Client)
OPTIONAL MATCH (n)<-[:CONCERNS]-(:Involvement)-[:CONCERNS]->(w:Client)
WITH n, [x IN collect(DISTINCT c.displayCode) + collect(DISTINCT t.displayCode) + collect(DISTINCT v.displayCode)
         + collect(DISTINCT w.displayCode) WHERE x IS NOT NULL] AS codes
RETURN labels(n)[0] AS label, n.origin AS origin, n.registeredAt AS at, codes, n AS node
ORDER BY at, label"""
REJECTED = """MATCH (a:AuditLog {action: 'Reject'})-[:ACTED_BY]->(s:Staff)
WHERE $id IS NULL OR a.targetId = $id
RETURN a.targetLabel AS label, a.targetId AS id, a.at AS at, a.reason AS reason, s.staffId AS by
ORDER BY at, id"""
SCHEMA = REPO / "docs" / "SCHEMA.md"
NOT_SHOWN = set(mcp_guard.SENSITIVE) | {"sourceHash", "documentHash", "quote"}  # quote は根拠の引用の行で出す
DASH = "本人「―」は、どの本人にも結ばれていないもの（本人の記録・関わりのどれともつながっていない）。承認の前に show で中身を見る"


def parse(argv):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list", help="未確定の一覧（古い順）")
    s.add_argument("--rejected", action="store_true", help="差し戻したものを理由と出す")
    s.add_argument("--code", help="本人の仮名（C-……）で絞る")
    s = sub.add_parser("show", help="一件の項目と根拠の引用")
    s.add_argument("--id", required=True)
    for name in ("approve", "reject"):
        s = sub.add_parser(name)
        s.add_argument("--staff", required=True, help="決める職員の ID（STF-…）")
        s.add_argument("--id", required=True)
        if name == "reject":
            s.add_argument("--reason", help="差し戻しの理由を一行（任意。名前を書かない）")
    return p.parse_args(argv)


def is_display_code(code):
    body = code[2:] if code.startswith("C-") else ""
    return len(body) == gw.DISPLAY_CODE_LENGTH and all(ch in ids.DISPLAY_ALPHABET for ch in body)


def label_of(target_id):
    for label, prefix in ids.LABEL_PREFIX.items():
        if label in ap.DECIDABLE and ids.is_valid_id(target_id, prefix):
            return label
    return None


def _print_quotes(quotes, target_id=None):
    if not quotes:
        print("  根拠の引用：無い")
    for q in quotes:
        state = "" if q["recordId"] == target_id else (
            "・未確定。先に承認する" if q.get("status") == "Pending" else "・差し戻し済み" if q.get("status") == "Inactive" else "")
        print("  根拠 %s（確度 %s・話し手 %s%s）：%s" % (q["recordId"], q["certainty"], q["informantKind"], state, q["quote"]))


def _list(d, code=None):
    with d.session(database="neo4j") as s:
        rows = s.execute_read(lambda tx: [r.data() for r in tx.run(PENDING, labels=sorted(ap.DECIDABLE))])
    if code:
        rows = [r for r in rows if code in r["codes"]]
    print("未確定 %d 件（古い順%s）" % (len(rows), "・本人 %s" % code if code else ""))
    for r in rows:
        node_id = r["node"][gw.key_of(r["label"])]
        print("%s  %s  %s  %s  本人 %s" % (node_id, r["label"], r["origin"], r["at"], "・".join(r["codes"]) or "―"))
    if not code and any(not r["codes"] for r in rows):
        print(DASH)
    return 0


def items_of(label, node):
    """承認の対象の項目を、正典の順（必須→任意）に [(項目の表示名, 出す値)] で返す。列挙値は「値（表示名）」。"""
    c = canon.load(SCHEMA)
    spec, names = c["personal"]["nodes"][label], semantics.enum_names()
    fields = semantics.field_names().get(label, {})
    out = []
    for key in spec["required"] + spec["optional"]:
        value = node.get(key)
        if key == gw.key_of(label) or key in NOT_SHOWN or value in (None, ""):
            continue
        if key == "text" and value == node.get("quote"):
            continue  # 引用と同じなら根拠の行で足りる
        enum = c["enumBindings"].get("%s.%s" % (label, key))
        if enum and value in names.get(enum, {}):
            value = "%s（%s）" % (value, names[enum][value])
        out.append((fields.get(key, key), value))
    return out


def _rejected(s, target_id=None):
    return s.execute_read(lambda tx: [r.data() for r in tx.run(REJECTED, id=target_id)])


def _print_rejected(r):
    print("  差し戻し %s（%s）理由：%s" % (r["at"], r["by"], r["reason"] or "―（書いていない）"))


def _list_rejected(d):
    with d.session(database="neo4j") as s:
        rows = _rejected(s)
    print("差し戻したもの %d 件（差し戻した順）" % len(rows))
    for r in rows:
        print("%s  %s" % (r["id"], r["label"]))
        _print_rejected(r)
    return 0


def _org_lines(s, resource_driver, target_id):
    orgs = s.execute_read(lambda tx: [r["orgId"] for r in tx.run(ap.INVOLVEMENT_ORGS, id=target_id)])
    if not orgs:
        return ["  機関：機関未確定"]
    names = ap._org_names(resource_driver, orgs)
    return ["  機関：%s（%s）" % (names.get(o) or "名前を引けない", o) for o in orgs]


def _show(d, label, target_id, resource_driver=None):
    with d.session(database="neo4j") as s:
        rows = s.execute_read(lambda tx: [r.data() for r in tx.run(
            "MATCH (n:%s {%s: $id}) RETURN n AS node" % (label, gw.key_of(label)), id=target_id)])
        if not rows:
            print("止めた：%s %s は無い" % (label, target_id))
            return 1
        quotes = s.execute_read(ap._quotes, label, gw.key_of(label), target_id)
        rejected = _rejected(s, target_id)
        orgs = _org_lines(s, resource_driver, target_id) if label == "Involvement" else []
    node = dict(rows[0]["node"])
    print("%s  %s  状態 %s  由来 %s" % (target_id, label, node.get("status"), node.get("origin")))
    items = items_of(label, node)
    if not items:
        print("  項目：無い")
    for key, value in items:
        print("  %s：%s" % (key, value))
    for line in orgs:
        print(line)
    _print_quotes(quotes, target_id)
    for r in rejected:
        _print_rejected(r)
    return 0


def _decide(d, a, label):
    target, rid = {"label": label, "id": a.id}, "req-review-" + uuid.uuid4().hex
    out = ap.approve(d, a.staff, target, rid) if a.cmd == "approve" else ap.reject(d, a.staff, target, rid, reason=a.reason)
    if not out["ok"]:
        print("止めた：" + "；".join(out["errors"]))
        return 1
    if a.cmd == "approve":
        print("承認した：%s %s → Active" % (label, a.id))
        if out.get("selfApproval"):
            print("自己承認（自分で登録したもの）として記録した（selfApproval）")
    else:
        print("差し戻した：%s %s → Inactive（理由：%s）" % (label, a.id, a.reason or "―（書いていない）"))
    _print_quotes(out["shown"], a.id)
    return 0


def _run(d, a, resource_driver=None):
    if a.cmd == "list":
        return _list_rejected(d) if a.rejected else _list(d, a.code)
    label = label_of(a.id)
    if a.cmd == "show":
        return _show(d, label, a.id, resource_driver)
    return _decide(d, a, label)


def main(argv=None, driver=None, resource_driver=None):
    a = parse(argv)
    if a.cmd == "list" and a.code is not None and not is_display_code(a.code):
        print("止めた：%r は本人の仮名（C-と 6 字）の形でない" % (a.code,))
        return 1
    if a.cmd != "list" and label_of(a.id) is None:
        print("止めた：%r は承認の対象の ID の形でない" % (a.id,))
        return 1
    if driver is not None:
        return _run(driver, a, resource_driver)
    from nest import connections
    with connections.driver("personal") as d:
        if a.cmd == "show" and label_of(a.id) == "Involvement":  # 機関の名前は資源の側から引く（読むだけ）
            with connections.driver("resource") as r:
                return _run(d, a, r)
        return _run(d, a)


if __name__ == "__main__":
    sys.exit(main())
