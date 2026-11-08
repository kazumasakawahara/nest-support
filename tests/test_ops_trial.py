"""N-46 運用の試走（2026-11-08 河原さん）。詰まりの知らせごとに、手順書のコマンドをそのまま流す形で固定する。

詰まり #1：段 1 の枠に up と down が並び、上から全部打つと DB が止まったまま段 2 に進んでしまった。
手順書の枠を上から順に流したとき、DB を使う道具の時点で DB が起きていること、終わりに止まることを確かめる。
"""
from doc_commands import all_lines

# DB が起きていないと動かない道具
NEEDS_UP = (
    "./scripts/doctor.sh",
    "scripts/bootstrap_admin.py",
    "scripts/new_staff.py",
    "scripts/new_client.py",
    "scripts/review_proposals.py",
    "scripts/purge_client.py",
    "field-ui/server.py",
    "api_server.py",
)
# DB を止めてから使う道具
NEEDS_DOWN = ("scripts/backup.py dump", "scripts/backup.py restore")


def _walk():
    up = False
    trouble = []
    for line in all_lines():
        if line.startswith("docker compose") and line.endswith(" up -d"):
            up = True
        elif line.startswith("docker compose") and line.endswith(" down"):
            up = False
        elif any(n in line for n in NEEDS_UP) and not up:
            trouble.append(("DB が止まっている", line))
        elif any(n in line for n in NEEDS_DOWN) and up:
            trouble.append(("DB が起きている", line))
    return trouble, up


def test_db_is_up_whenever_a_tool_needs_it_in_doc_order():
    """詰まり #1：段 1 の枠を全部打っても、段 2 の bootstrap_admin の時点で DB が起きている"""
    trouble, _ = _walk()
    assert trouble == []


def test_doc_ends_with_the_db_stopped():
    """止める操作は消さずに、手順書の終わりの段に置く（その日の作業の終わりに止める）"""
    _, up = _walk()
    assert up is False
