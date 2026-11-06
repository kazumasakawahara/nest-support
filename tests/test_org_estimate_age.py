"""担当機関の推定の候補の種類（2026-11-05 河原さんの決定。台帳 G-57）。DB を使わない。

- いつも候補にする 7 つ。CareInsuranceDivision は外す
- 本人の年齢で足す：65 歳以上は ElderlyDivision・CommunityGeneralSupportCenter、18 歳未満は ChildFamilyCenter
  （区切りは介護保険法 9 条 1 号・児童福祉法 4 条 1 項。年齢は言及の時期で数える。年齢の数え方は民法 143 条の準用で、誕生日の前日に達する）
- 生年月日の記録が無い・年や年月だけで区切りの前後が決まらないときは両方を出し、その旨を添える。AI は使わない
- 成年後見センターを選んだ関わりは Consultation だけ
"""
import datetime as dt
from pathlib import Path

import pytest

from nest import org_estimate as oe
from nest.gate import intake

ALWAYS = {"DisabilityDivision", "HardshipSupportDesk", "WelfareOffice", "BasicConsultationCenter", "MentalHealthDesk",
          "SocialWelfareCouncil", "GuardianshipCenter"}
OLD = {"ElderlyDivision", "CommunityGeneralSupportCenter"}
CHILD = {"ChildFamilyCenter"}
D = dt.date


def test_always_kinds_and_the_maximum():
    assert set(oe.ALWAYS_KINDS) == ALWAYS and len(oe.ALWAYS_KINDS) == 7
    assert "CareInsuranceDivision" not in oe.CONSULTATION_KINDS
    assert set(oe.CONSULTATION_KINDS) == ALWAYS | OLD | CHILD and len(oe.CONSULTATION_KINDS) == 10


@pytest.mark.parametrize("birth, on, extra", [
    ("1950-06-15", D(2025, 6, 15), OLD),
    ("1960-06-15", D(2025, 6, 14), OLD),         # 65 歳の誕生日の前日に 65 歳に達する
    ("1960-06-15", D(2025, 6, 13), set()),
    ("1990-01-01", D(2025, 1, 1), set()),
    ("2010-04-02", D(2028, 4, 1), set()),         # 18 歳に達した日
    ("2010-04-02", D(2028, 3, 31), CHILD),
    ("2020-01-01", D(2025, 1, 1), CHILD),
    ("1960-02-29", D(2025, 2, 28), OLD),           # うるう日生まれ：応当日が無い年は 3 月 1 日の前日
    ("1960-02-29", D(2025, 2, 27), set()),
])
def test_exact_birth_date(birth, on, extra):
    kinds, notes = oe.kinds_for(birth, "Day", on)
    assert set(kinds) == ALWAYS | extra and notes == []


def test_missing_precision_is_read_as_a_full_date():
    kinds, notes = oe.kinds_for("1950-06-15", None, D(2025, 1, 1))
    assert set(kinds) == ALWAYS | OLD and notes == []


@pytest.mark.parametrize("birth, precision", [(None, None), (None, "Day"), ("1960-01-01", "Unknown")])
def test_no_birth_record_gives_both_with_a_note(birth, precision):
    kinds, notes = oe.kinds_for(birth, precision, D(2025, 1, 1))
    assert set(kinds) == ALWAYS | OLD | CHILD
    assert any("年齢の記録なし" in n for n in notes)


@pytest.mark.parametrize("birth, precision, on, extra, word", [
    ("1960-01-01", "Year", D(2025, 6, 1), OLD, "65"),        # 1960 年生まれ：2025-06 には 64 か 65
    ("1960-01-01", "Year", D(2026, 1, 1), OLD, None),         # 遅くとも 1960-12-31 生まれ → 2025-12-30 に 65
    ("1961-01-01", "Year", D(2025, 6, 1), set(), None),
    ("2007-01-01", "Year", D(2025, 6, 1), CHILD, "18"),       # 17 か 18
    ("2007-06-01", "Month", D(2025, 6, 15), CHILD, "18"),     # 2007 年 6 月生まれ：6 月 15 日には 17 か 18
    ("2007-06-01", "Month", D(2025, 7, 1), set(), None),
    ("1960-06-01", "Month", D(2025, 5, 30), set(), None),
    ("1960-06-01", "Month", D(2025, 6, 10), OLD, "65"),
])
def test_partial_birth_date_gives_both_sides_when_undecided(birth, precision, on, extra, word):
    kinds, notes = oe.kinds_for(birth, precision, on)
    assert set(kinds) == ALWAYS | extra
    if word:
        assert any(word in n and "決まらない" in n for n in notes)
    else:
        assert notes == []


