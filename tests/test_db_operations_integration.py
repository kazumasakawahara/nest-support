"""N-17：ゲートを通らない書き込みの道（register_to_database）を閉じた。補正しない・書かない。

2026-11-05 河原さんの判断：新しい DB が動く時点で、ゲートを通らない書き込みの道を残さない。
書き込みはゲート（nest/gate。書き込みは N-20）だけを通る。それまで field-ui の支援記録の入力と
insight-engine の昇格は書けない。

書き換える前のこのファイルは「Guardian Layer の補正（PROHIBITED→MUST_AVOID、risk_level→riskLevel）が
DB に届くこと」「AuditLog を作ること」「許可リスト外を飛ばして他を書くこと」を確かめていた。
test_merge_scoping.py（クライアントごとの MERGE）と test_merge_keys_canon.py（名前で MERGE する鍵）は
名前で同定する書き方そのものを確かめていたので、ここに畳んだ（ADR D8・N-16：人は名前で同定しない）。
"""
import copy

import pytest
from unittest.mock import patch

from lib import db_operations

OLD_GRAPHS = {
    # 廃止のリレーション名（前は MUST_AVOID に直して書いていた）
    "deprecated-relationship": {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {"name": "架空太郎"}},
            {"temp_id": "ng1", "label": "NgAction",
             "properties": {"action": "後ろから声をかける", "riskLevel": "Panic"}},
        ],
        "relationships": [{"source_temp_id": "c1", "target_temp_id": "ng1", "type": "PROHIBITED", "properties": {}}],
    },
    # snake_case（前は camelCase に直して書いていた）
    "snake-case": {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {"name": "架空花子"}},
            {"temp_id": "ng1", "label": "NgAction", "properties": {"action": "大きな音", "risk_level": "LifeThreatening"}},
        ],
        "relationships": [],
    },
    # 列挙の別名（前は 高→LifeThreatening に直して書いていた）
    "risk-alias": {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {"name": "架空次郎"}},
            {"temp_id": "ng1", "label": "NgAction", "properties": {"action": "急な予定変更", "riskLevel": "高"}},
        ],
        "relationships": [],
    },
    # 知らないラベル・知らないリレーション（前は飛ばして残りを書いていた）
    "unknown-names": {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {"name": "架空三郎"}},
            {"temp_id": "e1", "label": "利用者", "properties": {"name": "架空"}},
        ],
        "relationships": [{"source_temp_id": "e1", "target_temp_id": "c1", "type": "EVIL_REL", "properties": {}}],
    },
    # 同じ名前の禁忌を二人に（前はクライアントごとに MERGE していた）
    "same-name-two-clients": {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {"name": "架空A"}},
            {"temp_id": "c2", "label": "Client", "properties": {"name": "架空B"}},
            {"temp_id": "ng1", "label": "NgAction", "properties": {"action": "大きな音", "riskLevel": "Panic"}},
        ],
        "relationships": [{"source_temp_id": "c1", "target_temp_id": "ng1", "type": "MUST_AVOID", "properties": {}},
                          {"source_temp_id": "c2", "target_temp_id": "ng1", "type": "MUST_AVOID", "properties": {}}],
    },
    # nodes の無いグラフ
    "no-nodes": {"relationships": []},
}


@pytest.fixture
def no_db():
    """DB に触れたら落とす。"""
    def _touch(*a, **k):
        raise AssertionError("DB に触れた")
    with patch("lib.db_operations.get_driver", side_effect=_touch), \
         patch("lib.db_operations.run_query", side_effect=_touch), \
         patch("lib.db_operations.execute_write", side_effect=_touch):
        yield


@pytest.mark.parametrize("name", sorted(OLD_GRAPHS))
def test_register_to_database_refuses_without_fixing_or_writing(no_db, name):
    graph = OLD_GRAPHS[name]
    before = copy.deepcopy(graph)
    result = db_operations.register_to_database(graph, user_name="pytest")
    assert result["status"] == "error"
    assert "ゲート" in result["message"]
    assert result["count"] == 0
    assert graph == before  # 渡したものを直さない


def test_name_based_merge_helpers_are_gone():
    for name in ("MERGE_KEYS", "CLIENT_SCOPED_LABELS", "_register_graph_tx", "_build_parent_link",
                 "_rebuild_support_log_chain", "_audit_node_creation", "create_audit_log"):
        assert not hasattr(db_operations, name), name


def test_guardian_layer_is_retired():
    with pytest.raises(ModuleNotFoundError):
        import lib.schema_validator  # noqa: F401


def test_insight_engine_promotion_cannot_write_until_the_gate(no_db):
    """insight-engine の昇格（CarePreference）は N-20 まで書けない。断りを返すだけ。"""
    import lib.insight_engine as ie
    result = ie.promote_to_care_preference("架空太郎", "入浴", "声をかけてから始める")
    assert result["status"] == "error" and "ゲート" in result["message"]
    assert "N-20" in ie.promote_to_care_preference.__doc__
