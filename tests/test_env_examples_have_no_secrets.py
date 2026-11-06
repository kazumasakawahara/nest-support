"""台帳 G-70（2026-11-06 河原さん）：.env.example の類（ルートと sos）に鍵やパスワードの実物を入れない。

「=」の右側が、空・YOUR_ で始まる・既定値の形（localhost・127.0.0.1 の URL、ポート番号、true/false）の
どれかであることだけを確かめる。キーの名前で許す既定の言葉もある（ALLOWED_BY_KEY）。値そのものは出力しない（失敗のときもキーの名前と行の番号だけを出す）。DB を使わない。
"""
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ALLOWED = [
    re.compile(r""),                                                    # 空
    re.compile(r"YOUR_[A-Za-z0-9_]*"),                                  # 置き換えの印
    re.compile(r"(?i)true|false"),
    re.compile(r"[0-9]{1,5}"),                                          # ポート番号
    re.compile(r"(?:[a-z+]+://)?(?:localhost|127\.0\.0\.1)(?::[0-9]{1,5})?/?"),  # 手元の URL
]

# キーの名前で許す既定の言葉（2026-11-06 河原さん。台帳 G-70）
ALLOWED_BY_KEY = {"PSEUDONYMIZATION_MODE": {"mask", "pseudonym"}, "NEO4J_USERNAME": {"neo4j"}}


def _bad_keys(text):
    """既定の形でない値を持つ行の（行の番号, キー）。値は返さない。"""
    bad = []
    for n, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.replace("export", "", 1).strip()
        value = value.split(" #", 1)[0].strip().strip("'\"")
        if value in ALLOWED_BY_KEY.get(key, ()):
            continue
        if not any(p.fullmatch(value) for p in ALLOWED):
            bad.append((n, key))
    return bad


def _examples():
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    return [p for p in out if Path(p).name.startswith(".env") and "example" in Path(p).name]


def test_the_checker_flags_real_looking_values_without_showing_them():
    sample = "\n".join(["# 架空", "A=", "B=YOUR_PASSWORD", "C=true", "D=7687", "E=bolt://localhost:7687",
                        "F=http://127.0.0.1:8000", "G=s3cr3t-架空", "export H=abcDEF123",
                        "PSEUDONYMIZATION_MODE=mask", "NEO4J_USERNAME=neo4j", "NEO4J_USERNAME=admin"])
    assert _bad_keys(sample) == [(8, "G"), (9, "H"), (12, "NEO4J_USERNAME")]


def test_both_example_files_are_tracked():
    assert {".env.example", "sos/.env.example"} <= set(_examples())


@pytest.mark.parametrize("path", _examples())
def test_example_env_has_only_placeholders(path):
    bad = _bad_keys((REPO / path).read_text(encoding="utf-8", errors="replace"))
    assert not bad, "既定の形でない値（行の番号, キー）: %s" % bad
