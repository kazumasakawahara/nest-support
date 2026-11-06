"""N-33：個人の側の DB のバックアップ（2026-11-06 河原さん。止まる点 F-1。台帳 G-74）。DB も本物の Docker も使わない。

- 置き場所は ~/nest-backup/（権限 700、Time Machine の対象外）。外のサービスに置かない
- DB を止めてから取る・戻す（Community 版は動いたまま書き出せない）。動いていれば止める
- 世代は 4 つ。古いものは、世代の名前の形（YYYYmmdd-HHMMSS）のフォルダだけを消す
- 取ったファイルが無いか空なら失敗にし、古い世代を消さない
DB を使う確かめ（取る・戻す・戻した後に正典のずれ 0 件）は tests/test_backup_live.py。
"""
import datetime as dt
import os
import stat
from pathlib import Path

import pytest

from nest import backup

REPO = Path(__file__).resolve().parents[1]
IMAGE = "neo4j:5.26.32-community@sha256:adaa077a3ab023015143b8f73f7076a7d053f12985f5b06f4c6a128c3a2f7240"
NOW = dt.datetime(2026, 11, 6, 10, 0, 0)


class Fake:
    """docker と tmutil の代わり。呼ばれた引数を残し、dump のときは指定のファイルを作る。"""

    def __init__(self, running="", dump_bytes=b"x" * 10):
        self.calls, self.running, self.dump_bytes = [], running, dump_bytes

    def __call__(self, args):
        self.calls.append(list(args))
        if args[:2] == ["docker", "ps"]:
            return 0, self.running
        if args[:2] == ["docker", "run"] and "dump" in args:
            gen = Path([a for a in args if a.endswith(":/backups")][0].rsplit(":", 1)[0])
            if self.dump_bytes is not None:
                (gen / "neo4j.dump").write_bytes(self.dump_bytes)
        return 0, ""


def _mode(p):
    return stat.S_IMODE(os.stat(p).st_mode)


def test_the_image_comes_from_compose():
    assert backup.personal_image((REPO / "docker-compose.yml").read_text(encoding="utf-8")) == IMAGE


def test_dump_refuses_while_the_personal_db_runs(tmp_path):
    fake = Fake(running="nest-redesign-personal\n")
    out = backup.dump(tmp_path / "bk", tmp_path / "data", IMAGE, fake, NOW)
    assert not out["ok"] and any("止め" in e for e in out["errors"])
    assert not any(c[:2] == ["docker", "run"] for c in fake.calls)


def test_dump_makes_a_private_excluded_generation(tmp_path):
    fake = Fake()
    root = tmp_path / "bk"
    out = backup.dump(root, tmp_path / "data", IMAGE, fake, NOW)
    assert out["ok"], out["errors"]
    gen = root / "20261106-100000"
    assert _mode(root) == 0o700 and _mode(gen) == 0o700 and _mode(gen / "neo4j.dump") == 0o600
    assert ["tmutil", "addexclusion", str(root)] in fake.calls
    run = [c for c in fake.calls if c[:2] == ["docker", "run"]][0]
    assert run == ["docker", "run", "--rm", "-v", "%s:/data" % (tmp_path / "data"), "-v", "%s:/backups" % gen, IMAGE,
                   "neo4j-admin", "database", "dump", "neo4j", "--to-path=/backups"]


@pytest.mark.parametrize("content", [None, b""])
def test_dump_fails_without_a_file_and_keeps_old_generations(tmp_path, content):
    root = tmp_path / "bk"
    root.mkdir()
    for n in range(5):
        (root / ("2026110%d-090000" % n)).mkdir()
    out = backup.dump(root, tmp_path / "data", IMAGE, Fake(dump_bytes=content), NOW)
    assert not out["ok"]
    assert len([p for p in root.iterdir() if backup.GENERATION.fullmatch(p.name)]) == 5  # 失敗した世代は残さない、古いものも消さない


def test_four_generations_are_kept_and_other_files_are_left_alone(tmp_path):
    root = tmp_path / "bk"
    root.mkdir()
    for n in range(1, 6):
        (root / ("2026110%d-090000" % n)).mkdir()
    (root / "README.txt").write_text("人のメモ", encoding="utf-8")
    (root / "keep-me").mkdir()
    out = backup.dump(root, tmp_path / "data", IMAGE, Fake(), NOW)
    assert out["ok"], out["errors"]
    names = sorted(p.name for p in root.iterdir())
    assert names == ["20261103-090000", "20261104-090000", "20261105-090000", "20261106-100000", "README.txt", "keep-me"]
    assert out["removed"] == ["20261101-090000", "20261102-090000"]


def test_restore_loads_over_the_current_db_only_when_stopped(tmp_path):
    gen = tmp_path / "bk" / "20261106-100000"
    gen.mkdir(parents=True)
    (gen / "neo4j.dump").write_bytes(b"x")
    # いつもの個人の側のデータに戻すときは、DB が動いていれば止める（動いている DB のデータは置き換えられない）
    assert not backup.restore(gen, backup.DEFAULT_DATA, IMAGE, Fake(running="nest-redesign-personal\n"))["ok"]
    fake = Fake()
    out = backup.restore(gen, tmp_path / "data", IMAGE, fake)
    assert out["ok"], out["errors"]
    run = [c for c in fake.calls if c[:2] == ["docker", "run"]][0]
    assert run == ["docker", "run", "--rm", "-v", "%s:/data" % (tmp_path / "data"), "-v", "%s:/backups" % gen, IMAGE,
                   "neo4j-admin", "database", "load", "neo4j", "--from-path=/backups", "--overwrite-destination=true"]


def test_restore_into_another_folder_does_not_need_the_db_stopped(tmp_path):
    """試しに別のデータのフォルダへ戻す（戻せることを確かめる）ときは、いつもの DB を止めなくてよい"""
    gen = tmp_path / "20261106-100000"
    gen.mkdir()
    (gen / "neo4j.dump").write_bytes(b"x")
    assert backup.restore(gen, tmp_path / "other", IMAGE, Fake(running="nest-redesign-personal\n"))["ok"]


def test_restore_refuses_a_folder_without_a_dump(tmp_path):
    gen = tmp_path / "20261106-100000"
    gen.mkdir()
    out = backup.restore(gen, tmp_path / "data", IMAGE, Fake())
    assert not out["ok"] and any("neo4j.dump" in e for e in out["errors"])


def test_the_default_place_is_outside_the_repository():
    assert backup.DEFAULT_ROOT == Path.home() / "nest-backup"
    assert REPO not in backup.DEFAULT_ROOT.parents


def test_the_old_shell_script_is_gone():
    assert not (REPO / "scripts" / "backup.sh").exists()
