from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

from models import NewsItem, Setting, get_db, init_db, SessionLocal
from news_fetcher import fetch_news_from_api, parse_published_at
from analyzer import keyword_classify, build_alert_message
from codesmart_client import classify_with_codesmart
from line_notifier import broadcast_line_message
from facebook_notifier import post_to_facebook_page
from translator import translate_to_thai

scheduler = AsyncIOScheduler()
last_fetch_time: Optional[datetime] = None


# ─── Pydantic Models ──────────────────────────────────────────

class ManualFetchRequest(BaseModel):
    from_datetime: Optional[str] = None
    to_datetime: Optional[str] = None

class SchedulerSettings(BaseModel):
    auto_fetch: bool
    interval_value: int
    interval_unit: str        # seconds / minutes / hours / days

class KeywordSettings(BaseModel):
    keywords: str
    danger_keywords: str
    peace_keywords: str
    max_news_age_hours: int
    # Classifier setting is optional so existing frontend calls keep working.
    negative_keywords: Optional[str]          = None
    classifier_mode: Optional[str]            = None   # "keyword" or "ai"

class ChannelSettings(BaseModel):
    line_enabled: bool
    facebook_enabled: bool


# ─── Helpers ──────────────────────────────────────────────────

def get_setting(db: Session, key: str, default: str = "") -> str:
    s = db.query(Setting).filter(Setting.key == key).first()
    return s.value if s else default

def set_setting(db: Session, key: str, value: str):
    s = db.query(Setting).filter(Setting.key == key).first()
    if s:
        s.value = value
    else:
        db.add(Setting(key=key, value=value))

def apply_scheduler(interval_value: int, interval_unit: str):
    scheduler.remove_all_jobs()
    scheduler.add_job(
        scheduled_fetch,
        IntervalTrigger(**{interval_unit: interval_value}),
        id="auto_fetch",
        replace_existing=True,
    )
    print(f"[Scheduler] Set to every {interval_value} {interval_unit}")

def build_fb_message(alert_msg: str) -> str:
    """Append hashtags to the LINE-style alert message for Facebook."""
    return alert_msg + "\n\n#WarAlertBot #ทองคำ #หุ้น #ข่าวสงคราม #GoldAlert"


# ─── Core Process ─────────────────────────────────────────────

async def process_and_notify(
    db: Session,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
) -> dict:
    global last_fetch_time
    last_fetch_time = datetime.utcnow()

    keywords        = get_setting(db, "keywords", "Iran attack,Israel strike,war")
    hours_back      = int(get_setting(db, "max_news_age_hours", "6"))
    line_on         = get_setting(db, "line_enabled", "true") == "true"
    fb_on           = get_setting(db, "facebook_enabled", "false") == "true"
    danger_kw_csv   = get_setting(db, "danger_keywords", "")
    peace_kw_csv    = get_setting(db, "peace_keywords", "")
    negative_kw_csv = get_setting(db, "negative_keywords", "")
    classifier_mode = get_setting(db, "classifier_mode", "keyword")
    use_ai          = classifier_mode == "ai"

    articles = await fetch_news_from_api(
        keywords=keywords,
        from_dt=from_dt,
        to_dt=to_dt,
        hours_back=hours_back,
    )

    new_count = sent_line = sent_fb = 0

    for article in articles:
        existing = db.query(NewsItem).filter(NewsItem.url == article["url"]).first()
        if existing:
            # Already in DB — retry sending to channels that haven't received it yet
            if existing.category in ("danger", "peace") and existing.alert_message:
                if line_on and not existing.line_sent:
                    if await broadcast_line_message(existing.alert_message):
                        existing.line_sent = True
                        db.commit()
                        sent_line += 1
                if fb_on and not existing.facebook_sent:
                    if await post_to_facebook_page(build_fb_message(existing.alert_message), existing.url or ""):
                        existing.facebook_sent = True
                        db.commit()
                        sent_fb += 1
            continue

        llm_used     = False
        llm_fallback = False
        if use_ai:
            llm_result = await classify_with_codesmart(article)
            if llm_result is not None:
                llm_used     = True
                final_result = llm_result
            else:
                llm_fallback = True
                final_result = {
                    "category": "neutral",
                    "confidence": 0.0,
                    "reason": "CodeSmart AI classifier unavailable",
                    "market_impact": "",
                }
        else:
            final_result = keyword_classify(article["title"], article["description"],
                                            danger_kw_csv, peace_kw_csv, negative_kw_csv)

        category      = final_result.get("category", "neutral")
        confidence    = final_result.get("confidence", 0.0)
        reason        = final_result.get("reason", "")
        market_impact = final_result.get("market_impact", "")

        pub_dt   = parse_published_at(article["published_at"])
        thai_dt  = pub_dt + timedelta(hours=7)
        pub_str  = thai_dt.strftime("%Y-%m-%d %H:%M น. (เวลาไทย)")
        title_th = await translate_to_thai(article["title"])
        alert_msg = build_alert_message(
            article["title"], title_th, article["url"],
            {"category": category, "market_impact": market_impact},
            pub_str,
        )

        news = NewsItem(
            title=article["title"],
            title_th=title_th,
            description=(article["description"] or "")[:500],
            url=article["url"],
            source=article["source"],
            published_at=pub_dt,
            category=category,
            alert_message=alert_msg or "",
            line_sent=False,
            facebook_sent=False,
            classification_confidence=confidence,
            classification_reason=(reason or "")[:500],
            llm_used=llm_used,
            llm_fallback=llm_fallback,
        )
        db.add(news)
        db.commit()
        db.refresh(news)
        new_count += 1

        if alert_msg and category in ("danger", "peace"):
            if line_on and await broadcast_line_message(alert_msg):
                news.line_sent = True
                db.commit()
                sent_line += 1

            if fb_on:
                if await post_to_facebook_page(build_fb_message(alert_msg), article["url"]):
                    news.facebook_sent = True
                    db.commit()
                    sent_fb += 1

    return {
        "fetched":    len(articles),
        "new":        new_count,
        "sent_line":  sent_line,
        "sent_fb":    sent_fb,
        "sent":       sent_line,   # backward compat
    }


