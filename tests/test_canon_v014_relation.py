"""正典 v0.14：新しい人と本人との続柄（2026-11-12 河原さんの承認。提案 docs/proposals/2026-11-12-relation-of-new-person.md。台帳 G-102）。

- SCHEMA §7 の二か所と §4.3 の一行は提案文 §3 の文言のまま。版は v0.14。機械検証ブロックの version は 0.5 のまま
- ChangeProposal（ADR-002）は v0.15 に送る（確認点 L-0 の決めごと 12 の読み替え。台帳と提案文に記録）
- SEMANTICS SEM-REC-06 は提案文 §3 の文言と、語の一覧に語を足すのは台帳への記録で足りる一行。語の一覧（入口の点検が読む）
"""
from pathlib import Path

from nest import canon

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "docs" / "SCHEMA.md").read_text(encoding="utf-8")
SEMANTICS = (ROOT / "docs" / "SEMANTICS.md").read_text(encoding="utf-8")
LEDGER = (ROOT / "docs" / "gray-decisions.md").read_text(encoding="utf-8")
PROPOSAL = (ROOT / "docs" / "proposals" / "2026-11-12-relation-of-new-person.md").read_text(encoding="utf-8")

S7_NEW = ("- AI 由来の `RELATED_TO` は、同じ依頼で作る AI 由来の新しい `Person` からだけ張れる。`status` はゲートが `Pending` にする。"
          "その `Person` の承認で一緒に `Active`、却下で一緒に `Inactive` になり、AuditLog を残す。関係だけを承認・却下する操作は無い")
S7_APPROVAL = ("- 承認の操作は、そのノードの根拠の `Record.quote` を並べて見せてから行う。AI 由来のノードをまとめて一括で承認しない"
               "（一回の操作で一つのノード。そのノードから張った未確定の `RELATED_TO` は一緒に変わる）。`Person` の承認では、"
               "未確定の `RELATED_TO` の `kind` と、その根拠（`evidenceRecordIds`）の記録の引用も見せる")
S43_LINE = ("- 同じ依頼の中の記録を根拠にするときは、依頼の `evidenceRecordIds` に記録の名札（ref）を書き、"
            "ゲートが書くときに発番した ID に置き換える")
REC06 = [
    "- AI が案に出す新しい人（`Person`）に、本人との続柄（`RELATED_TO.kind`）を書けるのは、原文に続柄が書いてあるときだけ"
    "（「母」「姉」「主治医」「近所の人」）。推し量って書かない",
    "- 案に書ける値は、親族の 8 つ（`Parent`・`Child`・`Spouse`・`Partner`・`Sibling`・`Grandparent`・`Grandchild`・`OtherRelative`）"
    "と `PrimaryDoctor`・`Neighbor`。`KeyPerson`・`Helper`・`OtherSupporter` は判断や役割の評価を含むので案に書けず、入口の点検が止める。"
    "`KeyPerson` は職員が決める",
    "- 根拠は、その続柄が読める引用の記録（同じ案の事実の `Record`）。確度は根拠の記録の確度を写し、それより強くしない",
    "- 新しい人を作る前に、照会口で既にいる人の続柄を読む。同じ続柄の人がいれば、同じ人として結ぶかを職員に尋ねる。"
    "続柄が同じでも同じ人とは決めない（D8）",
    "- 既にいる人に、後から続柄を足す道は今は無い",
    "- 続柄の語の一覧（下の表）に語を足すのは、台帳に記録すれば足りる。値を足す・値の意味を変えるのは河原さんの承認による",
]


def _section(text, head):
    i = text.index(head)
    j = text.find("\n## ", i + 1)
    k = text.find("\n### ", i + 1)
    ends = [x for x in (j, k) if x > 0]
    return text[i:min(ends)] if ends else text[i:]


def test_schema_is_v014_and_the_machine_version_stays():
    assert SCHEMA.splitlines()[0] == "# nest-support スキーマ正典 — v0.14"
    assert canon.load(ROOT / "docs" / "SCHEMA.md")["version"] == "0.5"
    history = [l for l in SCHEMA.splitlines() if l.startswith("- v0.14（2026-11-12）")]
    assert len(history) == 1 and "G-102" in history[0] and "v0.15" in history[0]


def test_section_7_has_the_two_texts():
    s7 = _section(SCHEMA, "## 7. 承認")
    lines = s7.splitlines()
    first = "- ゲートが書く事実・関係・記録は、AI 由来なら `Pending`（§4.1）"
    assert lines[lines.index(first) + 1] == S7_NEW
    assert S7_APPROVAL in lines
    assert "AI 由来のノードをまとめて一括で承認しない（一回の操作で一つのノード）\n" not in s7


def test_section_43_has_the_line_after_the_evidence_ids_rule():
    lines = SCHEMA.splitlines()
    i = next(n for n, l in enumerate(lines) if l.startswith("- `RELATED_TO` は関係そのものが事実なので"))
    assert lines[i + 1] == S43_LINE


def test_semantics_rec_06():
    s = _section(SEMANTICS, "### SEM-REC-06")
    head = s.splitlines()[0]
    assert head.startswith("### SEM-REC-06 新しい人と本人との続柄（2026-11-12 河原さん。台帳 G-102")
    for line in REC06:
        assert line in s.splitlines(), line


def test_the_ledger_and_the_proposal_record_the_version_shift():
    (row,) = [l for l in LEDGER.splitlines() if l.startswith("| G-102 |")]
    assert "v0.14" in row and "v0.15" in row and "ChangeProposal" in row and "決めごと 12" in row
    assert "v0.15" in PROPOSAL and "決めごと 12" in PROPOSAL and "可（2026-11-12" in PROPOSAL
