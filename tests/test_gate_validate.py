"""N-15：ゲートの検証（nest/gate/validate.py）。DB に触れない。正典 v0.4 の JSON から読む。

型に無い項目・値は直さずに止めて理由を返す。直すのは列挙値の大文字・小文字と、確度の日本語名だけ。
手本：tsunagu-net の tsunagu/gate/validate.py と tests/test_intake.py の二段の確度の試験（読むだけ）。
tsunagu-net と違い、snake_case の項目名は camelCase に直さず止める（計画 N-15）。
"""
import pytest

CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"
PROVIDER = "ORG-01HPPPPPPPPPPPPPPPPPPPPPPP"
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"


def _validate(req):
    from nest.gate import validate
    return validate.validate(req)


def _req(nodes, rels=()):
    return {"requestId": "req-v", "actorStaffId": ACTOR, "nodes": list(nodes), "relationships": list(rels)}


def _ng(**props):
    base = {"action": "大きな音を立てる", "riskLevel": "Panic"}
    base.update(props)
    return {"ref": "ng", "label": "NgAction", "origin": "AiExtracted", "properties": base}


def _must_avoid():
    return {"type": "MUST_AVOID", "from": {"label": "Client", "id": CLIENT}, "to": "ng"}


def test_good_request_passes():
    rep = _validate(_req([_ng()], [_must_avoid()]))
    assert rep["ok"], rep["errors"]
    assert rep["corrections"] == []


def test_unknown_label_stops():
    rep = _validate(_req([{"ref": "h", "label": "Hospital", "origin": "Human", "properties": {"name": "架空病院"}}]))
    assert not rep["ok"] and any("Hospital" in e for e in rep["errors"])


@pytest.mark.parametrize("old", ["PROHIBITED", "PREFERS", "EMERGENCY_CONTACT", "HAS_LEGAL_REP", "HAS_KEY_PERSON"])
def test_old_relationship_names_stop(old):
    rel = {"type": old, "from": {"label": "Client", "id": CLIENT}, "to": "ng"}
    rep = _validate(_req([_ng()], [rel]))
    assert not rep["ok"] and any(old in e for e in rep["errors"])


def test_snake_case_property_stops_without_fixing():
    rep = _validate(_req([_ng(risk_level="Panic")]))
    assert not rep["ok"] and any("risk_level" in e for e in rep["errors"])
    assert rep["corrections"] == []


def test_unknown_property_stops():
    rep = _validate(_req([_ng(score=3)]))
    assert not rep["ok"] and any("score" in e for e in rep["errors"])


@pytest.mark.parametrize("value", ["高", "High", "Danger", "生命"])
def test_risk_level_aliases_stop(value):
    rep = _validate(_req([_ng(riskLevel=value)]))
    assert not rep["ok"] and any("riskLevel" in e for e in rep["errors"])


def test_case_of_enum_value_is_fixed_and_reported():
    rep = _validate(_req([_ng(riskLevel="panic")]))
    assert rep["ok"], rep["errors"]
    assert rep["nodes"][0]["properties"]["riskLevel"] == "Panic"
    assert any("panic" in c for c in rep["corrections"])


@pytest.mark.parametrize("ja, value", [("確認済み", "Confirmed"), ("伝聞", "Hearsay"), ("本人の話", "SelfReport"),
                                       ("推測", "Inference"), ("確度の記載なし", "Unspecified")])
def test_japanese_certainty_name_is_fixed(ja, value):
    rec = {"ref": "r", "label": "Record", "origin": "AiExtracted", "properties": {
        "kind": "Interview", "text": "架空", "quote": "架空", "certainty": ja, "informantKind": "Family"}}
    rep = _validate(_req([rec], [{"type": "ABOUT", "from": "r", "to": {"label": "Client", "id": CLIENT}}]))
    assert rep["ok"], rep["errors"]
    assert rep["nodes"][0]["properties"]["certainty"] == value


def test_japanese_names_are_not_used_for_other_enums():
    rep = _validate(_req([_ng(riskLevel="パニック")]))
    assert not rep["ok"]


def test_missing_required_property_stops():
    rep = _validate(_req([{"ref": "ng", "label": "NgAction", "origin": "AiExtracted", "properties": {"action": "架空"}}]))
    assert not rep["ok"] and any("riskLevel" in e for e in rep["errors"])


