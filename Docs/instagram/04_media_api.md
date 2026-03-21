# IG Media Node

API version: v22.0

The IG Media node represents a single Instagram media object — a photo, video, reel, story, or carousel album. It provides access to media metadata, engagement metrics, comments, product tags, and publishing controls.

---

## Endpoint

```
GET /v22.0/{ig-media-id}
```

**Host URLs**

| Host | Usage |
|------|-------|
| `graph.instagram.com` | Instagram Login (limited permissions) |
| `graph.facebook.com` | Facebook Login (full permissions) |

---

## Media Types

The API surfaces media type information through two separate fields.

### `media_type`

Reflects the structural format of the media object.

| Value | Description |
|-------|-------------|
| `IMAGE` | Single photo |
| `VIDEO` | Single video |
| `CAROUSEL_ALBUM` | Album containing multiple photos and/or videos |

### `media_product_type`

Reflects the surface or placement where the media was published.

| Value | Description |
|-------|-------------|
| `AD` | Paid advertisement |
| `FEED` | Standard feed post |
| `STORY` | Story (ephemeral, 24-hour lifespan) |
| `REELS` | Short-form Reel |

A video posted to the feed has `media_type = VIDEO` and `media_product_type = FEED`. A Reel has `media_type = VIDEO` and `media_product_type = REELS`.

---

## Fields

Fields are requested via the `fields` query parameter. If no fields are specified, only `id` is returned by default.

```
GET /v22.0/{ig-media-id}?fields=id,media_type,media_url,caption,timestamp&access_token={token}
```

| Field | Type | Description |
|-------|------|-------------|
| `alt_text` | string | Descriptive alt text for the image |
| `boost_ads_list` | array | Instagram ad information; Facebook Login only |
| `boost_eligibility_info` | object | Details on whether the media is eligible to be boosted |
| `caption` | string | Post caption; `@` mentions are stripped unless the requesting app user is an admin |
| `comments_count` | integer | Total number of comments on the media |
| `copyright_check_information.status` | string | Status returned by copyright detection on the media |
| `id` | string | Unique media ID |
| `is_comment_enabled` | boolean | Whether comments are currently enabled on the media |
| `is_shared_to_feed` | boolean | For Reels: whether the reel also appears in the main Feed tab and the Reels tab |
| `legacy_instagram_media_id` | string | Media ID used by the Marketing API in v21.0 and older |
| `like_count` | integer | Number of likes on the media |
| `media_product_type` | enum | Publication surface: `AD`, `FEED`, `STORY`, `REELS` |
| `media_type` | enum | Structural format: `CAROUSEL_ALBUM`, `IMAGE`, `VIDEO` |
| `media_url` | string | URL of the media asset |
| `owner` | object | App-scoped User ID of the account that created the media |
| `permalink` | string | Permanent public URL to the Instagram post |
| `shortcode` | string | Shortcode identifier used in the Instagram URL |
| `thumbnail_url` | string | Thumbnail image URL for video media |
| `timestamp` | string | ISO 8601 datetime of when the media was created |
| `username` | string | Instagram username of the media creator |
| `view_count` | integer | Number of views; applicable to Reels |

**Example request — multiple fields:**

```
GET /v22.0/17854360229135492
  ?fields=id,caption,media_type,media_product_type,media_url,permalink,timestamp,like_count,comments_count
  &access_token={token}
```

**Example response:**

```json
{
  "id": "17854360229135492",
  "caption": "Morning light over the city.",
  "media_type": "IMAGE",
  "media_product_type": "FEED",
  "media_url": "https://cdninstagram.com/...",
  "permalink": "https://www.instagram.com/p/ABC123/",
  "timestamp": "2026-03-21T08:30:00+0000",
  "like_count": 412,
  "comments_count": 17
}
```

---

## Edges

| Edge | Endpoint | Description |
|------|----------|-------------|
| `children` | `GET /v22.0/{ig-media-id}/children` | Returns the individual image and video items within a carousel album |
| `collaborators` | `GET /v22.0/{ig-media-id}/collaborators` | Returns collaborator users tagged in the post; Facebook Login only |
| `comments` | `GET /v22.0/{ig-media-id}/comments` | Returns comments posted on the media |
| `insights` | `GET /v22.0/{ig-media-id}/insights` | Returns interaction and reach metrics for the media |

---

## Required Permissions

| Permission | Requirement |
|------------|-------------|
| `instagram_business_basic` or `instagram_basic` | Required for all media reads |
| `pages_read_engagement` | Required for all media reads |
| `ads_management` or `ads_read` | Required only when the user has been granted an ad role via Business Manager |

---

## Updating a Media Object

Use a POST request to enable or disable comments on a media object.

