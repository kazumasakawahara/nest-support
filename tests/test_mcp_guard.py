"""N-22：読み取りだけの MCP の包み（DB を使わない部分）。

手本：tsunagu-net の枝 claude/tender-dijkstra-xo3wwc のコミット d8e6e2d の tests/test_mcp_resource.py（読むだけ）の例を写した。
強めたところ（2026-11-05 河原さん）：行は流しながら 500 行で止める。EXPLAIN・PROFILE つきと空も拒否。
個人の側は、実名・かな・電話・住所・生年月日を返さない（Residence.address を含む）。
DB の試験は tests/test_mcp_read_live.py（NEST_LIVE_DB=1 のときだけ）。
"""
import datetime as dt
from pathlib import Path

import pytest

from nest import canon, mcp_guard

REPO = Path(__file__).resolve().parents[1]


def _plan(*ops, children=None):
    node = None
    for op, details in reversed(ops):
        node = {"operatorType": op + "@neo4j", "args": {"Details": details},
                "children": [node] if node else list(children or [])}
    return node


READ_PLAN = _plan(("ProduceResults", "n"), ("NodeByLabelScan", "n:Record"))


class FakeSummary:
    def __init__(self, query_type, plan):
        self.query_type, self.plan = query_type, plan


class FakeDriver:
    def __init__(self, query_type, plan=READ_PLAN):
        self.query_type, self.plan, self.calls = query_type, plan, []

    def execute_query(self, query, parameters=None, **kw):
        self.calls.append((query, kw))
        return [], FakeSummary(self.query_type, self.plan), []


def _refused(driver, query="MATCH (n) RETURN n", personal=False):
    with pytest.raises(mcp_guard.NotReadOnly) as e:
        mcp_guard.check_read_only(driver, query, {}, personal=personal)
    assert all(c[0].startswith("EXPLAIN ") for c in driver.calls)  # EXPLAIN だけ。本体は流さない
    return str(e.value)


@pytest.mark.parametrize("query_type", ["w", "rw", "s"])
def test_non_read_queries_are_refused_before_running(query_type):
    _refused(FakeDriver(query_type), "CREATE INDEX x FOR (n:A) ON (n.b)")


def test_read_query_passes():
    assert mcp_guard.check_read_only(FakeDriver("r"), "MATCH (n:Record) RETURN n.quote", {}) == "MATCH (n:Record) RETURN n.quote"


@pytest.mark.parametrize("query", ["EXPLAIN MATCH (n) RETURN n", "PROFILE MATCH (n) RETURN n", "explain MATCH (n) RETURN n", "", "   ", None])
def test_prefixed_or_empty_queries_are_refused(query):
    d = FakeDriver("r")
    _refused(d, query)
    assert d.calls == []


def test_load_csv_is_refused_although_it_is_a_read():
    msg = _refused(FakeDriver("r", _plan(("ProduceResults", "r"), ("LoadCSV", "r"))))
    assert "LOAD CSV" in msg


def test_load_csv_deep_in_a_branching_plan_is_refused():
    branch = [_plan(("NodeByLabelScan", "n:Record")), _plan(("Apply", ""), ("LoadCSV", "r"))]
    _refused(FakeDriver("r", _plan(("ProduceResults", "n"), ("CartesianProduct", ""), children=branch)))


@pytest.mark.parametrize("proc", sorted(mcp_guard.ALLOWED_PROCEDURES))
def test_allowed_procedures_pass(proc):
    plan = _plan(("ProduceResults", "x"), ("ProcedureCall", "%s() :: (x :: STRING)" % proc))
    mcp_guard.check_read_only(FakeDriver("r", plan), "CALL %s()" % proc, {})


@pytest.mark.parametrize("details", [
    "db.info() :: (id :: STRING, name :: STRING, creationDate :: STRING)",
    "dbms.components() :: (name :: STRING)",
    "apoc.meta.schema() :: (value :: MAP)",
    "db.labelsX() :: (label :: STRING)",
    "db.labels",
    "",
])
def test_other_procedures_are_refused(details):
    _refused(FakeDriver("r", _plan(("ProduceResults", "x"), ("ProcedureCall", details))))


