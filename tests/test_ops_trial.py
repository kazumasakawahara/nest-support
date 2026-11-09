"""N-46 運用の試走（2026-11-08 河原さん）。詰まりの知らせごとに、手順書のコマンドをそのまま流す形で固定する。

詰まり #1：段 1 の枠に up と down が並び、上から全部打つと DB が止まったまま段 2 に進んでしまった。
手順書の枠を上から順に流したとき、DB を使う道具の時点で DB が起きていること、終わりに止まることを確かめる。
"""
import pytest

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


# 詰まり #2：試走の DB に試験の残り（架空の職員 22 人など）があり、段 2 の bootstrap_admin が止まった。
# 片づけの段が手順書に無く、既存の Administrator の ID を知る手段も無かった。

def test_trial_cleanup_comes_before_bootstrap_admin():
    """詰まり #2：段 2 より前に、架空の印を置く → 試験の残りを片づける、の順で枠がある"""
    lines = all_lines()
    pos = {k: next((i for i, l in enumerate(lines) if k in l), None)
           for k in ("tests/live_mark.py", "tests/live_cleanup.py", "scripts/bootstrap_admin.py")}
    assert None not in pos.values(), pos
    assert pos["tests/live_mark.py"] < pos["tests/live_cleanup.py"] < pos["scripts/bootstrap_admin.py"]


def test_trial_cleanup_says_not_on_real_data():
    from doc_commands import DOC
    t = DOC.read_text(encoding="utf-8")
    i = t.index("tests/live_cleanup.py")
    sec = t[t.rfind("\n#", 0, i):t.find("\n#", i)]
    assert "実データ" in sec


def test_refused_bootstrap_shows_the_current_administrators():
    """詰まり #2：職員がいて止まったとき、今の Administrator の職員 ID を理由に添える"""
    from nest.gate import bootstrap
    from nest.gate import write as gw

    class Tx:
        def run(self, query, **kw):
            if "count(s)" in query:
                return iter([{"n": 2}])
            if "Administrator" in query:
                return iter([{"staffId": "STF-01AAAAAAAAAAAAAAAAAAAAAAAA"}])
            raise AssertionError("書き込みに進んだ：" + query)

    with pytest.raises(gw.Rejected) as e:
        bootstrap._create(Tx(), {"staffId": "STF-NEW"}, "req", None, None)
    assert "STF-01AAAAAAAAAAAAAAAAAAAAAAAA" in e.value.errors[0]


def test_section_1_tells_about_retry_lines_right_after_up():
    """詰まり #2（あわせて）：up -d の直後に道具を打つと再試行の行が出る。doctor の [2] を待つと書く"""
    from doc_commands import DOC
    t = DOC.read_text(encoding="utf-8")
    s1 = t[t.index("## 1."):t.index("## 2.")]
    assert "retried" in s1 and "[2]" in s1


# 詰まり #3：live_cleanup で DB の職員を消しても、トークンの表には DB にいない職員が残る。扱いが手順書に無かった。

def _trial_section():
    from doc_commands import DOC
    t = DOC.read_text(encoding="utf-8")
    i = t.index("### 試走")
    return t[i:t.index("\n## ", i)]


def test_trial_cleanup_removes_table_rows_with_the_doc_command(tmp_path, capsys):
    """詰まり #3：片づけの小段の staff_token の行をそのまま流すと、DB から消えた職員が表からも消える"""
    import re
    from doc_commands import argv, load
    sec = _trial_section()
    lines = [l.split("  #")[0].strip() for b in re.findall(r"```bash\n(.*?)```", sec, re.S) for l in b.splitlines()]
    remove = [l for l in lines if l.startswith("uv run python scripts/staff_token.py remove")]
    assert remove, "片づけの小段に staff_token.py remove の行が無い"
    st = load("staff_token.py")
    table = tmp_path / "staff.json"
    fake = "STF-0000FAKESTAFF0000000000001"
    assert st.main(["add", fake, "--table", str(table)]) == 0
    assert st.main(argv(remove[0], {"STF-…": fake}) + ["--table", str(table)]) == 0
    capsys.readouterr()
    assert st.main(["list", "--table", str(table)]) == 0
    assert fake not in capsys.readouterr().out


# 詰まり #4：架空の事例の住まいの確度（申告・住民票は未確認）を渡す引数が段 4 に無く、道具は Confirmed に決め打ちしていた。

CERTAINTIES = ["Confirmed", "SelfReport", "Hearsay", "Inference", "Unspecified"]


def _section(head):
    from doc_commands import DOC
    t = DOC.read_text(encoding="utf-8")
    i = t.index(head)
    return t[i:t.index("\n## ", i)]


def test_section_4_lists_how_to_choose_the_residence_certainty():
    """詰まり #4：段 4 に確度の値の選び方を一覧で書く（2026-11-08 河原さん）"""
    s4 = _section("## 4.")
    for value in CERTAINTIES:
        assert "`%s`" % value in s4, value
    for word in ("住民票", "本人の申告", "伝聞", "推定", "分からない", "後から変えられない"):
        assert word in s4, word


def test_section_4_add_command_passes_the_certainty():
    """詰まり #4：段 4 の add の行をそのまま道具に渡すと、住まいの確度が入る"""
    from doc_commands import argv, lines, load
    m = load("new_client.py")
    add = [l for l in lines("new_client.py") if " add " in l]
    assert add and "--address-certainty" in add[0]
    a = m.parse(argv(add[0], {"STF-…": "STF-01AAAAAAAAAAAAAAAAAAAAAAAA", "YYYY-MM-DD": "1998-04-12",
                              "確度": "SelfReport"}))
    req = m.client_request(a, "req-x")
    assert req["nodes"][1]["properties"]["certainty"] == "SelfReport"


# 詰まり #6：SOS を手順書どおり PORT=8010 で起動しても、起動の案内の文が「http://localhost:8000/app/…」のまま。
# 読んだ人が 8000 を開くと、この Mac では open-notebook につながる。

def test_sos_banner_shows_the_port_from_the_doc_command(monkeypatch):
    """詰まり #6：段 5 の SOS の起動の行の PORT をそのまま与えると、案内の URL がそのポートになる"""
    import re
    pytest.importorskip("fastapi")
    import sos.api_server as sos
    s5 = _section("## 5.")
    line = next(l for l in s5.splitlines() if "api_server.py" in l and "PORT=" in l)
    port = re.search(r"PORT=(\d+)", line).group(1)
    monkeypatch.setenv("PORT", port)
    text = "\n".join(sos.banner())
    assert "/app/" in text and "/api/sos" in text
    assert ":%s/" % port in text and ":8000/" not in text
