"""フィクスチャが架空であることの注記を確かめる（N-01）。

実案件のデータをリポジトリに入れないための機械の歯止め。注記があれば架空と見なすだけで、
中身が本当に架空かは人が確かめる。
"""
import json
from pathlib import Path

NOTICE = "架空"
HEAD_LINES = 10
TEXT_SUFFIXES = {".md", ".txt"}


def check_file(path: Path) -> list[str]:
    """問題を文の一覧で返す。空なら通る。"""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        try:
            head = path.read_text(encoding="utf-8").splitlines()[:HEAD_LINES]
        except UnicodeDecodeError:
            return ["%s：UTF-8 で読めない" % path]
        if not any(NOTICE in line for line in head):
            return ["%s：先頭 %d 行に「%s」の注記が無い" % (path, HEAD_LINES, NOTICE)]
        return []
    if suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ["%s：JSON として読めない" % path]
        note = data.get("_fictional") if isinstance(data, dict) else None
        if not isinstance(note, str) or not note.strip():
            return ['%s：最上位に空でない "_fictional" が無い' % path]
        return []
    return ["%s：この拡張子は受け付けない（.md・.txt・.json だけ）" % path]


def check_tree(root: Path) -> list[str]:
    root = Path(root)
    if not root.is_dir():
        return ["%s：フォルダが無い" % root]
    errors = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            errors.extend(check_file(p))
    return errors
