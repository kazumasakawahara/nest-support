"""G-63（2026-11-06 河原さん：欄を足す）。入口の案に、禁忌（NgAction）と推奨ケア（CarePreference）の候補の欄。DB を使わない。

(1) 候補は必ず、同じ案の中の事実（引用を持つもの）を根拠として指す。指していない候補はゲートが止める（G-52 (7) と同じ規則）
(2) 確度は根拠の事実のものを引き継ぐ。候補に独自の確度を持たせない
(3) 入るときは Pending
"""
from pathlib import Path

from nest import canon
from nest.gate import intake
from nest.gate import validate as gv

REPO = Path(__file__).resolve().parents[1]
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"
ORIGINAL = "架空の面談記録\n- 母の話では、後ろから急に声をかけるとパニックになる【伝聞】\n- 本人は、音楽を聴くと落ち着くと話した【本人の話】\n"
Q1 = "母の話では、後ろから急に声をかけるとパニックになる"
Q2 = "本人は、音楽を聴くと落ち着くと話した"


def _proposal(**extra):
    p = {"documentKind": "OwnCaseRecord", "clientId": CLIENT, "newPeople": [{"ref": "mother"}],
         "facts": [{"quote": Q1, "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family", "toldBy": "mother"},
                   {"quote": Q2, "recordKind": "Interview", "certainty": "SelfReport", "informantKind": "Self", "toldBy": "client"}]}
    p.update(extra)
    return p


NG = {"quote": Q1, "action": "後ろから急に声をかける", "riskLevel": "Panic"}
CP = {"quote": Q2, "category": "落ち着く方法", "instruction": "音楽を聴いてもらう"}


def _check(p):
    return intake.check(p, ORIGINAL, actor_staff_id=ACTOR, request_id="req-g63")


def _by_label(req, label):
    return [n for n in req["nodes"] if n["label"] == label]


def test_ngaction_candidate_becomes_pending_with_evidence_and_must_avoid():
    rep = _check(_proposal(ngActions=[NG]))
    assert rep["ok"], rep["errors"]
    req = rep["request"]
    [ng] = _by_label(req, "NgAction")
    assert ng["origin"] == "AiExtracted"
    assert ng["properties"] == {"action": NG["action"], "riskLevel": "Panic"}
    rels = req["relationships"]
    assert {"type": "MUST_AVOID", "from": {"label": "Client", "id": CLIENT}, "to": ng["ref"]} in rels
    assert {"type": "EVIDENCED_BY", "from": ng["ref"], "to": "fact-1"} in rels
    out = gv.validate(req)
    assert out["ok"], out["errors"]
    assert {n["status"] for n in out["nodes"] if n["label"] == "NgAction"} == {"Pending"}


def test_carepreference_candidate_becomes_pending_with_evidence_and_requires():
    rep = _check(_proposal(carePreferences=[CP]))
    assert rep["ok"], rep["errors"]
    req = rep["request"]
    [cp] = _by_label(req, "CarePreference")
    assert cp["origin"] == "AiExtracted"
    assert cp["properties"] == {"category": CP["category"], "instruction": CP["instruction"]}
    rels = req["relationships"]
    assert {"type": "REQUIRES", "from": {"label": "Client", "id": CLIENT}, "to": cp["ref"]} in rels
    assert {"type": "EVIDENCED_BY", "from": cp["ref"], "to": "fact-2"} in rels
    out = gv.validate(req)
    assert out["ok"], out["errors"]
    assert {n["status"] for n in out["nodes"] if n["label"] == "CarePreference"} == {"Pending"}


def test_candidate_must_point_at_a_fact_in_the_same_proposal():
    for key, cand in (("ngActions", NG), ("carePreferences", CP)):
        rep = _check(_proposal(**{key: [dict(cand, quote="原文に無い文")]}))
        assert not rep["ok"] and any("事実の引用" in e for e in rep["errors"]), (key, rep["errors"])
        rep = _check(_proposal(**{key: [{k: v for k, v in cand.items() if k != "quote"}]}))
        assert not rep["ok"] and any("事実の引用" in e for e in rep["errors"]), (key, rep["errors"])


def test_candidate_has_no_certainty_of_its_own():
    for key, cand in (("ngActions", NG), ("carePreferences", CP)):
        rep = _check(_proposal(**{key: [dict(cand, certainty="Confirmed")]}))
        assert not rep["ok"] and any("certainty" in e for e in rep["errors"]), (key, rep["errors"])
        rep = _check(_proposal(**{key: [cand]}))
        cand_node = [n for n in rep["request"]["nodes"] if n["label"] in ("NgAction", "CarePreference")][0]
        assert "certainty" not in cand_node["properties"]


def test_candidate_text_adds_no_numbers():
    rep = _check(_proposal(ngActions=[dict(NG, reason="3回あった")]))
    assert not rep["ok"] and any("数字" in e for e in rep["errors"]), rep["errors"]


def test_candidate_unknown_key_is_refused():
    rep = _check(_proposal(carePreferences=[dict(CP, ngActionId="NGA-01HZZZZZZZZZZZZZZZZZZZZZZZ")]))
    assert not rep["ok"] and any("ngActionId" in e for e in rep["errors"]), rep["errors"]


def test_gate_refuses_ai_carepreference_without_evidence():
    cp = {"ref": "cp", "label": "CarePreference", "origin": "AiExtracted",
          "properties": {"category": "落ち着く方法（架空）", "instruction": "音楽（架空）"}}
    rep = gv.validate({"requestId": "req-cp", "actorStaffId": ACTOR, "nodes": [cp], "relationships": []})
    assert not rep["ok"] and any("推奨ケア" in e and "根拠" in e for e in rep["errors"]), rep["errors"]


def test_canon_is_raised_and_says_candidates_carry_no_certainty():
    text = (REPO / "docs" / "SCHEMA.md").read_text(encoding="utf-8")
    assert "- v0.9（2026-11-06）" in text  # 版は後で上がる（v0.10 は G-64）
    assert "G-63" in text
    assert canon.load(REPO / "docs" / "SCHEMA.md")["personal"]["nodes"]["NgAction"]["required"] == ["ngActionId", "action", "riskLevel"]


def test_gate_refuses_human_carepreference_without_evidence():
    """2026-11-06 河原さん：推奨ケアは人が直接入れるものにも根拠の記録が要る（SEM-REC-03 をそのまま当てる）。"""
    cp = {"ref": "cp", "label": "CarePreference", "origin": "Human",
          "properties": {"category": "落ち着く方法（架空）", "instruction": "音楽（架空）"}}
    rep = gv.validate({"requestId": "req-cp", "actorStaffId": ACTOR, "nodes": [cp], "relationships": []})
    assert not rep["ok"] and any("推奨ケア" in e and "根拠" in e for e in rep["errors"]), rep["errors"]


def test_gate_accepts_human_carepreference_with_a_staff_observation():
    cp = {"ref": "cp", "label": "CarePreference", "origin": "Human",
          "properties": {"category": "落ち着く方法（架空）", "instruction": "音楽（架空）"}}
    rec = {"ref": "rec", "label": "Record", "origin": "Human",
           "properties": {"kind": "Observation", "text": "職員が見た（架空）", "quote": "職員が見た（架空）",
                          "certainty": "Confirmed", "informantKind": "Agency"}}
    rep = gv.validate({"requestId": "req-cp", "actorStaffId": ACTOR, "nodes": [cp, rec],
                       "relationships": [{"type": "EVIDENCED_BY", "from": "cp", "to": "rec"}]})
    assert not any("推奨ケア" in e and "根拠" in e for e in rep["errors"]), rep["errors"]
