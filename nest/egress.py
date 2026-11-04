"""送信の歯止め（N-02。docs/external-api.md v0.3 §5、ADR-001 D11、台帳 G-19）。

- 送り先の一覧（文書の NEXT 行）をコードに持つ。一覧に無い行・やめた行・行のホストと違う URL には送らない
- 「止める」「使わない」の行（gated）は、機能ごとの明示の設定と契約の確認の記録の両方がそろうまで送らない
- 外部 API の鍵の有無は見ない
- 設定と記録の置き場所はコードに固定する。環境変数（HOME を含む）では変えられない
- 迷ったら不許可（閉じる側に倒す）
"""
import json
import os
import pwd
import re
import stat
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[1]
DOCUMENT = REPO / "docs" / "external-api.md"

GEMINI = "generativelanguage.googleapis.com"


@dataclass(frozen=True)
class Destination:
    host: str | None  # None：nest-support の Python からは送らない（Claude のアプリが送る、など）
    kind: str  # "gated"（設定と記録がそろうまで送らない）／"open"（使う）／"abolished"（やめた）


DESTINATIONS = {
    "NEXT-01": Destination(None, "gated"),
    "NEXT-02": Destination(None, "gated"),
    "NEXT-03": Destination(GEMINI, "gated"),
    "NEXT-04": Destination(GEMINI, "gated"),
    "NEXT-05": Destination("api.line.me", "gated"),
    "NEXT-06": Destination(GEMINI, "abolished"),
    "NEXT-07": Destination(GEMINI, "abolished"),
    "NEXT-08": Destination("laws.e-gov.go.jp", "open"),
    "NEXT-09": Destination("github.com", "open"),
    "NEXT-10": Destination(None, "open"),
    "NEXT-11": Destination("registry.npmjs.org", "abolished"),
}

# 契約の確認の記録の項目（external-api §0 の 5 項目を、機械が読む名前にしたもの）と、次に確かめる日
RECORD_FIELDS = frozenset({
    "checkedBy", "checkedOn",              # 1. 確かめた人と日付
    "contractName", "contractVersion",     # 2. 送り先と契約の名前・版
    "trainingUse", "retention",            # 3. 入力を学習に使うか、保存の期間
    "legalArrangement",                    # 4. 外国にある第三者への提供か、委託か、の整理
    "sendsSensitiveData",                  # 5. 要配慮個人情報を送ること（明示の true だけ）
    "nextReviewOn",                        # 次に確かめる日
})
TEXT_FIELDS = RECORD_FIELDS - {"checkedOn", "nextReviewOn", "sendsSensitiveData"}
RECORD_VERSION = 1


class EgressDenied(Exception):
    """送らない（不許可）。理由を文で持つ。"""


def _home() -> Path:
    # HOME の環境変数ではなく、OS の利用者の情報から取る（環境変数で置き場所を変えさせない）
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def record_path() -> Path:
    return _home() / ".config" / "nest" / "external-api-record.json"


def features_path() -> Path:
    return _home() / ".config" / "nest" / "external-api-features.json"


def today() -> date:
    return date.today()


def _read_private_json(path: Path, what: str):
    path = Path(path)
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        raise EgressDenied("%s が無い（%s）" % (what, path)) from None
    except OSError as e:
        raise EgressDenied("%s を確かめられない（%s）" % (what, e)) from None
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise EgressDenied("%s が通常のファイルでない" % what)
    if st.st_uid != os.getuid():
        raise EgressDenied("%s の持ち主が今の利用者でない" % what)
    if st.st_mode & 0o177:
        raise EgressDenied("%s の権限が 600 より広い（%o）" % (what, stat.S_IMODE(st.st_mode)))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise EgressDenied("%s が読めない" % what) from None


def _date(entry: dict, key: str) -> date:
    v = entry.get(key)
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        raise EgressDenied("%s が YYYY-MM-DD の日付でない" % key)
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise EgressDenied("%s が日付として正しくない" % key) from None


