"""本人のデータの廃棄（計画 N-32。台帳 G-74）。Administrator が手元で使う。Claude は使わない。

使い方:
  # 1. 保存の判断を書く（ゲートを通る。Administrator だけ。理由に名前を書かない）
  uv run python scripts/purge_client.py decide --admin STF-… --code C-…… --decision Delete --decided-on 2026-11-06 --reason "…"
  # 2. 試しの実行（何も消さない。消す件数・残す人の数・他の機関から受け取った記録の件数を出す）
  uv run python scripts/purge_client.py purge --admin STF-… --code C-……
  # 3. 消す（仮名の打ち返しが要る）
  uv run python scripts/purge_client.py purge --admin STF-… --code C-…… --write --confirm C-……

消した後：新しいバックアップを取り、戻せることを確かめてから、消した日より前のバックアップを人が消す（docs/PRIVACY_GUIDELINES.md §5）。
"""
import argparse
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest.gate import purge, write  # noqa: E402

CLIENT_ID = "MATCH (c:Client {displayCode: $code}) RETURN c.clientId AS id"


def _decide(d, a):
    records, _, _ = d.execute_query(CLIENT_ID, {"code": a.code}, routing_="r", database_="neo4j")
    if not records:
        print("本人が無い：%s" % a.code)
        return 1
    out = write.record_retention(d, a.admin, records[0]["id"], a.decided_on, a.decision, a.reason,
                                 "req-retention-" + uuid.uuid4().hex, next_review_on=a.next_review_on)
    if not out["ok"]:
        print("書けなかった：" + "；".join(out["errors"]))
        return 1
    print("保存の判断を書いた：%s（%s）" % (out["ids"]["rd"], a.decision))
    return 0


def _purge(d, a):
    out = purge.purge(d, a.admin, a.code, write=a.write, confirm=a.confirm)
    if not out["ok"]:
        print("止めた：" + "；".join(out["errors"]))
        return 1
    print("%s　%s" % (a.code, "消した" if out["written"] else "試しの実行（何も消していない）"))
    print("- 消す：%s" % "・".join(out["purgedCounts"]))
    print("- 他の機関から受け取った記録（PROVIDED_BY あり）：%d 件。消してよいかを確かめる" % out["providedRecords"])
    print("- 残す人（ほかの本人にもつながる）：%d 人。つながりだけ外す：%s" % (out["keptPersons"], "・".join(out["keptLinked"]) or "なし"))
    print("- もとにした保存の判断：%s" % out["retentionId"])
    if out["written"]:
        print("- 監査ログ：%s。次に、新しいバックアップを取り、消した日より前のバックアップを消す" % out["auditId"])
    return 0


def main(argv=None, driver=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decide")
    d.add_argument("--admin", required=True)
    d.add_argument("--code", required=True)
    d.add_argument("--decision", required=True, choices=["Keep", "Delete"])
    d.add_argument("--decided-on", required=True)
    d.add_argument("--reason", required=True)
    d.add_argument("--next-review-on")
    p = sub.add_parser("purge")
    p.add_argument("--admin", required=True)
    p.add_argument("--code", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--confirm")
    a = ap.parse_args(argv)
    run = _decide if a.cmd == "decide" else _purge
    if driver is not None:
        return run(driver, a)
    from nest import connections
    with connections.driver("personal") as drv:
        return run(drv, a)


if __name__ == "__main__":
    sys.exit(main())
