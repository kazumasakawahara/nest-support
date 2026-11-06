"""N-37：音声を消す道具が、起動した個人の側（127.0.0.1:37687）から「承認された記録の documentHash」を引けること。
NEST_LIVE_DB=1 のときだけ。

    NEST_LIVE_DB=1 uv run pytest -q tests/test_voice_live.py

架空の本人に、架空の文字起こしを原文にした記録を二つ、ゲートで作る（人が入れた Active と、AI 由来の Pending）。
一時の置き場所に、その二つと記録の無い一つの音声を置き、消す道具が Active の分だけを消すこと、
消した後も Record の documentHash が DB に残ることを確かめる。
"""
import hashlib
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")


def _q(d, query, **params):
    records, _, _ = d.execute_query(query, params, database_="neo4j")
    return [r.data() for r in records]


def _h(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_purge_removes_only_audio_of_approved_records(tmp_path):
    from nest import connections, voice
    from nest.gate import write as gw
    tag = uuid.uuid4().hex
    texts = {"active": "（架空）承認された文字起こし " + tag, "pending": "（架空）未確定の文字起こし " + tag,
             "none": "（架空）記録の無い文字起こし " + tag}
    with connections.driver("personal") as d:
        admin = _q(d, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")
        if not admin:
            pytest.skip("Administrator がいない（ほかの DB つきの試験を先に流す）")
        admin = admin[0]["id"]

        def record(origin, text):
            out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                             "nodes": [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空"}},
                                       {"ref": "r", "label": "Record", "origin": origin, "properties": {
                                           "kind": "Observation", "text": text, "quote": text, "certainty": "Unspecified",
                                           "informantKind": "DocumentOnly", "documentHash": _h(text)}}],
                             "relationships": [{"type": "ABOUT", "from": "r", "to": "c"},
                                               {"type": "AUTHORED_BY", "from": "r", "to": {"label": "Staff", "id": admin}}]}, d)
            assert out["ok"], out["errors"]
            return out["ids"]["r"]
        rid_active = record("Human", texts["active"])
        rid_pending = record("AiExtracted", texts["pending"])
        statuses = {r["id"]: r["s"] for r in _q(d, "MATCH (r:Record) WHERE r.recordId IN $ids RETURN r.recordId AS id, r.status AS s",
                                                 ids=[rid_active, rid_pending])}
        assert statuses == {rid_active: "Active", rid_pending: "Pending"}

        root = tmp_path / "nest_voice_data"
        root.mkdir()
        paths = {k: root / (_h(t) + ".webm") for k, t in texts.items()}
        for p in paths.values():
            p.write_bytes(b"x")
        out = voice.purge(root, lambda hashes: voice.approved_hashes(d, hashes), write=True)
        assert out["errors"] == [] and out["approved"] == [paths["active"].name]
        assert not paths["active"].exists() and paths["pending"].exists() and paths["none"].exists()
        kept = _q(d, "MATCH (r:Record {recordId: $id}) RETURN r.documentHash AS h", id=rid_active)
        assert kept == [{"h": _h(texts["active"])}]  # 音声を消しても documentHash は残る
