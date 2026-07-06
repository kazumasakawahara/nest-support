"""
P0-3: SOS レスポンスの PII 混入と名前列挙オラクルの回帰テスト。

- SOS レスポンスに電話番号・禁忌全文・キーパーソン名を含めない（sent_message 廃止）。
- クライアント照会は部分一致（CONTAINS）ではなく完全一致とし、名前列挙を防ぐ。
"""

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import sos.api_server as sos


@pytest.fixture
def client(monkeypatch):
    async def _fake_send(message):
        return True
    monkeypatch.setattr(sos, "send_line_message", _fake_send)
    return TestClient(sos.app)


def test_sos_response_excludes_pii(client, monkeypatch):
    monkeypatch.setattr(sos, "get_client_info", lambda cid: {
        "name": "山田太郎",
        "keyPersons": [{"name": "山田花子", "relationship": "母", "phone": "090-1234-5678", "rank": 1}],
    })
    monkeypatch.setattr(sos, "get_client_cautions", lambda name: [
        {"action": "エビ・カニを与える", "risk": "LifeThreatening"},
    ])

    # displayCode で送信（入力値と実名が異なる）→ 実名が漏れないことを検証
    resp = client.post("/api/sos", json={"client_id": "A-001"})
    assert resp.status_code == 200
    body = resp.json()

    # sent_message / mock_mode / client_name はレスポンスに含めない
    assert "sent_message" not in body
    assert "mock_mode" not in body
    assert "client_name" not in body

    # PII（電話番号・禁忌全文・キーパーソン名）がレスポンス本文に混入しない
    text = resp.text
    assert "090-1234-5678" not in text
    assert "エビ・カニを与える" not in text
    assert "山田花子" not in text

    # R2-1: DB 由来の実名がレスポンスに混入しない（displayCode→実名オラクル封じ）
    assert "山田太郎" not in text
    # 入力した識別子はそのまま echo される（DB 由来ではない）
    assert body.get("received_id") == "A-001"


def test_sos_does_not_leak_registration_status(client, monkeypatch):
    """R2-1: 登録済み/未登録で応答が区別できない（登録有無オラクル封じ）。"""
    monkeypatch.setattr(sos, "get_client_info", lambda cid: {
        "name": "山田太郎", "keyPersons": [],
    })
    monkeypatch.setattr(sos, "get_client_cautions", lambda name: [])
    registered = client.post("/api/sos", json={"client_id": "A-001"}).json()

    monkeypatch.setattr(sos, "get_client_info", lambda cid: None)
    unregistered = client.post("/api/sos", json={"client_id": "A-999"}).json()

    # message が登録有無で変わらない（「未登録ユーザー」等の差分を出さない）
    assert registered["message"] == unregistered["message"]
    assert set(registered.keys()) == set(unregistered.keys())


def test_sos_unregistered_response_excludes_message(client, monkeypatch):
    monkeypatch.setattr(sos, "get_client_info", lambda cid: None)
    resp = client.post("/api/sos", json={"client_id": "未知ID"})
    assert resp.status_code == 200
    body = resp.json()
    assert "sent_message" not in body


def test_client_info_uses_exact_match(monkeypatch):
    """get_client_info のフォールバックは CONTAINS（部分一致）を使わない。"""
    captured = []

    def _fake_run_query(q, p=None):
        captured.append(q)
        return []

    monkeypatch.setattr(sos, "resolve_client_raw", lambda x: None)
    monkeypatch.setattr(sos, "run_query", _fake_run_query)

    sos.get_client_info("山")

    assert captured, "フォールバッククエリが実行されるはず"
    assert not any("CONTAINS" in q for q in captured), (
        "クライアント名照会に CONTAINS を使ってはならない（名前列挙オラクル）"
    )
