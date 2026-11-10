"""確認点 L-0（2026-11-10 河原さん。提案 docs/proposals/2026-11-10-L0-entrance-decisions.md §6）。DB を使わない。

入口の点検（nest/gate/intake.py）と受付の検証（nest/gate/validate.py）に足す規則を、検出すべき入力と通すべき入力の両方で確かめる。
- 決めごと 9：事実の recordKind・informantKind の有無と列挙値、supportLog の必須と列挙値を入口で見る
- 決めごと 6：見立て（certainty Inference）で informantKind が無ければ、もとになった情報源を書くよう理由を出して止める
- 決めごと 8：根拠が見立てだけの候補は、禁忌は入口で止め、推奨ケアは注意を出して通す
- 決めごと 10：どの toldBy・concerns にも使われない新しい人は入口で止める（N-46 #10 の注意から変えた）
- 決めごと 11：受付の検証でも、AI 由来の Person は同じ依頼の TOLD_BY・CONCERNS・RELATED_TO のどれかで結ばれていること
- 決めごと 1〜5：面接 1 回＝supportLog 1 件。根拠は事実の引用一つ。effectiveness は書かせない
"""
import pytest

from nest.gate import intake
from nest.gate import validate as gv

CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
PER = "PER-01H11111111111111111111111"
VISIT = "自宅を訪問。母と本人に会う。"
MOTHER = "母は「最近、夜に薬を出し忘れることが二回あった」と自分から話した。"
VIEW = "ヘルパーの交代が多いと落ち着かないのだろうと、私（相談支援専門員）は受け取りました。"
ORIGINAL = ("架空の面接記録（例）\n"
            "2026-11-01 訪問\n"
            + VISIT + "\n"
            + MOTHER + "【伝聞】\n"
            + VIEW + "【推測】\n"
            "次回は主治医への通院に同行することを母と確認。\n")


def _facts():
    return [{"quote": VISIT, "recordKind": "Observation", "certainty": "Unspecified", "informantKind": "Agency"},
            {"quote": MOTHER, "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family", "toldBy": "mother"},
            {"quote": VIEW, "recordKind": "Interview", "certainty": "Inference", "informantKind": "Self"}]


def _log(**over):
    log = {"quote": VISIT, "date": "2026-11-01", "contactKind": "Visit", "situation": "自宅。母と本人",
           "action": "母と本人に会い、話を聞いた", "nextAction": "次回は主治医への通院に同行する（母と確認）"}
    log.update(over)
    return {k: v for k, v in log.items() if v is not None}


def _proposal(**over):
    p = {"documentKind": "OwnCaseRecord", "clientId": CLIENT, "newPeople": [{"ref": "mother"}], "facts": _facts(),
         "supportLog": _log()}
    p.update(over)
    return {k: v for k, v in p.items() if v is not None}


def _check(p, original=ORIGINAL):
    return intake.check(p, original, ACTOR, "req-l0")


def _stopped(rep, *words):
    assert not rep["ok"] and rep["request"] is None, rep
    assert any(all(w in e for w in words) for e in rep["errors"]), rep["errors"]


def test_the_visit_record_passes():
    rep = _check(_proposal())
    assert rep["ok"], rep["errors"]


# ---- 決めごと 9：事実の recordKind・informantKind ----

@pytest.mark.parametrize("key", ["recordKind", "informantKind"])
def test_a_fact_without_record_kind_or_informant_kind_stops_at_the_intake(key):
    facts = _facts()
    del facts[0][key]
    _stopped(_check(_proposal(facts=facts)), "事実 1", key)


@pytest.mark.parametrize("key,value", [("recordKind", "Visit"), ("informantKind", "Recorder"), ("informantKind", "家族")])
def test_a_value_outside_the_canon_enum_stops_without_fixing(key, value):
    facts = _facts()
    facts[1][key] = value
    _stopped(_check(_proposal(facts=facts)), "事実 2", key, value)


# ---- 決めごと 6：見立ての情報源 ----

