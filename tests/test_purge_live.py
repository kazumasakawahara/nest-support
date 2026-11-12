"""N-32：本人のデータの廃棄を、試験用の DB（127.0.0.1:36687）で確かめる。NEST_LIVE_DB=1 のときだけ。

    NEST_LIVE_DB=1 uv run pytest -q tests/test_purge_live.py

架空のデータだけ。試験ごとに、架空の本人 A・B と、二人の親（共通の人）・A だけのきょうだい・A の記録（機関から受け取った書面を含む）を作る。
確かめること（計画 N-32、台帳 G-74）：AI の案や Administrator でない職員からは保存の判断を書けない／判断（Delete）が無ければ試しの実行でも動かない／
試しの実行は何も消さず、件数と他の機関から受け取った記録の件数を出す／仮名の打ち返しが要る／人の操作だけで消え、Purge の監査ログが 1 件残る／
B と、B にもつながる親には触れない。
G-77 の直し（2026-11-06 河原さん）：本人の記録の documentHash に合う音声を、同じ操作の中で消す。試しの実行では件数を出す。
"""
import datetime as dt
import hashlib
import os
import sys
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

REPO = Path(__file__).resolve().parents[1]
ORG = "ORG-01HYYYYYYYYYYYYYYYYYYYYYYY"


@pytest.fixture(scope="module")
def driver():
    from nest import connections
    with connections.driver("personal") as d:
        d.verify_connectivity()
        yield d


def _one(driver, query, **params):
    records, _, _ = driver.execute_query(query, params, routing_="r", database_="neo4j")
    return [r.data() for r in records]


def _n(driver, query, **params):
    return _one(driver, query, **params)[0]["n"]


@pytest.fixture(scope="module")
def admin(driver):
    from nest.gate import bootstrap
    rows = _one(driver, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")
    if rows:
        return rows[0]["id"]
    out = bootstrap.bootstrap_admin(driver, "架空の管理者", "req-bootstrap-" + uuid.uuid4().hex)
    assert out["ok"], out["errors"]
    return out["staffId"]


def _hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rec(text, **extra):
    return dict({"kind": "Interview", "text": text, "quote": text, "certainty": "Hearsay", "informantKind": "Family"}, **extra)


def _submit(driver, admin, nodes, rels):
    from nest.gate import write as gw
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin, "nodes": nodes, "relationships": rels}, driver)
    assert out["ok"], out["errors"]
    return out["ids"]


def _related(person, client, record, kind):
    return {"type": "RELATED_TO", "from": {"label": "Person", "id": person}, "to": {"label": "Client", "id": client},
            "properties": {"kind": kind, "certainty": "Hearsay", "evidenceRecordIds": [record], "status": "Active"}}


@pytest.fixture
def pair(driver, admin):
    """架空の本人 A・B。親 P は二人に、きょうだい S は A だけにつながる。"""
    mark = uuid.uuid4().hex[:8]
    h = lambda ref, label, props: {"ref": ref, "label": label, "origin": "Human", "properties": props}  # noqa: E731
    staff = {"label": "Staff", "id": admin}
    ids = _submit(driver, admin, [h("a", "Client", {"familyName": "架空"}), h("b", "Client", {"familyName": "架空"}),
                                  h("p", "Person", {}), h("s", "Person", {})], [])
    A, B = {"label": "Client", "id": ids["a"]}, {"label": "Client", "id": ids["b"]}
    more = _submit(driver, admin, [
        h("ra", "Record", _rec("架空 %s：母によると、A はエビで息が苦しくなる" % mark, documentHash=_hash("架空の録音 A " + mark))),
        h("rp", "Record", _rec("架空 %s：相談の窓口からの書面" % mark, kind="Document", informantKind="Agency",
                               providerCertainty="Confirmed")),
        h("rb", "Record", _rec("架空 %s：B の話" % mark, documentHash=_hash("架空の録音 B " + mark))),
        h("ng", "NgAction", {"action": "エビを食べさせる", "riskLevel": "LifeThreatening"}),
        h("cr", "CareRole", {"name": "架空：通院の付き添い"}),
        h("i", "Involvement", {"kind": "ServiceProvision", "howEnded": "Ongoing", "certainty": "Hearsay"}),
        h("org", "Organization", {"orgId": ORG}),
    ], [{"type": "ABOUT", "from": "ra", "to": A}, {"type": "ABOUT", "from": "rp", "to": A}, {"type": "ABOUT", "from": "rb", "to": B},
        {"type": "AUTHORED_BY", "from": "ra", "to": staff}, {"type": "AUTHORED_BY", "from": "rp", "to": staff},
        {"type": "AUTHORED_BY", "from": "rb", "to": staff},
        {"type": "TOLD_BY", "from": "ra", "to": {"label": "Person", "id": ids["p"]}},
        {"type": "PROVIDED_BY", "from": "rp", "to": "org"},
        {"type": "MUST_AVOID", "from": A, "to": "ng"}, {"type": "EVIDENCED_BY", "from": "ng", "to": "ra"},
        {"type": "ROLE_FOR", "from": "cr", "to": A}, {"type": "EVIDENCED_BY", "from": "cr", "to": "ra"},
        {"type": "PERFORMS", "from": {"label": "Person", "id": ids["s"]}, "to": "cr"},
        {"type": "CONCERNS", "from": "i", "to": A}, {"type": "HAS_INVOLVEMENT", "from": "org", "to": "i"},
        {"type": "EVIDENCED_BY", "from": "i", "to": "ra"}])
    _submit(driver, admin, [], [_related(ids["p"], ids["a"], more["ra"], "Parent"), _related(ids["p"], ids["b"], more["rb"], "Parent"),
                                _related(ids["s"], ids["a"], more["ra"], "Sibling")])
    code = _one(driver, "MATCH (c:Client {clientId: $id}) RETURN c.displayCode AS code", id=ids["a"])[0]["code"]
    return dict(ids, **more, code=code, mark=mark)


