# TikTok API — Display API

## Overview

The TikTok Display API enables platforms to showcase TikTok creator profiles and video content. It allows creators to display their TikTok identity and videos on third-party platforms, enriching content and attracting audiences without leaving your platform.

**Key distinction from Login Kit:** Display API is read-only, focused on displaying public creator content. Login Kit handles full user authentication and broader write permissions.

---

## Use Cases

1. **Profile Display** — Show creator's TikTok profile (avatar, name, bio) with deep links back to their TikTok page
2. **Self-Selected Videos** — Allow creators to choose which videos to display on your platform
3. **Recent Videos Feed** — Display a creator's most recent TikTok videos with embedded player integration

---

## Authentication

Uses the same OAuth 2.0 flow as Login Kit (see [02_authentication.md](02_authentication.md)). Requires user authorization and a user access token.

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `https://open.tiktokapis.com/v2/user/info/` | User profile info |
| POST | `https://open.tiktokapis.com/v2/video/list/` | Paginated list of user's videos |
| POST | `https://open.tiktokapis.com/v2/video/query/` | Fetch specific videos by ID (max 20) |

---

## Available User Fields

| Field | Scope | Description |
|-------|-------|-------------|
| open_id | user.info.basic | Unique user ID in your app |
| union_id | user.info.basic | Unique user ID across developer's apps |
| avatar_url | user.info.basic | Profile image URL |
| avatar_url_100 | user.info.basic | Profile image URL (100×100) |
| avatar_large_url | user.info.basic | Profile image URL (large) |
| display_name | user.info.basic | User's display name |
| bio_description | user.info.profile | User's bio text |
| profile_deep_link | user.info.profile | Deep link to TikTok profile page |
| is_verified | user.info.profile | Whether user has verified badge |
| username | user.info.profile | User's @username |
| follower_count | user.info.stats | Follower count |
| following_count | user.info.stats | Following count |
| likes_count | user.info.stats | Total likes across all videos |
| video_count | user.info.stats | Total public video count |

---

## Available Video Fields

All standard video object fields are available:

| Field | Description |
|-------|-------------|
| id | Unique video identifier |
| title | Video title |
| video_description | Video caption/description |
| create_time | Creation timestamp (Unix seconds) |
| cover_image_url | Thumbnail URL |
| share_url | Direct shareable link |
| duration | Duration in seconds |
| height | Height in pixels |
| width | Width in pixels |
| like_count | Like count |
| comment_count | Comment count |
| share_count | Share count |
| view_count | View count |
| embed_html | HTML embed code |
| embed_link | Embed URL |

---

## Required Scopes

| Scope | Required For |
|-------|-------------|
| user.info.basic | open_id, union_id, avatar_url, display_name |
| user.info.profile | bio_description, profile_deep_link, is_verified, username |
| user.info.stats | follower_count, following_count, likes_count, video_count |
| video.list | Both video list and video query endpoints |

---

## Embedding Videos

Use `embed_html` or `embed_link` fields from video objects to embed TikTok videos directly on your platform:

```html
<!-- Using embed_html field (ready-to-use iframe) -->
<div class="tiktok-embed">
  {embed_html value}
</div>
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET /v2/user/info/ | 600 req/min |
| POST /v2/video/list/ | 600 req/min |
| POST /v2/video/query/ | 600 req/min |

---

## Display API vs Login Kit

| Aspect | Display API | Login Kit |
|--------|-------------|-----------|
| Purpose | Read-only display of creator content | Full auth + read/write access |
| Scopes needed | user.info.basic, video.list | Any approved scope |
| Can post content | No | Yes (with video.publish) |
| Can access stats | Yes (user.info.stats) | Yes |
| Typical use case | Embed TikTok profile/videos on website | Full TikTok platform integration |
| Same endpoints | Yes | Yes |

Full endpoint documentation: see [03_user_api.md](03_user_api.md) and [04_video_api.md](04_video_api.md).
