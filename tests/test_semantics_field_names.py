"""項目の表示名（SEMANTICS SEM-FIELD-01。2026-11-11 河原さん）。DB を使わない。

review_proposals.py show に出る項目には、すべて日本語の表示名がある。表は正典の項目だけを名指す（項目・必須・列挙値は変えない）。
"""
import sys
from pathlib import Path

from nest import canon, semantics
from nest.gate import approve as ap
from nest.gate import write as gw

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import review_proposals as rp  # noqa: E402

NODES = canon.load(REPO / "docs" / "SCHEMA.md")["personal"]["nodes"]


def _shown(label):
    spec = NODES[label]
    return [k for k in spec["required"] + spec["optional"] if k != gw.key_of(label) and k not in rp.NOT_SHOWN]


def test_every_field_show_prints_has_a_display_name():
    names = semantics.field_names()
    missing = ["%s.%s" % (l, k) for l in sorted(ap.DECIDABLE) for k in _shown(l) if k not in names.get(l, {})]
    assert not missing, missing


def test_the_table_names_only_canon_fields_and_no_hidden_ones():
    for label, fields in semantics.field_names().items():
        assert label in NODES, label
        spec = NODES[label]
        for k, name in fields.items():
            assert k in spec["required"] + spec["optional"], "%s.%s" % (label, k)
            assert k not in rp.NOT_SHOWN and k != gw.key_of(label), "%s.%s" % (label, k)
            assert name and "`" not in name


def test_display_names_are_unique_within_a_label():
    for label, fields in semantics.field_names().items():
        assert len(set(fields.values())) == len(fields), label
