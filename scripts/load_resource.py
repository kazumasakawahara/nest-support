"""資源の側に、tsunagu-net の配布の一式の資源 DB の書き出しを読み込む入口（N-23）。既定は手順を出すだけ（--write で流す）。

使い方（Mac）:  uv run python scripts/load_resource.py --bundle ~/Dist/tsunagu-net-trial-20261104 [--write]
MANIFEST.json の指紋が合わない書き出しは読み込まない。資源の側のコンテナだけを止めて置き換え、また起動する。個人の側には触れない。
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from nest import resource_load as rl  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    try:
        rec = rl.verify(Path(a.bundle).expanduser())
        steps = rl.steps(Path(a.bundle).expanduser())
    except rl.LoadRefused as e:
        print("読み込まない：%s" % e)
        return 1
    print("書き出し %s（SHA-256 %s…、一式の正典 %s）" % (rec["dump"], rec["sha256"][:12], rec["schemaVersion"]))
    for s in steps:
        print(" ".join(s))
    if not a.write:
        print("流していない（%d 手順。--write で流す）" % len(steps))
        return 0
    rl.STAGE_DIR.mkdir(exist_ok=True)
    for s in steps:
        subprocess.run(s, check=True, cwd=REPO)
    rl.STAGE_DIR.rmdir()
    out = rl.write_record(rec)
    print("読み込んだ：%s（記録 %s）" % (out["schemaVersion"], rl.RECORD))
    return 0


if __name__ == "__main__":
    sys.exit(main())
