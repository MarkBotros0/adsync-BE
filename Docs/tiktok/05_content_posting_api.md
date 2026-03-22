# TikTok API — Content Posting

## Overview

The Content Posting API enables posting videos and photos to TikTok creator accounts.

**Two post destinations:**

| Mode | Scope | Description |
|------|-------|-------------|
| Direct Post | `video.publish` | Publishes immediately to creator's TikTok feed |
| Inbox (Draft) | `video.upload` | Sends to creator's Inbox as a draft to review and post |

**Two upload methods:**

| Method | Value | Description |
|--------|-------|-------------|
| PULL | `PULL_FROM_URL` | TikTok servers download media from a URL you provide |
| PUSH | `FILE_UPLOAD` | You upload the media binary directly to TikTok |

**Important:** All content posted by unaudited clients is restricted to `SELF_ONLY` (private) until API audit completes.

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `https://open.tiktokapis.com/v2/post/publish/creator_info/query/` | Get creator capabilities and privacy options |
| POST | `https://open.tiktokapis.com/v2/post/publish/video/init/` | Initialize Direct Post (video) |
| POST | `https://open.tiktokapis.com/v2/post/publish/inbox/video/init/` | Initialize Inbox/Draft Post (video) |
| POST | `https://open.tiktokapis.com/v2/post/publish/content/init/` | Initialize photo post |
| POST | `https://open.tiktokapis.com/v2/post/publish/status/fetch/` | Check publish status |
| PUT | `{upload_url from init response}` | Upload video chunks (PUSH/FILE_UPLOAD only) |

---

## Step 1: Query Creator Info

```
POST https://open.tiktokapis.com/v2/post/publish/creator_info/query/
Authorization: Bearer {access_token}
Content-Type: application/json
```

### Creator Info Response Fields

| Field | Type | Description |
|-------|------|-------------|
| creator_avatar_url | string | Creator's avatar image URL |
| creator_username | string | Creator's @username |
| creator_nickname | string | Creator's display name |
| privacy_level_options | string[] | Available privacy levels for this creator |
| duet_disabled | boolean | Whether duet feature is disabled for this creator |
| stitch_disabled | boolean | Whether stitch feature is disabled for this creator |
| comment_disabled | boolean | Whether comments are disabled for this creator |
| max_video_post_duration_sec | integer | Maximum video duration in seconds allowed for this creator |

---

## Step 2a: Initialize Direct Post (Video)

```
POST https://open.tiktokapis.com/v2/post/publish/video/init/
Authorization: Bearer {access_token}
Content-Type: application/json; charset=UTF-8
```

**Rate limit:** 6 requests/minute per access token

### Request Body

```json
{
  "post_info": {
    "title": "Video caption here #hashtag",
    "privacy_level": "PUBLIC_TO_EVERYONE",
    "disable_duet": false,
    "disable_stitch": false,
    "disable_comment": false,
    "video_cover_timestamp_ms": 1000,
    "brand_content_toggle": false,
    "brand_organic_toggle": false,
    "is_aigc": false
  },
  "source_info": {
    "source": "FILE_UPLOAD",
    "video_size": 52428800,
    "chunk_size": 10485760,
    "total_chunk_count": 5
  }
}
```

### post_info Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string | No | Video caption. Max 2200 UTF-16 runes. |
| privacy_level | string | Yes | `PUBLIC_TO_EVERYONE`, `MUTUAL_FOLLOW_FRIENDS`, `FOLLOWER_OF_CREATOR`, or `SELF_ONLY` |
| disable_duet | boolean | No | Prevent other users from creating duets with this video |
| disable_stitch | boolean | No | Prevent other users from stitching this video |
| disable_comment | boolean | No | Prevent comments on this video |
| video_cover_timestamp_ms | integer | No | Millisecond offset into the video for cover image frame selection |
| brand_content_toggle | boolean | No | Mark as paid partnership / branded content |
| brand_organic_toggle | boolean | No | Mark as creator's own business promotion |
| is_aigc | boolean | No | Mark as AI-generated content |

### source_info Fields — FILE_UPLOAD

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| source | string | Yes | `"FILE_UPLOAD"` |
| video_size | integer | Yes | Total file size in bytes |
| chunk_size | integer | Yes | Size of each chunk in bytes (min 5 MB, max 64 MB) |
| total_chunk_count | integer | Yes | Total number of chunks (max 1000) |

### source_info Fields — PULL_FROM_URL

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| source | string | Yes | `"PULL_FROM_URL"` |
| video_url | string | Yes | HTTPS URL to video file. Domain must be verified in Developer Portal. |

### Init Response

```json
{
  "data": {
    "publish_id": "v_pub_url~v2-7093091080579734827",
    "upload_url": "https://upload.tiktokapis.com/video/?upload_id=...&upload_token=..."
  },
  "error": { "code": "ok", "message": "", "log_id": "..." }
}
```

| Field | Type | Description |
|-------|------|-------------|
| publish_id | string | Tracking ID for this post (max 64 chars). Used to poll status. |
| upload_url | string | PUT endpoint for chunk upload. Valid 1 hour. FILE_UPLOAD only. Max 256 chars. |

---

## Step 2b: Initialize Inbox/Draft Post (Video)

```
POST https://open.tiktokapis.com/v2/post/publish/inbox/video/init/
```

Same request body and response as Direct Post init. Requires `video.upload` scope.

**Inbox limit:** Max 5 pending drafts within any 24-hour period (error: `spam_risk_too_many_pending_share`).

---

## Step 2c: Initialize Photo Post

```
POST https://open.tiktokapis.com/v2/post/publish/content/init/
```

