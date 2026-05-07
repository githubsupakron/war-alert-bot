import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from codesmart_client import _legacy_classify_batch_with_codesmart, classify_with_codesmart

pytestmark = pytest.mark.asyncio

_ARTICLE = {
    "title":        "Missile strikes capital",
    "description":  "Rockets and bombs hit the city centre",
    "source":       "Reuters",
    "published_at": "2026-05-07T00:00:00Z",
}
def _make_mock_client(status: int, body: dict | None = None, text: str = ""):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.text = text
    if body is not None:
        mock_resp.json.return_value = body

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)
    return mock_client


async def test_valid_response_returns_parsed_dict():
    payload = json.dumps({
        "category": "danger", "confidence": 0.92,
        "reason": "Clear military attack",
        "summary_th": "ขีปนาวุธโจมตีเมืองหลวง",
        "market_impact": "ทองคำอาจพุ่งสูงในระยะสั้น",
        "gold_impact": "📈 ทองคำอาจพุ่งแรง",
        "stock_impact": "📉 หุ้นร่วงหนัก",
        "usd_impact": "USD แข็งค่าขึ้น",
        "asia_impact": "",
    })
    body = {"choices": [{"message": {"content": payload}}]}
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is not None
    assert result["category"] == "danger"
    assert result["confidence"] == 0.92
    assert result["reason"] == "Clear military attack"
    assert result["summary_th"] == "ขีปนาวุธโจมตีเมืองหลวง"
    assert result["market_impact"] == "ทองคำอาจพุ่งสูงในระยะสั้น"
    assert result["gold_impact"] == "📈 ทองคำอาจพุ่งแรง"
    assert result["stock_impact"] == "📉 หุ้นร่วงหนัก"
    assert result["usd_impact"] == "USD แข็งค่าขึ้น"
    assert result["asia_impact"] == ""


async def test_missing_optional_fields_default_to_empty_string():
    payload = json.dumps({
        "category": "peace", "confidence": 0.80,
        "reason": "Ceasefire",
        # summary_th, market_impact, gold_impact, stock_impact, usd_impact, asia_impact all absent
    })
    body = {"choices": [{"message": {"content": payload}}]}
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is not None
    assert result["category"] == "peace"
    assert result["summary_th"] == ""
    assert result["market_impact"] == ""
    assert result["gold_impact"] == ""
    assert result["stock_impact"] == ""
    assert result["usd_impact"] == ""
    assert result["asia_impact"] == ""


async def test_invalid_json_returns_none():
    body = {"choices": [{"message": {"content": "not valid json at all"}}]}
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is None


async def test_non_200_returns_none():
    mock_client = _make_mock_client(500, text="Internal Server Error")

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is None


async def test_no_api_key_returns_none():
    env = {k: v for k, v in os.environ.items() if k != "CODESMART_API_KEY"}
    with patch.dict("os.environ", env, clear=True):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is None


async def test_invalid_category_returns_none():
    payload = json.dumps({
        "category": "UNKNOWN", "confidence": 0.9,
        "reason": "test", "market_impact": "N/A",
    })
    body = {"choices": [{"message": {"content": payload}}]}
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is None


async def test_missing_confidence_returns_none():
    payload = json.dumps({
        "category": "danger",
        "reason": "test", "market_impact": "Gold up",
        # confidence key absent
    })
    body = {"choices": [{"message": {"content": payload}}]}
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is None


async def test_network_exception_returns_none():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=Exception("connection refused"))

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is None


async def test_peace_category_accepted():
    payload = json.dumps({
        "category": "peace", "confidence": 0.88,
        "reason": "Ceasefire signed", "market_impact": "Gold down",
    })
    body = {"choices": [{"message": {"content": payload}}]}
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is not None
    assert result["category"] == "peace"


