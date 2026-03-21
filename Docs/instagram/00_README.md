# Instagram / Meta API Documentation

Source: Meta Developer Docs (developers.facebook.com/docs/instagram-platform)
API Version: v22.0 (released Feb 2025, supported until Feb 2027)
Base URLs: `https://graph.facebook.com/v22.0/` (Facebook Login) | `https://graph.instagram.com/v22.0/` (Instagram Login)

---

## Files in This Folder

| File | Contents |
|------|----------|
| [01_overview.md](01_overview.md) | API variants (Instagram Login vs Facebook Login), versioning, base URLs, node types, field selection, pagination, batch requests, rate limits |
| [02_authentication.md](02_authentication.md) | Both auth flows, all token types, scopes/permissions, long-lived exchange, token refresh, debug_token, appsecret_proof, system users |
| [03_instagram_user_api.md](03_instagram_user_api.md) | IG User node fields, all edges, business discovery API, hashtag search API, mentions API, recently searched hashtags |
| [04_media_api.md](04_media_api.md) | IG Media node fields, media types, carousel children, media specs per type, comments edge, product tags edge |
| [05_content_publishing_api.md](05_content_publishing_api.md) | Single image/video/reel/story publish flow, carousel 3-step flow, resumable upload, publishing limits, container status codes |
| [06_insights_api.md](06_insights_api.md) | Account-level metrics, media-level metrics (feed/reels/stories), breakdown dimensions, timeframes, required permissions per metric |
| [07_comments_moderation_api.md](07_comments_moderation_api.md) | Reading comments, replying, hiding/unhiding, deleting, enable/disable on media, mentions handling, comment webhooks |
| [08_webhooks.md](08_webhooks.md) | All webhook fields, setup flow, hub challenge verification, X-Hub-Signature-256 validation, payload examples per field type |
| [09_instagram_login_api.md](09_instagram_login_api.md) | Instagram API with Instagram Login (no Facebook Page required), scopes, token exchange, user fields, differences from Facebook Login path |

---

## Quick Reference

```
# IG User
GET /v22.0/{ig-user-id}                                          Read IG User profile
GET /v22.0/me                                                    Current user's IG profile
GET /v22.0/{ig-user-id}/media                                    Feed posts (max 10,000 most recent)
GET /v22.0/{ig-user-id}/stories                                  Active stories (24h window only)
GET /v22.0/{ig-user-id}/live_media                               Live video objects
GET /v22.0/{ig-user-id}/tags                                     Media where user was tagged by others
GET /v22.0/{ig-user-id}/insights                                 Account-level analytics
GET /v22.0/{ig-user-id}/content_publishing_limit                 Publishing quota usage
GET /v22.0/{ig-user-id}/recently_searched_hashtags               Hashtags searched in last 7 days

# IG Media
GET /v22.0/{ig-media-id}                                         Read media object
GET /v22.0/{ig-media-id}/comments                                Comments on media
GET /v22.0/{ig-media-id}/insights                                Post-level analytics
GET /v22.0/{ig-media-id}/children                                Items in carousel album
GET /v22.0/{ig-media-id}/product_tags                            Product tags on media

# Content Publishing — Single Image/Video (2-step)
POST /v22.0/{ig-user-id}/media                                   Step 1: Create container
GET  /v22.0/{ig-container-id}?fields=status_code                 Check container status (videos)
POST /v22.0/{ig-user-id}/media_publish                           Step 2: Publish container

# Content Publishing — Carousel (3-step)
POST /v22.0/{ig-user-id}/media  (is_carousel_item=true) ×N       Step 1a: Item containers
POST /v22.0/{ig-user-id}/media  (media_type=CAROUSEL)            Step 1b: Carousel container
POST /v22.0/{ig-user-id}/media_publish                           Step 2: Publish

# Resumable Upload
POST https://rupload.facebook.com/ig-api-upload/v22.0/{container-id}   Upload video bytes

# Hashtag Search
GET /v22.0/ig_hashtag_search?user_id={id}&q={hashtag}            Step 1: Get hashtag ID
GET /v22.0/{ig-hashtag-id}?fields=id,name                        Step 2: Hashtag metadata
GET /v22.0/{ig-hashtag-id}/top_media?user_id={id}                Step 3: Top posts
GET /v22.0/{ig-hashtag-id}/recent_media?user_id={id}             Step 4: Recent posts

# Business Discovery
GET /v22.0/{ig-user-id}?fields=business_discovery.fields(username,followers_count,media_count)

# Comments
POST   /v22.0/{ig-media-id}/comments?message={text}              Post top-level comment
POST   /v22.0/{ig-comment-id}/replies?message={text}             Reply to comment
POST   /v22.0/{ig-comment-id}?hide=true|false                    Hide / unhide comment
DELETE /v22.0/{ig-comment-id}                                    Delete comment
POST   /v22.0/{ig-media-id}?comment_enabled=true|false           Enable / disable comments on media

# Mentions
POST /v22.0/{ig-user-id}/mentions?commented_media_id={id}&message={text}   Reply to caption mention
POST /v22.0/{ig-user-id}/mentions?comment_id={id}&message={text}            Reply to comment mention

# Authentication
GET /v22.0/oauth/access_token?grant_type=fb_exchange_token&client_id=...&client_secret=...&fb_exchange_token=...
GET /v22.0/oauth/access_token?grant_type=ig_refresh_token&access_token=...
GET /v22.0/debug_token?input_token={token}&access_token={app-access-token}
GET /v22.0/me/accounts                                           List pages + page tokens

# Webhooks
POST   /v22.0/me/subscribed_apps?subscribed_fields=comments,mentions,story_insights,messages
DELETE /v22.0/me/subscribed_apps?subscribed_fields=comments,...
```

