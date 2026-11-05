"""N-23：資源の側の読み込み（ADR-001 D2-1・D2-3）。DB と docker を使わない部分。

- 一式の MANIFEST.json にある資源 DB の書き出し（resource/tsunagu-resource-*.dump）の SHA-256 が、ファイルと合わなければ読み込まない
- 書き出しが MANIFEST に無い・二つある・道筋が一式の外を指す、MANIFEST が読めない、も読み込まない
- 読み込んだ版（一式の正典の版）と指紋を記録に残す
- 既定は流す手順を出すだけ（--write で流す）。資源の側のコンテナを止めてから neo4j-admin で読み込み、また起動する
架空の一式（中身は架空のバイト列）を tmp に作って確かめる。
"""
import hashlib
import json
from pathlib import Path

import pytest

from nest import resource_load as rl

REPO = Path(__file__).resolve().parents[1]
DUMP = "resource/tsunagu-resource-2026-01-01-0000.dump"


def _bundle(tmp_path, dump_bytes=b"fictional dump", manifest=None, schema="# つなぐネット スキーマ正典 v0.99\n"):
    (tmp_path / "resource").mkdir()
    (tmp_path / DUMP).write_bytes(dump_bytes)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "SCHEMA.md").write_text(schema, encoding="utf-8")
    files = [{"path": DUMP, "sha256": hashlib.sha256(dump_bytes).hexdigest()},
             {"path": "docs/SCHEMA.md", "sha256": hashlib.sha256(schema.encode("utf-8")).hexdigest()}]
    (tmp_path / "MANIFEST.json").write_text(json.dumps(manifest if manifest is not None else {"files": files}), encoding="utf-8")
    return tmp_path


def test_matching_fingerprint_is_accepted(tmp_path):
    b = _bundle(tmp_path)
    rec = rl.verify(b)
    assert rec["dump"] == DUMP
    assert rec["sha256"] == hashlib.sha256(b"fictional dump").hexdigest()
    assert rec["schemaVersion"] == "v0.99"
    assert rec["manifestSha256"] == hashlib.sha256((b / "MANIFEST.json").read_bytes()).hexdigest()


def test_version_is_read_from_the_first_heading_after_a_comment(tmp_path):
    b = _bundle(tmp_path, schema="<!--\n  注釈 v9.9\n-->\n\n# tsunagu-net スキーマ正典 — v0.29\n")
    assert rl.verify(b)["schemaVersion"] == "v0.29"


def test_tampered_dump_is_refused(tmp_path):
    b = _bundle(tmp_path)
    (b / DUMP).write_bytes(b"changed")
    with pytest.raises(rl.LoadRefused, match="指紋"):
        rl.verify(b)


@pytest.mark.parametrize("manifest", [
    {"files": []},
    {"files": [{"path": DUMP, "sha256": "0" * 64}, {"path": "resource/tsunagu-resource-2026-01-02-0000.dump", "sha256": "0" * 64}]},
    {"files": [{"path": "../resource/tsunagu-resource-2026-01-01-0000.dump", "sha256": "0" * 64}]},
    {"files": [{"path": "/etc/tsunagu-resource-x.dump", "sha256": "0" * 64}]},
    {"nofiles": 1},
    [],
])
def test_bad_manifest_is_refused(tmp_path, manifest):
    with pytest.raises(rl.LoadRefused):
        rl.verify(_bundle(tmp_path, manifest=manifest))


def test_unreadable_manifest_is_refused(tmp_path):
    b = _bundle(tmp_path)
    (b / "MANIFEST.json").write_text("{", encoding="utf-8")
    with pytest.raises(rl.LoadRefused):
        rl.verify(b)


def test_missing_dump_is_refused(tmp_path):
    b = _bundle(tmp_path)
    (b / DUMP).unlink()
    with pytest.raises(rl.LoadRefused):
        rl.verify(b)


def test_schema_not_matching_manifest_gives_no_version(tmp_path):
    b = _bundle(tmp_path)
    (b / "docs" / "SCHEMA.md").write_text("# 書き換えた v1.0\n", encoding="utf-8")
    with pytest.raises(rl.LoadRefused, match="SCHEMA"):
        rl.verify(b)


def test_steps_touch_only_the_resource_service(tmp_path):
    steps = rl.steps(_bundle(tmp_path))
    text = "\n".join(" ".join(s) for s in steps)
    assert "neo4j-personal" not in text and "nest-redesign-personal" not in text
    assert "--remove-orphans" not in text and " down" not in text
    assert any(s[-2:] == ["stop", "neo4j-resource"] for s in steps)
    assert any(s[-2:] == ["start", "neo4j-resource"] for s in steps)
    load = next(s for s in steps if "neo4j-admin" in s)
    assert "--overwrite-destination=true" in load
    assert any(a.endswith("nest_neo4j_resource_data:/data") for a in load)
    assert any(a.startswith("neo4j:5.26.32-community@sha256:") for a in load)


def test_image_matches_compose():
    compose = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    assert rl.IMAGE in compose


def test_record_keeps_version_and_fingerprint_and_the_resource_mcp_returns_it(tmp_path, monkeypatch):
    monkeypatch.setattr(rl, "RECORD", tmp_path / "meta" / "load.json")
    (tmp_path / "b").mkdir()
    rec = rl.write_record(rl.verify(_bundle(tmp_path / "b")))
    assert rec["schemaVersion"] == "v0.99" and len(rec["sha256"]) == 64 and "loadedAt" in rec and "dumpPath" not in rec
    from nest import mcp_resource
    assert mcp_resource.resource_version() == rec


def test_resource_mcp_says_when_nothing_was_loaded(tmp_path, monkeypatch):
    monkeypatch.setattr(rl, "RECORD", tmp_path / "none.json")
    from nest import mcp_resource
    assert mcp_resource.resource_version() == {"loaded": False}
