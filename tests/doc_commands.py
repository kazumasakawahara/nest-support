"""手順書（docs/OPERATIONS.md）に書いたコマンドを、そのまま流すための部品（段階 I。2026-11-06 河原さん）。

手順書の ```bash の枠から `uv run python scripts/<名前>` で始まる行を取り、注釈（#…）を外して、
置き換えの表（例：{"STF-…": 職員 ID}）で書きかけの印を埋め、道具の main に渡す引数にする。
"""
import importlib.util
import re
import shlex
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "OPERATIONS.md"


def lines(script):
    text = DOC.read_text(encoding="utf-8")
    out = []
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        for line in block.splitlines():
            line = line.split("  #")[0].strip()
            if line.startswith("uv run python scripts/%s " % script) or line == "uv run python scripts/%s" % script:
                out.append(line)
    return out


def argv(line, fill):
    words = shlex.split(line)[4:]
    return [fill.get(w, w) for w in words]


def load(script):
    spec = importlib.util.spec_from_file_location(script.replace(".py", "") + "_doc", REPO / "scripts" / script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
