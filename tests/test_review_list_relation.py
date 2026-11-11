"""Claude Desktop での確かめ（2026-11-12 河原さん。C-TM2KZZ）の表示の気づき 1〜3。scripts/review_proposals.py。DB を使わない（偽の DB）。

1 list の人の行に同じ仮名を二度出さない（続柄と話した記録の両方から同じ本人に着く）
2 list の人の行に続柄を添える（提案 2026-11-12 §4）
3 人の show で出す項目が無いとき、欠けているように読める「項目：無い」を出さない。伏せているから出さないと書く
"""
from nest import semantics
from tests.test_review_show_content import BASE, CODE, PER, REC, FakeDriver, _script


def _list(rows, argv, capsys):
    assert _script().main(argv, driver=FakeDriver(rows=rows)) == 0
    return capsys.readouterr().out


def _row(**kw):
    return dict({"label": "Person", "origin": "AiExtracted", "at": "2026-11-12", "codes": [CODE, CODE], "node": {"personId": PER}}, **kw)


def test_list_names_the_client_once(capsys):
    (line,) = [l for l in _list([_row()], ["list", "--code", CODE], capsys).splitlines() if l.startswith(PER)]
    assert line.count(CODE) == 1, line


def test_list_adds_the_relation_to_a_person_line(capsys):
    rows = [_row(relations=[{"kind": "Parent", "code": CODE, "status": "Pending"}])]
    (line,) = [l for l in _list(rows, ["list"], capsys).splitlines() if l.startswith(PER)]
    name = semantics.enum_names()["clientRelationKind"]["Parent"]
    assert "続柄 %s（Parent）・Pending" % name in line, line
    assert line.count(CODE) == 1, line  # 続柄の先の本人は「本人」の欄と同じなので、仮名を繰り返さない


def test_list_says_when_a_person_has_no_relation(capsys):
    (line,) = [l for l in _list([_row(relations=[])], ["list"], capsys).splitlines() if l.startswith(PER)]
    assert "続柄 無い" in line, line


def test_list_adds_no_relation_to_other_labels(capsys):
    rows = [{"label": "Record", "origin": "AiExtracted", "at": "2026-11-12", "codes": [CODE], "node": {"recordId": REC}, "relations": []}]
    (line,) = [l for l in _list(rows, ["list"], capsys).splitlines() if l.startswith(REC)]
    assert "続柄" not in line, line


def test_show_of_a_person_with_nothing_to_show_does_not_read_as_missing(capsys):
    assert _script().main(["show", "--id", PER], driver=FakeDriver(node=dict(BASE, personId=PER, familyName="架空"))) == 0
    out = capsys.readouterr().out
    assert "項目：無い" not in out
    assert "項目：名前・かな・電話・住所・生年月日は、ここでは出さない。ほかに出す項目は無い" in out
