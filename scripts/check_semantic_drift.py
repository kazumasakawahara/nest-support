"""
四者一致チェッカー（意味・ルール層のドリフト検知）

SEMANTIC_MODEL.md §6 の機械検証ブロック（あるべき仕様）を基準に、
  ① 正本ドキュメント（docs/SEMANTIC_MODEL.md、無ければ shared-schema のマスター）
  ② lib/schema_validator.py（Guardian の実装）
  ③ GET /api/narrative/schema（agno 実行時 allowlist。停止時はソース AST 解析）
  ④ lib/db_operations.py（nest Python 登録経路の MERGE_KEYS / CLIENT_SCOPED_LABELS。
    AST 解析。2026-07-13 追加——DRIFT-12 が機械検出されなかった死角の解消）
を突合する。

既知の不一致は正本の acceptedDrifts に登録されており KNOWN として報告する。
未登録の不一致のみ FAIL（終了コード 1）。--strict で KNOWN も FAIL 扱い。

使い方:
  uv run python scripts/check_semantic_drift.py
  uv run python scripts/check_semantic_drift.py --strict

出力はラベル名・件数のみ（スキーマレベル）。実データは扱わない。
"""

import argparse
import ast
import inspect
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DOC_CANDIDATES = [
    REPO_ROOT / "docs" / "SEMANTIC_MODEL.md",
    Path.home() / "Dev-Work" / "shared-schema" / "SEMANTIC_MODEL.md",
]
AGNO_SCHEMA_URL = os.environ.get(
    "AGNO_SCHEMA_URL", "http://localhost:8000/api/narrative/schema"
)
AGNO_SOURCE = Path(
    os.environ.get(
        "AGNO_DB_OPERATIONS",
        Path.home() / "Dev-Work" / "neo4j-agno-agent" / "lib" / "db_new_operations.py",
    )
)

_FENCE_RE = re.compile(r"```json machine-check\n(.*?)```", re.DOTALL)

results = {"OK": 0, "KNOWN": 0, "FAIL": 0, "WARN": 0}


def report(level: str, message: str):
    results[level] = results.get(level, 0) + 1
    print(f"[{level}] {message}")


# ---------------------------------------------------------------------------
# ① 正本ドキュメントの機械検証ブロック
# ---------------------------------------------------------------------------

def load_doc_spec() -> dict:
    for path in DOC_CANDIDATES:
        if path.is_file():
            m = _FENCE_RE.search(path.read_text(encoding="utf-8"))
            if not m:
                print(f"ERROR: {path} に ```json machine-check ブロックがありません")
                sys.exit(2)
            print(f"正本: {path}")
            return json.loads(m.group(1))
    print("ERROR: SEMANTIC_MODEL.md が見つかりません")
    sys.exit(2)


# ---------------------------------------------------------------------------
# ③ agno 実行時 allowlist（API → ソース AST の順で取得）
# ---------------------------------------------------------------------------

def fetch_agno_allowlist() -> tuple[set, set, str] | None:
    try:
        with urllib.request.urlopen(AGNO_SCHEMA_URL, timeout=3) as resp:
            data = json.loads(resp.read())
            return (
                set(data["allowed_labels"]),
                set(data["allowed_rels"]),
                f"API {AGNO_SCHEMA_URL}",
            )
    except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError):
        pass

    if not AGNO_SOURCE.is_file():
        return None
    tree = ast.parse(AGNO_SOURCE.read_text(encoding="utf-8"))
    consts: dict[str, object] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in (
                "MERGE_KEYS", "ALLOWED_CREATE_LABELS", "ALLOWED_REL_TYPES",
            ):
                try:
                    consts[target.id] = ast.literal_eval(node.value)
                except ValueError:
                    pass
    if "MERGE_KEYS" not in consts or "ALLOWED_REL_TYPES" not in consts:
        return None
    labels = set(consts["MERGE_KEYS"].keys()) | set(
        consts.get("ALLOWED_CREATE_LABELS", set())
    )
    return labels, set(consts["ALLOWED_REL_TYPES"]), f"AST {AGNO_SOURCE}"


# ---------------------------------------------------------------------------
# 突合ロジック
# ---------------------------------------------------------------------------