@pytest.mark.parametrize("prop", ["ngActionId", "registeredAt", "status", "sourceHash"])
def test_gate_managed_properties_are_rejected(prop):
    rep = _validate(_req([_ng(**{prop: "x"})]))
    assert not rep["ok"] and any(prop in e for e in rep["errors"])


def test_embedding_property_stops():
    rep = _validate(_req([_ng(embedding=[0.1, 0.2])]))
    assert not rep["ok"] and any("embedding" in e for e in rep["errors"])


@pytest.mark.parametrize("label", ["AuditLog"])
def test_gate_only_labels_cannot_be_requested(label):
    rep = _validate(_req([{"ref": "a", "label": label, "origin": "Human", "properties": {}}]))
    assert not rep["ok"]


@pytest.mark.parametrize("rtype", ["APPROVED", "AUDIT_FOR", "ACTED_BY"])
def test_gate_only_relationships_cannot_be_requested(rtype):
    rel = {"type": rtype, "from": {"label": "Staff", "id": ACTOR}, "to": "ng"}
    rep = _validate(_req([_ng()], [rel]))
    assert not rep["ok"] and any(rtype in e for e in rep["errors"])


def test_relationship_end_labels_are_checked():
    rel = {"type": "MUST_AVOID", "from": {"label": "Staff", "id": ACTOR}, "to": "ng"}
    rep = _validate(_req([_ng()], [rel]))
    assert not rep["ok"] and any("MUST_AVOID" in e for e in rep["errors"])


def test_existing_node_must_be_pointed_by_valid_id():
    rel = {"type": "MUST_AVOID", "from": {"label": "Client", "id": "山田太郎"}, "to": "ng"}
    rep = _validate(_req([_ng()], [rel]))
    assert not rep["ok"]


def test_organization_holds_org_id_only():
    ok = _validate(_req([{"ref": "o", "label": "Organization", "origin": "Human", "properties": {"orgId": PROVIDER}}]))
    assert ok["ok"], ok["errors"]
    bad = _validate(_req([{"ref": "o", "label": "Organization", "origin": "Human", "properties": {"orgId": "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"}}]))
    assert not bad["ok"]
    named = _validate(_req([{"ref": "o", "label": "Organization", "origin": "Human", "properties": {"orgId": PROVIDER, "name": "架空"}}]))
    assert not named["ok"]                                                  # 機関の属性は置かない（D3）


def test_guardianship_type_only_for_guardianship():
    inv = {"ref": "i", "label": "Involvement", "origin": "AiExtracted", "properties": {
        "kind": "Medical", "howEnded": "Ongoing", "certainty": "Hearsay", "guardianshipType": "Guardianship"}}
    assert not _validate(_req([inv]))["ok"]
    inv["properties"]["kind"] = "Guardianship"
    assert _validate(_req([inv]))["ok"]


@pytest.mark.parametrize("value, ok", [("2026-09-15", True), ("2026/09/15", False), ("2026-02-30", False), ("9月15日", False)])
def test_dates_are_checked_not_guessed(value, ok):
    rep = _validate(_req([_ng(validFrom=value)]))
    assert rep["ok"] is ok


def test_datetime_needs_time_zone():
    rec = {"type": "PERFORMS", "from": {"label": "Person", "id": "PER-01H11111111111111111111111"}, "to": "c"}
    role = {"ref": "c", "label": "CareRole", "origin": "Human", "properties": {"name": "通院の付き添い"}}
    assert _validate(_req([role], [rec]))["ok"]
    review = {"ref": "rv", "label": "Review", "origin": "Human", "properties": {
        "domain": "NgAction", "reviewedAt": "2026-09-15T10:00:00", "informantKind": "Family"}}
    rep = _validate(_req([review]))
    assert not rep["ok"] and any("時差" in e for e in rep["errors"])


# ---- 二段の確度（ゲートの側でも守る。入口を通らない依頼にも効く） ----

def _gate_req(certainty, provider, provided=True):
    rels = [{"type": "ABOUT", "from": "r", "to": {"label": "Client", "id": CLIENT}}]
    nodes = [{"ref": "r", "label": "Record", "origin": "Human", "properties": {
        "kind": "Document", "text": "架空", "quote": "架空", "certainty": certainty, "informantKind": "Agency",
        **({"providerCertainty": provider} if provider else {})}}]
    if provided:
        nodes.append({"ref": "pv", "label": "Organization", "origin": "Human", "properties": {"orgId": PROVIDER}})
        rels.append({"type": "PROVIDED_BY", "from": "r", "to": "pv"})
    return _req(nodes, rels)


