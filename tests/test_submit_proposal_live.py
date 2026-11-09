"""N-46 詰まり #7：手順書（docs/OPERATIONS.md 4.5 (c)）の submit_proposal の行を、起動した個人の側でそのまま流す。
NEST_LIVE_DB=1 のときだけ。

- 点検で止まる案は何も入れない（未確定の数が変わらない）
- 通った案は未確定（Pending）で入り、review_proposals.py list に記録の ID と仮名が並ぶ
"""
import importlib.util
import json
import os
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("doc_commands", REPO / "tests" / "doc_commands.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


def _q(d, query, **params):
    records, _, _ = d.execute_query(query, params, database_="neo4j")
    return [r.data() for r in records]


@pytest.fixture
def driver():
    from nest import connections
    with connections.driver("personal") as d:
        yield d


@pytest.fixture
def setup(driver, tmp_path):
    from nest.gate import write as gw
    admin = _q(driver, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")[0]["id"]
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                     "nodes": [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空"}}],
                     "relationships": []}, driver)
    assert out["ok"], out["errors"]
    code = _q(driver, "MATCH (c:Client {clientId: $id}) RETURN c.displayCode AS code", id=out["ids"]["c"])[0]["code"]
    word = uuid.uuid4().hex[:6]
    quote = "本人は、音楽 %s を聴くと落ち着くと話した" % word
    original = tmp_path / "original.txt"
    original.write_text("架空の面談記録\n%s【本人の話】\n" % quote, encoding="utf-8")
    return {"admin": admin, "code": code, "quote": quote, "original": original, "dir": tmp_path}


def _submit(setup, facts, driver):
    proposal = setup["dir"] / ("proposal-%s.json" % uuid.uuid4().hex[:6])
    proposal.write_text(json.dumps({"documentKind": "OwnCaseRecord", "facts": facts}, ensure_ascii=False), encoding="utf-8")
    line = dc.lines("submit_proposal.py")[0]
    args = dc.argv(line, {"STF-…": setup["admin"], "C-……": setup["code"]})
    args[args.index("--original") + 1] = str(setup["original"])
    args[args.index("--proposal") + 1] = str(proposal)
    return dc.load("submit_proposal.py").main(args, driver=driver)


def _pending(driver):
    return _q(driver, "MATCH (n {status: 'Pending'}) RETURN count(n) AS n")[0]["n"]


def test_rejected_proposal_adds_nothing(driver, setup):
    before = _pending(driver)
    bad = [{"quote": setup["quote"].replace("音楽", "ジャズ"), "recordKind": "Interview",
            "certainty": "SelfReport", "informantKind": "Self"}]
    assert _submit(setup, bad, driver) == 1
    assert _pending(driver) == before


def test_passed_proposal_is_pending_and_listed(driver, setup, capsys):
    good = [{"quote": setup["quote"], "recordKind": "Interview", "certainty": "SelfReport", "informantKind": "Self",
             "toldBy": "client"}]
    assert _submit(setup, good, driver) == 0
    rec = _q(driver, "MATCH (r:Record {quote: $q}) RETURN r.recordId AS id, r.status AS status", q=setup["quote"])
    assert len(rec) == 1 and rec[0]["status"] == "Pending"
    capsys.readouterr()
    line = next(l for l in dc.lines("review_proposals.py") if l.endswith(" list"))
    assert dc.load("review_proposals.py").main(dc.argv(line, {}), driver=driver) == 0
    out = capsys.readouterr().out
    assert rec[0]["id"] in out and setup["code"] in out
