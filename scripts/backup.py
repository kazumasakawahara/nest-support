"""個人の側の DB のバックアップ（計画 N-33。決まりは nest/backup.py の先頭、docs/PRIVACY_GUIDELINES.md §5）。

使い方（個人の側の DB を止めてから）:
  docker compose --env-file ~/.config/nest/neo4j-redesign.env down
  uv run python scripts/backup.py dump                       # ~/nest-backup/<日時>/neo4j.dump。世代は 4 つ
  uv run python scripts/backup.py list
  uv run python scripts/backup.py restore <日時>              # 今の個人の側を、その世代で置き換える
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest import backup  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dump", "list", "restore"])
    ap.add_argument("generation", nargs="?")
    ap.add_argument("--root", default=str(backup.DEFAULT_ROOT))
    ap.add_argument("--data", default=str(backup.DEFAULT_DATA))
    a = ap.parse_args(argv)
    root = Path(a.root)
    image = backup.personal_image((REPO / "docker-compose.yml").read_text(encoding="utf-8"))
    if a.cmd == "list":
        for g in backup.generations(root):
            print(g.name)
        return 0
    if a.cmd == "dump":
        out = backup.dump(root, a.data, image, now=datetime.now())
        if out["ok"]:
            print("取った：%s/%s（消した古い世代：%s）" % (root, out["generation"], "・".join(out["removed"]) or "なし"))
    else:
        if not a.generation:
            ap.error("restore には世代（list で出る名前）が要る")
        out = backup.restore(root / a.generation, a.data, image)
        if out["ok"]:
            print("戻した：%s。DB を起動して確かめる" % a.generation)
    if not out["ok"]:
        print("止めた：" + "；".join(out["errors"]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
