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

## Naming Conventions

| Thing | Convention | Example |
|---|---|---|
| Files/modules | `snake_case.py` | `brand_auth.py` |
| Classes | `PascalCase` | `BrandRepository` |
| Functions/methods | `snake_case` | `get_brand_by_email` |
| Variables | `snake_case` | `brand_token` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_OTP_ATTEMPTS` |
| Pydantic schemas | `PascalCase` + suffix | `BrandRegisterRequest`, `BrandResponse` |
| ORM models | `PascalCase` + `Model` suffix | `BrandModel` |

---

## Key Conventions

### Routers
- **Prefix**: platform-namespaced — `/facebook/...`, `/brands/...`, `/subscriptions/...`
- Import the module, then access `.router`: `from app.routers.brands import auth as brands_auth` → `app.include_router(brands_auth.router)`
- For packages with a `router.py` sub-module: `from app.routers.subscriptions import router as sub_router` → `app.include_router(sub_router.router)`
- Always set `tags=["Domain Name"]` on routers for grouped Swagger docs.
- Always set explicit `status_code` on endpoints (`201` for create, `200` for reads, etc.).
- Use `response_model=` to declare the shape of the response — this drives OpenAPI docs and strips extra fields.

```python
@router.post("/register", response_model=BrandResponse, status_code=201, tags=["Brand Auth"])
async def register_brand(payload: BrandRegisterRequest, db: Session = Depends(get_db)):
    ...
```

### Pydantic Schemas (Request / Response)
- Keep **ORM models** (`app/models/`) separate from **Pydantic schemas** (request/response validation).
- ORM models define the database table; Pydantic schemas define what comes in/out of the API.
- Schema naming: `<Resource>Request` for inputs, `<Resource>Response` for outputs.
- Use `model_config = ConfigDict(from_attributes=True)` (Pydantic v2) to allow `model_validate(orm_obj)`.
- Never use `to_dict()` on ORM objects for API responses — use `response_model` + `model_validate`.

```python
# schemas/brand.py
from pydantic import BaseModel, EmailStr, ConfigDict

class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    is_active: bool
    # NOTE: never include hashed_password or session_key here
```

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
- Validate token + session_key on every protected request via the shared `require_brand` dependency from `app.dependencies`.
- **Never copy-paste auth logic** — always import `require_brand` and `optional_brand_id` from `app/dependencies.py`.

### Shared Dependencies (`app/dependencies.py`)
- `require_brand` — validates JWT + session_key, eagerly loads `brand.subscription`, returns the brand ORM object.
- `optional_brand_id` — returns brand_id from JWT if present, `None` otherwise. Never raises.
- Import these in every router that needs brand auth instead of writing a local version:

```python
from app.dependencies import require_brand, optional_brand_id

@router.get("/session")
async def get_session(brand=Depends(require_brand)):
    ...

@router.get("/connect")
async def connect(brand_id: int | None = Depends(optional_brand_id)):
    ...
```

### Type Hints
- **All function signatures must have type hints** — parameters and return types.
- Use `T | None` (Python 3.10+ union syntax) for nullable values — never `Optional[T]`.
- Use `list[T]`, `dict[K, V]` (lowercase, Python 3.9+) — never `List`, `Dict`, `Optional` from `typing`.
- Never use bare `dict` or `list` without type parameters for function signatures.
- Remove unused `typing` imports when switching to built-in syntax.

### Code Readability & No Duplication
- **Divide large files** into focused modules — routers over ~200 lines should be split by resource (accounts, media, insights).
- **Extract shared helpers** into separate modules — never copy-paste functions across router files.
- Each router file should import shared session/auth helpers rather than defining its own.
- Session-lookup helpers (e.g., `get_instagram_session`) live in a `session.py` module beside the routers that use them.
- Use module-level constants for repeated literal sets (e.g., `_VALID_PERIODS = {"day", "week", "days_28", "month"}`).

```python
# Good — shared, importable
# routers/instagram/session.py
def get_instagram_session(session_id: str) -> dict[str, str]: ...

