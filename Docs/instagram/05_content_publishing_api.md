# Instagram Content Publishing API

API Version: v22.0

---

## Overview

Content publishing uses a two-step workflow for single images and videos, and a three-step workflow for carousels. All publishing is orchestrated through two endpoints:

- `/{ig-user-id}/media` — creates a media container
- `/{ig-user-id}/media_publish` — publishes the container

Containers must be published within 24 hours of creation or they expire. Large videos can be uploaded using the resumable upload protocol via `rupload.facebook.com`.

---

## Host URLs

| Purpose | Host |
|---|---|
| Standard API calls (Facebook Login) | `graph.facebook.com` |
| Standard API calls (Instagram Login) | `graph.instagram.com` |
| Resumable video uploads | `rupload.facebook.com` |

---

## Required Permissions

### Facebook Login

| Permission | Purpose |
|---|---|
| `instagram_basic` | Read basic account info |
| `instagram_content_publish` | Create and publish media |
| `pages_read_engagement` | Read Page engagement data |

### Instagram Login

| Permission | Purpose |
|---|---|
| `instagram_business_basic` | Read basic account info |
| `instagram_business_content_publish` | Create and publish media |

### Product Tagging (additional)

| Permission | Purpose |
|---|---|
| `catalog_management` | Access product catalog |
| `instagram_shopping_tag_products` | Tag products in media |

---

## Rate Limits and Quotas

| Limit | Value |
|---|---|
| Posts per IG user per 24-hour moving window | 50 |
| Media containers created per rolling 24-hour period | 400 |
| Container expiry | 24 hours after creation |

Notes:

- Carousels count as a single post against the 50/24h limit.
- Containers that expire must be recreated — they cannot be reused.
- Use the `content_publishing_limit` endpoint to check current quota usage before publishing.

---

## Unsupported Features

The following features are not supported via the Publishing API:

- Shopping tags
- Branded content tags
- Filters
- Page Publishing Authorization (PPA) — if the connected Page requires PPA, it must be completed before publishing will succeed.

---

## Single Image Publish (2-step)

### Step 1 — Create Image Container

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `image_url` | string | Yes | Publicly accessible URL of the image |
| `caption` | string | No | Post caption, max 2200 chars, 30 hashtags, 20 @tags |
| `location_id` | string | No | Facebook Page ID for location tagging |
| `user_tags` | JSON array | No | Array of user tag objects, max 30 people |
| `alt_text` | string | No | Accessibility alt text, max 1000 chars (images only) |
| `access_token` | string | Yes | User access token |

User tag object format:

```json
[
  {"username": "someuser", "x": 0.5, "y": 0.8}
]
```

Example request:

```
POST https://graph.facebook.com/v22.0/17841400008460056/media
  ?image_url=https%3A%2F%2Fexample.com%2Fimage.jpg
  &caption=Hello%20world%20%23example
  &location_id=110867665606484
  &user_tags=%5B%7B%22username%22%3A%22testuser%22%2C%22x%22%3A0.5%2C%22y%22%3A0.5%7D%5D
  &alt_text=A%20scenic%20mountain%20view
  &access_token={access-token}
```

Response:

```json
{
  "id": "17889615814797561"
}
```

### Step 2 — Publish Image Container

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media_publish
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `creation_id` | string | Yes | Container ID returned from Step 1 |
| `access_token` | string | Yes | User access token |

Example request:

```
POST https://graph.facebook.com/v22.0/17841400008460056/media_publish
  ?creation_id=17889615814797561
  &access_token={access-token}
```

Response:

```json
{
  "id": "17854360229135492"
}
```

The returned `id` is the published IG Media ID.

---

## Single Video Publish (2-step)

### Step 1 — Create Video Container

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `video_url` | string | Yes | Publicly accessible URL of the video |
| `caption` | string | No | Post caption, max 2200 chars |
| `access_token` | string | Yes | User access token |

Example request:

```
POST https://graph.facebook.com/v22.0/17841400008460056/media
  ?video_url=https%3A%2F%2Fexample.com%2Fvideo.mp4
  &caption=Check%20out%20this%20video
  &access_token={access-token}
```

Response:

```json
{
  "id": "17889615814797562"
}
```

### Step 1b — Check Container Status

Video containers require processing time. Poll the container status before publishing.

```
GET https://graph.facebook.com/v22.0/{ig-container-id}
  ?fields=status_code
  &access_token={access-token}
```

Example request:

```
GET https://graph.facebook.com/v22.0/17889615814797562?fields=status_code&access_token={access-token}
```

Response:

```json
{
  "status_code": "FINISHED",
  "id": "17889615814797562"
}
```

Status codes:

| Code | Meaning |
|---|---|
| `IN_PROGRESS` | Video is still processing |
| `FINISHED` | Processing complete, ready to publish |
| `ERROR` | Processing failed; `status` field contains error subcode |
| `EXPIRED` | Container was not published within 24 hours; create a new container |
| `PUBLISHED` | Container has already been published |

Recommendation: Poll once per minute, up to a maximum of 5 minutes. Do not attempt to publish until `status_code` is `FINISHED`.

