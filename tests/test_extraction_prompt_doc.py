"""N-26：EXTRACTION_PROMPT の書き直し。原文に無い値で埋める指示を消す。DB を使わない。

- 「明確でない場合は Neutral とする」のような、分からない値を決まった値で埋める指示が無い
- 前の形（temp_id の nodes・relationships、前の正典のラベル）を出させない。案の形は narrative-extractor の SKILL.md に一本化する
- 例に人の名前（それらしい実名）を書かない
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC = (REPO / "docs" / "EXTRACTION_PROMPT.md").read_text(encoding="utf-8")


def test_no_instruction_to_fill_unknown_values():
    for phrase in ("明確でない場合は", "とする。", "最も近い値を選択", "読み取り、"):
        assert phrase not in DOC, phrase


def test_no_old_output_shape_or_old_labels():
    for word in ("temp_id", "source_temp_id", "KeyPerson", "Supporter", "ServiceProvider", "SupportLog", "LOGGED",
                 "HAS_KEY_PERSON", "emotion", "triggerTag", "山田", "鈴木"):
        assert word not in DOC, word


def test_points_to_the_one_proposal_format_and_states_the_rules():
    for words in (("claude-skills/narrative-extractor/SKILL.md",), ("原文に無い", "書かない"), ("quote", "そのまま"),
                  ("【", "確度"), ("ゲート", "Pending"), ("役割の名前",)):
        assert all(w in DOC for w in words), words
