# Backend — Claude Code Guide

## Project Overview

FastAPI backend (`Social Media Sync API v2.0.0`) for syncing and analyzing social media data across Facebook, Instagram, and TikTok.

Entry point: `main.py`
App package: `app/`

---

## Documentation Reference

**Always consult the `Docs/` folder before implementing or modifying any platform integration.**

| Platform | Docs Folder | Status |
|---|---|---|
| Facebook | `Docs/facebook/` | Active — routers/services exist |
| Instagram | `Docs/instagram/` | In progress — docs available, integration pending |
| TikTok | `Docs/tiktok/` | Active — docs complete |

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

### TikTok Docs (`Docs/tiktok/`)
- `00_README.md` — index + quick-reference cheat sheet (endpoints, tokens, scopes, rate limits, error codes)
- `01_overview.md` — API products, base URLs, versioning, request/response format, pagination, rate limits, sandbox
- `02_authentication.md` — OAuth 2.0 flow, PKCE, token types (access 24h / refresh 365d / client 2h), all scopes, token exchange/refresh/revoke, client credentials
- `03_user_api.md` — User Info endpoint, all 14 fields with scopes, open_id vs union_id
- `04_video_api.md` — Video List and Video Query endpoints, all video fields, pagination, privacy levels
- `05_content_posting_api.md` — Direct Post vs Inbox/Draft, PULL vs PUSH, chunk upload specs, video/photo specs, creator info, publish status polling, error codes
- `06_display_api.md` — Display API overview, available fields, embedding, Display vs Login Kit comparison
- `07_ads_api.md` — Account hierarchy, campaign/ad group/ad fields, all objective types, reporting metrics (delivery/video/engagement/conversion), async report jobs, audiences
- `08_webhooks_and_errors.md` — Webhook setup/retry, all error codes, rate limits, retry strategy, sandbox vs production

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

---

## Project Structure

```
app/
  config.py              # Settings via pydantic-settings (env vars)
  database.py            # SQLAlchemy engine + session factory
  models/                # ORM models (BrandModel, SubscriptionModel, …)
  repositories/          # Data-access layer — one class per model
    base.py              # BaseRepository[T] with CRUD helpers
  routers/
    brands/auth.py       # Brand registration, login, JWT, session mgmt
    facebook/            # auth, ads, pages routers
    subscriptions/router.py
  services/
    jwt_auth.py          # hash_password, verify_password, create/decode token
    email.py             # Gmail SMTP OTP sender
    facebook/
  utils/
alembic/
  versions/              # Migration scripts (run via alembic upgrade head)
main.py                  # App factory, middleware, startup hook
requirements.txt
```

---

## Key Conventions

### Routers
- **Prefix**: platform-namespaced — `/facebook/...`, `/brands/...`, `/subscriptions/...`
- Import the module, then access `.router`: `from app.routers.brands import auth as brands_auth` → `app.include_router(brands_auth.router)`
- For packages with a `router.py` sub-module: `from app.routers.subscriptions import router as sub_router` → `app.include_router(sub_router.router)`

### Repositories
- Every endpoint creates its own DB session via `_get_*_repo()` helpers — **do not share sessions across helpers**.
- Always close sessions in a `finally` block; never leak them.
- `BaseRepository.create()` calls `db.commit()` + `db.refresh(obj)` — the returned object is attached and fully populated.
- Lazy-loaded relationships (`lazy="select"`) are safe to access **before** `db.close()`. Access `.relationship` inside the `try` block, not after `finally`.

### Settings
- Loaded via `get_settings()` from `app/config.py` (cached with `@lru_cache`).
- Required fields with no default (`secret_key`, `database_url`, `session_storage`) will raise at import time if missing from `.env`. Always keep `.env` complete.
- `jwt_secret` falls back to `secret_key` if unset.

### Authentication (Brand JWT)
- Every JWT embeds `sub` (brand id), `session_key`, `exp`, `iat`, `type`.
- `session_key` is a UUID stored on the brand row. Rotating it (`rotate_session_key`) immediately invalidates **all** existing tokens — force sign-out.
- Validate token + session_key on every protected request via `_require_brand` dependency.

---

## Dependency Management

### Critical: bcrypt + passlib compatibility
- **Use `bcrypt==4.0.1`** (pinned in `requirements.txt`). Do **not** upgrade bcrypt past 4.x.
- `passlib 1.7.4` (last stable release) internally tests passwords >72 bytes during initialisation. `bcrypt 4.1+` rejects those with a hard `ValueError` that escapes middleware and produces a raw non-JSON 500.
- If you see `ValueError: password cannot be longer than 72 bytes` in logs, the bcrypt version has drifted — re-pin: `pip install "bcrypt==4.0.1"`.

### Other pinned versions
- `SQLAlchemy==2.0.x` — use the ORM query API (`db.query(Model)`), not the 2.0 `select()` style, since repositories use the legacy API.
- `alembic==1.13.x` — migrations are synchronous; always run them from the startup hook or CLI.
- `python-jose[cryptography]==3.3.0` — JWT encoding/decoding.

---

## Database & Migrations