@pytest.mark.parametrize("certainty, provider, provided, ok", [
    ("Hearsay", "Confirmed", True, True),
    ("Inference", "Inference", True, True),
    ("Confirmed", "Confirmed", True, False),        # 受けた側が確かめたことにしない
    ("SelfReport", "SelfReport", True, False),
    ("Hearsay", None, True, False),                 # 提供元の確度が要る
    ("Hearsay", "Hearsay", False, False),           # 提供元が無いのに提供元の確度を書かない
    ("Hearsay", "Inference", True, False),          # 受けた側の確度は提供元より強くしない
])
def test_gate_two_level_rule(certainty, provider, provided, ok):
    assert _validate(_gate_req(certainty, provider, provided))["ok"] is ok


# ---- 入口が作る依頼はゲートの検証を通る ----

def test_intake_request_passes_validation():
    from tests.test_intake import _check, _proposal, _fact
    rep = _check(_proposal([_fact("ハナに尋ねると「転んだ」と言うが、転倒の具体的な状況は話せない", toldBy="p-hana")],
                           newPeople=[{"ref": "p-hana", "givenName": "ハナ"}]))
    assert rep["ok"], rep["errors"]
    v = _validate(rep["request"])
    assert v["ok"], v["errors"]


# ---- ゲートが持つ名前は正典にある（N-08 の「ゲートの許す一覧との突き合わせ」。ゲートは許す一覧を別に持たず正典を読む） ----

def test_gate_constants_refer_to_canon_names():
    from nest import canon
    from nest.gate import validate
    data = canon.load(validate.SCHEMA)
    nodes, rels = data["personal"]["nodes"], data["personal"]["relationships"]
    assert validate.GATE_ONLY_LABELS <= set(nodes)
    assert validate.GATE_ONLY_RELATIONSHIPS <= set(rels)
    for rtype, props in validate.GATE_MANAGED_REL.items():
        assert props <= set(rels[rtype]["required"]) | set(rels[rtype]["optional"]), rtype
    for label, prop in validate.EXTERNAL_ID_PROP.items():
        assert prop in nodes[label]["required"] and label in data["externalIds"]
    for label, props in validate.GATE_MANAGED_BY_LABEL.items():
        assert props <= set(nodes[label]["required"]) | set(nodes[label]["optional"])


# ---- N-16：AI 由来は未確定。人は名前で同定しない ----

def test_ai_extracted_nodes_are_planned_as_pending():
    human = {"ref": "c", "label": "CareRole", "origin": "Human", "properties": {"name": "通院の付き添い"}}
    rep = _validate(_req([_ng(), human]))
    assert rep["ok"], rep["errors"]
    status = {n["ref"]: n["status"] for n in rep["nodes"]}
    assert status == {"ng": "Pending", "c": "Active"}


@pytest.mark.parametrize("end", [
    {"label": "Person", "name": "ハナ"},                        # 名前で既にいる人を指す
    {"label": "Person", "id": "ハナ"},
    {"label": "Person", "id": "PER-01H11111111111111111111111", "name": "ハナ"},   # ID に名前を添えても止める
])
def test_existing_person_cannot_be_pointed_by_name(end):
    rec = {"ref": "r", "label": "Record", "origin": "AiExtracted", "properties": {
        "kind": "Interview", "text": "架空", "quote": "架空", "certainty": "Hearsay", "informantKind": "Family"}}
    rep = _validate(_req([rec], [{"type": "TOLD_BY", "from": "r", "to": end}]))
    assert not rep["ok"]


def test_new_person_ref_format_is_checked_at_intake():
    from tests.test_intake import _check, _proposal, _fact
    quote = "ハナに尋ねると「転んだ」と言うが、転倒の具体的な状況は話せない"
    for refs in ([{"ref": "ハナ", "givenName": "ハナ"}], [{"ref": "p-a"}, {"ref": "p-a"}]):
        rep = _check(_proposal([_fact(quote, toldBy=refs[0]["ref"])], newPeople=refs))
        assert not rep["ok"], refs
