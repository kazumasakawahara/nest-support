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


# ---- 段階 L の確かめ（2026-11-11 河原さん）：根拠の記録が未確定のまま、禁忌・面接記録が承認で有効になった ----
# 正典 §7「一回の操作で一つのノード」に合わせ、根拠を一緒に承認しない。根拠（EVIDENCED_BY の先の記録）が未確定なら
# 対象の承認を止め、先に承認する記録を名指す。根拠がすべて差し戻し済みなら止める。差し戻しは止めない。
NGA = "NGA-" + "2" * 26
REC2 = "REC-" + "3" * 26


class _Session:
    def __init__(self, tx):
        self.tx = tx

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute_write(self, fn, *args):
        return fn(self.tx, *args)


class _Driver:
    def __init__(self, evidence):
        self.tx = _Tx(evidence)

    def session(self, **kw):
        return _Session(self.tx)


class _Tx:
    """職員は Active、対象は Pending の NgAction。evidence は [(recordId, status)]。"""
    def __init__(self, evidence):
        self.evidence, self.changed = evidence, []

    def run(self, query, **p):
        if "MATCH (s:Staff {staffId: $id})" in query:
            return [{"status": "Active", "role": "Administrator"}]
        if "RETURN t.status AS status, t.origin AS origin" in query:
            return [{"status": "Pending", "origin": "AiExtracted"}]
        if "-[:EVIDENCED_BY]->(e:Record) RETURN" in query:
            return [{"id": i, "status": s} for i, s in self.evidence]
        if "SET t.status" in query:
            self.changed.append(query)
            return [{"n": 1}]
        if "RETURN r.recordId AS recordId" in query or "count(a) AS n" in query:
            return [{"n": 0}] if "count(a)" in query else []
        return []


def _approve(evidence):
    d = _Driver(evidence)
    return ga.approve(d, STAFF, {"label": "NgAction", "id": NGA}, "req-1"), d.tx


def test_approval_stops_while_the_evidence_is_pending_and_names_it():
    out, tx = _approve([(REC, "Active"), (REC2, "Pending")])
    assert out["ok"] is False and not tx.changed
    (e,) = out["errors"]
    assert REC2 in e and REC not in e and "先に" in e and "承認" in e


def test_approval_stops_when_all_evidence_was_rejected():
    out, tx = _approve([(REC, "Inactive"), (REC2, "Inactive")])
    assert out["ok"] is False and not tx.changed
    assert any("差し戻し" in e for e in out["errors"])


def test_approval_passes_when_the_evidence_is_active():
    out, tx = _approve([(REC, "Active"), (REC2, "Inactive")])
    assert out["ok"], out["errors"]
    assert len(tx.changed) == 1  # 対象だけ。根拠を一緒に変えない


def test_approval_without_evidence_links_is_unchanged():
    out, tx = _approve([])
    assert out["ok"], out["errors"]


def test_reject_is_not_stopped_by_pending_evidence():
    d = _Driver([(REC2, "Pending")])
    out = ga.reject(d, STAFF, {"label": "NgAction", "id": NGA}, "req-1")
    assert out["ok"], out["errors"]
