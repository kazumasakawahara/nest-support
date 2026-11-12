"""関わり（Involvement）を承認・差し戻ししたときの出力に、結ばれた機関を出す（2026-11-12 河原さん。journal 2026-11-11 の論点 5）。
DB を使わない（偽の DB）。

- show と同じ言い回し：「機関：名前（ID）」、結ばれていなければ「機関：機関未確定」。名前は資源の側から引く
- サービスの種類と終わり方も、show と同じ行があれば並べる
- 関わりのほかの承認の出力には出さない
"""
import contextlib

from nest import semantics
from tests.test_review_show_content import BASE, NGA, REC, FakeDriver, _script
from tests.test_review_show_content import INV, ORG, FakeResource

STAFF = "STF-" + "0" * 26
F = semantics.field_names()["Involvement"]
QUOTE = {"recordId": REC, "quote": "生活介護の事業所に通っていると話した。", "certainty": "Hearsay", "informantKind": "Family",
         "status": "Active"}


def _node(**kw):
    return dict(BASE, involvementId=INV, kind="ServiceProvision", howEnded="Ongoing", certainty="Hearsay", **kw)


def _decide(cmd, node, orgs, names, capsys, monkeypatch):
    from nest.gate import approve as ap
    monkeypatch.setattr(ap, cmd, lambda *a, **kw: {"ok": True, "shown": [QUOTE], "selfApproval": False, "relations": []})
    argv = [cmd, "--staff", STAFF, "--id", node.get("involvementId") or node.get("ngActionId")]
    if cmd == "reject":
        argv += ["--reason", "重複"]
    assert _script().main(argv, driver=FakeDriver(node=node, orgs=orgs), resource_driver=FakeResource(names)) == 0
    return capsys.readouterr().out


def test_approving_an_involvement_prints_the_linked_org_with_its_id(capsys, monkeypatch):
    out = _decide("approve", _node(serviceTypeName="生活介護"), [ORG], {ORG: "つばさ（架空）"}, capsys, monkeypatch)
    assert "機関：つばさ（架空）（%s）" % ORG in out and "機関未確定" not in out
    assert "%s：生活介護" % F["serviceTypeName"] in out
    assert "%s：Ongoing（%s）" % (F["howEnded"], semantics.enum_names()["howEnded"]["Ongoing"]) in out
    assert out.index("承認した") < out.index("機関：") < out.index("根拠 %s" % REC)


def test_rejecting_an_involvement_says_the_org_is_undecided(capsys, monkeypatch):
    out = _decide("reject", _node(), [], {}, capsys, monkeypatch)
    assert "機関：機関未確定" in out
    assert "%s：" % F["serviceTypeName"] not in out  # サービスの種類が無ければ、その行を出さない
    assert out.index("差し戻した") < out.index("機関：")


def test_other_labels_print_no_org_line(capsys, monkeypatch):
    node = dict(BASE, ngActionId=NGA, action="卵を食べさせる", riskLevel="LifeThreatening")
    out = _decide("approve", node, [], {}, capsys, monkeypatch)
    assert "機関：" not in out and "%s：" % F["serviceTypeName"] not in out


def test_deciding_an_involvement_opens_the_resource_side_to_read_names(monkeypatch, capsys):
    from nest import connections
    from nest.gate import approve as ap
    opened = []
    fake = {"personal": FakeDriver(node=_node(), orgs=[ORG]), "resource": FakeResource({ORG: "つばさ（架空）"})}

    @contextlib.contextmanager
    def driver(side):
        opened.append(side)
        yield fake[side]

    monkeypatch.setattr(connections, "driver", driver)
    monkeypatch.setattr(ap, "approve", lambda *a, **kw: {"ok": True, "shown": [], "selfApproval": False, "relations": []})
    assert _script().main(["approve", "--staff", STAFF, "--id", INV]) == 0
    assert opened == ["personal", "resource"]
    assert "機関：つばさ（架空）（%s）" % ORG in capsys.readouterr().out