### Startup hook (`main.py → on_startup`)
1. `Base.metadata.create_all(bind=engine)` — safety net that creates any missing tables on every start. Idempotent and harmless.
2. `alembic upgrade head` — applies pending migrations. Wrapped in `try/except` so a migration warning (e.g. column already exists) never crashes the server.
3. `SubscriptionRepository.seed_defaults()` — upserts the default subscription plans.

### Writing migrations
- **Always add `server_default`** when adding a `NOT NULL` column to an existing table, otherwise the migration fails when rows already exist:
  ```python
  op.add_column('brands', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
  ```
- **Make migrations idempotent** — check column/table existence before adding:
  ```python
  inspector = sa.inspect(op.get_bind())
  existing = {c['name'] for c in inspector.get_columns('brands')}
  if 'new_col' not in existing:
      op.add_column('brands', sa.Column('new_col', sa.String(), nullable=True))
  ```
- Never leave the initial migration body empty (`pass`). It should either create the full schema or be a genuine no-op with a comment explaining why.
- After adding a new model, generate a migration: `alembic revision --autogenerate -m "describe change"`, then review the output before committing.

### Model conventions
- Every model has `created_at` and `updated_at` with Python-side defaults. `updated_at` uses `onupdate=datetime.utcnow`.
- `session_key` on `BrandModel` is the server-side nonce for JWT invalidation — never expose it in API responses.
- `to_dict()` must only return fields safe to send to the client. Never include `hashed_password`, `session_key`, or verification codes.

---

## Error Handling

### Global exception handler
- Registered in `main.py` for `Exception` — returns `{"detail": "...", "type": "..."}` as JSON with status 500.
- **Does not fire** when an exception propagates out of `BaseHTTPMiddleware` (e.g. the logging middleware). Exceptions inside `call_next` bypass FastAPI's handlers and cause uvicorn to return a raw text 500.
- Rule: middleware must **never** let exceptions from `call_next` escape unhandled.

### Endpoint error handling
- Use `HTTPException` for expected client errors (400, 401, 403, 404, 409).
- Use `try/finally` (not `try/except`) in endpoints — let exceptions bubble to the global handler; always close DB sessions in `finally`.
- Never swallow exceptions silently (empty `except: pass`) unless it's a non-critical optional operation (e.g. email send).

### Startup errors
- Errors in `@app.on_event("startup")` that are not caught will cause Starlette to return raw 500 responses for **all** subsequent requests, bypassing FastAPI's exception handlers. Always wrap risky startup operations in `try/except`.

---

## Security

- **Passwords**: hashed with bcrypt via `passlib`. Never store or log plaintext passwords. Never log the `[parameters: ...]` section of SQLAlchemy errors (they can contain the hashed password).
- **JWT secret**: must be a cryptographically random string (≥32 bytes). Falls back to `SECRET_KEY`. Never commit it to source control.
- **Email verification codes**: 6-digit OTP, 15-minute expiry. Stored on the brand row. Cleared after verification.
- **Session invalidation**: rotate `session_key` to force sign-out of all devices at once.
- **CORS**: currently `allow_origins=["*"]`. Tighten to specific origins before production (`FRONTEND_URL` env var pattern).
- **SQL injection**: not possible via SQLAlchemy ORM — never use raw string interpolation in queries.

---

## Async & Email

- The email service (`app/services/email.py`) uses synchronous `smtplib` wrapped in `asyncio.get_event_loop().run_in_executor()`.
- Use `asyncio.get_running_loop()` (not `get_event_loop()`) inside coroutines — the latter is deprecated in Python 3.10+ when a loop is already running.
- If `GMAIL_USER` or `GMAIL_APP_PASSWORD` are not set, email sending is silently skipped (returns `False`). Registration still succeeds — the user just won't receive a verification email.
- SMTP failures are caught and logged; they must never propagate and abort a request.

---

## Adding a New Platform

1. Read the relevant `Docs/<platform>/` files first.
2. Create `app/routers/<platform>/` with an `__init__.py`.
3. Create `app/services/<platform>/` with an `__init__.py`.
4. Register routers in `main.py` via `app.include_router(...)`.
5. Add platform config fields to `app/config.py`.
6. Mirror the Facebook structure: router → service → repository if DB state is needed.

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt   # bcrypt==4.0.1 is pinned — do not upgrade

# Start server
python main.py
# or
uvicorn main:app --reload --port 8000
```

The startup hook runs migrations and seeds subscriptions automatically on every start.

API docs available at `http://localhost:8000/docs`.

---

## Common Debugging

| Symptom | Likely cause | Fix |
|---|---|---|
| `ValueError: password cannot be longer than 72 bytes` | bcrypt > 4.0.1 installed | `pip install "bcrypt==4.0.1"` |
| Frontend gets raw 500 with no JSON body | Exception escaped middleware | Check `log_requests` middleware; exception bypassed FastAPI handlers |
| `alembic upgrade head` fails on startup | Adding NOT NULL column without `server_default`, or column already exists | Make migration idempotent; add `server_default` |
| Registration 409 "Email already registered" | Brand with that email exists in DB | Use a different email or delete the test row |
| JWT 401 "Session invalidated" | `session_key` was rotated (force sign-out) | Re-login to get a fresh token |
| Subscriptions endpoint works but brands endpoint 500s | `brands` table missing a column | Run `alembic upgrade head` or restart server (startup `create_all` will fix it) |
