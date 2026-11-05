"""
nest-support データベース操作モジュール
接続・読み取り・仮名化の出力。

グラフの登録（register_to_database）は N-17 で閉じた。書き込みはゲート（nest/gate）だけを通る。
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
# 個人層（port 7688）の接続情報。~/.zshrc が読み込む neo4j.env（共有層 7687）より優先する
load_dotenv(Path.home() / ".config" / "nest" / "neo4j-personal.env", override=True)

# 仮名化スキーマ設定
# 有効/無効の判定は lib/pseudonymizer 側（環境変数駆動のシングルトン）に一本化する。
# db_operations 側で二重に env を読まない。

def _get_pseudonymizer():
    try:
        from lib.pseudonymizer import get_pseudonymizer
        return get_pseudonymizer()
    except Exception:
        from lib.pseudonymizer import Pseudonymizer
        return Pseudonymizer(enabled=False)

def _mask_output(records: list[dict], field_rules: dict = None) -> list[dict]:
    """読み取り結果を仮名化する（PSEUDONYMIZATION 無効時はそのまま返す）。

    NgAction（禁忌事項）/ CarePreference（推奨ケア）は安全に直結するため
    仮名化しない（呼び出し側でこれらのレコードを本関数に渡さない運用とする）。
    """
    return _get_pseudonymizer().mask_records(records, field_rules)

def log(message: str, level: str = "INFO"):
    sys.stderr.write(f"[DB_Ops:{level}] {message}\n")
    sys.stderr.flush()

# --- Neo4j 接続 ---
_driver = None

def get_driver():
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        pwd = os.getenv("NEO4J_PASSWORD", "")
        if not uri or not user:
            log("Neo4j環境変数が未設定です", "ERROR")
            return None
        try:
            _driver = GraphDatabase.driver(uri, auth=(user, pwd))
            _driver.verify_connectivity()
        except Exception as e:
            log(f"Neo4j接続失敗: {e}", "ERROR")
            _driver = None
    return _driver

def run_query(query, params=None):
    try:
        driver = get_driver()
        if driver is None: return []
        with driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]
    except Exception as e:
        log(f"クエリ実行エラー: {e}", "ERROR")
        return []

def execute_write(query, params=None):
    """書き込みクエリを実行し、失敗時は例外を送出する（握り潰さない）。

    読み取り用 run_query が失敗時に [] を返すのと異なり、書き込みの失敗を
    呼び出し側へ伝播させる。安全に関わる NgAction / Client 等の登録が静かに
    失敗したまま「成功」と誤報告されるのを防ぐため、register_to_database の
    主要な登録経路で使用する。
    """
    driver = get_driver()
    if driver is None:
        raise RuntimeError("Neo4j ドライバーを取得できません（接続失敗）")
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]

# =============================================================================
# 書き込み（閉じた。N-17）
# =============================================================================

GATE_ONLY_MESSAGE = (
    "この書き込みの道は閉じました。書き込みはゲート（nest/gate）だけを通ります（ゲートの書き込みは N-20）。"
    "入力を直さず、データベースにも触れていません。"
)


def register_to_database(extracted_graph: dict, user_name: str = "system") -> dict:
    """閉じた書き込みの道（N-17。2026-11-05）。何も直さず、何も書かず、断りを返す。

    前は Guardian Layer（lib/schema_validator.py）で名前・列挙を直し、名前で MERGE して書いていた。
    新しい DB では、ゲートを通らない書き込みの道を残さない（ADR-001 D6）。
    呼び出し元（field-ui の支援記録・insight-engine の昇格）は N-20 まで書けない。
    """
    return {"status": "error", "message": GATE_ONLY_MESSAGE, "count": 0}


# =============================================================================
# 取得系（互換性維持）
# =============================================================================

def resolve_client_raw(identifier: str) -> Optional[dict]:
    """識別子から Client を解決する（仮名化しない生データ）。

    解決結果の name / clientId は downstream の照会キー（MATCH ... {name:$name}）
    として使われるため、および SOS 緊急通知のように実名・実データが必須の経路
    では、必ずこの raw 版を使うこと。仮名化するとキー照合が壊れる。
    """
    # 旧db_operationsの高度な解決ロジック（clientId/displayCode対応）を維持
    clean = identifier.replace("さん", "").replace("くん", "").strip()
    res = run_query("""
        MATCH (c:Client)
        WHERE c.name = $id OR c.clientId = $id OR c.displayCode = $id OR c.kana = $id
           OR ANY(a IN COALESCE(c.aliases, []) WHERE a = $id)
        RETURN c.name as name, c.clientId as clientId, c.displayCode as displayCode
        LIMIT 1
    """, {"id": clean})
    return res[0] if res else None

def resolve_client(identifier: str) -> Optional[dict]:
    """識別子から Client を解決する（PSEUDONYMIZATION 有効時は出力を仮名化）。

    表示用途向け。照会キーとして downstream に渡す場合や SOS 緊急通知など
    実名が必要な場合は resolve_client_raw() を使うこと。
    """
    res = resolve_client_raw(identifier)
    if res is None:
        return None
    return _mask_output([res])[0]

def get_clients_list():
    res = run_query("MATCH (c:Client) RETURN c.name as name ORDER BY c.name")
    names = [r['name'] for r in res]
    p = _get_pseudonymizer()
    if getattr(p, "enabled", False):
        names = [p.mask_name(n) for n in names]
    return names

def get_display_name(identifier: str, fallback: str = "不明") -> str:
    """識別子から表示用の名前を取得する。

    SOS 緊急通知サービス等が、clientId / displayCode / 通称などの
    様々な識別子を人間可読な氏名へ解決するために使用する。
    緊急時に実名が必要なため、仮名化しない raw 解決を用いる（意図的例外）。
    """
    client = resolve_client_raw(identifier)
    if client:
        return client.get('name') or client.get('displayCode') or fallback
    return fallback
