"""
register_to_database の MERGE スコープのテスト。

MERGE_KEYS が弱い識別キー（NgAction=["action"], KeyPerson=["name"] 等）で
グローバル MERGE を行うと、複数クライアントの
同種ノードが 1 ノードに収斂し、`SET n += $props` で互いのプロパティ
（nextRenewalDate, riskLevel 等）を上書きし合う。

このテストは「Client 配下の子ノードはクライアントごとに別ノードになる」
「Supporter / Hospital 等の実体共有ノードはグローバル MERGE を維持する」
ことを検証する。

方針は test_db_operations_integration.py と同じく実DB・実APIには接続しない。
ただし発行クエリの記録だけでは「同一ノードに解決されたか」を判定できない
ため、Neo4j の MERGE 一致セマンティクスをキー一致レベルで再現する
テストダブル（_FakeMergeStore）を使う。
"""

import json

import pytest
from unittest.mock import patch

from lib import db_operations


class _FakeMergeStore:
    """Neo4j の MERGE 一致セマンティクスを「キー一致」レベルで再現する代役。

    - MERGE を含み elementId(n) を返すクエリ:
      クエリ文字列＋一致パラメータ（params から SET 専用ペイロード
      props / relProps を除いたもの）が同一なら同一ノードIDを返す。
      これは「同一の MERGE パターンと一致値は同一ノードに解決される」
      という Neo4j 実機の挙動に対応する。
    - CREATE で elementId(n) を返すクエリ: 常に新規IDを返す。
    - それ以外（リレーション・監査ログ等）: 記録のみ。
    """

    _SET_PAYLOAD_KEYS = {"props", "relProps"}

    def __init__(self):
        self.calls = []  # list[tuple[str, dict]]
        self.node_calls = []  # list[tuple[str, dict, str]] (query, params, node_id)
        self._nodes = {}  # 一致キー -> node_id
        self._counter = 0

    def __call__(self, query, params=None):
        params = params or {}
        self.calls.append((query, params))
        if "RETURN elementId(n) AS id" not in query:
            return []
        if "MERGE" in query:
            match_params = {k: v for k, v in params.items()
                            if k not in self._SET_PAYLOAD_KEYS}
            key = (query, json.dumps(match_params, sort_keys=True,
                                     ensure_ascii=False, default=str))
            if key not in self._nodes:
                self._counter += 1
                self._nodes[key] = f"elem-{self._counter}"
            node_id = self._nodes[key]
        else:
            self._counter += 1
            node_id = f"elem-{self._counter}"
        self.node_calls.append((query, params, node_id))
        return [{"id": node_id}]

    def node_ids_for_label(self, label):
        """指定ラベルのノード作成/MERGE クエリが解決したノードIDの集合。"""
        return {nid for q, _, nid in self.node_calls if f"n:{label}" in q}

    def queries_containing(self, needle):
        return [(q, p) for q, p in self.calls if needle in q]


# --- Neo4j driver/session/transaction のテストダブル ---
# register_to_database は単一 managed transaction（session.execute_write）で
# ノード＋リレーションを書く。get_driver を差し替えて全書き込みを store に届ける。
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


class _FakeDriver:
    def __init__(self, rec): self._rec = rec
    def session(self): return _FakeSession(self._rec)
    def verify_connectivity(self): pass
    def close(self): pass


@pytest.fixture
def store():
    rec = _FakeMergeStore()
    with patch("lib.db_operations.get_driver", return_value=_FakeDriver(rec)), \
         patch("lib.embedding.embed_texts_batch", return_value=[]), \
         patch("lib.embedding.embed_client_summary", return_value=None):
        yield rec


def _graph(client_name, child_label, child_props, rel_type, rel_props=None):
    return {
        "nodes": [
            {"temp_id": "c1", "label": "Client",
             "properties": {"name": client_name}},
            {"temp_id": "x1", "label": child_label,
             "properties": child_props},
        ],
        "relationships": [
            {"source_temp_id": "c1", "target_temp_id": "x1",
             "type": rel_type, "properties": rel_props or {}},
        ],
    }


