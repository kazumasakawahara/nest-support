"""N-24a：担当機関の推定（DB を使わない部分）。

- 住所から 6 桁の団体コードを、同梱した総務省の表（tsunagu-net の docs/reference から写した。指紋つき）と
  市区町村名の文字列の一致で出す。外に送らない。一致しなければ空
- ゲートは Residence の登録のとき areaCode を住所から出す。依頼の areaCode が住所と食い違えば止める
- 推定に使う住所：過去の言及は当時の住所。当時の住所が無ければ今の住所で推定し、その旨を書く。区が分からなければ機関未確定
- Claude に渡すのは候補の orgId と名前だけ（区コード・住所・種類・根拠を渡さない）
- 窓口（Window）までは絞らない。機関の単位で止める
住所はすべて架空（町名・番地は実在しない形）。
"""
import hashlib
import json
from pathlib import Path

import pytest

from nest import area_code, org_estimate as oe

REPO = Path(__file__).resolve().parents[1]
TABLE = REPO / "nest" / "data" / "area-codes-kitakyushu-2026-10-25.json"


# ---- 表 ----

def test_table_is_the_copy_with_the_recorded_fingerprint():
    assert hashlib.sha256(TABLE.read_bytes()).hexdigest() == area_code.TABLE_SHA256
    assert area_code.TABLE_SHA256.startswith("a7700fd4")
    src = json.loads(TABLE.read_text(encoding="utf-8"))["source"]
    assert "総務省" in src and "令和6年1月1日" in src


def test_provenance_is_written_in_semantics():
    text = (REPO / "docs" / "SEMANTICS.md").read_text(encoding="utf-8")
    assert area_code.TABLE_SHA256 in text and "令和6年1月1日" in text and "tsunagu-net" in text


# ---- 住所 → 団体コード ----

@pytest.mark.parametrize("address, code", [
    ("福岡県北九州市小倉北区架空町1-2-3", "401064"),
    ("北九州市小倉北区架空町1-2-3", "401064"),
    ("福岡県　北九州市 八幡西区 架空台４丁目", "401099"),
    ("北九州市架空町1", "401005"),          # 区が無ければ市
    ("福岡県遠賀郡芦屋町架空1-1", "403814"),
    ("芦屋町架空1-1", "403814"),
    ("福岡県行橋市架空2", "402133"),
])
def test_address_gives_the_code_by_name(address, code):
    assert area_code.from_address(address) == code


@pytest.mark.parametrize("address", [
    "小倉北区架空町1-2-3",               # 市の名前が無い（推測で足さない）
    "東京都千代田区架空1",                # 表に無い
    "架空市架空町1",
    "架空町北九州市小倉北区",             # 先頭で一致しない
    "",
    None,
])
def test_address_without_a_match_gives_empty(address):
    assert area_code.from_address(address) == ""


def test_area_code_does_not_reach_outside():
    src = (REPO / "nest" / "area_code.py").read_text(encoding="utf-8")
    for word in ("http", "requests", "urllib", "socket", "geocod"):
        assert word not in src


# ---- 推定に使う住所 ----

NOW = {"areaCode": "401064", "since": "2023-04-01", "until": None}
OLD = {"areaCode": "401099", "since": "2015-04-01", "until": "2023-04-01"}


def test_past_mention_uses_the_address_at_that_time():
    r = oe.residence_for([NOW, OLD], "2020-06-01")
    assert r["areaCode"] == "401099" and r["basis"] == "AtTheTime" and r["notes"] == []


def test_recent_mention_uses_the_current_address_as_at_that_time():
    r = oe.residence_for([NOW, OLD], "2024-01-10")
    assert r["areaCode"] == "401064" and r["basis"] == "AtTheTime"


def test_past_mention_without_the_old_address_falls_back_with_a_note():
    r = oe.residence_for([NOW], "2019-01-01")
    assert r["areaCode"] == "401064" and r["basis"] == "CurrentFallback"
    assert any("今の住所で推定" in n for n in r["notes"])


def test_mention_without_a_date_uses_the_current_address_with_a_note():
    r = oe.residence_for([NOW, OLD], None)
    assert r["areaCode"] == "401064" and r["basis"] == "CurrentFallback" and r["notes"]


@pytest.mark.parametrize("residences", [
    [],
    [{"areaCode": "", "since": "2023-04-01", "until": None}],
    [{"areaCode": None, "since": None, "until": None}],
    [NOW, {"areaCode": "401099", "since": "2024-01-01", "until": None}],  # 今の住所が二つ
])
def test_unknown_area_leaves_the_organization_undecided(residences):
    r = oe.residence_for(residences, "2024-06-01")
    assert r["areaCode"] is None and r["basis"] is None and r["notes"]


# ---- 推定の結果（Claude に渡すもの） ----

class _Personal:
    def __init__(self, residences):
        self.residences = residences

    def execute_query(self, query, parameters=None, **kw):
        class R:
            def __init__(self, rows):
                self.records = rows
        return R([dict(r) for r in self.residences])


CANDS = [{"orgId": "ORG-01AAAAAAAAAAAAAAAAAAAAAAAA", "name": "架空区高齢者・障害者相談コーナー", "kind": "DisabilityDivision",
          "servesBasis": "PresumedByLocation", "partOfArea": False, "viaParent": False}]


def test_estimate_carries_no_area_code_or_address(monkeypatch):
    seen = {}

    def fake_by_area(driver, code, limit=30):
        seen["code"] = code
        return {"candidates": CANDS, "truncated": False}
    monkeypatch.setattr(oe, "by_area", fake_by_area)
    est = oe.estimate(_Personal([NOW]), object(), "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ", "2024-06-01")
    assert seen["code"] == "401064"
    assert "401064" not in repr(est) and "areaCode" not in repr(est)
    assert est["window"] is None and est["chosen"] is None
    assert est["candidates"][0]["servesBasis"] == "PresumedByLocation"  # 職員には根拠を見せる（格上げしない）
    assert oe.for_claude(est) == [{"orgId": CANDS[0]["orgId"], "name": CANDS[0]["name"]}]


def test_estimate_without_an_area_gives_no_candidates(monkeypatch):
    monkeypatch.setattr(oe, "by_area", lambda *a, **k: pytest.fail("区が分からないのに資源の側を引いた"))
    est = oe.estimate(_Personal([]), object(), "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ", None)
    assert est["candidates"] == [] and est["notes"] and oe.for_claude(est) == []


def test_candidate_query_is_limited_to_consultation_kinds_and_served_areas():
    q = oe.BY_AREA
    assert ":SERVES" in q and ":PART_OF" in q and "$kinds" in q and "status: 'Active'" in q
    assert "servesBasis" in q
    assert {"DisabilityDivision", "ElderlyDivision", "HardshipSupportDesk", "CommunityGeneralSupportCenter"} <= set(oe.CONSULTATION_KINDS)
    assert not {"ChildGuidanceCenter", "DisabilityServiceSupervision"} & set(oe.CONSULTATION_KINDS)
