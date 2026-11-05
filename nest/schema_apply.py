"""正典の JSON から個人の側の制約とインデックスを作る（N-19）。

- 一意制約は `{label}_{prop}_unique`、RANGE インデックスは `{label}_{prop}_range` の名前で、IF NOT EXISTS つきで作る。
- ベクトル・全文インデックスは作らない（ADR-001 D11-1。埋め込みを使わない）。正典に書かれていても拒否する。
- ラベル・プロパティの名前は英数字だけを許す（文に埋め込むため）。
手本：tsunagu-net の tsunagu/schema_apply.py（読むだけ）。nest-support の正典は個人の側だけを持つ。
"""
import re

SAFE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
ALLOWED_INDEX_KINDS = {"RANGE"}


def _safe(name):
    if not isinstance(name, str) or not SAFE_NAME.match(name):
        raise ValueError("ラベル・プロパティの名前として使えない: %r" % (name,))
    return name


def constraint_name(label, prop):
    return "%s_%s_unique" % (_safe(label), _safe(prop))


def index_name(label, prop):
    return "%s_%s_range" % (_safe(label), _safe(prop))


def expected_constraint_names(c):
    return [constraint_name(label, p) for label, spec in sorted(c["personal"]["nodes"].items()) for p in spec["unique"]]


def expected_index_names(c):
    return [index_name(idx["label"], idx["property"]) for idx in c.get("indexes", [])]


def statements(c):
    out = []
    for label, spec in sorted(c["personal"]["nodes"].items()):
        for prop in spec["unique"]:
            out.append("CREATE CONSTRAINT %s IF NOT EXISTS FOR (n:%s) REQUIRE n.%s IS UNIQUE"
                       % (constraint_name(label, prop), _safe(label), _safe(prop)))
    for idx in c.get("indexes", []):
        if idx.get("kind") not in ALLOWED_INDEX_KINDS:
            raise ValueError("個人の側に作れないインデックスの種類: %s" % idx.get("kind"))
        out.append("CREATE INDEX %s IF NOT EXISTS FOR (n:%s) ON (n.%s)"
                   % (index_name(idx["label"], idx["property"]), _safe(idx["label"]), _safe(idx["property"])))
    return out


def apply(driver, c, database="neo4j"):
    for stmt in statements(c):
        driver.execute_query(stmt, database_=database)