def test_a_view_without_informant_kind_stops_with_how_to_write_it():
    facts = _facts()
    del facts[2]["informantKind"]
    rep = _check(_proposal(facts=facts))
    _stopped(rep, "事実 3", "見立て", "もとになった情報源")
    (e,) = [e for e in rep["errors"] if "見立て" in e]
    assert "Self" in e and "Family" in e and "Agency" in e and "DocumentOnly" in e


def test_a_view_is_a_record_authored_by_the_staff_and_not_told_by_anyone():
    rep = _check(_proposal())
    assert rep["ok"], rep["errors"]
    view = next(n for n in rep["request"]["nodes"] if n["label"] == "Record" and n["properties"]["quote"] == VIEW)
    assert view["properties"]["certainty"] == "Inference" and view["properties"]["informantKind"] == "Self"
    rels = rep["request"]["relationships"]
    assert any(r["type"] == "AUTHORED_BY" and r["from"] == view["ref"] for r in rels)
    assert not any(r["type"] == "TOLD_BY" and r["from"] == view["ref"] for r in rels)


# ---- 決めごと 8：根拠が見立てだけの候補 ----

def test_a_prohibition_resting_only_on_a_view_stops_at_the_intake():
    rep = _check(_proposal(ngActions=[{"quote": VIEW, "action": "ヘルパーを頻繁に交代させる", "riskLevel": "Panic"}]))
    _stopped(rep, "ngActions 1", "見立て", "禁忌")


def test_a_care_preference_resting_only_on_a_view_passes_with_a_warning():
    rep = _check(_proposal(carePreferences=[{"quote": VIEW, "category": "ヘルパー", "instruction": "ヘルパーをなるべく同じ人にする"}]))
    assert rep["ok"], rep["errors"]
    assert any("carePreferences 1" in w and "見立て" in w for w in rep["warnings"]), rep["warnings"]


def test_a_prohibition_resting_on_hearsay_still_passes():
    rep = _check(_proposal(ngActions=[{"quote": MOTHER, "action": "夜に薬を出し忘れる", "riskLevel": "Discomfort"}]))
    assert rep["ok"], rep["errors"]


# ---- 決めごと 10：使われない新しい人 ----

def test_a_new_person_used_by_no_fact_or_involvement_stops():
    rep = _check(_proposal(newPeople=[{"ref": "mother"}, {"ref": "neighbor"}]))
    _stopped(rep, "neighbor", "toldBy", "concerns", "案から外す")


# ---- 決めごと 1〜5：面接記録（supportLog） ----

def test_the_support_log_becomes_one_pending_node_tied_to_the_client_staff_and_the_contact_sentence():
    rep = _check(_proposal())
    assert rep["ok"], rep["errors"]
    nodes = rep["request"]["nodes"]
    (log,) = [n for n in nodes if n["label"] == "SupportLog"]
    assert log["origin"] == "AiExtracted"
    assert log["properties"] == {"date": "2026-11-01", "contactKind": "Visit", "situation": "自宅。母と本人",
                                 "action": "母と本人に会い、話を聞いた", "nextAction": "次回は主治医への通院に同行する（母と確認）"}
    visit = next(n["ref"] for n in nodes if n["label"] == "Record" and n["properties"]["quote"] == VISIT)
    mine = [(r["type"], r["to"]) for r in rep["request"]["relationships"] if r["from"] == log["ref"]]
    assert sorted(mine, key=str) == sorted([("ABOUT", {"label": "Client", "id": CLIENT}),
                                            ("AUTHORED_BY", {"label": "Staff", "id": ACTOR}),
                                            ("EVIDENCED_BY", visit)], key=str)


def test_the_whole_request_passes_the_gate_validation():
    rep = _check(_proposal())
    out = gv.validate(rep["request"])
    assert out["ok"], out["errors"]
    (log,) = [n for n in out["nodes"] if n["label"] == "SupportLog"]
    assert log["status"] == "Pending"


def test_contact_kind_may_be_left_out():
    rep = _check(_proposal(supportLog=_log(contactKind=None)))
    assert rep["ok"], rep["errors"]
    (log,) = [n for n in rep["request"]["nodes"] if n["label"] == "SupportLog"]
    assert "contactKind" not in log["properties"]


