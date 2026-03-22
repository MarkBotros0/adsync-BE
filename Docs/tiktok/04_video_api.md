# TikTok API — Video

## Overview

Two endpoints for reading user video data:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `https://open.tiktokapis.com/v2/video/list/` | POST | Paginated list of all user's public videos |
| `https://open.tiktokapis.com/v2/video/query/` | POST | Fetch specific videos by ID (max 20 per request) |

Both require the `video.list` scope.

---

## Video Object Fields — Complete List

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique video identifier |
| title | string | Video title / headline |
| video_description | string | Text caption or description of the video |
| create_time | integer | Unix timestamp (seconds) when the video was created |
| cover_image_url | string | URL of the video's thumbnail / cover image |
| share_url | string | Direct shareable link to the video |
| video_url | string | URL to the video file (if available) |
| duration | integer | Length of the video in seconds |
| height | integer | Video resolution height in pixels |
| width | integer | Video resolution width in pixels |
| like_count | integer | Total number of likes |
| comment_count | integer | Total number of comments |
| share_count | integer | Total number of shares |
| view_count | integer | Total number of views |
| embed_html | string | HTML code for embedding the video in a webpage |
| embed_link | string | URL for embedding the video content |

---

## Endpoint 1: Video List

| | |
|-|-|
| **Method** | POST |
| **URL** | `https://open.tiktokapis.com/v2/video/list/` |
| **Scope** | `video.list` |
| **Rate Limit** | 600 req/min |

### Request Headers

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| Authorization | string | Yes | `Bearer {access_token}` |
| Content-Type | string | Yes | `application/json` |

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| fields | string | Yes | Comma-separated video fields to return |

### Request Body

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| cursor | int64 | No | Pagination cursor (UTC Unix timestamp in ms). Fetches videos created before this timestamp. Default: current time. |
| max_count | int32 | No | Results per page. Default: 10, max: 20. |

### Example Request

```bash
curl -X POST 'https://open.tiktokapis.com/v2/video/list/?fields=id,title,video_description,create_time,cover_image_url,share_url,duration,height,width,like_count,comment_count,share_count,view_count,embed_link,embed_html' \
  -H 'Authorization: Bearer act.example...' \
  -H 'Content-Type: application/json' \
  -d '{"max_count": 20}'
```

### Response

```json
{
  "data": {
    "videos": [
      {
        "id": "7093091080579734827",
        "title": "Example video",
        "video_description": "Check this out #fyp",
        "create_time": 1651392000,
        "cover_image_url": "https://...",
        "duration": 30,
        "height": 1920,
        "width": 1080,
        "like_count": 1234,
        "comment_count": 56,
        "share_count": 78,
        "view_count": 99000
      }
    ],
    "cursor": 1651392000000,
    "has_more": true
  },
  "error": { "code": "ok", "message": "", "log_id": "..." }
}
```

### Pagination

- Results sorted by creation time (descending — newest first)
- When `has_more` is `true`, pass `response.cursor` as the `cursor` body parameter in the next request
- `cursor` is a UTC Unix timestamp in milliseconds
- Pass a custom timestamp as `cursor` to fetch videos created before that specific time

---

## Endpoint 2: Video Query

| | |
|-|-|
| **Method** | POST |
| **URL** | `https://open.tiktokapis.com/v2/video/query/` |
| **Scope** | `video.list` |
| **Rate Limit** | 600 req/min |
| **Max IDs per request** | 20 |

### Request Headers

Same as Video List.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| fields | string | Yes | Comma-separated video fields to return |

### Request Body

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| filters | object | Yes | Filter object |
| filters.video_ids | string[] | Yes | Array of video IDs to fetch (max 20) |

### Example Request

```bash
curl -X POST 'https://open.tiktokapis.com/v2/video/query/?fields=id,title,like_count,comment_count,share_count,view_count,cover_image_url,share_url,duration,create_time' \
  -H 'Authorization: Bearer act.example...' \
  -H 'Content-Type: application/json' \
  -d '{"filters": {"video_ids": ["7093091080579734827", "7093091080579734828"]}}'
```

### Response

```json
{
  "data": {
    "videos": [
      {
        "id": "7093091080579734827",
        "title": "Example video",
        "like_count": 1234,
        "comment_count": 56,
        "share_count": 78,
        "view_count": 99000
      }
    ]
  },
  "error": { "code": "ok", "message": "", "log_id": "..." }
}
```

**Notes:**
- Only returns videos belonging to the authorized user
- Can be used to refresh cover image URL TTL
- No pagination — use `video_ids` filter to select specific videos

---

## Privacy Level Values

| Value | Description |
|-------|-------------|
| PUBLIC_TO_EVERYONE | Visible to all TikTok users |
| MUTUAL_FOLLOW_FRIENDS | Visible only to mutual followers |
| FOLLOWER_OF_CREATOR | Visible to followers only |
| SELF_ONLY | Private, visible only to the creator |

---

## Video Status Values (Content Posting)

| Status | Description |
|--------|-------------|
| PROCESSING_DOWNLOAD | TikTok is downloading the video (PULL_FROM_URL flow) |
| PROCESSING_UPLOAD | TikTok is processing the uploaded video (FILE_UPLOAD flow) |
| FAILED | Post failed — check `fail_reason` field |
| PUBLISHED | Video successfully published to TikTok |
