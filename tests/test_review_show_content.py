"""段階 L の確かめ（2026-11-11 河原さん）の詰まり 1・2。scripts/review_proposals.py。DB を使わない（偽の DB）。

1【B】show は、承認する対象の中身を出す：「対象の項目（項目は SEMANTICS の表示名。列挙値は表示名を添える）→ 根拠の引用」の順。
  伏せる項目（実名・かな・電話・住所・生年月日）と、ゲートが付ける項目（ID・状態・由来・登録日時・指紋）は出さない
2【C】list --code C-…… で本人に絞る。本人「―」の行が何かを一言で出す
"""
import pytest

from nest import semantics
from tests import doc_commands

CODE = "C-N5AE5P"
SLG = "SLG-01AAAAAAAAAAAAAAAAAAAAAAAA"
NGA = "NGA-01AAAAAAAAAAAAAAAAAAAAAAAA"
PER = "PER-01AAAAAAAAAAAAAAAAAAAAAAAA"
REC = "REC-01AAAAAAAAAAAAAAAAAAAAAAAA"
QUOTE = {"recordId": REC, "quote": "自宅を訪問。母と本人に会う。", "certainty": "Unspecified", "informantKind": "Agency", "status": "Pending"}


class _Rec(dict):
    def data(self):
        return dict(self)


class FakeTx:
    def __init__(self, node, rows, orgs=()):
        self.node, self.rows, self.orgs, self.relations = node, rows, list(orgs), []

    def run(self, query, **params):
        if "RELATED_TO]->(c:Client)" in query:  # 2026-11-12：人の続柄（台帳 G-102）
            return [_Rec(r) for r in self.relations]
        if "HAS_INVOLVEMENT]->(:Involvement" in query:
            return [_Rec(orgId=o) for o in self.orgs]
        if "RETURN n AS node" in query:
            return [_Rec(node=self.node)] if self.node is not None else []
        if "EVIDENCED_BY]->(e:Record)" in query:
            return [_Rec(QUOTE)]
        if "action: 'Reject'" in query:
            return []
        if "n.status = 'Pending'" in query:
            return [_Rec(r) for r in self.rows]
        raise AssertionError(query)


class FakeDriver:
    def __init__(self, node=None, rows=(), orgs=()):
        self.tx = FakeTx(node, list(rows), orgs)

    def session(self, **kw):
        driver = self

        class S:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute_read(self, fn, *args):
                return fn(driver.tx, *args)
        return S()


def _script():
    return doc_commands.load("review_proposals.py")


def _show(node, target, capsys):
    assert _script().main(["show", "--id", target], driver=FakeDriver(node=node)) == 0
    return capsys.readouterr().out


BASE = {"status": "Pending", "origin": "AiExtracted", "registeredAt": "2026-11-11T10:00:00+09:00"}


# ---- 1 show ----

def test_show_prints_the_support_log_items_before_the_quote(capsys):
    node = dict(BASE, supportLogId=SLG, date="2026-11-01", contactKind="Visit", situation="自宅。母と本人",
                action="母と本人に会い、話を聞いた", nextAction="次回は通院に同行する（母と確認）")
    out = _show(node, SLG, capsys)
    f = semantics.field_names()["SupportLog"]
    for key, value in (("date", "2026-11-01"), ("contactKind", "Visit（訪問）"), ("situation", "自宅。母と本人"),
                       ("action", "母と本人に会い、話を聞いた"), ("nextAction", "次回は通院に同行する（母と確認）")):
        assert "  %s：%s" % (f[key], value) in out, key
    assert out.index(f["contactKind"]) < out.index("根拠 %s" % REC)
    assert "contactKind" not in out and "nextAction" not in out


def test_show_prints_the_prohibition_with_the_risk_level_name(capsys):
    node = dict(BASE, ngActionId=NGA, action="卵を食べさせる", riskLevel="LifeThreatening", reason="アレルギー")
    out = _show(node, NGA, capsys)
    name, f = semantics.enum_names()["riskLevel"]["LifeThreatening"], semantics.field_names()["NgAction"]
    assert "%s：卵を食べさせる" % f["action"] in out and "%s：LifeThreatening（%s）" % (f["riskLevel"], name) in out
    assert "%s：アレルギー" % f["reason"] in out


def test_show_does_not_print_hidden_or_gate_managed_items(capsys):
    node = dict(BASE, personId=PER, familyName="架空", givenName="はなこ", phone="090-0000-0000", note="母の妹")
    out = _show(node, PER, capsys)
    for word in ("架空", "はなこ", "090-0000-0000", "familyName", "phone", "registeredAt", "personId"):
        assert word not in out.split("\n", 1)[1], word
    assert "%s：母の妹" % semantics.field_names()["Person"]["note"] in out


def test_show_prints_a_paraphrased_text_but_not_the_hash(capsys):
    node = dict(BASE, recordId=REC, kind="Interview", certainty="Hearsay", informantKind="Family", quote=QUOTE["quote"],
                text="母と本人に会った（言い換え）", documentHash="0" * 64)
    out = _show(node, REC, capsys)
    f = semantics.field_names()["Record"]
    assert "%s：母と本人に会った（言い換え）" % f["text"] in out and "0" * 64 not in out
    assert "%s：Hearsay（伝聞）" % f["certainty"] in out and "%s：Interview（聞き取り）" % f["kind"] in out
    assert "先に承認" not in out  # 承認の対象そのものの記録には付けない


def test_show_says_when_there_are_no_items(capsys):
    out = _show(dict(BASE, personId=PER), PER, capsys)
    # 2026-11-12 河原さん：「項目：無い」は欠けているように読めるので、伏せているから出さないと書く（tests/test_review_list_relation.py）
    assert "ほかに出す項目は無い" in out


