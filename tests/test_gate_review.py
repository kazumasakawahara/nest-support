"""N-20a：確認の記録（Review）をゲートの操作で作る（2026-11-06 河原さん。止まる点 E-1）。DB を使わない。

- Review は人が確かめた記録。AI 由来（AiExtracted）にしない。入口の案（intake）からは作れない
- 職員の ID（REVIEWED の始点＝依頼の職員）・確かめた日（reviewedAt）・領域（domain。reviewDomain）を必須にする
- CONFIRMS で対象の記録（Record）に一つ以上結ぶ。ABOUT で本人に結ぶ
- そろえば Active で書かれる
"""
import pytest

from nest.gate import intake
from nest.gate import validate as gv
from nest.gate import write as gw

STAFF = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
OTHER = "STF-01HYYYYYYYYYYYYYYYYYYYYYYY"
CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"
RECORD = "REC-01HZZZZZZZZZZZZZZZZZZZZZZZ"


def _ok_request(**changes):
    return gw.review_request(STAFF, CLIENT, changes.get("domain", "NgAction"),
                             changes.get("reviewed_at", "2026-11-06T10:00:00+09:00"),
                             changes.get("informant_kind", "Family"), changes.get("record_ids", [RECORD]),
                             "req-review", note=changes.get("note"))


def test_review_request_validates_and_is_active():
    rep = gv.validate(_ok_request())
    assert rep["ok"], rep["errors"]
    [rv] = [n for n in rep["nodes"] if n["label"] == "Review"]
    assert rv["origin"] == "Human" and rv["status"] == "Active"
    rels = {(r["type"], str(r["from"]), str(r["to"])) for r in rep["relationships"]}
    assert ("REVIEWED", str({"label": "Staff", "id": STAFF}), "review") in rels
    assert ("ABOUT", "review", str({"label": "Client", "id": CLIENT})) in rels
    assert ("CONFIRMS", "review", str({"label": "Record", "id": RECORD})) in rels


@pytest.mark.parametrize("bad, word", [
    ({"domain": None}, "domain"),
    ({"domain": "Wish"}, "domain"),
    ({"reviewed_at": None}, "reviewedAt"),
    ({"informant_kind": None}, "informantKind"),
    ({"record_ids": []}, "CONFIRMS"),
])
def test_review_request_refuses_missing_parts(bad, word):
    rep = gv.validate(_ok_request(**bad))
    assert not rep["ok"] and any(word in e for e in rep["errors"]), rep["errors"]


def test_ai_extracted_review_is_refused():
    req = _ok_request()
    for n in req["nodes"]:
        if n["label"] == "Review":
            n["origin"] = "AiExtracted"
    rep = gv.validate(req)
    assert not rep["ok"] and any("Review" in e and "人" in e for e in rep["errors"]), rep["errors"]


def test_review_must_be_by_the_acting_staff():
    req = _ok_request()
    for r in req["relationships"]:
        if r["type"] == "REVIEWED":
            r["from"] = {"label": "Staff", "id": OTHER}
    rep = gv.validate(req)
    assert not rep["ok"] and any("REVIEWED" in e for e in rep["errors"]), rep["errors"]
    req = _ok_request()
    req["relationships"] = [r for r in req["relationships"] if r["type"] != "REVIEWED"]
    rep = gv.validate(req)
    assert not rep["ok"] and any("REVIEWED" in e for e in rep["errors"]), rep["errors"]


def test_review_must_be_about_a_client():
    req = _ok_request()
    req["relationships"] = [r for r in req["relationships"] if r["type"] != "ABOUT"]
    rep = gv.validate(req)
    assert not rep["ok"] and any("ABOUT" in e for e in rep["errors"]), rep["errors"]


def test_intake_cannot_carry_a_review():
    original = "架空の面談記録\n- 母の話では、禁忌は無い【伝聞】\n"
    proposal = {"documentKind": "OwnCaseRecord", "clientId": CLIENT,
                "facts": [{"quote": "母の話では、禁忌は無い", "recordKind": "Interview", "certainty": "Hearsay",
                           "informantKind": "Family"}],
                "reviews": [{"domain": "NgAction"}]}
    rep = intake.check(proposal, original, STAFF, "req-x")
    assert not rep["ok"] and any("reviews" in e for e in rep["errors"]), rep["errors"]
