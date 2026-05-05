import httpx


def is_thai(text: str) -> bool:
    return any('฀' <= c <= '๿' for c in (text or ''))


async def translate_to_thai(text: str) -> str:
    """Translate text to Thai using Google Translate (unofficial, free).
    Returns original text if already Thai or if translation fails."""
    if not text or is_thai(text):
        return text
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                "https://translate.googleapis.com/translate_a/single",
                params={"client": "gtx", "sl": "auto", "tl": "th", "dt": "t", "q": text[:500]},
            )
        data = resp.json()
        result = "".join(p[0] for p in data[0] if p and p[0])
        return result if result else text
    except Exception as e:
        print(f"[Translator] {e}")
        return text
