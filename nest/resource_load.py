"""資源の側の読み込み（N-23。ADR-001 D2-1・D2-3）。資源の側に書くのは、この道具だけ。

tsunagu-net の配布の一式（scripts/make_distribution.py が作る。指紋は MANIFEST.json）の資源 DB の書き出しを、
nest-support の資源の側（compose のサービス neo4j-resource）にそのまま読み込む。
- MANIFEST.json の書き出しの SHA-256 がファイルと合わなければ読み込まない。読めない・無い・二つある・一式の外を指す、も止める
- 版は、一式の docs/SCHEMA.md（MANIFEST の指紋と合うもの）の最初の「# 」の見出しの版。合わなければ止める
- 読み込むときは資源の側のコンテナだけを止め、neo4j-admin database load で置き換え、また起動する。個人の側には触れない
- 読み込んだ版と指紋は nest_neo4j_resource_meta/load.json に残す（照会の結果に添えるため。資源の側の MCP が返す）
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IMAGE = "neo4j:5.26.32-community@sha256:adaa077a3ab023015143b8f73f7076a7d053f12985f5b06f4c6a128c3a2f7240"
DUMP_PATH = re.compile(r"^resource/tsunagu-resource-[0-9-]+\.dump$")
VERSION = re.compile(r"\bv\d+(?:\.\d+)+\b")
DATA_DIR = REPO / "nest_neo4j_resource_data"
STAGE_DIR = REPO / "nest_neo4j_resource_load"
RECORD = REPO / "nest_neo4j_resource_meta" / "load.json"
ENV_FILE = Path.home() / ".config" / "nest" / "neo4j-redesign.env"


class LoadRefused(Exception):
    """読み込まない（指紋が合わない、一式の形が違う、など）。"""


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _entries(bundle):
    try:
        data = json.loads((bundle / "MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise LoadRefused("MANIFEST.json が読めない：%s" % e)
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, list):
        raise LoadRefused("MANIFEST.json に files の一覧が無い")
    return {f.get("path"): f.get("sha256") for f in files if isinstance(f, dict)}


def _checked(bundle, rel, want):
    path = (bundle / rel).resolve()
    if bundle.resolve() not in path.parents:
        raise LoadRefused("%s は一式の外を指す" % rel)
    if not path.is_file():
        raise LoadRefused("%s が無い" % rel)
    got = _sha256(path)
    if got != want:
        raise LoadRefused("%s の指紋が MANIFEST.json と合わない（MANIFEST %s…・ファイル %s…）" % (rel, str(want)[:12], got[:12]))
    return path, got


def verify(bundle):
    bundle = Path(bundle)
    entries = _entries(bundle)
    dumps = [p for p in entries if isinstance(p, str) and p.endswith(".dump")]
    if len(dumps) != 1 or not DUMP_PATH.match(dumps[0]):
        raise LoadRefused("MANIFEST.json の資源 DB の書き出しは resource/tsunagu-resource-*.dump がちょうど一つ（%r）" % dumps)
    path, digest = _checked(bundle, dumps[0], entries[dumps[0]])
    if "docs/SCHEMA.md" not in entries:
        raise LoadRefused("MANIFEST.json に docs/SCHEMA.md が無い（版が分からない）")
    try:
        schema, _ = _checked(bundle, "docs/SCHEMA.md", entries["docs/SCHEMA.md"])
    except LoadRefused as e:
        raise LoadRefused("docs/SCHEMA.md：%s" % e)
    heading = next((l for l in schema.read_text(encoding="utf-8").splitlines() if l.startswith("# ")), "")
    m = VERSION.search(heading)
    if not m:
        raise LoadRefused("docs/SCHEMA.md の最初の見出しに版が無い")
    return {"bundle": str(bundle.resolve()), "dump": dumps[0], "dumpPath": str(path), "sha256": digest,
            "manifestSha256": _sha256(bundle / "MANIFEST.json"), "schemaVersion": m.group(0)}


def steps(bundle):
    """流す手順（コマンドの並び）。資源の側のサービスだけを止め、読み込み、起動する。"""
    rec = verify(bundle)
    compose = ["docker", "compose", "--env-file", str(ENV_FILE)]
    return [
        compose + ["stop", "neo4j-resource"],
        ["cp", rec["dumpPath"], str(STAGE_DIR / "neo4j.dump")],
        ["docker", "run", "--rm", "-v", "%s:/data" % DATA_DIR, "-v", "%s:/backups" % STAGE_DIR, IMAGE,
         "neo4j-admin", "database", "load", "neo4j", "--from-path=/backups", "--overwrite-destination=true"],
        ["rm", str(STAGE_DIR / "neo4j.dump")],
        compose + ["start", "neo4j-resource"],
    ]


def write_record(rec, now=None):
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    out = dict(rec, loadedAt=(now or datetime.now(timezone.utc)).isoformat())
    out.pop("dumpPath", None)
    RECORD.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def read_record():
    try:
        return json.loads(RECORD.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
