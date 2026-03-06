"""
親なき後支援データベース - 仮名化（Pseudonymization）モジュール

研修・説明会・デモで個人情報を使わずにシステムを操作するための
出力レイヤー仮名化機能。Neo4j 内の実データは変更せず、
表示時にのみマスク処理を行う。

使い方:
    from lib.pseudonymizer import Pseudonymizer

    p = Pseudonymizer(enabled=True, mode="mask")
    masked_name = p.mask_name("山田健太")       # → "山●●●"
    masked_phone = p.mask_phone("090-1234-5678") # → "090-****-5678"
    masked_dob = p.mask_date("1995-03-15")       # → "1995-XX-XX"

モード:
    - "mask": 部分マスク（●や*で隠す）- デモ・研修向け
    - "pseudonym": 一貫した仮名に置換 - テスト・開発向け
    - "off": 仮名化なし（通常運用）
"""

import hashlib
import os
import re
from typing import Optional


# =============================================================================
# 仮名辞書（pseudonym モードで使用する架空の名前）
# =============================================================================

# 姓の仮名リスト（50音順で十分な数を用意）
PSEUDO_FAMILY_NAMES = [
    "青山", "石川", "上野", "江藤", "大原",
    "桂", "北村", "草野", "小泉", "桜井",
    "白石", "杉本", "瀬戸", "高原", "千葉",
    "土屋", "手塚", "戸田", "中里", "西村",
    "野口", "橋本", "日野", "福田", "星野",
    "松岡", "三浦", "向井", "望月", "森川",
    "矢島", "結城", "横田", "若林", "渡辺",
]

# 名前の仮名リスト
PSEUDO_GIVEN_NAMES = [
    "あおい", "いつき", "うみ", "えいた", "おうか",
    "かえで", "きよし", "くるみ", "けいこ", "こうた",
    "さくら", "しおり", "すずか", "せいじ", "そうま",
    "たくみ", "ちはる", "つばさ", "てるき", "ともや",
    "なつき", "にこ", "ぬくみ", "ねね", "のぞみ",
    "はると", "ひかり", "ふうか", "へいた", "ほのか",
    "まなみ", "みつき", "むつみ", "めぐみ", "もえか",
]

# 地名の仮名リスト（住所マスク用）
PSEUDO_PLACES = [
    "桜ヶ丘", "緑町", "若葉台", "青葉区", "日の出町",
    "花見川", "光が丘", "泉ヶ丘", "風の杜", "星川",
]

# 医療機関名の仮名リスト
PSEUDO_HOSPITALS = [
    "さくら病院", "あおば医院", "ひかりクリニック",
    "みどり総合病院", "はなみ医療センター",
    "ほしの心療内科", "かえで診療所", "いずみ病院",
]

# 組織名の仮名リスト
PSEUDO_ORGS = [
    "あさひ福祉協議会", "みらい作業所", "ひまわり支援センター",
    "たいよう相談室", "にじいろ事業所", "わかば地域センター",
    "そよかぜの家", "あおぞら支援協会",
]


