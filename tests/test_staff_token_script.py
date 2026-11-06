"""N-37：職員のトークンの表を作る道具（scripts/staff_token.py）。本物の表は使わない（--table で一時の場所）。

- add：職員 ID に新しいトークンを作り、表には sha256 だけを書く。トークンは一度だけ画面に出す。表は権限 600
- 同じ職員に add し直すと、前のトークンは使えなくなる（作り直し）
- remove：その職員の行を消す。list：職員 ID だけを出す（ハッシュは出さない）
- 職員 ID の形でなければ止める
"""
import importlib.util
import json
import os
import stat
from pathlib import Path

import pytest

import nest.auth as auth

REPO = Path(__file__).resolve().parents[1]
STAFF = "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"


def _script():
    spec = importlib.util.spec_from_file_location("staff_token", REPO / "scripts" / "staff_token.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _token(out):
    return [line for line in out.splitlines() if line.startswith("トークン：")][0].split("：", 1)[1]


def test_add_writes_only_a_hash_and_prints_the_token_once(tmp_path, capsys, monkeypatch):
    table = tmp_path / "nest" / "field-ui-staff.json"
    assert _script().main(["add", STAFF, "--table", str(table)]) == 0
    token = _token(capsys.readouterr().out)
    assert stat.S_IMODE(os.stat(table).st_mode) == 0o600
    data = json.loads(table.read_text(encoding="utf-8"))
    assert data == {"version": 1, "staff": {STAFF: auth.token_hash(token)}}
    assert token not in table.read_text(encoding="utf-8")
    monkeypatch.setattr(auth, "staff_tokens_path", lambda: table)
    assert auth.staff_of(token) == STAFF


def test_add_again_replaces_the_token(tmp_path, capsys, monkeypatch):
    table = tmp_path / "t.json"
    s = _script()
    s.main(["add", STAFF, "--table", str(table)])
    first = _token(capsys.readouterr().out)
    s.main(["add", STAFF, "--table", str(table)])
    second = _token(capsys.readouterr().out)
    monkeypatch.setattr(auth, "staff_tokens_path", lambda: table)
    assert first != second and auth.staff_of(first) is None and auth.staff_of(second) == STAFF


def test_remove_and_list(tmp_path, capsys):
    table = tmp_path / "t.json"
    s = _script()
    other = "STF-01BBBBBBBBBBBBBBBBBBBBBBBB"
    s.main(["add", STAFF, "--table", str(table)])
    s.main(["add", other, "--table", str(table)])
    capsys.readouterr()
    assert s.main(["remove", STAFF, "--table", str(table)]) == 0
    capsys.readouterr()
    s.main(["list", "--table", str(table)])
    out = capsys.readouterr().out
    assert out.split() == [other]  # 職員 ID だけ（ハッシュは出さない）


def test_a_non_staff_id_is_refused(tmp_path, capsys):
    table = tmp_path / "t.json"
    assert _script().main(["add", "山田", "--table", str(table)]) == 1
    assert not table.exists()