async def scheduled_fetch():
    db = SessionLocal()
    try:
        result = await process_and_notify(db)
        print(f"[Scheduler] {datetime.utcnow().strftime('%H:%M:%S')} → {result}")
    finally:
        db.close()


# ─── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.start()
    db = SessionLocal()
    try:
        if get_setting(db, "auto_fetch") == "true":
            iv   = int(get_setting(db, "fetch_interval_value", "30"))
            unit = get_setting(db, "fetch_interval_unit", "minutes")
            apply_scheduler(iv, unit)
            print(f"✅ Auto-fetch restored: every {iv} {unit}")
    finally:
        db.close()
    print("✅ War Alert Bot v2.2 started!")
    yield
    if scheduler.running:
        scheduler.shutdown()


# ─── App ──────────────────────────────────────────────────────

app = FastAPI(title="War Alert Bot API", version="2.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Status ───────────────────────────────────────────────────

@app.get("/api/status")
async def get_status(db: Session = Depends(get_db)):
    total        = db.query(NewsItem).count()
    line_sent    = db.query(NewsItem).filter(NewsItem.line_sent == True).count()
    fb_sent      = db.query(NewsItem).filter(NewsItem.facebook_sent == True).count()
    danger_count = db.query(NewsItem).filter(NewsItem.category == "danger").count()
    peace_count  = db.query(NewsItem).filter(NewsItem.category == "peace").count()
    return {
        "auto_fetch":        get_setting(db, "auto_fetch") == "true",
        "interval_value":    int(get_setting(db, "fetch_interval_value", "30")),
        "interval_unit":     get_setting(db, "fetch_interval_unit", "minutes"),
        "last_fetch":        last_fetch_time.isoformat() if last_fetch_time else None,
        "total_news":        total,
        "sent_news":         line_sent,
        "fb_sent":           fb_sent,
        "danger_count":      danger_count,
        "peace_count":       peace_count,
        "scheduler_running": scheduler.running,
        "scheduler_jobs":    len(scheduler.get_jobs()),
        "line_enabled":      get_setting(db, "line_enabled", "true") == "true",
        "facebook_enabled":  get_setting(db, "facebook_enabled", "false") == "true",
        "classifier_mode":   get_setting(db, "classifier_mode", "keyword"),
        "codesmart_ready":   bool(os.getenv("CODESMART_API_KEY", "")),
    }


# ─── News ─────────────────────────────────────────────────────

@app.get("/api/news")
async def get_news(
    limit: int = 100,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(NewsItem).order_by(NewsItem.created_at.desc())
    if category and category != "all":
        if category == "sent":
            q = q.filter(NewsItem.line_sent == True)
        elif category == "fb_sent":
            q = q.filter(NewsItem.facebook_sent == True)
        else:
            q = q.filter(NewsItem.category == category)
    news = q.limit(limit).all()
    return [
        {
            "id":                        n.id,
            "title":                     n.title,
            "title_th":                  n.title_th or "",
            "description":               n.description,
            "url":                       n.url,
            "source":                    n.source,
            "published_at":              n.published_at.isoformat() if n.published_at else None,
            "category":                  n.category,
            "alert_message":             n.alert_message,
            "line_sent":                 n.line_sent,
            "facebook_sent":             n.facebook_sent or False,
            "created_at":                n.created_at.isoformat() if n.created_at else None,
            "classification_confidence": n.classification_confidence or 0.0,
            "classification_reason":     n.classification_reason or "",
            "llm_used":                  n.llm_used or False,
            "llm_fallback":              n.llm_fallback or False,
        }
        for n in news
    ]


@app.post("/api/news/fetch")
async def manual_fetch(req: ManualFetchRequest, db: Session = Depends(get_db)):
    from_dt = to_dt = None
    if req.from_datetime:
        from_dt = datetime.fromisoformat(req.from_datetime)
    if req.to_datetime:
        to_dt = datetime.fromisoformat(req.to_datetime)
    result = await process_and_notify(db, from_dt=from_dt, to_dt=to_dt)
    return {"status": "success", **result}


@app.delete("/api/news/{news_id}")
async def delete_news(news_id: int, db: Session = Depends(get_db)):
    news = db.query(NewsItem).filter(NewsItem.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    db.delete(news)
    db.commit()
    return {"status": "deleted"}


@app.delete("/api/news")
async def delete_all_news(db: Session = Depends(get_db)):
    db.query(NewsItem).delete()
    db.commit()
    return {"status": "all deleted"}


# ─── Settings ─────────────────────────────────────────────────

@app.get("/api/settings")
async def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}


@app.put("/api/settings/scheduler")
async def update_scheduler_settings(body: SchedulerSettings, db: Session = Depends(get_db)):
    unit = body.interval_unit
    if unit not in ("seconds", "minutes", "hours", "days"):
        raise HTTPException(status_code=400, detail="unit must be seconds/minutes/hours/days")
    if body.interval_value < 1:
        raise HTTPException(status_code=400, detail="interval_value must be >= 1")

    set_setting(db, "auto_fetch",           "true" if body.auto_fetch else "false")
    set_setting(db, "fetch_interval_value", str(body.interval_value))
    set_setting(db, "fetch_interval_unit",  unit)
    db.commit()

    if body.auto_fetch:
        apply_scheduler(body.interval_value, unit)
    else:
        scheduler.remove_all_jobs()

    return {"status": "updated", "auto_fetch": body.auto_fetch,
            "interval_value": body.interval_value, "interval_unit": unit}


@app.put("/api/settings/keywords")
async def update_keyword_settings(body: KeywordSettings, db: Session = Depends(get_db)):
    set_setting(db, "keywords",           body.keywords)
    set_setting(db, "danger_keywords",    body.danger_keywords)
    set_setting(db, "peace_keywords",     body.peace_keywords)
    set_setting(db, "max_news_age_hours", str(body.max_news_age_hours))
    if body.negative_keywords is not None:
        set_setting(db, "negative_keywords", body.negative_keywords)
    if body.classifier_mode is not None:
        if body.classifier_mode not in ("keyword", "ai"):
            raise HTTPException(status_code=400, detail="classifier_mode must be 'keyword' or 'ai'")
        set_setting(db, "classifier_mode", body.classifier_mode)
    db.commit()
    return {"status": "updated"}


@app.put("/api/settings/channels")
async def update_channel_settings(body: ChannelSettings, db: Session = Depends(get_db)):
    """เปิด/ปิด LINE และ Facebook alert channels"""
    set_setting(db, "line_enabled",     "true" if body.line_enabled     else "false")
    set_setting(db, "facebook_enabled", "true" if body.facebook_enabled else "false")
    db.commit()
    return {"status": "updated",
            "line_enabled": body.line_enabled, "facebook_enabled": body.facebook_enabled}


# ─── LINE ─────────────────────────────────────────────────────

@app.post("/api/line/test")
async def test_line():
    msg = "🤖 War Alert Bot v2.2 — ทดสอบ LINE Alert!\n\nระบบทำงานปกติ ✅\nรองรับข่าว 2 ภาษา + Facebook"
    success = await broadcast_line_message(msg)
    return {"success": success}


@app.post("/api/line/send/{news_id}")
async def send_line_for_news(news_id: int, db: Session = Depends(get_db)):
    news = db.query(NewsItem).filter(NewsItem.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    if not news.alert_message:
        raise HTTPException(status_code=400, detail="No alert message")
    success = await broadcast_line_message(news.alert_message)
    if success:
        news.line_sent = True
        db.commit()
    return {"success": success}


# ─── Facebook ─────────────────────────────────────────────────

@app.post("/api/facebook/test")
async def test_facebook():
    msg = "🤖 War Alert Bot v2.2 — ทดสอบการโพสต์ Facebook Page!\n\nระบบเชื่อมต่อสำเร็จ ✅\n\n#WarAlertBot #Test"
    success = await post_to_facebook_page(msg)
    return {"success": success}


@app.post("/api/facebook/send/{news_id}")
async def post_facebook_for_news(news_id: int, db: Session = Depends(get_db)):
    news = db.query(NewsItem).filter(NewsItem.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    if not news.alert_message:
        raise HTTPException(status_code=400, detail="No alert message")
    fb_msg = build_fb_message(news.alert_message)
    success = await post_to_facebook_page(fb_msg, news.url or "")
    if success:
        news.facebook_sent = True
        db.commit()
    return {"success": success}


# ─── Frontend ─────────────────────────────────────────────────

_frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
app.mount("/static", StaticFiles(directory=_frontend_dir), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(_frontend_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
