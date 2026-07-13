"""
MERGE_KEYS の正典整合テスト（DRIFT-12 の再発防止）。

正典 = SCHEMA_CONVENTION §10.3（Certificate 複合キー）と SEMANTIC_MODEL
ENT-16（CareRole per-client 則）/ ENT-24（Review 追記のみ則）。
「MERGE_KEYS に無いことが正しい」ラベルは、その不在をテストで表明する
（うっかり追加すると安全則が壊れるため）。
"""

from lib.db_operations import CLIENT_SCOPED_LABELS, MERGE_KEYS
from lib.schema_validator import VALID_NODE_LABELS


class TestMergeKeysCanonConformance:
    def test_certificate_uses_composite_key(self):
        """正典 §10.3: 療育手帳 A と B は別ノード（type 単独キーは DRIFT-12 の実バグ）。"""
        assert MERGE_KEYS["Certificate"] == ["type", "grade"]

    def test_new_labels_have_canonical_keys(self):
        assert MERGE_KEYS["Doctor"] == ["name"]
        assert MERGE_KEYS["Relative"] == ["name"]
        assert MERGE_KEYS["Identity"] == ["name", "dob"]

    def test_never_merge_labels_are_absent(self):
        """常時 CREATE が正しいラベル。無いことが正しい（追加してはならない）。

        - Review: 追記のみ（ENT-24）。MERGE は確認履歴の積み上げを壊す
        - CareRole: per-client 則（ENT-16）。親が Relative のためスコープ機構にも乗らない
        - ProviderFeedback: feedbackId 欠落時に登録ごと落ちるのを避ける
        """
        for label in ("Review", "CareRole", "ProviderFeedback"):
            assert label not in MERGE_KEYS, \
                f"{label} は MERGE してはならない（常時 CREATE が正）"

    def test_relative_is_client_scoped(self):
        """Relative の name グローバル MERGE は別クライアントの同姓同名家族を収斂させる。"""
        assert "Relative" in CLIENT_SCOPED_LABELS

    def test_all_labels_exist_in_guardian(self):
        """MERGE_KEYS / CLIENT_SCOPED_LABELS のラベルはすべて Guardian の正規ラベル。"""
        unknown = (set(MERGE_KEYS) | set(CLIENT_SCOPED_LABELS)) - set(VALID_NODE_LABELS)
        assert not unknown, f"Guardian に無いラベル: {sorted(unknown)}"

    def test_client_scoped_labels_have_merge_keys(self):
        """スコープ対象は MERGE 前提（キーが無いと常に CREATE フォールバックになる）。"""
        missing = set(CLIENT_SCOPED_LABELS) - set(MERGE_KEYS)
        assert not missing, f"MERGE_KEYS の無いスコープ対象: {sorted(missing)}"
