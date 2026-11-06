"""正典（docs/SCHEMA.md）の machine-check JSON を読む部品（N-07）。

正典の中にちょうど 1 つある ```json machine-check のブロックを読み、形を確かめて返す。
形が合わなければ CanonError。読めないものを空として扱わない（未検査を合格と区別するため）。
手本：tsunagu-net の tsunagu/canon.py（読むだけ）。nest-support は個人の側だけを持つ。
"""
import json
import re
from pathlib import Path

BLOCK_RE = re.compile(r"^```json machine-check\n(.*?)^```", re.S | re.M)
TOP_KEYS = ("version", "personal", "idPrefixes", "externalIds", "enums", "enumBindings")
NODE_LISTS = ("required", "optional", "unique")
REL_LISTS = ("from", "to", "required", "optional")
ANY_LABEL = "*"
RESERVED_PREFIX = "ORG"  # 資源の側の機関の ID。個人の側で発番しない（ADR D3）。externalIds でだけ使う


class CanonError(Exception):
    """正典が読めない、または形が合わない。"""


def extract_block(text):
    blocks = BLOCK_RE.findall(text)
    if len(blocks) != 1:
        raise CanonError("machine-check のブロックがちょうど 1 つではない（%d 個）" % len(blocks))
    return blocks[0]


def load(path):
    path = Path(path)
    if not path.is_file():
        raise CanonError("正典が見つからない: %s" % path)
    try:
        data = json.loads(extract_block(path.read_text(encoding="utf-8")))
    except ValueError as e:
        raise CanonError("machine-check の JSON が読めない: %s" % e)
    validate(data)
    return data


def _is_list(v):
    return isinstance(v, list)


def validate(data):
    if not isinstance(data, dict):
        raise CanonError("machine-check の最上位がオブジェクトではない")
    missing = [k for k in TOP_KEYS if k not in data]
    if missing:
        raise CanonError("最上位のキーが欠けている: %s" % ", ".join(missing))

    personal = data["personal"]
    if not isinstance(personal, dict):
        raise CanonError("personal がオブジェクトではない")
    for k in ("nodes", "relationships"):
        if not isinstance(personal.get(k), dict):
            raise CanonError("personal.%s が無い" % k)

    nodes = personal["nodes"]
    for label, spec in nodes.items():
        for k in NODE_LISTS:
            if not _is_list(spec.get(k)):
                raise CanonError("personal.nodes.%s に %s の並びが無い" % (label, k))

    for rel, spec in personal["relationships"].items():
        for k in REL_LISTS:
            if not _is_list(spec.get(k)):
                raise CanonError("personal.relationships.%s に %s の並びが無い" % (rel, k))
        for end in ("from", "to"):
            if not spec[end]:
                raise CanonError("personal.relationships.%s の %s が空" % (rel, end))
            for label in spec[end]:
                if label != ANY_LABEL and label not in nodes:
                    raise CanonError("personal.relationships.%s の %s に無いラベル: %s" % (rel, end, label))

    prefixes = data["idPrefixes"]
    external = data["externalIds"]
    if not isinstance(prefixes, dict) or not isinstance(external, dict):
        raise CanonError("idPrefixes・externalIds がオブジェクトではない")
    for label in nodes:
        if (label in prefixes) == (label in external):
            raise CanonError("%s は idPrefixes と externalIds のちょうど一方に要る" % label)
    for label, prefix in external.items():
        if prefix != RESERVED_PREFIX:
            raise CanonError("externalIds の %s が %s ではない" % (label, RESERVED_PREFIX))
    if RESERVED_PREFIX in prefixes.values():
        raise CanonError("個人の側の接頭辞に %s を使っている" % RESERVED_PREFIX)
    values = list(prefixes.values())
    if len(values) != len(set(values)):
        raise CanonError("idPrefixes に同じ接頭辞がある")

    enums = data["enums"]
    if not isinstance(enums, dict):
        raise CanonError("enums がオブジェクトではない")
    for name, vals in enums.items():
        if not _is_list(vals) or not vals:
            raise CanonError("enums.%s が空か並びではない" % name)

    if not isinstance(data["enumBindings"], dict):
        raise CanonError("enumBindings がオブジェクトではない")
    for prop, name in data["enumBindings"].items():
        if name not in enums:
            raise CanonError("enumBindings の %s が無い列挙値 %s を指す" % (prop, name))
