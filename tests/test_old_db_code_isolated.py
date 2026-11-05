"""前の DB を指すコードの残り（台帳 G-49。N-27〜N-30 で置き換える）が、置き換えるまでの間に新しい DB を指さないこと。DB を使わない。

2026-11-06 河原さん：「置き換えるまでの間、どれも新しい DB（37687・38687）を指さないことを試験で固定する」。
新しい DB のポート（37474・37687・38474・38687）、コンテナの名前、接続の設定のファイルの名前のどれも書かない。
"""
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
OLD_DB_CODE = ["lib/db_operations.py", "sos/api_server.py", "scripts/doctor.sh", "scripts/rotate_password.py", "setup.sh"]
# claude-skills/ecomap-generator/scripts/generate_mermaid.py は N-27g で git から外した（2026-11-06）
NEW_DB = re.compile(r"3[78](474|687)|nest-redesign|neo4j-redesign")


def _installer_files():
    out = subprocess.run(["git", "ls-files", "installer"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    assert out, "installer/ が git に無い"
    return out


def test_the_pattern_catches_the_new_db():
    for s in ("bolt://127.0.0.1:37687", "localhost:38687", "http://127.0.0.1:37474", "38474",
              "nest-redesign-personal", "~/.config/nest/neo4j-redesign.env"):
        assert NEW_DB.search(s), s
    for s in ("bolt://localhost:7687", "7688", "7474", "nest-support-neo4j", "~/.config/nest/neo4j.env"):
        assert not NEW_DB.search(s), s


@pytest.mark.parametrize("path", OLD_DB_CODE + _installer_files())
def test_old_db_code_does_not_point_at_the_new_db(path):
    text = (REPO / path).read_text(encoding="utf-8", errors="replace")
    hits = sorted({m.group(0) for m in NEW_DB.finditer(text)})
    assert not hits, (path, hits)
