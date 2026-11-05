"""機関の候補（N-24。ADR-001 D3）。原文の名前から、資源の側の機関の候補を出す。読むだけ。選ぶのは人。

- 名前は Unicode の NFKC にそろえ、空白（全角の空白を含む）を除いてから、機関の名前と別名（OrgName）に含まれるかで引く
- 点数づけ・並べ替えの重みづけをしない。名前の順に並べ、上限を超えたら切ったことを示す（truncated）
- 返すのは候補だけ。chosen はいつも None（候補から職員が選び、intake.check の provider_org_id で渡す）
- 一致が無ければ空。似た名前を推測で足さない
"""
import re
import unicodedata

CANDIDATE_KEYS = {"orgId", "name", "kind", "matchedBy"}
MIN_LENGTH = 2
SEARCH = """MATCH (o:Organization {status: 'Active'})
WITH o, replace(replace(normalize(o.name, NFKC), ' ', ''), '　', '') AS own
OPTIONAL MATCH (o)-[:HAS_NAME]->(x:OrgName)
WITH o, own, collect(replace(replace(normalize(x.name, NFKC), ' ', ''), '　', '')) AS aliases
WHERE own CONTAINS $name OR any(a IN aliases WHERE a CONTAINS $name)
RETURN o.orgId AS orgId, o.name AS name, o.kind AS kind,
       CASE WHEN own CONTAINS $name THEN 'name' ELSE 'alias' END AS matchedBy
ORDER BY name, orgId"""


def _key(name):
    if not isinstance(name, str):
        raise ValueError("名前は文字列")
    key = re.sub(r"\s+", "", unicodedata.normalize("NFKC", name))
    if len(key) < MIN_LENGTH:
        raise ValueError("名前が短すぎる（%d 字以上）" % MIN_LENGTH)
    return key


def by_name(driver, name, limit=20, database="neo4j"):
    key = _key(name)
    rows = []
    with driver.session(database=database) as s:
        def work(tx):
            out = []
            for record in tx.run(SEARCH, name=key):
                out.append({k: record[k] for k in CANDIDATE_KEYS})
                if len(out) > limit:
                    break
            return out
        rows = s.execute_read(work)
    return {"query": name, "candidates": rows[:limit], "truncated": len(rows) > limit, "chosen": None}
