"""N-02：LINE の SOS 送信（NEXT-05）は、機能の設定と契約の確認の記録がそろうまで送らない。

LINE の鍵（トークン）があるだけでは送らない。送信は偽の httpx で数え、外へは出さない。
"""
import asyncio
import json
import os
from datetime import date

import pytest

pytest.importorskip("fastapi")
import sos.api_server as sos
from nest import egress

from tests.test_egress import good_entry


class FakeClient:
    posts = []

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        FakeClient.posts.append(url)

        class R:
            status_code = 200
            text = ""
        return R()


@pytest.fixture
def env(monkeypatch, tmp_path):
    FakeClient.posts = []
    rec, feat = tmp_path / "record.json", tmp_path / "features.json"
    monkeypatch.setattr(egress, "record_path", lambda: rec)
    monkeypatch.setattr(egress, "features_path", lambda: feat)
    monkeypatch.setattr(egress, "today", lambda: date(2026, 11, 5))
    monkeypatch.setattr(sos.httpx, "AsyncClient", FakeClient)
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy-not-a-token")
    monkeypatch.setenv("LINE_GROUP_ID", "dummy-group")
    return rec, feat


def _write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.chmod(path, 0o600)


def test_token_alone_does_not_send(env):
    assert asyncio.run(sos.send_line_message("（架空）SOS")) is False
    assert FakeClient.posts == []


def test_record_without_feature_does_not_send(env):
    rec, _ = env
    _write(rec, {"version": 1, "destinations": {"NEXT-05": good_entry()}})
    assert asyncio.run(sos.send_line_message("（架空）SOS")) is False
    assert FakeClient.posts == []


def test_both_present_sends_to_line_only(env):
    rec, feat = env
    _write(rec, {"version": 1, "destinations": {"NEXT-05": good_entry()}})
    _write(feat, {"NEXT-05": True})
    assert asyncio.run(sos.send_line_message("（架空）SOS")) is True
    assert FakeClient.posts == ["https://api.line.me/v2/bot/message/push"]
