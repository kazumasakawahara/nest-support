"""N-37：音声を消す道具の入口（scripts/purge_voice.py）。DB は偽物、置き場所は一時の場所（--root）。

- 既定は数えるだけ（消さない）。--write で消す
- 出すのは件数と音声の名前（ハッシュ）だけ。本人の ID や名前は出さない
- DB を読めなくても 30 日を過ぎたものは消し、読めなかったことを知らせる
"""
import hashlib
import importlib.util
import os
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _script():
    spec = importlib.util.spec_from_file_location("purge_voice", REPO / "scripts" / "purge_voice.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _put(root, text, age_days):
    root.mkdir(exist_ok=True)
    p = root / (hashlib.sha256(text.encode("utf-8")).hexdigest() + ".webm")
    p.write_bytes(b"x")
    t = (datetime.now() - timedelta(days=age_days)).timestamp()
    os.utime(p, (t, t))
    return p


class Driver:
    """承認された documentHash を返す偽の DB。"""

    def __init__(self, approved):
        self.approved = approved

    def session(self, database):
        outer = self

        class S:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute_read(self, work):
                class Tx:
                    def run(self, query, hashes):
                        return [{"h": h} for h in hashes if h in outer.approved]
                return work(Tx())
        return S()


def test_dry_run_counts_and_keeps_files(tmp_path, capsys):
    root = tmp_path / "v"
    a = _put(root, "承認", 1)
    b = _put(root, "古い", 31)
    approved = {a.name[:64]}
    assert _script().main(["--root", str(root)], driver=Driver(approved)) == 0
    out = capsys.readouterr().out
    assert "承認済み 1 件" in out and "30 日過ぎ 1 件" in out and "消していない" in out
    assert a.exists() and b.exists()


def test_write_deletes(tmp_path, capsys):
    root = tmp_path / "v"
    a = _put(root, "承認", 1)
    b = _put(root, "古い", 31)
    c = _put(root, "新しい", 1)
    assert _script().main(["--root", str(root), "--write"], driver=Driver({a.name[:64]})) == 0
    assert not a.exists() and not b.exists() and c.exists()
    assert "消した" in capsys.readouterr().out


def test_db_down_still_removes_expired_and_says_so(tmp_path, capsys):
    root = tmp_path / "v"
    old = _put(root, "古い", 31)

    class Down:
        def session(self, database):
            raise RuntimeError("（架空）つながらない")
    assert _script().main(["--root", str(root), "--write"], driver=Down()) == 1
    assert not old.exists()
    assert "DB を読めない" in capsys.readouterr().out
