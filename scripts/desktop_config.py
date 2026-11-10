"""Claude Desktop の設定に nest-personal・nest-resource・nest-gate を足す・足したか確かめる（N-46 詰まり #8。2026-11-09 河原さん。
書き込み受付の nest-gate は台帳 G-96 (f)。2026-11-10 河原さん）。

- add：設定（~/Library/Application Support/Claude/claude_desktop_config.json）に 3 つを足す。ほかの道具の設定は消さない。
  このフォルダの完全なパスと、uv の完全なパスを自動で埋める。前の設定は同じ場所に .bak として残す。
  設定が JSON として読めなければ、何も書かずに止める
- check：3 つがあり、このフォルダと、在る uv を指しているかを確かめる。nest-gate の職員の ID は scripts/gate_staff.py で設定する

使い方:
  uv run python scripts/desktop_config.py add
  uv run python scripts/desktop_config.py check
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
MODULES = {"nest-personal": "nest.mcp_personal", "nest-resource": "nest.mcp_resource", "nest-gate": "nest.mcp_gate"}
NAMES = "・".join(MODULES)
which = shutil.which


def _entry(uv, module):
    return {"command": uv, "args": ["run", "--quiet", "--directory", str(REPO), "python", "-m", module]}


def _read(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("中身が JSON のオブジェクトでない")
    return data


def add(path):
    uv = which("uv")
    if not uv:
        print("止めた：uv が見つからない（docs/SETUP_GUIDE.md の 0 で uv を入れる）。何も書いていない")
        return 1
    try:
        data = _read(path)
    except ValueError as e:  # json.JSONDecodeError を含む
        print("止めた：Desktop の設定が読めない（%s）。何も書いていない。%s" % (e, path))
        return 1
    servers = data.setdefault("mcpServers", {})
    for name, module in MODULES.items():
        servers[name] = _entry(uv, module)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") == text:
            print("足してある（変えていない）：%s" % path)
            return 0
        shutil.copyfile(path, path.with_name(path.name + ".bak"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print("足した：%s（フォルダ %s、uv %s）。Claude Desktop を ⌘Q で終了して起動し直す" % (NAMES, REPO, uv))
    return 0


def check(path):
    try:
        servers = _read(path).get("mcpServers", {})
    except ValueError as e:
        print("足していない：Desktop の設定が読めない（%s）" % e)
        return 1
    bad = []
    for name, module in MODULES.items():
        e = servers.get(name)
        args = (e or {}).get("args", [])
        if not e:
            bad.append("%s が無い" % name)
        elif "--directory" not in args or args[args.index("--directory") + 1:][:1] != [str(REPO)]:
            bad.append("%s がこのフォルダを指していない" % name)
        elif not Path(e.get("command", "")).is_file():
            bad.append("%s の uv が見つからない" % name)
    if bad:
        print("足していない：" + "、".join(bad) + "。uv run python scripts/desktop_config.py add を打つ")
        return 1
    print("足してある：%s（%s）" % (NAMES, path))
    return 0


def main(argv=None, path=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["add", "check"])
    a = ap.parse_args(argv)
    path = Path(path) if path else DEFAULT
    return add(path) if a.action == "add" else check(path)


if __name__ == "__main__":
    sys.exit(main())
