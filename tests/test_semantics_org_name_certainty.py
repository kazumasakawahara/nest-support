"""機関の名前（orgName）のある関わりの確度（2026-11-11 河原さんの決めごと。SEMANTICS の変更を承認）。DB を使わない。

- SEM-AREA-04 の「いつも Inference」は、機関の名前が無い言及（住所からの推定）に限る
- SEM-REC-05：名前のある関わりは根拠の記録の確度を写す。強くしない。結んだか機関未確定かで分けない。
  印の無い原文は Unspecified のまま。orgName と推定の候補からの orgId の両方があれば止める
"""
from pathlib import Path

TEXT = (Path(__file__).resolve().parents[1] / "docs" / "SEMANTICS.md").read_text(encoding="utf-8")


def _sec(head):
    i = TEXT.index("### " + head)
    return TEXT[i:TEXT.index("\n#", i + 1)]


def test_area_04_limits_inference_to_mentions_without_a_name():
    s = _sec("SEM-AREA-04")
    assert "\n- 関わりの確度はいつも `Inference`" not in s  # 前の文（範囲を限らない「いつも」）は無い
    assert "機関の名前が無い言及（住所からの推定）の関わりの確度はいつも `Inference`" in s
    assert "SEM-REC-05" in s


def test_rec_05_states_the_three_rules():
    s = _sec("SEM-REC-05")
    for words in ("根拠の記録", "確度を写す", "強くしない", "機関未確定", "分けない", "`Unspecified`", "`Inference` に寄せない",
                  "orgName", "orgId", "止める", "inferenceBasis"):
        assert words in s, words
    assert "情報提供の書面" not in s  # 書面のときの扱いは決めていない（journal の論点。承認の範囲の外）
