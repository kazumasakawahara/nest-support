"""
db_operations / db_new_operations のモジュール統合に関する回帰テスト。

背景:
レビューにより db_new_operations.py(930行) は外部からは run_query しか
使われておらず、残りは db_operations.py と重複・分裂したデッドコードで
あることが判明した。run_query を db_operations.run_query に一本化し、
db_new_operations.py を削除する。

このテストは「統合後にどのモジュールも db_new_operations へ依存して
いないこと」「消費者モジュールが import 可能であること」を保証する
回帰テスト。削除によって起動時 ImportError が再発しないことを守る。

実DB・実APIには接続しない。
"""

import ast
import importlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _source_files():
    """lib/ scripts/ field-ui/ sos/ の .py を列挙（__pycache__ 除外）。"""
    targets = []
    for sub in ["lib", "scripts", "field-ui", "sos"]:
        base = REPO_ROOT / sub
        if base.exists():
            targets.extend(base.rglob("*.py"))
    return [p for p in targets if "__pycache__" not in p.parts]


# 本リポジトリ内の旧モジュールへの依存（import / 本リポ内パス参照）のみを検出する。
# 訂正（2026-07-12）: 旧判定は単純な部分文字列一致だったため、外部リポジトリ
# （neo4j-agno-agent。あちらでは db_new_operations.py が現役）のファイルパスを
# 参照するだけの scripts/check_semantic_drift.py に誤反応した。テストの意図
# （統合後の起動時 ImportError 再発防止）どおり、実際の依存のみを検出する。
_LOCAL_DEPENDENCY_RE = re.compile(
    r"(?:from|import)\s+(?:lib\.)?db_new_operations|lib/db_new_operations"
)


def test_no_module_references_db_new_operations():
    """ソースコードのどこからも本リポの db_new_operations に依存していないこと。"""
    offenders = []
    for path in _source_files():
        if _LOCAL_DEPENDENCY_RE.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        f"db_new_operations への参照が残っています（統合後は db_operations を使う）: {offenders}"
    )


def test_db_new_operations_file_is_removed():
    """db_new_operations.py そのものが削除されていること。"""
    assert not (REPO_ROOT / "lib" / "db_new_operations.py").exists(), (
        "lib/db_new_operations.py がまだ存在します"
    )


def test_canonical_db_operations_exposes_run_query():
    """統合先 db_operations が run_query を提供していること（消費者の生命線）。"""
    mod = importlib.import_module("lib.db_operations")
    assert hasattr(mod, "run_query") and callable(mod.run_query)


def test_consumer_modules_parse_and_import_cleanly():
    """run_query 差し替え後、消費者が構文・import 健全であること。"""
    importlib.import_module("lib.embedding")
    backfill = REPO_ROOT / "scripts" / "backfill_embeddings.py"
    ast.parse(backfill.read_text(encoding="utf-8"))
