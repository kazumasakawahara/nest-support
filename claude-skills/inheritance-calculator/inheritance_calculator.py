#!/usr/bin/env python3
"""
相続カルキュレーター (Inheritance Calculator)

日本の民法に基づいて法定相続人と相続分を計算するスクリプト。

使用方法:
    python inheritance_calculator.py <input.json>
    python inheritance_calculator.py --stdin  # 標準入力からJSON読み込み
    python inheritance_calculator.py --help   # ヘルプ表示

入力:
    JSON形式の相続情報（詳細はforms.mdを参照）

出力:
    計算結果をJSON形式で標準出力に出力
"""

import json
import sys
import argparse
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
        
        # ステップ3: 血族相続人の確定
        blood_heirs_determined = self._determine_blood_heirs()
        
        # ステップ4: 法定相続分の計算
        if blood_heirs_determined:
            self._calculate_inheritance_shares()
        
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
    
    def _determine_blood_heirs(self) -> bool:
        """血族相続人を確定"""
        # 第1順位: 子
        if self._process_first_rank():
            return True
        
        # 第2順位: 直系尊属
        if self._process_second_rank():
            return True
        
        # 第3順位: 兄弟姉妹
        if self._process_third_rank():
            return True
        
        return False
    
    def _process_first_rank(self) -> bool:
        """第1順位（子）の処理"""
        children = self.input.get("children", [])
        if not children:
            return False
        
        first_rank_heirs = []
        
        for child in children:
            status = child.get("status", "unknown")
            renounced = child.get("renounced", False)
            
            if status == PersonStatus.ALIVE and not renounced:
                first_rank_heirs.append(Heir(
                    name=child["name"],
                    rank=InheritanceRank.FIRST
                ))
            elif status in [PersonStatus.DECEASED, PersonStatus.SIMULTANEOUS_DEATH]:
                if not renounced:
                    substitutes = self._process_substitution(child, InheritanceRank.FIRST)
                    first_rank_heirs.extend(substitutes)
        
        if first_rank_heirs:
            self.heirs.extend(first_rank_heirs)
            return True
        
        return False
    
    def _process_second_rank(self) -> bool:
        """第2順位（直系尊属）の処理"""
        parents = self.input.get("parents", [])
        if not parents:
            return False
        
        second_rank_heirs = []
        
        for parent in parents:
            status = parent.get("status", "unknown")
            renounced = parent.get("renounced", False)
            
            if status == PersonStatus.ALIVE and not renounced:
                second_rank_heirs.append(Heir(
                    name=parent["name"],
                    rank=InheritanceRank.SECOND
                ))
        
        if second_rank_heirs:
            self.heirs.extend(second_rank_heirs)
            return True
        
        return False
    
    def _process_third_rank(self) -> bool:
        """第3順位（兄弟姉妹）の処理"""
        siblings = self.input.get("siblings", [])
        if not siblings:
            return False
        
        third_rank_heirs = []
        
        for sibling in siblings:
            status = sibling.get("status", "unknown")
            renounced = sibling.get("renounced", False)
            blood_relation = sibling.get("blood_relation", "full")
            
            if status == PersonStatus.ALIVE and not renounced:
                third_rank_heirs.append(Heir(
                    name=sibling["name"],
                    rank=InheritanceRank.THIRD,
                    blood_relation=BloodRelationType(blood_relation)
                ))
            elif status in [PersonStatus.DECEASED, PersonStatus.SIMULTANEOUS_DEATH]:
                if not renounced:
                    children = sibling.get("children", [])
                    for nephew_niece in children:
                        nn_status = nephew_niece.get("status", "unknown")
                        nn_renounced = nephew_niece.get("renounced", False)
                        
                        if nn_status == PersonStatus.ALIVE and not nn_renounced:
                            third_rank_heirs.append(Heir(
                                name=nephew_niece["name"],
                                rank=InheritanceRank.THIRD,
                                is_substitute=True,
                                original_heir_name=sibling["name"],
                                blood_relation=BloodRelationType(blood_relation)
                            ))
        
        if third_rank_heirs:
            self.heirs.extend(third_rank_heirs)
            return True
        
        return False
    
    def _process_substitution(self, deceased_person: Dict, rank: InheritanceRank) -> List[Heir]:
        """代襲相続の処理（再帰的）"""
        substitutes = []
        children = deceased_person.get("children", [])
        
        for child in children:
            status = child.get("status", "unknown")
            renounced = child.get("renounced", False)
            
            if status == PersonStatus.ALIVE and not renounced:
                substitutes.append(Heir(
                    name=child["name"],
                    rank=rank,
                    is_substitute=True,
                    original_heir_name=deceased_person["name"]
                ))
            elif status in [PersonStatus.DECEASED, PersonStatus.SIMULTANEOUS_DEATH]:
                if not renounced:
                    further_substitutes = self._process_substitution(child, rank)
                    substitutes.extend(further_substitutes)
        
        return substitutes
    
    def _calculate_inheritance_shares(self):
        """法定相続分を計算"""
        if not self.heirs:
            return
        
        spouse_heirs = [h for h in self.heirs if h.rank == InheritanceRank.SPOUSE]
        blood_heirs = [h for h in self.heirs if h.rank != InheritanceRank.SPOUSE]
        
        if not blood_heirs:
            for heir in spouse_heirs:
                heir.share_numerator = 1
                heir.share_denominator = 1
            return
        
        blood_rank = blood_heirs[0].rank
        
        if spouse_heirs:
            if blood_rank == InheritanceRank.FIRST:
                spouse_share = (1, 2)
                blood_share = (1, 2)
            elif blood_rank == InheritanceRank.SECOND:
                spouse_share = (2, 3)
                blood_share = (1, 3)
            else:
                spouse_share = (3, 4)
                blood_share = (1, 4)
            
            for heir in spouse_heirs:
                heir.share_numerator = spouse_share[0]
                heir.share_denominator = spouse_share[1]
        else:
            blood_share = (1, 1)
        
        self._distribute_blood_shares(blood_heirs, blood_share)
    
    def _distribute_blood_shares(self, blood_heirs: List[Heir], total_share: tuple):
        """血族相続人間で相続分を按分"""
        groups = {}
        direct_heirs = []
        
        for heir in blood_heirs:
            if heir.is_substitute:
                key = heir.original_heir_name or heir.name
                if key not in groups:
                    groups[key] = []
                groups[key].append(heir)
            else:
                direct_heirs.append(heir)
        
        num_divisions = len(direct_heirs) + len(groups)
        
        if num_divisions == 0:
            return
        
        base_numerator = total_share[0]
        base_denominator = total_share[1] * num_divisions
        
        for heir in direct_heirs:
            if heir.rank == InheritanceRank.THIRD and heir.blood_relation == BloodRelationType.HALF:
                heir.share_numerator = base_numerator
                heir.share_denominator = base_denominator * 2
            else:
                heir.share_numerator = base_numerator
                heir.share_denominator = base_denominator
        
        for group_heirs in groups.values():
            num_in_group = len(group_heirs)
            for heir in group_heirs:
                if heir.rank == InheritanceRank.THIRD and heir.blood_relation == BloodRelationType.HALF:
                    heir.share_numerator = base_numerator
                    heir.share_denominator = base_denominator * 2 * num_in_group
                else:
                    heir.share_numerator = base_numerator
                    heir.share_denominator = base_denominator * num_in_group
    
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