class TestClientScopedChildNodes:
    """Client 配下の子ノードはクライアント間で共有されてはならない。"""

    def test_same_ngaction_across_clients_creates_separate_nodes(self, store):
        """2クライアントに同名 action の NgAction を登録すると別ノードになる。"""
        r1 = db_operations.register_to_database(
            _graph("山田太郎", "NgAction",
                   {"action": "大きな音", "riskLevel": "Panic"},
                   "MUST_AVOID"),
            user_name="pytest")
        r2 = db_operations.register_to_database(
            _graph("佐藤花子", "NgAction",
                   {"action": "大きな音", "riskLevel": "LifeThreatening"},
                   "MUST_AVOID"),
            user_name="pytest")

        assert r1["status"] == "success" and r2["status"] == "success"
        ng_ids = store.node_ids_for_label("NgAction")
        assert len(ng_ids) == 2, (
            "別クライアントの同名 NgAction が同一ノードに収斂している"
            "（riskLevel が相互上書きされる）")

    def test_same_certificate_type_across_clients_creates_separate_nodes(self, store):
        """同 type の Certificate が別ノードになる（全員の療育手帳が1ノードに収斂しない）。"""
        db_operations.register_to_database(
            _graph("山田太郎", "Certificate",
                   {"type": "療育手帳", "nextRenewalDate": "2026-09-30"},
                   "HAS_CERTIFICATE", {"status": "Active"}),
            user_name="pytest")
        db_operations.register_to_database(
            _graph("佐藤花子", "Certificate",
                   {"type": "療育手帳", "nextRenewalDate": "2027-03-31"},
                   "HAS_CERTIFICATE", {"status": "Active"}),
            user_name="pytest")

        cert_ids = store.node_ids_for_label("Certificate")
        assert len(cert_ids) == 2, (
            "別クライアントの同 type Certificate が同一ノードに収斂している"
            "（nextRenewalDate が相互上書きされる）")

    def test_same_keyperson_name_across_clients_creates_separate_nodes(self, store):
        """同名の KeyPerson が別ノードになる（同姓同名の他人を混同しない）。"""
        db_operations.register_to_database(
            _graph("山田太郎", "KeyPerson",
                   {"name": "田中一郎", "phone": "090-1111-1111"},
                   "HAS_KEY_PERSON", {"rank": 1}),
            user_name="pytest")
        db_operations.register_to_database(
            _graph("佐藤花子", "KeyPerson",
                   {"name": "田中一郎", "phone": "080-2222-2222"},
                   "HAS_KEY_PERSON", {"rank": 1}),
            user_name="pytest")

        kp_ids = store.node_ids_for_label("KeyPerson")
        assert len(kp_ids) == 2, (
            "別クライアントの同名 KeyPerson が同一ノードに収斂している"
            "（電話番号が相互上書きされる）")

    def test_same_wish_for_same_client_is_idempotent(self, store):
        """同一クライアントへの同内容 Wish の再登録は重複ノードを作らない。"""
        graph = _graph("山田太郎", "Wish",
                       {"content": "グループホームで暮らしたい"},
                       "HAS_WISH")
        db_operations.register_to_database(graph, user_name="pytest")
        db_operations.register_to_database(graph, user_name="pytest")

        wish_ids = store.node_ids_for_label("Wish")
        assert len(wish_ids) == 1, "同一クライアントの同内容 Wish が重複登録された"


def _reverse_graph(client_name, child_label, child_props, rel_type, rel_props=None):
    """(node)-[rel]->(Client) の逆向きリレーションを持つグラフ（Relative 等）。"""
    return {
        "nodes": [
            {"temp_id": "c1", "label": "Client",
             "properties": {"name": client_name}},
            {"temp_id": "x1", "label": child_label,
             "properties": child_props},
        ],
        "relationships": [
            {"source_temp_id": "x1", "target_temp_id": "c1",
             "type": rel_type, "properties": rel_props or {}},
        ],
    }


class TestReverseScopedRelative:
    """Relative は (Relative)-[:IS_PARENT_OF]->(Client) と逆向きだが
    クライアント配下にスコープされること（DRIFT-12）。"""

    def test_same_relative_name_across_clients_creates_separate_nodes(self, store):
        """別クライアントの同姓同名の家族は別ノードになる。"""
        db_operations.register_to_database(
            _reverse_graph("山田太郎", "Relative",
                           {"name": "田中花子", "relationship": "母"},
                           "IS_PARENT_OF"),
            user_name="pytest")
        db_operations.register_to_database(
            _reverse_graph("佐藤次郎", "Relative",
                           {"name": "田中花子", "relationship": "母"},
                           "IS_PARENT_OF"),
            user_name="pytest")

        rel_ids = store.node_ids_for_label("Relative")
        assert len(rel_ids) == 2, (
            "別クライアントの同姓同名 Relative が同一ノードに収斂している"
            "（healthStatus 等が相互上書きされる）")

    def test_reregistering_same_relative_is_idempotent(self, store):
        """同一クライアントへの同名 Relative の再登録は同一ノードに解決される。"""
        graph = _reverse_graph("山田太郎", "Relative",
                               {"name": "田中花子", "relationship": "母"},
                               "IS_PARENT_OF")
        db_operations.register_to_database(graph, user_name="pytest")
        db_operations.register_to_database(graph, user_name="pytest")

        rel_ids = store.node_ids_for_label("Relative")
        assert len(rel_ids) == 1, "同一クライアントの同名 Relative が重複登録された"

    def test_relative_relationship_direction_is_preserved(self, store):
        """スコープ付き MERGE でも向きは (Relative)->(Client) のまま。"""
        db_operations.register_to_database(
            _reverse_graph("山田太郎", "Relative",
                           {"name": "田中花子", "relationship": "母"},
                           "IS_PARENT_OF"),
            user_name="pytest")

        calls = store.queries_containing("IS_PARENT_OF")
        assert calls, "IS_PARENT_OF が書き込まれていない"
        assert any("(n:Relative" in q and "]->(c)" in q for q, _ in calls), \
            "逆向きリレーションの向きが保存されていない（Client→Relative になっている）"


