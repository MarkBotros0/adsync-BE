# Instagram User API (IG User Node)

## Overview

The IG User node represents an Instagram professional (business or creator) account. It provides access to profile data, media, analytics, and specialized APIs for hashtags, mentions, and business discovery.

API version used throughout this document: **v22.0**

---

## Host URLs

| Login Method | Host URL |
|---|---|
| Instagram Login | `graph.instagram.com` |
| Facebook Login | `graph.facebook.com` |

---

## IG User Node

### Endpoint

```
GET /v22.0/{ig-user-id}
```

Alternatively, resolve to the current token's IG User:

```
GET /v22.0/me
```

### Required Permissions

- `instagram_business_basic` OR `instagram_basic`
- `pages_read_engagement`
- `ads_management` or `ads_read` (if role was granted via Business Manager)

### Example Request

```
GET /v22.0/17841405822304914
  ?fields=id,username,name,biography,followers_count,media_count
  &access_token={access-token}
```

### Example Response

```json
{
  "id": "17841405822304914",
  "username": "examplebrand",
  "name": "Example Brand",
  "biography": "Official account of Example Brand.",
  "followers_count": 48200,
  "media_count": 312
}
```

---

## Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | App-scoped User ID |
| `name` | string | Profile display name |
| `username` | string | Profile username |
| `biography` | string | Profile bio text |
| `profile_picture_url` | string | Profile picture URL |
| `website` | string | Website URL from profile |
| `followers_count` | integer | Total number of followers |
| `follows_count` | integer | Number of accounts the user follows |
| `media_count` | integer | Total number of published media objects |
| `has_profile_pic` | boolean | Whether the account has a profile picture |
| `is_published` | boolean | Account publication status |
| `alt_text` | string | Descriptive text for images (accessibility) |
| `shopping_product_tag_eligibility` | boolean | Whether the account is eligible for Instagram Shopping product tags |
| `legacy_instagram_user_id` | string | Marketing API user ID; applicable for v21.0 and older |

---

## Edges

| Edge | Description |
|---|---|
| `media` | IG Media objects published to the account feed (not stories) |
| `stories` | Active story IG Media objects (24-hour window) |
| `live_media` | Live video IG Media objects |
| `insights` | Account-level analytics |
| `mentions` | IG Media where the account is @mentioned in a caption |
| `mentioned_comment` | Comments where the account is @mentioned |
| `mentioned_media` | Media where the account is @mentioned in a caption |
| `tags` | IG Media where the account has been tagged by other users |
| `content_publishing_limit` | Current publishing quota usage |
| `recently_searched_hashtags` | Hashtags searched within the last 7 days |
| `business_discovery` | Access public data of other professional accounts |
| `agencies` | Agency relationships |
| `authorized_adaccounts` | Ad accounts authorized for this user |
| `connected_threads_user` | Connected Threads platform user |
| `instagram_backed_threads_user` | Instagram-backed Threads user |
| `media_publish` | Publish an IG Container as a media post |
| `upcoming_events` | Upcoming events associated with the account |
| `collaboration_invites` | Collaboration invitations |

---

## Media Edge

### Endpoint

```
GET /v22.0/{ig-user-id}/media
```

Returns all IG Media objects published to the account feed. Stories are excluded; use the `/stories` edge for those.

### Limits and Pagination

- Returns a maximum of 10,000 of the most recently created media objects.
- Supports time-based pagination using `since` and `until` Unix timestamps.
- Cursor-based pagination is also supported via `before` and `after` cursors.

### Example Request

```
GET /v22.0/17841405822304914/media
  ?fields=id,caption,media_type,timestamp
  &access_token={access-token}
```

### Example Response

```json
{
  "data": [
    {
      "id": "17895695668004550",
      "caption": "Check out our latest product launch!",
      "media_type": "IMAGE",
      "timestamp": "2024-01-15T10:00:00+0000"
    },
    {
      "id": "17895695668004551",
      "caption": "Behind the scenes at HQ.",
      "media_type": "VIDEO",
      "timestamp": "2024-01-12T14:30:00+0000"
    }
  ],
  "paging": {
    "cursors": {
      "before": "QVFIUm...",
      "after": "QVFIUm..."
    },
    "next": "https://graph.instagram.com/v22.0/17841405822304914/media?after=QVFIUm..."
  }
}
```

### Time-Based Pagination Example

```
GET /v22.0/17841405822304914/media
  ?fields=id,caption,timestamp
  &since=1704067200
  &until=1706745599
  &access_token={access-token}
```

---

## Stories Edge

### Endpoint

```
GET /v22.0/{ig-user-id}/stories
```

Returns active story IG Media objects for the account. Only stories within the current 24-hour window are returned.

### Limitations

- Live Video stories are not returned.
- Reshared stories are not returned.
- Only one caption per story is returned.

### Example Request

```
GET /v22.0/17841405822304914/stories
  ?fields=id,media_type,timestamp,media_url
  &access_token={access-token}
```

### Example Response

