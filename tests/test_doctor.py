"""N-30：doctor.sh を新しい構成に合わせる。DB も本物の Docker も使わない（偽の HOME と偽の docker で確かめる）。

確かめる項目：
- 前の DB のコンテナが動いていない
- 新しい二つのコンテナは、動いていれば 127.0.0.1 だけで待ち受けている（止まっているのは正しい状態）
- 接続の設定のファイルがあり、権限が 600（中身は読まない）
- .mcp.json が nest-personal・nest-resource を持ち、前の neo4j・neo4j-shared を持たない
- スキルのリンクが、このリポジトリの claude-skills を指している。外したスキルのリンクが残っていない
- 正典のずれが 0 件
"""
import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOCTOR = REPO / "scripts" / "doctor.sh"
SKILLS = sorted(p.name for p in (REPO / "claude-skills").iterdir() if (p / "SKILL.md").is_file())


def _run(tmp_path, ps_lines, *, env_mode=0o600, extra_links=(), drop_link=None):
    home = tmp_path / "home"
    (home / ".config" / "nest").mkdir(parents=True)
    env_file = home / ".config" / "nest" / "neo4j-redesign.env"
    env_file.write_text("# 架空\n", encoding="utf-8")
    os.chmod(env_file, env_mode)
    skills = home / ".claude" / "skills"
    skills.mkdir(parents=True)
    for s in SKILLS:
        if s != drop_link:
            (skills / s).symlink_to(REPO / "claude-skills" / s)
    for name in extra_links:
        (skills / name).symlink_to(tmp_path / "gone" / name)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "docker"
    fake.write_text("#!/bin/sh\n[ \"$1\" = ps ] && cat \"$FAKE_PS\"\nexit 0\n", encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    ps = tmp_path / "ps.txt"
    ps.write_text("".join(line + "\n" for line in ps_lines), encoding="utf-8")
    env = dict(os.environ, HOME=str(home), PATH="%s:%s" % (bin_dir, os.environ["PATH"]), FAKE_PS=str(ps))
    return subprocess.run(["bash", str(DOCTOR)], cwd=REPO, env=env, capture_output=True, text=True, timeout=120)


def test_all_pass_when_the_dbs_are_stopped(tmp_path):
    out = _run(tmp_path, [])
    assert out.returncode == 0, out.stdout + out.stderr
    assert "FAIL" not in out.stdout


def test_all_pass_when_the_new_dbs_listen_on_localhost_only(tmp_path):
    out = _run(tmp_path, ["nest-redesign-personal 127.0.0.1:37474->7474/tcp, 127.0.0.1:37687->7687/tcp",
                          "nest-redesign-resource 127.0.0.1:38474->7474/tcp, 127.0.0.1:38687->7687/tcp"])
    assert out.returncode == 0, out.stdout + out.stderr


@pytest.mark.parametrize("line", ["nest-support-neo4j 0.0.0.0:7688->7687/tcp", "support-db-neo4j 0.0.0.0:7687->7687/tcp"])
def test_fails_when_an_old_db_runs(tmp_path, line):
    out = _run(tmp_path, [line])
    assert out.returncode == 1 and line.split()[0] in out.stdout


def test_fails_when_a_new_db_listens_on_all_addresses(tmp_path):
    out = _run(tmp_path, ["nest-redesign-personal 0.0.0.0:37687->7687/tcp"])
    assert out.returncode == 1 and "nest-redesign-personal" in out.stdout


def test_fails_when_the_settings_file_is_readable_by_others(tmp_path):
    out = _run(tmp_path, [], env_mode=0o644)
    assert out.returncode == 1 and "600" in out.stdout


def test_fails_when_a_removed_skill_link_remains(tmp_path):
    out = _run(tmp_path, [], extra_links=["wamnet-provider-sync"])
    assert out.returncode == 1 and "wamnet-provider-sync" in out.stdout


def test_fails_when_a_skill_link_is_missing(tmp_path):
    out = _run(tmp_path, [], drop_link="neo4j-support-db")
    assert out.returncode == 1 and "neo4j-support-db" in out.stdout


def test_doctor_does_not_read_the_settings_file():
    text = DOCTOR.read_text(encoding="utf-8")
    for word in ("cat ", "source ", ". \"$", "grep", "dotenv"):
        for line in text.splitlines():
            if "neo4j-redesign.env" in line or "ENV_FILE" in line:
                assert word not in line, line
