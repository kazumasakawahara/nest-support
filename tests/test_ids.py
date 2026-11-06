"""N-10: ID の発番と検査（正典 v0.4 §3）。手本：tsunagu-net の tests/test_ids.py（読むだけ）。"""
from pathlib import Path

import pytest

from nest import canon, ids

SCHEMA = Path(__file__).resolve().parent.parent / "docs" / "SCHEMA.md"
ULID = "01HZZZZZZZZZZZZZZZZZZZZZZZ"


def test_prefixes_match_canon():
    data = canon.load(SCHEMA)
    assert ids.LABEL_PREFIX == data["idPrefixes"]
    assert data["externalIds"] == {"Organization": "ORG"}


@pytest.mark.parametrize("label", sorted(ids.LABEL_PREFIX))
def test_new_id_for_each_label_is_valid(label):
    value = ids.new_id_for(label)
    prefix = ids.LABEL_PREFIX[label]
    assert value.startswith(prefix + "-") and len(value) == len(prefix) + 27
    assert ids.is_valid_id(value, prefix)


def test_ids_are_not_made_from_names():
    """名前や生年月日から作らない（D8）：同じ入力が無いので、二度発番すれば違う ID になる。"""
    assert ids.new_id("CLI") != ids.new_id("CLI")


def test_ulids_issued_in_the_same_millisecond_keep_order():
    a = ids.new_ulid(now_ms=1_700_000_000_000)
    b = ids.new_ulid(now_ms=1_700_000_000_000)
    assert a < b


def test_personal_side_does_not_issue_org_ids():
    with pytest.raises(ValueError):
        ids.new_id("ORG")
    with pytest.raises(ValueError):
        ids.new_id_for("Organization")


def test_unknown_prefix_is_rejected():
    with pytest.raises(ValueError):
        ids.new_id("HH")          # tsunagu-net の世帯。nest-support では使わない


@pytest.mark.parametrize("value, ok", [
    ("ORG-" + ULID, True),
    ("ORG-" + ULID.lower(), False),
    ("ORG-" + ULID[:-1], False),
    ("ORG-01HZZZZZZZZZZZZZZZZZZZZZZI", False),   # I は Crockford の base32 に無い
    ("ORG " + ULID, False),
    ("CLI-" + ULID, False),
    (None, False),
])
def test_org_id_shape(value, ok):
    assert ids.is_valid_org_id(value) is ok


def test_personal_id_with_org_prefix_is_rejected():
    assert not ids.is_valid_id("ORG-" + ULID, "ORG")
    assert not ids.is_valid_id("ORG-" + ULID, "CLI")


@pytest.mark.parametrize("value, prefix, ok", [
    ("CLI-" + ULID, "CLI", True),
    ("CLI-" + ULID, "PER", False),
    ("RES-" + ULID, "RES", True),
    ("cli-" + ULID, "CLI", False),
    ("CLI-" + ULID + "0", "CLI", False),
])
def test_personal_id_shape(value, prefix, ok):
    assert ids.is_valid_id(value, prefix) is ok


@pytest.mark.parametrize("value, ok", [
    ("401307", True),     # 検査数字の合う 6 桁（どの団体のコードかは問わない）
    ("401308", False),    # 検査数字が合わない
    ("40130", False),
    ("4013071", False),
    (None, False),
])
def test_area_code_check_digit(value, ok):
    assert ids.is_valid_area_code(value) is ok
