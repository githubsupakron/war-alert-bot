from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from facebook_notifier import post_to_facebook_page
from line_notifier import broadcast_line_message, send_line_message


pytestmark = pytest.mark.asyncio


def _mock_client(status_code: int, body: dict | None = None, text: str = ""):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = body or {}

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.post = AsyncMock(return_value=response)
    return client


async def test_send_line_message_posts_push_payload():
    client = _mock_client(200)

    with patch("line_notifier.httpx.AsyncClient", return_value=client), patch.dict(
        "os.environ",
        {"LINE_CHANNEL_ACCESS_TOKEN": "line-token", "LINE_USER_ID": "user-id"},
        clear=True,
    ):
        result = await send_line_message("hello")

    assert result is True
    _, kwargs = client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer line-token"
    assert kwargs["json"] == {"to": "user-id", "messages": [{"type": "text", "text": "hello"}]}


async def test_send_line_message_returns_false_without_credentials():
    with patch.dict("os.environ", {}, clear=True):
        result = await send_line_message("hello")

    assert result is False


async def test_broadcast_line_message_posts_broadcast_payload():
    client = _mock_client(200)

    with patch("line_notifier.httpx.AsyncClient", return_value=client), patch.dict(
        "os.environ", {"LINE_CHANNEL_ACCESS_TOKEN": "line-token"}, clear=True
    ):
        result = await broadcast_line_message("alert")

    assert result is True
    args, kwargs = client.post.call_args
    assert args[0] == "https://api.line.me/v2/bot/message/broadcast"
    assert kwargs["json"] == {"messages": [{"type": "text", "text": "alert"}]}


async def test_facebook_post_includes_message_token_and_link():
    client = _mock_client(200, {"id": "post-id"})

    with patch("facebook_notifier.httpx.AsyncClient", return_value=client), patch.dict(
        "os.environ",
        {"FB_PAGE_ID": "page-id", "FB_PAGE_ACCESS_TOKEN": "fb-token"},
        clear=True,
    ):
        result = await post_to_facebook_page("message", "https://example.com")

    assert result is True
    args, kwargs = client.post.call_args
    assert args[0] == "https://graph.facebook.com/v19.0/page-id/feed"
    assert kwargs["data"] == {
        "message": "message",
        "access_token": "fb-token",
        "link": "https://example.com",
    }


async def test_facebook_post_returns_false_without_credentials():
    with patch.dict("os.environ", {}, clear=True):
        result = await post_to_facebook_page("message")

    assert result is False
