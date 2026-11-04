"""N-02：送信の歯止め（docs/external-api.md v0.3 §5、台帳 G-19）。

架空の記録だけを使う。本物の ~/.config/nest/ は読まない（置き場所の定数を試験の中で差し替える）。
"""
import json
import os
from datetime import date
from pathlib import Path

import pytest

from nest import egress

TODAY = date(2026, 11, 5)


def good_entry(**over):
    e = {
        "checkedBy": "架空 確認者",
        "checkedOn": "2026-11-01",
        "contractName": "架空の契約",
        "contractVersion": "v1",
        "trainingUse": "学習に使わない（架空）",
        "retention": "30 日（架空）",
        "legalArrangement": "委託として整理（架空）",
        "sendsSensitiveData": True,
        "nextReviewOn": "2027-05-01",
    }
    e.update(over)
    return e


def write(path: Path, data, mode=0o600):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.chmod(path, mode)
    return path


@pytest.fixture
def record(tmp_path):
    return write(tmp_path / "record.json", {"version": 1, "destinations": {"NEXT-05": good_entry()}})


# --- 記録：そろえば許可 ---------------------------------------------------------

def test_complete_record_allows(record):
    egress.check_record(record, "NEXT-05", TODAY)  # 例外が出なければ許可


# --- 条件 1：行ごと ----------------------------------------------------------

def test_record_for_other_row_does_not_open(tmp_path):
    p = write(tmp_path / "r.json", {"version": 1, "destinations": {"NEXT-03": good_entry()}})
    with pytest.raises(egress.EgressDenied):
        egress.check_record(p, "NEXT-01", TODAY)


# --- 条件 2：5 項目がすべて埋まる ------------------------------------------------

@pytest.mark.parametrize("key", sorted(egress.RECORD_FIELDS))
def test_missing_field_denies(tmp_path, key):
    e = good_entry()
    del e[key]
    p = write(tmp_path / "r.json", {"version": 1, "destinations": {"NEXT-05": e}})
    with pytest.raises(egress.EgressDenied):
        egress.check_record(p, "NEXT-05", TODAY)


@pytest.mark.parametrize("key", ["checkedBy", "contractName", "contractVersion",
                                 "trainingUse", "retention", "legalArrangement"])
def test_blank_field_denies(tmp_path, key):
    p = write(tmp_path / "r.json", {"version": 1, "destinations": {"NEXT-05": good_entry(**{key: "  "})}})
    with pytest.raises(egress.EgressDenied):
        egress.check_record(p, "NEXT-05", TODAY)


def test_unknown_field_denies(tmp_path):
    p = write(tmp_path / "r.json", {"version": 1, "destinations": {"NEXT-05": good_entry(sendSensitive=True)}})
    with pytest.raises(egress.EgressDenied):
        egress.check_record(p, "NEXT-05", TODAY)


# --- 条件 3：要配慮は明示の true だけ ---------------------------------------------

@pytest.mark.parametrize("value", [False, "true", 1, None])
def test_sensitive_flag_must_be_literal_true(tmp_path, value):
    p = write(tmp_path / "r.json", {"version": 1, "destinations": {"NEXT-05": good_entry(sendsSensitiveData=value)}})
    with pytest.raises(egress.EgressDenied):
        egress.check_record(p, "NEXT-05", TODAY)


# --- 条件 4：次に確かめる日 ------------------------------------------------------

def test_review_date_passed_denies(tmp_path):
    p = write(tmp_path / "r.json", {"version": 1, "destinations": {"NEXT-05": good_entry(nextReviewOn="2026-11-04")}})
    with pytest.raises(egress.EgressDenied):
        egress.check_record(p, "NEXT-05", TODAY)


def test_review_date_today_allows(tmp_path):
    p = write(tmp_path / "r.json", {"version": 1, "destinations": {"NEXT-05": good_entry(nextReviewOn="2026-11-05")}})
    egress.check_record(p, "NEXT-05", TODAY)


@pytest.mark.parametrize("key,value", [("nextReviewOn", "来年"), ("checkedOn", "2026/11/01"),
                                       ("checkedOn", "2026-11-06")])
