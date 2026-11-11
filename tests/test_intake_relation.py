"""新しい人と本人との続柄を案に書く（2026-11-12 河原さんの承認。SEMANTICS SEM-REC-06。台帳 G-102）。入口の点検。DB を使わない。

- newPeople の人に任意の relation: {"kind", "quote"}。kind は親族の 8 つと PrimaryDoctor・Neighbor だけ
- quote は案の事実の引用のどれか。原文の続柄の語を、長い語を先に当てて確かめる（「祖母」を Parent にしない）
- 止まったときの理由に、止まった語と「続柄を書かない案で出し直せる。その人は本人と結ばれないので、後で結ぶ必要がある」を出す
- 依頼に RELATED_TO（新しい人 → 本人、evidenceRecordIds は記録の名札、確度は根拠の事実の確度）が入る
"""
import pytest

from nest import semantics
from nest.gate import intake

CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
REDO = "続柄を書かない案で出し直せる。その人は本人と結ばれないので、後で結ぶ必要がある"


def _proposal(quote, kind, mark="【伝聞】", ref="mother", told=True):
    fact = {"quote": quote, "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Family"}
    if told:
        fact["toldBy"] = ref
    p = {"documentKind": "OwnCaseRecord", "clientId": CLIENT, "newPeople": [{"ref": ref, "relation": {"kind": kind, "quote": quote}}],
         "facts": [fact]}
    original = "架空の面接記録（例）\n2026-11-02 電話\n" + quote + mark + "\n"
    return p, original


def _check(quote, kind, **kw):
    p, original = _proposal(quote, kind, **kw)
    return intake.check(p, original, ACTOR, "req-rel")


def _related(rep):
    return [r for r in rep["request"]["relationships"] if r["type"] == "RELATED_TO"]


ALLOWED = [("母が電話で話した。", "Parent"), ("姉から電話があった。", "Sibling"), ("息子が来た。", "Child"),
           ("妻が話した。", "Spouse"), ("内縁の夫が話した。", "Partner"), ("祖母が話した。", "Grandparent"),
           ("孫が来た。", "Grandchild"), ("叔母が話した。", "OtherRelative"), ("主治医が話した。", "PrimaryDoctor"),
           ("近所の人が話した。", "Neighbor")]


@pytest.mark.parametrize("quote, kind", ALLOWED)
def test_the_ten_values_pass_with_a_matching_word(quote, kind):
    rep = _check(quote, kind)
    assert rep["ok"], rep["errors"]
    (rel,) = _related(rep)
    assert rel["from"] == "mother" and rel["to"] == {"label": "Client", "id": CLIENT}
    assert rel["properties"] == {"kind": kind, "certainty": "Hearsay", "evidenceRecordIds": ["fact-1"]}


@pytest.mark.parametrize("kind", ["KeyPerson", "Helper", "OtherSupporter"])
def test_judgement_values_stop(kind):
    rep = _check("母が電話で話した。", kind)
    assert not rep["ok"]
    assert any(kind in e and "案に書けない" in e and REDO in e for e in rep["errors"]), rep["errors"]


@pytest.mark.parametrize("kind", ["Mother", "親", None, 1])
def test_values_outside_the_canon_stop(kind):
    rep = _check("母が電話で話した。", kind)
    assert not rep["ok"] and any("relation" in e and REDO in e for e in rep["errors"]), rep["errors"]


@pytest.mark.parametrize("word", ["祖母", "叔母", "伯母", "義母", "義姉"])
def test_a_longer_word_that_contains_another_relation_is_read_first(word):
    """2026-11-12 河原さんの条件 1：「祖母」を Parent と書いた案は通らない（「母」を含む語を先に見て、残りで判定する）"""
    rep = _check("%sが電話で話した。" % word, "Parent" if word != "義姉" else "Sibling")
    assert not rep["ok"]
    (err,) = [e for e in rep["errors"] if "続柄" in e and "語" in e]
    assert word in err and REDO in err


