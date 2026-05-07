# War Alert Bot - Business Requirements

## 1. Business Objective

War Alert Bot gives market-aware users a fast operational view of conflict-related news and turns selected events into actionable alert messages. The product focuses on geopolitical risk events that can move gold, equities, USD, and broader risk appetite.

The current implementation is designed for a small team or individual operator who wants to monitor war-related news, classify it quickly, and distribute alerts through LINE and Facebook. The next classifier requirement keeps the low-cost keyword workflow but adds optional LLM review for ambiguous or high-signal items where context matters.

## 2. Business Problem

Geopolitical events can affect markets quickly, but monitoring multiple news sources manually is slow and inconsistent. A small operator needs a lightweight system that can:

- Find relevant conflict and peace news.
- Separate risky escalation from positive de-escalation.
- Convert news into Thai-friendly market alert messages.
- Send alerts through channels already used by the audience.
- Preserve an admin history of what was fetched and sent.

## 3. Business Goals

- Reduce the time from news publication to operator awareness.
- Support Thai-language consumption by translating article titles.
- Lower operating cost by using keyword analysis as the default filter and limiting paid or rate-limited LLM calls to ambiguous or high-signal items.
- Give the admin control over automatic and manual monitoring.
- Support multi-channel publishing through LINE and Facebook.
- Maintain a searchable history of fetched and sent news.

## 4. Target Users and Stakeholders

### Primary Operator

The operator manages the admin dashboard, reviews news items, tunes keywords, and decides whether alerts should be sent.

### Investors and Market Watchers

Recipients use the alerts as early signals for geopolitical risk or relief. They are interested in gold, stocks, USD, and risk-on or risk-off market behavior.

### Social Media Audience

Followers of the Facebook Page receive public alert posts with source links.

### Development Team

The development team maintains the FastAPI backend, static frontend, integrations, deployment settings, and database model.

## 5. Value Proposition

War Alert Bot provides a low-cost market intelligence workflow:

- Automatic news discovery.
- Explainable hybrid classification with keyword evidence, confidence, and LLM reasons when used.
- Thai-first alert output.
- Direct LINE delivery.
- Optional Facebook Page publishing.
- Admin-level control without needing a complex CMS.

## 6. Business Capabilities

### News Monitoring

The business can monitor configured conflict, attack, military, ceasefire, and negotiation topics through NewsAPI.org.

### Alert Categorization

The business can categorize events into danger, peace, or neutral so the operator can quickly decide what matters. Hybrid mode should use keyword/filter rules first, then LLM review only when the first pass is ambiguous or strongly indicates danger or peace.

### Market Framing

The business can attach standard market framing to alerts:

- Danger news: gold may rise, stocks may fall, USD may strengthen.
- Peace news: stocks may recover, gold may soften, Asian markets may improve.

### Channel Distribution

The business can distribute alerts to:

- LINE recipients through Messaging API.
- Facebook Page followers through Graph API.

### Operational Control

The business can switch between manual monitoring and scheduled automatic monitoring, tune keywords, and turn channels on or off.

## 7. Success Metrics

Suggested business success metrics:

- Number of relevant danger or peace articles detected per day.
- Percentage of relevant alerts sent successfully to LINE.
- Percentage of relevant alerts posted successfully to Facebook.
- Average time between article publication and alert delivery.
- Number of duplicate articles prevented by URL deduplication.
- Admin review time per monitoring session.
- Keyword tuning frequency and resulting classification quality.

## 8. Business Rules

- Only danger and peace items produce alert messages.
- Neutral items are stored but not automatically distributed.
- Existing articles should not be duplicated.
- Previously unsent eligible alerts may be retried when channels are enabled.
- LINE is enabled by default.
- Facebook is disabled by default until configured.
- Manual date range search must respect practical NewsAPI free-tier limits.
- The admin can delete news history when needed.

## 9. Operational Requirements

### Admin Operation

The admin should be able to operate the product from a single dashboard without command-line access after deployment.

### Cost Control

The product should keep keyword/filter classification as the baseline. LLM classification should be optional, rate-limited by design, and used only when it can reduce false positives or false negatives enough to justify the cost.

### Deployment

The product should run locally for development and on Railway for hosting.

### Availability

The application should recover from process restarts and restore scheduled fetching when previously enabled.

### Data Retention

The current product keeps news records indefinitely until the admin deletes them. No automated retention policy is implemented yet.

## 10. Risks

### Classification Accuracy

Keyword matching can misclassify context. For example, an article mentioning both attack and ceasefire may be classified based on simple keyword counts.

Hybrid classification adds LLM dependency risk. The system must handle provider timeout, invalid JSON, quota failure, and inconsistent answers by falling back to deterministic keyword/filter results.

### Source Dependency

News discovery depends on NewsAPI availability, quota, and search behavior.

### Integration Dependency

LINE and Facebook delivery depend on valid credentials, API availability, permissions, and policy compliance.

### Security

Credentials are sensitive. Any exposed tokens must be rotated before production usage.

### Compliance and Liability

Market-impact language should be treated as informational, not financial advice.

## 11. Future Business Opportunities

- Add admin authentication.
- Add follower subscriptions and recipient groups.
- Add Telegram, Discord, email, or web push channels.
- Add hybrid AI-assisted classification with negative rules, weighted keywords, confidence scoring, and manual approval workflow.
- Add charts for alert volume and channel performance.
- Add source allowlist or blocklist.
- Add richer Thai summaries beyond title translation.
- Add quality reporting so the team can compare keyword and hybrid classifier performance over time.
