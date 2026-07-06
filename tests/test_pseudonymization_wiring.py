"""
P0-4: 仮名化レイヤーが読み取り関数に接続されていることの回帰テスト。

PSEUDONYMIZATION 有効時に、表示向け読み取り関数（get_clients_list /
resolve_client / insight-agent の staffName）の出力に実名が含まれないこと。
一方、照会・SOS 緊急通知向けの resolve_client_raw / get_display_name は
実名を返すこと（安全上の意図的例外）。
"""

import lib.db_operations as dbops
import lib.insight_engine as insight
import lib.pseudonymizer as pmod
from lib.pseudonymizer import Pseudonymizer


def _enable_masking(monkeypatch):
    """仮名化シングルトンを有効な mask モードに差し替える。"""
    inst = Pseudonymizer(enabled=True, mode="mask", seed="test")
    monkeypatch.setattr(pmod, "_default_instance", inst)
    return inst


def test_get_clients_list_is_masked(monkeypatch):
    _enable_masking(monkeypatch)
    monkeypatch.setattr(
        dbops, "run_query",
        lambda q, p=None: [{"name": "山田健太"}, {"name": "田中花子"}],
    )
    names = dbops.get_clients_list()
    assert "山田健太" not in names
    assert "田中花子" not in names
    # マスク済み（山●●● 形式）であること
    assert all("●" in n for n in names)


def test_resolve_client_masks_name_but_keeps_ids(monkeypatch):
    _enable_masking(monkeypatch)
    monkeypatch.setattr(
        dbops, "run_query",
        lambda q, p=None: [{"name": "山田健太", "clientId": "c-001", "displayCode": "A-001"}],
    )
    res = dbops.resolve_client("山田健太")
    assert res["name"] != "山田健太"
    assert "●" in res["name"]
    # 識別子は照合キーなのでマスクしない
    assert res["clientId"] == "c-001"
    assert res["displayCode"] == "A-001"


def test_resolve_client_raw_returns_real_name(monkeypatch):
    """SOS 緊急通知・照会キー用の raw は実名を返す（意図的例外）。"""
    _enable_masking(monkeypatch)
    monkeypatch.setattr(
        dbops, "run_query",
        lambda q, p=None: [{"name": "山田健太", "clientId": "c-001", "displayCode": "A-001"}],
    )
    res = dbops.resolve_client_raw("山田健太")
    assert res["name"] == "山田健太"


def test_get_display_name_returns_real_name(monkeypatch):
    """get_display_name は SOS 通知用に実名を返す（意図的例外）。"""
    _enable_masking(monkeypatch)
    monkeypatch.setattr(
        dbops, "run_query",
        lambda q, p=None: [{"name": "山田健太", "clientId": "c-001", "displayCode": "A-001"}],
    )
    assert dbops.get_display_name("c-001") == "山田健太"


def test_disabled_masking_is_passthrough(monkeypatch):
    """PSEUDONYMIZATION 無効時は実名のまま（既定挙動）。"""
    monkeypatch.setattr(pmod, "_default_instance", Pseudonymizer(enabled=False))
    monkeypatch.setattr(
        dbops, "run_query",
        lambda q, p=None: [{"name": "山田健太"}],
    )
    assert dbops.get_clients_list() == ["山田健太"]


def test_staff_overload_masks_staff_name(monkeypatch):
    _enable_masking(monkeypatch)
    monkeypatch.setattr(
        insight, "_run_query",
        lambda q, p=None: [{"staffName": "佐藤支援員", "totalLogs": 5, "negativeLogs": 4}],
    )
    results = insight.detect_staff_overload()
    assert results
    assert results[0]["staffName"] != "佐藤支援員"
    assert "●" in results[0]["staffName"]