# routers/instagram/content.py
from app.routers.instagram.session import get_instagram_session

# Bad — copy-pasted
# Every router file defines its own _get_instagram_session
```

```python
# Good
def get_brand_by_email(email: str) -> Optional[BrandModel]:
    ...

# Bad — no return type, bare dict
def get_brand(email):
    return {"id": 1}
```

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
- **Every model must have `created_at`, `updated_at`, and `deleted_at`** with Python-side defaults. `updated_at` uses `onupdate=datetime.utcnow`. `deleted_at` defaults to `None` (nullable).
- **All entities support soft deletion** — never issue `db.delete(obj)`. Set `deleted_at = datetime.utcnow()` instead. Queries must filter out soft-deleted rows with `.filter(Model.deleted_at.is_(None))`.
- `BaseRepository` must include a `soft_delete(id)` method and all `get`/`list` queries must exclude soft-deleted rows by default.

```python
# Standard timestamps on every model
from datetime import datetime
from sqlalchemy import Column, DateTime

created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
deleted_at = Column(DateTime, nullable=True, default=None)  # None = active; set to soft-delete
```

- `session_key` on `BrandModel` is the server-side nonce for JWT invalidation — never expose it in API responses.
- `to_dict()` must only return fields safe to send to the client. Never include `hashed_password`, `session_key`, or verification codes.

---

## Service Layer

- **Routers** handle HTTP: parse request, call service, return response. No business logic.
- **Services** handle business logic: validation, orchestration, calling external APIs, calling repositories.
- **Repositories** handle DB access only: no business logic, no HTTP concerns.

```
Router → Service → Repository → DB
Router → Service → External API (Facebook, Instagram, TikTok)
```

- Keep services free of FastAPI types (`Request`, `HTTPException`). A service function should be testable without an HTTP context.
- Raise plain Python exceptions in services; let the router catch and convert to `HTTPException`.

```python
# services/brand.py — no FastAPI imports
def get_brand_or_raise(brand_id: int, repo: BrandRepository) -> BrandModel:
    brand = repo.get(brand_id)
    if not brand:
        raise ValueError(f"Brand {brand_id} not found")
    return brand

# routers/brands/auth.py — converts to HTTP error
@router.get("/me")
def get_me(brand: BrandModel = Depends(_require_brand)):
    try:
        return BrandResponse.model_validate(brand)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
```

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
- Always use the correct HTTP status codes:

| Scenario | Status code |
|---|---|
| Resource not found | `404` |
| Already exists (email taken) | `409` |
| Bad input / validation | `422` (Pydantic handles automatically) |
| Unauthorized (no/bad token) | `401` |
| Forbidden (valid token, wrong permission) | `403` |
| Created successfully | `201` |

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
- **Secrets in logs**: never log request bodies, tokens, or anything from `[parameters: ...]` SQLAlchemy error output.

---

## Logging

- Use Python's `logging` module — never `print()`.
- Logger per module: `logger = logging.getLogger(__name__)` at the top of each file.
- Log at the right level:
  - `DEBUG` — internal state useful during development
  - `INFO` — normal operation milestones (server ready, migration complete)
  - `WARNING` — unexpected but recoverable (skipped optional step)
  - `ERROR` — something failed that needs attention
  - `EXCEPTION` (via `logger.exception`) — unhandled exceptions (includes stack trace)
- Never log sensitive data: passwords, tokens, OTPs, full SQL `[parameters: ...]`.

```python
import logging
logger = logging.getLogger(__name__)

# Good
logger.info("Brand %d logged in", brand.id)
logger.warning("Email send skipped: %s", exc)

# Bad
logger.info(f"Password hash: {hashed_password}")
print("Error:", exc)
```

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
| Endpoint not in Swagger docs | Router not registered in `main.py` | Add `app.include_router(...)` |
| Response includes unexpected fields | No `response_model` set on endpoint | Add `response_model=YourSchema` to the decorator |
