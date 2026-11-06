"""試験の DB を片づける（合流前の直し 1。2026-11-06 河原さん。台帳 G-86・G-87）。

- 架空の印（NestLiveProbe）のある DB でだけ動く。印が無ければ何も消さずに RuntimeError
- 印のノード以外をすべて DETACH DELETE する。ゲートを通さない（印を置くのと同じく、試験の DB での人の手の操作）
- DB つきの試験を流す前に、手で一度流す（試験の途中では流さない。ほかの試験の職員や本人まで消えるため）：

    uv run python tests/live_cleanup.py
"""
import sys
from pathlib import Path

MARKED = "MATCH (m:NestLiveProbe) RETURN count(m) > 0 AS marked"
WIPE = "MATCH (n) WHERE NOT n:NestLiveProbe DETACH DELETE n RETURN count(*) AS n"


def clear_fictional_db(driver, database="neo4j"):
    records, _, _ = driver.execute_query(MARKED, {}, database_=database)
    if not (records and records[0]["marked"]):
        raise RuntimeError("架空の印（NestLiveProbe）が無い DB なので片づけない")
    records, _, _ = driver.execute_query(WIPE, {}, database_=database)
    return records[0]["n"] if records else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nest import connections
    with connections.driver("personal") as d:
        print("消した：%d 件（架空の印のノードは残した）" % clear_fictional_db(d))
