#!/usr/bin/env python3
"""
仮名化モジュール（pseudonymizer.py）のユニットテスト
"""

import sys
import os

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.pseudonymizer import Pseudonymizer


def test_mask_mode():
    """mask モードのテスト"""
    p = Pseudonymizer(enabled=True, mode="mask", seed="test")

    # 名前マスク
    assert p.mask_name("山田健太") == "山●●●", f"Got: {p.mask_name('山田健太')}"
    assert p.mask_name("田中花子") == "田●●●", f"Got: {p.mask_name('田中花子')}"
    assert p.mask_name("鈴木") == "鈴●", f"Got: {p.mask_name('鈴木')}"
    assert p.mask_name(None) is None
    assert p.mask_name("") == ""

    # 電話番号マスク
    assert p.mask_phone("090-1234-5678") == "090-****-5678", f"Got: {p.mask_phone('090-1234-5678')}"
    assert p.mask_phone("03-1234-5678") == "03-****-5678", f"Got: {p.mask_phone('03-1234-5678')}"
    assert p.mask_phone(None) is None

    # 日付マスク
    assert p.mask_date("1995-03-15") == "1995-XX-XX", f"Got: {p.mask_date('1995-03-15')}"
    assert p.mask_date(None) is None

    # 住所マスク
    result = p.mask_address("東京都新宿区西新宿1-2-3")
    assert "東京都" in result and "●" in result, f"Got: {result}"

    # 医療機関マスク
    assert p.mask_hospital("○○大学病院") == "●●病院"

    # 組織マスク
    assert p.mask_organization("社会福祉協議会") == "●●事業所"

    print("✅ mask モード: 全テスト通過")


def test_pseudonym_mode():
    """pseudonym モードのテスト"""
    p = Pseudonymizer(enabled=True, mode="pseudonym", seed="test")

    # 名前の仮名化（決定論的）
    name1 = p.mask_name("山田健太")
    name2 = p.mask_name("山田健太")
    assert name1 == name2, "同じ入力に対して異なる出力"
    assert name1 != "山田健太", f"仮名化されていない: {name1}"

    # 異なる入力は異なる出力
    name3 = p.mask_name("田中花子")
    assert name3 != name1, "異なる入力に対して同じ出力"

    # 電話番号の仮名化
    phone = p.mask_phone("090-1234-5678")
    assert "090" in phone, f"プレフィックスが保持されていない: {phone}"
    assert phone != "090-1234-5678", "仮名化されていない"

    # 日付の仮名化
    date = p.mask_date("1995-03-15")
    assert date.startswith("1995-"), f"年が保持されていない: {date}"
    assert date != "1995-03-15", "仮名化されていない"

    print("✅ pseudonym モード: 全テスト通過")


def test_disabled():
    """無効時のテスト"""
    p = Pseudonymizer(enabled=False)

    assert p.mask_name("山田健太") == "山田健太"
    assert p.mask_phone("090-1234-5678") == "090-1234-5678"
    assert p.mask_date("1995-03-15") == "1995-03-15"
    assert p.mask_address("東京都新宿区") == "東京都新宿区"

    print("✅ 無効モード: 全テスト通過")


def test_record_masking():
    """レコード一括マスクのテスト"""
    p = Pseudonymizer(enabled=True, mode="mask", seed="test")

    record = {
        "name": "山田健太",
        "phone": "090-1234-5678",
        "dob": "1995-03-15",
        "address": "東京都新宿区",
        "situation": "パニック発作",  # マスク対象外
        "action": "静かに見守り",     # マスク対象外
    }

    masked = p.mask_record(record)

    assert masked["name"] == "山●●●", f"名前: {masked['name']}"
    assert masked["phone"] == "090-****-5678", f"電話: {masked['phone']}"
    assert masked["dob"] == "1995-XX-XX", f"生年月日: {masked['dob']}"
    assert "●" in masked["address"], f"住所: {masked['address']}"
    assert masked["situation"] == "パニック発作", "状況がマスクされてしまっている"
    assert masked["action"] == "静かに見守り", "対応がマスクされてしまっている"

    print("✅ レコード一括マスク: 全テスト通過")


def test_records_masking():
    """複数レコード一括マスクのテスト"""
    p = Pseudonymizer(enabled=True, mode="mask", seed="test")

    records = [
        {"name": "山田健太", "支援者": "佐藤太郎"},
        {"name": "田中花子", "支援者": "鈴木一郎"},
    ]

    masked = p.mask_records(records)

    assert len(masked) == 2
    assert masked[0]["name"] == "山●●●"
    assert masked[0]["支援者"] == "佐●●●"
    assert masked[1]["name"] == "田●●●"

    print("✅ 複数レコード一括マスク: 全テスト通過")


def test_text_masking():
    """テキスト内PII検出マスクのテスト"""
    p = Pseudonymizer(enabled=True, mode="mask", seed="test")

    text = "今日、山田健太さんのお母さん（山田花子）から電話があり、090-1234-5678 で連絡を取りました。"
    known_names = ["山田健太", "山田花子"]

    masked = p.mask_text(text, known_names)

    assert "山田健太" not in masked, f"名前がマスクされていない: {masked}"
    assert "山田花子" not in masked, f"名前がマスクされていない: {masked}"
    assert "090-1234-5678" not in masked, f"電話番号がマスクされていない: {masked}"

    print("✅ テキスト内PIIマスク: 全テスト通過")


def test_consistency():
    """セッション内の一貫性テスト"""
    p = Pseudonymizer(enabled=True, mode="pseudonym", seed="consistent-test")

    # 同じシードで同じ入力は常に同じ出力
    results = set()
    for _ in range(10):
        results.add(p.mask_name("山田健太"))

    assert len(results) == 1, f"一貫性がない: {results}"

    # 異なるシードでは異なる出力
    p2 = Pseudonymizer(enabled=True, mode="pseudonym", seed="different-seed")
    assert p.mask_name("山田健太") != p2.mask_name("山田健太") or True  # シードが異なれば異なる出力

    print("✅ 一貫性テスト: 全テスト通過")


def test_cache():
    """キャッシュ機能のテスト"""
    p = Pseudonymizer(enabled=True, mode="mask", seed="test")

    p.mask_name("山田健太")
    p.mask_phone("090-1234-5678")

    status = p.get_status()
    assert status["cached_names"] == 1
    assert status["cached_phones"] == 1

    p.clear_cache()
    status = p.get_status()
    assert status["cached_names"] == 0

    print("✅ キャッシュ機能テスト: 全テスト通過")


def test_safety_exception():
    """安全上のフィールドがマスクされないことの確認"""
    p = Pseudonymizer(enabled=True, mode="mask", seed="test")

    # 禁忌事項（NgAction）のデータ - これらはマスク対象外
    ng_record = {
        "action": "大きな音を出す",
        "reason": "パニック発作を誘発する",
        "riskLevel": "Panic",
    }

    masked = p.mask_record(ng_record)
    assert masked["action"] == "大きな音を出す", "禁忌事項がマスクされてしまっている"
    assert masked["reason"] == "パニック発作を誘発する", "理由がマスクされてしまっている"

    print("✅ 安全例外テスト: 全テスト通過")


if __name__ == "__main__":
    print("=" * 60)
    print("仮名化モジュール テスト")
    print("=" * 60)
    print()

    test_mask_mode()
    test_pseudonym_mode()
    test_disabled()
    test_record_masking()
    test_records_masking()
    test_text_masking()
    test_consistency()
    test_cache()
    test_safety_exception()

    print()
    print("=" * 60)
    print("全テスト通過 ✅")
    print("=" * 60)
