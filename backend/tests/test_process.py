import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


def _make_article(n: int) -> dict:
    return {
        "title":        f"Article {n}",
        "description":  f"Description {n}",
        "source":       "Reuters",
        "url":          f"https://example.com/{n}",
        "published_at": "2026-05-07T00:00:00Z",
    }


def _make_single_result(category: str = "neutral") -> dict:
    return {
        "category":               category,
        "confidence":             0.9 if category != "neutral" else 0.3,
        "reason":                 "test reason",
        "summary_th":             "สรุป",
        "market_impact":          "ผลกระทบ",
        "gold_impact":            "ทอง",
        "stock_impact":           "หุ้น",
        "usd_impact":             "USD",
        "asia_impact":            "เอเชีย",
        "crypto_currency_impact": "คริปโต",
    }


def _make_db(articles: list[dict], existing_urls: set[str] | None = None):
    """Return a mock SQLAlchemy Session."""
    existing_urls = existing_urls or set()

    mock_filter = MagicMock()
    mock_query  = MagicMock()
    mock_query.filter = MagicMock(return_value=mock_filter)

    db = MagicMock()
    db.query  = MagicMock(return_value=mock_query)
    db.add    = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()

    call_index = [0]

    def url_aware_first():
        idx = call_index[0]
        call_index[0] += 1
        if idx < len(articles) and articles[idx]["url"] in existing_urls:
            item = MagicMock()
            item.category = "neutral"
            item.alert_message = ""
            item.line_sent = True
            item.facebook_sent = True
            item.url = articles[idx]["url"]
            return item
        return None

    mock_filter.first = url_aware_first
    return db


def _settings_side_effect(_db, key: str, default: str = "") -> str:
    defaults = {
        "keywords":           "war",
        "max_news_age_hours": "6",
        "line_enabled":       "true",
        "facebook_enabled":   "false",
        "danger_keywords":    "",
        "peace_keywords":     "",
        "negative_keywords":  "",
        "classifier_mode":    "ai",
    }
    return defaults.get(key, default)


def _keyword_settings_side_effect(_db, key: str, default: str = "") -> str:
    defaults = {
        "keywords":           "war",
        "max_news_age_hours": "6",
        "line_enabled":       "true",
        "facebook_enabled":   "false",
        "danger_keywords":    "",
        "peace_keywords":     "",
        "negative_keywords":  "",
        "classifier_mode":    "keyword",
    }
    return defaults.get(key, default)


async def test_12_new_articles_produce_12_classify_calls():
    """12 new articles must trigger exactly 12 classify_with_codesmart calls (one per article)."""
    articles = [_make_article(i) for i in range(1, 13)]
    db = _make_db(articles)

    classify_mock = AsyncMock(return_value=_make_single_result("neutral"))

    with patch("main.get_setting", side_effect=_settings_side_effect), \
         patch("main.fetch_news_from_api", AsyncMock(return_value=articles)), \
         patch("main.classify_with_codesmart", classify_mock), \
         patch("main.translate_to_thai", AsyncMock(return_value="แปลแล้ว")), \
         patch("main.broadcast_line_message", AsyncMock(return_value=False)), \
         patch("main.post_to_facebook_page", AsyncMock(return_value=False)), \
         patch("main.build_alert_message", return_value=""):
        from main import process_and_notify
        result = await process_and_notify(db)

    assert classify_mock.call_count == 12
    assert result["new"] == 12


async def test_keyword_mode_makes_zero_classify_calls():
    """When classifier_mode is 'keyword', classify_with_codesmart is never called."""
    articles = [_make_article(i) for i in range(1, 4)]
    db = _make_db(articles)

    classify_mock = AsyncMock()

    with patch("main.get_setting", side_effect=_keyword_settings_side_effect), \
         patch("main.fetch_news_from_api", AsyncMock(return_value=articles)), \
         patch("main.classify_with_codesmart", classify_mock), \
         patch("main.keyword_classify", return_value={"category": "neutral", "confidence": 0.5, "reason": "", "market_impact": ""}), \
         patch("main.translate_to_thai", AsyncMock(return_value="แปลแล้ว")), \
         patch("main.broadcast_line_message", AsyncMock(return_value=False)), \
         patch("main.post_to_facebook_page", AsyncMock(return_value=False)), \
         patch("main.build_alert_message", return_value=""):
        from main import process_and_notify
        await process_and_notify(db)

    classify_mock.assert_not_called()


async def test_classify_failure_stores_neutral_fallback():
    """When classify_with_codesmart returns None, the article is stored as neutral fallback."""
    articles = [_make_article(1), _make_article(2)]
    db = _make_db(articles)

    added_items: list[MagicMock] = []
    db.add = lambda item: added_items.append(item)

    with patch("main.get_setting", side_effect=_settings_side_effect), \
         patch("main.fetch_news_from_api", AsyncMock(return_value=articles)), \
         patch("main.classify_with_codesmart", AsyncMock(return_value=None)), \
         patch("main.translate_to_thai", AsyncMock(return_value="แปลแล้ว")), \
         patch("main.broadcast_line_message", AsyncMock(return_value=False)), \
         patch("main.post_to_facebook_page", AsyncMock(return_value=False)), \
         patch("main.build_alert_message", return_value=""):
        from main import process_and_notify
        result = await process_and_notify(db)

    assert result["new"] == 2
    for item in added_items:
        assert item.category == "neutral"
        assert item.llm_fallback is True
        assert item.llm_used is False


async def test_danger_result_generates_line_alert():
    """A danger classification should trigger LINE broadcast."""
    articles = [_make_article(1)]
    db = _make_db(articles)

    line_mock = AsyncMock(return_value=True)

    with patch("main.get_setting", side_effect=_settings_side_effect), \
         patch("main.fetch_news_from_api", AsyncMock(return_value=articles)), \
         patch("main.classify_with_codesmart", AsyncMock(return_value=_make_single_result("danger"))), \
         patch("main.translate_to_thai", AsyncMock(return_value="แปลแล้ว")), \
         patch("main.broadcast_line_message", line_mock), \
         patch("main.post_to_facebook_page", AsyncMock(return_value=False)), \
         patch("main.build_alert_message", return_value="Alert message"):
        from main import process_and_notify
        result = await process_and_notify(db)

    line_mock.assert_called_once()
    assert result["sent_line"] == 1


async def test_peace_result_generates_line_alert():
    """A peace classification should trigger LINE broadcast."""
    articles = [_make_article(1)]
    db = _make_db(articles)

    line_mock = AsyncMock(return_value=True)

    with patch("main.get_setting", side_effect=_settings_side_effect), \
         patch("main.fetch_news_from_api", AsyncMock(return_value=articles)), \
         patch("main.classify_with_codesmart", AsyncMock(return_value=_make_single_result("peace"))), \
         patch("main.translate_to_thai", AsyncMock(return_value="แปลแล้ว")), \
         patch("main.broadcast_line_message", line_mock), \
         patch("main.post_to_facebook_page", AsyncMock(return_value=False)), \
         patch("main.build_alert_message", return_value="Alert message"):
        from main import process_and_notify
        result = await process_and_notify(db)

    line_mock.assert_called_once()
    assert result["sent_line"] == 1
