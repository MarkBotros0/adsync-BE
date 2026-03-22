# TikTok API Documentation — Index

## Files

| File | Description | Key Topics |
|------|-------------|------------|
| [01_overview.md](01_overview.md) | API products, base URLs, versioning, environments | Products, base URLs, request/response format, pagination, rate limits, sandbox |
| [02_authentication.md](02_authentication.md) | OAuth 2.0, tokens, scopes | OAuth flow, PKCE, token types, token exchange/refresh/revoke, client credentials, all scopes |
| [03_user_api.md](03_user_api.md) | User Info endpoint | All user fields, required scopes, open_id vs union_id |
| [04_video_api.md](04_video_api.md) | Video List and Video Query endpoints | All video fields, pagination, privacy levels, video status values |
| [05_content_posting_api.md](05_content_posting_api.md) | Post videos and photos to TikTok | Direct Post vs Inbox/Draft, PULL vs PUSH, chunk upload, video/photo specs, publish status |
| [06_display_api.md](06_display_api.md) | Read-only access to creator content | Display API overview, available fields, embed videos, Display vs Login Kit |
| [07_ads_api.md](07_ads_api.md) | TikTok Ads / Marketing API | Account hierarchy, campaign/ad group/ad fields, objective types, reporting metrics, audiences |
| [08_webhooks_and_errors.md](08_webhooks_and_errors.md) | Webhooks, error codes, rate limits | Webhook setup/retry, all error codes, rate limits, retry strategy, sandbox vs production |

---

## Quick Reference

### Base URLs

| Purpose | URL |
|---------|-----|
| All v2 API calls | `https://open.tiktokapis.com/v2/` |
| OAuth user authorization | `https://www.tiktok.com/v2/auth/authorize/` |
| Token management (exchange / refresh / client creds) | `https://open.tiktokapis.com/v2/oauth/token/` |
| Token revocation | `https://open.tiktokapis.com/v2/oauth/revoke/` |
| Ads / Marketing API | `https://business-api.tiktok.com/open_api/v1.3/` |

---

### Common Endpoints

| Method | Endpoint | Scope | Description |
|--------|----------|-------|-------------|
| GET | `https://open.tiktokapis.com/v2/user/info/` | user.info.basic | Get user profile info |
| POST | `https://open.tiktokapis.com/v2/video/list/` | video.list | List user's videos (paginated) |
| POST | `https://open.tiktokapis.com/v2/video/query/` | video.list | Fetch specific videos by ID |
| POST | `https://open.tiktokapis.com/v2/oauth/token/` | — | Exchange code for tokens / refresh token / client credentials |
| POST | `https://open.tiktokapis.com/v2/oauth/revoke/` | — | Revoke access token |
| POST | `https://open.tiktokapis.com/v2/post/publish/creator_info/query/` | video.publish | Get creator capabilities |
| POST | `https://open.tiktokapis.com/v2/post/publish/video/init/` | video.publish | Initialize direct video post |
| POST | `https://open.tiktokapis.com/v2/post/publish/inbox/video/init/` | video.upload | Initialize inbox/draft video post |
| POST | `https://open.tiktokapis.com/v2/post/publish/content/init/` | video.publish | Initialize photo post |
| POST | `https://open.tiktokapis.com/v2/post/publish/status/fetch/` | video.publish | Poll publish status |

---

### Token Types

| Token | Prefix | Validity | Grant Type |
|-------|--------|----------|------------|
| access_token | `act.` | 24 hours (86400s) | authorization_code |
| refresh_token | `rft.` | 365 days (31536000s) | refresh_token |
| client_access_token | `clt.` | 2 hours (7200s) | client_credentials |

---

### Key Scopes

| Scope | Description |
|-------|-------------|
| user.info.basic | open_id, union_id, avatar_url, display_name |
| user.info.profile | bio_description, profile_deep_link, is_verified, username |
| user.info.stats | follower_count, following_count, likes_count, video_count |
| video.list | Read user's public videos |
| video.publish | Directly post to creator's TikTok feed |
| video.upload | Send content to creator's Inbox as draft |
| research.data.basic | TikTok public data (Research API) |
| research.adlib.basic | Public commercial data (Research API) |

---

### Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET /v2/user/info/ | 600 req/min |
| POST /v2/video/list/ | 600 req/min |
| POST /v2/video/query/ | 600 req/min |
| POST /v2/post/publish/video/init/ | 6 req/min per token |
| POST /v2/post/publish/inbox/video/init/ | 6 req/min per token |

Exceeded: HTTP `429`, error `rate_limit_exceeded`. Window: 1-minute sliding.

---

### Common Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| ok | 200 | Success |
| access_token_invalid | 401 | Token invalid or missing — refresh and retry |
| scope_not_authorized | 401 | User hasn't authorized required scope — re-OAuth |
| scope_permission_missed | 400 | Token valid but field needs additional scope |
| invalid_params | 400 | Request parameter invalid — check error.message |
| rate_limit_exceeded | 429 | Rate limited — backoff and retry |
| spam_risk_too_many_pending_share | 403 | Max 5 inbox drafts per 24 hours |
| unaudited_client_can_only_post_to_private_accounts | 403 | App needs audit for public posts |
| url_ownership_unverified | 403 | Domain must be verified for PULL_FROM_URL |
| internal_error | 500 | TikTok server error — retry with backoff |

---

### Video Fields (Quick Reference)

`id` · `title` · `video_description` · `create_time` · `cover_image_url` · `share_url` · `video_url` · `duration` · `height` · `width` · `like_count` · `comment_count` · `share_count` · `view_count` · `embed_html` · `embed_link`

---

### Ads API Reporting Metrics (Quick Reference)

**Delivery:** `impressions` · `reach` · `frequency` · `clicks` · `ctr` · `cpm` · `cpc` · `cpa` · `spend`

**Video:** `video_play_actions` · `video_watched_2s` · `video_watched_6s` · `video_views_p25` · `video_views_p50` · `video_views_p75` · `video_views_p100` · `average_video_play` · `engaged_view` · `engaged_view_15s`

**Engagement:** `likes` · `comments` · `shares` · `follows` · `profile_visits`

**Conversion:** `conversions` · `cost_per_conversion` · `conversion_rate` · `result` · `cost_per_result`