def accepted(spec: dict, target: str, kind: str) -> dict | None:
    for d in spec.get("acceptedDrifts", []):
        if d["target"] == target and d["kind"] == kind:
            return d
    return None


def diff_sets(spec: dict, name: str, canonical: set, actual: set, target: str):
    """canonical（あるべき仕様）と actual（実装）を突合し、差分を報告する。"""
    missing = canonical - actual
    extra = actual - canonical

    for kind, values in (("missing-values", missing), ("extra-values", extra)):
        if not values:
            continue
        drift = accepted(spec, target, kind)
        word = "不足" if kind == "missing-values" else "過剰"
        if drift and values == set(drift["values"]):
            report("KNOWN", f"{name}: {word} {sorted(values)} （{drift['id']}: {drift['reason']}）")
        elif drift:
            known = values & set(drift["values"])
            unknown = values - set(drift["values"])
            if known:
                report("KNOWN", f"{name}: {word} {sorted(known)} （{drift['id']}）")
            if unknown:
                report("FAIL", f"{name}: 未登録の{word} {sorted(unknown)}")
        else:
            report("FAIL", f"{name}: 未登録の{word} {sorted(values)}")
    if not missing and not extra:
        report("OK", f"{name}: 一致（{len(canonical)}件）")


def check_validator(spec: dict):
    import lib.schema_validator as sv

    canon = spec["canonical"]
    diff_sets(spec, "Guardian ノードラベル", set(canon["nodeLabels"]),
              set(sv.VALID_NODE_LABELS), "validator.nodeLabels")
    diff_sets(spec, "Guardian リレーション", set(canon["relationshipTypes"]),
              set(sv.VALID_RELATIONSHIP_TYPES), "validator.relationshipTypes")
    for key, values in canon["enums"].items():
        if key not in sv.ENUM_VALUES:
            report("WARN", f"Guardian 列挙 {key}: validator に検証定義なし（検証対象外）")
            continue
        diff_sets(spec, f"Guardian 列挙 {key}", set(values),
                  set(sv.ENUM_VALUES[key]), f"validator.enums.{key}")


def check_insight_engine(spec: dict):
    import lib.insight_engine as ie

    if set(spec["canonical"]["negativeEmotions"]) == ie.NEGATIVE_EMOTIONS:
        report("OK", "負の感情の集合: 一致（5件）")
    else:
        report("FAIL", f"負の感情の集合: 正本={sorted(spec['canonical']['negativeEmotions'])} "
                       f"実装={sorted(ie.NEGATIVE_EMOTIONS)}")

    m = spec["metrics"]
    expected_defaults = [
        (ie.detect_emotion_drift, {"baseline_days": m["emotionDrift"]["baselineDays"],
                                   "recent_days": m["emotionDrift"]["recentDays"],
                                   "threshold": m["emotionDrift"]["warnThreshold"]}),
        (ie.detect_cascading_risk, {"days": m["cascadingRisk"]["days"],
                                    "min_cascade": m["cascadingRisk"]["minCascade"]}),
        (ie.detect_staff_overload, {"days": m["staffOverload"]["days"],
                                    "negative_ratio_threshold": m["staffOverload"]["negativeRatioThreshold"]}),
        (ie.discover_care_patterns, {"min_frequency": m["carePattern"]["discoverMinFrequency"]}),
        (ie.propose_care_promotions, {"min_frequency": m["carePattern"]["promoteMinFrequency"]}),
    ]
    for func, params in expected_defaults:
        sig = inspect.signature(func)
        for pname, expected in params.items():
            actual = sig.parameters[pname].default
            if actual == expected:
                report("OK", f"閾値 {func.__name__}.{pname} = {expected}")
            else:
                report("FAIL", f"閾値 {func.__name__}.{pname}: 正本={expected} 実装={actual}")

    # シグネチャに現れないハードコード値はソーステキストの簡易照合
    source = inspect.getsource(ie)
    for label, needle in [
        (f"重大判定 severeThreshold = {m['emotionDrift']['severeThreshold']}",
         f">= {m['emotionDrift']['severeThreshold']}"),
        (f"スタッフ負荷 minLogs = {m['staffOverload']['minLogs']}",
         f">= {m['staffOverload']['minLogs']}"),
    ]:
        if needle in source:
            report("OK", f"閾値 {label}（ソース照合）")
        else:
            report("WARN", f"閾値 {label}: ソース内に見つからず（手動確認要）")


