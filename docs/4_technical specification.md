# War Alert Bot - Technical Specification

## 1. Technology Stack

| Layer | Technology |
| --- | --- |
| Backend | Python, FastAPI |
| ASGI server | Uvicorn |
| ORM | SQLAlchemy |
| Database | SQLite |
| Scheduler | APScheduler `AsyncIOScheduler` |
| HTTP client | HTTPX |
| Configuration | `python-dotenv`, environment variables |
| Frontend | Static HTML, CSS, vanilla JavaScript |
| Deployment | Railway, Nixpacks |

Python dependencies are declared in `backend/requirements.txt`.

## 2. Source Layout

```text
war-alert-bot/
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── news_fetcher.py
│   ├── analyzer.py
│   ├── translator.py
│   ├── line_notifier.py
│   ├── facebook_notifier.py
│   ├── requirements.txt
│   └── war_alert.db
├── frontend/
│   └── index.html
├── env.example
├── start.sh
├── stop.sh
├── railway.json
├── nixpacks.toml
├── README.md
└── DEVELOPMENT_STEPS.md
```

## 3. Environment Variables

| Variable | Required | Used By | Purpose |
| --- | --- | --- | --- |
| `NEWSAPI_KEY` | Yes for fetching | `news_fetcher.py` | NewsAPI.org API key. |
| `LINE_CHANNEL_ACCESS_TOKEN` | Yes for LINE | `line_notifier.py` | LINE Messaging API bearer token. |
| `LINE_USER_ID` | Yes for LINE push | `line_notifier.py` | Target recipient user ID. |
| `FB_PAGE_ID` | Yes for Facebook | `facebook_notifier.py` | Facebook Page ID. |
| `FB_PAGE_ACCESS_TOKEN` | Yes for Facebook | `facebook_notifier.py` | Page access token. |
| `ADMIN_SECRET` | Present but not enforced | Environment | Intended admin secret. |
| `PORT` | Optional | `main.py`, scripts | Server port, default `8000`. |

Security note: example files should contain placeholders only. Tokens that have been shared or committed should be rotated.

## 4. Application Startup

Entry point:

```bash
cd backend && python main.py
```

Runtime behavior:

1. `load_dotenv()` loads environment variables.
2. FastAPI lifespan calls `init_db()`.
3. SQLAlchemy creates tables if missing.
4. Lightweight migrations attempt to add `title_th` and `facebook_sent`.
5. Default settings are inserted when missing.
6. APScheduler starts.
7. If `auto_fetch` is `true`, the scheduler restores the configured interval job.
8. FastAPI serves the API and `frontend/index.html`.

## 5. Database Specification

### 5.1 Connection

Current database URL:

```python
sqlite:///./war_alert.db
```

Because the production start command runs from `backend`, the SQLite file resolves to `backend/war_alert.db`.

### 5.2 Tables

#### `news_items`

| Column | Type | Constraints / Default |
| --- | --- | --- |
| `id` | Integer | Primary key, indexed |
| `title` | Text | Not null |
| `title_th` | Text | Nullable |
| `description` | Text | Nullable |
| `url` | String(500) | Nullable |
| `source` | String(200) | Nullable |
| `published_at` | DateTime | Nullable |
| `category` | String(20) | Default `neutral` |
| `alert_message` | Text | Nullable |
| `line_sent` | Boolean | Default `False` |
| `facebook_sent` | Boolean | Default `False` |
| `created_at` | DateTime | Default `datetime.utcnow` |

#### `settings`

| Column | Type | Constraints |
| --- | --- | --- |
| `key` | String(100) | Primary key |
| `value` | Text | Nullable |

## 6. Core Processing Specification

### 6.1 `process_and_notify`

Location: `backend/main.py`

Inputs:

- SQLAlchemy session.
- Optional `from_dt`.
- Optional `to_dt`.

Algorithm:

1. Set global `last_fetch_time` to current UTC time.
2. Read `keywords`, `max_news_age_hours`, `line_enabled`, and `facebook_enabled` from settings.
3. Call `fetch_news_from_api`.
4. For each article:
   - Check duplicate by URL.
   - For duplicates, retry enabled unsent channels if the item is danger or peace.
   - For new articles, classify with `analyze_news`.
   - Parse publish timestamp.
   - Convert publish timestamp to Thailand time for alert display.
   - Translate title to Thai.
   - Build alert message.
   - Insert `NewsItem`.
   - Send LINE if category is eligible and LINE is enabled.
   - Post Facebook if category is eligible and Facebook is enabled.