```
POST /v22.0/{ig-media-id}?comment_enabled=true&access_token={token}
```

```
POST /v22.0/{ig-media-id}?comment_enabled=false&access_token={token}
```

**Notes:**
- Updating is not supported on live video media.
- The only supported update operation is toggling `comment_enabled`.

**Example response:**

```json
{
  "success": true
}
```

---

## Deleting a Media Object

```
DELETE /v22.0/{ig-media-id}?access_token={token}
```

**Requirements and limitations:**

| Condition | Detail |
|-----------|--------|
| Login type | Facebook Login only; Instagram Login is not supported |
| Supported types | Non-ad feed posts, stories, reels, carousel albums |
| Carousel deletion | Deletes the entire album; individual carousel child items cannot be deleted separately |
| Ad media | Media associated with an active ad cannot be deleted |

**Example response:**

```json
{
  "success": true
}
```

---

## Carousel Children Edge

Returns the individual IG Media objects (images and/or videos) contained within a carousel album.

```
GET /v22.0/{ig-media-id}/children
  ?fields=id,media_type,media_url
  &access_token={token}
```

The response is an array of media objects. Only carousel albums (`media_type = CAROUSEL_ALBUM`) have children; requesting this edge on other media types returns an empty data array.

**Example response:**

```json
{
  "data": [
    {
      "id": "17846368219941196",
      "media_type": "IMAGE",
      "media_url": "https://cdninstagram.com/..."
    },
    {
      "id": "17846368219941197",
      "media_type": "VIDEO",
      "media_url": "https://cdninstagram.com/..."
    }
  ]
}
```

---

## Media Specifications

### Images

| Property | Specification |
|----------|---------------|
| Format | JPEG only (MPO and JPS are not supported) |
| Max file size | 8 MB |
| Aspect ratio | 4:5 (portrait) to 1.91:1 (landscape) |
| Min width | 320 px |
| Max width | 1440 px |
| Min height (1:1 aspect ratio) | 320 px |
| Color space | sRGB |

---

### Videos (Feed)

| Property | Specification |
|----------|---------------|
| Container | MOV or MP4 (MPEG-4 Part 14) |
| Video codec | HEVC or H264 |
| Audio codec | AAC |
| Max audio sample rate | 48 kHz |
| Audio channels | Mono or stereo |
| Frame rate | 23–60 FPS |
| Max bitrate | 25 Mbps |
| Max duration | 60 minutes |
| Max file size | 1 GB |
| Min dimension | 320 px |
| Max dimension | 1440 px |

---

### Reels

| Property | Specification |
|----------|---------------|
| Container | MOV or MP4 |
| Video codec | HEVC or H264 |
| Audio codec | AAC |
| Max audio sample rate | 48 kHz |
| Audio channels | Mono or stereo |
| Frame rate | 23–60 FPS |
| Max bitrate | 25 Mbps |
| Min duration | 3 seconds |
| Max duration | 15 minutes |
| Max file size | 300 MB |
| Recommended aspect ratio | 9:16 |
| Cover photo format | JPEG |
| Cover photo max file size | 8 MB |
| Cover photo recommended aspect ratio | 9:16 |

---

### Stories — Images

| Property | Specification |
|----------|---------------|
| Format | JPEG |
| Max file size | 8 MB |
| Recommended aspect ratio | 9:16 |
| Color space | sRGB |

---

### Stories — Videos

| Property | Specification |
|----------|---------------|
| Container | MOV or MP4 |
| Video codec | HEVC or H264 |
| Audio codec | AAC |
| Max audio sample rate | 48 kHz |
| Frame rate | 23–60 FPS |
| Max bitrate | 25 Mbps |
| Min duration | 3 seconds |
| Max duration | 60 seconds |
| Max file size | 100 MB |

---

### Carousel Albums

| Property | Specification |
|----------|---------------|
| Max items | 10 (images and videos can be mixed) |
| Aspect ratio | All items are cropped to match the first item's aspect ratio |
| Default aspect ratio | 1:1 |
| Publishing limit impact | Counts as a single post against the daily publishing limit |

---

## Comments Edge

### Reading Comments

```
GET /v22.0/{ig-media-id}/comments
  ?fields=id,text,timestamp,username
  &access_token={token}
```

**Behavior and limitations:**

| Property | Detail |
|----------|--------|
| Order | Reverse chronological (newest first); v3.2 and later |
| Max results per query | 50 comments |
| Scope | Top-level comments only |
| Replies | Use the `replies` field on an IG Comment node to expand threaded replies |
| Timestamp filtering | Not supported |

**Example response:**