def test_allowlist_is_small_and_has_no_apoc():
    assert mcp_guard.ALLOWED_PROCEDURES == {"db.labels", "db.relationshipTypes", "db.propertyKeys"}


@pytest.mark.parametrize("plan", [None, {}, "plan", {"operatorType": ""}])
def test_unreadable_plan_is_refused(plan):
    _refused(FakeDriver("r", plan))


# --- 行は流しながら 500 行で止める ---

class _Rec:
    def __init__(self, i):
        self.i = i

    def items(self):
        return [("i", self.i)]


class _Tx:
    def __init__(self, counter):
        self.counter = counter

    def run(self, query, params=None):
        def gen():
            i = 0
            while True:  # 終わりの無い結果。全部を受け取ってから切る作りなら、ここで止まらない
                self.counter["pulled"] += 1
                yield _Rec(i)
                i += 1
        return gen()


def test_rows_stop_at_the_limit_while_streaming():
    counter = {"pulled": 0}
    rows = mcp_guard.stream_rows(_Tx(counter), "UNWIND range(1, 1000000) AS i RETURN i", {}, personal=False)
    assert len(rows) == mcp_guard.MAX_ROWS == 500
    assert counter["pulled"] == 501  # 上限の次の 1 行だけ読んで、切れたかを知る（台帳 G-87）


def test_limit_is_not_injected_into_the_query():
    src = (REPO / "nest" / "mcp_guard.py").read_text(encoding="utf-8")
    assert "LIMIT" not in src.replace("上限", "")


# --- 個人の側の伏せ字 ---

SENSITIVE = ["familyName", "givenName", "familyNameKana", "givenNameKana", "phone", "address", "birthDate"]


def test_sensitive_names_exist_in_the_canon():
    c = canon.load(REPO / "docs" / "SCHEMA.md")
    props = {p for spec in c["personal"]["nodes"].values() for p in spec["required"] + spec["optional"]}
    assert set(mcp_guard.SENSITIVE) == set(SENSITIVE)
    assert set(SENSITIVE) <= props


@pytest.mark.parametrize("query", [
    "MATCH (c:Client) RETURN c.familyName",
    "MATCH (c:Client) RETURN c.FAMILYNAME",
    "MATCH (c:Client) RETURN c.`givenNameKana`",
    "MATCH (p:Person) RETURN p.phone",
    "MATCH (r:Residence) RETURN r.address",
    "MATCH (c:Client) WHERE c.birthDate > date('2000-01-01') RETURN c.clientId",
    "MATCH (c:Client) RETURN properties(c)",
    "MATCH (c:Client) RETURN keys(c)",
    "MATCH (c:Client) RETURN c {.*}",
    "MATCH (c:Client) RETURN c { .* }",
    "MATCH (c:Client) RETURN c['family' + 'Name']",
    "MATCH (c:Client) RETURN c [$k]",
    "MATCH (c:Client) WITH c, 'x' AS k RETURN c[k]",
    "MATCH (c:Client) RETURN (c)['x']",
    # 注釈をはさんで角かっこの前を隠す（2026-11-05 自動のセキュリティ点検の指摘）
    "MATCH (c:Client) RETURN c/**/['family' + 'Name']",
    "MATCH (c:Client) RETURN c //\n['family' + 'Name']",
    "MATCH (c:Client) RETURN c.clientId // 注釈",
    "MATCH (c:Client) RETURN {a: c}['a']['family' + 'Name']",
    "MATCH (c:Client) RETURN c\t['x']",
    # 語の後ろだけが IN などに見える変数名（2 回目の自動の点検の指摘）
    "MATCH (あIN:Client) RETURN あIN['family' + 'Name']",
    "MATCH (c1IN:Client) RETURN c1IN['family' + 'Name']",
    "MATCH (c:Client) WITH c AS ｃIN RETURN ｃIN['x']",
])
def test_personal_side_refuses_sensitive_or_dynamic_access(query):
    d = FakeDriver("r")
    _refused(d, query, personal=True)
    assert d.calls == []