Request body includes:
- `post_mode`: `"DIRECT_POST"` or `"INBOX_VIDEO"`
- `media_type`: `"PHOTO"`
- `post_info`: title, privacy_level, auto_add_music
- `source_info.source`: `"PULL_FROM_URL"` only (photos must be URL-sourced)
- `source_info.photo_images`: array of image URLs
- `source_info.photo_cover_index`: index of the cover photo

---

## Step 3: Upload Video (FILE_UPLOAD / PUSH only)

Upload in chunks via HTTP PUT to the `upload_url` from the init response.

```
PUT {upload_url}
Content-Type: video/mp4
Content-Length: {chunk_byte_size}
Content-Range: bytes {first_byte}-{last_byte}/{total_bytes}
```

Accepted Content-Type values: `video/mp4`, `video/quicktime`, `video/webm`

### Example — 3-chunk upload (30 MB file, 10 MB chunks)

```
Chunk 1:  Content-Range: bytes 0-10485759/31457280
Chunk 2:  Content-Range: bytes 10485760-20971519/31457280
Chunk 3:  Content-Range: bytes 20971520-31457279/31457280
```

### Upload Response Codes

| HTTP Status | Meaning | Action |
|-------------|---------|--------|
| 201 Created | All chunks received; processing begins | Poll `/status/fetch/` |
| 206 Partial Content | Chunk accepted; more chunks needed | Upload next chunk |
| 400 Bad Request | Malformed headers or byte size mismatch | Fix Content-Range / Content-Length |
| 403 Forbidden | `upload_url` expired (1 hour limit) | Re-initialize to get new upload_url |
| 416 Range Not Satisfiable | Content-Range doesn't match upload progress | Verify byte offsets |

---

## Chunk Upload Specifications

| Parameter | Value |
|-----------|-------|
| Minimum chunk size | 5 MB |
| Maximum chunk size (non-final) | 64 MB |
| Maximum chunk size (final chunk) | 128 MB |
| Files under 5 MB | Upload as single chunk |
| Maximum total chunks | 1,000 |

---

## Step 4: Poll Publish Status

```
POST https://open.tiktokapis.com/v2/post/publish/status/fetch/
Authorization: Bearer {access_token}
Content-Type: application/json

{"publish_id": "v_pub_url~v2-7093091080579734827"}
```

### Status Values

| Status | Description |
|--------|-------------|
| PROCESSING_DOWNLOAD | TikTok is downloading the video (PULL_FROM_URL) |
| PROCESSING_UPLOAD | TikTok is processing the uploaded file (FILE_UPLOAD) |
| FAILED | Post failed — check `fail_reason` field |
| PUBLISHED | Video successfully published to TikTok |

---

## Video Specifications

| Property | Specification |
|----------|--------------|
| Recommended format | MP4 |
| Supported formats | MP4, WebM, MOV |
| Recommended codec | H.264 |
| Supported codecs | H.264, H.265, VP8, VP9 |
| Frame rate | 23–60 FPS |
| Resolution (height or width) | 360–4096 pixels |
| Maximum duration (API) | 10 minutes (600 seconds) |
| Maximum file size | 4 GB |

---

## Photo Specifications

| Property | Specification |
|----------|--------------|
| Supported formats | WebP, JPEG |
| Maximum file size per image | 20 MB |
| Maximum resolution | 1080p |
| Source method | PULL_FROM_URL only |

---

## Privacy Level Values

| Value | Description |
|-------|-------------|
| PUBLIC_TO_EVERYONE | Visible to all TikTok users |
| MUTUAL_FOLLOW_FRIENDS | Visible only to mutual followers |
| FOLLOWER_OF_CREATOR | Visible to followers of this creator |
| SELF_ONLY | Private, visible only to the creator |

---

## PULL_FROM_URL Requirements

- Domain or URL prefix must be verified in Developer Portal app settings
- URL must remain accessible for the entire download duration
- Download times out 1 hour after task initiation
- Must be HTTPS

---

## Error Codes

| HTTP | Error Code | Description | Action |
|------|------------|-------------|--------|
| 400 | invalid_param | One or more request parameters are invalid | Review error message for specific field |
| 401 | access_token_invalid | Access token is invalid or missing | Refresh token and retry |
| 401 | scope_not_authorized | User has not authorized required scope | Re-initiate OAuth with correct scope |
| 403 | spam_risk_too_many_posts | Creator has exceeded posting frequency limits | Reduce posting frequency; retry later |
| 403 | spam_risk_too_many_pending_share | Max 5 pending inbox shares within 24 hours | Wait for existing drafts to be posted/deleted |
| 403 | user_banned_from_posting | Creator account is banned from posting | Creator resolves account issue with TikTok |
| 403 | unaudited_client_can_only_post_to_private_accounts | App not yet audited; posts forced to SELF_ONLY | Complete TikTok API audit for public posting |
| 403 | url_ownership_unverified | Domain not verified for PULL_FROM_URL | Register and verify domain in Developer Portal |
| 429 | rate_limit_exceeded | 6 req/min limit exceeded for init endpoint | Implement exponential backoff |
| 500 | internal_error | TikTok server error | Retry with backoff; contact support if persistent |

---

## Flow Comparison

| Aspect | Direct Post (`video.publish`) | Inbox/Draft (`video.upload`) |
|--------|-------------------------------|------------------------------|
| Where content goes | Creator's TikTok feed immediately | Creator's TikTok Inbox as a draft |
| Creator approval needed | No | Yes — creator must post from Inbox |
| Required scope | `video.publish` | `video.upload` |
| Inbox limit | N/A | Max 5 pending drafts per 24 hours |
| API audit required | Yes (for public posts) | No |
| Init endpoint | `/v2/post/publish/video/init/` | `/v2/post/publish/inbox/video/init/` |
