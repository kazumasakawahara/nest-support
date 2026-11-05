"""N-19：正典の JSON から個人の側の一意制約とインデックスの文を作る。ベクトル・全文インデックスを作らない。

手本：tsunagu-net の tsunagu/schema_apply.py と tests/test_schema_apply.py（読むだけ）。
nest-support の正典は個人の側だけを持つ。資源の側の制約は tsunagu-net の書き出しに入っている（N-23）。
DB に当てる結合の試験は tests/test_db_new_live.py（NEST_LIVE_DB=1 のときだけ）。
"""
import copy
from pathlib import Path

import pytest

from nest import canon, schema_apply

SCHEMA = Path(__file__).resolve().parents[1] / "docs" / "SCHEMA.md"


def _c():
    return canon.load(SCHEMA)


def test_every_unique_property_gets_a_constraint():
    c = _c()
    stmts = schema_apply.statements(c)
    for label, spec in c["personal"]["nodes"].items():
        for prop in spec["unique"]:
            name = schema_apply.constraint_name(label, prop)
            assert any(name in s and "IS UNIQUE" in s for s in stmts), (label, prop)


def test_expected_names_match_statements():
    c = _c()
    stmts = schema_apply.statements(c)
    names = schema_apply.expected_constraint_names(c) + schema_apply.expected_index_names(c)
    assert len(stmts) == len(names)
    for name, s in zip(names, stmts):
        assert (" %s " % name) in s


def test_statements_are_idempotent():
    for s in schema_apply.statements(_c()):
        assert "IF NOT EXISTS" in s, s


def test_no_vector_or_fulltext_index():
    for s in schema_apply.statements(_c()):
        assert "VECTOR" not in s.upper() and "FULLTEXT" not in s.upper(), s


def test_range_indexes_follow_canon():
    c = _c()
    stmts = schema_apply.statements(c)
    for idx in c["indexes"]:
        assert any(schema_apply.index_name(idx["label"], idx["property"]) in s for s in stmts), idx


def test_forbidden_index_kind_in_canon_is_rejected():
    for kind in ("VECTOR", "FULLTEXT", "TEXT"):
        c = copy.deepcopy(_c())
        c["indexes"].append({"label": "Record", "property": "text", "kind": kind})
        with pytest.raises(ValueError):
            schema_apply.statements(c)


@pytest.mark.parametrize("label,prop", [("Person`) DETACH DELETE (n", "personId"), ("Person", "id`) DETACH"), ("", "x")])
def test_unsafe_names_are_rejected(label, prop):
    c = copy.deepcopy(_c())
    c["personal"]["nodes"] = {label: {"required": [], "optional": [], "unique": [prop]}}
    with pytest.raises(ValueError):
        schema_apply.statements(c)
