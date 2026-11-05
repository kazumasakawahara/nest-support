"""乖離の検査（N-08）：正典 docs/SCHEMA.md の表と、末尾の machine-check JSON を突き合わせる。

突き合わせるもの：§3 の ID の接頭辞、§4.2 のノードと項目（✅ は必須）、§4.3 のリレーションの
始点・終点と項目、§4.5 の列挙値。検査対象の節や表が見つからないときも失敗にする
（未検査を合格と区別するため）。ゲートの許す一覧との突き合わせは、ゲートができてから足す。

使い方：uv run python scripts/check_drift.py [docs/SCHEMA.md]
ずれが無ければ 0、あれば 1 を返す。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nest import canon  # noqa: E402

DEFAULT = ROOT / "docs" / "SCHEMA.md"
NAME_RE = re.compile(r"`(\w+)`(✅)?")
PAREN_RE = re.compile(r"\([^)]*\)|（[^）]*）")
PREFIX_RE = re.compile(r"`\^\(([A-Z|]+)\)-\[0-9A-HJKMNP-TV-Z\]\{26\}\$`")
ANY = "*"


def section(text, heading):
    """heading で始まる行から、次の見出しの行までを返す。無ければ None。"""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith(heading):
            body = []
            for rest in lines[i + 1:]:
                if rest.startswith("#"):
                    break
                body.append(rest)
            return "\n".join(body)
    return None


def rows(body):
    """`名前` で始まる表の行を、列の並びにして返す。"""
    out = []
    for line in body.split("\n"):
        if line.startswith("| `"):
            out.append([c.strip() for c in line.strip().strip("|").split("|")])
    return out


def props(cell):
    """項目の欄から {名前: 必須か} を取り出す。括弧の中（型・注記）は読まない。"""
    if cell in ("—", ""):
        return {}
    return {m.group(1): bool(m.group(2)) for m in NAME_RE.finditer(PAREN_RE.sub("", cell))}


def ends(cell):
    if cell.startswith("（") and cell.endswith("）"):
        return {ANY}
    return {x.strip() for x in cell.split("/")}


def _compare_fields(kind, name, table, spec, out):
    req, opt = set(spec["required"]), set(spec["optional"])
    t_req = {k for k, v in table.items() if v}
    t_opt = {k for k, v in table.items() if not v}
    if t_req != req:
        out.append("%s %s の必須が違う：表 %s ／ JSON %s" % (kind, name, sorted(t_req), sorted(req)))
    if t_opt != opt:
        out.append("%s %s の任意が違う：表 %s ／ JSON %s" % (kind, name, sorted(t_opt), sorted(opt)))


def check(path):
    """ずれの一覧を返す。空ならずれ無し。"""
    path = Path(path)
    try:
        data = canon.load(path)
    except canon.CanonError as e:
        return ["正典が読めない：%s" % e]
    text = path.read_text(encoding="utf-8")
    out = []
    personal = data["personal"]

    bodies = {}
    for key, heading in (("ids", "## 3. "), ("nodes", "### 4.2 "), ("rels", "### 4.3 "), ("enums", "### 4.5 ")):
        bodies[key] = section(text, heading)
        if not bodies[key]:
            out.append("節が見つからない：%s" % heading.strip())
    if out:
        return out

    # §3 接頭辞
    m = PREFIX_RE.search(bodies["ids"])
    if not m:
        out.append("§3 に接頭辞の正規表現が見つからない")
    elif set(m.group(1).split("|")) != set(data["idPrefixes"].values()):
        out.append("§3 の接頭辞が違う：表 %s ／ JSON %s" % (sorted(m.group(1).split("|")), sorted(data["idPrefixes"].values())))

    # §4.2 ノード
    t_nodes = {}
    for r in rows(bodies["nodes"]):
        if len(r) >= 2:
            label = NAME_RE.match(r[0])
            if label:
                t_nodes[label.group(1)] = props(r[1])
    if not t_nodes:
        out.append("§4.2 にノードの表が見つからない")
    for label in sorted(set(t_nodes) ^ set(personal["nodes"])):
        out.append("ノード %s が %s にしかない" % (label, "表" if label in t_nodes else "JSON"))
    for label in sorted(set(t_nodes) & set(personal["nodes"])):
        _compare_fields("ノード", label, t_nodes[label], personal["nodes"][label], out)

    # §4.3 リレーション
    t_rels = {}
    for r in rows(bodies["rels"]):
        if len(r) >= 3 and "→" in r[1]:
            name = NAME_RE.match(r[0]).group(1)
            frm, to = r[1].split("→", 1)
            t_rels[name] = (ends(frm.strip()), ends(to.strip()), props(r[2]))
    if not t_rels:
        out.append("§4.3 にリレーションの表が見つからない")
    for name in sorted(set(t_rels) ^ set(personal["relationships"])):
        out.append("リレーション %s が %s にしかない" % (name, "表" if name in t_rels else "JSON"))
    for name in sorted(set(t_rels) & set(personal["relationships"])):
        frm, to, fields = t_rels[name]
        spec = personal["relationships"][name]
        if frm != set(spec["from"]):
            out.append("リレーション %s の始点が違う：表 %s ／ JSON %s" % (name, sorted(frm), sorted(spec["from"])))
        if to != set(spec["to"]):
            out.append("リレーション %s の終点が違う：表 %s ／ JSON %s" % (name, sorted(to), sorted(spec["to"])))
        _compare_fields("リレーション", name, fields, spec, out)

    # §4.5 列挙値
    t_enums = {}
    for r in rows(bodies["enums"]):
        if len(r) >= 2:
            names = NAME_RE.findall(PAREN_RE.sub("", r[0]))
            values = [n for n, _ in NAME_RE.findall(PAREN_RE.sub("", r[1]))]
            for n, _ in names:
                t_enums[n] = values
    if not t_enums:
        out.append("§4.5 に列挙値の表が見つからない")
    for name in sorted(set(t_enums) ^ set(data["enums"])):
        out.append("列挙値 %s が %s にしかない" % (name, "表" if name in t_enums else "JSON"))
    for name in sorted(set(t_enums) & set(data["enums"])):
        if t_enums[name] != data["enums"][name]:
            out.append("列挙値 %s が違う：表 %s ／ JSON %s" % (name, t_enums[name], data["enums"][name]))
    return out


def main(argv):
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT
    drift = check(path)
    for d in drift:
        print(d)
    print("ずれ %d 件（%s）" % (len(drift), path))
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
