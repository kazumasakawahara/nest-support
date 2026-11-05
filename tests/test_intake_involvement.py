"""N-24a：機関の名前が無い言及から、関わり（Involvement）の案を作る。DB を使わない。

- 案の involvements は {quote, kind, orgId?}。quote は案の事実の引用のどれか（その記録が根拠になる）
- orgId は、担当機関の推定（org_estimate.estimate）が出した候補の中からだけ選べる。候補の外・推定なしは止める
- orgId が無ければ機関未確定のまま関わりを作る（D3）
- 確度は案に書かせない。いつも Inference。AI 由来なので Pending（N-16。承認は N-21）
- 推定の注記（今の住所で推定した、など）は点検の結果 notes に載り、承認の前に職員が見る
"""
from pathlib import Path

import pytest

from nest.gate import intake
from nest.gate import validate as gv

OWN = (Path(__file__).resolve().parent / "fixtures" / "intake" / "own_record_desk.md").read_text(encoding="utf-8")
CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
ORG = "ORG-01AAAAAAAAAAAAAAAAAAAAAAAA"
QUOTE = "母の話では、去年の春に区役所の相談コーナーで、本人の通所のことを相談した"
ESTIMATE = {"candidates": [{"orgId": ORG, "name": "架空区高齢者・障害者相談コーナー", "kind": "DisabilityDivision",
                            "servesBasis": "PresumedByLocation", "partOfArea": False, "viaParent": False}],
            "truncated": False, "notes": ["当時の住所が記録に無いので、今の住所で推定した"], "window": None, "chosen": None}


def _proposal(inv=None):
    return {"documentKind": "OwnCaseRecord", "clientId": CLIENT,
            "facts": [{"quote": QUOTE, "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family"}],
            "involvements": [inv if inv is not None else {"quote": QUOTE, "kind": "Consultation", "orgId": ORG}]}


def _check(p, estimate=ESTIMATE):
    return intake.check(p, OWN, actor_staff_id=ACTOR, request_id="req-inv", estimate=estimate)


def _nodes(rep, label):
    return [n for n in rep["request"]["nodes"] if n["label"] == label]


def test_chosen_candidate_becomes_a_pending_inference_involvement():
    rep = _check(_proposal())
    assert rep["ok"], rep["errors"]
    inv = _nodes(rep, "Involvement")
    assert len(inv) == 1 and inv[0]["origin"] == "AiExtracted"
    assert inv[0]["properties"] == {"kind": "Consultation", "howEnded": "Unknown", "certainty": "Inference"}
    rels = {(r["type"], r["from"] if isinstance(r["from"], str) else r["from"]["id"],
             r["to"] if isinstance(r["to"], str) else r["to"]["id"]) for r in rep["request"]["relationships"]}
    ref = inv[0]["ref"]
    assert ("CONCERNS", ref, CLIENT) in rels
    assert ("EVIDENCED_BY", ref, "fact-1") in rels
    org = _nodes(rep, "Organization")
    assert org[0]["properties"] == {"orgId": ORG}
    assert ("HAS_INVOLVEMENT", org[0]["ref"], ref) in rels
    assert rep["notes"] == ESTIMATE["notes"]
    v = gv.validate(rep["request"])
    assert v["ok"], v["errors"]
    assert {n["ref"]: n["status"] for n in v["nodes"]}[ref] == "Pending"


def test_no_window_is_created():
    rep = _check(_proposal())
    assert not any(n["label"] == "Window" for n in rep["request"]["nodes"])


def test_without_org_the_involvement_stays_undecided():
    rep = _check(_proposal({"quote": QUOTE, "kind": "Consultation"}))
    assert rep["ok"], rep["errors"]
    assert _nodes(rep, "Organization") == []
    assert not any(r["type"] == "HAS_INVOLVEMENT" for r in rep["request"]["relationships"])
    assert _nodes(rep, "Involvement")[0]["properties"]["certainty"] == "Inference"


def test_org_outside_the_candidates_is_refused():
    rep = _check(_proposal({"quote": QUOTE, "kind": "Consultation", "orgId": "ORG-01BBBBBBBBBBBBBBBBBBBBBBBB"}))
    assert not rep["ok"] and any("候補" in e for e in rep["errors"])


def test_org_without_an_estimate_is_refused():
    rep = _check(_proposal(), estimate=None)
    assert not rep["ok"] and any("候補" in e for e in rep["errors"])


@pytest.mark.parametrize("inv, word", [
    ({"quote": "区役所で相談した", "kind": "Consultation"}, "事実"),           # 事実の引用のどれでもない
    ({"quote": QUOTE, "kind": "Chat"}, "kind"),
    ({"quote": QUOTE, "kind": "Consultation", "certainty": "Confirmed"}, "certainty"),
    ({"quote": QUOTE, "kind": "Consultation", "window": "x"}, "window"),
    ({"quote": QUOTE, "kind": "Guardianship"}, "Guardianship"),             # 後見は推定で作らない
])
def test_bad_involvements_are_refused(inv, word):
    rep = _check(_proposal(inv))
    assert not rep["ok"] and any(word in e for e in rep["errors"]), rep["errors"]


def test_proposal_without_involvements_is_unchanged():
    p = _proposal()
    del p["involvements"]
    rep = _check(p, estimate=None)
    assert rep["ok"] and _nodes(rep, "Involvement") == [] and rep.get("notes", []) == []


def test_same_org_as_the_provider_is_not_created_twice():
    original = OWN + "- 架空区高齢者・障害者相談コーナーからの連絡票【確認済み】\n"
    p = _proposal()
    p.update(documentKind="ProvisionDocument", providerName="架空区高齢者・障害者相談コーナー")
    p["facts"][0].update(certainty="Hearsay", providerCertainty="Hearsay", informantKind="Agency", recordKind="Document")
    rep = intake.check(p, original, actor_staff_id=ACTOR, request_id="req-inv2", provider_org_id=ORG, estimate=ESTIMATE)
    assert rep["ok"], rep["errors"]
    assert [n["properties"]["orgId"] for n in _nodes(rep, "Organization")] == [ORG]
    assert gv.validate(rep["request"])["ok"]