async def test_neutral_category_accepted():
    payload = json.dumps({
        "category": "neutral", "confidence": 0.55,
        "reason": "Context unclear", "market_impact": "",
    })
    body = {"choices": [{"message": {"content": payload}}]}
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is not None
    assert result["category"] == "neutral"


async def test_plain_assistant_text_returns_none():
    body = {
        "id": "chatcmpl-728d22f4-e30e-47e6-9729-6b74f9c320b0",
        "created": 1778131076,
        "model": "claude-sonnet-4-6",
        "object": "chat.completion",
        "choices": [{
            "finish_reason": "stop",
            "index": 0,
            "message": {
                "content": "Hello! How are you doing? Is there something I can help you with today?",
                "role": "assistant",
            },
        }],
        "usage": {"completion_tokens": 23, "prompt_tokens": 15, "total_tokens": 38},
    }
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is None


async def test_fenced_json_content_is_accepted():
    payload = """```json
{"category": "danger", "confidence": 0.91, "reason": "Missile strike", "summary_th": "ขีปนาวุธโจมตีเป้าหมาย", "market_impact": "ทองคำอาจปรับขึ้น", "gold_impact": "ทองคำพุ่ง", "stock_impact": "หุ้นร่วง", "usd_impact": "USD แข็ง", "asia_impact": ""}
```"""
    body = {"choices": [{"message": {"content": payload}}]}
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is not None
    assert result["category"] == "danger"


async def test_embedded_json_content_is_accepted():
    payload = 'Here is the result: {"category": "peace", "confidence": 0.82, "reason": "Peace talks", "summary_th": "การเจรจาสันติภาพเริ่มขึ้น", "market_impact": "ทองคำอาจอ่อนตัว", "gold_impact": "ทองคำอ่อนตัว", "stock_impact": "หุ้นฟื้น", "usd_impact": "", "asia_impact": "ตลาดเอเชียบวก"}'
    body = {"choices": [{"message": {"content": payload}}]}
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is not None
    assert result["category"] == "peace"


# ── _legacy_classify_batch_with_codesmart tests ───────────────────────────────────────

def _make_batch_body(results: list[dict]) -> dict:
    return {"choices": [{"message": {"content": json.dumps({"results": results})}}]}


def _make_article(n: int) -> dict:
    return {
        "title":        f"Article {n}",
        "description":  f"Description {n}",
        "source":       "Reuters",
        "published_at": "2026-05-07T00:00:00Z",
    }


def _result_item(news_id: str, category: str = "neutral", confidence: float = 0.5) -> dict:
    return {
        "id":            news_id,
        "category":      category,
        "confidence":    confidence,
        "reason":        f"reason for {news_id}",
        "summary_th":    "สรุปข่าว",
        "market_impact": "ผลกระทบตลาด",
        "gold_impact":   "ทองคำ",
        "stock_impact":  "หุ้น",
        "usd_impact":    "USD",
        "asia_impact":   "เอเชีย",
    }


async def test_batch_valid_5_items():
    articles = [_make_article(i) for i in range(1, 6)]
    raw = [_result_item(f"news_{i}", "neutral", 0.5) for i in range(1, 6)]
    mock_client = _make_mock_client(200, _make_batch_body(raw))

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await _legacy_classify_batch_with_codesmart(articles)

    assert result is not None
    assert len(result) == 5
    for i in range(1, 6):
        assert f"news_{i}" in result
        assert result[f"news_{i}"]["category"] == "neutral"


async def test_batch_fewer_than_5_articles():
    articles = [_make_article(i) for i in range(1, 3)]
    raw = [_result_item(f"news_{i}", "danger", 0.9) for i in range(1, 3)]
    mock_client = _make_mock_client(200, _make_batch_body(raw))

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await _legacy_classify_batch_with_codesmart(articles)

    assert result is not None
    assert len(result) == 2
    assert result["news_1"]["category"] == "danger"
    assert result["news_2"]["category"] == "danger"


