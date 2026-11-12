"""新しい 2 つの Neo4j への接続（ADR-001 D2-2。N-18）。

接続先は 127.0.0.1 の新しいポートだけ。前の DB（7687・7688）を指さない。
パスワードは環境変数から取り、無ければ ~/.config/nest/neo4j-redesign.env から読む（リポジトリには置かない）。
手本：tsunagu-net の tsunagu/connections.py（読むだけ）。

個人の側の接続先は、決まった二つから選ぶ（2026-11-12 河原さん。案 A。台帳 G-103）：
- trial（試走の DB。127.0.0.1:37687）：既定。Claude Desktop の道具・端末の道具はこちらだけに向く
- test（DB を使う試験の専用の DB。127.0.0.1:36687）：環境変数 NEST_DB_TARGET=test のときだけ。DB を使う試験が使う
それ以外の値は止める。任意の接続先を外から渡す道は作らない。資源の側（38687）は読むだけなので共有する。
試験用の DB のパスワードは、個人の側と同じ NEST_PERSONAL_PASSWORD を使う（新しい設定を足さない。中身を読まずに済む）
"""
import os
from pathlib import Path

ENV_FILE = Path.home() / ".config" / "nest" / "neo4j-redesign.env"
SETTINGS = {
    "personal": ("NEST_PERSONAL_PASSWORD", "bolt://127.0.0.1:37687"),
    "resource": ("NEST_RESOURCE_PASSWORD", "bolt://127.0.0.1:38687"),
}
TARGETS = {"trial": "bolt://127.0.0.1:37687", "test": "bolt://127.0.0.1:36687"}


def target():
    """個人の側の向き先（trial か test）。指定が無ければ trial。ほかの値は止める。"""
    value = os.environ.get("NEST_DB_TARGET", "trial")
    if value not in TARGETS:
        raise RuntimeError("NEST_DB_TARGET は trial か test のどちらか（%r は使えない）" % value)
    return value


def uri(side):
    return TARGETS[target()] if side == "personal" else SETTINGS[side][1]


def password(side):
    key = SETTINGS[side][0]
    value = os.environ.get(key)
    if not value and ENV_FILE.is_file():
        from dotenv import dotenv_values
        value = dotenv_values(ENV_FILE).get(key)
    if not value:
        raise RuntimeError("%s が設定されていない（%s）" % (key, ENV_FILE))
    return value


def driver(side):
    from neo4j import GraphDatabase
    # まだ無いラベル・関係・プロパティの通知（UNRECOGNIZED）は、記録の少ない DB でいつも出るので抑える（tsunagu-net と同じ）
    return GraphDatabase.driver(uri(side), auth=("neo4j", password(side)),
                                notifications_disabled_classifications=["UNRECOGNIZED"])
