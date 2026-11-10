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
    "scripts/backup.py count",
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


# 詰まり #6 の続き（注意）：試走の環境は「LINE設定: 設定済み」。SOS のボタンを押したとき（POST /api/sos）、
# NEXT-05 の歯止めが止めれば LINE へ送る関数（httpx）が呼ばれないことを、本物に送らずに確かめる。

LINE_URL = "https://api.line.me/v2/bot/message/push"


class _Sent:
    """httpx.AsyncClient の代わり。作られた回数と送った先を数える（外へは出さない）"""
    made, posts = 0, []

    def __init__(self, *a, **k):
        _Sent.made += 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        _Sent.posts.append(url)

        class R:
            status_code = 200
            text = ""
        return R()


@pytest.fixture
def sos_press(monkeypatch):
    """SOS のボタンを押したのと同じ POST /api/sos。LINE の鍵は架空の値（鍵がある状態にする）"""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    import sos.api_server as sos
    _Sent.made, _Sent.posts = 0, []
    monkeypatch.setattr(sos.httpx, "AsyncClient", _Sent)
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy-not-a-token")
    monkeypatch.setenv("LINE_GROUP_ID", "dummy-group")
    client = TestClient(sos.app)
    return lambda: client.post("/api/sos", json={"client_id": "C-ZZZZZZ"})


def test_sos_press_does_not_send_when_egress_denies(sos_press, monkeypatch):
    """(1) egress.ensure が止めたら、送る関数は作られもしない。応答は失敗"""
    from nest import egress
    calls = []

    def deny(row, url):
        calls.append((row, url))
        raise egress.EgressDenied("（試験）止めた")
    monkeypatch.setattr(egress, "ensure", deny)
    resp = sos_press()
    assert calls == [("NEXT-05", LINE_URL)]
    assert _Sent.made == 0 and _Sent.posts == []
    assert resp.status_code == 500


def test_sos_press_would_send_if_egress_allowed(sos_press, monkeypatch):
    """対照：歯止めが通せば、偽の httpx に一度だけ届く（上の試験が送信を見逃していないことの確かめ）"""
    from nest import egress
    monkeypatch.setattr(egress, "ensure", lambda row, url: None)
    resp = sos_press()
    assert _Sent.posts == [LINE_URL] and resp.status_code == 200


def test_sos_press_does_not_send_in_the_current_state_without_the_files(sos_press, monkeypatch):
    """(2) 今の状態：機能の設定と契約の確認の記録が本物の置き場所に無い。差し替えずに押しても送らない。
    ファイルがあれば中身を読まずに飛ばす（~/.config/nest/ を読まないため）"""
    from nest import egress
    present = [p.name for p in (egress.features_path(), egress.record_path()) if p.exists()]
    if present:
        pytest.skip("置き場所にファイルがある（%s）。読まずに飛ばす" % "、".join(present))
    denied = []
    real = egress.ensure

    def watch(row, url):
        try:
            real(row, url)
        except egress.EgressDenied as e:
            denied.append(str(e))
            raise
    monkeypatch.setattr(egress, "ensure", watch)
    resp = sos_press()
    assert denied, "歯止めが止めなかった"
    assert _Sent.made == 0 and _Sent.posts == []
    assert resp.status_code == 500


# 詰まり #14：段 8 の「消した後」に、古い世代を消すコマンドが無く、rm を手で打つことになっていた。

def _section(title):
    from doc_commands import DOC
    t = DOC.read_text(encoding="utf-8")
    i = t.index(title)
    return t[i:t.find("\n## ", i + 1)]


def test_section_8_after_purge_is_a_box_of_commands_in_order():
    """段 8：消した後 → 新しいバックアップを取る → 戻せることを確かめる → 古い世代を試しに一覧 → 消す、が枠の行で並ぶ"""
    import re
    sec = _section("## 8. 本人を廃棄する")
    lines = [l.split("  #")[0].strip() for b in re.findall(r"```bash\n(.*?)```", sec, re.S) for l in b.splitlines()]
    lines = [l for l in lines if l and not l.startswith("#")]
    order = ["purge --admin STF-… --code C-…… --write", "backup.py dump", "backup.py restore", "backup.py prune --before",
             "backup.py prune --before <新しい世代> --write"]
    pos = [next((i for i, l in enumerate(lines) if k in l), None) for k in order]
    assert None not in pos, list(zip(order, pos))
    assert pos == sorted(pos) and pos[3] < pos[4]
    assert not any(l.startswith("rm ") for l in lines)


def test_section_8_prune_lines_delete_only_the_generation_before_the_new_one(tmp_path, capsys):
    """段 8 の prune の 2 行をそのまま流す：試しでは何も消えず、--write で廃棄の前の世代だけが消え、残った世代が出る"""
    from doc_commands import argv, lines, load
    root = tmp_path / "bk"
    for n in ("20261110-114507", "20261110-121315"):
        (root / n).mkdir(parents=True)
        (root / n / "neo4j.dump").write_bytes(b"x")
    prune = [l for l in lines("backup.py") if " prune " in l]
    assert len(prune) == 2, prune
    mod = load("backup.py")
    fill = {"<新しい世代>": "20261110-121315"}
    assert mod.main(argv(prune[0], fill) + ["--root", str(root)]) == 0
    assert sorted(p.name for p in root.iterdir()) == ["20261110-114507", "20261110-121315"]
    dry = capsys.readouterr().out
    assert "20261110-114507" in dry and "消していない" in dry
    assert mod.main(argv(prune[1], fill) + ["--root", str(root)]) == 0
    assert [p.name for p in root.iterdir()] == ["20261110-121315"]
    out = capsys.readouterr().out
    assert "残った世代" in out and "20261110-121315" in out


