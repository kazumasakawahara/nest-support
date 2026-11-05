"""新しい 2 つの Neo4j への接続（ADR-001 D2-2。N-18）。

接続先は 127.0.0.1 の新しいポートだけ。前の DB（7687・7688）を指さない。
パスワードは環境変数から取り、無ければ ~/.config/nest/neo4j-redesign.env から読む（リポジトリには置かない）。
手本：tsunagu-net の tsunagu/connections.py（読むだけ）。
"""
import os
from pathlib import Path

ENV_FILE = Path.home() / ".config" / "nest" / "neo4j-redesign.env"
SETTINGS = {
    "personal": ("NEST_PERSONAL_PASSWORD", "bolt://127.0.0.1:37687"),
    "resource": ("NEST_RESOURCE_PASSWORD", "bolt://127.0.0.1:38687"),
}


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
    key, uri = SETTINGS[side]
    # まだ無いラベル・関係・プロパティの通知（UNRECOGNIZED）は、記録の少ない DB でいつも出るので抑える（tsunagu-net と同じ）
    return GraphDatabase.driver(uri, auth=("neo4j", password(side)),
                                notifications_disabled_classifications=["UNRECOGNIZED"])
