"""N-37：音声の置き場所と消す道具（2026-11-06 河原さん。止まる点 F-1、台帳 G-74）。DB も本物の tmutil も使わない。

- 置き場所はリポジトリの nest_voice_data/（git に入れない。権限 700、Time Machine の対象外）。音声は権限 600
- 音声の名前は、文字起こしの sha256（＝ intake がその文字起こしを原文にして作る Record.documentHash）と拡張子
- 消す道具は、その documentHash の Record が承認された（status が Active）音声と、置いてから 30 日を過ぎた音声を消す。
  DB の Record（documentHash を含む）には触れない
- 既定は消さずに数えるだけ（--write で消す）。DB を読めなくても、30 日を過ぎたものは消す（遅くとも 30 日の約束を守る）
- 名前の形（64 桁の 16 進と音声の拡張子）でないファイルには触れない
DB を使う確かめは tests/test_voice_live.py。
"""
import hashlib
import os
import stat
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from nest import voice

REPO = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 6, 12, 0, 0)
TRANSCRIPT = "（架空）散歩の途中で座り込んだ。"


def _h(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Fake:
    def __init__(self):
        self.calls = []

    def __call__(self, args):
        self.calls.append(list(args))
        return 0, ""


def _mode(p):
    return stat.S_IMODE(os.stat(p).st_mode)


def _put(root, text, age_days, ext=".webm"):
    root.mkdir(exist_ok=True)
    p = root / (_h(text) + ext)
    p.write_bytes(b"x")
    t = (NOW - timedelta(days=age_days)).timestamp()
    os.utime(p, (t, t))
    return p


def test_the_place_is_in_the_repository_and_ignored_by_git():
    assert voice.VOICE_DIR == REPO / "nest_voice_data"
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "nest_voice_data/" in ignored


def test_store_names_the_file_by_the_transcript_hash(tmp_path):
    src = tmp_path / "upload.webm"
    src.write_bytes(b"audio")
    root = tmp_path / "voice"
    fake = Fake()
    digest = voice.store(src, TRANSCRIPT, ".webm", root, runner=fake)
    assert digest == _h(TRANSCRIPT)
    dest = root / (digest + ".webm")
    assert dest.read_bytes() == b"audio" and not src.exists()
    assert _mode(root) == 0o700 and _mode(dest) == 0o600
    assert ["tmutil", "addexclusion", str(root)] in fake.calls


def test_plan_picks_approved_and_expired_only(tmp_path):
    root = tmp_path / "voice"
    approved = _put(root, "承認された", 1)
    expired = _put(root, "古い", 31)
    edge = _put(root, "ちょうど30日", 30)
    fresh = _put(root, "新しい", 1, ".m4a")
    (root / "README.txt").write_text("人のメモ", encoding="utf-8")
    (root / ("x" * 64 + ".webm")).write_bytes(b"x")  # 16 進でない
    out = voice.plan(root, {_h("承認された")}, NOW)
    assert out == {"approved": [approved.name], "expired": [expired.name], "kept": sorted([edge.name, fresh.name])}


def test_files_lists_only_voice_names(tmp_path):
    root = tmp_path / "voice"
    a = _put(root, "a", 0)
    (root / (_h("b") + ".exe")).write_bytes(b"x")
    assert [p.name for p in voice.files(root)] == [a.name]
    assert voice.files(tmp_path / "none") == []


def test_purge_counts_without_write_and_deletes_with_write(tmp_path):
    root = tmp_path / "voice"
    a = _put(root, "承認された", 1)
    b = _put(root, "古い", 40)
    c = _put(root, "新しい", 1)
    asked = []

    def approved(hashes):
        asked.append(sorted(hashes))
        return {_h("承認された")}
    dry = voice.purge(root, approved, write=False, now=NOW)
    assert dry["write"] is False and dry["approved"] == [a.name] and dry["expired"] == [b.name]
    assert a.exists() and b.exists()
    assert asked == [sorted([_h("承認された"), _h("古い"), _h("新しい")])]
    done = voice.purge(root, approved, write=True, now=NOW)
    assert done["write"] is True and not a.exists() and not b.exists() and c.exists()


def test_purge_still_removes_expired_when_the_db_cannot_be_read(tmp_path):
    root = tmp_path / "voice"
    old = _put(root, "古い", 31)
    new = _put(root, "新しい", 1)

    def down(hashes):
        raise RuntimeError("（架空）つながらない")
    out = voice.purge(root, down, write=True, now=NOW)
    assert out["expired"] == [old.name] and out["approved"] == []
    assert any("DB" in e for e in out["errors"])
    assert not old.exists() and new.exists()


def test_approved_query_reads_active_records_by_hash():
    seen = {}

    class Tx:
        def run(self, query, **params):
            seen.update(query=query, params=params)
            return [{"h": "a" * 64}]

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute_read(self, work):
            return work(Tx())

    class Driver:
        def session(self, database):
            seen["database"] = database
            return Session()
    assert voice.approved_hashes(Driver(), {"a" * 64, "b" * 64}) == {"a" * 64}
    assert "Record" in seen["query"] and "documentHash" in seen["query"] and "'Active'" in seen["query"]
    assert sorted(seen["params"]["hashes"]) == ["a" * 64, "b" * 64]
    assert "DELETE" not in seen["query"].upper() and "SET" not in seen["query"].upper()
