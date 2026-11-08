"""N-39：本人を Claude の外で作る入口（scripts/new_client.py）。DB を使わない部分。

- 作る依頼は、本人（Client）と、住所があれば住まい（Residence、RESIDES_AT）。人が入れたもの（origin Human）。ゲートの検査を通る
- 実名・かな・生年月日・住所は DB に入れてよい（包みが返さないだけ）。仮名はゲートが発番する（依頼に書かない）
- 氏と名は要る
DB を使う確かめ（作る・引く・二重登録を止める）は tests/test_new_client_live.py。
"""
import importlib.util
from pathlib import Path

import pytest

from nest.gate import validate as gv

REPO = Path(__file__).resolve().parents[1]
STAFF = "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"


def _script():
    spec = importlib.util.spec_from_file_location("new_client", REPO / "scripts" / "new_client.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _args(*extra):
    return _script().parse(["add", "--staff", STAFF, "--family", "架空", "--given", "花子", *extra])


def test_request_with_an_address_has_client_residence_and_link():
    m = _script()
    req = m.client_request(_args("--family-kana", "カクウ", "--given-kana", "ハナコ", "--birth", "1990-04-01",
                                 "--address", "福岡県北九州市小倉北区架空町1-2-3", "--address-certainty", "Confirmed"),
                            "req-x")
    assert [n["label"] for n in req["nodes"]] == ["Client", "Residence"]
    assert all(n["origin"] == "Human" for n in req["nodes"])
    c = req["nodes"][0]["properties"]
    assert c == {"familyName": "架空", "givenName": "花子", "familyNameKana": "カクウ", "givenNameKana": "ハナコ",
                 "birthDate": "1990-04-01", "birthDatePrecision": "Day"}
    assert "displayCode" not in c
    assert req["nodes"][1]["properties"] == {"address": "福岡県北九州市小倉北区架空町1-2-3", "certainty": "Confirmed"}
    assert req["relationships"] == [{"type": "RESIDES_AT", "from": "c", "to": "r", "properties": {}}]
    assert req["actorStaffId"] == STAFF
    assert gv.validate(req)["ok"], gv.validate(req)["errors"]


def test_request_without_an_address_has_only_the_client():
    req = _script().client_request(_args(), "req-x")
    assert [n["label"] for n in req["nodes"]] == ["Client"] and req["relationships"] == []
    assert req["nodes"][0]["properties"] == {"familyName": "架空", "givenName": "花子"}
    assert gv.validate(req)["ok"], gv.validate(req)["errors"]


@pytest.mark.parametrize("drop", ["--family", "--given", "--staff"])
def test_family_given_and_staff_are_required(drop):
    argv = ["add", "--staff", STAFF, "--family", "架空", "--given", "花子"]
    i = argv.index(drop)
    del argv[i:i + 2]
    with pytest.raises(SystemExit):
        _script().parse(argv)


def test_the_mcp_wrappers_do_not_use_this_tool():
    """名前を受け取る道具は Claude の側（MCP の包み）に置かない（台帳 G-42 (2)）"""
    for name in ("mcp_personal.py", "mcp_resource.py", "mcp_guard.py"):
        assert "new_client" not in (REPO / "nest" / name).read_text(encoding="utf-8")


# N-46 詰まり #4（2026-11-08 河原さん。台帳 G-93）：住まいの確度は決め打ちせず、住所を入れるなら必ず指定する。作った後は変えられない

@pytest.mark.parametrize("value", ["Confirmed", "SelfReport", "Hearsay", "Inference", "Unspecified"])
def test_residence_certainty_is_what_the_staff_chose(value):
    req = _script().client_request(_args("--address", "福岡県北九州市小倉北区架空町1-2-3", "--address-certainty", value),
                                   "req-x")
    assert req["nodes"][1]["properties"]["certainty"] == value
    assert gv.validate(req)["ok"], gv.validate(req)["errors"]


@pytest.mark.parametrize("extra", [["--address", "福岡県北九州市小倉北区架空町1-2-3"],
                                   ["--address-certainty", "Confirmed"],
                                   ["--address", "福岡県北九州市小倉北区架空町1-2-3", "--address-certainty", "Maybe"]])
def test_address_and_certainty_go_together_and_certainty_is_from_the_canon(extra):
    with pytest.raises(SystemExit):
        _args(*extra)
