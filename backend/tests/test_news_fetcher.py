from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news_fetcher import fetch_news_from_api, parse_published_at


def _mock_client_with_response(payload: dict):
    response = MagicMock()
    response.json.return_value = payload

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(return_value=response)
    return client


@pytest.mark.asyncio
async def test_fetch_news_builds_newsapi_request_and_filters_removed_titles():
    client = _mock_client_with_response(
        {
            "status": "ok",
            "articles": [
                {
                    "title": "Missile strike reported",
                    "description": "A short description",
                    "url": "https://example.com/a",
                    "source": {"name": "Reuters"},
                    "publishedAt": "2026-05-07T00:00:00Z",
                },
                {
                    "title": "[Removed]",
                    "description": "Removed item",
                    "url": "https://example.com/removed",
                    "source": {"name": "Unknown"},
                    "publishedAt": "2026-05-07T00:01:00Z",
                },
            ],
        }
    )

    with patch("news_fetcher.httpx.AsyncClient", return_value=client), patch.dict(
        "os.environ", {"NEWSAPI_KEY": "news-key"}
    ):
        result = await fetch_news_from_api(
            "Iran attack,Israel strike,war,ceasefire,peace talks,extra",
            from_dt=datetime(2026, 5, 7, 0, 0, 0),
            to_dt=datetime(2026, 5, 7, 1, 0, 0),
        )

    assert result == [
        {
            "title": "Missile strike reported",
            "description": "A short description",
            "url": "https://example.com/a",
            "source": "Reuters",
            "published_at": "2026-05-07T00:00:00Z",
        }
    ]
    _, kwargs = client.get.call_args
    assert kwargs["params"]["q"] == '"Iran attack" OR "Israel strike" OR "war" OR "ceasefire" OR "peace talks"'
    assert kwargs["params"]["language"] == "en"
    assert kwargs["params"]["pageSize"] == 100
    assert kwargs["params"]["apiKey"] == "news-key"


@pytest.mark.asyncio
async def test_fetch_news_returns_empty_when_api_key_missing():
    with patch.dict("os.environ", {}, clear=True):
        result = await fetch_news_from_api("war")

    assert result == []


@pytest.mark.asyncio
async def test_fetch_news_returns_empty_on_newsapi_error_response():
    client = _mock_client_with_response({"status": "error", "message": "quota exceeded"})

    with patch("news_fetcher.httpx.AsyncClient", return_value=client), patch.dict(
        "os.environ", {"NEWSAPI_KEY": "news-key"}
    ):
        result = await fetch_news_from_api("war")

    assert result == []


def test_parse_published_at_accepts_zulu_timestamp():
    parsed = parse_published_at("2026-05-07T10:11:12Z")

    assert parsed == datetime(2026, 5, 7, 10, 11, 12)


def test_parse_published_at_falls_back_to_utcnow_on_bad_value():
    with patch("news_fetcher.datetime") as mock_datetime:
        mock_datetime.fromisoformat.side_effect = ValueError("bad date")
        mock_datetime.utcnow.return_value = datetime(2026, 5, 7, 12, 0, 0)

        parsed = parse_published_at("not-a-date")

    assert parsed == datetime(2026, 5, 7, 12, 0, 0)
