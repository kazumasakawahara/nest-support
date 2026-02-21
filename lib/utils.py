"""
親亡き後支援データベース - ユーティリティモジュール
共通ヘルパー関数
"""

import re
from datetime import datetime, date


# =============================================================================
# 元号（和暦）定義
# =============================================================================

GENGO_MAP = {
    '明治': {'start': 1868, 'end': 1912},
    '大正': {'start': 1912, 'end': 1926},
    '昭和': {'start': 1926, 'end': 1989},
    '平成': {'start': 1989, 'end': 2019},
    '令和': {'start': 2019, 'end': 9999},
    # 略称対応
    'M': {'start': 1868, 'end': 1912},
    'T': {'start': 1912, 'end': 1926},
    'S': {'start': 1926, 'end': 1989},
    'H': {'start': 1989, 'end': 2019},
    'R': {'start': 2019, 'end': 9999},
}


def convert_wareki_to_seireki(wareki_str: str) -> str | None:
    """
    和暦（元号）を西暦（YYYY-MM-DD形式）に変換

    対応形式:
    - 「昭和50年3月15日」「平成7年12月1日」「令和5年1月10日」
    - 「S50.3.15」「H7.12.1」「R5.1.10」
    - 「昭和50/3/15」「平成7/12/1」
    - 「昭和50-3-15」

    Args:
        wareki_str: 和暦形式の日付文字列

    Returns:
        YYYY-MM-DD形式の西暦文字列、または変換失敗時はNone
    """
    if not wareki_str:
        return None

    wareki_str = wareki_str.strip()

    # パターン1: 「昭和50年3月15日」形式
    pattern1 = r'^(明治|大正|昭和|平成|令和)(\d{1,2})年(\d{1,2})月(\d{1,2})日?$'
    match = re.match(pattern1, wareki_str)
    if match:
        gengo, year, month, day = match.groups()
        return _convert_gengo_to_date(gengo, int(year), int(month), int(day))

    # パターン2: 「S50.3.15」「H7/12/1」「R5-1-10」形式
    pattern2 = r'^([MTSHR])(\d{1,2})[./\-](\d{1,2})[./\-](\d{1,2})$'
    match = re.match(pattern2, wareki_str.upper())
    if match:
        gengo, year, month, day = match.groups()
        return _convert_gengo_to_date(gengo, int(year), int(month), int(day))

    # パターン3: 「昭和50/3/15」「平成7-12-1」形式
    pattern3 = r'^(明治|大正|昭和|平成|令和)(\d{1,2})[./\-](\d{1,2})[./\-](\d{1,2})$'
    match = re.match(pattern3, wareki_str)
    if match:
        gengo, year, month, day = match.groups()
        return _convert_gengo_to_date(gengo, int(year), int(month), int(day))

    return None


def _convert_gengo_to_date(gengo: str, year: int, month: int, day: int) -> str | None:
    """
    元号・年・月・日から西暦日付文字列を生成
    """
    if gengo not in GENGO_MAP:
        return None

    gengo_info = GENGO_MAP[gengo]
    seireki_year = gengo_info['start'] + year - 1

    # 日付の妥当性チェック
    try:
        result_date = date(seireki_year, month, day)
        return result_date.strftime("%Y-%m-%d")
    except ValueError:
        return None


def safe_date_parse(date_str: str) -> date | None:
    """
    日付文字列を安全にパース（元号対応）

    対応形式:
    - 西暦: YYYY-MM-DD, YYYY/MM/DD
    - 和暦: 昭和50年3月15日, S50.3.15, 平成7/12/1 など

    Args:
        date_str: 日付文字列（西暦または和暦）

    Returns:
        dateオブジェクト、またはパース失敗時はNone
    """
    if not date_str:
        return None

    date_str = str(date_str).strip()

    # 1. 西暦YYYY-MM-DD形式
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        pass

    # 2. 西暦YYYY/MM/DD形式
    try:
        return datetime.strptime(date_str, "%Y/%m/%d").date()
    except (ValueError, TypeError):
        pass

    # 3. 和暦形式を西暦に変換して再パース
    seireki = convert_wareki_to_seireki(date_str)
    if seireki:
        try:
            return datetime.strptime(seireki, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass

    return None


def calculate_age(birth_date: date | str, reference_date: date = None) -> int | None:
    """
    生年月日から年齢を計算

    Args:
        birth_date: 生年月日（dateオブジェクトまたは日付文字列）
        reference_date: 基準日（デフォルトは今日）

    Returns:
        年齢（整数）、または計算失敗時はNone
    """
    if birth_date is None:
        return None

    # 文字列の場合はパース
    if isinstance(birth_date, str):
        birth_date = safe_date_parse(birth_date)
        if birth_date is None:
            return None

    if reference_date is None:
        reference_date = date.today()

    # 年齢計算（誕生日前なら-1）
    age = reference_date.year - birth_date.year
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1

    return age if age >= 0 else None


def format_date_with_age(birth_date: date | str) -> str:
    """
    生年月日と年齢を整形して返す

    Args:
        birth_date: 生年月日

    Returns:
        「YYYY-MM-DD（XX歳）」形式の文字列
    """
    if birth_date is None:
        return "不明"

    # 文字列の場合はパース
    if isinstance(birth_date, str):
        parsed = safe_date_parse(birth_date)
        if parsed is None:
            return birth_date  # パース失敗時は元の文字列を返す
        birth_date = parsed

    age = calculate_age(birth_date)
    date_str = birth_date.strftime("%Y-%m-%d")

    if age is not None:
        return f"{date_str}（{age}歳）"
    return date_str
