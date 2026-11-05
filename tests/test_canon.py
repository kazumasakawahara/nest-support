"""N-07: 正典（docs/SCHEMA.md）の machine-check JSON を読む部品の試験。"""
import copy
import json
from pathlib import Path

import pytest

from nest import canon

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "docs" / "SCHEMA.md"

MINIMAL = {
    "version": "0.0",
    "personal": {
        "commonRequired": ["registeredAt", "status", "origin"],
        "nodes": {
            "Client": {"required": ["clientId"], "optional": [], "unique": ["clientId"]},
            "Record": {"required": ["recordId", "certainty"], "optional": [], "unique": ["recordId"]},
        },
        "relationships": {
            "ABOUT": {"from": ["Record"], "to": ["Client"], "required": [], "optional": []},
        },
    },
    "idPrefixes": {"Client": "CLI", "Record": "REC"},
    "enums": {"status": ["Active"], "certainty": ["Confirmed"]},
    "enumBindings": {"*.status": "status", "Record.certainty": "certainty"},
}


def _write(tmp_path, data=None, raw=None, blocks=1):
    body = raw if raw is not None else json.dumps(data if data is not None else MINIMAL)
    text = "# 正典\n\n" + ("```json machine-check\n%s\n```\n\n" % body) * blocks
    p = tmp_path / "SCHEMA.md"
    p.write_text(text, encoding="utf-8")
    return p


def _broken(mutate):
    d = copy.deepcopy(MINIMAL)
    mutate(d)
    return d


def test_minimal_canon_loads(tmp_path):
    assert canon.load(_write(tmp_path))["version"] == "0.0"


def test_missing_file_fails(tmp_path):
    with pytest.raises(canon.CanonError):
        canon.load(tmp_path / "none.md")


@pytest.mark.parametrize("blocks", [0, 2])
def test_block_count_must_be_one(tmp_path, blocks):
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, blocks=blocks))


def test_broken_json_fails(tmp_path):
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, raw='{"version": "0.0",'))


@pytest.mark.parametrize("key", ["version", "personal", "idPrefixes", "enums", "enumBindings"])
def test_missing_top_key_fails(tmp_path, key):
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, _broken(lambda d: d.pop(key))))


@pytest.mark.parametrize("key", ["nodes", "relationships"])
def test_missing_personal_key_fails(tmp_path, key):
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, _broken(lambda d: d["personal"].pop(key))))


@pytest.mark.parametrize("key", ["required", "optional", "unique"])
def test_node_without_list_fails(tmp_path, key):
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, _broken(lambda d: d["personal"]["nodes"]["Client"].pop(key))))


@pytest.mark.parametrize("key", ["from", "to", "required", "optional"])
def test_relationship_without_list_fails(tmp_path, key):
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, _broken(lambda d: d["personal"]["relationships"]["ABOUT"].pop(key))))


def test_relationship_to_unknown_label_fails(tmp_path):
    def m(d):
        d["personal"]["relationships"]["ABOUT"]["to"] = ["Hospital"]
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, _broken(m)))


def test_node_without_id_prefix_fails(tmp_path):
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, _broken(lambda d: d["idPrefixes"].pop("Record"))))


def test_org_prefix_is_rejected(tmp_path):
    def m(d):
        d["idPrefixes"]["Record"] = "ORG"
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, _broken(m)))


def test_duplicate_id_prefix_fails(tmp_path):
    def m(d):
        d["idPrefixes"]["Record"] = "CLI"
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, _broken(m)))


def test_binding_to_unknown_enum_fails(tmp_path):
    def m(d):
        d["enumBindings"]["Record.certainty"] = "certainity"
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, _broken(m)))


def test_empty_enum_fails(tmp_path):
    def m(d):
        d["enums"]["certainty"] = []
    with pytest.raises(canon.CanonError):
        canon.load(_write(tmp_path, _broken(m)))


# --- 本物の正典 ---

def test_repository_canon_loads():
    data = canon.load(SCHEMA)
    assert data["version"] == "0.2"


def test_repository_canon_labels():
    nodes = canon.load(SCHEMA)["personal"]["nodes"]
    assert set(nodes) == {
        "Client", "Person", "Staff", "Involvement",
        "NgAction", "CarePreference", "Condition", "Wish", "LifeHistory", "CareRole",
        "Certificate", "PublicAssistance", "SupportLog",
        "Record", "Review", "AuditLog",
    }


def test_repository_canon_shared_enums_match_contract():
    """約束 3 と tsunagu-net v0.29 にそろえた列挙値（止まる点 2 の 4・8）。"""
    enums = canon.load(SCHEMA)["enums"]
    assert enums["certainty"] == ["Confirmed", "Hearsay", "SelfReport", "Inference", "Unspecified"]
    assert enums["informantKind"] == ["Self", "Family", "Agency", "Neighbor", "DocumentOnly"]
    assert set(enums["staffRole"]) <= {"Staff", "Approver", "Administrator"}
    assert "Approver" not in enums["staffRole"]


def test_repository_canon_record_fields_match_tsunagu():
    """止まる点 2 の 9：Record の項目は tsunagu-net v0.29 とすべてそろえる（heardOn は nest-support だけ）。"""
    rec = canon.load(SCHEMA)["personal"]["nodes"]["Record"]
    tsunagu = {"recordId", "kind", "aboutDate", "text", "certainty", "informantKind", "sourceHash",
               "quote", "documentHash", "providerCertainty", "receivedOn"}
    assert set(rec["required"]) | set(rec["optional"]) == tsunagu | {"heardOn"}


def test_repository_canon_has_no_embedding_property():
    data = canon.load(SCHEMA)
    for label, spec in data["personal"]["nodes"].items():
        for prop in spec["required"] + spec["optional"]:
            assert not prop.lower().startswith("embedding") and not prop.lower().endswith("embedding"), (label, prop)