5. Return counters: `fetched`, `new`, `sent_line`, `sent_fb`, and backward-compatible `sent`.

### 6.2 News Fetching

Location: `backend/news_fetcher.py`

Function:

```python
fetch_news_from_api(keywords, from_dt=None, to_dt=None, hours_back=6)
```

Request:

- URL: `https://newsapi.org/v2/everything`
- Method: `GET`
- Timeout: 30 seconds.
- `trust_env=False`.

Parameters:

| Parameter | Value |
| --- | --- |
| `q` | Up to five keywords joined with `OR` and quoted. |
| `from` | Manual start datetime or UTC now minus `hours_back`. |
| `to` | Manual end datetime or UTC now. |
| `language` | `en` |
| `sortBy` | `publishedAt` |
| `pageSize` | `100` |
| `apiKey` | `NEWSAPI_KEY` |

Output article dict:

```json
{
  "title": "string",
  "description": "string",
  "url": "string",
  "source": "string",
  "published_at": "string"
}
```

### 6.3 Classification

Location: `backend/analyzer.py`

Function:

```python
analyze_news(title: str, description: str) -> dict
```

Rules:

- Lowercase concatenated title and description.
- Count keyword presence from `DANGER_KEYWORDS`.
- Count keyword presence from `PEACE_KEYWORDS`.
- Return `danger` when `danger_score > 0 and danger_score >= peace_score`.
- Return `peace` when `peace_score > 0 and peace_score > danger_score`.
- Otherwise return `neutral`.

Output:

```json
{
  "category": "danger | peace | neutral",
  "market_impact": "string"
}
```

Important implementation note: settings endpoint stores `danger_keywords` and `peace_keywords`, but the analyzer currently uses module-level arrays. Runtime keyword customization for classification is not fully implemented.

### 6.4 Alert Message Generation

Location: `backend/analyzer.py`

Function:

```python
build_alert_message(title_en, title_th, url, analysis, published_at)
```

Returns:

- LINE-style danger alert for `danger`.
- LINE-style peace alert for `peace`.
- `None` for `neutral`.

Facebook messages are generated by appending hashtags in `backend/main.py`:

```python
build_fb_message(alert_msg)
```

### 6.5 Translation

Location: `backend/translator.py`

Functions:

- `is_thai(text)`.
- `translate_to_thai(text)`.

Behavior:

- If text is empty or already Thai, return original.
- Otherwise call Google Translate endpoint.
- On failure, log the exception and return original.

### 6.6 LINE Notification

Location: `backend/line_notifier.py`

Function:

```python
send_line_message(message: str, user_id: Optional[str] = None) -> bool
```

Endpoint:

```text
POST https://api.line.me/v2/bot/message/push
```

Payload:

```json
{
  "to": "LINE_USER_ID",
  "messages": [
    {"type": "text", "text": "message"}
  ]
}
```

Success condition: HTTP `200`.

### 6.7 Facebook Posting

Location: `backend/facebook_notifier.py`

Function:

```python
post_to_facebook_page(message: str, link: str = "") -> bool
```

Endpoint:

```text
POST https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed
```

Payload fields:

- `message`
- `access_token`
- optional `link`

Success condition: HTTP `200`.

## 7. API Specification

### 7.1 `GET /api/status`

Returns:

```json
{
  "auto_fetch": true,
  "interval_value": 30,
  "interval_unit": "minutes",
  "last_fetch": "2026-05-07T00:00:00",
  "total_news": 0,
  "sent_news": 0,
  "fb_sent": 0,
  "danger_count": 0,
  "peace_count": 0,
  "scheduler_running": true,
  "scheduler_jobs": 1,
  "line_enabled": true,
  "facebook_enabled": false
}
```

### 7.2 `GET /api/news`

Query parameters:

| Name | Type | Default | Notes |
| --- | --- | --- | --- |
| `limit` | int | `100` | Maximum rows returned. |
| `category` | string | `None` | `all`, `danger`, `peace`, `neutral`, `sent`, or `fb_sent`. |

Returns a list of news item objects.

### 7.3 `POST /api/news/fetch`

Request body:

```json
{
  "from_datetime": "2026-05-07T00:00:00",
  "to_datetime": "2026-05-07T23:59:59"
}
```

Both fields are optional. When omitted, auto lookback settings are used.

Response:

