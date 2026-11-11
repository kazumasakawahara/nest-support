"""L-1 の残り：関わりを資源の側の機関に結ぶ一往復（2026-11-11 河原さん）。入口の点検の部分。DB を使わない。

- 案の関わりは orgName（原文に書かれた機関の名前。任意）と serviceTypeName（任意）を受ける
- orgName は、その関わりの quote（根拠の記録の引用）に含まれていなければ止める。DB には入れない（名前は引用に残る。正典 Involvement の説明）
- serviceTypeName は関わりの項目（正典 Involvement.serviceTypeName）として入る。資源の側のサービスと照らさない
- 機関 ID を案に書かせない約束（N-24）は変えない：orgId は担当機関の推定の候補からだけ
"""
import pytest

from nest.gate import intake

CLIENT = "CLI-01HZZZZZZZZZZZZZZZZZZZZZZZ"
ACTOR = "STF-01HZZZZZZZZZZZZZZZZZZZZZZZ"
PHONE = "通っている「つばさ」の生活支援員から電話で聞き取った。"
OTHER = "本人は週五日、休まず通っている。"
ORIGINAL = "架空の面接記録（例）\n2026-11-05 電話\n" + PHONE + "\n" + OTHER + "【伝聞】\n"


def _proposal(**inv):
    i = {"quote": PHONE, "kind": "ServiceProvision"}
    i.update(inv)
    return {"documentKind": "OwnCaseRecord", "clientId": CLIENT,
            "facts": [{"quote": PHONE, "recordKind": "Interview", "certainty": "Unspecified", "informantKind": "Agency"},
                      {"quote": OTHER, "recordKind": "Interview", "certainty": "Hearsay", "informantKind": "Agency"}],
            "involvements": [{k: v for k, v in i.items() if v is not None}]}


def _check(p):
    return intake.check(p, ORIGINAL, ACTOR, "req-org-name")


def _stopped(rep, *words):
    """止まり、理由に words がそろう。「項目は無い」で止まったのは数えない（欄を受けていない）。"""
    assert not rep["ok"], rep
    assert not [e for e in rep["errors"] if "という項目は無い" in e], rep["errors"]
    assert any(all(w in e for w in words) for e in rep["errors"]), rep["errors"]


def _involvement(rep):
    (inv,) = [n for n in rep["request"]["nodes"] if n["label"] == "Involvement"]
    return inv


def test_org_name_and_service_type_pass():
    rep = _check(_proposal(orgName="つばさ", serviceTypeName="生活介護"))
    assert rep["ok"], rep["errors"]
    props = _involvement(rep)["properties"]
    assert props["serviceTypeName"] == "生活介護"
    assert "orgName" not in props  # 名前は根拠の記録の引用に残り、関わりには写さない
    assert not [n for n in rep["request"]["nodes"] if n["label"] == "Organization"]  # 結ぶのは人が選んでから


def test_both_are_optional():
    rep = _check(_proposal())
    assert rep["ok"], rep["errors"]
    assert "serviceTypeName" not in _involvement(rep)["properties"]


def test_org_name_must_be_in_the_quote_of_that_involvement():
    _stopped(_check(_proposal(orgName="さくら")), "orgName", "引用")


def test_org_name_in_another_fact_but_not_in_its_quote_stops():
    _stopped(_check(_proposal(quote=OTHER, orgName="つばさ")), "orgName", "引用")


def test_whitespace_differences_in_the_org_name_are_ignored():
    rep = _check(_proposal(orgName="つ ばさ"))
    assert rep["ok"], rep["errors"]


@pytest.mark.parametrize("name", ["", "つ", 3, ["つばさ"]])
def test_org_name_must_be_text_of_two_or_more_letters(name):
    _stopped(_check(_proposal(orgName=name)), "orgName")


@pytest.mark.parametrize("name", ["", "   ", 3])
def test_service_type_name_must_be_text(name):
    _stopped(_check(_proposal(serviceTypeName=name)), "serviceTypeName")


def test_an_org_id_is_still_not_accepted_from_the_proposal():
    _stopped(_check(_proposal(orgName="つばさ", orgId="ORG-01HPPPPPPPPPPPPPPPPPPPPPPP")), "orgId", "候補")
