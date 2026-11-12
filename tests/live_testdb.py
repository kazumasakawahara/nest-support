"""DB を使う試験の専用の DB（127.0.0.1:36687）の印と片づけ（2026-11-12 河原さんの決めごと。案 A。台帳 G-103）。

- 試験用の DB にだけ置く専用の印は NestTestDbProbe。試走の DB の印（NestLiveProbe）とは別のもの
- 印を置く（mark）のは、接続先が試験用の DB で、しかも中身が一つも無い DB のときだけ。試走の DB には中身があるので置けない
- 空にする（clear）のは、接続先が試験用の DB で、しかも NestTestDbProbe があるときだけ。どちらかが欠ければ何も消さずに止まる。
  ポート番号だけで見分けない。二つの印（NestTestDbProbe・NestLiveProbe）は残す。読み取りの包みは NestLiveProbe のある DB だけを読む
- DB を使う試験は、向き先が試験用の DB（NEST_DB_TARGET=test）でなければ始まりで止まる（tests/conftest.py）
- ゲートを通さない（試験用の DB での、人と試験の手の操作）

使い方（初めの一度。試験用の DB を起こした後）:
    NEST_DB_TARGET=test uv run python tests/live_testdb.py mark
"""
import sys
from pathlib import Path

TEST_MARK = "NestTestDbProbe"
TEST_URI = "bolt://127.0.0.1:36687"
MARKED = "MATCH (m:%s) RETURN count(m) > 0 AS marked"
COUNT = "MATCH (n) RETURN count(n) AS n"
MARK = ("CREATE (:NestTestDbProbe {probe: 'test-db', _fictional: true}) "
        "CREATE (:NestLiveProbe {probe: 'test-db', _fictional: true})")
WIPE = "MATCH (n) WHERE NOT n:NestTestDbProbe AND NOT n:NestLiveProbe DETACH DELETE n RETURN count(*) AS n"
TRIAL_MESSAGE = ("試走の DB に向いているので、DB を使う試験を止める。試験用の DB（127.0.0.1:36687）を起こし、"
                 "NEST_DB_TARGET=test NEST_LIVE_DB=1 uv run pytest -q で流す")


def require_test_target():
    from nest import connections
    if connections.target() != "test":
        raise RuntimeError(TRIAL_MESSAGE)


def _marked(driver, label, database):
    records, _, _ = driver.execute_query(MARKED % label, {}, database_=database)
    return bool(records and records[0]["marked"])


def place_test_mark(driver, uri, database="neo4j"):
    if uri != TEST_URI:
        raise RuntimeError("接続先が試験用の DB（%s）でない（%s）ので印を置かない" % (TEST_URI, uri))
    records, _, _ = driver.execute_query(COUNT, {}, database_=database)
    if records[0]["n"] != 0:
        raise RuntimeError("中身のある DB には試験用の印を置かない（%d 件ある）" % records[0]["n"])
    driver.execute_query(MARK, {}, database_=database)


def clear_test_db(driver, uri, database="neo4j"):
    if uri != TEST_URI:
        raise RuntimeError("接続先が試験用の DB（%s）でない（%s）ので空にしない" % (TEST_URI, uri))
    if not _marked(driver, TEST_MARK, database):
        raise RuntimeError("試験用の印（%s）が無い DB なので空にしない" % TEST_MARK)
    records, _, _ = driver.execute_query(WIPE, {}, database_=database)
    return records[0]["n"] if records else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nest import connections
    if sys.argv[1:] != ["mark"]:
        sys.exit("使い方：NEST_DB_TARGET=test uv run python tests/live_testdb.py mark")
    try:  # 止めるときは理由の一行だけを出す（Traceback を出さない。2026-11-12 河原さん）
        require_test_target()
        with connections.driver("personal") as d:
            place_test_mark(d, connections.uri("personal"))
    except RuntimeError as e:
        sys.exit(str(e))
    print("試験用の印を置いた（%s）" % connections.uri("personal"))