async def test_batch_missing_article_id_absent_from_result():
    articles = [_make_article(i) for i in range(1, 4)]
    # news_2 is absent from the response
    raw = [_result_item("news_1", "danger", 0.9), _result_item("news_3", "peace", 0.8)]
    mock_client = _make_mock_client(200, _make_batch_body(raw))

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await _legacy_classify_batch_with_codesmart(articles)

    assert result is not None
    assert "news_1" in result
    assert "news_3" in result
    assert "news_2" not in result


async def test_batch_invalid_json_returns_none():
    body = {"choices": [{"message": {"content": "not json at all"}}]}
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await _legacy_classify_batch_with_codesmart([_make_article(1)])

    assert result is None


async def test_batch_non_200_returns_none():
    mock_client = _make_mock_client(500, text="Internal Server Error")

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await _legacy_classify_batch_with_codesmart([_make_article(1)])

    assert result is None


async def test_batch_invalid_category_rejected_for_item():
    articles = [_make_article(1), _make_article(2)]
    raw = [
        {**_result_item("news_1", "danger", 0.9)},
        {**_result_item("news_2"), "category": "INVALID"},
    ]
    mock_client = _make_mock_client(200, _make_batch_body(raw))

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await _legacy_classify_batch_with_codesmart(articles)

    assert result is not None
    assert "news_1" in result
    assert "news_2" not in result


async def test_batch_invalid_confidence_rejected_for_item():
    articles = [_make_article(1), _make_article(2)]
    raw = [
        {**_result_item("news_1", "peace", 0.8)},
        {**_result_item("news_2"), "confidence": "high"},
    ]
    mock_client = _make_mock_client(200, _make_batch_body(raw))

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await _legacy_classify_batch_with_codesmart(articles)

    assert result is not None
    assert "news_1" in result
    assert "news_2" not in result


async def test_batch_no_api_key_returns_none():
    env = {k: v for k, v in os.environ.items() if k != "CODESMART_API_KEY"}
    with patch.dict("os.environ", env, clear=True):
        result = await _legacy_classify_batch_with_codesmart([_make_article(1)])

    assert result is None


async def test_batch_empty_list_returns_empty_dict():
    with patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await _legacy_classify_batch_with_codesmart([])

    assert result == {}


async def test_batch_unknown_id_skipped():
    articles = [_make_article(1)]
    raw = [
        _result_item("news_99", "danger", 0.9),
        _result_item("news_1",  "peace",  0.7),
    ]
    mock_client = _make_mock_client(200, _make_batch_body(raw))

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await _legacy_classify_batch_with_codesmart(articles)

    assert result is not None
    assert "news_1" in result
    assert "news_99" not in result


async def test_batch_duplicate_id_uses_first_occurrence():
    articles = [_make_article(1)]
    raw = [
        _result_item("news_1", "danger", 0.9),
        _result_item("news_1", "peace",  0.5),  # duplicate — second is skipped
    ]
    mock_client = _make_mock_client(200, _make_batch_body(raw))

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await _legacy_classify_batch_with_codesmart(articles)

    assert result is not None
    assert result["news_1"]["category"] == "danger"


async def test_classify_with_codesmart_direct_call_succeeds():
    payload = json.dumps({
        "category": "danger", "confidence": 0.95,
        "reason": "Direct single-article call",
        "summary_th": "ทดสอบ", "market_impact": "ทอง",
        "gold_impact": "สูง", "stock_impact": "ต่ำ",
        "usd_impact": "แข็ง", "asia_impact": "",
        "crypto_currency_impact": "ผันผวน",
    })
    body = {"choices": [{"message": {"content": payload}}]}
    mock_client = _make_mock_client(200, body)

    with patch("codesmart_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"CODESMART_API_KEY": "test-key"}):
        result = await classify_with_codesmart(_ARTICLE)

    assert result is not None
    assert result["category"] == "danger"
    assert result["confidence"] == 0.95
    assert result["crypto_currency_impact"] == "ผันผวน"