def _decide(driver, actor, client, decision):
    from nest.gate import write as gw
    return gw.record_retention(driver, actor, client, str(dt.date.today()), decision, "架空：保存の期間を過ぎた",
                               "req-" + uuid.uuid4().hex)


def _total(driver):
    return _n(driver, "MATCH (n) RETURN count(n) AS n")


def test_without_a_decision_even_the_dry_run_refuses(driver, admin, pair):
    from nest.gate import purge
    out = purge.purge(driver, admin, pair["code"])
    assert not out["ok"] and any("保存の判断" in e for e in out["errors"])


def test_decision_cannot_come_from_ai_or_a_non_administrator(driver, admin, pair):
    from nest.gate import write as gw
    req = gw.retention_request(admin, pair["a"], str(dt.date.today()), "Delete", "架空", "req-" + uuid.uuid4().hex)
    req["nodes"][0]["origin"] = "AiExtracted"
    assert not gw.submit(req, driver)["ok"]
    staff = _submit(driver, admin, [{"ref": "st", "label": "Staff", "origin": "Human",
                                     "properties": {"displayName": "架空の職員", "role": "Staff"}}], [])["st"]
    out = _decide(driver, staff, pair["a"], "Delete")
    assert not out["ok"] and any("Administrator" in e for e in out["errors"])
    assert _n(driver, "MATCH (:RetentionDecision)-[:DECIDES_ON]->(:Client {clientId: $id}) RETURN count(*) AS n", id=pair["a"]) == 0


def test_a_later_keep_decision_stops_the_purge(driver, admin, pair):
    from nest.gate import purge
    assert _decide(driver, admin, pair["a"], "Delete")["ok"]
    assert _decide(driver, admin, pair["a"], "Keep")["ok"]
    out = purge.purge(driver, admin, pair["code"])
    assert not out["ok"] and any("Delete" in e for e in out["errors"])


def test_dry_run_reports_counts_and_writes_nothing(driver, admin, pair):
    from nest.gate import purge
    assert _decide(driver, admin, pair["a"], "Delete")["ok"]
    before = _total(driver)
    out = purge.purge(driver, admin, pair["code"])
    assert out["ok"], out["errors"]
    assert out["written"] is False and _total(driver) == before
    assert set(out["purgedCounts"]) == {"Client:1", "Person:1", "Record:2", "NgAction:1", "CareRole:1", "Involvement:1",
                                        "RetentionDecision:1"}
    assert out["providedRecords"] == 1 and out["keptPersons"] == 1 and out["keptLinked"] == ["Person:1"]


def test_write_needs_the_display_code_echoed(driver, admin, pair):
    from nest.gate import purge
    assert _decide(driver, admin, pair["a"], "Delete")["ok"]
    before = _total(driver)
    for confirm in (None, "C-ZZZZZZ" if pair["code"] != "C-ZZZZZZ" else "C-YYYYYY"):
        out = purge.purge(driver, admin, pair["code"], write=True, confirm=confirm)
        assert not out["ok"] and any("打ち返し" in e for e in out["errors"])
    assert _total(driver) == before


