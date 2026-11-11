"""確認点 L-0：正典 v0.13（2026-11-10 河原さん。決めごと 1〜13）。DB を使わない。

- SupportLog に任意の項目 contactKind（列挙 contactKind。nest-support だけ。6 値。「その他」は作らない）を足す（決めごと 2）
- ラベル・関係・必須の項目・共有の列挙値（informantKind など）は変えない。機械検証ブロックの version は 0.5 のまま（決めごと 13）
- SEMANTICS に SEM-REC-04（面接記録の書き方・見立ての書き方・新しい人の根拠）と contactKind の表示名を足す
"""
from pathlib import Path

from nest import canon, semantics

REPO = Path(__file__).resolve().parents[1]
C = canon.load(REPO / "docs" / "SCHEMA.md")
TEXT = (REPO / "docs" / "SCHEMA.md").read_text(encoding="utf-8")
SEM = (REPO / "docs" / "SEMANTICS.md").read_text(encoding="utf-8")
SIX = ["Visit", "OfficeVisit", "Phone", "Accompaniment", "Meeting", "Correspondence"]


def _sem_rec_04():
    start = SEM.index("### SEM-REC-04")
    end = SEM.find("\n#", start + 1)
    return SEM[start:end]


def test_support_log_has_an_optional_contact_kind_and_the_required_items_are_unchanged():
    s = C["personal"]["nodes"]["SupportLog"]
    assert "contactKind" in s["optional"] and "contactKind" not in s["required"]
    assert s["required"] == ["supportLogId", "date", "situation"]


def test_contact_kind_has_the_six_values_and_no_other():
    assert C["enums"]["contactKind"] == SIX
    assert "Other" not in C["enums"]["contactKind"]
    assert C["enumBindings"]["SupportLog.contactKind"] == "contactKind"


def test_shared_enums_and_the_machine_block_version_are_unchanged():
    assert C["enums"]["informantKind"] == ["Self", "Family", "Agency", "Neighbor", "DocumentOnly"]
    assert C["version"] == "0.5"


def test_the_tables_and_history_say_v0_13():
    assert TEXT.startswith("# nest-support スキーマ正典 — v0.1")  # 2026-11-12 に v0.14（台帳 G-102）。v0.13 の記載は履歴に残る
    assert "- v0.13（2026-11-10）" in TEXT
    row = next(l for l in TEXT.splitlines() if l.startswith("| `SupportLog` |"))
    assert "`contactKind`(enum)" in row
    enum_row = next(l for l in TEXT.splitlines() if l.startswith("| `contactKind`"))
    assert "nest-support だけ" in enum_row and all("`%s`" % v in enum_row for v in SIX)


def test_contact_kind_has_japanese_names():
    assert semantics.enum_names()["contactKind"] == {
        "Visit": "訪問", "OfficeVisit": "来所", "Phone": "電話", "Accompaniment": "同行", "Meeting": "会議",
        "Correspondence": "文書・メール・FAX 等のやり取り"}


def test_sem_rec_04_says_how_to_write_an_interview_record():
    sec = _sem_rec_04()
    for words in ("面接 1 回", "`SupportLog` 1 件", "`Record` に分ける", "`situation`", "役割の名前", "`nextAction`",
                  "`effectiveness`", "行動支援の記録だけ"):
        assert words in sec, words


def test_sem_rec_04_says_how_to_write_the_recorders_own_view():
    sec = _sem_rec_04()
    for words in ("見立て", "`Inference`", "もとになった", "`AUTHORED_BY`", "`TOLD_BY` は張らない",
                  "`PROVIDED_BY` の無い `Agency`", "記録者の観察", "禁忌", "推奨ケア"):
        assert words in sec, words


def test_sem_rec_04_says_a_new_person_needs_a_tie():
    sec = _sem_rec_04()
    assert "新しい人" in sec and "`TOLD_BY`" in sec and "`CONCERNS`" in sec and "`RELATED_TO`" in sec
