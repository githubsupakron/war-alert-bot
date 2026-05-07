import httpx
import os

FB_GRAPH_URL = "https://graph.facebook.com/v19.0"


async def post_to_facebook_page(message: str, link: str = "") -> bool:
    """Post a message (and optional link preview) to a Facebook Page feed."""
    page_id = os.getenv("FB_PAGE_ID", "")
    token   = os.getenv("FB_PAGE_ACCESS_TOKEN", "")

    if not page_id or not token:
        print("⚠️ Missing Facebook credentials (FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN)")
        return False

    payload: dict = {"message": message, "access_token": token}
    if link:
        payload["link"] = link  # adds link-preview card to the post

    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            resp = await client.post(f"{FB_GRAPH_URL}/{page_id}/feed", data=payload)

        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Facebook posted — post_id: {data.get('id')}")
            return True
        else:
            print(f"❌ Facebook error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Facebook exception: {e}")
        return False
