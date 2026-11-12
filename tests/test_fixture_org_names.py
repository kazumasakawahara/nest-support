"""fixture_kakuu_haruto.md に、関わりの機関の一往復を試す一文を足した（2026-11-11 河原さん）。DB を使わない。

- §3 は案 A：架空の正式な名前（候補 0 件 → 機関未確定のまま通る道）
- 記録 2 の電話は案 B：呼び名「つばさ」（候補が出て番号で選ぶ道）
- 選んだ実在の事業所の名前と機関 ID は、fixture・試験・journal・手順書に書かない。fixture に書くのは呼び名だけ
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEXT = (REPO / "fixture_kakuu_haruto.md").read_text(encoding="utf-8")


def _part(head, end):
    i = TEXT.index(head)
    return TEXT[i:TEXT.index(end, i + 1)] if end in TEXT[i + 1:] else TEXT[i:]


def test_section_3_names_a_made_up_office():
    assert "事業所（かくう生活介護センター）の生活支援員から電話で聞き取りました。" in _part("## 3.", "\n## 4.")


def test_record_2_names_the_office_only_by_its_nickname():
    rec = TEXT[TEXT.index("### 記録 2"):]
    assert "「つばさ」" in rec


def test_no_organization_id_is_written_in_the_files_that_must_not_name_it():
    for path in ("fixture_kakuu_haruto.md", "docs/OPERATIONS.md", "docs/journal/2026-11-11-stage-L-trial-fixes.md"):
        assert not re.search(r"ORG-[0-9A-Z]{20,}", (REPO / path).read_text(encoding="utf-8")), path
