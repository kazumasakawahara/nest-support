"""関わりの機関の候補（2026-11-11 河原さん）。DB を使わない（偽の DB）。

- 同じ呼び名が並ぶと人が選べないので、候補ごとに所在地の市区（資源の側の Area.name）と、その機関のサービスの種類
  （資源の側の Service.serviceTypeName の一覧）を添える。資源の側から読むだけ
- 点数づけ・並べ替え・自動の絞り込みはしない（DB の名前の順のまま。案の serviceTypeName と照らして減らさない）
- by_name（N-24 の提供元の候補）の返す形は変えない
"""
import pytest

from nest import org_candidates as oc

ROWS = [{"orgId": "ORG-B", "name": "つばさ（い）", "kind": "DisabilityServiceOffice", "matchedBy": "name",
         "areas": ["北九州市小倉北区"], "services": ["生活介護", "就労継続支援B型"]},
        {"orgId": "ORG-A", "name": "つばさ（ろ）", "kind": "CareServiceOffice", "matchedBy": "alias",
         "areas": [], "services": []}]


class _Driver:
    def __init__(self, rows):
        self.rows, self.queries = rows, []

    def session(self, **kw):
        driver = self

        class S:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute_read(self, fn):
                class Tx:
                    def run(self, query, **params):
                        driver.queries.append((query, params))
                        return iter(driver.rows)
                return fn(Tx())
        return S()


def test_each_candidate_carries_its_city_and_service_types():
    out = oc.for_involvement(_Driver(ROWS), "つばさ")
    first, second = out["candidates"]
    assert first == {"orgId": "ORG-B", "name": "つばさ（い）", "kind": "DisabilityServiceOffice", "matchedBy": "name",
                     "areas": ["北九州市小倉北区"], "serviceTypes": ["就労継続支援B型", "生活介護"]}
    assert second["areas"] == [] and second["serviceTypes"] == []
    assert out["query"] == "つばさ" and out["truncated"] is False


def test_the_order_is_the_db_order_and_nothing_is_dropped():
    out = oc.for_involvement(_Driver(ROWS), "つばさ")
    assert [c["orgId"] for c in out["candidates"]] == ["ORG-B", "ORG-A"]


def test_it_takes_no_service_type_to_filter_by():
    import inspect
    assert list(inspect.signature(oc.for_involvement).parameters) == ["driver", "name", "limit", "database"]


def test_the_name_is_matched_like_by_name():
    d = _Driver(ROWS)
    oc.for_involvement(d, "つ ば　さ")
    (query, params), = d.queries
    assert params == {"name": "つばさ"}
    assert "LOCATED_IN" in query and "PROVIDES" in query and "serviceTypeName" in query
    assert oc.SEARCH.split("WHERE")[0].strip() in query  # 名前の引き方は by_name と同じ


def test_over_the_limit_is_cut_and_marked():
    rows = [dict(ROWS[0], orgId="ORG-%02d" % n) for n in range(5)]
    out = oc.for_involvement(_Driver(rows), "つばさ", limit=3)
    assert len(out["candidates"]) == 3 and out["truncated"] is True


def test_a_short_name_stops():
    with pytest.raises(ValueError):
        oc.for_involvement(_Driver(ROWS), "つ")


def test_by_name_keeps_its_shape():
    rows = [{k: r[k] for k in oc.CANDIDATE_KEYS} for r in ROWS]
    out = oc.by_name(_Driver(rows), "つばさ")
    assert set(out) == {"query", "candidates", "truncated", "chosen"}
    assert all(set(c) == {"orgId", "name", "kind", "matchedBy"} for c in out["candidates"])