@pytest.mark.parametrize("query", [
    "MATCH (c:Client) RETURN c.displayCode, c.clientId",
    "RETURN [1, 2, 3][0]",
    "WITH [1, 2, 3] AS xs RETURN xs[1..2], xs[-1]",
    # 引用（quote）を自由な Cypher で読む例は、台帳 G-42 で拒否する側に移した（tests/test_mcp_personal_gate.py）
    "UNWIND [1, 2] AS i RETURN i",
    "MATCH (c:Client) WHERE c.clientId IN ['CLI-1'] RETURN c",
])
def test_personal_side_lets_ordinary_reads_through(query):
    assert mcp_guard.check_read_only(FakeDriver("r"), query, {}, personal=True) == query


def test_resource_side_does_not_apply_the_personal_masks():
    mcp_guard.check_read_only(FakeDriver("r"), "MATCH (o:Organization) RETURN o.phone, o.address", {}, personal=False)


class FakeNode(dict):
    def __init__(self, labels, props):
        super().__init__(props)
        self.labels = frozenset(labels)


def test_redaction_of_nodes_maps_and_lists():
    node = FakeNode(["Client"], {"clientId": "CLI-1", "displayCode": "C-ABCDEF", "familyName": "架空",
                                 "birthDate": dt.date(2000, 1, 1)})
    out = mcp_guard.to_plain({"c": node, "m": {"address": "架空市", "areaCode": "401307"}, "xs": [node]}, personal=True)
    assert out["c"] == {"_labels": ["Client"], "clientId": "CLI-1", "displayCode": "C-ABCDEF"}
    assert out["m"] == {"areaCode": "401307"}
    assert out["xs"][0]["_labels"] == ["Client"] and "familyName" not in out["xs"][0]


def test_exact_sensitive_values_are_masked_wherever_they_appear():
    out = mcp_guard.to_plain({"x": "架空", "q": "架空の人が言った"}, personal=True, sensitive_values={"架空"})
    assert out == {"x": mcp_guard.MASK, "q": "架空の人が言った"}  # 文の中の部分一致は伏せない。引用は read_quote でだけ返す（台帳 G-42）


def test_resource_side_returns_nodes_as_they_are():
    node = FakeNode(["Organization"], {"orgId": "ORG-1", "phone": "000"})
    assert mcp_guard.to_plain(node, personal=False) == {"_labels": ["Organization"], "orgId": "ORG-1", "phone": "000"}


def test_each_server_connects_to_its_own_side_only():
    personal = (REPO / "nest" / "mcp_personal.py").read_text(encoding="utf-8")
    resource = (REPO / "nest" / "mcp_resource.py").read_text(encoding="utf-8")
    assert 'driver("personal")' in personal and 'driver("resource")' not in personal
    assert 'driver("resource")' in resource and 'driver("personal")' not in resource
    assert "personal=True" in personal


class _FiniteTx:
    def __init__(self, n):
        self.n = n

    def run(self, query, params=None):
        return (_Rec(i) for i in range(self.n))


def test_cut_rows_are_marked_truncated():
    """合流前の直し 2（2026-11-06 河原さん。台帳 G-87）：上限より多ければ truncated と上限の値を返す。行の形は変えない"""
    out = mcp_guard.stream(_Tx({"pulled": 0}), "UNWIND range(1, 1000000) AS i RETURN i", {}, personal=False)
    assert out["truncated"] is True and out["maxRows"] == mcp_guard.MAX_ROWS and len(out["rows"]) == mcp_guard.MAX_ROWS
    assert out["rows"][0] == {"i": 0}


@pytest.mark.parametrize("n", [0, 3, 500])
def test_rows_up_to_the_limit_are_not_truncated(n):
    out = mcp_guard.stream(_FiniteTx(n), "MATCH (n) RETURN n", {}, personal=False)
    assert out["truncated"] is False and len(out["rows"]) == n
