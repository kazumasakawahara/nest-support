"""個人の側の DB のバックアップ（計画 N-33。決まりは nest/backup.py の先頭、docs/PRIVACY_GUIDELINES.md §5）。

使い方（個人の側の DB を止めてから）:
  docker compose --env-file ~/.config/nest/neo4j-redesign.env down
  uv run python scripts/backup.py dump                       # ~/nest-backup/<日時>/neo4j.dump。世代は 4 つ
  uv run python scripts/backup.py list
  uv run python scripts/backup.py restore <日時>              # 今の個人の側を、その世代で置き換える
  uv run python scripts/backup.py count                      # DB を起こした後：ラベルごとの数（戻す前と後で比べる）
  uv run python scripts/backup.py prune --before <日時>       # その世代より前の世代を一覧（消さない）
  uv run python scripts/backup.py prune --before <日時> --write   # 消して、残った世代を出す（廃棄の後）
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest import backup  # noqa: E402


def main(argv=None, driver=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dump", "list", "restore", "prune", "count"])
    ap.add_argument("generation", nargs="?")
    ap.add_argument("--root", default=str(backup.DEFAULT_ROOT))
    ap.add_argument("--data", default=str(backup.DEFAULT_DATA))
    ap.add_argument("--before", help="prune：この世代より前を消す（list で出る名前）")
    ap.add_argument("--write", action="store_true", help="prune：本当に消す（無ければ一覧だけ）")
    a = ap.parse_args(argv)
    root = Path(a.root)
    if a.cmd == "count":
        from nest import connections
        d = driver or connections.driver("personal")
        out = backup.counts(d)
        if not out["ok"]:
            print("止めた：" + "；".join(out["errors"]))
            return 1
        print("数：" + "・".join("%s %d" % kv for kv in out["counts"].items()))
        return 0
    image = backup.personal_image((REPO / "docker-compose.yml").read_text(encoding="utf-8"))
    if a.cmd == "list":
        for g in backup.generations(root):
            print(g.name)
        return 0
    if a.cmd == "prune":
        if not a.before:
            ap.error("prune には --before <世代>（list で出る名前）が要る")
        out = backup.prune(root, a.before, write=a.write)
        if out["ok"]:
            print("%s：%s" % ("消した世代" if out["written"] else "消す世代（試し。何も消していない）",
                             "・".join(out["removed"]) or "なし"))
            print("残った世代：" if out["written"] else "残す世代：", "・".join(out["kept"]), sep="")
    elif a.cmd == "dump":
        out = backup.dump(root, a.data, image, now=datetime.now())
        if out["ok"]:
            print("取った：%s/%s（消した古い世代：%s）" % (root, out["generation"], "・".join(out["removed"]) or "なし"))
    else:
        if not a.generation:
            ap.error("restore には世代（list で出る名前）が要る")
        out = backup.restore(root / a.generation, a.data, image)
        if out["ok"]:
            print("戻した：%s。DB を起こしてから uv run python scripts/backup.py count で数を見て、戻す前の数と比べる" % a.generation)
    if not out["ok"]:
        print("止めた：" + "；".join(out["errors"]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
