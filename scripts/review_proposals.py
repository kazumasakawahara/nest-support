"""書き込みの案（未確定のもの）を点検し、一つずつ承認・差し戻しする（計画 N-44。2026-11-06 河原さん）。職員が手元で打つ。

- list：未確定（Pending）の一覧を古い順（registeredAt）に出す。本人は仮名（displayCode）で出す。実名は出さない
- show：一件の根拠の引用（記録の quote）を出す
- approve・reject：一件ずつ承認（Active）・差し戻し（Inactive）する。ゲートの承認（nest.gate.approve）を通すので、
  AuditLog（Approve・Reject）が残る。自分で登録したものを承認したら selfApproval が付く（自己承認）
- まとめての承認はしない。ID の形から種類（ラベル）を決め、承認の対象でない ID は DB に触れる前に止める

使い方:
  uv run python scripts/review_proposals.py list
  uv run python scripts/review_proposals.py show --id REC-…
  uv run python scripts/review_proposals.py approve --staff STF-… --id REC-…
  uv run python scripts/review_proposals.py reject --staff STF-… --id REC-…
"""
import argparse
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest import ids  # noqa: E402
from nest.gate import approve as ap  # noqa: E402
from nest.gate import write as gw  # noqa: E402

PENDING = """MATCH (n) WHERE n.status = 'Pending' AND labels(n)[0] IN $labels
OPTIONAL MATCH (n)--(c:Client)
OPTIONAL MATCH (n)<-[:TOLD_BY]-(:Record)-[:ABOUT]->(t:Client)
WITH n, [x IN collect(DISTINCT c.displayCode) + collect(DISTINCT t.displayCode) WHERE x IS NOT NULL] AS codes
RETURN labels(n)[0] AS label, n.origin AS origin, n.registeredAt AS at, codes, n AS node
ORDER BY at, label"""


def parse(argv):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="未確定の一覧（古い順）")
    s = sub.add_parser("show", help="一件の根拠の引用")
    s.add_argument("--id", required=True)
    for name in ("approve", "reject"):
        s = sub.add_parser(name)
        s.add_argument("--staff", required=True, help="決める職員の ID（STF-…）")
        s.add_argument("--id", required=True)
    return p.parse_args(argv)


def label_of(target_id):
    for label, prefix in ids.LABEL_PREFIX.items():
        if label in ap.DECIDABLE and ids.is_valid_id(target_id, prefix):
            return label
    return None


def _print_quotes(quotes):
    if not quotes:
        print("  根拠の引用：無い")
    for q in quotes:
        print("  根拠 %s（確度 %s・話し手 %s）：%s" % (q["recordId"], q["certainty"], q["informantKind"], q["quote"]))


def _list(d):
    with d.session(database="neo4j") as s:
        rows = s.execute_read(lambda tx: [r.data() for r in tx.run(PENDING, labels=sorted(ap.DECIDABLE))])
    print("未確定 %d 件（古い順）" % len(rows))
    for r in rows:
        node_id = r["node"][gw.key_of(r["label"])]
        print("%s  %s  %s  %s  本人 %s" % (node_id, r["label"], r["origin"], r["at"], "・".join(r["codes"]) or "―"))
    return 0


def _show(d, label, target_id):
    with d.session(database="neo4j") as s:
        rows = s.execute_read(lambda tx: [r.data() for r in tx.run(
            "MATCH (n:%s {%s: $id}) RETURN n.status AS status, n.origin AS origin" % (label, gw.key_of(label)), id=target_id)])
        if not rows:
            print("止めた：%s %s は無い" % (label, target_id))
            return 1
        quotes = s.execute_read(ap._quotes, label, gw.key_of(label), target_id)
    print("%s  %s  状態 %s  由来 %s" % (target_id, label, rows[0]["status"], rows[0]["origin"]))
    _print_quotes(quotes)
    return 0


def _decide(d, a, label):
    fn = ap.approve if a.cmd == "approve" else ap.reject
    out = fn(d, a.staff, {"label": label, "id": a.id}, "req-review-" + uuid.uuid4().hex)
    if not out["ok"]:
        print("止めた：" + "；".join(out["errors"]))
        return 1
    if a.cmd == "approve":
        print("承認した：%s %s → Active" % (label, a.id))
        if out.get("selfApproval"):
            print("自己承認（自分で登録したもの）として記録した（selfApproval）")
    else:
        print("差し戻した：%s %s → Inactive" % (label, a.id))
    _print_quotes(out["shown"])
    return 0


def _run(d, a):
    if a.cmd == "list":
        return _list(d)
    label = label_of(a.id)
    if a.cmd == "show":
        return _show(d, label, a.id)
    return _decide(d, a, label)


def main(argv=None, driver=None):
    a = parse(argv)
    if a.cmd != "list" and label_of(a.id) is None:
        print("止めた：%r は承認の対象の ID の形でない" % (a.id,))
        return 1
    if driver is not None:
        return _run(driver, a)
    from nest import connections
    with connections.driver("personal") as d:
        return _run(d, a)


if __name__ == "__main__":
    sys.exit(main())
