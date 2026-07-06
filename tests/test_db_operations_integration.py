"""
db_operations.register_to_database の統合テスト。

既存の Guardian Layer 単体テスト（test_schema_validator.py）は
validate_and_normalize_graph 単体の正規化を検証するが、
「その正規化が register_to_database を経て実際に Neo4j へ発行される
Cypher / パラメータまで貫いているか」は未検証だった。

このテストはその穴を塞ぐ。Neo4j 接続と embedding（Gemini）はモックし、
run_query に渡される (cypher, params) を捕捉して、
Guardian Layer の効果がDB書き込み層まで届いていることを確認する。

方針は既存テスト（test_insight_engine.py）と揃え、unittest.mock.patch で
モジュール境界をモックする。実DB・実APIには一切接続しない。
"""

import pytest
from unittest.mock import patch

from lib import db_operations


class _QueryRecorder:
    """run_query の代役。発行された全クエリを記録し、
    ノード作成クエリには擬似 elementId を返して temp_id_map を成立させる。"""

    def __init__(self):
        self.calls = []  # list[tuple[str, dict]]
        self._counter = 0

    def __call__(self, query, params=None):
        self.calls.append((query, params or {}))
        # register_to_database はノード作成時に "RETURN elementId(n) AS id" を期待する
        if "RETURN elementId(n) AS id" in query:
            self._counter += 1
            return [{"id": f"elem-{self._counter}"}]
        return []

    def queries_containing(self, needle):
        return [(q, p) for q, p in self.calls if needle in q]


# --- Neo4j driver/session/transaction のテストダブル ---
# register_to_database はノード＋リレーションを session.execute_write(tx_fn) の
# 単一 managed transaction で書き込み、監査等は run_query/execute_write（session.run）
# で書く。get_driver をこの FakeDriver に差し替えると、どちらの経路も recorder に届く。
class _FakeRecord:
    def __init__(self, d): self._d = d
    def data(self): return self._d


class _FakeResult:
    def __init__(self, rows): self._rows = list(rows or [])
    def data(self): return self._rows
    def __iter__(self): return iter(_FakeRecord(r) for r in self._rows)


class _FakeTx:
    def __init__(self, rec): self._rec = rec
    def run(self, query, params=None): return _FakeResult(self._rec(query, params))


class _FakeSession:
    def __init__(self, rec): self._rec = rec
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def run(self, query, params=None): return _FakeResult(self._rec(query, params))
    def execute_write(self, fn, *args, **kw): return fn(_FakeTx(self._rec), *args, **kw)
    def close(self): pass


class FakeDriver:
    def __init__(self, rec): self._rec = rec
    def session(self): return _FakeSession(self._rec)
    def verify_connectivity(self): pass
    def close(self): pass


@pytest.fixture
def recorder():
    """get_driver と embedding 系をモックした状態で register_to_database を動かす。"""
    rec = _QueryRecorder()
    with patch("lib.db_operations.get_driver", return_value=FakeDriver(rec)), \
         patch("lib.embedding.embed_texts_batch", return_value=[]), \
         patch("lib.embedding.embed_client_summary", return_value=None):
        yield rec


class TestRegisterGuardianLayerReachesDB:
    """Guardian Layer の正規化が run_query への発行内容まで貫くことを検証。"""

    def test_deprecated_relationship_is_rewritten_before_write(self, recorder):
        """廃止リレーション PROHIBITED が MUST_AVOID に補正されてから書き込まれる。"""
        graph = {
            "nodes": [
                {"temp_id": "c1", "label": "Client",
                 "properties": {"name": "統合テスト太郎"}},
                {"temp_id": "ng1", "label": "NgAction",
                 "properties": {"action": "後ろから声をかける",
                                "reason": "パニックになる",
                                "riskLevel": "Panic"}},
            ],
            "relationships": [
                {"source_temp_id": "c1", "target_temp_id": "ng1",
                 "type": "PROHIBITED", "properties": {}},
            ],
        }

        result = db_operations.register_to_database(graph, user_name="pytest")

        assert result["status"] == "success"
        # 廃止名は一切発行されてはならない
        assert recorder.queries_containing("[r:PROHIBITED]") == []
        # 正式名で関係が張られていること
        assert recorder.queries_containing("[r:MUST_AVOID]"), \
            "PROHIBITED が MUST_AVOID に補正されて発行されていない"

    def test_snake_case_property_is_camelcased_before_write(self, recorder):
        """snake_case プロパティ risk_level が riskLevel に変換されてDBに渡る。"""
        graph = {
            "nodes": [
                {"temp_id": "c1", "label": "Client",
                 "properties": {"name": "統合テスト花子"}},
                {"temp_id": "ng1", "label": "NgAction",
                 "properties": {"action": "大きな音",
                                "risk_level": "LifeThreatening"}},
            ],
            "relationships": [],
        }

        db_operations.register_to_database(graph, user_name="pytest")

        # NgAction を作成した run_query の props を集める
        ng_props = []
        for _, params in recorder.calls:
            props = params.get("props")
            if isinstance(props, dict) and props.get("action") == "大きな音":
                ng_props.append(props)

        assert ng_props, "NgAction の作成クエリが発行されていない"
        merged = ng_props[-1]
        assert "riskLevel" in merged, "risk_level が camelCase に正規化されていない"
        assert "risk_level" not in merged, "snake_case のキーが残存している"
        assert merged["riskLevel"] == "LifeThreatening"

    def test_ngaction_creates_audit_log(self, recorder):
        """安全上重要な NgAction 登録時に監査ログ(AuditLog)が必ず作られる。"""
        graph = {
            "nodes": [
                {"temp_id": "c1", "label": "Client",
                 "properties": {"name": "監査テスト次郎"}},
                {"temp_id": "ng1", "label": "NgAction",
                 "properties": {"action": "急な予定変更", "riskLevel": "Panic"}},
            ],
            "relationships": [],
        }

        db_operations.register_to_database(graph, user_name="pytest")

        audit_calls = recorder.queries_containing("CREATE (al:AuditLog")
        assert audit_calls, "AuditLog が作成されていない"
        # NgAction を対象にした監査が含まれること
        ng_audits = [p for _, p in audit_calls if p.get("type") == "NgAction"]
        assert ng_audits, "NgAction を対象とする監査ログが無い"
        assert ng_audits[0]["user"] == "pytest"


