"""N-41：契約の確認の記録と機能の設定の作り方 docs/EXTERNAL_API_SETUP.md（2026-11-06 河原さん）。

- 先頭の節「記録を作る前に確かめること」に台帳 G-80 の内容（個人向けプランでは満たせない見込み・事業者向けの契約は未決）
- 手順書の例の JSON（記録と設定）は、日付が書きかけ（YYYY-MM-DD）のままでは通らない。日付を入れると通り、鍵が一つ欠けると止まる
- 例の鍵の名前は nest/egress.py の RECORD_FIELDS と同じ。置き場所・権限 600・doctor の項目・確かめ方を書く
- 記録の中身（契約の内容そのもの）は河原さんが書くので、例は書きかけの印（〈…〉）だけ
"""
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from nest import egress

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "EXTERNAL_API_SETUP.md"
TODAY = date(2026, 11, 6)


def _text():
    return DOC.read_text(encoding="utf-8")


def _json_blocks():
    return [json.loads(b) for b in re.findall(r"```json\n(.*?)```", _text(), re.S)]


def _record_example():
    return next(b for b in _json_blocks() if "destinations" in b)


def _features_example():
    return next(b for b in _json_blocks() if "destinations" not in b)


def _put(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.chmod(p, 0o600)
    return p


def _filled(rec):
    rec = json.loads(json.dumps(rec))
    for entry in rec["destinations"].values():
        entry["checkedOn"] = TODAY.isoformat()
        entry["nextReviewOn"] = (TODAY + timedelta(days=180)).isoformat()
    return rec


def test_first_section_is_what_to_check_before_writing_with_g80():
    t = _text()
    first = re.search(r"^## (.+)$", t, re.M).group(1)
    assert "記録を作る前に確かめること" in first
    body = t[t.index(first):t.index("\n## ", t.index(first))]
    assert "G-80" in body and "個人向けプラン" in body and "事業者向け" in body and "未決" in body


def test_example_record_uses_exactly_the_record_fields():
    rec = _record_example()
    assert rec["version"] == egress.RECORD_VERSION
    for row, entry in rec["destinations"].items():
        assert egress.DESTINATIONS[row].kind == "gated", row
        assert set(entry) == set(egress.RECORD_FIELDS), row


def test_example_record_with_placeholder_dates_is_denied(tmp_path):
    rec = _record_example()
    p = _put(tmp_path, "r.json", rec)
    for row in rec["destinations"]:
        with pytest.raises(egress.EgressDenied):
            egress.check_record(p, row, TODAY)


def test_example_record_with_dates_filled_in_passes(tmp_path):
    rec = _filled(_record_example())
    p = _put(tmp_path, "r.json", rec)
    for row in rec["destinations"]:
        egress.check_record(p, row, TODAY)


def test_example_record_missing_one_key_is_denied(tmp_path):
    rec = _filled(_record_example())
    row = next(iter(rec["destinations"]))
    del rec["destinations"][row]["legalArrangement"]
    with pytest.raises(egress.EgressDenied, match="欠けている"):
        egress.check_record(_put(tmp_path, "r.json", rec), row, TODAY)


def test_example_features_pass_only_for_true_rows(tmp_path):
    feats = _features_example()
    p = _put(tmp_path, "f.json", feats)
    assert any(v is True for v in feats.values()) and any(v is False for v in feats.values())
    for row, on in feats.items():
        if on:
            egress.check_feature(p, row)
        else:
            with pytest.raises(egress.EgressDenied):
                egress.check_feature(p, row)


def test_example_holds_no_contract_content():
    """契約の中身は河原さんが書く。例の文字の項目は書きかけの印だけ"""
    for entry in _record_example()["destinations"].values():
        for key in egress.TEXT_FIELDS:
            assert re.fullmatch(r"〈.+〉", entry[key]), (key, entry[key])


def test_places_permissions_and_checks_are_written():
    t = _text()
    for s in ("~/.config/nest/external-api-record.json", "~/.config/nest/external-api-features.json",
              "chmod 600", "[3]", "egress.authorize", "nextReviewOn"):
        assert s in t, s
