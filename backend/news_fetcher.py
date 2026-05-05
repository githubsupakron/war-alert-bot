import httpx
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional


async def fetch_news_from_api(
    keywords: str,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
    hours_back: int = 6,
) -> List[Dict]:
    """
    ดึงข่าวจาก NewsAPI.org
    - ถ้าส่ง from_dt / to_dt มา → ใช้ช่วงเวลานั้น (Manual mode)
    - ถ้าไม่ส่ง → ย้อนหลัง hours_back ชั่วโมง (Auto mode)
    """
    api_key = os.getenv("NEWSAPI_KEY", "")
    if not api_key:
        print("⚠️ No NEWSAPI_KEY found")
        return []

    # สร้าง query จาก keywords
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    query = " OR ".join([f'"{kw}"' for kw in kw_list[:5]])

    # กำหนดช่วงเวลา
    if from_dt and to_dt:
        from_str = from_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        to_str = to_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        from_str = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
        to_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "q": query,
        "from": from_str,
        "to": to_str,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 100,
        "apiKey": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get("https://newsapi.org/v2/everything", params=params)
            data = resp.json()

        if data.get("status") != "ok":
            print(f"NewsAPI error: {data.get('message')}")
            return []

        articles = data.get("articles", [])
        results = []
        for a in articles:
            title = a.get("title", "")
            if title and "[Removed]" not in title:
                results.append({
                    "title": title,
                    "description": a.get("description") or a.get("content") or "",
                    "url": a.get("url", ""),
                    "source": a.get("source", {}).get("name", "Unknown"),
                    "published_at": a.get("publishedAt", ""),
                })
        return results

    except Exception as e:
        print(f"NewsAPI fetch error: {e}")
        return []


def parse_published_at(published_str: str) -> datetime:
    """แปลง ISO string เป็น datetime"""
    try:
        return datetime.fromisoformat(published_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()