def test_bad_or_future_dates_deny(tmp_path, key, value):
    p = write(tmp_path / "r.json", {"version": 1, "destinations": {"NEXT-05": good_entry(**{key: value})}})
    with pytest.raises(egress.EgressDenied):
        egress.check_record(p, "NEXT-05", TODAY)


# --- 条件 5：無い・読めない・600 より広い ------------------------------------------

def test_missing_file_denies(tmp_path):
    with pytest.raises(egress.EgressDenied):
        egress.check_record(tmp_path / "none.json", "NEXT-05", TODAY)


def test_unreadable_json_denies(tmp_path):
    p = tmp_path / "r.json"
    p.write_text("{", encoding="utf-8")
    os.chmod(p, 0o600)
    with pytest.raises(egress.EgressDenied):
        egress.check_record(p, "NEXT-05", TODAY)


@pytest.mark.parametrize("mode", [0o644, 0o640, 0o604, 0o700, 0o666])
def test_permissions_wider_than_600_deny(record, mode):
    os.chmod(record, mode)
    with pytest.raises(egress.EgressDenied):
        egress.check_record(record, "NEXT-05", TODAY)


def test_symlink_denies(record, tmp_path):
    link = tmp_path / "link.json"
    link.symlink_to(record)
    with pytest.raises(egress.EgressDenied):
        egress.check_record(link, "NEXT-05", TODAY)


def test_wrong_version_denies(tmp_path):
    p = write(tmp_path / "r.json", {"version": 2, "destinations": {"NEXT-05": good_entry()}})
    with pytest.raises(egress.EgressDenied):
        egress.check_record(p, "NEXT-05", TODAY)


# --- 条件 6：置き場所はコードに固定 ------------------------------------------------

def test_paths_do_not_follow_home_env(monkeypatch, tmp_path):
    before = (egress.record_path(), egress.features_path())
    monkeypatch.setenv("HOME", str(tmp_path))
    assert (egress.record_path(), egress.features_path()) == before
    assert str(tmp_path) not in str(before[0])


def test_paths_are_under_config_nest():
    assert egress.record_path().parent.parts[-2:] == (".config", "nest")
    assert egress.features_path().parent == egress.record_path().parent


# --- 機能ごとの明示の設定 ---------------------------------------------------------

def test_feature_enabled_allows(tmp_path):
    p = write(tmp_path / "f.json", {"NEXT-05": True})
    egress.check_feature(p, "NEXT-05")


@pytest.mark.parametrize("value", [False, "true", 1, None])
def test_feature_must_be_literal_true(tmp_path, value):
    p = write(tmp_path / "f.json", {"NEXT-05": value})
    with pytest.raises(egress.EgressDenied):
        egress.check_feature(p, "NEXT-05")


def test_feature_for_other_row_does_not_open(tmp_path):
    p = write(tmp_path / "f.json", {"NEXT-03": True})
    with pytest.raises(egress.EgressDenied):
        egress.check_feature(p, "NEXT-05")


def test_feature_unknown_row_key_denies(tmp_path):
    p = write(tmp_path / "f.json", {"NEXT-05": True, "NEXT-99": True})
    with pytest.raises(egress.EgressDenied):
        egress.check_feature(p, "NEXT-05")


def test_feature_non_bool_value_for_other_row_denies(tmp_path):
    p = write(tmp_path / "f.json", {"NEXT-05": True, "NEXT-03": "true"})
    with pytest.raises(egress.EgressDenied):
        egress.check_feature(p, "NEXT-05")


def test_feature_explicit_false_for_other_row_allows(tmp_path):
    p = write(tmp_path / "f.json", {"NEXT-05": True, "NEXT-03": False})
    egress.check_feature(p, "NEXT-05")


def test_feature_symlink_and_not_object_deny(tmp_path):
    real = write(tmp_path / "f.json", {"NEXT-05": True})
    link = tmp_path / "link.json"
    link.symlink_to(real)
    with pytest.raises(egress.EgressDenied):
        egress.check_feature(link, "NEXT-05")
    arr = write(tmp_path / "a.json", ["NEXT-05"])
    with pytest.raises(egress.EgressDenied):
        egress.check_feature(arr, "NEXT-05")


