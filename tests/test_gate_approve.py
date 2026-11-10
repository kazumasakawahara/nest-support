"""N-21：承認の操作（ADR-001 D9）。DB を使わない部分。

- 承認は書き込みとは別の操作。対象は一件ずつ（{label, id}）
- AI 由来のものをまとめて承認しない（approve_many は 2 件以上の AI 由来を、何も変えずに断る。DB の試験で確かめる）
- 一人で使う人の自己承認を認め、selfApproval に残す（DB の試験）
- 承認の出力に、事実ごとの原文の引用を並べる（DB の試験）
DB に書く試験は tests/test_gate_approve_live.py（NEST_LIVE_DB=1 のときだけ）。
"""
import pytest

from nest.gate import approve as ga

STAFF = "STF-" + "0" * 26
REC = "REC-" + "1" * 26


@pytest.mark.parametrize("target", [None, {}, {"label": "Record"}, {"label": "Record", "id": "x"},
                                    {"label": "AuditLog", "id": "AUD-" + "1" * 26},
                                    {"label": "Staff", "id": STAFF},
                                    {"label": "Record", "id": REC, "name": "架空"}])
def test_bad_target_is_refused_without_touching_the_driver(target):
    out = ga.approve(None, STAFF, target, "req-1")
    assert out["ok"] is False and out["errors"]


@pytest.mark.parametrize("actor", [None, "", "PER-" + "0" * 26])
def test_actor_must_be_staff(actor):
    out = ga.approve(None, actor, {"label": "Record", "id": REC}, "req-1")
    assert out["ok"] is False and any("actorStaffId" in e for e in out["errors"])


def test_request_id_is_required():
    out = ga.approve(None, STAFF, {"label": "Record", "id": REC}, "")
    assert out["ok"] is False and any("requestId" in e for e in out["errors"])


def test_approve_takes_one_target_not_a_list():
    out = ga.approve(None, STAFF, [{"label": "Record", "id": REC}], "req-1")
    assert out["ok"] is False


def test_approve_many_refuses_duplicates_and_empty():
    assert ga.approve_many(None, STAFF, [], "req-1")["ok"] is False
    dup = [{"label": "Record", "id": REC}, {"label": "Record", "id": REC}]
    assert ga.approve_many(None, STAFF, dup, "req-1")["ok"] is False


# G-91（2026-11-06 河原さん承認）：差し戻しの理由（AuditLog.reason）。差し戻しのときだけ・任意・一行
@pytest.mark.parametrize("reason", ["", "   ", "一行目\n二行目", "改行\r", 3, ["理由"]])
def test_reject_reason_must_be_one_line_text(reason):
    out = ga.reject(None, STAFF, {"label": "Record", "id": REC}, "req-1", reason=reason)
    assert out["ok"] is False and any("理由" in e for e in out["errors"])


def test_approve_takes_no_reason():
    import inspect
    assert "reason" not in inspect.signature(ga.approve).parameters
    assert "reason" in inspect.signature(ga.reject).parameters


def test_reject_reason_is_at_most_the_quote_limit():
    """G-92（2026-11-06 河原さん）：理由は 200 字まで（read_quote の上限 QUOTE_MAX と同じ）。超えたら止める"""
    from nest import mcp_guard
    assert mcp_guard.QUOTE_MAX == 200
    over = ga.reject(None, STAFF, {"label": "Record", "id": REC}, "req-1", reason="あ" * 201)
    assert over["ok"] is False and any("200" in e for e in over["errors"])
    at_limit = ga.reject(None, STAFF, {"label": "Record", "id": REC}, "", reason="あ" * 200)
    assert not any("理由" in e for e in at_limit["errors"])  # 200 字は理由として通る（requestId が無いので先で止まる）
