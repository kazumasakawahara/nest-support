"""N-44：書き込みの案の点検と承認の道具 scripts/review_proposals.py（2026-11-06 河原さん）。DB を使わない部分。

- list・show・approve・reject の四つ。承認と差し戻しは一つずつ（--id は一つ）。まとめての承認（approve_many）は使わない
- ID の形から種類（ラベル）を決める。知らない ID は DB に触れる前に止める
- 手順書（docs/OPERATIONS.md）に四つのコマンドがある
DB を使う確かめ（手順書のコマンドをそのまま流す）は tests/test_review_proposals_live.py。
"""
import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
STAFF = "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"
REC = "REC-01AAAAAAAAAAAAAAAAAAAAAAAA"
_spec = importlib.util.spec_from_file_location("doc_commands", REPO / "tests" / "doc_commands.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


def _script():
    return dc.load("review_proposals.py")


def test_label_comes_from_the_id():
    m = _script()
    assert m.label_of(REC) == "Record" and m.label_of("NGA-01AAAAAAAAAAAAAAAAAAAAAAAA") == "NgAction"
    assert m.label_of("STF-01AAAAAAAAAAAAAAAAAAAAAAAA") is None  # 職員は承認の対象にならない
    assert m.label_of("XYZ-1") is None


@pytest.mark.parametrize("cmd", [["approve", "--id", "XYZ-1", "--staff", STAFF], ["reject", "--id", "XYZ-1", "--staff", STAFF],
                                 ["show", "--id", "XYZ-1"]])
def test_unknown_id_stops_before_the_db(cmd, capsys):
    class NoDB:
        def __getattr__(self, name):
            raise AssertionError("DB に触れた")
    assert _script().main(cmd, driver=NoDB()) == 1
    assert "止めた" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [["approve", "--id", REC], ["reject", "--id", REC], ["approve", "--staff", STAFF], ["show"]])
def test_required_arguments(argv):
    with pytest.raises(SystemExit):
        _script().parse(argv)


def test_one_at_a_time():
    src = (REPO / "scripts" / "review_proposals.py").read_text(encoding="utf-8")
    assert "approve_many" not in src


def test_manual_has_the_four_commands():
    got = " ".join(dc.lines("review_proposals.py"))
    for sub in ("review_proposals.py list", "review_proposals.py show", "review_proposals.py approve", "review_proposals.py reject"):
        assert sub in got, sub
