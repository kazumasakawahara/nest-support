"""承認の画面（scripts/review_proposals.py）に人の続柄を出す（2026-11-12 河原さんの承認。正典 v0.14 §7。台帳 G-102）。DB を使わない。

- show --id PER-… に「続柄：この人は本人 C-…… の〈続柄〉」と状態・確度、続柄の根拠の引用（未確定なら「・未確定。先に承認する」）
- 承認・差し戻しの結果に、一緒に変わった続柄を出す
"""
from nest import semantics
from tests.test_review_show_content import BASE, CODE, PER, FakeDriver, _script

REC = "REC-01BBBBBBBBBBBBBBBBBBBBBBBB"
RELATION = {"kind": "Parent", "status": "Pending", "certainty": "Hearsay", "code": CODE,
            "evidence": [{"recordId": REC, "quote": "母が電話で話した。", "certainty": "Hearsay", "informantKind": "Family",
                          "status": "Pending"}]}


def _show(relations, capsys):
    d = FakeDriver(node=dict(BASE, personId=PER))
    d.tx.relations = relations
    assert _script().main(["show", "--id", PER], driver=d) == 0
    return capsys.readouterr().out


def test_show_prints_the_relation_and_its_evidence(capsys):
    out = _show([RELATION], capsys)
    names = semantics.enum_names()
    parent = names["clientRelationKind"]["Parent"]
    assert "続柄：この人は本人 %s の%s（Parent）" % (CODE, parent) in out
    assert "Pending" in out and "Hearsay（%s）" % names["certainty"]["Hearsay"] in out
    assert "続柄の根拠 %s（確度 Hearsay・話し手 Family・未確定。先に承認する）：母が電話で話した。" % REC in out


def test_show_without_a_relation_says_so(capsys):
    out = _show([], capsys)
    assert "続柄：無い" in out


def test_the_decision_prints_the_relations_that_changed_together(capsys, monkeypatch):
    from nest.gate import approve as ap
    monkeypatch.setattr(ap, "approve", lambda *a, **kw: {"ok": True, "shown": [], "selfApproval": False,
                                                         "relations": [dict(RELATION, status="Active")]})
    assert _script().main(["approve", "--staff", "STF-" + "0" * 26, "--id", PER], driver=FakeDriver()) == 0
    out = capsys.readouterr().out
    assert "続柄も Active にした：本人 %s の%s（Parent）" % (CODE, semantics.enum_names()["clientRelationKind"]["Parent"]) in out
