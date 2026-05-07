# War Alert Bot - Requirements

## 1. Purpose

War Alert Bot monitors geopolitical conflict news, classifies each item as danger, peace, or neutral, and helps an admin send market-impact alerts through LINE and Facebook. The current product is aimed at users who care about fast signals that may affect gold, equities, USD, and broader risk sentiment.

## 2. Current Scope

The system provides:

- News collection from NewsAPI.org.
- Keyword-based classification for danger and peace events.
- Thai translation of English news titles.
- Bilingual alert message generation.
- SQLite storage for fetched news and delivery status.
- Admin dashboard for manual fetch, auto fetch, settings, and delivery controls.
- LINE Messaging API push notifications.
- Facebook Page posting through Facebook Graph API.
- Railway-compatible deployment configuration.

## 3. Users

### Admin User

The admin user operates the web dashboard, configures keywords and channels, triggers manual fetches, reviews news, and sends or deletes alert items.

### Alert Recipient

The alert recipient receives LINE alerts about danger or peace news that may affect markets.

### Facebook Audience

The Facebook audience sees selected or automated Page posts containing the alert message and source link.

## 4. Functional Requirements

### FR-1 News Fetching

- The system shall fetch news from NewsAPI.org using configured comma-separated keywords.
- The system shall query up to the first five configured keywords.
- The system shall fetch English-language articles sorted by publish time.
- The system shall support automatic fetch using a configurable lookback window in hours.
- The system shall support manual fetch for a selected date/time range.
- The system shall ignore articles whose title is missing or contains `[Removed]`.

### FR-2 News Deduplication

- The system shall store each news item only once based on article URL.
- If an existing item was not sent to an enabled channel, the system shall retry delivery for that channel during later fetches.

### FR-3 News Classification

- The system shall classify fetched articles into `danger`, `peace`, or `neutral`.
- The current classification method shall use keyword matching in `backend/analyzer.py`.
- Danger classification shall be selected when at least one danger keyword is present and danger score is greater than or equal to peace score.
- Peace classification shall be selected when at least one peace keyword is present and peace score is greater than danger score.
- Neutral classification shall be selected when neither danger nor peace rules match.

### FR-4 Translation

- The system shall translate non-Thai article titles into Thai using the free Google Translate endpoint currently implemented in `backend/translator.py`.
- The system shall preserve the original title when the title is already Thai or translation fails.

### FR-5 Alert Message Generation

- The system shall generate alert messages only for `danger` and `peace` news.
- Danger alerts shall include expected market impact for gold, stocks, and USD.
- Peace alerts shall include expected market impact for gold, stocks, and Asian markets.
- Alert messages shall include Thai title, original English title when available, source URL, and publish time converted to Thailand time.
- Neutral news shall not generate an alert message.

### FR-6 LINE Delivery

- The system shall send LINE push messages through LINE Messaging API.
- The system shall require `LINE_CHANNEL_ACCESS_TOKEN` and `LINE_USER_ID`.
- The admin shall be able to test LINE delivery.
- The admin shall be able to manually send an eligible news alert to LINE.
- The system shall store whether each news item has been sent to LINE.

### FR-7 Facebook Delivery

- The system shall post alerts to a Facebook Page through Graph API v19.0.
- The system shall require `FB_PAGE_ID` and `FB_PAGE_ACCESS_TOKEN`.
- The admin shall be able to test Facebook posting.
- The admin shall be able to manually post an eligible news alert to Facebook.
- Facebook posts shall append configured hashtags through the current `build_fb_message` helper.
- The system shall store whether each news item has been posted to Facebook.

### FR-8 Admin Dashboard

- The system shall serve the admin dashboard at `/`.
- The dashboard shall show total news, danger count, peace count, LINE sent count, Facebook posted count, and last fetch time.
- The dashboard shall support manual fetch with optional date range presets.
- The dashboard shall support toggling LINE and Facebook alert channels.
- The dashboard shall support enabling and disabling auto fetch.
- The dashboard shall support configuring auto fetch interval value and unit.
- The dashboard shall support editing search keywords, danger keywords, peace keywords, and auto-mode lookback hours.
- The dashboard shall list news items and allow filtering by all, danger, peace, neutral, LINE sent, and Facebook posted.
- The dashboard shall support deleting one news item or all news items.

### FR-9 Settings

- The system shall persist settings in SQLite.
- The system shall initialize default settings when missing.
- Settings shall include auto fetch status, interval value, interval unit, keywords, classifier keywords, lookback hours, and channel toggles.

### FR-10 Scheduling

- The system shall use APScheduler to run automatic fetch jobs.
- The system shall restore auto fetch schedule on application startup when `auto_fetch` is enabled.
- The system shall allow interval units of seconds, minutes, hours, and days.
- The system shall reject interval values below 1.

## 5. API Requirements

The backend shall expose these current API routes:

| Method | Path | Requirement |
| --- | --- | --- |
| GET | `/api/status` | Return dashboard status, counts, scheduler state, and channel state. |
| GET | `/api/news` | Return stored news, optionally filtered by category. |
| POST | `/api/news/fetch` | Trigger manual fetch and processing. |
| DELETE | `/api/news/{news_id}` | Delete one news item. |
| DELETE | `/api/news` | Delete all news items. |
| GET | `/api/settings` | Return persisted settings. |
| PUT | `/api/settings/scheduler` | Update auto fetch and interval settings. |
| PUT | `/api/settings/keywords` | Update search and classification settings. |
| PUT | `/api/settings/channels` | Update LINE and Facebook channel toggles. |
| POST | `/api/line/test` | Send a LINE test message. |
| POST | `/api/line/send/{news_id}` | Send one news alert to LINE. |
| POST | `/api/facebook/test` | Post a Facebook test message. |
| POST | `/api/facebook/send/{news_id}` | Post one news alert to Facebook. |
| GET | `/` | Serve admin dashboard. |

## 6. Data Requirements

The system shall store news items with:

- English title.
- Thai title.
- Description.
- Source URL.
- Source name.
- Published timestamp.
- Category.
- Generated alert message.
- LINE sent status.
- Facebook sent status.
- Created timestamp.

The system shall store settings as key-value records.

## 7. Non-Functional Requirements

### Reliability

- External API failures shall not crash the application.
- Missing credentials shall prevent only the affected integration from sending.
- Failed sends shall return `False` and leave delivery status unset.

### Cost

- The classification process shall remain free and shall not depend on paid AI APIs.
- The current system shall use NewsAPI free-tier-compatible queries.

### Maintainability

- Backend concerns shall stay separated across fetcher, analyzer, translator, notifier, model, and API modules.
- Admin UI shall remain a static single-page HTML file unless future complexity justifies a frontend framework.

### Security

- Secrets shall be provided through environment variables.
- Real credentials should not be committed to example files or documentation.
- Existing exposed tokens should be rotated before production use.

### Deployment

- The application shall run locally through `start.sh`.
- The application shall be deployable on Railway using `railway.json` and `nixpacks.toml`.

## 8. Assumptions

- The primary timezone for display is Asia/Bangkok.
- The default backend port is `8000`.
- SQLite is acceptable for the current single-instance deployment.
- Keyword classification accuracy is acceptable for a lightweight hackathon product.

## 9. Out of Scope

- User login and role-based access control.
- Multi-user subscriptions.
- Payment or billing.
- Advanced financial forecasting.
- Guaranteed trading advice.
- Full multilingual article translation beyond title translation.
- AI-based classification.
- Push delivery to channels other than LINE and Facebook.

