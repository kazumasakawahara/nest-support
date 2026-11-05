"""N-09: shared-schema の写し（前の正典）を外した後の検査。

文書・スキルの説明文（*.md）の参照は N-27・N-29 で直すので、ここではコードと設定だけを見る。
試験のファイル（tests/）は、過去の経緯として名前を書いていることがあるので見ない。
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REMOVED = [
    "docs/SCHEMA_CONVENTION.md",
    "docs/SEMANTIC_MODEL.md",
    "docs/semantic-model-instruction.md",
    "scripts/check_semantic_drift.py",
]
FORBIDDEN = ("shared-schema", "/api/narrative", "check_semantic_drift")
CODE_SUFFIXES = {".py", ".sh", ".ps1", ".json", ".toml", ".yml", ".yaml", ".cypher"}


def _repo_files():
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split("\n")
    return [ROOT / f for f in out if f and (ROOT / f).is_file()]


def test_old_canon_files_are_removed():
    left = [f for f in REMOVED if (ROOT / f).exists()]
    assert not left, left


def test_no_backup_copies_left_in_docs():
    left = sorted(p.name for p in (ROOT / "docs").glob("*.bak-*"))
    assert not left, left


def test_code_does_not_refer_to_shared_schema():
    offenders = []
    for path in _repo_files():
        rel = path.relative_to(ROOT)
        if rel.parts[0] == "tests" or path.suffix not in CODE_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for word in FORBIDDEN:
            if word in text:
                offenders.append("%s: %s" % (rel, word))
    assert not offenders, offenders