```json
{
  "data": [
    {
      "id": "17858893269000001",
      "media_type": "IMAGE",
      "timestamp": "2024-01-15T08:00:00+0000",
      "media_url": "https://..."
    }
  ]
}
```

---

## Tags Edge

### Endpoint

```
GET /v22.0/{ig-user-id}/tags
```

Returns IG Media objects where the authenticated user has been tagged by another user.

### Required Permissions

- `instagram_basic`
- `instagram_manage_comments`
- `pages_read_engagement`

### Pagination Notes

- Uses cursor-based pagination.
- `previous` and `next` fields are not returned; cursors must be constructed manually using the `before` and `after` cursor values.

### Example Request

```
GET /v22.0/17841405822304914/tags
  ?fields=id,media_type,timestamp,permalink
  &access_token={access-token}
```

### Example Response

```json
{
  "data": [
    {
      "id": "17895695000000001",
      "media_type": "IMAGE",
      "timestamp": "2024-01-10T12:00:00+0000",
      "permalink": "https://www.instagram.com/p/abc123/"
    }
  ],
  "paging": {
    "cursors": {
      "before": "QVFIUm...",
      "after": "QVFIUm..."
    }
  }
}
```

### Limitations

- Private media belonging to other users is not returned.

---

## Business Discovery API

The Business Discovery API allows an authenticated professional account to look up public data for other Instagram professional accounts by username.

### Endpoint

```
GET /v22.0/{ig-user-id}?fields=business_discovery.fields({field,field,...})
```

The `{ig-user-id}` is the ID of the authenticated user making the request. The target account is specified via a `username` field inside the `business_discovery` edge.

### Example — Look Up Another Account

```
GET /v22.0/17841405309211844
  ?fields=business_discovery.fields(username,followers_count,media_count)
  &access_token={access-token}
```

### Example Response

```json
{
  "business_discovery": {
    "username": "targetbrand",
    "followers_count": 125000,
    "media_count": 540
  },
  "id": "17841405309211844"
}
```

### Example — Include Media

```
GET /v22.0/17841405309211844
  ?fields=business_discovery.fields(username,followers_count,media_count,media{caption,media_type})
  &access_token={access-token}
```

### Example Response with Media

```json
{
  "business_discovery": {
    "username": "targetbrand",
    "followers_count": 125000,
    "media_count": 540,
    "media": {
      "data": [
        {
          "caption": "Our new collection is here.",
          "media_type": "IMAGE",
          "id": "17896129349180965"
        }
      ]
    }
  },
  "id": "17841405309211844"
}
```

### Available Fields via `business_discovery`

| Field / Edge | Description |
|---|---|
| `id` | IG User ID of the target account |
| `username` | Target account username |
| `biography` | Target account bio |
| `website` | Target account website |
| `profile_picture_url` | Target account profile picture URL |
| `followers_count` | Target account follower count |
| `media_count` | Target account published media count |
| `media` | Edge: returns the target account's media objects |
| `media.insights` | Public engagement metrics: `comments_count`, `like_count`, `view_count` |

### Limitations

- Age-gated accounts return no data.
- The requesting app user must have a linked Instagram professional account.
- Personal (non-professional) accounts cannot be queried.

---

## Hashtag Search API

The Hashtag Search API allows discovery of public media associated with a hashtag. It operates in four steps.

### Step 1 — Get Hashtag ID

Resolve a hashtag string to its stable IG Hashtag ID.

```
GET /v22.0/ig_hashtag_search
  ?user_id={ig-user-id}
  &q={hashtag-text}
  &access_token={access-token}
```

Example — search for `#travel`:

```
GET /v22.0/ig_hashtag_search
  ?user_id=17841405822304914
  &q=travel
  &access_token={access-token}
```

Response:

```json
{
  "data": [
    {
      "id": "17841593698074073"
    }
  ]
}
```

Note: Do not include the `#` symbol in the `q` parameter.

### Step 2 — Get Hashtag Data

Retrieve metadata for the hashtag using its ID.

```
GET /v22.0/{ig-hashtag-id}
  ?fields=id,name
  &access_token={access-token}
```

Example:

```
GET /v22.0/17841593698074073
  ?fields=id,name
  &access_token={access-token}
```

Response:

```json
{
  "id": "17841593698074073",
  "name": "travel"
}
```

### Step 3 — Get Top Media

Returns the most popular public media for the hashtag.

```
GET /v22.0/{ig-hashtag-id}/top_media
  ?user_id={ig-user-id}
  &fields=id,media_type,permalink
  &access_token={access-token}
```

Example:

```
GET /v22.0/17841593698074073/top_media
  ?user_id=17841405822304914
  &fields=id,media_type,permalink
  &access_token={access-token}
```

Response:

```json
{
  "data": [
    {
      "id": "17896129349180001",
      "media_type": "IMAGE",
      "permalink": "https://www.instagram.com/p/xyz001/"
    },
    {
      "id": "17896129349180002",
      "media_type": "VIDEO",
      "permalink": "https://www.instagram.com/p/xyz002/"
    }
  ]
}
```

