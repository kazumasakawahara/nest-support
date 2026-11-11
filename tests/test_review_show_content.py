"""段階 L の確かめ（2026-11-11 河原さん）の詰まり 1・2。scripts/review_proposals.py。DB を使わない（偽の DB）。

1【B】show は、承認する対象の中身を出す：「対象の項目（列挙値は正典の表示名を添える）→ 根拠の引用」の順。
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
QUOTE = {"recordId": REC, "quote": "自宅を訪問。母と本人に会う。", "certainty": "Unspecified", "informantKind": "Agency"}


class _Rec(dict):
    def data(self):
        return dict(self)


class FakeTx:
    def __init__(self, node, rows):
        self.node, self.rows = node, rows

    def run(self, query, **params):
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
    def __init__(self, node=None, rows=()):
        self.tx = FakeTx(node, list(rows))

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
    for line in ("date：2026-11-01", "contactKind：Visit（訪問）", "situation：自宅。母と本人", "action：母と本人に会い、話を聞いた",
                 "nextAction：次回は通院に同行する（母と確認）"):
        assert line in out, line
    assert out.index("contactKind") < out.index("根拠 %s" % REC)


def test_show_prints_the_prohibition_with_the_risk_level_name(capsys):
    node = dict(BASE, ngActionId=NGA, action="卵を食べさせる", riskLevel="LifeThreatening", reason="アレルギー")
    out = _show(node, NGA, capsys)
    name = semantics.enum_names()["riskLevel"]["LifeThreatening"]
    assert "action：卵を食べさせる" in out and "riskLevel：LifeThreatening（%s）" % name in out and "reason：アレルギー" in out


def test_show_does_not_print_hidden_or_gate_managed_items(capsys):
    node = dict(BASE, personId=PER, familyName="架空", givenName="はなこ", phone="090-0000-0000", note="母の妹")
    out = _show(node, PER, capsys)
    for word in ("架空", "はなこ", "090-0000-0000", "familyName", "phone", "registeredAt", "personId"):
        assert word not in out.split("\n", 1)[1], word
    assert "note：母の妹" in out


def test_show_prints_a_paraphrased_text_but_not_the_hash(capsys):
    node = dict(BASE, recordId=REC, kind="Interview", certainty="Hearsay", informantKind="Family", quote=QUOTE["quote"],
                text="母と本人に会った（言い換え）", documentHash="0" * 64)
    out = _show(node, REC, capsys)
    assert "text：母と本人に会った（言い換え）" in out and "0" * 64 not in out
    assert "certainty：Hearsay（伝聞）" in out and "kind：Interview（聞き取り）" in out


def test_show_says_when_there_are_no_items(capsys):
    out = _show(dict(BASE, personId=PER), PER, capsys)
    assert "項目：無い" in out


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
