"""
P1-20: WAM NET 同期の廃止誤爆・復活・冪等性。
P1-21: レポート HTML のエスケープ。
"""

import importlib
import sys
from pathlib import Path

import pytest

_SCRIPTS = (
    Path(__file__).resolve().parent.parent
    / "claude-skills" / "wamnet-provider-sync" / "scripts"
)


@pytest.fixture(scope="module")
def sync_mod():
    sys.path.insert(0, str(_SCRIPTS))
    return importlib.import_module("sync_providers")


@pytest.fixture(scope="module")
def report_mod():
    sys.path.insert(0, str(_SCRIPTS))
    return importlib.import_module("generate_report")


# --- P1-20 (a): 部分 CSV が範囲外事業所を廃止しない ---

def test_partial_csv_does_not_close_out_of_scope(sync_mod):
    s = sync_mod.ServiceProviderSync(dry_run=True)
    # CSV は「東京都×通所介護」のみ。既存には別サービス種別・別県もある。
    new_providers = [
        {"providerId": "T1", "prefecture": "東京都", "serviceType": "通所介護"},
    ]
    existing = {
        "T1": {"providerId": "T1", "prefecture": "東京都", "serviceType": "通所介護"},
        "T2": {"providerId": "T2", "prefecture": "東京都", "serviceType": "居宅介護"},  # 別種別
        "O1": {"providerId": "O1", "prefecture": "大阪府", "serviceType": "通所介護"},  # 別県
    }
    to_add, to_update, closed = s.detect_changes(new_providers, existing)
    assert closed == [], "CSV のカバー範囲外の事業所を誤って廃止判定している"


def test_in_scope_missing_is_closed(sync_mod):
    s = sync_mod.ServiceProviderSync(dry_run=True)
    new_providers = [
        {"providerId": "T1", "prefecture": "東京都", "serviceType": "通所介護"},
    ]
    existing = {
        "T1": {"providerId": "T1", "prefecture": "東京都", "serviceType": "通所介護"},
        # 同じ範囲（東京都×通所介護）だが CSV から消えた → 廃止
        "T9": {"providerId": "T9", "prefecture": "東京都", "serviceType": "通所介護"},
    }
    _, _, closed = s.detect_changes(new_providers, existing)
    assert closed == ["T9"]


# --- P1-20 (b)/(c): クエリの安全性（文字列アサーション。実DBは使わない） ---

def test_create_uses_merge_and_active(sync_mod):
    s = sync_mod.ServiceProviderSync(dry_run=True)
    captured = {}

    class _Sess:
        def run(self, query, **kw):
            captured["q"] = query

    s._batch_create(_Sess(), [{"providerId": "X"}])
    q = captured["q"]
    assert "MERGE (sp:ServiceProvider {providerId: p.providerId})" in q, "再実行で重複する CREATE のまま"
    assert "sp.status = 'Active'" in q


def test_update_reactivates(sync_mod):
    s = sync_mod.ServiceProviderSync(dry_run=True)
    captured = {}

    class _Sess:
        def run(self, query, **kw):
            captured["q"] = query

    s._batch_update(_Sess(), [{"providerId": "X"}])
    assert "sp.status = 'Active'" in captured["q"], "CSV 再登場でも Closed のまま（復活しない）"


def test_mark_closed_guards_existing_closed(sync_mod):
    s = sync_mod.ServiceProviderSync(dry_run=True)
    captured = {}

    class _Sess:
        def run(self, query, **kw):
            captured["q"] = query

    s._mark_closed(_Sess(), ["X"])
    assert "<> 'Closed'" in captured["q"], "既存 Closed の closedAt を毎回上書きしている"


# --- P1-21: レポート HTML エスケープ ---

def test_report_escapes_html(report_mod):
    r = report_mod.__dict__
    assert "_esc" in r
    assert report_mod._esc('<img src=x onerror=alert(1)>') == \
        '&lt;img src=x onerror=alert(1)&gt;'
    assert report_mod._esc(None) == ""