### Step 4 — Get Recent Media

Returns the most recently published public media for the hashtag.

```
GET /v22.0/{ig-hashtag-id}/recent_media
  ?user_id={ig-user-id}
  &fields=id,media_type,permalink
  &access_token={access-token}
```

Example:

```
GET /v22.0/17841593698074073/recent_media
  ?user_id=17841405822304914
  &fields=id,media_type,permalink
  &access_token={access-token}
```

Response:

```json
{
  "data": [
    {
      "id": "17896129349190010",
      "media_type": "IMAGE",
      "permalink": "https://www.instagram.com/p/abc010/"
    }
  ],
  "paging": {
    "cursors": {
      "before": "QVFIUm...",
      "after": "QVFIUm..."
    },
    "next": "https://graph.instagram.com/v22.0/17841593698074073/recent_media?after=QVFIUm..."
  }
}
```

### Hashtag API Limits and Restrictions

| Constraint | Detail |
|---|---|
| Unique hashtags per user | Max 30 unique hashtags per IG User per rolling 7-day period |
| Emoji support | Emojis in `q` parameter are not supported |
| Stories hashtags | Not supported |
| Sensitive hashtags | Sensitive or offensive hashtags return a generic error |
| Required feature | Instagram Public Content Access feature must be enabled for the app |
| Required permission | `instagram_basic` |

---

## Recently Searched Hashtags

Retrieve the list of hashtag IDs that the IG User has searched within the last 7 days.

### Endpoint

```
GET /v22.0/{ig-user-id}/recently_searched_hashtags
```

### Example Request

```
GET /v22.0/17841405822304914/recently_searched_hashtags
  ?limit=30
  &access_token={access-token}
```

### Example Response

```json
{
  "data": [
    {"id": "17841593698074073"},
    {"id": "17841563011452226"},
    {"id": "17841574812751225"}
  ]
}
```

### Pagination

- Default page size: 25 hashtag IDs
- Maximum page size: 30 hashtag IDs
- Use the `limit` parameter to set page size up to the maximum

---

## Mentions API

The Mentions API provides access to IG Media and comments where the authenticated IG User has been @mentioned by another user.

### Get a Mentioned Comment

Retrieve fields from a specific comment where the IG User was @mentioned.

```
GET /v22.0/{ig-user-id}
  ?fields=mentioned_comment.comment_id({comment-id}){field,field}
  &access_token={access-token}
```

Example:

```
GET /v22.0/17841405822304914
  ?fields=mentioned_comment.comment_id(17858893269000099){id,text,timestamp}
  &access_token={access-token}
```

Response:

```json
{
  "mentioned_comment": {
    "id": "17858893269000099",
    "text": "@examplebrand great product!",
    "timestamp": "2024-01-14T09:30:00+0000"
  },
  "id": "17841405822304914"
}
```

### Get a Mentioned Media Object

Retrieve fields from a specific media object where the IG User was @mentioned in the caption.

```
GET /v22.0/{ig-user-id}
  ?fields=mentioned_media.media_id({media-id}){field,field}
  &access_token={access-token}
```

Example:

```
GET /v22.0/17841405822304914
  ?fields=mentioned_media.media_id(17896129349180965){id,caption,media_type,like_count,timestamp}
  &access_token={access-token}
```

Response:

```json
{
  "mentioned_media": {
    "id": "17896129349180965",
    "caption": "Loving this product from @examplebrand!",
    "media_type": "IMAGE",
    "like_count": 842,
    "timestamp": "2024-01-13T16:00:00+0000"
  },
  "id": "17841405822304914"
}
```

### Available Fields for `mentioned_media`

| Field | Description |
|---|---|
| `id` | Media object ID |
| `caption` | Caption text |
| `comments` | Comments on the media |
| `comments_count` | Number of comments |
| `like_count` | Number of likes |
| `media_type` | Media type: `IMAGE`, `VIDEO`, `CAROUSEL_ALBUM` |
| `media_url` | URL of the media file |
| `owner` | IG User who owns the media |
| `timestamp` | ISO 8601 publish timestamp |
| `username` | Username of the media owner |

### Reply to a Mention

Post a reply to a comment or caption mention.

```
POST /v22.0/{ig-user-id}/mentions
```

| Parameter | Required | Description |
|---|---|---|
| `media_id` | Yes | ID of the media where the mention occurred |
| `comment_id` | No | ID of the specific comment to reply to (omit to reply to caption mention) |
| `message` | Yes | Text of the reply |

Example — reply to a comment mention:

```
POST /v22.0/17841405822304914/mentions
  ?media_id=17896129349180965
  &comment_id=17858893269000099
  &message=Thanks for the mention!
  &access_token={access-token}
```

### Mentions API Limitations

- Mentions on Stories are not supported.
- Commenting on tagged photos via this API is not supported.
- Webhooks are not sent for mentions on private account media.
