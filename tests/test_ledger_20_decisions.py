"""台帳の承認欄が空だった 20 件への河原さんの判断（2026-11-06）のうち、コードの直しが要るもの。DB を使わない。

- G-49：前の DB を指す、ゲートを通らない書き込みの 4 本を git から外す
- G-52 (1)：displayCode は「C- ＋ 乱数 6 字」。紛れやすい字（0・O・1・I・l）を除いた集合。名前・生年月日から導かない。一意制約
- G-52 (7)：根拠の記録（EVIDENCED_BY → Record）が一つも無い新しい禁忌は止める（D5）
- G-61：jp-normalize は使わない。正規化は NFKC と空白だけを自前で持つ
"""
import re
import subprocess
from pathlib import Path

import pytest

from nest import canon
from nest.gate import validate as gv
from nest.gate import write as gw

REPO = Path(__file__).resolve().parents[1]
C = canon.load(REPO / "docs" / "SCHEMA.md")
SCHEMA_TEXT = (REPO / "docs" / "SCHEMA.md").read_text(encoding="utf-8")


def _tracked():
    return subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split()


# ---- G-49 ----
OLD_DB_WRITERS = ["scripts/migrate_carerole_per_client.py", "scripts/migrate_condition_status_case.py",
                  "scripts/migrate_hospital_doctor_to_node.py", "scripts/examples/phase2-poc/01_register.py"]


@pytest.mark.parametrize("path", OLD_DB_WRITERS)
def test_old_db_writers_are_out_of_git(path):
    assert path not in _tracked()
    assert not (REPO / path).exists()


# ---- G-52 (1) ----
def test_display_code_shape_and_alphabet():
    codes = {gw.new_display_code() for _ in range(2000)}
    assert len(codes) == 2000
    for code in codes:
        assert re.fullmatch(r"C-[2-9A-HJKMNP-TV-Z]{6}", code), code
        assert not set(code[2:]) & set("0O1Il"), code


def test_display_code_is_not_derived_from_inputs():
    import inspect
    assert inspect.signature(gw.new_display_code).parameters == {}


def test_display_code_form_and_constraint_are_in_the_canon():
    row = next(l for l in SCHEMA_TEXT.splitlines() if l.startswith("| 表示用の仮名"))
    assert "C-" in row and "6" in row and "0・O・1・I・l" in row and "形は N-10 で決める" not in row
    assert "displayCode" in C["personal"]["nodes"]["Client"]["unique"]


# ---- G-52 (7) ----
STAFF = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
NG = {"ref": "ng", "label": "NgAction", "origin": "Human",
      "properties": {"action": "大きな音を立てる（架空）", "riskLevel": "Panic"}}
REC = {"ref": "rec", "label": "Record", "origin": "Human",
       "properties": {"kind": "Observation", "text": "職員が見た（架空）", "quote": "職員が見た（架空）",
                      "certainty": "Confirmed", "informantKind": "Agency"}}


def _req(nodes, rels):
    return {"requestId": "req-ng", "actorStaffId": STAFF, "nodes": nodes, "relationships": rels}


def test_new_ngaction_without_evidence_is_refused():
    rep = gv.validate(_req([NG], []))
    assert not rep["ok"] and any("禁忌" in e and "根拠" in e for e in rep["errors"]), rep["errors"]


def test_new_ngaction_with_a_new_record_passes():
    rep = gv.validate(_req([NG, REC], [{"type": "EVIDENCED_BY", "from": "ng", "to": "rec"}]))
    assert not any("禁忌" in e and "根拠" in e for e in rep["errors"]), rep["errors"]


def test_new_ngaction_with_an_existing_record_passes():
    rep = gv.validate(_req([NG], [{"type": "EVIDENCED_BY", "from": "ng",
                                   "to": {"label": "Record", "id": "REC-01HZZZZZZZZZZZZZZZZZZZZZZZ"}}]))
    assert not any("禁忌" in e and "根拠" in e for e in rep["errors"]), rep["errors"]


# ---- G-61 ----
def test_jp_normalize_is_not_a_dependency():
    assert "jp-normalize" not in (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert "jp-normalize" not in (REPO / "uv.lock").read_text(encoding="utf-8")
    for path in _tracked():
        if path.endswith(".py") and (path.startswith("nest/") or path.startswith("tests/")):
            text = (REPO / path).read_text(encoding="utf-8")
            assert not re.search(r"^\s*(import|from)\s+jp_normalize", text, re.M), path
