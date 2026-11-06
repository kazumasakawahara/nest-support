"""field-ui の音声を消す（計画 N-37。決まりは nest/voice.py の先頭）。

承認された記録（その documentHash の Record が Active）の音声と、置いてから 30 日を過ぎた音声を消す。
DB の Record（documentHash を含む）には触れない。DB を読めなくても、30 日を過ぎたものは消す。

使い方:
  uv run python scripts/purge_voice.py            # 数えるだけ（消さない）
  uv run python scripts/purge_voice.py --write    # 消す
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest import voice  # noqa: E402


def main(argv=None, driver=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--root", default=str(voice.VOICE_DIR))
    a = ap.parse_args(argv)

    def approved_of(hashes):
        if driver is not None:
            return voice.approved_hashes(driver, hashes)
        from nest import connections
        with connections.driver("personal") as d:
            return voice.approved_hashes(d, hashes)

    out = voice.purge(Path(a.root), approved_of, write=a.write)
    for e in out["errors"]:
        print("注意：" + e)
    verb = "消した" if a.write else "消すもの（まだ消していない。--write で消す）"
    print("%s：承認済み %d 件・30 日過ぎ %d 件。残す %d 件" % (verb, len(out["approved"]), len(out["expired"]), len(out["kept"])))
    for name in out["approved"]:
        print("  承認済み  " + name)
    for name in out["expired"]:
        print("  30 日過ぎ " + name)
    return 1 if out["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
