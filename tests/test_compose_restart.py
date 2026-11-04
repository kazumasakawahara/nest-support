"""N-18a: compose のサービスは Docker の再起動で勝手に立ち上がらない（ADR-001・gray-decisions G-12）。

`restart:` の行がすべて "no" であることを、docker-compose.yml の本文で確かめる。
コメントアウトされた行（# で始まる）は対象外。
"""

import re
from pathlib import Path

COMPOSE = Path(__file__).resolve().parents[1] / "docker-compose.yml"
RESTART = re.compile(r"^\s*restart:\s*(.+?)\s*$")


def restart_values(text: str) -> list[str]:
    values = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = RESTART.match(line)
        if m:
            values.append(m.group(1))
    return values


def test_restart_values_detects_unless_stopped():
    sample = 'services:\n  a:\n    restart: unless-stopped\n  # restart: always\n'
    assert restart_values(sample) == ["unless-stopped"]


def test_compose_services_do_not_restart_automatically():
    values = restart_values(COMPOSE.read_text(encoding="utf-8"))
    assert values, "restart: の行が無い（明示して \"no\" にする）"
    assert all(v == '"no"' for v in values), values
