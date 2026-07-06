#!/usr/bin/env python3
"""
相続カルキュレーター (Inheritance Calculator)

日本の民法に基づいて法定相続人と相続分を計算するスクリプト。

使用方法:
    python inheritance_calculator.py <input.json>
    python inheritance_calculator.py --stdin  # 標準入力からJSON読み込み
    python inheritance_calculator.py --help   # ヘルプ表示

入力:
    JSON形式の相続情報（スキーマの詳細は SKILL.md「入力JSONスキーマ」を参照）

出力:
    計算結果をJSON形式で標準出力に出力
"""

import json
import sys
import argparse
from fractions import Fraction
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass

# ===================================================================
# 定数定義
# ===================================================================

VERSION = "1.0.0"

# ===================================================================
# データモデル
# ===================================================================

class PersonStatus(str, Enum):
    """人物の生存状態"""
    ALIVE = "alive"
    DECEASED = "deceased"
    SIMULTANEOUS_DEATH = "simultaneous_death"
    UNKNOWN = "unknown"

class InheritanceRank(str, Enum):
    """相続順位"""
    SPOUSE = "spouse"
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"

class BloodRelationType(str, Enum):
    """血縁関係の種類"""
    FULL = "full"
    HALF = "half"

# ===================================================================
# 相続人クラス
# ===================================================================

@dataclass
class Heir:
    """相続人の情報"""
    name: str
    rank: InheritanceRank
    is_substitute: bool = False
    original_heir_name: Optional[str] = None
    blood_relation: Optional[BloodRelationType] = None
    share_numerator: int = 0
    share_denominator: int = 1
    
    def share_as_fraction(self) -> str:
        """相続分を分数形式で返す"""
        if self.share_denominator == 1:
            return "1"
        return f"{self.share_numerator}/{self.share_denominator}"
    
    def share_as_percentage(self) -> str:
        """相続分をパーセント形式で返す"""
        percentage = (self.share_numerator / self.share_denominator) * 100
        return f"{percentage:.2f}%"

# ===================================================================
# 相続計算エンジン
# ===================================================================

