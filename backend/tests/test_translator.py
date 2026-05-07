from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from translator import is_thai, translate_to_thai


def _mock_client_with_json(payload):
    response = MagicMock()
    response.json.return_value = payload

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(return_value=response)
    return client


def test_is_thai_detects_thai_characters():
    assert is_thai("ข่าวสงคราม") is True
    assert is_thai("war news") is False


@pytest.mark.asyncio
async def test_translate_to_thai_returns_original_for_empty_or_thai_text():
    assert await translate_to_thai("") == ""
    assert await translate_to_thai("ข่าวสงคราม") == "ข่าวสงคราม"


@pytest.mark.asyncio
async def test_translate_to_thai_uses_google_translate_endpoint():
    client = _mock_client_with_json([[["สวัสดี"]]])

    with patch("translator.httpx.AsyncClient", return_value=client):
        result = await translate_to_thai("Hello")

    assert result == "สวัสดี"
    _, kwargs = client.get.call_args
    assert kwargs["params"]["sl"] == "auto"
    assert kwargs["params"]["tl"] == "th"
    assert kwargs["params"]["q"] == "Hello"


@pytest.mark.asyncio
async def test_translate_to_thai_returns_original_on_exception():
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(side_effect=Exception("network down"))

    with patch("translator.httpx.AsyncClient", return_value=client):
        result = await translate_to_thai("Hello")

    assert result == "Hello"
