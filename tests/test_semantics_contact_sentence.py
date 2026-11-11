"""接触の一文と語られた中身の記録の種類（2026-11-12 河原さんの承認。台帳 G-99）。DB を使わない。

- SEM-REC-04「面接記録の書き方」の一行目の後に一行：接触そのものを述べる一文は Observation、相手が語った中身は Interview。
  「聞き取った」と書いてあっても、聞いたという行為を述べるだけの一文は Observation
- 承認の範囲はその一行と、見出し・台帳の記載だけ
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "docs" / "SEMANTICS.md").read_text(encoding="utf-8")
LINE = ("- 接触そのものを述べる一文（「自宅を訪問。母と本人に会う。」「電話で聞き取った」など、記録者がしたこと・見たこと）は "
        "`kind: Observation`。相手が語った中身（「〜とのこと」「〜と話した」）は `kind: Interview`。"
        "「聞き取った」と書いてあっても、聞いたという行為を述べるだけの一文は `Observation`")


def _sec(head):
    i = TEXT.index("### " + head)
    return TEXT[i:TEXT.index("\n### ", i + 1)]


def test_rec_04_has_the_line_right_after_the_first_line_of_interview_records():
    s = _sec("SEM-REC-04")
    lines = s.split("面接記録の書き方\n", 1)[1].splitlines()
    assert lines[0].startswith("- 相談支援の面接 1 回")
    assert lines[1] == LINE


def test_the_line_appears_once_and_only_in_rec_04():
    assert TEXT.count(LINE) == 1


def test_the_heading_and_the_ledger_name_the_change():
    head = TEXT[TEXT.index("### SEM-REC-04"):].splitlines()[0]
    assert "2026-11-12" in head and "G-99" in head
    ledger = (ROOT / "docs" / "gray-decisions.md").read_text(encoding="utf-8")
    (row,) = [l for l in ledger.splitlines() if l.startswith("| G-99 |")]
    assert "SEM-REC-04" in row and "Observation" in row and "Interview" in row
