"""
CodeSmart AI classifier for news articles.
Calls CodeSmart Chat Completions; returns None on any failure so callers can
avoid sending false alerts when AI mode is unavailable.
"""
from __future__ import annotations

import json
import os
import re
import time

import httpx

_SYSTEM_PROMPT = (
    "You are a geopolitical news classifier. "
    "Classify each news article as danger, peace, or neutral. "
    "Use danger for military escalation, attacks, strikes, casualties, invasion, "
    "missile/drone activity, bombing, or credible threats. "
    "Use peace for ceasefire, peace talks, de-escalation, withdrawal, treaties, "
    "hostage/prisoner deals, mediation, or agreements. "
    "Use neutral when the article is not clearly war-related or the evidence is weak. "
    "Respond ONLY with valid JSON containing exactly these keys: "
    "category (string: 'danger', 'peace', or 'neutral'), "
    "confidence (float 0.0–1.0), "
    "reason (string, max 200 chars), "
    "market_impact (string in Thai, max 200 chars). "
    "No other text, no markdown, no explanation outside the JSON object."
)

_VALID_CATEGORIES = {"danger", "peace", "neutral"}
_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.IGNORECASE | re.DOTALL)


def _preview(value, limit: int = 500) -> str:
    text = str(value or "")
    text = text.replace("\n", "\\n").replace("\r", "\\r")
    if len(text) > limit:
        return text[:limit] + "...<truncated>"
    return text


def _response_debug(resp) -> str:
    content_type = ""
    try:
        content_type = resp.headers.get("content-type", "")
    except Exception:
        content_type = ""
    return (
        f"status={getattr(resp, 'status_code', 'unknown')} "
        f"content_type={content_type or '-'} "
        f"body_preview={_preview(getattr(resp, 'text', ''), 800)!r}"
    )


def _completion_debug(data: dict) -> str:
    choice = {}
    if isinstance(data, dict):
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            choice = choices[0] if isinstance(choices[0], dict) else {}
    usage = data.get("usage") if isinstance(data, dict) else None
    return (
        f"id={data.get('id', '-') if isinstance(data, dict) else '-'} "
        f"model={data.get('model', '-') if isinstance(data, dict) else '-'} "
        f"finish_reason={choice.get('finish_reason', '-')} "
        f"usage={usage if usage is not None else '-'}"
    )


def _article_debug(article: dict) -> str:
    return (
        f"title={_preview(article.get('title', ''), 160)!r} "
        f"source={_preview(article.get('source', ''), 80)!r} "
        f"published_at={_preview(article.get('published_at', ''), 80)!r}"
    )


def _extract_message_content(data: dict) -> str | None:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content)


def _parse_assistant_json(content: str) -> dict:
    cleaned = (content or "").strip()
    fence_match = _JSON_FENCE_RE.match(cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(cleaned[start:end + 1])

    if not isinstance(parsed, dict):
        raise ValueError(f"assistant JSON must be an object, got {type(parsed).__name__}")
    return parsed


def _build_user_prompt(article: dict) -> str:
    return (
        f"Article:\n"
        f"  Title: {article.get('title', '')}\n"
        f"  Description: {article.get('description', '')}\n"
        f"  Source: {article.get('source', '')}\n"
        f"  Published: {article.get('published_at', '')}\n\n"
        f"Classify this article and return ONLY valid JSON."
    )


async def classify_with_codesmart(article: dict) -> dict | None:
    """
    Call CodeSmart to classify an article in AI mode.
    Returns dict with category/confidence/reason/market_impact, or None on failure.
    """
    api_key = os.getenv("CODESMART_API_KEY", "")
    if not api_key:
        return None

    api_url = os.getenv("CODESMART_API_URL", "https://api.codesmart.app/v1/chat/completions")
    model   = os.getenv("CODESMART_MODEL", "claude-sonnet-4.6")

    payload = {
        "model": model,
        "stream": False,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": _build_user_prompt(article)},
        ],
    }

    started_at = time.perf_counter()
    print(
        "[CodeSmart] Calling API: "
        f"url={api_url} model={model} temperature={payload['temperature']} "
        f"{_article_debug(article)}"
    )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                api_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        print(f"[CodeSmart] API response received: status={resp.status_code} elapsed_ms={elapsed_ms}")

        if resp.status_code != 200:
            print(f"[CodeSmart] HTTP error after {elapsed_ms}ms: {_response_debug(resp)}")
            return None

        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            print(f"[CodeSmart] Response JSON parse error: {exc}; {_response_debug(resp)}")
            return None

        content = _extract_message_content(data)
        if content is None:
            print(
                "[CodeSmart] Unexpected response shape: "
                f"{_completion_debug(data)}; "
                f"top_level_keys={list(data.keys()) if isinstance(data, dict) else type(data).__name__}; "
                f"response_preview={_preview(data, 800)!r}"
            )
            return None

        try:
            parsed = _parse_assistant_json(content)
        except (json.JSONDecodeError, ValueError) as exc:
            print(
                "[CodeSmart] Non-JSON assistant content: "
                f"{exc}; {_completion_debug(data)}; "
                f"content_preview={_preview(content, 800)!r}; {_response_debug(resp)}"
            )
            return None

        if parsed.get("category") not in _VALID_CATEGORIES:
            print(f"[CodeSmart] Invalid category: {parsed.get('category')!r}; parsed={_preview(parsed, 800)!r}")
            return None
        if not isinstance(parsed.get("confidence"), (int, float)):
            print(f"[CodeSmart] Invalid confidence: {parsed.get('confidence')!r}; parsed={_preview(parsed, 800)!r}")
            return None

        result = {
            "category":      str(parsed["category"]),
            "confidence":    float(parsed["confidence"]),
            "reason":        str(parsed.get("reason", ""))[:500],
            "market_impact": str(parsed.get("market_impact", ""))[:500],
        }
        print(
            "[CodeSmart] Classification success: "
            f"category={result['category']} confidence={result['confidence']:.3f} "
            f"{_completion_debug(data)}"
        )
        return result

    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        print(
            "[CodeSmart] Request error: "
            f"{type(exc).__name__}: {exc}; elapsed_ms={elapsed_ms} "
            f"url={api_url} model={model} {_article_debug(article)}"
        )
        return None
