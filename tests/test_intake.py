"""N-11〜N-16：書き込みの案を受ける入口（nest/gate/intake.py）。DB を使わない。AI を使わない点検。

tsunagu-net の tests/test_intake.py の例（両方向・架空）を写し、nest-support の形（本人一人。世帯を持たない）に合わせた（N-11）。
検出すべき入力と通すべき入力の両方を確かめる：
- 原文に無い引用（N-12）・数字を足した本文（N-13）・確度の格上げと格下げ（N-14）・型に無い項目（N-15）は、直さずに止める
- 情報提供の書面は確度を二段で持つ（提供元がどう知ったか＝原文の印、受けた側から見て＝他の機関からの情報）
- 人は既にある ID か、案の中の新しい人（Pending）だけ。名前で既にいる人に結び付けない（N-16）
- 原本の指紋は道具が原文から作る（案には書かせない）
"""
import copy
import hashlib
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "intake"
ORIGINAL = (FIXTURES / "provision_document.md").read_text(encoding="utf-8")
OWN = (FIXTURES / "own_record.md").read_text(encoding="utf-8")

CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"
PROVIDER = "ORG-01HPPPPPPPPPPPPPPPPPPPPPPP"
PER = "PER-01H11111111111111111111111"
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
BRUISE = "ハナの右上腕に、指の形に見えるあざ（2か所）を送迎時に確認し、写真を記録"


def _intake():
    from nest.gate import intake
    return intake


def _fact(quote, certainty="Hearsay", provider="Confirmed", **over):
    f = {"quote": quote, "recordKind": "Document", "certainty": certainty, "providerCertainty": provider,
         "informantKind": "Agency"}
    f.update(over)
    return f


def _proposal(facts=None, **over):
    p = {"documentKind": "ProvisionDocument", "providerOrgId": PROVIDER, "clientId": CLIENT, "receivedOn": "2026-09-15",
         "facts": facts if facts is not None else [_fact(BRUISE)]}
    p.update(over)
    return p


def _check(proposal, original=ORIGINAL):
    return _intake().check(proposal, original, actor_staff_id=ACTOR, request_id="req-intake")


def _records(rep):
    return [n for n in rep["request"]["nodes"] if n["label"] == "Record"]


# ---- 入口の形（N-12） ----

def test_quote_not_in_original_stops():
    rep = _check(_proposal([_fact("ハナの左腕にあざがある")]))
    assert not rep["ok"] and any("原文に無い" in e for e in rep["errors"])
    assert rep["request"] is None


def test_quote_must_be_present():
    rep = _check(_proposal([_fact("")]))
    assert not rep["ok"] and any("引用" in e for e in rep["errors"])


def test_quote_ignores_only_whitespace_differences():
    rep = _check(_proposal([_fact("ハナの右上腕に、 指の形に見えるあざ（2か所）を\n送迎時に確認し、写真を記録")]))
    assert not any("原文に無い" in e for e in rep["errors"])


def test_document_kind_and_provider_rules():
    assert not _check(_proposal(providerOrgId=None))["ok"]                 # 書面なのに提供元が無い
    assert not _check(_proposal(documentKind="Memo"))["ok"]
    assert not _check(_proposal(documentKind="OwnCaseRecord"))["ok"]        # 自分の記録に提供元を書かない
    assert not _check(_proposal(clientId="本人A"))["ok"]                    # 本人は ID で指す
    assert not _check(_proposal(providerOrgId="CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"))["ok"]


def test_facts_must_be_present():
    rep = _check(_proposal([]))
    assert not rep["ok"] and any("facts" in e for e in rep["errors"])


def test_document_hash_is_made_from_the_original():
    rep = _check(_proposal())
    assert rep["ok"], rep["errors"]
    (rec,) = _records(rep)
    assert rec["properties"]["documentHash"] == hashlib.sha256(ORIGINAL.encode("utf-8")).hexdigest()


def test_does_not_mutate_input():
    p = _proposal()
    before = copy.deepcopy(p)
    _check(p)
    assert p == before


# ---- 数字（N-13） ----

def test_paraphrase_is_allowed_only_without_new_numbers():
    ok = _check(_proposal([_fact(BRUISE, text="右上腕に指の形のあざが2か所")]))
    assert ok["ok"], ok["errors"]
    assert any("言い換え" in w for w in ok["warnings"])
    bad = _check(_proposal([_fact(BRUISE, text="右上腕に指の形のあざが3か所")]))
    assert not bad["ok"] and any("3" in e for e in bad["errors"])


def test_full_width_digits_count_as_the_same_number():
    ok = _check(_proposal([_fact(BRUISE, text="右上腕にあざが２か所")]))
    assert ok["ok"], ok["errors"]


# ---- 確度（N-14） ----

def test_good_provision_document_has_two_level_certainty():
    rep = _check(_proposal())
    assert rep["ok"], rep["errors"]
    (rec,) = _records(rep)
    p = rec["properties"]
    assert p["certainty"] == "Hearsay" and p["providerCertainty"] == "Confirmed"
    assert p["text"] == p["quote"] == BRUISE
    assert p["receivedOn"] == "2026-09-15"
    types = {(r["type"], r["to"]["id"] if isinstance(r["to"], dict) else r["to"]) for r in rep["request"]["relationships"]}
    assert ("ABOUT", CLIENT) in types and ("PROVIDED_BY", "provider") in types and ("AUTHORED_BY", ACTOR) in types


