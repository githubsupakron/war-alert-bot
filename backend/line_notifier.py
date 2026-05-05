import httpx
import os
from typing import Optional


async def send_line_message(message: str, user_id: Optional[str] = None) -> bool:
    """ส่งข้อความผ่าน LINE Messaging API (Push Message)"""
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    target_id = user_id or os.getenv("LINE_USER_ID", "")

    if not token or not target_id:
        print("⚠️ Missing LINE credentials (token or user_id)")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": target_id,
        "messages": [{"type": "text", "text": message}],
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.line.me/v2/bot/message/push",
                headers=headers,
                json=payload,
            )
        if resp.status_code == 200:
            print("✅ LINE sent successfully")
            return True
        else:
            print(f"❌ LINE error: {resp.status_code} — {resp.text}")
            return False
    except Exception as e:
        print(f"❌ LINE exception: {e}")
        return False


async def broadcast_line_message(message: str) -> bool:
    """Broadcast ไปยังทุก follower"""
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"messages": [{"type": "text", "text": message}]}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.line.me/v2/bot/message/broadcast",
                headers=headers,
                json=payload,
            )
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ LINE broadcast exception: {e}")
        return False
