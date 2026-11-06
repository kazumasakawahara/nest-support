"""本人を作る・名前から仮名を引く、Claude の外の入口（計画 N-39。2026-11-06 河原さん。台帳 G-42 (2)）。

- 職員が手元のターミナルで打つ。Claude には何も渡さない（この道具の出力を Claude の会話に貼らない）。
  MCP の包みには、名前を受け取る道具を作らない（名前と仮名の対応が Claude の側の記録に残るため）
- add：ゲート（nest.gate.write.submit）を通して、本人（Client）と、住所があれば住まい（Residence、RESIDES_AT）を作る。
  人が入れたもの（origin Human）なので、そのまま Active。仮名（displayCode）はゲートが発番し、画面に出す
- 実名・かな・生年月日・住所は DB に入れてよい（読み取りの包みが返さないだけ）
- 二重登録を止める：同じ氏名の本人がいて、生年月日が同じか、どちらかに生年月日が無ければ作らない（今いる本人の仮名を出す）
- find：氏名から仮名を引く（名は省ける）。ほかの項目は出さない

使い方:
  uv run python scripts/new_client.py add --staff STF-… --family 氏 --given 名 [--family-kana …] [--given-kana …]
                                          [--birth YYYY-MM-DD] [--address 住所]
  uv run python scripts/new_client.py find --family 氏 [--given 名]
"""
import argparse
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest.gate import write as gw  # noqa: E402

SAME = """MATCH (c:Client {familyName: $family, givenName: $given})
WHERE $birth IS NULL OR c.birthDate IS NULL OR c.birthDate = date($birth)
RETURN c.displayCode AS code ORDER BY code"""
FIND = """MATCH (c:Client {familyName: $family}) WHERE $given IS NULL OR c.givenName = $given
RETURN c.displayCode AS code ORDER BY code"""
CODE_OF = "MATCH (c:Client {clientId: $id}) RETURN c.displayCode AS code"


def parse(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("--staff", required=True, help="登録する職員の ID（STF-…）")
    add.add_argument("--family", required=True)
    add.add_argument("--given", required=True)
    add.add_argument("--family-kana")
    add.add_argument("--given-kana")
    add.add_argument("--birth", help="YYYY-MM-DD")
    add.add_argument("--address")
    find = sub.add_parser("find")
    find.add_argument("--family", required=True)
    find.add_argument("--given")
    return ap.parse_args(argv)


def client_request(a, request_id):
    props = {"familyName": a.family, "givenName": a.given}
    for key, value in (("familyNameKana", a.family_kana), ("givenNameKana", a.given_kana), ("birthDate", a.birth)):
        if value:
            props[key] = value
    if a.birth:
        props["birthDatePrecision"] = "Day"
    nodes = [{"ref": "c", "label": "Client", "origin": "Human", "properties": props}]
    rels = []
    if a.address:
        nodes.append({"ref": "r", "label": "Residence", "origin": "Human",
                      "properties": {"address": a.address, "certainty": "Confirmed"}})
        rels.append({"type": "RESIDES_AT", "from": "c", "to": "r", "properties": {}})
    return {"requestId": request_id, "actorStaffId": a.staff, "nodes": nodes, "relationships": rels}


def _codes(d, query, **params):
    records, _, _ = d.execute_query(query, params, database_="neo4j")
    return [r["code"] for r in records]


def _add(d, a):
    same = _codes(d, SAME, family=a.family, given=a.given, birth=a.birth)
    if same:
        print("作らなかった：二重登録のおそれ。同じ氏名の本人がいる（%s）。別の人なら生年月日を確かめて入れる" % "・".join(same))
        return 1
    out = gw.submit(client_request(a, "req-new-client-" + uuid.uuid4().hex), d)
    if not out["ok"]:
        print("作らなかった：" + "；".join(out["errors"]))
        return 1
    print("作った。仮名：%s（Claude にはこの仮名で伝える）" % _codes(d, CODE_OF, id=out["ids"]["c"])[0])
    return 0


def _find(d, a):
    codes = _codes(d, FIND, family=a.family, given=a.given)
    if not codes:
        print("見つからない")
        return 1
    for code in codes:
        print(code)
    return 0


def main(argv=None, driver=None):
    a = parse(argv)
    run = _add if a.cmd == "add" else _find
    if driver is not None:
        return run(driver, a)
    from nest import connections
    with connections.driver("personal") as d:
        return run(d, a)


if __name__ == "__main__":
    sys.exit(main())
