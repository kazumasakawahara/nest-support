"""
P0-5: Gemini へ送信する Client 概要テキストから実名・生年月日を除外する回帰テスト。

build_client_summary_text() の出力は embedding 生成のため Gemini API に送られる。
類似度分析に氏名・生年月日は不要なため、これらを含めない。
"""

import lib.embedding as emb


_ROW = {
    "name": "山田健太",
    "dob": "1990-01-15",
    "bloodType": "O",
    "clientId": "c-001",
    "displayCode": "A-001",
    "conditions": ["自閉症スペクトラム障害"],
    "ngActions": ["大きな音"],
    "careInstructions": ["絵カードを使って予定を伝える"],
    "recentLogs": ["食事→見守り"],
}


def test_summary_excludes_name_and_dob(monkeypatch):
    monkeypatch.setattr(emb, "_run_query", lambda q, p=None: [dict(_ROW)])
    text = emb.build_client_summary_text("山田健太")
    assert text is not None
    assert "山田健太" not in text, "実名が概要テキストに含まれてはならない"
    assert "1990-01-15" not in text, "生年月日が概要テキストに含まれてはならない"


def test_summary_keeps_care_characteristics(monkeypatch):
    """ケア特性（類似度分析に必要）は保持される。"""
    monkeypatch.setattr(emb, "_run_query", lambda q, p=None: [dict(_ROW)])
    text = emb.build_client_summary_text("山田健太")
    assert "自閉症スペクトラム障害" in text
    assert "大きな音" in text
    assert "絵カードを使って予定を伝える" in text