def check_record(path: Path, row: str, on: date) -> None:
    """契約の確認の記録を確かめる。不許可なら EgressDenied。"""
    data = _read_private_json(path, "契約の確認の記録")
    if not isinstance(data, dict) or data.get("version") != RECORD_VERSION:
        raise EgressDenied("契約の確認の記録の版が %d でない" % RECORD_VERSION)
    dests = data.get("destinations")
    entry = dests.get(row) if isinstance(dests, dict) else None
    if not isinstance(entry, dict):
        raise EgressDenied("%s の記録が無い（ほかの行の記録では開かない）" % row)
    missing = sorted(RECORD_FIELDS - entry.keys())
    if missing:
        raise EgressDenied("%s の記録に項目が欠けている：%s" % (row, "・".join(missing)))
    unknown = sorted(entry.keys() - RECORD_FIELDS)
    if unknown:
        raise EgressDenied("%s の記録に決まっていない項目がある：%s" % (row, "・".join(unknown)))
    for key in sorted(TEXT_FIELDS):
        v = entry[key]
        if not isinstance(v, str) or not v.strip():
            raise EgressDenied("%s の記録の %s が空" % (row, key))
    if entry["sendsSensitiveData"] is not True:
        raise EgressDenied("%s の記録の sendsSensitiveData が明示の true でない" % row)
    if _date(entry, "checkedOn") > on:
        raise EgressDenied("%s の記録の checkedOn が今日より後" % row)
    if _date(entry, "nextReviewOn") < on:
        raise EgressDenied("%s の記録の次に確かめる日（nextReviewOn）を過ぎている" % row)


def check_feature(path: Path, row: str) -> None:
    """機能ごとの明示の設定を確かめる。明示の true だけが許可。"""
    data = _read_private_json(path, "機能の設定")
    if not isinstance(data, dict):
        raise EgressDenied("機能の設定が {行: true/false} の形でない")
    unknown = sorted(k for k in data if k not in DESTINATIONS)
    if unknown:
        raise EgressDenied("機能の設定に一覧に無い行がある：%s" % "・".join(unknown))
    not_bool = sorted(k for k, v in data.items() if not isinstance(v, bool))
    if not_bool:
        raise EgressDenied("機能の設定の値が true/false でない：%s" % "・".join(not_bool))
    if data.get(row) is not True:
        raise EgressDenied("%s が機能の設定で明示に有効になっていない" % row)


def _destination(row: str) -> Destination:
    d = DESTINATIONS.get(row)
    if d is None:
        raise EgressDenied("%s は送り先の一覧に無い" % row)
    if d.kind == "abolished":
        raise EgressDenied("%s はやめた行" % row)
    return d


def authorize(row: str) -> None:
    """この行で送ってよいかを確かめる。不許可なら EgressDenied。"""
    d = _destination(row)
    if d.kind == "open":
        return
    check_feature(features_path(), row)
    check_record(record_path(), row, today())


def check_url(row: str, url: str) -> None:
    """URL がこの行のホスト（https）に向いているかを確かめる。"""
    d = _destination(row)
    parts = urlsplit(url)
    if d.host is None or parts.scheme != "https" or parts.hostname != d.host:
        raise EgressDenied("%s の送り先（%s）でない URL：%s" % (row, d.host, parts.hostname))


def ensure(row: str, url: str) -> None:
    """送る直前に呼ぶ：行の許可と URL の両方を確かめる。"""
    authorize(row)
    check_url(row, url)


# --- 文書との突き合わせ -----------------------------------------------------------

_HOST = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+(/\S*)?$")
_BOLD = re.compile(r"\*\*(.+?)\*\*")


def _kind(cell: str) -> str:
    m = _BOLD.search(cell)
    label = m.group(1) if m else ""
    if label.startswith("やめる"):
        return "abolished"
    if label == "使う":
        return "open"
    return "gated"


def record_fields_from_document(path: Path) -> frozenset:
    """文書 §0 の対応表（見出しが「| §0 の項目」の表）から、JSON の項目の名前を集める。"""
    names = set()
    in_table = False
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("| §0 の項目"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) > 1:
                names.update(re.findall(r"`([A-Za-z]+)`", cells[1]))
    return frozenset(names)


def rows_from_document(path: Path) -> dict:
    """文書の NEXT 行から {行: (ホスト, 種類)} を作る。「同上」は直前の行のホストを継ぐ。"""
    rows = {}
    prev_host = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.startswith("| NEXT-"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        row, api = cells[0], cells[1]
        hosts = [h.split("/")[0] for h in re.findall(r"`([^`]+)`", api) if _HOST.match(h)]
        host = hosts[0] if hosts else (prev_host if "同上" in api else None)
        rows[row] = (host, _kind(cells[-2]))
        prev_host = host
    return rows