class TestRegisterInputGuards:
    """不正入力に対する防御挙動。"""

    def test_missing_nodes_key_returns_error(self, recorder):
        """'nodes' キーの無いグラフはエラーを返し、DB書き込みを一切行わない。"""
        result = db_operations.register_to_database({"relationships": []},
                                                    user_name="pytest")
        assert result["status"] == "error"
        assert recorder.calls == [], "不正グラフなのに run_query が呼ばれた"

    def test_node_without_label_is_skipped(self, recorder):
        """label 欠落ノードはスキップされ、登録カウントに含まれない。"""
        graph = {
            "nodes": [
                {"temp_id": "c1", "label": "Client",
                 "properties": {"name": "正常クライアント"}},
                {"temp_id": "x1", "properties": {"name": "ラベル無し"}},
            ],
            "relationships": [],
        }
        result = db_operations.register_to_database(graph, user_name="pytest")
        assert result["status"] == "success"
        assert result["types"] == ["Client"]
        assert result["count"] == 1


class TestAllowlistEnforcement:
    """P1-2: 許可リストに無いラベル/リレーションは書き込まない。"""

    def test_unknown_label_is_not_written(self, recorder):
        """スキーマ外ラベル（日本語ラベル等）は f-string に到達させずスキップ。"""
        graph = {
            "nodes": [
                {"temp_id": "c1", "label": "Client",
                 "properties": {"name": "太郎"}},
                {"temp_id": "e1", "label": "利用者",  # 未知ラベル
                 "properties": {"name": "悪意"}},
            ],
            "relationships": [],
        }
        result = db_operations.register_to_database(graph, user_name="pytest")
        assert result["status"] == "success"
        assert result["types"] == ["Client"]
        # 未知ラベルを含むクエリが一切発行されていないこと
        assert recorder.queries_containing("利用者") == []
        assert any("スキップ" in w and "利用者" in w for w in result["warnings"])

    def test_unknown_relationship_is_not_written(self, recorder):
        """許可リストに無いリレーション型はスキップされる。"""
        graph = {
            "nodes": [
                {"temp_id": "c1", "label": "Client", "properties": {"name": "太郎"}},
                {"temp_id": "s1", "label": "Supporter", "properties": {"name": "花子"}},
            ],
            "relationships": [
                {"source_temp_id": "s1", "target_temp_id": "c1",
                 "type": "EVIL_REL", "properties": {}},
            ],
        }
        result = db_operations.register_to_database(graph, user_name="pytest")
        assert result["status"] == "success"
        assert recorder.queries_containing("EVIL_REL") == []


class TestTransactionAtomicity:
    """P1-1: 途中失敗時は全体ロールバック（部分登録を残さない）。"""

    def test_write_failure_returns_error_no_partial(self):
        """トランザクション内の書き込みが失敗したら error を返す（partial_count=0）。"""
        rec = _QueryRecorder()

        def _boom(query, params=None):
            if "SupportLog" in query:
                raise RuntimeError("書き込み失敗（模擬）")
            return rec(query, params)

        driver = FakeDriver(_boom)
        with patch("lib.db_operations.get_driver", return_value=driver), \
             patch("lib.embedding.embed_texts_batch", return_value=[]), \
             patch("lib.embedding.embed_client_summary", return_value=None):
            graph = {
                "nodes": [
                    {"temp_id": "c1", "label": "Client", "properties": {"name": "太郎"}},
                    {"temp_id": "log1", "label": "SupportLog",
                     "properties": {"date": "2026-01-01", "situation": "x"}},
                ],
                "relationships": [],
            }
            result = db_operations.register_to_database(graph, user_name="pytest")
        assert result["status"] == "error"
        assert result["partial_count"] == 0


class TestAuditFailureSurfaced:
    """P1-3: 監査ログ書き込み失敗は握り潰さず warnings で伝える。"""

    def test_audit_failure_appears_in_warnings(self):
        rec = _QueryRecorder()

        def _fail_audit(query, params=None):
            if "AuditLog" in query:
                raise RuntimeError("監査書き込み失敗（模擬）")
            return rec(query, params)

        driver = FakeDriver(_fail_audit)
        with patch("lib.db_operations.get_driver", return_value=driver), \
             patch("lib.embedding.embed_texts_batch", return_value=[]), \
             patch("lib.embedding.embed_client_summary", return_value=None):
            graph = {
                "nodes": [
                    {"temp_id": "c1", "label": "Client", "properties": {"name": "太郎"}},
                    {"temp_id": "ng1", "label": "NgAction",
                     "properties": {"action": "大きな音", "riskLevel": "Panic"}},
                ],
                "relationships": [
                    {"source_temp_id": "c1", "target_temp_id": "ng1",
                     "type": "MUST_AVOID", "properties": {}},
                ],
            }
            result = db_operations.register_to_database(graph, user_name="pytest")

        # ノード登録自体は成功（監査はベストエフォート）だが、失敗は warnings に載る
        assert result["status"] == "success"
        assert any("監査ログ書き込み失敗" in w for w in result["warnings"])