def test_feature_file_missing_or_wide_denies(tmp_path):
    with pytest.raises(egress.EgressDenied):
        egress.check_feature(tmp_path / "none.json", "NEXT-05")
    p = write(tmp_path / "f.json", {"NEXT-05": True}, mode=0o644)
    with pytest.raises(egress.EgressDenied):
        egress.check_feature(p, "NEXT-05")


# --- 両方そろうまで送らない（鍵の有無は見ない） ----------------------------------------

@pytest.fixture
def fixed_paths(monkeypatch, tmp_path):
    rec = tmp_path / "record.json"
    feat = tmp_path / "features.json"
    monkeypatch.setattr(egress, "record_path", lambda: rec)
    monkeypatch.setattr(egress, "features_path", lambda: feat)
    monkeypatch.setattr(egress, "today", lambda: TODAY)
    return rec, feat


def test_key_alone_does_not_allow(fixed_paths, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-not-a-key")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy-not-a-token")
    for row in ("NEXT-03", "NEXT-04", "NEXT-05"):
        with pytest.raises(egress.EgressDenied):
            egress.authorize(row)


def test_record_without_feature_denies(fixed_paths):
    rec, _ = fixed_paths
    write(rec, {"version": 1, "destinations": {"NEXT-05": good_entry()}})
    with pytest.raises(egress.EgressDenied):
        egress.authorize("NEXT-05")


def test_feature_without_record_denies(fixed_paths):
    _, feat = fixed_paths
    write(feat, {"NEXT-05": True})
    with pytest.raises(egress.EgressDenied):
        egress.authorize("NEXT-05")


def test_both_allow(fixed_paths):
    rec, feat = fixed_paths
    write(rec, {"version": 1, "destinations": {"NEXT-05": good_entry()}})
    write(feat, {"NEXT-05": True})
    egress.authorize("NEXT-05")
    egress.ensure("NEXT-05", "https://api.line.me/v2/bot/message/push")


# --- 送り先の一覧 ---------------------------------------------------------------

def test_unknown_row_denies():
    with pytest.raises(egress.EgressDenied):
        egress.authorize("NEXT-99")


@pytest.mark.parametrize("row", ["NEXT-06", "NEXT-07", "NEXT-11"])
def test_abolished_rows_deny(row, fixed_paths):
    rec, feat = fixed_paths
    write(rec, {"version": 1, "destinations": {row: good_entry()}})
    write(feat, {row: True})
    with pytest.raises(egress.EgressDenied):
        egress.authorize(row)


@pytest.mark.parametrize("url", ["https://evil.example.com/v2/bot/message/push",
                                 "http://api.line.me/v2/bot/message/push",
                                 "https://api.line.me.evil.example/v2",
                                 "https://generativelanguage.googleapis.com/v1"])
def test_url_outside_row_host_denies(url):
    with pytest.raises(egress.EgressDenied):
        egress.check_url("NEXT-05", url)


def test_open_row_needs_no_record(fixed_paths):
    egress.ensure("NEXT-08", "https://laws.e-gov.go.jp/api/2/laws")


def test_code_table_matches_document():
    doc = egress.rows_from_document(egress.DOCUMENT)
    assert doc == {k: (d.host, d.kind) for k, d in egress.DESTINATIONS.items()}


def test_record_field_table_matches_code():
    assert egress.record_fields_from_document(egress.DOCUMENT) == egress.RECORD_FIELDS


def test_record_field_table_drift_is_detected(tmp_path):
    text = egress.DOCUMENT.read_text(encoding="utf-8").replace("`retention`", "`keepDays`")
    p = tmp_path / "external-api.md"
    p.write_text(text, encoding="utf-8")
    assert egress.record_fields_from_document(p) != egress.RECORD_FIELDS


def test_document_drift_is_detected(tmp_path):
    text = egress.DOCUMENT.read_text(encoding="utf-8").replace("`api.line.me`", "`api.line.example`")
    p = tmp_path / "external-api.md"
    p.write_text(text, encoding="utf-8")
    doc = egress.rows_from_document(p)
    assert doc != {k: (d.host, d.kind) for k, d in egress.DESTINATIONS.items()}