def test_purge_client_after_write_shows_the_backup_commands(monkeypatch, capsys):
    """段 8 (3) の後の案内が、取る・戻せるか確かめる・古い世代を消すコマンドを具体的に示す"""
    from types import SimpleNamespace
    from doc_commands import load
    mod = load("purge_client.py")
    done = {"ok": True, "written": True, "purgedCounts": [], "voiceFiles": 0, "voiceFilesRemoved": 0, "errors": [],
            "providedRecords": 0, "keptPersons": 0, "keptLinked": [], "retentionId": "RD-1", "auditId": "AUD-1"}
    monkeypatch.setattr(mod.purge, "purge", lambda *a, **k: done)
    mod._purge(None, SimpleNamespace(admin="STF-1", code="C-ABCDEF", write=True, confirm="C-ABCDEF"))
    out = capsys.readouterr().out
    for k in ("scripts/backup.py dump", "scripts/backup.py restore", "scripts/backup.py prune --before", "--write"):
        assert k in out, k


# 詰まり #13：段 7 の「戻ったことを、知っている本人で確かめる」は、戻す前の DB にも同じ本人がいるので区別できない。

def _box_lines(sec, which=None):
    import re
    blocks = re.findall(r"```bash\n(.*?)```", sec, re.S)
    if which is not None:
        blocks = [blocks[which]]
    out = []
    for b in blocks:
        for l in b.splitlines():
            code, _, note = l.partition("  #")
            if code.strip() and not code.strip().startswith("#"):
                out.append((code.strip(), note.strip()))
    return out


def _restore_box():
    sec = _section("## 7. バックアップを取る・戻す")
    return _box_lines(sec[sec.index("戻すとき"):], 0)


def test_section_7_restore_compares_counts_and_finds_the_added_fictitious_client():
    """段 7 の戻す枠：数を控える →（試走のときだけ）架空の本人を足す → down → restore → up → 数 → 足した本人が find で見つからない
    （#12 で、up -d の直後に待つ count を置くため、数を控えてから足す順にした）"""
    lines = [c for c, _ in _restore_box()]
    def at(k, start=0):
        return next(i for i, l in enumerate(lines) if k in l and i >= start)
    add = at("new_client.py add")
    before = at("backup.py count")
    down = at(" down")
    restore = at("backup.py restore")
    up = at(" up -d", restore)
    after = at("backup.py count", up)
    find = at("new_client.py find", after)
    assert before < add < down < restore < up < after < find
    import shlex
    a, f = shlex.split(lines[add]), shlex.split(lines[find])
    assert a[a.index("--family") + 1] == f[f.index("--family") + 1] and a[a.index("--given") + 1] == f[f.index("--given") + 1]


def test_section_7_trial_lines_are_marked_and_the_known_client_check_is_gone():
    box = _restore_box()
    for code, note in box:
        if "new_client.py" in code:
            assert "試走のときだけ" in note, code
    assert not any("知っている本人" in n for _, n in box)
    sec = _section("## 7. バックアップを取る・戻す")
    assert "「戻した：" in sec and "先に進まない" in sec


def test_section_8_after_purge_checks_counts_and_the_purged_client_is_not_found():
    """段 8 の消した後：restore → up → 数 → 廃棄した本人が find で見つからない"""
    sec = _section("## 8. 本人を廃棄する")
    box = _box_lines(sec, 1)
    lines = [c for c, _ in box]
    r = next(i for i, l in enumerate(lines) if "backup.py restore" in l)
    rest = lines[r:]
    up = next(i for i, l in enumerate(rest) if l.endswith(" up -d"))
    cnt = next(i for i, l in enumerate(rest) if "backup.py count" in l)
    fnd = next(i for i, l in enumerate(rest) if "new_client.py find" in l)
    assert up < cnt < fnd
    assert "見つからない" in box[r + fnd][1] and "廃棄" in box[r + fnd][1]


# 詰まり #12：restore に「20261110」と打って止まった。<日時> の形が手順書に無かった。up -d の直後の道具が再試行の行を出した。

def test_restore_lines_say_to_type_the_name_from_list_with_an_example():
    import re
    for sec in ("## 7. バックアップを取る・戻す", "## 8. 本人を廃棄する"):
        for code, note in _box_lines(_section(sec)):
            if "backup.py restore" in code:
                assert re.search(r"\d{8}-\d{6}", note) and ("list" in note or "取った" in note), (sec, note)


def test_every_up_in_sections_7_and_8_is_followed_by_count_which_waits():
    """起動を待つのは道具の側（count が起ききるまで待つ）。up -d の次の行は count"""
    for sec in ("## 7. バックアップを取る・戻す", "## 8. 本人を廃棄する"):
        lines = [c for c, _ in _box_lines(_section(sec))]
        for i, l in enumerate(lines):
            if l.endswith(" up -d"):
                assert i + 1 < len(lines) and "backup.py count" in lines[i + 1], (sec, lines[i + 1:i + 2])
    assert "待" in _section("## 7. バックアップを取る・戻す")