def test_a_quote_without_a_relation_word_stops():
    rep = _check("電話で話を聞いた。", "Parent", told=False, ref="caller")
    assert not rep["ok"]
    assert any("続柄の語が引用に無い" in e and REDO in e for e in rep["errors"]), rep["errors"]


def test_a_relation_quote_must_be_one_of_the_facts():
    p, original = _proposal("母が電話で話した。", "Parent")
    p["newPeople"][0]["relation"]["quote"] = "母が来た。"
    rep = intake.check(p, original + "母が来た。\n", ACTOR, "req-rel")
    assert not rep["ok"] and any("relation" in e and "事実の引用" in e for e in rep["errors"]), rep["errors"]


def test_relation_takes_only_kind_and_quote():
    p, original = _proposal("母が電話で話した。", "Parent")
    p["newPeople"][0]["relation"]["certainty"] = "Confirmed"
    rep = intake.check(p, original, ACTOR, "req-rel")
    assert not rep["ok"] and any("certainty" in e and "項目は無い" in e for e in rep["errors"]), rep["errors"]


def test_the_certainty_is_copied_from_the_record_and_never_raised():
    rep = _check("母が電話で話した。", "Parent", mark="")
    p, _ = _proposal("母が電話で話した。", "Parent", mark="")
    assert not rep["ok"]  # 案の事実は Hearsay、原文に印が無い → 事実の確度で止まる（確度は事実の側で決まる）
    p["facts"][0]["certainty"] = "Unspecified"
    rep = intake.check(p, "架空の面接記録（例）\n2026-11-02 電話\n母が電話で話した。\n", ACTOR, "req-rel")
    assert rep["ok"], rep["errors"]
    assert _related(rep)[0]["properties"]["certainty"] == "Unspecified"


def test_a_person_with_only_a_relation_counts_as_tied():
    """SEM-REC-04：新しい人は TOLD_BY・CONCERNS・RELATED_TO のどれかで結ぶ。続柄だけでも使われている"""
    p, original = _proposal("母のことを姉が話した。", "Parent", told=False)
    p["newPeople"].append({"ref": "sister"})
    p["facts"][0]["toldBy"] = "sister"
    rep = intake.check(p, original, ACTOR, "req-rel")
    assert rep["ok"], rep["errors"]


def test_without_a_relation_nothing_changes():
    p, original = _proposal("母が電話で話した。", "Parent")
    del p["newPeople"][0]["relation"]
    rep = intake.check(p, original, ACTOR, "req-rel")
    assert rep["ok"], rep["errors"]
    assert _related(rep) == []


def test_the_word_list_comes_from_semantics_and_has_everyday_words():
    """条件 2：一覧は SEMANTICS から読む。「お母様」「母親」「ママ」など、ふつうに使う言い方を最初から入れる"""
    words = semantics.relation_words()
    for w in ("お母様", "母親", "ママ", "お父さん", "お姉さん", "おばあちゃん"):
        assert any(w in ws for ws in words.values()), w
    assert set(words) <= set(intake.PROPOSABLE_RELATIONS)
    assert set(intake.PROPOSABLE_RELATIONS) == {"Parent", "Child", "Spouse", "Partner", "Sibling", "Grandparent", "Grandchild",
                                                "OtherRelative", "PrimaryDoctor", "Neighbor"}


@pytest.mark.parametrize("quote, kind", [("お母様が話した。", "Parent"), ("ママが話した。", "Parent"), ("母親が話した。", "Parent")])
def test_everyday_words_pass(quote, kind):
    assert _check(quote, kind)["ok"]


@pytest.mark.parametrize("quote", ["大丈夫だと話した。", "工夫していると話した。", "母方の祖母が話した。"])
def test_words_that_only_contain_a_relation_letter_do_not_count(quote):
    """「大丈夫」の「夫」、「母方の祖母」の「母」は続柄の語として数えない"""
    kind = "Spouse" if "夫" in quote else "Parent"
    rep = _check(quote, kind)
    assert not rep["ok"], rep
    assert not [e for e in rep["errors"] if "項目は無い" in e], rep["errors"]
    assert any("続柄" in e and "語" in e and REDO in e for e in rep["errors"]), rep["errors"]
