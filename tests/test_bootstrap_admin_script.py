"""N-38：最初の管理者（Administrator）を登録する入口（scripts/bootstrap_admin.py）。DB は使わない（登録の関数を差し替える）。

- 表示名（--name）が要る。登録の関数 nest.gate.bootstrap.bootstrap_admin を呼び、職員 ID を出す
- 職員がもういるなど、断られたら理由を出して 1 を返す
- 次の手順（職員のトークン）を案内する。トークンはこの道具では作らない
"""
import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _script():
    spec = importlib.util.spec_from_file_location("bootstrap_admin", REPO / "scripts" / "bootstrap_admin.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_registers_and_prints_the_staff_id(monkeypatch, capsys):
    from nest.gate import bootstrap
    calls = []

    def fake(driver, display_name, request_id, **kw):
        calls.append((driver, display_name, request_id))
        return {"ok": True, "errors": [], "requestId": request_id, "staffId": "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"}
    monkeypatch.setattr(bootstrap, "bootstrap_admin", fake)
    assert _script().main(["--name", "（架空）最初の管理者"], driver="D") == 0
    assert calls and calls[0][0] == "D" and calls[0][1] == "（架空）最初の管理者" and calls[0][2].startswith("req-bootstrap-")
    out = capsys.readouterr().out
    assert "STF-01AAAAAAAAAAAAAAAAAAAAAAAA" in out and "staff_token.py add" in out


def test_refused_prints_the_reason(monkeypatch, capsys):
    from nest.gate import bootstrap
    monkeypatch.setattr(bootstrap, "bootstrap_admin",
                        lambda driver, display_name, request_id, **kw: {"ok": False, "errors": ["既に職員が 1 人いる"],
                                                                        "requestId": request_id, "staffId": None})
    assert _script().main(["--name", "（架空）"], driver="D") == 1
    assert "既に職員が 1 人いる" in capsys.readouterr().out


def test_name_is_required():
    with pytest.raises(SystemExit):
        _script().main([], driver="D")