```json
{
  "status": "success",
  "fetched": 0,
  "new": 0,
  "sent_line": 0,
  "sent_fb": 0,
  "sent": 0
}
```

### 7.4 `DELETE /api/news/{news_id}`

Deletes one news item. Returns `404` when not found.

### 7.5 `DELETE /api/news`

Deletes all news items.

### 7.6 `GET /api/settings`

Returns all settings as a JSON object.

### 7.7 `PUT /api/settings/scheduler`

Request body:

```json
{
  "auto_fetch": true,
  "interval_value": 30,
  "interval_unit": "minutes"
}
```

Validation:

- `interval_unit` must be one of `seconds`, `minutes`, `hours`, `days`.
- `interval_value` must be at least 1.

### 7.8 `PUT /api/settings/keywords`

Request body:

```json
{
  "keywords": "Iran attack,Israel strike,war",
  "danger_keywords": "attack,strike,missile",
  "peace_keywords": "ceasefire,peace talks",
  "max_news_age_hours": 6
}
```

### 7.9 `PUT /api/settings/channels`

Request body:

```json
{
  "line_enabled": true,
  "facebook_enabled": false
}
```

### 7.10 Delivery Routes

| Method | Path | Success Response |
| --- | --- | --- |
| POST | `/api/line/test` | `{"success": true}` |
| POST | `/api/line/send/{news_id}` | `{"success": true}` |
| POST | `/api/facebook/test` | `{"success": true}` |
| POST | `/api/facebook/send/{news_id}` | `{"success": true}` |

Manual delivery routes return `404` when the news item does not exist and `400` when no alert message exists.

## 8. Frontend Specification

Location: `frontend/index.html`

### 8.1 Runtime

- Served by FastAPI route `/`.
- Uses relative API root `const API = ''`.
- Polls status and news every 30 seconds.

### 8.2 UI Sections

- Header badges: online, auto, LINE, Facebook, last fetch.
- Stats cards: total, danger, peace, LINE sent, Facebook posted, last update.
- Manual search panel.
- Alert channel panel.
- Auto fetch panel.
- Keyword panel.
- News feed panel.

### 8.3 Client Functions

| Function | Purpose |
| --- | --- |
| `loadStatus()` | Fetch and render status counters and toggles. |
| `loadSettings()` | Populate keyword settings form. |
| `saveChannels()` | Persist channel toggles. |
| `saveScheduler()` | Persist scheduler settings. |
| `saveKeywords()` | Persist keyword settings. |
| `manualFetch()` | Trigger backend fetch. |
| `testLine()` | Trigger LINE test. |
| `testFacebook()` | Trigger Facebook test. |
| `loadNews()` | Fetch news list. |
| `renderNews()` | Render current news tab. |
| `sendLine(id)` | Send one alert to LINE. |
| `postFacebook(id)` | Post one alert to Facebook. |
| `delNews(id)` | Delete one item. |
| `deleteAll()` | Delete all items. |

## 9. Error Handling

- Missing API credentials return `False` from notifier/fetcher functions.
- External HTTP exceptions are caught and logged.
- NewsAPI non-`ok` responses return an empty article list.
- Translation failure returns original text.
- API validation errors use FastAPI `HTTPException`.
- Frontend displays toast messages for success and failure states.

## 10. Local Development

Start:

```bash
./start.sh
```

Stop:

```bash
./stop.sh
```

Manual backend command:

```bash
cd backend
python main.py
```

Expected local URL:

```text
http://localhost:8000
```

## 11. Deployment

Railway configuration:

- `railway.json` selects Nixpacks and starts `cd backend && python main.py`.
- `nixpacks.toml` installs `backend/requirements.txt`.

Set production environment variables in Railway project settings.

## 12. Testing Recommendations

No automated test suite is currently present. Recommended tests:

- Unit tests for `analyze_news` scoring rules.
- Unit tests for `build_alert_message` output conditions.
- Unit tests for `parse_published_at`.
- API tests for scheduler validation and CRUD routes.
- Mocked integration tests for NewsAPI, LINE, Facebook, and translation failures.
- Frontend smoke test for dashboard load and main actions.

## 13. Known Technical Debt

- `ADMIN_SECRET` is not used for authentication.
- Persisted danger and peace keyword settings are not applied by `analyze_news`.
- Example environment values should be replaced with placeholders.
- SQLite is not ideal for multi-instance production deployments.
- In-process scheduler can duplicate jobs if the app runs with multiple workers or replicas.
- No structured logging or monitoring.
- No automated migration framework.