class InheritanceCalculator:
    """相続計算を行うメインクラス"""
    
    def __init__(self, input_data: Dict[str, Any]):
        self.input = input_data
        self.heirs: List[Heir] = []
        self._validate_input()
    
    def _validate_input(self):
        """入力データの基本的な検証"""
        required_fields = ["deceased_name", "has_simultaneous_death"]
        for field in required_fields:
            if field not in self.input:
                raise ValueError(f"必須フィールド '{field}' が見つかりません")
        
        # オプションフィールドのデフォルト値
        if "spouse" not in self.input:
            self.input["spouse"] = None
        if "children" not in self.input:
            self.input["children"] = []
        if "parents" not in self.input:
            self.input["parents"] = []
        if "siblings" not in self.input:
            self.input["siblings"] = []
    
    def calculate(self) -> Dict[str, Any]:
        """相続計算の全体フローを実行"""
        # ステップ1: 同時死亡の確認
        simultaneous_death_note = ""
        if self.input["has_simultaneous_death"]:
            simultaneous_death_note = (
                "【注意】同時死亡の推定が適用されています（民法32条の2）。\n"
                "同時死亡者間では互いに相続は発生しません。\n"
                "ただし、同時死亡した相続人に子がいれば、代襲相続は発生します。\n\n"
            )
        
        # ステップ2: 配偶者の確認
        self._process_spouse()

        # ステップ3-4: 血族相続人の確定と法定相続分の按分（fractions.Fraction）
        self._determine_and_distribute()

        # 結果の整形
        result = self._format_result(simultaneous_death_note)

        return result
    
    def _process_spouse(self):
        """配偶者を相続人リストに追加"""
        spouse = self.input.get("spouse")
        if spouse:
            status = spouse.get("status", "unknown")
            renounced = spouse.get("renounced", False)
            
            if status == PersonStatus.ALIVE and not renounced:
                self.heirs.append(Heir(
                    name=spouse["name"],
                    rank=InheritanceRank.SPOUSE
                ))
    
    # -----------------------------------------------------------------
    # 生存・死亡判定ヘルパー
    # -----------------------------------------------------------------

    @staticmethod
    def _is_alive(person: Dict) -> bool:
        return (
            person.get("status", "unknown") == PersonStatus.ALIVE
            and not person.get("renounced", False)
        )

    @staticmethod
    def _is_deceased(person: Dict) -> bool:
        return person.get("status", "unknown") in (
            PersonStatus.DECEASED,
            PersonStatus.SIMULTANEOUS_DEATH,
        )

    @classmethod
    def _line_has_living(cls, person: Dict) -> bool:
        """その人物の系統（本人＋代襲卑属）に相続可能な生存者がいるか。

        放棄した者は代襲を生じさせない（民法887条2項但書の趣旨）ため、
        放棄者は系統ごと除外する。
        """
        if person.get("renounced", False):
            return False
        if cls._is_alive(person):
            return True
        if cls._is_deceased(person):
            return any(cls._line_has_living(ch) for ch in person.get("children", []))
        return False

    @staticmethod
    def _set_share(heir: Heir, frac: Fraction):
        heir.share_numerator = frac.numerator
        heir.share_denominator = frac.denominator

    def _make_heir(self, name, rank, share: Fraction, *, is_substitute=False,
                   original=None, blood_relation=None) -> Heir:
        heir = Heir(
            name=name,
            rank=rank,
            is_substitute=is_substitute,
            original_heir_name=original,
            blood_relation=blood_relation,
        )
        self._set_share(heir, share)
        return heir

    @staticmethod
    def _spouse_share(blood_rank: InheritanceRank) -> Fraction:
        """血族の順位に応じた配偶者の法定相続分（民法900条）。"""
        if blood_rank == InheritanceRank.FIRST:
            return Fraction(1, 2)
        if blood_rank == InheritanceRank.SECOND:
            return Fraction(2, 3)
        return Fraction(3, 4)  # 第3順位（兄弟姉妹）

    # -----------------------------------------------------------------
    # 血族相続人の確定と按分
    # -----------------------------------------------------------------

    def _determine_and_distribute(self):
        """血族の順位を順に試し、確定した順位に blood_share を株分けする。"""
        spouse_heirs = [h for h in self.heirs if h.rank == InheritanceRank.SPOUSE]
        spouse_present = bool(spouse_heirs)

        for rank, distributor in (
            (InheritanceRank.FIRST, self._distribute_first_rank),
            (InheritanceRank.SECOND, self._distribute_second_rank),
            (InheritanceRank.THIRD, self._distribute_third_rank),
        ):
            blood_share = (
                Fraction(1) - self._spouse_share(rank) if spouse_present else Fraction(1)
            )
            blood_heirs = distributor(blood_share)
            if blood_heirs:
                if spouse_present:
                    sp = self._spouse_share(rank)
                    for h in spouse_heirs:
                        self._set_share(h, sp)
                self.heirs.extend(blood_heirs)
                self._assert_total()
                return

        # 血族相続人なし → 配偶者が全部相続
        if spouse_present:
            for h in spouse_heirs:
                self._set_share(h, Fraction(1))
            self._assert_total()

    def _resolve_descendant_line(self, person: Dict, share: Fraction,
                                 original: Optional[str]) -> List[Heir]:
        """直系卑属（子）の系統に share を株分けする（再代襲は無制限）。

        original は代襲元（被代襲者名）。None なら本人が生存本人。
        """
        if person.get("renounced", False):
            return []
        if self._is_alive(person):
            return [self._make_heir(
                person["name"], InheritanceRank.FIRST, share,
                is_substitute=original is not None, original=original,
            )]
        if self._is_deceased(person):
            living = [ch for ch in person.get("children", []) if self._line_has_living(ch)]
            if not living:
                return []
            each = share / len(living)
            next_original = original if original is not None else person["name"]
            out: List[Heir] = []
            for ch in living:
                out += self._resolve_descendant_line(ch, each, next_original)
            return out
        return []

    def _distribute_first_rank(self, blood_share: Fraction) -> Optional[List[Heir]]:
        """第1順位（子）— 生存する子の系統を株（stirpes）として均等分割。"""
        children = self.input.get("children", [])
        stems = [c for c in children if self._line_has_living(c)]
        if not stems:
            return None
        per_stem = blood_share / len(stems)
        heirs: List[Heir] = []
        for c in stems:
            heirs += self._resolve_descendant_line(c, per_stem, original=None)
        return heirs

    def _distribute_second_rank(self, blood_share: Fraction) -> Optional[List[Heir]]:
        """第2順位（直系尊属）— 代襲なし。生存する尊属で均等分割。

        （親等の遠近による優先は本修正の範囲外。生存する尊属を均等分割する。）
        """
        parents = self.input.get("parents", [])
        living = [p for p in parents if self._is_alive(p)]
        if not living:
            return None
        per = blood_share / len(living)
        return [self._make_heir(p["name"], InheritanceRank.SECOND, per) for p in living]

    def _distribute_third_rank(self, blood_share: Fraction) -> Optional[List[Heir]]:
        """第3順位（兄弟姉妹）— 全血=2・半血=1 の重み付け。代襲は一代限り（甥姪）。"""
        siblings = self.input.get("siblings", [])
        stems = []  # (sibling_dict, "alive" | [nephew_dict, ...])
        for s in siblings:
            if s.get("renounced", False):
                continue
            if self._is_alive(s):
                stems.append((s, "alive"))
            elif self._is_deceased(s):
                nephews = [n for n in s.get("children", []) if self._is_alive(n)]
                if nephews:
                    stems.append((s, nephews))
        if not stems:
            return None

        def weight(sib: Dict) -> int:
            return 1 if sib.get("blood_relation", "full") == BloodRelationType.HALF else 2

        total_weight = sum(weight(s) for s, _ in stems)
        heirs: List[Heir] = []
        for sib, kind in stems:
            stem_share = blood_share * Fraction(weight(sib), total_weight)
            br = BloodRelationType(sib.get("blood_relation", "full"))
            if kind == "alive":
                heirs.append(self._make_heir(
                    sib["name"], InheritanceRank.THIRD, stem_share, blood_relation=br,
                ))
            else:
                nephews = kind
                each = stem_share / len(nephews)
                for n in nephews:
                    heirs.append(self._make_heir(
                        n["name"], InheritanceRank.THIRD, each,
                        is_substitute=True, original=sib["name"], blood_relation=br,
                    ))
        return heirs

    def _assert_total(self):
        """相続分の合計が 1 であることを保証する（内部整合性チェック）。"""
        total = sum(
            (Fraction(h.share_numerator, h.share_denominator) for h in self.heirs),
            Fraction(0),
        )
        assert total == Fraction(1), f"相続分の合計が1になりません: {total}"
    
    def _format_result(self, note: str) -> Dict[str, Any]:
        """計算結果を整形"""
        if not self.heirs:
            return {
                "deceased_name": self.input["deceased_name"],
                "has_legal_heirs": False,
                "note": note + "法定相続人はいません。",
                "heirs": [],
                "summary": "法定相続人が存在しないため、相続財産は最終的に国庫に帰属します。"
            }
        
        heirs_info = []
        for heir in self.heirs:
            heir_dict = {
                "name": heir.name,
                "rank": self._rank_to_japanese(heir.rank),
                "is_substitute": heir.is_substitute,
                "inheritance_share_fraction": heir.share_as_fraction(),
                "inheritance_share_percentage": heir.share_as_percentage()
            }
            
            if heir.is_substitute:
                heir_dict["original_heir"] = heir.original_heir_name
            
            if heir.blood_relation:
                heir_dict["blood_relation"] = "全血" if heir.blood_relation == BloodRelationType.FULL else "半血"
            
            heirs_info.append(heir_dict)
        
        return {
            "deceased_name": self.input["deceased_name"],
            "has_legal_heirs": True,
            "note": note,
            "heirs": heirs_info,
            "important_notes": [
                "相続放棄の熟慮期間は、相続の開始を知った時から3ヶ月です。",
                "ただし、多額の債務など自身の利害に重大な影響を及ぼす事実を後から知った場合、その時から3ヶ月となる場合もあります。",
                "再転相続の場合、熟慮期間の起算点は再転相続人が自身のために相続が開始した事実を知った時です。",
                "このツールは参考情報を提供するものであり、法的助言ではありません。実際の相続では専門家にご相談ください。"
            ]
        }
    
    def _rank_to_japanese(self, rank: InheritanceRank) -> str:
        """相続順位を日本語に変換"""
        rank_map = {
            InheritanceRank.SPOUSE: "配偶者",
            InheritanceRank.FIRST: "第1順位（子）",
            InheritanceRank.SECOND: "第2順位（直系尊属）",
            InheritanceRank.THIRD: "第3順位（兄弟姉妹）"
        }
        return rank_map.get(rank, "不明")

