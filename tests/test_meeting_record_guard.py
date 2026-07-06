"""
R2-2: register_meeting_record が未存在クライアントで幽霊 Client を作らない。
"""

import lib.embedding as emb


def test_rejects_unknown_client_no_ghost(tmp_path, monkeypatch):
    audio = tmp_path / "rec.webm"
    audio.write_bytes(b"x" * 10)

    calls = []

    def fake_rq(q, p=None):
        calls.append((q, p or {}))
        if "count(c)" in q:
            return [{"n": 0}]  # クライアント不在
        return []

    monkeypatch.setattr(emb, "_run_query", fake_rq)

    result = emb.register_meeting_record(
        str(audio), "居ない太郎", "職員A", "2026-07-01"
    )
    assert result["status"] == "error"
    # MeetingRecord を作る書き込みが一切発行されていない（幽霊 Client も作られない）
    assert not any("MeetingRecord" in q for q, _ in calls)
    assert not any("MERGE (c:Client" in q for q, _ in calls)


def test_existing_client_uses_match_not_merge(tmp_path, monkeypatch):
    audio = tmp_path / "rec.webm"
    audio.write_bytes(b"x" * 10)

    calls = []

    def fake_rq(q, p=None):
        calls.append((q, p or {}))
        if "count(c)" in q:
            return [{"n": 1}]  # クライアント存在
        return [{"id": "elem-1"}]

    monkeypatch.setattr(emb, "_run_query", fake_rq)
    # 高コストな音声処理はスタブ化
    monkeypatch.setattr(emb, "_get_audio_duration", lambda p: 5.0)
    monkeypatch.setattr(emb, "embed_audio", lambda p: None)
    monkeypatch.setattr(emb, "transcribe_audio", lambda p: "文字起こし")
    monkeypatch.setattr(emb, "embed_text", lambda *a, **k: None)

    result = emb.register_meeting_record(
        str(audio), "山田太郎", "職員A", "2026-07-01"
    )
    assert result["status"] == "success"
    write_qs = [q for q, _ in calls if "MeetingRecord" in q]
    assert write_qs, "MeetingRecord 登録クエリが発行されていない"
    assert "MATCH (c:Client {name: $client_name})" in write_qs[0]
    assert "MERGE (c:Client" not in write_qs[0]