### Step 2 — Publish Video Container

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media_publish
  ?creation_id=17889615814797562
  &access_token={access-token}
```

Response:

```json
{
  "id": "17854360229135493"
}
```

---

## Reel Publish (2-step)

### Step 1 — Create Reel Container

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `video_url` | string | Yes | Publicly accessible URL of the video |
| `media_type` | string | Yes | Must be `REELS` |
| `caption` | string | No | Post caption, max 2200 chars |
| `share_to_feed` | boolean | No | If `true`, reel also appears in the Feed tab |
| `cover_url` | string | No | URL of a custom cover image |
| `audio_name` | string | No | Custom name for the audio; can only be set once |
| `thumb_offset` | integer | No | Millisecond offset into the video for the thumbnail frame |
| `collaborators` | JSON array | No | Array of usernames to invite as collaborators, max 3 |
| `trial_params` | JSON object | No | Trial reel parameters, e.g. `{"graduation_strategy":"MANUAL"}` |
| `access_token` | string | Yes | User access token |

Example request:

```
POST https://graph.facebook.com/v22.0/17841400008460056/media
  ?video_url=https%3A%2F%2Fexample.com%2Freel.mp4
  &media_type=REELS
  &caption=My%20latest%20reel%20%23reel
  &share_to_feed=true
  &cover_url=https%3A%2F%2Fexample.com%2Fcover.jpg
  &thumb_offset=2000
  &collaborators=%5B%22collab_user1%22%2C%22collab_user2%22%5D
  &access_token={access-token}
```

Response:

```json
{
  "id": "17889615814797563"
}
```

### Step 1b — Check Container Status

Poll container status as described in the Single Video Publish section. Do not proceed until `status_code` is `FINISHED`.

### Step 2 — Publish Reel Container

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media_publish
  ?creation_id=17889615814797563
  &access_token={access-token}
```

Response:

```json
{
  "id": "17854360229135494"
}
```

---

## Story Publish (2-step)

### Step 1 — Create Story Container

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `image_url` | string | Yes (image) | Publicly accessible URL of the image |
| `video_url` | string | Yes (video) | Publicly accessible URL of the video |
| `media_type` | string | Yes | Must be `STORIES` |
| `user_tags` | JSON array | No | Array of user tag objects; `x`/`y` coordinates are optional for stories |
| `access_token` | string | Yes | User access token |

Example request (image story):

```
POST https://graph.facebook.com/v22.0/17841400008460056/media
  ?image_url=https%3A%2F%2Fexample.com%2Fstory.jpg
  &media_type=STORIES
  &user_tags=%5B%7B%22username%22%3A%22taggeduser%22%7D%5D
  &access_token={access-token}
```

Example request (video story):

```
POST https://graph.facebook.com/v22.0/17841400008460056/media
  ?video_url=https%3A%2F%2Fexample.com%2Fstory.mp4
  &media_type=STORIES
  &access_token={access-token}
```

Response:

```json
{
  "id": "17889615814797564"
}
```

### Step 2 — Publish Story Container

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media_publish
  ?creation_id=17889615814797564
  &access_token={access-token}
```

Response:

```json
{
  "id": "17854360229135495"
}
```

---

## Carousel Publish (3-step)

Carousels support a mix of images and videos, up to 10 items. The entire carousel counts as a single post against the 50/24h rate limit. All items are cropped to match the aspect ratio of the first item; the default aspect ratio is 1:1.

### Step 1a — Create Item Containers

Create one container per carousel item. Repeat this call for each image or video.

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `image_url` | string | Yes (image) | Publicly accessible URL of the image |
| `video_url` | string | Yes (video) | Publicly accessible URL of the video |
| `is_carousel_item` | boolean | Yes | Must be `true` |
| `access_token` | string | Yes | User access token |

Example — image item:

```
POST https://graph.facebook.com/v22.0/17841400008460056/media
  ?image_url=https%3A%2F%2Fexample.com%2Fslide1.jpg
  &is_carousel_item=true
  &access_token={access-token}
```

Response:

```json
{
  "id": "17889615814797571"
}
```

Example — video item:

```
POST https://graph.facebook.com/v22.0/17841400008460056/media
  ?video_url=https%3A%2F%2Fexample.com%2Fslide2.mp4
  &is_carousel_item=true
  &access_token={access-token}
```

Response:

```json
{
  "id": "17889615814797572"
}
```

Repeat for all items. For video items, check each container's `status_code` and wait for `FINISHED` before proceeding.

### Step 1b — Create Carousel Container

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `media_type` | string | Yes | Must be `CAROUSEL` |
| `children` | JSON array | Yes | Array of item container IDs, in display order |
| `caption` | string | No | Post caption, max 2200 chars, 30 hashtags, 20 @tags |
| `location_id` | string | No | Facebook Page ID for location tagging |
| `access_token` | string | Yes | User access token |

Example request:

```
POST https://graph.facebook.com/v22.0/17841400008460056/media
  ?media_type=CAROUSEL
  &children=%5B%2217889615814797571%22%2C%2217889615814797572%22%5D
  &caption=Check%20out%20these%20photos%20%23carousel
  &access_token={access-token}