def check_nest_lib(spec: dict):
    """④ nest lib/db_operations.py の MERGE_KEYS / CLIENT_SCOPED_LABELS を AST 照合。

    実行時 import は Neo4j ドライバ等を巻き込むため、agno フォールバックと同じく
    AST（literal_eval）で読む。CLIENT_SCOPED_LABELS は frozenset({...}) の Call
    形式なので引数の集合リテラルを取り出す。
    """
    src = REPO_ROOT / "lib" / "db_operations.py"
    if not src.is_file():
        report("WARN", "nest lib: lib/db_operations.py が見つかりません（未検証）")
        return
    tree = ast.parse(src.read_text(encoding="utf-8"))
    consts: dict[str, object] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in (
                "MERGE_KEYS", "CLIENT_SCOPED_LABELS",
            ):
                value = node.value
                if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                        and value.func.id == "frozenset" and value.args):
                    value = value.args[0]
                try:
                    consts[target.id] = ast.literal_eval(value)
                except ValueError:
                    pass
    if "MERGE_KEYS" not in consts:
        report("WARN", "nest lib: MERGE_KEYS を AST で取得できません（手動確認要）")
        return
    merge_keys: dict = consts["MERGE_KEYS"]
    scoped = set(consts.get("CLIENT_SCOPED_LABELS", set()))

    # ラベル整合: lib が扱うラベルはすべて正典の nodeLabels に存在すること
    lib_labels = set(merge_keys) | scoped
    unknown = lib_labels - set(spec["canonical"]["nodeLabels"])
    if unknown:
        report("FAIL", f"nest lib ラベル: 正典に無いラベル {sorted(unknown)}")
    else:
        report("OK", f"nest lib ラベル: すべて正典内（{len(lib_labels)}件）")

    nest_spec = spec.get("nestLib")
    if not nest_spec:
        report("WARN", "nest lib: 正本に nestLib ブロックが無く MERGE キーは未検証")
        return
    for label, expected in nest_spec.get("mergeKeys", {}).items():
        actual = merge_keys.get(label)
        if actual == expected:
            report("OK", f"nest lib MERGE キー {label} = {expected}")
        else:
            report("FAIL", f"nest lib MERGE キー {label}: 正本={expected} 実装={actual}")
    for label in nest_spec.get("neverMergeLabels", []):
        if label in merge_keys:
            report("FAIL", f"nest lib: {label} が MERGE_KEYS に存在"
                           "（常時 CREATE が正。ENT-16 / ENT-24 参照）")
        else:
            report("OK", f"nest lib: {label} は MERGE_KEYS に無い（常時 CREATE・正）")


def check_agno(spec: dict):
    fetched = fetch_agno_allowlist()
    if fetched is None:
        report("WARN", "agno allowlist を取得できません（API 停止かつソース不在）。三者目は未検証")
        return
    labels, rels, origin = fetched
    print(f"agno allowlist: {origin}")
    canon = spec["canonical"]
    diff_sets(spec, "agno ノードラベル", set(canon["nodeLabels"]), labels,
              "agno.nodeLabels")
    diff_sets(spec, "agno リレーション", set(canon["relationshipTypes"]), rels,
              "agno.relationshipTypes")


def main():
    parser = argparse.ArgumentParser(description="意味・ルール層の三者一致チェック")
    parser.add_argument("--strict", action="store_true",
                        help="既知ドリフト（KNOWN）も失敗として扱う")
    args = parser.parse_args()

    spec = load_doc_spec()
    print("--- ② Guardian (lib/schema_validator.py) ---")
    check_validator(spec)
    print("--- ② Oracle (lib/insight_engine.py) ---")
    check_insight_engine(spec)
    print("--- ③ agno 実行時 allowlist ---")
    check_agno(spec)
    print("--- ④ nest lib (lib/db_operations.py) ---")
    check_nest_lib(spec)

    print(f"\n結果: OK={results['OK']} KNOWN={results['KNOWN']} "
          f"FAIL={results['FAIL']} WARN={results['WARN']}")
    if results["FAIL"] or (args.strict and results["KNOWN"]):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