def test_write_purges_only_this_client_and_leaves_one_purge_log(driver, admin, pair):
    from nest.gate import purge
    assert _decide(driver, admin, pair["a"], "Delete")["ok"]
    old_logs = _n(driver, "MATCH (a:AuditLog) RETURN count(a) AS n")
    out = purge.purge(driver, admin, pair["code"], write=True, confirm=pair["code"])
    assert out["ok"] and out["written"], out["errors"]
    for label, key in (("Client", pair["a"]), ("Person", pair["s"]), ("Record", pair["ra"]), ("Record", pair["rp"]),
                       ("NgAction", pair["ng"]), ("CareRole", pair["cr"]), ("Involvement", pair["i"])):
        prop = {"Client": "clientId", "Person": "personId", "Record": "recordId", "NgAction": "ngActionId",
                "CareRole": "careRoleId", "Involvement": "involvementId"}[label]
        assert _n(driver, "MATCH (n:%s {%s: $id}) RETURN count(n) AS n" % (label, prop), id=key) == 0, label
    # B と、B にもつながる親は残る。機関の写しも残る
    assert _n(driver, "MATCH (:Person {personId: $p})-[:RELATED_TO]->(:Client {clientId: $b}) RETURN count(*) AS n",
              p=pair["p"], b=pair["b"]) == 1
    assert _n(driver, "MATCH (:Person {personId: $p})-[:RELATED_TO]->(c:Client) RETURN count(c) AS n", p=pair["p"]) == 1
    assert _n(driver, "MATCH (:Record {recordId: $r})-[:ABOUT]->(:Client {clientId: $b}) RETURN count(*) AS n",
              r=pair["rb"], b=pair["b"]) == 1
    assert _n(driver, "MATCH (o:Organization {orgId: $o}) RETURN count(o) AS n", o=ORG) >= 1
    # 監査ログ：今までのものは残り、Purge が 1 件だけ増える。件数だけで、名前・理由は無い
    assert _n(driver, "MATCH (a:AuditLog) RETURN count(a) AS n") == old_logs + 1
    log = _one(driver, "MATCH (a:AuditLog {action: 'Purge', targetId: $id})-[:ACTED_BY]->(:Staff {staffId: $s}) "
                       "RETURN properties(a) AS p", id=pair["a"], s=admin)
    assert len(log) == 1
    p = log[0]["p"]
    assert p["retentionId"] == out["retentionId"] and p["keptPersons"] == 1 and "Client:1" in p["purgedCounts"]
    assert not {"reason", "displayCode", "familyName"} & set(p)
    # 今までの監査ログは残り、相手が消えたので AUDIT_FOR は外れている（ID の文字だけ残る）
    assert _n(driver, "MATCH (a:AuditLog {targetId: $id, action: 'Create'}) RETURN count(a) AS n", id=pair["a"]) >= 1
    assert _n(driver, "MATCH (a:AuditLog {targetId: $id})-[:AUDIT_FOR]->() RETURN count(a) AS n", id=pair["a"]) == 0


def test_the_command_line_runs_a_dry_run(driver, admin, pair, capsys):
    sys.path.insert(0, str(REPO / "scripts"))
    import purge_client
    assert purge_client.main(["decide", "--admin", admin, "--code", pair["code"], "--decision", "Delete",
                              "--decided-on", str(dt.date.today()), "--reason", "架空"], driver=driver) == 0
    assert purge_client.main(["purge", "--admin", admin, "--code", pair["code"]], driver=driver) == 0
    text = capsys.readouterr().out
    assert "試しの実行" in text and "PROVIDED_BY あり）：1 件" in text and "音声" in text
    assert _n(driver, "MATCH (c:Client {clientId: $id}) RETURN count(c) AS n", id=pair["a"]) == 1


def test_purge_removes_this_clients_voice_in_the_same_operation(driver, admin, pair, tmp_path):
    from nest.gate import purge
    assert _decide(driver, admin, pair["a"], "Delete")["ok"]
    root = tmp_path / "nest_voice_data"
    root.mkdir()
    files = {k: root / (_hash("架空の録音 %s %s" % (k, pair["mark"])) + ".webm") for k in ("A", "B", "X")}
    for f in files.values():
        f.write_bytes(b"x")
    dry = purge.purge(driver, admin, pair["code"], voice_root=root)
    assert dry["ok"] and dry["voiceFiles"] == 1 and all(f.exists() for f in files.values())
    out = purge.purge(driver, admin, pair["code"], write=True, confirm=pair["code"], voice_root=root)
    assert out["ok"] and out["written"] and out["voiceFilesRemoved"] == 1, out
    assert not files["A"].exists() and files["B"].exists() and files["X"].exists()
