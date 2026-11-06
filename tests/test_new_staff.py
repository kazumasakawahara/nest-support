"""N-43：職員の登録の道具 scripts/new_staff.py（2026-11-06 河原さん）。DB を使わない部分。

- 依頼は職員（Staff）一人。人が入れたもの（origin Human）。役割は Staff か Administrator（既定は Staff）。ゲートの検査を通る
- 手順書（docs/OPERATIONS.md）に new_staff のコマンドがあり、作った後に staff_token へ続ける行がある
DB を使う確かめ（手順書のコマンドをそのまま流す）は tests/test_new_staff_live.py。
"""
import importlib.util
from pathlib import Path

import pytest

from nest.gate import validate as gv

REPO = Path(__file__).resolve().parents[1]
ADMIN = "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"
_spec = importlib.util.spec_from_file_location("doc_commands", REPO / "tests" / "doc_commands.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


def _script():
    return dc.load("new_staff.py")


@pytest.mark.parametrize("extra,role", [([], "Staff"), (["--role", "Administrator"], "Administrator")])
def test_request_is_one_staff_made_by_a_human(extra, role):
    m = _script()
    req = m.staff_request(m.parse(["--admin", ADMIN, "--name", "架空の職員", *extra]), "req-x")
    assert req["actorStaffId"] == ADMIN and req["relationships"] == []
    assert req["nodes"] == [{"ref": "s", "label": "Staff", "origin": "Human",
                             "properties": {"displayName": "架空の職員", "role": role}}]
    assert gv.validate(req)["ok"], gv.validate(req)["errors"]


@pytest.mark.parametrize("argv", [["--name", "x"], ["--admin", ADMIN], ["--admin", ADMIN, "--name", "x", "--role", "Approver"]])
def test_admin_name_are_required_and_role_is_closed(argv):
    with pytest.raises(SystemExit):
        _script().parse(argv)


def test_manual_has_the_command_and_the_next_step():
    assert dc.lines("new_staff.py"), "手順書に new_staff のコマンドが無い"
    text = dc.DOC.read_text(encoding="utf-8")
    i = text.index("scripts/new_staff.py")
    assert "scripts/staff_token.py add" in text[i:i + 1500]
