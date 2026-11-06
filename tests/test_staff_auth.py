"""N-37：field-ui の職員ごとのトークン（2026-11-06 河原さん：職員ごとのトークンで、ゲートに渡す職員 ID を決める）。

- 表は ~/.config/nest/field-ui-staff.json（権限 600。リンクは読まない）。中身は職員 ID とトークンの sha256 だけ。トークンそのものは置かない
- ログインに使ったトークンから職員 ID を決める。名義は自己申告にならない
- 表が無い・壊れている・権限が 600 でない → 503（fail-closed）。どの職員にも合わない → 401
DB も本物の表も使わない。
"""
import hashlib
import json
import os

import pytest

pytest.importorskip("fastapi")
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

import nest.auth as auth

TOKEN_A = "fictional-token-a"  # 架空
TOKEN_B = "fictional-token-b"  # 架空


def _h(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


@pytest.fixture
def table(tmp_path, monkeypatch):
    p = tmp_path / "field-ui-staff.json"
    p.write_text(json.dumps({"version": 1, "staff": {"STF-01AAAAAAAAAAAAAAAAAAAAAAAA": _h(TOKEN_A), "STF-01BBBBBBBBBBBBBBBBBBBBBBBB": _h(TOKEN_B)}}),
                 encoding="utf-8")
    os.chmod(p, 0o600)
    monkeypatch.setattr(auth, "staff_tokens_path", lambda: p)
    return p


def _app():
    app = FastAPI()

    @app.get("/who")
    def who(staff: str = Depends(auth.require_staff)):
        return {"staff": staff}
    return TestClient(app)


def test_the_token_decides_the_staff(table):
    assert auth.staff_of(TOKEN_A) == "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"
    assert auth.staff_of(TOKEN_B) == "STF-01BBBBBBBBBBBBBBBBBBBBBBBB"
    assert auth.staff_of("wrong") is None
    assert auth.staff_of("") is None


def test_require_staff_uses_header_or_cookie(table):
    c = _app()
    assert c.get("/who", headers={"Authorization": "Bearer " + TOKEN_B}).json() == {"staff": "STF-01BBBBBBBBBBBBBBBBBBBBBBBB"}
    c.cookies.set(auth.SESSION_COOKIE, TOKEN_A)
    assert c.get("/who").json() == {"staff": "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"}


def test_unknown_token_is_401(table):
    assert _app().get("/who", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_proxy_header_does_not_choose_the_staff(table, monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    r = _app().get("/who", headers={"Authorization": "Bearer " + TOKEN_A, "X-Authenticated-User": "STF-01BBBBBBBBBBBBBBBBBBBBBBBB"})
    assert r.json() == {"staff": "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"}


@pytest.mark.parametrize("problem", ["missing", "mode", "broken", "badid", "link"])
def test_a_bad_table_is_503(table, tmp_path, monkeypatch, problem):
    if problem == "missing":
        table.unlink()
    elif problem == "mode":
        os.chmod(table, 0o644)
    elif problem == "broken":
        table.write_text("{", encoding="utf-8")
    elif problem == "badid":
        table.write_text(json.dumps({"version": 1, "staff": {"山田": _h(TOKEN_A)}}), encoding="utf-8")
    else:
        link = tmp_path / "link.json"
        link.symlink_to(table)
        monkeypatch.setattr(auth, "staff_tokens_path", lambda: link)
    r = _app().get("/who", headers={"Authorization": "Bearer " + TOKEN_A})
    assert r.status_code == 503
    with pytest.raises(auth.StaffTableError):
        auth.staff_of(TOKEN_A)


def test_the_default_table_lives_with_the_nest_config():
    from pathlib import Path
    assert auth.DEFAULT_STAFF_TOKENS == Path.home() / ".config" / "nest" / "field-ui-staff.json"