class Pseudonymizer:
    """
    出力レイヤー仮名化クラス

    セッション内で一貫した仮名を生成するため、
    入力文字列のハッシュをシードとして使用する。
    同じ入力には常に同じ仮名が割り当てられる。
    """

    def __init__(
        self,
        enabled: bool = False,
        mode: str = "mask",
        seed: str = ""
    ):
        """
        Args:
            enabled: 仮名化を有効にするか
            mode: "mask"（部分マスク）, "pseudonym"（仮名置換）, "off"（無効）
            seed: ハッシュのシード値（セッションごとに変えると異なる仮名が生成される）
        """
        self.enabled = enabled and mode != "off"
        self.mode = mode if enabled else "off"
        self.seed = seed or os.getenv("PSEUDONYMIZATION_SEED", "nest-support-demo")

        # キャッシュ（同じ入力 → 同じ出力を保証）
        self._name_cache: dict[str, str] = {}
        self._phone_cache: dict[str, str] = {}
        self._org_cache: dict[str, str] = {}
        self._hospital_cache: dict[str, str] = {}

    # =========================================================================
    # ハッシュベースのインデックス生成
    # =========================================================================

    def _hash_index(self, text: str, list_length: int) -> int:
        """
        テキストのハッシュからリストインデックスを決定論的に生成

        Args:
            text: 入力テキスト
            list_length: 対象リストの長さ

        Returns:
            0〜list_length-1 のインデックス
        """
        h = hashlib.sha256(f"{self.seed}:{text}".encode("utf-8")).hexdigest()
        return int(h[:8], 16) % list_length

    # =========================================================================
    # 名前のマスク・仮名化
    # =========================================================================

    def mask_name(self, name: Optional[str]) -> Optional[str]:
        """
        人名を仮名化する

        mask モード:
            - 「山田健太」→「山●●●」（姓の1文字目のみ残す）
            - 「田中花子」→「田●●●」

        pseudonym モード:
            - 「山田健太」→「青山あおい」（一貫した仮名に置換）

        Args:
            name: 人名

        Returns:
            仮名化された名前、または None
        """
        if not self.enabled or not name:
            return name

        # キャッシュ確認
        if name in self._name_cache:
            return self._name_cache[name]

        if self.mode == "mask":
            result = self._mask_name_partial(name)
        elif self.mode == "pseudonym":
            result = self._pseudonym_name(name)
        else:
            result = name

        self._name_cache[name] = result
        return result

    def _mask_name_partial(self, name: str) -> str:
        """部分マスク: 最初の1文字のみ残し、残りを●に"""
        if len(name) <= 1:
            return "●"

        # 空白区切り（外国人名）の場合
        if " " in name or "　" in name:
            parts = re.split(r'[\s　]+', name)
            return parts[0][0] + "●" * (len(parts[0]) - 1) + " " + "●" * len("".join(parts[1:]))

        # 日本語名: 最初の1文字 + ●
        return name[0] + "●" * (len(name) - 1)

    def _pseudonym_name(self, name: str) -> str:
        """仮名置換: 決定論的に架空の名前を割り当て"""
        family_idx = self._hash_index(name, len(PSEUDO_FAMILY_NAMES))
        given_idx = self._hash_index(name + "_given", len(PSEUDO_GIVEN_NAMES))
        return f"{PSEUDO_FAMILY_NAMES[family_idx]}{PSEUDO_GIVEN_NAMES[given_idx]}"

    # =========================================================================
    # 電話番号のマスク
    # =========================================================================

    def mask_phone(self, phone: Optional[str]) -> Optional[str]:
        """
        電話番号をマスクする

        mask モード:
            - 「090-1234-5678」→「090-****-5678」
            - 「03-1234-5678」→「03-****-5678」

        pseudonym モード:
            - 「090-1234-5678」→「090-0000-0001」（決定論的）

        Args:
            phone: 電話番号

        Returns:
            マスクされた電話番号
        """
        if not self.enabled or not phone:
            return phone

        if phone in self._phone_cache:
            return self._phone_cache[phone]

        if self.mode == "mask":
            result = self._mask_phone_partial(phone)
        elif self.mode == "pseudonym":
            result = self._pseudonym_phone(phone)
        else:
            result = phone

        self._phone_cache[phone] = result
        return result

    def _mask_phone_partial(self, phone: str) -> str:
        """部分マスク: 中間部分を*に"""
        # ハイフンあり: 090-1234-5678
        match = re.match(r'^(\d{2,4})-(\d{3,4})-(\d{4})$', phone)
        if match:
            return f"{match.group(1)}-{'*' * len(match.group(2))}-{match.group(3)}"

        # ハイフンなし: 09012345678
        digits = re.sub(r'\D', '', phone)
        if len(digits) >= 10:
            return digits[:3] + "*" * (len(digits) - 7) + digits[-4:]

        # パターン不明の場合は全マスク
        return "*" * len(phone)

    def _pseudonym_phone(self, phone: str) -> str:
        """仮名置換: 決定論的な架空番号"""
        idx = self._hash_index(phone, 9999)
        # 元の番号形式を保持
        match = re.match(r'^(\d{2,4})-', phone)
        prefix = match.group(1) if match else "090"
        return f"{prefix}-0000-{idx:04d}"

    # =========================================================================
    # 日付のマスク
    # =========================================================================

    def mask_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        日付をマスクする（生年月日などのPII保護）

        mask モード:
            - 「1995-03-15」→「1995-XX-XX」（年のみ残す）

        pseudonym モード:
            - 「1995-03-15」→「1995-07-22」（月日をハッシュで置換）

        Args:
            date_str: YYYY-MM-DD形式の日付文字列

        Returns:
            マスクされた日付
        """
        if not self.enabled or not date_str:
            return date_str

        date_str = str(date_str)

        # YYYY-MM-DD 形式の場合
        match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', date_str)
        if match:
            year = match.group(1)
            if self.mode == "mask":
                return f"{year}-XX-XX"
            elif self.mode == "pseudonym":
                h = self._hash_index(date_str, 365)
                month = (h % 12) + 1
                day = (h % 28) + 1  # 安全な日数範囲
                return f"{year}-{month:02d}-{day:02d}"

        return date_str

    # =========================================================================
    # 住所のマスク
    # =========================================================================

    def mask_address(self, address: Optional[str]) -> Optional[str]:
        """
        住所をマスクする

        mask モード:
            - 「東京都新宿区西新宿1-2-3」→「東京都●●区●●●」

        pseudonym モード:
            - 「東京都新宿区西新宿1-2-3」→「○○県桜ヶ丘1-1-1」

        Args:
            address: 住所文字列

        Returns:
            マスクされた住所
        """
        if not self.enabled or not address:
            return address

        if self.mode == "mask":
            # 都道府県を残し、残りをマスク
            pref_match = re.match(r'^(.{2,4}[都道府県])', address)
            if pref_match:
                return pref_match.group(1) + "●●区●●●"
            return "●●県●●市●●●"

        elif self.mode == "pseudonym":
            place_idx = self._hash_index(address, len(PSEUDO_PLACES))
            return f"○○県{PSEUDO_PLACES[place_idx]}1-1-1"

        return address

    # =========================================================================
    # 医療機関名のマスク
    # =========================================================================

    def mask_hospital(self, hospital_name: Optional[str]) -> Optional[str]:
        """
        医療機関名を仮名化する

        Args:
            hospital_name: 医療機関名

        Returns:
            仮名化された医療機関名
        """
        if not self.enabled or not hospital_name:
            return hospital_name

        if hospital_name in self._hospital_cache:
            return self._hospital_cache[hospital_name]

        if self.mode == "mask":
            result = "●●病院"
        elif self.mode == "pseudonym":
            idx = self._hash_index(hospital_name, len(PSEUDO_HOSPITALS))
            result = PSEUDO_HOSPITALS[idx]
        else:
            result = hospital_name

        self._hospital_cache[hospital_name] = result
        return result

    # =========================================================================
    # 組織名のマスク
    # =========================================================================

    def mask_organization(self, org_name: Optional[str]) -> Optional[str]:
        """
        組織名（福祉事業所等）を仮名化する

        Args:
            org_name: 組織名

        Returns:
            仮名化された組織名
        """
        if not self.enabled or not org_name:
            return org_name

        if org_name in self._org_cache:
            return self._org_cache[org_name]

        if self.mode == "mask":
            result = "●●事業所"
        elif self.mode == "pseudonym":
            idx = self._hash_index(org_name, len(PSEUDO_ORGS))
            result = PSEUDO_ORGS[idx]
        else:
            result = org_name

        self._org_cache[org_name] = result
        return result

    # =========================================================================
    # レコード（辞書）の一括マスク
    # =========================================================================

    def mask_record(self, record: dict, field_rules: Optional[dict] = None) -> dict:
        """
        辞書形式のレコードを一括マスクする

        デフォルトのフィールド推定ルール:
        - name, クライアント, 支援者, 操作者 などのキー → mask_name
        - phone, 電話 などのキー → mask_phone
        - dob, 生年月日 などのキー → mask_date
        - address, 住所 などのキー → mask_address

        Args:
            record: マスク対象の辞書
            field_rules: カスタムフィールドルール {フィールド名: マスク関数名}

        Returns:
            マスクされた辞書（元の辞書は変更しない）
        """
        if not self.enabled:
            return record

        # デフォルトのフィールド推定ルール
        default_rules = {
            # 人名フィールド
            "name": "name",
            "client_name": "name",
            "クライアント": "name",
            "supporter": "name",
            "支援者": "name",
            "操作者": "name",
            "対象名": "name",
            "perpetrator": "name",
            "doctor": "name",
            "contact_person": "name",
            "targetName": "name",
            "clientName": "name",
            "user": "name",

            # 電話番号フィールド
            "phone": "phone",
            "電話": "phone",

            # 日付フィールド（PII）
            "dob": "date",
            "生年月日": "date",

            # 住所フィールド
            "address": "address",
            "住所": "address",

            # 医療機関フィールド
            "hospital": "hospital",
            "病院": "hospital",

            # 組織フィールド
            "organization": "org",
            "org_name": "org",
            "事業所": "org",
        }

        rules = {**default_rules, **(field_rules or {})}

        masked = {}
        for key, value in record.items():
            if key in rules and isinstance(value, str):
                mask_type = rules[key]
                if mask_type == "name":
                    masked[key] = self.mask_name(value)
                elif mask_type == "phone":
                    masked[key] = self.mask_phone(value)
                elif mask_type == "date":
                    masked[key] = self.mask_date(value)
                elif mask_type == "address":
                    masked[key] = self.mask_address(value)
                elif mask_type == "hospital":
                    masked[key] = self.mask_hospital(value)
                elif mask_type == "org":
                    masked[key] = self.mask_organization(value)
                else:
                    masked[key] = value
            else:
                masked[key] = value

        return masked

    def mask_records(self, records: list[dict], field_rules: Optional[dict] = None) -> list[dict]:
        """
        辞書のリストを一括マスクする

        Args:
            records: マスク対象の辞書リスト
            field_rules: カスタムフィールドルール

        Returns:
            マスクされた辞書リスト
        """
        if not self.enabled:
            return records
        return [self.mask_record(r, field_rules) for r in records]

    # =========================================================================
    # テキスト内のPII検出・マスク
    # =========================================================================

    def mask_text(self, text: Optional[str], known_names: Optional[list[str]] = None) -> Optional[str]:
        """
        自由記述テキスト内の既知の個人名をマスクする

        Args:
            text: マスク対象のテキスト
            known_names: 検出対象の名前リスト（データベースから取得）

        Returns:
            マスクされたテキスト
        """
        if not self.enabled or not text:
            return text

        result = text

        # 既知の名前をマスク
        if known_names:
            # 長い名前から優先的にマスク（部分一致の問題を防ぐ）
            sorted_names = sorted(known_names, key=len, reverse=True)
            for name in sorted_names:
                if name and name in result:
                    masked_name = self.mask_name(name)
                    result = result.replace(name, masked_name)

        # 電話番号パターンをマスク
        phone_pattern = r'(\d{2,4}[-ー]\d{3,4}[-ー]\d{4})'
        result = re.sub(phone_pattern, lambda m: self.mask_phone(m.group(1)), result)

        return result

    # =========================================================================
    # ユーティリティ
    # =========================================================================

    def get_status(self) -> dict:
        """
        仮名化の現在の状態を返す

        Returns:
            dict: {"enabled": bool, "mode": str, "cached_names": int}
        """
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "cached_names": len(self._name_cache),
            "cached_phones": len(self._phone_cache),
            "cached_hospitals": len(self._hospital_cache),
            "cached_orgs": len(self._org_cache),
        }

    def clear_cache(self):
        """キャッシュをクリアする（セッション終了時に推奨）"""
        self._name_cache.clear()
        self._phone_cache.clear()
        self._org_cache.clear()
        self._hospital_cache.clear()


# =============================================================================
# グローバルインスタンス（環境変数から自動構成）
# =============================================================================

def get_default_pseudonymizer() -> Pseudonymizer:
    """
    環境変数から設定を読み込み、デフォルトの Pseudonymizer を返す

    環境変数:
        PSEUDONYMIZATION_ENABLED: "true" で有効化
        PSEUDONYMIZATION_MODE: "mask" または "pseudonym"（デフォルト: "mask"）
        PSEUDONYMIZATION_SEED: ハッシュシード値

    Returns:
        Pseudonymizer インスタンス
    """
    enabled = os.getenv("PSEUDONYMIZATION_ENABLED", "false").lower() == "true"
    mode = os.getenv("PSEUDONYMIZATION_MODE", "mask")
    seed = os.getenv("PSEUDONYMIZATION_SEED", "nest-support-demo")

    return Pseudonymizer(enabled=enabled, mode=mode, seed=seed)


# モジュールレベルのデフォルトインスタンス
_default_instance: Optional[Pseudonymizer] = None


def get_pseudonymizer() -> Pseudonymizer:
    """デフォルトの Pseudonymizer シングルトンを取得"""
    global _default_instance
    if _default_instance is None:
        _default_instance = get_default_pseudonymizer()
    return _default_instance


def reset_pseudonymizer():
    """デフォルトインスタンスをリセット（テスト用）"""
    global _default_instance
    _default_instance = None