```json
{
  "data": [
    {
      "id": "17858893269000001",
      "text": "Great shot!",
      "timestamp": "2026-03-21T09:15:00+0000",
      "username": "jane_doe"
    },
    {
      "id": "17858893269000002",
      "text": "Love the colors.",
      "timestamp": "2026-03-21T08:55:00+0000",
      "username": "john_smith"
    }
  ]
}
```

### Creating a Comment

Post a new top-level comment on a media object.

```
POST /v22.0/{ig-media-id}/comments
  ?message={text}
  &access_token={token}
```

**Example response:**

```json
{
  "id": "17858893269000099"
}
```

**Notes:**
- Creating comments is not supported on live video media.
- The `message` parameter must be URL-encoded.

---

## Product Tags Edge

Product tagging requires an approved Instagram Shop with an associated product catalog. Creator accounts and Stories, IGTV, Live, and Mentions media are not supported.

**Required permissions:**

| Permission | Purpose |
|------------|---------|
| `catalog_management` | Access to the product catalog |
| `instagram_shopping_tag_products` | Permission to tag products in media |
| `instagram_basic` | Basic media access |

### Creating or Updating Product Tags

Tags are additive. If a `product_id` already exists on the media, the operation updates its coordinates rather than creating a duplicate.

```
POST /v22.0/{ig-media-id}/product_tags
  ?updated_tags=[{"product_id":"3231775643511089","x":0.5,"y":0.8}]
  &access_token={token}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `product_id` | string | ID of the product in the catalog |
| `x` | float | Horizontal position of the tag as a decimal (0.0–1.0, left to right) |
| `y` | float | Vertical position of the tag as a decimal (0.0–1.0, top to bottom) |

**Limits:**
- Maximum 5 product tags per media object.

**Example response:**

```json
{
  "success": true
}
```

### Reading Product Tags

```
GET /v22.0/{ig-media-id}/product_tags&access_token={token}
```

**Example response:**

```json
{
  "data": [
    {
      "product_id": 3231775643511089,
      "merchant_id": 90010177253934,
      "name": "Test Product",
      "price_string": "$10.00",
      "image_url": "https://images.example.com/product.jpg",
      "review_status": "approved",
      "is_checkout": true,
      "stripped_price_string": "10.00",
      "string_sale_price_string": "",
      "x": 0.5,
      "y": 0.8
    }
  ]
}
```

**Response fields per tag:**

| Field | Description |
|-------|-------------|
| `product_id` | Catalog product ID |
| `merchant_id` | ID of the merchant who owns the product |
| `name` | Product display name |
| `price_string` | Formatted price string including currency symbol |
| `image_url` | URL of the product image |
| `review_status` | Current review state of the product tag |
| `is_checkout` | Whether the product supports in-app checkout |
| `stripped_price_string` | Price without currency symbol |
| `string_sale_price_string` | Sale price as a string, if applicable |
| `x` | Horizontal tag position (0.0–1.0) |
| `y` | Vertical tag position (0.0–1.0) |

**`review_status` values:**

| Value | Meaning |
|-------|---------|
| `approved` | Product is approved for tagging |
| `rejected` | Product has been rejected |
| `pending` | Review is in progress |
| `outdated` | Product information has changed since last review |
| *(empty)* | No review has been initiated |

---

## Mentions on Media

To retrieve metadata for media in which the business account has been mentioned (via `@username` in a caption or comment), query the IG User node using the `mentioned_media` field.

```
GET /v22.0/{ig-user-id}
  ?fields=mentioned_media.media_id({media-id}){caption,media_type,timestamp}
  &access_token={token}
```

**Available fields when querying via `mentioned_media`:**

| Field | Description |
|-------|-------------|
| `caption` | Caption of the media containing the mention |
| `comments` | Comments on the media |
| `comments_count` | Total number of comments |
| `id` | Media ID |
| `like_count` | Number of likes |
| `media_type` | Structural format: `CAROUSEL_ALBUM`, `IMAGE`, or `VIDEO` |
| `media_url` | URL of the media asset |
| `owner` | App-scoped User ID of the account that created the media |
| `timestamp` | ISO 8601 creation datetime |
| `username` | Username of the media creator |

**Example request:**

```
GET /v22.0/17841400008460056
  ?fields=mentioned_media.media_id(17854360229135492){id,caption,media_type,media_url,timestamp,username}
  &access_token={token}
```

**Example response:**

```json
{
  "mentioned_media": {
    "id": "17854360229135492",
    "caption": "Check out @yourbrand for more!",
    "media_type": "IMAGE",
    "media_url": "https://cdninstagram.com/...",
    "timestamp": "2026-03-20T14:22:00+0000",
    "username": "another_user"
  },
  "id": "17841400008460056"
}
```
