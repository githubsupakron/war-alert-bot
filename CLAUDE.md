# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**War Alert Bot** — a geopolitical news monitoring system that fetches war-related news, classifies sentiment, translates to Thai, and sends alerts via LINE and Facebook to help users track events affecting gold/stock markets.

## Commands

```bash
# Start development server (creates venv, installs deps, starts on :8000)
./start.sh

# Stop server
./stop.sh

# Run manually
cd backend && python main.py

# Install dependencies manually
pip install -r backend/requirements.txt
```

No test suite is currently configured.

## Architecture

**Stack:** FastAPI + SQLite (SQLAlchemy 2.0) + APScheduler + HTTPX. Static HTML/JS frontend. Deployed on Railway.app.

**Data flow:**
1. `news_fetcher.py` — fetches articles from NewsAPI.org by keyword
2. `analyzer.py` — currently keyword-based classification into `danger` / `peace` / `neutral`; planned hybrid classifier adds weighted keywords, negative rules, confidence, and optional LLM JSON review for ambiguous or danger/peace candidates
3. `translator.py` — translates English headlines to Thai via unofficial Google Translate (no auth required)
4. `line_notifier.py` / `facebook_notifier.py` — sends formatted alerts to LINE Messaging API and Facebook Graph API
5. `models.py` — SQLAlchemy ORM for `news_items` and `settings` tables; tracks what was already sent to avoid duplicates
6. `main.py` — FastAPI app with all API endpoints, lifespan setup (DB init, default settings, scheduler start)

**Frontend:** `frontend/index.html` is a single-file admin dashboard (no build step) served as a static file by FastAPI.

**Scheduler:** APScheduler runs periodic fetch jobs based on the `fetch_interval` setting stored in the database. Controlled by `auto_fetch` setting toggle.

## Key Design Decisions

- **Classifier status:** Runtime code is still keyword matching. The docs now define a planned hybrid classifier using CodeSmart Chat Completions: keyword/filter first, optional LLM only for ambiguous or danger/peace candidates, strict JSON output, and keyword fallback on LLM failure.
- **No hot reload** in production (`reload=False`); restart the server after backend changes.
- **Auto-migration:** On startup, code safely adds missing columns (`title_th`, `facebook_sent`) via raw SQL — does not use Alembic.
- **Thai timezone:** Published times are offset +7 hours from UTC before display.
- **CORS:** Wildcard (`*`) — expected since the frontend is served from the same origin.

## Environment Variables

Copy `env.example` to `.env` in the project root:

```
NEWSAPI_KEY=           # NewsAPI.org key
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=          # Starts with "U"
FB_PAGE_ID=
FB_PAGE_ACCESS_TOKEN=
ADMIN_SECRET=          # Admin panel password
PORT=8000
```

## API Surface

All endpoints are under `/api/`. Key ones:

| Endpoint | Purpose |
|----------|---------|
| `POST /api/news/fetch` | Manual fetch (optional `from_date`/`to_date`) |
| `PUT /api/settings/scheduler` | Set interval + auto/manual mode |
| `PUT /api/settings/keywords` | Update search keywords |
| `PUT /api/settings/channels` | Toggle LINE/Facebook on/off |
| `POST /api/line/test` | Send test LINE message |
| `POST /api/facebook/test` | Send test Facebook post |

## Deployment

- Platform: Railway.app
- Build: `nixpacks.toml` (reads `backend/requirements.txt`)
- Start command: `cd backend && python main.py`
- Restart policy: ON_FAILURE, max 10 retries
