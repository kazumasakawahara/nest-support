"""関わりを資源の側の機関に結ぶ一往復（2026-11-11 河原さん。L-1 の残り）。DB を使わない。

決めたこと：選ぶのは案を出した人。会話の中で候補から選び、関わりは未確定のまま機関に結ぶ。確定は承認。
候補に無いときは機関未確定のまま通す。サービスの種類は案の任意の欄で、資源の側のサービスと自動で照らさない。

- submit_proposal の返り値に、orgName のある関わりごとの候補（機関 ID・名前・種類・所在地の市区・サービスの種類）を添える。
  候補が 0 件でも通す
- nest-gate の link_organization：引数は仮名・関わりの ID・原文の名前・選んだ機関 ID。職員 ID は引数で受けない。
  止める：関わりがその本人のものでない／未確定でない／すでに機関が結ばれている／名前が根拠の記録の引用に無い／
  機関 ID がその名前の候補に無い。書くのはゲート（AuditLog が残る）
"""
import inspect

import pytest

from nest import egress, org_candidates
from nest.gate import org_link
from nest.gate import validate as gv
from nest.gate import write as gw

STAFF = "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"
CODE = "C-ZZZZZZ"
INV = "INV-01AAAAAAAAAAAAAAAAAAAAAAAA"
ORG = "ORG-01AAAAAAAAAAAAAAAAAAAAAAAA"
ORG2 = "ORG-01BBBBBBBBBBBBBBBBBBBBBBBB"
QUOTE = "通っている「つばさ」の生活支援員から電話で聞き取った。"
FACTS = {"status": "Pending", "mine": True, "quotes": [QUOTE], "orgs": 0}
CANDS = {"query": "つばさ", "truncated": False,
         "candidates": [{"orgId": ORG, "name": "つばさ（架空）", "kind": "DisabilityServiceOffice", "matchedBy": "name",
                         "areas": ["架空市"], "serviceTypes": ["生活介護"]}]}


def _errors(facts=FACTS, name="つばさ", org=ORG, cands=CANDS):
    return org_link.link_errors(facts, CODE, INV, name, org, cands)


# ---- 止める条件 ----

def test_a_pending_involvement_of_this_client_with_a_listed_org_passes():
    assert _errors() == []


@pytest.mark.parametrize("facts, words", [
    (None, ("無い",)),
    (dict(FACTS, mine=False), (CODE, "本人のものでない")),
    (dict(FACTS, status="Active"), ("未確定でない",)),
    (dict(FACTS, status="Inactive"), ("未確定でない",)),
    (dict(FACTS, orgs=1), ("すでに機関",)),
    (dict(FACTS, quotes=["本人は週五日、休まず通っている。"]), ("引用に無い",)),
])
def test_it_stops(facts, words):
    errors = _errors(facts=facts)
    assert any(all(w in e for w in words) for e in errors), errors


def test_an_org_that_is_not_a_candidate_of_that_name_stops():
    errors = _errors(org=ORG2)
    assert any(ORG2 in e and "候補に無い" in e for e in errors), errors


def test_whitespace_differences_in_the_name_are_ignored():
    assert _errors(name="つ ばさ") == []


# ---- 書く依頼 ----

def test_the_request_links_the_org_to_the_existing_involvement():
    req = org_link.link_request(STAFF, INV, ORG, "req-1")
    assert req["actorStaffId"] == STAFF
    (node,) = req["nodes"]
    assert node["label"] == "Organization" and node["properties"] == {"orgId": ORG} and node["origin"] == "Human"
    (rel,) = req["relationships"]
    assert rel["type"] == "HAS_INVOLVEMENT" and rel["from"] == node["ref"] and rel["to"] == {"label": "Involvement", "id": INV}
    assert gv.validate(req)["ok"], gv.validate(req)["errors"]


def test_link_writes_through_the_gate_only_when_nothing_stops(monkeypatch):
    sent = []
    monkeypatch.setattr(org_link, "_facts", lambda driver, code, inv: FACTS)
    monkeypatch.setattr(org_candidates, "for_involvement", lambda driver, name, **kw: CANDS)
    monkeypatch.setattr(gw, "submit", lambda req, driver, **kw: sent.append(req) or {"ok": True, "errors": [], "ids": {}})
    out = org_link.link(None, None, STAFF, CODE, INV, "つばさ", ORG)
    assert out["ok"] and out["orgId"] == ORG and out["name"] == "つばさ（架空）" and len(sent) == 1
    bad = org_link.link(None, None, STAFF, CODE, INV, "つばさ", ORG2)
    assert not bad["ok"] and len(sent) == 1


@pytest.mark.parametrize("args", [("C-ZZZZZZ", "INV-x", "つばさ", ORG), (CODE, INV, "つ", ORG), (CODE, INV, "つばさ", "ORG-x")])
def test_malformed_arguments_stop_before_the_db(args):
    class NoDB:
        def __getattr__(self, name):
            raise AssertionError("DB に触れた")
    out = org_link.link(NoDB(), NoDB(), STAFF, *args)
    assert not out["ok"] and out["errors"]


# ---- nest-gate の道具 ----