class _Personal:
    def __init__(self, residences, birth=None, precision=None):
        self.residences, self.birth, self.precision = residences, birth, precision

    def execute_query(self, query, parameters=None, **kw):
        class R:
            def __init__(self, rows):
                self.records = rows
        if "birthDate" in query:
            return R([{"birthDate": self.birth, "birthDatePrecision": self.precision}])
        return R([dict(r) for r in self.residences])


NOW = {"areaCode": "401064", "since": "2023-04-01", "until": None}


def test_estimate_uses_the_age_at_the_time_of_the_mention_and_never_returns_the_birth_date(monkeypatch):
    seen = {}

    def fake_by_area(driver, code, kinds=oe.ALWAYS_KINDS, limit=30):
        seen["kinds"] = set(kinds)
        return {"candidates": [], "truncated": False}
    monkeypatch.setattr(oe, "by_area", fake_by_area)
    est = oe.estimate(_Personal([NOW], "2008-05-01", "Day"), object(), "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ", "2024-06-01")
    assert seen["kinds"] == ALWAYS | CHILD                       # 2024-06 には 16 歳
    assert "2008" not in repr(est) and "birthDate" not in repr(est)
    est = oe.estimate(_Personal([NOW], None, None), object(), "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ", "2024-06-01")
    assert seen["kinds"] == ALWAYS | OLD | CHILD and any("年齢の記録なし" in n for n in est["notes"])


def test_estimate_without_a_date_uses_today(monkeypatch):
    seen = {}
    monkeypatch.setattr(oe, "by_area", lambda d, c, kinds=oe.ALWAYS_KINDS, limit=30: seen.update(k=set(kinds)) or
                        {"candidates": [], "truncated": False})
    oe.estimate(_Personal([NOW], "1950-01-01", "Day"), object(), "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ", None, today=D(2026, 11, 5))
    assert seen["k"] == ALWAYS | OLD


# ---- 成年後見センターを選んだ関わりは Consultation だけ ----

OWN = (Path(__file__).resolve().parent / "fixtures" / "intake" / "own_record_desk.md").read_text(encoding="utf-8")
QUOTE = "母の話では、去年の春に区役所の相談コーナーで、本人の通所のことを相談した"
GC = "ORG-01GGGGGGGGGGGGGGGGGGGGGGGG"


@pytest.mark.parametrize("kind, ok", [("Consultation", True), ("CaseManagement", False), ("Administrative", False)])
def test_guardianship_center_only_as_consultation(kind, ok):
    est = {"basis": "AtTheTime", "notes": [], "window": None, "chosen": None, "truncated": False,
           "candidates": [{"orgId": GC, "name": "架空成年後見センター", "kind": "GuardianshipCenter", "servesBasis": "Designated",
                           "partOfArea": False, "viaParent": False}]}
    p = {"documentKind": "OwnCaseRecord", "clientId": "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ",
         "facts": [{"quote": QUOTE, "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family"}],
         "involvements": [{"quote": QUOTE, "kind": kind, "orgId": GC}]}
    rep = intake.check(p, OWN, actor_staff_id="STF-01HZZZZZZZZZZZZZZZZZZZZZZZ", request_id="req-gc", estimate=est)
    assert rep["ok"] is ok, rep["errors"]
    if not ok:
        assert any("成年後見センター" in e for e in rep["errors"])


# ---- 年齢の数え方：河原さんの jp-normalize の age_at(..., legal=True) と同じ答え（2026-11-05 河原さん） ----

def test_born_on_april_1st_reaches_18_on_march_31st():
    assert oe._reached(18, D(2008, 4, 1), D(2026, 3, 31))
    assert not oe._reached(18, D(2008, 4, 1), D(2026, 3, 30))
    assert set(oe.kinds_for("2008-04-01", "Day", D(2026, 3, 31))[0]) == ALWAYS
    assert set(oe.kinds_for("2008-04-01", "Day", D(2026, 3, 30))[0]) == ALWAYS | CHILD


def test_born_on_february_29th_ages_on_february_28th_in_a_common_year():
    assert oe._reached(18, D(2008, 2, 29), D(2026, 2, 28))
    assert not oe._reached(18, D(2008, 2, 29), D(2026, 2, 27))
    assert oe._reached(16, D(2008, 2, 29), D(2024, 2, 28))      # うるう年は 2 月 28 日（29 日の前日）
    assert not oe._reached(16, D(2008, 2, 29), D(2024, 2, 27))
