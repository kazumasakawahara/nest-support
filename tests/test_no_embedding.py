"""N-04：埋め込みを外す（ADR-001 D10、external-api NEXT-06）。

- 埋め込みの呼び出し・ベクトルの書き込み・ベクトル索引の作成と照会が、コードに残っていない
- Gemini の入口（get_genai_client）を NEXT-06 で呼ぶ箇所が残っていない。行は文字列で直接渡す（行を計算で作ると検査をすり抜けるため）
- 外したファイルが戻っていない
"""
import re
import subprocess

from nest import egress

REPO = egress.REPO

CODE_SUFFIXES = (".py", ".cypher", ".sh", ".ps1", ".js", ".toml", ".yml", ".yaml", ".json")
# .env.example は読み取りの権限で開けなかったため外す（台帳 G-32。河原さんが直す）
CODE_FILES_EXTRA = ()
# 一覧そのもの（egress）と試験は、やめた行の名前を持つので除く
EXCLUDE = ("tests/", "nest/egress.py")

FORBIDDEN = [
    re.compile(r"embed_content"),
    re.compile(r"setNodeVectorProperty"),
    re.compile(r"VECTOR\s+INDEX", re.I),
    re.compile(r"db\.index\.vector"),
    re.compile(r"lib\.embedding"),
    re.compile(r"GEMINI_EMBED_MODEL"),
    re.compile(r"NEXT-06"),
]

REMOVED = [
    "lib/embedding.py",
    "scripts/backfill_embeddings.py",
    "scripts/check_weight_consistency.py",
]


def code_files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], capture_output=True, text=True,
                         cwd=REPO, check=True).stdout.split("\n")
    for p in out:
        if not p or p.startswith(EXCLUDE):
            continue
        if p.endswith(CODE_SUFFIXES) or p in CODE_FILES_EXTRA:
            if (REPO / p).is_file():
                yield p


def test_removed_files_are_gone():
    assert [p for p in REMOVED if (REPO / p).exists()] == []


def test_no_embedding_calls_or_vector_indexes_in_code():
    hits = []
    for p in code_files():
        text = (REPO / p).read_text(encoding="utf-8", errors="replace")
        for pat in FORBIDDEN:
            for m in pat.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append("%s:%d %s" % (p, line, pat.pattern))
    assert hits == []


def test_gemini_entry_is_called_with_literal_open_rows_only():
    call = re.compile(r"get_genai_client\(")
    literal = re.compile(r'get_genai_client\(\s*"(NEXT-\d+)"\s*\)')
    rows, nonliteral = [], []
    for p in code_files():
        if not p.endswith(".py"):
            continue
        text = (REPO / p).read_text(encoding="utf-8")
        for m in call.finditer(text):
            if text[max(0, m.start() - 4):m.start()] == "def ":
                continue
            lm = literal.match(text, m.start())
            if lm:
                rows.append((p, lm.group(1)))
            else:
                nonliteral.append(p)
    assert nonliteral == []
    assert rows, "呼び出しが一つも見つからない（検査が働いていない）"
    # NEXT-07（構造化）は N-05 で外した（tests/test_no_structurize.py）
    assert {r for _, r in rows} <= {"NEXT-03", "NEXT-04"}
