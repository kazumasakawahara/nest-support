"""ID の発番と検査（N-10。正典 v0.4 §3）。手本：tsunagu-net の tsunagu/ids.py（読むだけ）。

- 個人の側のノードの ID は「接頭辞-ULID」。ULID は時刻（ミリ秒、48 ビット）と乱数（80 ビット）を
  Crockford の base32 で 26 文字にしたもの。名前や生年月日から作らない（ADR D8）
- `ORG-` は資源の側の機関の ID。個人の側では発番せず、形だけを確かめる（ADR D3）
- 団体コードは総務省の 6 桁（上 5 桁＋検査数字）。`Residence.areaCode` に使う
- 接頭辞の表は正典の JSON（`idPrefixes`）と同じ。ずれは tests/test_ids.py が見つける
"""
import re
import secrets
import time

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
# 表示用の仮名の字（2026-11-06 河原さん。台帳 G-52）：Crockford の字から紛れやすい 0・1 を除いた 30 字（O・I・L は元から無い）
DISPLAY_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
ULID_RE = r"[0-9A-HJKMNP-TV-Z]{26}"
ORG_PREFIX = "ORG"
LABEL_PREFIX = {
    "Client": "CLI", "Person": "PER", "Staff": "STF", "Involvement": "INV", "Residence": "RES", "Record": "REC",
    "NgAction": "NGA", "CarePreference": "CPF", "Condition": "CND", "Wish": "WSH", "LifeHistory": "LHS",
    "CareRole": "CRL", "Certificate": "CRT", "PublicAssistance": "PAS", "SupportLog": "SLG",
    "Review": "REV", "AuditLog": "AUD",
}
PREFIXES = frozenset(LABEL_PREFIX.values())


def _encode(value, length):
    out = []
    for _ in range(length):
        out.append(CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(out))


_last = {"ms": -1, "rand": 0}


def new_ulid(now_ms=None):
    """同じミリ秒の中では、乱数の部分を 1 ずつ増やす（ULID の単調増加の方式）。発番した順に並ぶ。"""
    ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    if not 0 <= ms < 2 ** 48:
        raise ValueError("時刻が ULID の範囲外")
    if ms == _last["ms"] and _last["rand"] < 2 ** 80 - 1:
        rand = _last["rand"] + 1
    else:
        rand = secrets.randbits(79)  # 上の 1 ビットを空けて、同じミリ秒に増やす余地を残す
    _last.update(ms=ms, rand=rand)
    return _encode(ms, 10) + _encode(rand, 16)


def new_id(prefix, now_ms=None):
    if prefix not in PREFIXES:
        raise ValueError("個人の側で発番しない接頭辞: %s" % prefix)
    return "%s-%s" % (prefix, new_ulid(now_ms))


def new_id_for(label, now_ms=None):
    if label not in LABEL_PREFIX:
        raise ValueError("個人の側で ID を発番しないラベル: %s" % label)
    return new_id(LABEL_PREFIX[label], now_ms)


def is_valid_id(value, prefix):
    """個人の側の ID の形か。`ORG` は個人の側の接頭辞ではないので常に偽。"""
    return (isinstance(value, str) and prefix in PREFIXES
            and re.fullmatch(r"%s-%s" % (prefix, ULID_RE), value) is not None)


def is_valid_org_id(value):
    return isinstance(value, str) and re.fullmatch(r"%s-%s" % (ORG_PREFIX, ULID_RE), value) is not None


def area_check_digit(code5):
    """上 5 桁に 6,5,4,3,2 を掛けた和を 11 で割った余りを 11 から引き、その 1 の位。"""
    if not re.fullmatch(r"[0-9]{5}", code5 or ""):
        raise ValueError("団体コードの上 5 桁ではない: %r" % code5)
    s = sum(int(d) * w for d, w in zip(code5, (6, 5, 4, 3, 2)))
    return (11 - s % 11) % 10


def is_valid_area_code(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{6}", value):
        return False
    return area_check_digit(value[:5]) == int(value[5])