---

## Key Limits & Quotas

| Limit | Value |
|-------|-------|
| Publishing quota | 50 posts per IG User per 24-hour rolling window |
| Container creation max | 400 containers per rolling 24-hour period |
| Container expiry | 24 hours after creation |
| Hashtag search limit | 30 unique hashtags per IG User per 7-day rolling window |
| Standard API rate limit | 4,800 calls per 24h × number of impressions |
| Caption max length | 2,200 characters |
| Caption max hashtags | 30 |
| Caption max @tags | 20 |
| Carousel max items | 10 (images and/or videos mixed) |
| Carousel counts as | 1 post against publishing quota |
| Product tags per media | 5 maximum |
| Collaborators per post | 3 maximum (Feed, Reels, Carousels) |
| Comments per query | 50 maximum |
| Webhook retry window | 36 hours |
| Long-lived token validity | 60 days |
| Reel max duration | 15 minutes |
| Reel min duration | 3 seconds |
| Story video max duration | 60 seconds |
| Story image max size | 8 MB |
| Feed image max size | 8 MB |
| Reel max file size | 300 MB |
| Feed video max file size | 1 GB |

---

## API Variants Comparison

| Feature | Instagram Login | Facebook Login |
|---------|----------------|----------------|
| Base URL | `graph.instagram.com` | `graph.facebook.com` |
| Token type | Instagram User token | Facebook User / Page token |
| Facebook Page required | No | Yes |
| Ads access | No | Yes |
| Product tagging | No | Yes |
| Key scope prefix | `instagram_business_*` | `instagram_*` / `pages_*` |
| Short-lived token validity | 1 hour | ~1 hour |
| Long-lived token validity | 60 days | 60 days |
| `/me` resolves at | `graph.instagram.com/me` | `graph.facebook.com/me` |

---

## Container Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| `IN_PROGRESS` | Still processing | Poll again (once per minute, max 5 min) |
| `FINISHED` | Ready to publish | Call `/media_publish` |
| `ERROR` | Processing failed | Check `status` field for error subcode |
| `EXPIRED` | Not published within 24 hours | Create a new container |
| `PUBLISHED` | Already published | No action needed |

---

## Media Types

| `media_type` | `media_product_type` | Description |
|-------------|---------------------|-------------|
| `IMAGE` | `FEED` or `STORY` | Single photo |
| `VIDEO` | `FEED` | Single video |
| `CAROUSEL_ALBUM` | `FEED` | Multiple photos/videos |
| `VIDEO` | `REELS` | Short-form video (Reel) |
| `IMAGE` or `VIDEO` | `STORY` | Ephemeral 24h story |

---

## Permissions Quick Reference

### Facebook Login

| Permission | Required For |
|-----------|-------------|
| `instagram_basic` | Read profile and media |
| `instagram_content_publish` | Publish media |
| `instagram_manage_comments` | Read/manage comments |
| `instagram_manage_insights` | Account and media insights |
| `instagram_manage_messages` | Direct messages |
| `pages_read_engagement` | Required with most IG permissions |
| `ads_management` | If role granted via Business Manager |
| `instagram_shopping_tag_products` | Product tagging |

### Instagram Login (new scopes — old values deprecated Jan 27, 2025)

| Scope | Replaces |
|-------|---------|
| `instagram_business_basic` | `business_basic` |
| `instagram_business_content_publish` | `business_content_publish` |
| `instagram_business_manage_comments` | `business_manage_comments` |
| `instagram_business_manage_messages` | `business_manage_messages` |
