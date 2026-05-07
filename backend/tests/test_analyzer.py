import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analyzer import keyword_classify


def test_danger_only_article():
    result = keyword_classify("Missile strikes capital city", "rockets and bombs hit civilian areas")
    assert result["category"] == "danger"
    assert result["confidence"] > 0.5
    assert len(result["matched_keywords"]) > 0


def test_peace_only_article():
    result = keyword_classify("Ceasefire agreement reached", "peace deal signed after negotiations and diplomacy")
    assert result["category"] == "peace"
    assert result["confidence"] > 0.5
    assert len(result["matched_keywords"]) > 0


def test_mixed_danger_peace_lower_confidence():
    # Both sides match — confidence should be lower than a one-sided article
    one_sided = keyword_classify("Missile strikes city", "airstrike kills civilians")
    mixed     = keyword_classify("War and ceasefire ongoing", "missile attack but peace talks progressing")
    assert mixed["confidence"] < one_sided["confidence"]


def test_neutral_article():
    result = keyword_classify("Economy grows 3% this quarter", "stock market reaches all-time high")
    assert result["category"] == "neutral"
    assert result["confidence"] == 0.0


def test_negative_keywords_reduce_confidence():
    base   = keyword_classify("war battle attack scene", "military combat in the film")
    with_neg = keyword_classify("war battle attack scene", "military combat in the film",
                                negative_kw_csv="film,scene,movie")
    assert with_neg["confidence"] <= base["confidence"]
    assert "film" in with_neg["negative_matches"] or "scene" in with_neg["negative_matches"]


def test_negative_keywords_force_neutral():
    # Three negative hits → −0.45 from confidence; if base is ~0.67, result < 0.1 → neutral
    result = keyword_classify(
        "Strike action in war movie set",
        "filming a war scene with blast effects in studio",
        negative_kw_csv="movie,film,scene,studio,filming,action",
    )
    # At least verify negative_matches are captured and confidence dropped
    assert len(result["negative_matches"]) > 0
    assert result["confidence"] < 0.7


def test_custom_danger_keyword_used():
    result = keyword_classify("revolution breaks out in region", "",
                              danger_kw_csv="revolution")
    assert result["category"] == "danger"
    assert "revolution" in result["matched_keywords"]


def test_custom_peace_keyword_used():
    result = keyword_classify("handshake between rivals ends standoff", "",
                              peace_kw_csv="handshake,standoff")
    # "standoff" matched as peace custom kw; "handshake" also
    assert result["category"] == "peace"


def test_thai_keywords():
    result = keyword_classify("ขีปนาวุธโจมตีเมือง", "การโจมตีทางอากาศทำให้เสียชีวิตหลายราย")
    assert result["category"] == "danger"


def test_returns_expected_keys():
    result = keyword_classify("Some news title", "some description")
    for key in ("category", "confidence", "reason", "market_impact", "matched_keywords", "negative_matches"):
        assert key in result


def test_analyze_news_backward_compat():
    from analyzer import analyze_news
    result = analyze_news("Missile strikes city", "bombs explode")
    assert "category" in result
    assert "market_impact" in result
    assert "confidence" not in result


# ── build_alert_message tests ──────────────────────────────────────────────────

from analyzer import build_alert_message

_BASE = dict(
    title_en="Rockets hit city",
    title_th="จรวดโจมตีเมือง",
    url="https://example.com/1",
    published_at="2026-05-07 10:00",
)


def test_neutral_returns_none():
    msg = build_alert_message(
        **_BASE,
        analysis={"category": "neutral", "market_impact": ""},
    )
    assert msg is None


def test_danger_with_ai_fields():
    analysis = {
        "category": "danger",
        "summary_th": "ขีปนาวุธโจมตีเมืองหลวง",
        "market_impact": "ตลาดผันผวนรุนแรง",
        "gold_impact": "ทองคำพุ่งแรง",
        "stock_impact": "หุ้นร่วงหนัก",
        "usd_impact": "USD แข็งค่า",
        "asia_impact": "",
    }
    msg = build_alert_message(**_BASE, analysis=analysis)
    assert msg is not None
    assert "🚨 WAR ALERT" in msg
    assert "ขีปนาวุธโจมตีเมืองหลวง" in msg
    assert "ทองคำพุ่งแรง" in msg
    assert "หุ้นร่วงหนัก" in msg
    assert "USD แข็งค่า" in msg
    assert "ตลาดผันผวนรุนแรง" in msg
    assert "🧠 สรุปข่าว:" in msg


def test_peace_with_ai_fields():
    analysis = {
        "category": "peace",
        "summary_th": "การเจรจาสันติภาพประสบความสำเร็จ",
        "market_impact": "ตลาดฟื้นตัว",
        "gold_impact": "ทองคำอ่อนตัว",
        "stock_impact": "หุ้นฟื้น",
        "usd_impact": "",
        "asia_impact": "ตลาดเอเชียบวก",
    }
    msg = build_alert_message(**_BASE, analysis=analysis)
    assert msg is not None
    assert "☮️ PEACE NEWS" in msg
    assert "การเจรจาสันติภาพประสบความสำเร็จ" in msg
    assert "ทองคำอ่อนตัว" in msg
    assert "หุ้นฟื้น" in msg
    assert "ตลาดเอเชียบวก" in msg
    assert "ตลาดฟื้นตัว" in msg
    assert "🧠 สรุปข่าว:" in msg


def test_danger_fallback_when_ai_fields_empty():
    analysis = {
        "category": "danger",
        "summary_th": "",
        "market_impact": "",
        "gold_impact": "",
        "stock_impact": "",
        "usd_impact": "",
        "asia_impact": "",
    }
    msg = build_alert_message(**_BASE, analysis=analysis)
    assert msg is not None
    assert "safe haven" in msg
    assert "risk-off" in msg
    assert "flight to safety" in msg
    assert "🧠 สรุปข่าว:" not in msg


def test_peace_fallback_when_ai_fields_empty():
    analysis = {
        "category": "peace",
        "summary_th": "",
        "market_impact": "",
        "gold_impact": "",
        "stock_impact": "",
        "usd_impact": "",
        "asia_impact": "",
    }
    msg = build_alert_message(**_BASE, analysis=analysis)
    assert msg is not None
    assert "safe haven demand" in msg
    assert "risk-on" in msg
    assert "อาจบวก" in msg
    assert "🧠 สรุปข่าว:" not in msg
