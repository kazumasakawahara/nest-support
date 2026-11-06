"""N-40：運用の手順書 docs/OPERATIONS.md（2026-11-06 河原さん）。

- 職員が上から順に読んで動かせる一本の手順。決めた段がそろっている
- 段ごとに doctor のどの項目で点検できるかを書く（「点検」の列）。点検できない段は「人が確かめる」
- 書いた doctor の項目（[n]）は scripts/doctor.sh に実在する。書いた scripts/… の道具は実在する
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "OPERATIONS.md"
STEPS = ["bootstrap_admin", "staff_token", "new_client", "field-ui", "purge_voice", "backup", "purge_client", "doctor"]


def _text():
    return DOC.read_text(encoding="utf-8")


def _table():
    """「段と点検の対応」の表の行（段・点検）"""
    t = _text()
    i = t.index("## 段と点検の対応")
    j = t.find("\n## ", i + 3)
    rows = [line for line in t[i:j if j > 0 else len(t)].splitlines() if line.startswith("|")]
    out = []
    for line in rows[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        out.append((cells[0], cells[-1]))
    return out


def _doctor_items():
    return set(re.findall(r'echo "\[(\d+)\]', (REPO / "scripts" / "doctor.sh").read_text(encoding="utf-8")))


@pytest.mark.parametrize("step", STEPS)
def test_each_step_has_a_section_and_a_row(step):
    t = _text()
    assert re.search(r"^## \d+\..*" + re.escape(step), t, re.M), step
    assert any(step in s for s, _ in _table()), step


def test_steps_are_in_order():
    t = _text()
    heads = [line for line in t.splitlines() if re.match(r"^## \d+\.", line)]
    found = [next(i for i, h in enumerate(heads) if s in h) for s in STEPS]
    assert found == sorted(found)


def test_every_row_names_a_doctor_item_or_a_person():
    for step, check in _table():
        items = re.findall(r"\[(\d+)\]", check)
        assert items or "人が確かめる" in check, (step, check)


def test_named_doctor_items_exist():
    have = _doctor_items()
    named = {n for _, check in _table() for n in re.findall(r"\[(\d+)\]", check)}
    assert named and named <= have, named - have


def test_named_scripts_exist():
    names = set(re.findall(r"scripts/([\w.]+\.(?:py|sh))", _text()))
    assert names
    assert [n for n in names if not (REPO / "scripts" / n).exists()] == []


def test_real_data_limits_are_stated():
    """実データを Claude に渡さないこと（G-80）と、画面が読む条件（NEXT-02 か架空の印）を書く"""
    t = _text()
    assert "G-80" in t and "NestLiveProbe" in t


def _section_of(head):
    t = _text()
    i = t.index(head)
    j = t.find("\n## ", i + 3)
    return t[i:j if j > 0 else len(t)]


def test_real_db_blocks_records_and_voice_too():
    """最終レビュー：画面が止まるのは本人の一覧だけでなく、記録の入力（/record）と録音（/voice）も"""
    limits = _section_of("**先に読むこと")
    assert "/record" in limits and "/voice" in limits


def test_marker_must_not_be_put_on_a_real_db():
    """最終レビュー：架空の印を実データの DB に置けば G-80 の歯止めが外れる。置かないと書く"""
    assert "実データの DB に架空の印（`NestLiveProbe`）を置かない" in _text()


def test_voice_is_not_kept_while_transcription_is_off():
    """最終レビュー：文字起こしが止まっている間、録音は保存されない（field-ui/server.py は文字起こしの後にだけ置く）"""
    assert "録音は残りません" in _section_of("## 6.")


def test_sos_signs_in_with_the_shared_token_and_http_needs_insecure_cookie():
    """最終レビュー：SOS は職員のトークンでなく APP_ACCESS_TOKEN。127.0.0.1 の http では SESSION_COOKIE_SECURE=false が要る"""
    s5 = _section_of("## 5.")
    assert "APP_ACCESS_TOKEN" in s5
    assert "試すときだけ" not in s5
