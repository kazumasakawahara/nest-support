"""試走の DB に架空の印を置く（N-46 詰まり #2。2026-11-08 河原さん）。

- 接続先が試走の DB（個人の側 bolt://127.0.0.1:37687）でなければ、何もせずに RuntimeError
- 架空の印（NestLiveProbe）を一つ置く（MERGE。何度打っても一つ）。ゲートを通さない（人の手の操作。G-51）
- 何も消さない。試験の残りを消すのは tests/live_cleanup.py（印のある DB でだけ動く）
- 実データを入れた DB では打たない。印を置くと Claude の照会が DB を読めるようになる（台帳 G-80）

    uv run python tests/live_mark.py
"""
import sys
from pathlib import Path

TRIAL_URI = "bolt://127.0.0.1:37687"
MARK = "MERGE (m:NestLiveProbe {probe: 'trial'}) SET m._fictional = true"


def place_mark(driver, uri, database="neo4j"):
    if uri != TRIAL_URI:
        raise RuntimeError("接続先が試走の DB（%s）でない（%s）ので印を置かない" % (TRIAL_URI, uri))
    driver.execute_query(MARK, {}, database_=database)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nest import connections
    uri = connections.SETTINGS["personal"][1]
    with connections.driver("personal") as d:
        place_mark(d, uri)
    print("架空の印を置いた（%s）" % uri)