def test_show_of_a_missing_id_stops(capsys):
    assert _script().main(["show", "--id", SLG], driver=FakeDriver(node=None)) == 1


# ---- 2 list --code ----

ROWS = [{"label": "Record", "origin": "AiExtracted", "at": "2026-11-01", "codes": ["C-ZZZZZZ"], "node": {"recordId": REC}},
        {"label": "SupportLog", "origin": "AiExtracted", "at": "2026-11-02", "codes": [CODE], "node": {"supportLogId": SLG}},
        {"label": "Person", "origin": "AiExtracted", "at": "2026-11-03", "codes": [], "node": {"personId": PER}}]


def _list(argv, capsys):
    assert _script().main(argv, driver=FakeDriver(rows=ROWS)) == 0
    return capsys.readouterr().out


def test_list_by_code_shows_only_that_client(capsys):
    out = _list(["list", "--code", CODE], capsys)
    assert SLG in out and REC not in out and PER not in out
    assert "未確定 1 件" in out and CODE in out.splitlines()[0]


def test_list_without_code_shows_all_and_explains_the_dash(capsys):
    out = _list(["list"], capsys)
    assert REC in out and SLG in out and PER in out
    (line,) = [l for l in out.splitlines() if l.startswith("本人「―」")]
    assert "どの本人にも結ばれていない" in line


def test_a_malformed_code_stops_before_the_db(capsys):
    class NoDB:
        def __getattr__(self, name):
            raise AssertionError("DB に触れた")
    assert _script().main(["list", "--code", "はると"], driver=NoDB()) == 1
    assert "止めた" in capsys.readouterr().out


def test_the_manual_checks_with_the_code():
    assert "uv run python scripts/review_proposals.py list --code C-……" in doc_commands.all_lines()
    t = doc_commands.DOC.read_text(encoding="utf-8")
    c = t[t.index("### (c) 未確定で入ったことを確かめる"):]
    c = c[:c.index("\n### ")]
    assert "list --code C-……" in c and "「―」" in c


def test_show_marks_evidence_that_is_still_pending(capsys):
    """2026-11-11：根拠の記録が未確定かどうかを、承認の前に見えるようにする。未確定なら先に承認する。"""
    node = dict(BASE, ngActionId=NGA, action="卵を食べさせる", riskLevel="LifeThreatening")
    out = _show(node, NGA, capsys)
    (line,) = [l for l in out.splitlines() if l.strip().startswith("根拠 %s" % REC)]
    assert "未確定" in line and "先に承認" in line


def test_the_manual_says_to_approve_the_evidence_first():
    t = doc_commands.DOC.read_text(encoding="utf-8")
    sec = t[t.index("### 書き込みの案を点検して承認する"):]
    sec = sec[:sec.index("\n## ")]
    assert "根拠の記録を先に承認" in sec and "未確定。先に承認する" in sec and "止まります" in sec


# ---- 2026-11-11：関わりに、サービスの種類と、結ばれた機関の名前（無ければ「機関未確定」）を出す ----
INV = "INV-01AAAAAAAAAAAAAAAAAAAAAAAA"
ORG = "ORG-01AAAAAAAAAAAAAAAAAAAAAAAA"


class FakeResource:
    def __init__(self, names):
        self.names = names

    def execute_query(self, query, params=None, **kw):
        class Out:
            records = [{"orgId": o, "name": n} for o, n in self.names.items() if o in (params or {}).get("ids", [])]
        return Out()


def _show_inv(orgs, names, capsys):
    node = dict(BASE, involvementId=INV, kind="ServiceProvision", howEnded="Unknown", certainty="Inference",
                serviceTypeName="生活介護")
    rc = _script().main(["show", "--id", INV], driver=FakeDriver(node=node, orgs=orgs), resource_driver=FakeResource(names))
    assert rc == 0
    return capsys.readouterr().out


def test_show_prints_the_service_type_and_the_linked_org_name(capsys):
    out = _show_inv([ORG], {ORG: "つばさ（架空）"}, capsys)
    assert "%s：生活介護" % semantics.field_names()["Involvement"]["serviceTypeName"] in out
    assert "機関：つばさ（架空）" in out and "機関未確定" not in out
    assert out.index("機関：") < out.index("根拠 %s" % REC)


def test_show_says_the_org_is_undecided_when_nothing_is_linked(capsys):
    out = _show_inv([], {}, capsys)
    assert "機関：機関未確定" in out


def test_show_of_other_labels_has_no_org_line(capsys):
    out = _show(dict(BASE, ngActionId=NGA, action="卵を食べさせる", riskLevel="LifeThreatening"), NGA, capsys)
    assert "機関：" not in out


def test_show_prints_the_certainty_of_an_involvement(capsys):
    """2026-11-11：名前のある関わりは根拠の記録の確度を写す。show の確度の行は今どおり出る"""
    node = dict(BASE, involvementId=INV, kind="ServiceProvision", howEnded="Unknown", certainty="Hearsay")
    assert _script().main(["show", "--id", INV], driver=FakeDriver(node=node), resource_driver=FakeResource({})) == 0
    out = capsys.readouterr().out
    assert "%s：Hearsay（伝聞）" % semantics.field_names()["Involvement"]["certainty"] in out


def test_show_prints_an_ongoing_involvement(capsys):
    """2026-11-12：終わり方の行は今の表示のまま「終わり方：Ongoing（続いている）」と出る"""
    node = dict(BASE, involvementId=INV, kind="ServiceProvision", howEnded="Ongoing", certainty="Unspecified")
    assert _script().main(["show", "--id", INV], driver=FakeDriver(node=node), resource_driver=FakeResource({})) == 0
    assert "%s：Ongoing（続いている）" % semantics.field_names()["Involvement"]["howEnded"] in capsys.readouterr().out
