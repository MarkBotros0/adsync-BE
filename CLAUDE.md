# Backend — Claude Code Guide

## Project Overview

FastAPI backend (`Social Media Sync API v2.0.0`) for syncing and analyzing social media data across Facebook, Instagram, and TikTok.

Entry point: `main.py`
App package: `app/`

## Documentation Reference

**Always consult the `Docs/` folder before implementing or modifying any platform integration.**

| Platform | Docs Folder | Status |
|---|---|---|
| Facebook | `Docs/facebook/` | Active — routers/services exist |
| Instagram | `Docs/instagram/` | In progress — docs available, integration pending |
| TikTok | *(no docs yet)* | Planned |

### Facebook Docs (`Docs/facebook/`)
- `00_README.md` — overview and index
- `01_graph_api_overview.md` — Graph API fundamentals
- `02_authentication.md` — OAuth flow, access tokens
- `03_pages_api.md` — Pages endpoints
- `04_page_insights_api.md` — Page insights/metrics
- `05_marketing_ads_api.md` — Ads API
- `06_instagram_graph_api.md` — Instagram via Facebook Graph API
- `07_webhooks_errors_rate_limits.md` — Webhooks, error handling, rate limits
- `08_business_manager_api.md` — Business Manager

### Instagram Docs (`Docs/instagram/`)
- `00_README.md` — overview and index
- `01_overview.md` — platform overview
- `02_authentication.md` — OAuth, permissions
- `03_instagram_user_api.md` — User API
- `04_media_api.md` — Media endpoints
- `05_content_publishing_api.md` — Publishing
- `06_insights_api.md` — Insights/analytics
- `07_comments_moderation_api.md` — Comments
- `08_webhooks.md` — Webhooks
- `09_instagram_login_api.md` — Login API

## Project Structure

```
app/
  config.py          # Settings via pydantic (env vars)
  database.py        # SQLAlchemy engine setup
  models/            # ORM models
  repositories/      # Data access layer
  routers/
    facebook/        # auth, ads, pages routers
  services/
    auth.py          # Auth service
    facebook/        # Facebook-specific services
    session_storage.py
  utils/
```

## Key Conventions

- **Router prefix**: platform-namespaced (e.g., `/facebook/...`)
- **Session storage**: configurable — `memory` or `postgresql` (set via `SESSION_STORAGE` env var)
- **Settings**: loaded via `get_settings()` from `app/config.py`
- **New platform integrations** (Instagram, TikTok) should mirror the Facebook structure: `routers/<platform>/` and `services/<platform>/`

## Adding a New Platform

1. Read the relevant `Docs/<platform>/` files first.
2. Create `app/routers/<platform>/` with an `__init__.py`.
3. Create `app/services/<platform>/` with an `__init__.py`.
4. Register routers in `main.py` via `app.include_router(...)`.
5. Add platform config fields to `app/config.py`.