# ===================================================================
# CLIインターフェース
# ===================================================================

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="相続カルキュレーター - 法定相続人と相続分を計算",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # JSONファイルから読み込み
  python inheritance_calculator.py input.json

  # 標準入力から読み込み
  echo '{"deceased_name":"山田太郎",...}' | python inheritance_calculator.py --stdin

  # ヘルプ表示
  python inheritance_calculator.py --help
        """
    )
    
    parser.add_argument(
        "input_file",
        nargs="?",
        help="入力JSONファイルのパス"
    )
    
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="標準入力からJSON読み込み"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"相続カルキュレーター v{VERSION}"
    )
    
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="整形されたJSON出力"
    )
    
    args = parser.parse_args()
    
    # 入力の読み込み
    try:
        if args.stdin:
            input_data = json.load(sys.stdin)
        elif args.input_file:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                input_data = json.load(f)
        else:
            parser.print_help()
            sys.exit(1)
    except FileNotFoundError:
        print(f"エラー: ファイル '{args.input_file}' が見つかりません", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"エラー: JSON解析に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"エラー: 入力の読み込みに失敗しました: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 計算の実行
    try:
        calculator = InheritanceCalculator(input_data)
        result = calculator.calculate()
        
        # 結果の出力
        if args.pretty:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False))
        
        sys.exit(0)
    
    except ValueError as e:
        error_result = {
            "error": "入力データエラー",
            "message": str(e),
            "suggestion": "入力データの形式を確認してください。詳細はforms.mdを参照してください。"
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        error_result = {
            "error": "計算エラー",
            "message": str(e),
            "suggestion": "予期しないエラーが発生しました。入力データを確認してください。"
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
