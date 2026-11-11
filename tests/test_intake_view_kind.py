"""見立て（確度 Inference）の記録の種類と話し手の組み合わせを入口の点検で確かめる（2026-11-12 河原さん。台帳 G-101）。DB を使わない。

- SEMANTICS SEM-REC-04：見立ての記録の種類は、もとになった情報に合わせる。
  Self・Family・Neighbor なら Interview、Agency（記録者の観察）なら Observation、DocumentOnly なら Document
- 合わなければ止め、理由に正しい組み合わせを出す
- 情報提供の書面（ProvisionDocument）の見立ては今回決めない。点検の対象にしない
"""
import pytest

from nest.gate import intake

CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
VIEW = "予定が急に変わると落ち着かないのだろうと、私は受け取った。"
ORIGINAL = "架空の面接記録（例）\n2026-11-02 訪問\n" + VIEW + "【推測】\n"
RIGHT = {"Self": "Interview", "Family": "Interview", "Neighbor": "Interview", "Agency": "Observation",
         "DocumentOnly": "Document"}
KINDS = ("Observation", "Interview", "Notification", "MeetingMinutes", "Plan", "Document")


def _check(record_kind, informant, certainty="Inference", original=ORIGINAL):
    p = {"documentKind": "OwnCaseRecord", "clientId": CLIENT,
         "facts": [{"quote": VIEW, "recordKind": record_kind, "certainty": certainty, "informantKind": informant}]}
    return intake.check(p, original, ACTOR, "req-view-kind")


def _kind_errors(rep):
    return [e for e in rep["errors"] if "見立て" in e and "記録の種類" in e]


@pytest.mark.parametrize("informant, kind", sorted(RIGHT.items()))
def test_the_right_pair_passes(informant, kind):
    rep = _check(kind, informant)
    assert rep["ok"], rep["errors"]


@pytest.mark.parametrize("informant, kind", [(i, k) for i in RIGHT for k in KINDS if k != RIGHT[i]])
def test_a_wrong_pair_stops_and_names_the_right_kind(informant, kind):
    rep = _check(kind, informant)
    assert not rep["ok"]
    (err,) = _kind_errors(rep)
    assert "informantKind %s なら recordKind は %s" % (informant, RIGHT[informant]) in err
    assert "Self・Family・Neighbor なら Interview" in err and "Agency なら Observation" in err \
        and "DocumentOnly なら Document" in err


def test_a_fact_that_is_not_a_view_is_not_checked():
    """見立てでない記録（印の無い一文）は、この組み合わせを確かめない"""
    original = "架空の面接記録（例）\n2026-11-02 訪問\n" + VIEW + "\n"
    rep = _check("Interview", "Agency", certainty="Unspecified", original=original)
    assert rep["ok"], rep["errors"]


def test_a_provision_document_view_is_not_checked_yet():
    """情報提供の書面の見立ては今回決めない（journal の先の論点）"""
    p = {"documentKind": "ProvisionDocument", "providerName": "架空の事業所", "clientId": CLIENT,
         "facts": [{"quote": VIEW, "recordKind": "Document", "certainty": "Inference", "providerCertainty": "Inference",
                    "informantKind": "Agency"}]}
    rep = intake.check(p, ORIGINAL, ACTOR, "req-view-kind", provider_org_id="ORG-01HPPPPPPPPPPPPPPPPPPPPPPP")
    assert not _kind_errors(rep), rep["errors"]
