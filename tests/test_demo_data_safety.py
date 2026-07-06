"""
デモデータの投入・削除が実データを破壊しないことを検証するテスト（P0-7）。

背景（バグ）:
  installer/demo-data.cypher は `MERGE (ng:NgAction {action:'...'}) SET ng.isDemo=true`
  のようにグローバル MERGE を使っていた。同じ action/name を持つ実ノードが既にあると
  MERGE がそれにマッチし、実ノードに isDemo=true を付与してしまう。その後
  load-demo-data.sh の削除処理 `MATCH (n) WHERE n.isDemo = true DETACH DELETE n` が、
  汚染された実データまで削除してしまう。

修正:
  すべてのデモノードの MERGE キーに一意な demoId を含める。demoId を持たない実ノードには
  決してマッチせず、削除も `WHERE n.demoId IS NOT NULL` 基準に統一する。

このテストは実 Neo4j には接続せず、Neo4j の MERGE 一致セマンティクスを Python 上で
模擬する（FakeGraph）。加えて demo-data.cypher / load-demo-data.sh を静的にパースし、
demoId 化と削除基準の統一を検証する。
"""

import re
from pathlib import Path

import pytest

INSTALLER_DIR = Path(__file__).resolve().parent.parent / "installer"
DEMO_CYPHER = INSTALLER_DIR / "demo-data.cypher"
LOAD_SH = INSTALLER_DIR / "load-demo-data.sh"
LOAD_PS1 = INSTALLER_DIR / "load-demo-data.ps1"


# ─────────────────────────────────────────────────────────────
# Neo4j MERGE 一致セマンティクスの模擬
# ─────────────────────────────────────────────────────────────
class FakeNode:
    def __init__(self, label, props):
        self.label = label
        self.props = dict(props)


class FakeGraph:
    """MERGE の「キー一致」セマンティクスをノード単位で再現する代役。

    Neo4j の `MERGE (n:Label {k1:v1, k2:v2})` は、Label を持ち、指定した全プロパティが
    等しいノードにマッチする。マッチが無ければ新規作成する。実ノードが demoId を
    持たない限り、demoId をキーに含むデモ MERGE は決して実ノードにマッチしない。
    """

    def __init__(self):
        self.nodes = []

    def add_real_node(self, label, props):
        n = FakeNode(label, props)
        self.nodes.append(n)
        return n

    def merge_node(self, label, merge_key, set_props=None):
        for n in self.nodes:
            if n.label == label and all(
                n.props.get(k) == v for k, v in merge_key.items()
            ):
                if set_props:
                    n.props.update(set_props)
                return n, False  # matched existing
        props = dict(merge_key)
        if set_props:
            props.update(set_props)
        n = FakeNode(label, props)
        self.nodes.append(n)
        return n, True  # created new

    def delete_where_demoId_not_null(self):
        self.nodes = [n for n in self.nodes if n.props.get("demoId") is None]

    def count(self, label=None):
        if label is None:
            return len(self.nodes)
        return sum(1 for n in self.nodes if n.label == label)


class TestDemoLoadDoesNotPolluteRealData:
    """demoId をキーに含めることで、実ノードが汚染されないこと。"""

    ACTION = "突然大きな声で話しかける"

    def test_demo_load_creates_separate_node_from_real(self):
        g = FakeGraph()
        real = g.add_real_node("NgAction", {"action": self.ACTION, "riskLevel": "Discomfort"})

        # デモ投入: demoId をキーに含む MERGE
        demo, created = g.merge_node(
            "NgAction",
            {"action": self.ACTION, "demoId": "demo-ng-1"},
            {"isDemo": True, "riskLevel": "Panic"},
        )

        assert created is True, "demoId 付き MERGE が実ノードにマッチしてしまった"
        assert g.count("NgAction") == 2, "デモノードが実ノードと別に作られていない"
        # 実ノードは一切汚染されない
        assert "demoId" not in real.props
        assert "isDemo" not in real.props
        assert real.props["riskLevel"] == "Discomfort"

    def test_delete_by_demoId_preserves_real_node(self):
        g = FakeGraph()
        real = g.add_real_node("NgAction", {"action": self.ACTION, "riskLevel": "Discomfort"})
        g.merge_node(
            "NgAction",
            {"action": self.ACTION, "demoId": "demo-ng-1"},
            {"isDemo": True, "riskLevel": "Panic"},
        )

        g.delete_where_demoId_not_null()

        assert g.count() == 1, "デモ削除後にノード数が想定と異なる"
        assert g.nodes[0] is real, "削除で実ノードが消えた（デモだけ残った）"
        assert "demoId" not in g.nodes[0].props

    def test_reload_is_idempotent(self):
        g = FakeGraph()
        g.add_real_node("NgAction", {"action": self.ACTION})
        for _ in range(3):
            g.merge_node(
                "NgAction",
                {"action": self.ACTION, "demoId": "demo-ng-1"},
                {"isDemo": True},
            )
        assert g.count("NgAction") == 2, "デモ再投入でノードが重複した"