@pytest.mark.parametrize("key", ["quote", "date", "situation"])
def test_a_support_log_without_a_required_item_stops(key):
    _stopped(_check(_proposal(supportLog=_log(**{key: None}))), "supportLog", key)


@pytest.mark.parametrize("value", ["訪問", "Other", "visit-home"])
def test_a_contact_kind_outside_the_six_stops_without_fixing(value):
    _stopped(_check(_proposal(supportLog=_log(contactKind=value))), "supportLog", "contactKind", value)


@pytest.mark.parametrize("value", ["11月1日", "2026-13-01", "2026/11/01"])
def test_a_date_that_is_not_a_real_day_stops(value):
    _stopped(_check(_proposal(supportLog=_log(date=value))), "supportLog", "date")


def test_the_quote_must_be_one_of_the_fact_quotes():
    rep = _check(_proposal(supportLog=_log(quote="次回は主治医への通院に同行することを母と確認。")))
    _stopped(rep, "supportLog", "quote", "事実の引用")


def test_effectiveness_is_not_written_by_the_proposal():
    _stopped(_check(_proposal(supportLog=_log(effectiveness="Effective"))), "supportLog", "effectiveness", "職員")


def test_an_unknown_key_in_the_support_log_stops():
    _stopped(_check(_proposal(supportLog=_log(attendees="母"))), "supportLog", "attendees")


def test_numbers_not_in_the_whole_original_stop():
    _stopped(_check(_proposal(supportLog=_log(nextAction="3日後に主治医への通院に同行する"))), "supportLog", "3")
    ok = _check(_proposal(supportLog=_log(note="2026-11-01 の訪問")))      # 原文にある数字は通す
    assert ok["ok"], ok["errors"]


def test_the_support_log_is_one_object():
    _stopped(_check(_proposal(supportLog=[_log()])), "supportLog", "オブジェクト")


# ---- 決めごと 11：受付の検証（入口を通らない道から来た場合） ----

def _person_req(*rels):
    nodes = [{"ref": "neighbor", "label": "Person", "origin": "AiExtracted", "properties": {}},
             {"ref": "r", "label": "Record", "origin": "AiExtracted", "properties": {
                 "kind": "Interview", "text": "近所の人の話", "quote": "近所の人の話", "certainty": "Hearsay",
                 "informantKind": "Neighbor"}},
             {"ref": "inv", "label": "Involvement", "origin": "AiExtracted", "properties": {
                 "kind": "Consultation", "howEnded": "Unknown", "certainty": "Inference"}}]
    base = [{"type": "ABOUT", "from": "r", "to": {"label": "Client", "id": CLIENT}},
            {"type": "EVIDENCED_BY", "from": "inv", "to": "r"}]
    return {"requestId": "req-v", "actorStaffId": ACTOR, "nodes": nodes, "relationships": base + list(rels)}


def test_the_gate_stops_an_ai_person_tied_to_nothing():
    out = gv.validate(_person_req({"type": "CONCERNS", "from": "inv", "to": {"label": "Client", "id": CLIENT}}))
    assert not out["ok"]
    assert any("neighbor" in e and "TOLD_BY" in e and "CONCERNS" in e and "RELATED_TO" in e for e in out["errors"]), out["errors"]


@pytest.mark.parametrize("rel", [
    {"type": "TOLD_BY", "from": "r", "to": "neighbor"},
    {"type": "CONCERNS", "from": "inv", "to": "neighbor"},
    {"type": "RELATED_TO", "from": "neighbor", "to": {"label": "Client", "id": CLIENT},
     "properties": {"kind": "Neighbor", "certainty": "Hearsay", "evidenceRecordIds": []}},
])
def test_the_gate_passes_an_ai_person_tied_by_told_by_concerns_or_related_to(rel):
    out = gv.validate(_person_req(rel))
    assert not any("neighbor" in e and "TOLD_BY" in e for e in out["errors"]), out["errors"]


def test_the_gate_rule_is_only_for_ai_people():
    req = _person_req()
    req["nodes"][0]["origin"] = "Human"
    out = gv.validate(req)
    assert not any("neighbor" in e and "TOLD_BY" in e for e in out["errors"]), out["errors"]