def _mcp():
    from nest import mcp_gate
    return mcp_gate


def test_the_gate_server_has_the_link_tool_without_a_staff_argument():
    params = set(inspect.signature(_mcp().link_organization).parameters)
    assert params == {"code", "involvement_id", "org_name", "org_id"}


def test_the_link_tool_says_to_ask_the_staff_and_never_choose():
    doc = _mcp().link_organization.__doc__
    assert "職員" in doc and "選" in doc and "未確定" in doc and "承認" in doc


def test_the_link_tool_checks_the_guard_first(monkeypatch):
    body = inspect.getsource(_mcp()._link)
    assert body.index("require_personal_allowed") < body.index("org_link.link")


def test_the_link_reply_always_names_the_pseudonym(monkeypatch):
    m = _mcp()
    monkeypatch.setenv("NEST_GATE_STAFF_ID", STAFF)
    monkeypatch.setattr(m.mcp_guard, "require_personal_allowed", lambda d: None)
    monkeypatch.setattr(org_link, "link", lambda *a, **kw: {"ok": True, "errors": [], "involvementId": INV, "orgId": ORG,
                                                            "name": "つばさ（架空）", "areas": ["架空市"]})
    ok = m._link(None, None, CODE, INV, "つばさ", ORG)
    assert CODE in ok["summary"] and "未確定" in ok["summary"]
    monkeypatch.setattr(org_link, "link", lambda *a, **kw: {"ok": False, "errors": ["止めた理由"]})
    ng = m._link(None, None, CODE, INV, "つばさ", ORG)
    assert CODE in ng["summary"] and "結んでいない" in ng["summary"]


# ---- submit_proposal の返り値の候補 ----

PHONE_ORIGINAL = "架空の面接記録（例）\n2026-11-05 電話\n" + QUOTE + "\n"


def _phone_proposal(**inv):
    i = {"quote": QUOTE, "kind": "ServiceProvision", "orgName": "つばさ", "serviceTypeName": "生活介護"}
    i.update(inv)
    return {"documentKind": "OwnCaseRecord",
            "facts": [{"quote": QUOTE, "recordKind": "Interview", "certainty": "Unspecified", "informantKind": "Agency"}],
            "involvements": [{k: v for k, v in i.items() if v is not None}]}


class _R(dict):
    pass


class FakePersonal:
    def execute_query(self, query, params=None, **kw):
        if "NestLiveProbe" in query:
            return [_R(marked=True)], None, None
        if "displayCode" in query:
            return [_R(id="CLI-01BBBBBBBBBBBBBBBBBBBBBBBB")], None, None
        return [], None, None


@pytest.fixture
def gate(monkeypatch):
    monkeypatch.setattr(gw, "submit", lambda req, driver, **kw: {"ok": True, "errors": [],
                                                                "ids": {n["ref"]: "%s-X" % n["ref"] for n in req["nodes"]}})
    monkeypatch.setenv("NEST_GATE_STAFF_ID", STAFF)
    monkeypatch.setattr(egress, "authorize", lambda row: (_ for _ in ()).throw(egress.EgressDenied("記録が無い（試験）")))


def test_submit_adds_the_candidates_for_each_named_involvement(gate, monkeypatch):
    monkeypatch.setattr(org_candidates, "for_involvement", lambda driver, name, **kw: dict(CANDS, query=name))
    out = _mcp()._submit(FakePersonal(), CODE, PHONE_ORIGINAL, _phone_proposal(), resource_driver=object())
    assert out["ok"]
    (choice,) = out["orgChoices"]
    assert choice["involvementId"] == "involvement-1-X" and choice["orgName"] == "つばさ"
    assert choice["candidates"] == CANDS["candidates"] and choice["truncated"] is False
    assert "番号" in out["next"] and "link_organization" in out["next"]


def test_zero_candidates_still_pass(gate, monkeypatch):
    monkeypatch.setattr(org_candidates, "for_involvement", lambda driver, name, **kw: {"query": name, "candidates": [], "truncated": False})
    out = _mcp()._submit(FakePersonal(), CODE, PHONE_ORIGINAL, _phone_proposal(), resource_driver=object())
    assert out["ok"] and out["orgChoices"][0]["candidates"] == []


def test_without_an_org_name_there_are_no_choices(gate, monkeypatch):
    monkeypatch.setattr(org_candidates, "for_involvement", lambda *a, **kw: pytest.fail("引かない"))
    out = _mcp()._submit(FakePersonal(), CODE, PHONE_ORIGINAL, _phone_proposal(orgName=None), resource_driver=object())
    assert out["ok"] and out["orgChoices"] == []


def test_a_failed_lookup_does_not_hide_that_it_was_written(gate, monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("資源の側につながらない（試験）")
    monkeypatch.setattr(org_candidates, "for_involvement", boom)
    out = _mcp()._submit(FakePersonal(), CODE, PHONE_ORIGINAL, _phone_proposal(), resource_driver=object())
    assert out["ok"] and out["pending"] >= 1
    (choice,) = out["orgChoices"]
    assert choice["candidates"] == [] and "機関未確定" in choice["note"]