class TestOldGlobalMergeWasUnsafe:
    """回帰ドキュメント: demoId なしのグローバル MERGE は実ノードを汚染・削除する。"""

    ACTION = "突然大きな声で話しかける"

    def test_old_approach_pollutes_and_deletes_real_node(self):
        g = FakeGraph()
        real = g.add_real_node("NgAction", {"action": self.ACTION, "riskLevel": "Discomfort"})

        # 旧: demoId を含まないグローバル MERGE → 実ノードにマッチしてしまう
        _, created = g.merge_node(
            "NgAction", {"action": self.ACTION}, {"isDemo": True}
        )
        assert created is False, "前提が崩れている（旧 MERGE は実ノードにマッチするはず）"
        assert real.props.get("isDemo") is True, "実ノードが isDemo で汚染される（旧バグ）"

        # 旧削除基準 isDemo=true では実ノードまで消える
        g.nodes = [n for n in g.nodes if n.props.get("isDemo") is not True]
        assert g.count() == 0, "旧基準では汚染された実ノードが削除される（P0-7 の被害）"


# ─────────────────────────────────────────────────────────────
# demo-data.cypher / load スクリプトの静的検証
# ─────────────────────────────────────────────────────────────
def _split_statements(cypher_text):
    lines = []
    for line in cypher_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped == "":
            continue
        lines.append(line)
    joined = "\n".join(lines)
    return [s for s in joined.split(";") if s.strip()]


# ラベル付きプロパティノードパターン: (var:Label {  ... }
_LABELED_NODE_RE = re.compile(r"\(\s*\w+\s*:\s*\w+\s*\{")


class TestDemoCypherIsDemoIdScoped:
    def test_every_labeled_node_statement_contains_demoId(self):
        text = DEMO_CYPHER.read_text(encoding="utf-8")
        offenders = []
        for stmt in _split_statements(text):
            if _LABELED_NODE_RE.search(stmt) and "demoId" not in stmt:
                offenders.append(stmt.strip()[:80])
        assert not offenders, (
            "demoId を含まないラベル付きノードパターンが残っている:\n"
            + "\n".join(offenders)
        )

    def test_uses_merge_not_bare_create_for_demo_nodes(self):
        """CREATE (var:Label {...}) の裸ノード作成が残っていない（再実行の冪等性）。"""
        text = DEMO_CYPHER.read_text(encoding="utf-8")
        bare_create = re.findall(r"CREATE\s*\(\s*\w+\s*:\s*\w+\s*\{", text)
        assert not bare_create, (
            "CREATE による裸のノード作成が残っている（demoId MERGE に置換すべき）: "
            + str(bare_create)
        )


class TestLoadShDeletesByDemoId:
    def test_delete_uses_demoId_not_null(self):
        text = LOAD_SH.read_text(encoding="utf-8")
        assert "demoId IS NOT NULL" in text, "削除が demoId 基準になっていない"

    def test_no_isDemo_based_delete(self):
        text = LOAD_SH.read_text(encoding="utf-8")
        assert not re.search(r"isDemo\s*=\s*true\s+DETACH DELETE", text), (
            "isDemo=true 基準の DETACH DELETE が残っている（実データ破壊の原因）"
        )

    def test_has_real_data_guard(self):
        text = LOAD_SH.read_text(encoding="utf-8")
        assert "demoId IS NULL" in text, (
            "投入前ガード（実データ検出）が実装されていない"
        )


class TestLoadPs1DeletesByDemoId:
    def test_delete_uses_demoId_not_null(self):
        text = LOAD_PS1.read_text(encoding="utf-8")
        assert "demoId IS NOT NULL" in text, "PS1 削除が demoId 基準になっていない"

    def test_no_isDemo_based_delete(self):
        text = LOAD_PS1.read_text(encoding="utf-8")
        assert not re.search(r"isDemo\s*=\s*true\s+DETACH DELETE", text), (
            "PS1 に isDemo=true 基準の DETACH DELETE が残っている"
        )

    def test_has_real_data_guard(self):
        text = LOAD_PS1.read_text(encoding="utf-8")
        assert "demoId IS NULL" in text, "PS1 に投入前ガードが実装されていない"
