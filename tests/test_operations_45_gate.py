"""手順書 4.5 を書き込み受付（nest-gate）の流れに書き換えた（2026-11-10 河原さん）。DB を使わない。

(a) 設定を足す（desktop_config.py で nest-gate も足す・gate_staff.py で職員の ID を設定する）
→ (b) Claude Desktop に語りを貼る → 仮名の復唱に「はい」→ 未確定で入る
→ (c) review_proposals.py list で確かめる
scripts/submit_proposal.py は「MCP が使えないときの予備」として 4.5 の末尾に移す。河原さんが Claude Desktop で一巡を確かめた後に外す。
"""
from tests import doc_commands

TEXT = doc_commands.DOC.read_text(encoding="utf-8")


def _section():
    i = TEXT.index("## 4.5")
    return TEXT[i:TEXT.index("\n## ", i)]


def _sub(head):
    s = _section()
    i = s.index(head)
    j = s.find("\n### ", i + 1)
    return s[i:] if j < 0 else s[i:j]


def test_the_steps_are_in_order():
    s = _section()
    order = ["### (a)", "desktop_config.py add", "gate_staff.py set", "### (b)", "貼", "復唱", "「はい」", "未確定",
             "### (c)", "review_proposals.py list", "### MCP が使えないときの予備", "submit_proposal.py"]
    at = 0
    for w in order:  # 前の語より後ろに、次の語がある
        found = s.find(w, at)
        assert found >= 0, "%s が %s より後ろに無い" % (w, s[at - 20:at])
        at = found + len(w)


def test_a_sets_up_the_three_tools_and_the_staff_id():
    a = _sub("### (a)")
    assert "nest-gate" in a and "nest-personal" in a and "nest-resource" in a
    assert "nest-gate.env" in a and "600" in a
    assert "gate_staff.py check" in a
    assert "[3]" in a and "[10]" in a


def test_b_says_to_compare_the_pseudonym_before_answering_yes():
    b = _sub("### (b)")
    for words in ("紙の記録", "一字ずつ", "「はい」", "違", "仮名と件数", "作り直", "手で直さ"):
        assert words in b, words
    assert "submit_proposal" in b and "nest-gate" in b
    assert "submit_proposal.py" not in b


def test_c_checks_the_list():
    c = _sub("### (c)")
    assert "review_proposals.py list" in c and "未確定" in c and "仮名" in c


def test_the_spare_is_last_in_4_5_and_says_when_it_goes():
    s = _section()
    spare = s[s.index("### MCP が使えないときの予備"):]
    assert "\n### " not in spare[5:]
    assert "submit_proposal.py" in spare and "外" in spare and "一巡" in spare


def test_the_spare_lines_still_run_with_the_tool():
    line = doc_commands.lines("submit_proposal.py")
    assert len(line) == 1
    assert TEXT.index(line[0]) > TEXT.index("### MCP が使えないときの予備")


def test_b_follows_the_screen_that_worked():
    """2026-11-11 河原さん：今朝通った形に合わせる。アプリで「新規作成」→「プロジェクトまたはフォルダー」は選ばない→右下は「手動」のまま。
    区別として残すのは「ターミナルで claude と打って起動したものには nest-gate がつながっていない」だけ。選んだ場合のことは書かない。"""
    b = _sub("### (b)")
    for words in ("新規作成", "「プロジェクトまたはフォルダー」", "選ばず", "「手動」", "ターミナルで `claude` と打って起動したもの"):
        assert words in b, words
    assert "フォルダーを選ばせる画面" not in b and "Claude Code" not in b


def test_b_says_to_check_the_pseudonym_before_allowing_the_tool():
    b = _sub("### (b)")
    assert "許可を求められたら、仮名を確かめてから許可する" in b


def test_b_says_to_paste_the_heading_line_with_the_date():
    b = _sub("### (b)")
    assert "見出しの行" in b and "日付" in b and "supportLog" in b


def test_a_says_whose_staff_id_goes_into_gate_staff():
    a = _sub("### (a)")
    assert "案を出す人" in a and "承認する人" in a and "new_staff" in a and "selfApproval" in a
    assert "2 の段で控えた `STF-…`" not in a


def test_b_has_the_round_trip_to_link_the_org():
    """2026-11-11：返事に機関の候補が出たら、番号で選ぶ（無ければ「無い」）。Claude は自分で選ばない。"""
    b = _sub("### (b)")
    for words in ("候補", "番号", "所在地", "サービスの種類", "「無い」", "機関未確定", "link_organization", "選びません"):
        assert words in b, words


def test_c_checks_the_org_with_show():
    c = _sub("### (c)")
    assert "show --id INV-…" in c and "機関未確定" in c
