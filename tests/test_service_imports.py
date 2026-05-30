"""
独立サービス (sos / field-ui) の import 健全性テスト。

これらは FastAPI の独立プロセスで、ユニットテストの外で起動するため、
import エラーが「起動して初めてクラッシュ」という形で顕在化しやすい。
特に SOS は親が倒れた際の緊急通知という最重要機能であり、
import 段階での破綻は致命的。

ここでは外部API(LINE)やネットワークに触れず、
「サービスが lib から import しようとしているシンボルが実在するか」だけを
静的に検証する。（モジュール全体の exec はせず、AST で import 文を抽出して
対象シンボルの存在を確認する。）
"""

import ast
import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _lib_imports(service_relpath: str) -> list[tuple[str, str]]:
    """サービスファイルから `from lib.X import a, b` を抽出して
    (module, symbol) のリストを返す。"""
    source = (REPO_ROOT / service_relpath).read_text(encoding="utf-8")
    tree = ast.parse(source)
    pairs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("lib."):
            for alias in node.names:
                pairs.append((node.module, alias.name))
    return pairs


@pytest.mark.parametrize("service", ["sos/api_server.py", "field-ui/server.py"])
def test_service_lib_imports_resolve(service):
    """サービスが lib から import する全シンボルが実在することを確認。

    db_operations と db_new_operations の分裂により、存在しない関数を
    import して起動時 ImportError になる事故を防ぐ回帰テスト。
    """
    missing = []
    for module_name, symbol in _lib_imports(service):
        module = importlib.import_module(module_name)
        if not hasattr(module, symbol):
            missing.append(f"{module_name}.{symbol}")
    assert not missing, (
        f"{service} が存在しないシンボルを import しています: {missing}"
    )
