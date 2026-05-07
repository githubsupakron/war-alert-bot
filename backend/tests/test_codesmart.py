import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from codesmart_client import classify_with_codesmart

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