```

Response:

```json
{
  "id": "17889615814797580"
}
```

### Step 2 — Publish Carousel Container

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media_publish
  ?creation_id=17889615814797580
  &access_token={access-token}
```

Response:

```json
{
  "id": "17854360229135500"
}
```

---

## Resumable Upload Protocol

Use resumable uploads for large video files. The upload occurs via `rupload.facebook.com` independently from the Graph API host.

### Step 1 — Create Container with Resumable Flag

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `media_type` | string | Yes | Must be `REELS` |
| `upload_type` | string | Yes | Must be `resumable` |
| `caption` | string | No | Post caption |
| `access_token` | string | Yes | User access token |

Example request:

```
POST https://graph.facebook.com/v22.0/17841400008460056/media
  ?media_type=REELS
  &upload_type=resumable
  &caption=My%20uploaded%20reel
  &access_token={access-token}
```

Response:

```json
{
  "id": "17889615814797590",
  "uri": "https://rupload.facebook.com/ig-api-upload/v22.0/17889615814797590"
}
```

The `uri` field contains the upload endpoint for the next step.

### Step 2 — Upload the Video File

Send the binary file data to the URI returned in Step 1.

```
POST https://rupload.facebook.com/ig-api-upload/v22.0/{ig-container-id}
```

| Header | Value | Description |
|---|---|---|
| `Authorization` | `OAuth {user-access-token}` | User access token |
| `offset` | `0` | Byte offset; set to current position when resuming |
| `file_size` | `{total-bytes}` | Total size of the file in bytes |

Body: raw binary file data.

Example request headers:

```
POST https://rupload.facebook.com/ig-api-upload/v22.0/17889615814797590
Authorization: OAuth {access-token}
offset: 0
file_size: 52428800
```

To resume an interrupted upload, set the `offset` header to the last successfully uploaded byte position and send the remaining bytes.

Response (success):

```json
{
  "success": true
}
```

### Step 3 — Check Status and Publish

After the upload completes, check the container `status_code` as described above, then publish using the standard `media_publish` endpoint:

```
POST https://graph.facebook.com/v22.0/{ig-user-id}/media_publish
  ?creation_id=17889615814797590
  &access_token={access-token}
```

---

## Content Publishing Limit Endpoint

Check current quota usage before publishing to avoid hitting the 50/24h rate limit.

```
GET https://graph.facebook.com/v22.0/{ig-user-id}/content_publishing_limit
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `fields` | string | Yes | Comma-separated fields to return; use `quota_usage,config` |
| `since` | integer | No | Unix timestamp; max 24 hours ago; scopes `quota_usage` to this window |
| `access_token` | string | Yes | User access token |

Example request:

```
GET https://graph.facebook.com/v22.0/17841400008460056/content_publishing_limit
  ?fields=quota_usage%2Cconfig
  &since=1711000000
  &access_token={access-token}
```

Response:

```json
{
  "data": [
    {
      "quota_usage": 2,
      "config": {
        "quota_total": 50,
        "quota_duration": 86400
      }
    }
  ]
}
```

Response fields:

| Field | Type | Description |
|---|---|---|
| `quota_usage` | integer | Number of containers published since the `since` timestamp |
| `config.quota_total` | integer | Maximum allowed posts per window (50) |
| `config.quota_duration` | integer | Duration of the quota window in seconds (86400 = 24 hours) |

---

## Media Specifications

| Type | Format | Max Size | Aspect Ratio | Max Duration | Notes |
|---|---|---|---|---|---|
| Feed Image | JPEG | 8 MB | 4:5 to 1.91:1 | — | Min 320px wide, max 1440px wide |
| Feed Video | MOV / MP4 | 1 GB | 4:5 to 1.91:1 | 60 min | H.264 or HEVC codec; AAC audio |
| Reel | MOV / MP4 | 300 MB | 9:16 recommended | 15 min (min 3s) | H.264 or HEVC codec |
| Story Image | JPEG | 8 MB | 9:16 recommended | — | sRGB color space |
| Story Video | MOV / MP4 | 100 MB | 9:16 recommended | 60s (min 3s) | H.264 or HEVC codec |
| Carousel Item Image | JPEG | 8 MB | Matches first item | — | Cropped to first item's ratio |
| Carousel Item Video | MOV / MP4 | 1 GB | Matches first item | 60 min | Cropped to first item's ratio |

Caption limits:

| Limit | Value |
|---|---|
| Max characters | 2200 |
| Max hashtags | 30 |
| Max @mentions | 20 |

---

## Publishing Requirements

Before calling `media_publish`, ensure the following conditions are met:

- The container `status_code` must be `FINISHED` (for video and reel containers).
- If the connected Facebook Page requires Page Publishing Authorization (PPA), the user must complete PPA before publishing.
- If the connected Facebook Page requires two-factor authentication (2FA), the user must complete 2FA before publishing.
- The container must not be expired (containers expire 24 hours after creation).
