"""試験の DB の架空の本人を片づける（合流前の直し。2026-11-06 河原さん）。DB つきの試験から使う。

- 架空の印（NestLiveProbe）のある DB でだけ動く。印が無ければ何も消さずに RuntimeError
- 本人（Client）を DETACH DELETE する。ゲートを通さない（印を置くのと同じく、試験の DB での人の手の操作）
"""
MARKED = "MATCH (m:NestLiveProbe) RETURN count(m) > 0 AS marked"


def clear_fictional_clients(driver, database="neo4j"):
    records, _, _ = driver.execute_query(MARKED, {}, database_=database)
    if not (records and records[0]["marked"]):
        raise RuntimeError("架空の印（NestLiveProbe）が無い DB なので片づけない")
    records, _, _ = driver.execute_query("MATCH (c:Client) DETACH DELETE c RETURN count(*) AS n", {}, database_=database)
    return records[0]["n"] if records else 0
