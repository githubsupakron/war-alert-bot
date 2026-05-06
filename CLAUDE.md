# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# First run (creates venv and installs deps)
./start.sh

# App runs at http://localhost:8000
```

Manual startup:
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cd backend && python3 main.py
```

## Environment Setup

Copy `env.example` to `.env` in the project root. Required variables:
- `NEWSAPI_KEY` — from newsapi.org (free tier)
- `LINE_CHANNEL_ACCESS_TOKEN` — from LINE Developers console
- `LINE_USER_ID` — target LINE user ID for push messages
- `PORT` — defaults to 8000

## Architecture

**Backend** (`backend/`) — FastAPI app (`main.py`) running on uvicorn with APScheduler for periodic news fetching. SQLite (`war_alert.db`) via SQLAlchemy.

**Frontend** (`frontend/`) — Single-page admin dashboard served as static files by FastAPI. Vanilla JS (`app.js`) + Tailwind CSS (CDN) + custom CSS (`style.css`). No build step.

### Data Flow

1. `news_fetcher.py` — fetches from NewsAPI.org using comma-separated keyword list (max 5 sent as OR query)
2. `analyzer.py` — pure keyword matching (no AI) categorizes articles as `danger`, `peace`, or `neutral`
3. `translator.py` — translates English titles to Thai via unofficial Google Translate endpoint (free, may break)
4. `line_notifier.py` — pushes formatted alerts to LINE via LINE Messaging API (push to single user or broadcast)
5. `main.py` — deduplicates by URL before storing; only sends LINE alerts for `danger` and `peace` categories

### Key Models (`models.py`)

- `NewsItem` — stores fetched articles with category, Thai title, alert message, and `line_sent` flag
- `Setting` — key/value store for runtime config (auto-fetch toggle, interval, keywords, etc.)

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/status` | Scheduler state + aggregate counts |
| GET | `/api/news` | List news (filterable by category) |
| POST | `/api/news/fetch` | Manual fetch with optional datetime range |
| DELETE | `/api/news/{id}` | Delete single item |
| DELETE | `/api/news` | Delete all |
| GET/PUT | `/api/settings` | Read/write all settings |
| PUT | `/api/settings/scheduler` | Toggle auto-fetch + interval |
| PUT | `/api/settings/keywords` | Update keyword lists |
| POST | `/api/line/test` | Send test LINE message |
| POST | `/api/line/send/{id}` | Manually send LINE for a specific article |

## Deployment

Configured for Railway via `railway.json` and `nixpacks.toml`. Build runs `pip install -r backend/requirements.txt`; start command is `cd backend && python main.py`. Set all env vars in Railway dashboard.
