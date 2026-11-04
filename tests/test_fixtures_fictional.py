"""N-01：フィクスチャには架空の注記が要る（実案件のデータをリポジトリに入れない）。

- .md・.txt（語り・面談記録）：先頭 10 行以内に「架空」の語がある
- .json：最上位に空でない "_fictional" がある
- それ以外の拡張子は受け付けない（中身を機械で確かめられないため）
"""
import json
from pathlib import Path

from nest import fixtures_check

REPO = Path(__file__).resolve().parents[1]


def test_text_without_notice_fails(tmp_path):
    p = tmp_path / "narrative.txt"
    p.write_text("母の話。\n朝は大きな音が苦手です。\n", encoding="utf-8")
    assert fixtures_check.check_file(p)


def test_text_with_notice_passes(tmp_path):
    p = tmp_path / "narrative.txt"
    p.write_text("（この語りは架空です）\n母の話。\n", encoding="utf-8")
    assert fixtures_check.check_file(p) == []


def test_markdown_with_notice_passes(tmp_path):
    p = tmp_path / "record.md"
    p.write_text("# 面談記録（架空事例）\n\n- 面談日：2026-10-01\n", encoding="utf-8")
    assert fixtures_check.check_file(p) == []


def test_notice_after_line_10_fails(tmp_path):
    p = tmp_path / "record.md"
    body = "".join("行%d\n" % i for i in range(10)) + "この事例は架空です。\n"
    p.write_text(body, encoding="utf-8")
    assert fixtures_check.check_file(p)


def test_json_without_notice_fails(tmp_path):
    p = tmp_path / "proposal.json"
    p.write_text(json.dumps({"facts": []}), encoding="utf-8")
    assert fixtures_check.check_file(p)


def test_json_with_notice_passes(tmp_path):
    p = tmp_path / "proposal.json"
    p.write_text(json.dumps({"_fictional": "この事例は架空です", "facts": []}, ensure_ascii=False), encoding="utf-8")
    assert fixtures_check.check_file(p) == []


def test_json_with_empty_notice_fails(tmp_path):
    p = tmp_path / "proposal.json"
    p.write_text(json.dumps({"_fictional": "  ", "facts": []}), encoding="utf-8")
    assert fixtures_check.check_file(p)


def test_json_not_object_fails(tmp_path):
    p = tmp_path / "proposal.json"
    p.write_text(json.dumps(["架空"], ensure_ascii=False), encoding="utf-8")
    assert fixtures_check.check_file(p)


def test_broken_json_fails(tmp_path):
    p = tmp_path / "proposal.json"
    p.write_text("{", encoding="utf-8")
    assert fixtures_check.check_file(p)


def test_unknown_extension_fails(tmp_path):
    p = tmp_path / "record.docx"
    p.write_bytes(b"PK")
    assert fixtures_check.check_file(p)


def test_check_tree_reports_each_bad_file(tmp_path):
    (tmp_path / "ok.txt").write_text("架空の語り\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "bad.txt").write_text("本物の語り\n", encoding="utf-8")
    errors = fixtures_check.check_tree(tmp_path)
    assert len(errors) == 1 and "bad.txt" in errors[0]


def test_check_tree_missing_dir_fails(tmp_path):
    assert fixtures_check.check_tree(tmp_path / "none")


def test_repository_fixtures_are_all_fictional():
    errors = fixtures_check.check_tree(REPO / "tests" / "fixtures")
    assert errors == [], "\n".join(errors)