def test_weaker_provider_marks_carry_through():
    rep = _check(_proposal([
        _fact("7月に、誠がハナを大声で怒鳴っているのを送迎の運転手が玄関先で聞いた", "Hearsay", "Hearsay"),
        _fact("近所の人の話では、誠は日中パチンコ店にいることが多い", "Hearsay", "Hearsay"),
        _fact("保育所の送り迎えと夕食の用意も翔太がしている様子", "Inference", "Inference"),
        _fact("デイの利用は週2回の契約だが、8月以降は月2〜3回に減っている", "Unspecified", "Unspecified")]))
    assert rep["ok"], rep["errors"]


def test_own_case_record_uses_one_level():
    rep = _check({"documentKind": "OwnCaseRecord", "clientId": CLIENT,
                  "facts": [{"quote": "児童扶養手当の申請を、離婚後まだしていない", "recordKind": "Interview",
                             "certainty": "Confirmed", "informantKind": "Self"}]}, OWN)
    assert rep["ok"], rep["errors"]
    (rec,) = _records(rep)
    assert "providerCertainty" not in rec["properties"] and rec["properties"]["certainty"] == "Confirmed"
    assert not any(r["type"] == "PROVIDED_BY" for r in rep["request"]["relationships"])


def test_certainty_upgrade_and_downgrade_stop():
    up = _check(_proposal([_fact("近所の人の話では、誠は日中パチンコ店にいることが多い", "Hearsay", "Confirmed")]))
    assert not up["ok"] and any("原文の印" in e for e in up["errors"])
    down = _check(_proposal([_fact(BRUISE, "Hearsay", "Hearsay")]))
    assert not down["ok"]                                                  # 格下げも直さず止める
    unmarked = _check(_proposal([_fact("デイの利用は週2回の契約だが、8月以降は月2〜3回に減っている", "Hearsay", "Hearsay")]))
    assert not unmarked["ok"]                                              # 印が無ければ Unspecified


def test_provided_information_cannot_be_confirmed_by_the_receiver():
    rep = _check(_proposal([_fact(BRUISE, "Confirmed", "Confirmed")]))
    assert not rep["ok"] and any("他の機関からの情報" in e for e in rep["errors"])


def test_unknown_mark_stops():
    rep = _check(_proposal([_fact("ハナ", "Hearsay", "Confirmed")]), "- ハナ【たぶん】\n")
    assert not rep["ok"] and any("印を読めない" in e for e in rep["errors"])


# ---- 型に無い項目（N-15） ----

def test_unknown_keys_stop_without_fixing():
    bad = _proposal()
    bad["facts"][0]["confidence"] = "high"
    rep = _check(bad)
    assert not rep["ok"] and any("confidence" in e for e in rep["errors"])
    assert not _check(_proposal(score=3))["ok"]
    assert not _check(_proposal(documentHash="0" * 64))["ok"]             # 指紋は案に書かせない


def test_snake_case_key_stops():
    bad = _proposal()
    bad["facts"][0]["informant_kind"] = bad["facts"][0].pop("informantKind")
    rep = _check(bad)
    assert not rep["ok"] and any("informant_kind" in e for e in rep["errors"])


# ---- 未確定と人（N-16） ----

def test_records_are_pending_ai_extracted():
    rep = _check(_proposal())
    assert rep["ok"], rep["errors"]
    assert all(n["origin"] == "AiExtracted" for n in _records(rep))


def test_new_person_is_a_pending_candidate_not_matched_by_name():
    rep = _check(_proposal([_fact("ハナに尋ねると「転んだ」と言うが、転倒の具体的な状況は話せない", toldBy="p-hana")],
                           newPeople=[{"ref": "p-hana", "givenName": "ハナ"}]))
    assert rep["ok"], rep["errors"]
    (person,) = [n for n in rep["request"]["nodes"] if n["label"] == "Person"]
    assert person["origin"] == "AiExtracted" and person["properties"] == {"givenName": "ハナ"}
    assert any(r["type"] == "TOLD_BY" and r["to"] == "p-hana" for r in rep["request"]["relationships"])


def test_told_by_must_be_existing_id_or_new_person_ref():
    quote = "ハナに尋ねると「転んだ」と言うが、転倒の具体的な状況は話せない"
    assert not _check(_proposal([_fact(quote, toldBy="ハナ")]))["ok"]      # 名前で結び付けない
    assert not _check(_proposal([_fact(quote, toldBy="p-x")]))["ok"]       # 案に無い名札
    assert _check(_proposal([_fact(quote, toldBy=PER)]))["ok"]
    assert _check(_proposal([_fact(quote, toldBy="client")]))["ok"]        # 本人が話した


# N-11：写した直後は赤。各タスクで緑にしたら、そのタスクの印を外す
# 通すべき入力の試験（良い案が通る）は、入口が依頼を作った時点（N-12）で緑になる。各タスクの印は止めるべき入力の試験に残す（台帳 G-46）
_PENDING = {
    "N-13": ["test_paraphrase_is_allowed_only_without_new_numbers"],
    "N-14": ["test_certainty_upgrade_and_downgrade_stop", "test_provided_information_cannot_be_confirmed_by_the_receiver",
             "test_unknown_mark_stops"],
    "N-15": ["test_unknown_keys_stop_without_fixing", "test_snake_case_key_stops"],
    "N-16": ["test_told_by_must_be_existing_id_or_new_person_ref"],
}
for _task, _names in _PENDING.items():
    for _name in _names:
        globals()[_name] = pytest.mark.xfail(strict=True, reason="%s で緑にする" % _task)(globals()[_name])