class TestCertificateCompositeKey:
    """Certificate は type+grade の複合キー（正典 §10.3・DRIFT-12）。"""

    def test_different_grades_for_same_client_are_separate_nodes(self, store):
        """同一人の療育手帳 A と B は別ノード（旧 type 単独キーの実バグ）。"""
        db_operations.register_to_database(
            _graph("山田太郎", "Certificate",
                   {"type": "療育手帳", "grade": "A"},
                   "HAS_CERTIFICATE"),
            user_name="pytest")
        db_operations.register_to_database(
            _graph("山田太郎", "Certificate",
                   {"type": "療育手帳", "grade": "B"},
                   "HAS_CERTIFICATE"),
            user_name="pytest")

        cert_ids = store.node_ids_for_label("Certificate")
        assert len(cert_ids) == 2, (
            "同一人の等級違い Certificate が1ノードに潰れている（DRIFT-12 の実バグ）")

    def test_missing_grade_defaults_to_unknown(self, store):
        """grade 未指定は「不明」で補完される（複合キーの欠落防止・正典 §10.3）。"""
        db_operations.register_to_database(
            _graph("山田太郎", "Certificate",
                   {"type": "療育手帳"},
                   "HAS_CERTIFICATE"),
            user_name="pytest")

        cert_calls = [(q, p, nid) for q, p, nid in store.node_calls
                      if "n:Certificate" in q]
        assert cert_calls, "Certificate が書き込まれていない"
        assert all(p.get("grade") == "不明" for _, p, _ in cert_calls), \
            "grade 未指定時に「不明」が補完されていない"


class TestSharedEntitiesRemainGlobal:
    """実体共有が正しいノードはグローバル MERGE を維持する（リグレッションガード）。"""

    def test_shared_hospital_remains_single_node(self, store):
        """2クライアントが同じ病院にかかる場合、Hospital ノードは1つに共有される。"""
        db_operations.register_to_database(
            _graph("山田太郎", "Hospital", {"name": "中央病院"}, "TREATED_AT"),
            user_name="pytest")
        db_operations.register_to_database(
            _graph("佐藤花子", "Hospital", {"name": "中央病院"}, "TREATED_AT"),
            user_name="pytest")

        hospital_ids = store.node_ids_for_label("Hospital")
        assert len(hospital_ids) == 1, "実体共有すべき Hospital が複製された"


class TestScopedRegistrationPreservesBehavior:
    """スコープ化後も既存の登録セマンティクスが保たれること。"""

    def test_reregistering_same_client_ngaction_is_idempotent(self, store):
        """同一クライアントへの同名 NgAction の再登録は同一ノードに解決される。"""
        graph = _graph("山田太郎", "NgAction",
                       {"action": "大きな音", "riskLevel": "Panic"},
                       "MUST_AVOID")
        db_operations.register_to_database(graph, user_name="pytest")
        db_operations.register_to_database(graph, user_name="pytest")

        ng_ids = store.node_ids_for_label("NgAction")
        assert len(ng_ids) == 1, "同一クライアントの同名 NgAction が重複登録された"

    def test_client_child_relationship_is_created_with_properties(self, store):
        """Client→子ノードのリレーションが正式名・プロパティ付きで作成される。"""
        db_operations.register_to_database(
            _graph("山田太郎", "Certificate",
                   {"type": "療育手帳", "nextRenewalDate": "2026-09-30"},
                   "HAS_CERTIFICATE", {"status": "Active", "issuedDate": "2024-10-01"}),
            user_name="pytest")

        cert_rel_calls = store.queries_containing("HAS_CERTIFICATE")
        assert cert_rel_calls, "HAS_CERTIFICATE リレーションが作成されていない"
        # リレーションプロパティ（status 等）がいずれかの書き込みに含まれること
        flattened = json.dumps([p for _, p in cert_rel_calls],
                               ensure_ascii=False, default=str)
        assert "Active" in flattened and "issuedDate" in flattened, \
            "リレーションプロパティが書き込みに含まれていない"
