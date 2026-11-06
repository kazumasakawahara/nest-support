"""住所から 6 桁の団体コードを出す（N-24a。正典 v0.4 Residence.areaCode、台帳 G-43）。手元だけ。外に送らない。

表は nest/data/area-codes-kitakyushu-2026-10-25.json（tsunagu-net の docs/reference から写した。出どころと版は docs/SEMANTICS.md）。
- 住所を Unicode の NFKC にそろえ、空白を除き、先頭の「福岡県」を外す
- 表の名前（「北九州市小倉北区」・「遠賀郡芦屋町」・「芦屋町」など）が住所の先頭に一致するもののうち、いちばん長いもの
- 一致しなければ空。区だけ・町名だけからは推測しない
"""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

TABLE_PATH = Path(__file__).resolve().parent / "data" / "area-codes-kitakyushu-2026-10-25.json"
TABLE_SHA256 = "a7700fd45f8e7811964531344bcf0584022de9c6b7fde0f02df6212fa7e291db"
PREFECTURE = "福岡県"


def _norm(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def _names():
    raw = TABLE_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != TABLE_SHA256:
        raise RuntimeError("団体コードの表の指紋が記録と合わない（%s）" % TABLE_PATH.name)
    out = {}
    for row in json.loads(raw.decode("utf-8"))["rows"]:
        for name in (row["official_name"], row["name"]):
            out[_norm(name)] = row["official_code6"]
    return sorted(out.items(), key=lambda kv: -len(kv[0]))


NAMES = _names()


def from_address(address):
    if not isinstance(address, str):
        return ""
    text = _norm(address)
    if text.startswith(PREFECTURE):
        text = text[len(PREFECTURE):]
    for name, code in NAMES:
        if text.startswith(name):
            return code
    return ""
