"""N-33：バックアップを取って戻すことを、起動した個人の側（127.0.0.1:37687）で確かめる。NEST_LIVE_DB=1 のときだけ。

    NEST_LIVE_DB=1 uv run pytest -q tests/test_backup_live.py

いつもの個人の側は置き換えない：
1. いつもの個人の側に架空の本人（前）を作り、コンテナを止めて書き出す（試験の一時フォルダ。~/nest-backup は使わない）。起こして、架空の本人（後）を作る
2. 書き出しを、試験の一時のデータのフォルダに戻し、使い捨てのコンテナ（127.0.0.1:39687 だけで待ち受け。パスワードは試験ごとの乱数）で起こす
3. 戻した DB に（前）があり（後）が無いこと、制約・索引・ラベルが正典とずれていないこと（ずれ 0 件）、正典の文書のずれ 0 件を確かめる
戻す命令は、いつもの個人の側に戻すときと同じ（データのフォルダの場所だけが違う）。計画 N-33、台帳 G-74・G-75。
"""
import datetime as dt
import os
import secrets
import subprocess
import time
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("NEST_LIVE_DB") != "1", reason="NEST_LIVE_DB=1 のときだけ")

REPO = Path(__file__).resolve().parents[1]
ENV = str(Path.home() / ".config" / "nest" / "neo4j-redesign.env")
SCRATCH = "nest-backup-restore-test"
SCRATCH_PORT = 39687  # nest-support の 37xxx・38xxx、tsunagu-net の 17xxx・27xxx・47xxx・48xxx を避けた
EXTRA_LABELS = {"NestLiveProbe"}  # 架空の印（ゲートを通さず人が置く。正典の外）


def _compose(*args):
    subprocess.run(["docker", "compose", "--env-file", ENV, *args, "neo4j-personal"], cwd=REPO, check=True,
                   capture_output=True)


def _wait(open_driver, timeout=120):
    end = time.time() + timeout
    while True:
        try:
            d = open_driver()
            d.verify_connectivity()
            return d
        except Exception:
            if time.time() > end:
                raise
            time.sleep(2)


def _personal():
    from nest import connections
    cm = connections.driver("personal")
    d = cm.__enter__()
    d._nest_cm = cm
    return d


def _close(d):
    getattr(d, "_nest_cm", None).__exit__(None, None, None) if hasattr(d, "_nest_cm") else d.close()


def _q(d, query, **params):
    records, _, _ = d.execute_query(query, params, database_="neo4j")
    return [r.data() for r in records]


def _client(d, admin):
    from nest.gate import write as gw
    out = gw.submit({"requestId": "req-" + uuid.uuid4().hex, "actorStaffId": admin,
                     "nodes": [{"ref": "c", "label": "Client", "origin": "Human", "properties": {"familyName": "架空"}}],
                     "relationships": []}, d)
    assert out["ok"], out["errors"]
    return out["ids"]["c"]


def test_dump_and_restore_bring_back_the_earlier_state_without_drift(tmp_path):
    import neo4j
    from nest import backup, canon, schema_apply
    d = _wait(_personal)
    try:
        admin = _q(d, "MATCH (s:Staff {role: 'Administrator', status: 'Active'}) RETURN s.staffId AS id ORDER BY id LIMIT 1")
        if not admin:
            pytest.skip("Administrator がいない（ほかの DB つきの試験を先に流す）")
        admin = admin[0]["id"]
        before = _client(d, admin)
    finally:
        _close(d)

    image = backup.personal_image((REPO / "docker-compose.yml").read_text(encoding="utf-8"))
    root = tmp_path / "nest-backup"
    _compose("stop")
    try:
        out = backup.dump(root, backup.DEFAULT_DATA, image, now=dt.datetime.now())
        assert out["ok"], out["errors"]
        assert oct(os.stat(root).st_mode & 0o777) == "0o700"
    finally:
        _compose("start")
    d = _wait(_personal)
    try:
        after = _client(d, admin)
    finally:
        _close(d)

    data = tmp_path / "restored-data"
    data.mkdir()
    r = backup.restore(root / out["generation"], data, image)
    assert r["ok"], r["errors"]
    password = secrets.token_urlsafe(16)
    subprocess.run(["docker", "run", "-d", "--name", SCRATCH, "-p", "127.0.0.1:%d:7687" % SCRATCH_PORT,
                    "-e", "NEO4J_AUTH=neo4j/%s" % password, "-e", "NEO4J_dbms_usage__report_enabled=false",
                    "-v", "%s:/data" % data, image], check=True, capture_output=True)
    ok = False
    try:
        ports = subprocess.run(["docker", "ps", "--filter", "name=" + SCRATCH, "--format", "{{.Ports}}"],
                               capture_output=True, text=True).stdout
        assert "127.0.0.1:%d" % SCRATCH_PORT in ports and "0.0.0.0" not in ports
        d = _wait(lambda: neo4j.GraphDatabase.driver("bolt://127.0.0.1:%d" % SCRATCH_PORT, auth=("neo4j", password)))
        try:
            n = lambda cid: _q(d, "MATCH (c:Client {clientId: $id}) RETURN count(c) AS n", id=cid)[0]["n"]  # noqa: E731
            assert n(before) == 1 and n(after) == 0
            c = canon.load(REPO / "docs" / "SCHEMA.md")
            constraints = {x["name"] for x in _q(d, "SHOW CONSTRAINTS YIELD name RETURN name")}
            indexes = {x["name"] for x in _q(d, "SHOW INDEXES YIELD name RETURN name")}
            labels = {x["label"] for x in _q(d, "CALL db.labels() YIELD label RETURN label")}
            assert constraints == set(schema_apply.expected_constraint_names(c))
            assert set(schema_apply.expected_index_names(c)) <= indexes
            assert labels - EXTRA_LABELS <= set(c["personal"]["nodes"]), labels
        finally:
            d.close()
        ok = True
    finally:
        if not ok:  # 失敗したときだけ、使い捨てのコンテナのログの終わりを出す（架空のデータだけ）
            print(subprocess.run(["docker", "logs", "--tail", "30", SCRATCH], capture_output=True, text=True).stdout[-3000:])
        subprocess.run(["docker", "rm", "-f", SCRATCH], capture_output=True)
    drift = subprocess.run(["uv", "run", "--quiet", "python", "scripts/check_drift.py"], cwd=REPO, capture_output=True, text=True)
    assert drift.returncode == 0 and "ずれ 0 件" in drift.stdout
