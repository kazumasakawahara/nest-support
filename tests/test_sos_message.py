"""N-28：SOS の中身（ADR-001 D11-3、external-api NEXT-05）。DB も LINE も使わない。

LINE に送るのは、SOS があったこと・誰のことか（仮名 displayCode）・位置・確かめる先だけ。
電話・禁忌・実名・キーパーソンの名前は送らない。送る文を作るのに DB を読まない。
"""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import sos.api_server as sos

CODE = "C-ZZZZZZ"


@pytest.fixture
def sent(monkeypatch):
    box = []

    async def _fake_send(message):
        box.append(message)
        return True

    def _no_db(*a, **k):
        raise AssertionError("SOS の文を作るのに DB を読まない")

    monkeypatch.setattr(sos, "send_line_message", _fake_send)
    monkeypatch.setattr(sos, "get_client_info", _no_db)
    monkeypatch.setattr(sos, "get_client_cautions", _no_db)
    return box


def test_message_has_only_the_allowed_parts():
    msg = sos.create_sos_message(CODE, latitude=33.5, longitude=130.4, accuracy=12.3)
    assert "SOS" in msg and CODE in msg
    assert "https://www.google.com/maps?q=33.5,130.4" in msg
    assert "手元の緊急連絡カード" in msg and "SOS の画面" in msg


def test_message_without_location_says_so():
    msg = sos.create_sos_message(CODE)
    assert "位置" in msg and "maps" not in msg


def test_message_does_not_carry_a_name_shaped_id():
    """仮名の形でないもの（実名かもしれない）は、誰のことかとして送らない。"""
    for raw in ("架空太郎", "C-00000O", "c-zzzzzz", "C-ZZZZZZZ", ""):
        msg = sos.create_sos_message(raw)
        assert raw == "" or raw not in msg
        assert "仮名の形でない" in msg


def test_endpoint_sends_no_phone_no_ngaction_no_db(sent):
    client = TestClient(sos.app)
    resp = client.post("/api/sos", json={"client_id": CODE, "latitude": 33.5, "longitude": 130.4})
    assert resp.status_code == 200
    [msg] = sent
    assert CODE in msg and "手元の緊急連絡カード" in msg
    for word in ("緊急連絡先:", "対応時の注意", "電話", "📞", "⚠️"):
        assert word not in msg, word


def test_registered_and_unknown_ids_send_the_same_shape(sent):
    client = TestClient(sos.app)
    client.post("/api/sos", json={"client_id": CODE})
    client.post("/api/sos", json={"client_id": "C-YYYYYY"})
    a, b = (["" if "発信" in l else l for l in m.splitlines()] for m in sent)
    assert [l.replace(CODE, "C-YYYYYY") for l in a] == b
