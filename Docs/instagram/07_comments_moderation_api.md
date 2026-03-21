# Instagram Comments Moderation API

API Version: v22.0

---

## Overview

The Instagram Graph API provides full comment lifecycle management: reading, creating, replying, hiding, deleting, and monitoring comments via webhooks. All endpoints require a valid user access token with the appropriate permissions scoped to the authenticated Instagram Business or Creator account.

---

## IG Comment Node

The IG Comment node represents a single comment or reply on an IG Media object.

**Endpoint**

```
GET /v22.0/{ig-comment-id}?fields={fields}&access_token={token}
```

**Host URLs**

| Host | Usage |
|------|-------|
| `graph.instagram.com` | Instagram Login flows |
| `graph.facebook.com` | Facebook Login flows |

---

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique comment ID |
| `text` | string | Comment text content |
| `timestamp` | string | ISO 8601 creation timestamp |
| `username` | string | Instagram username of the commenter |
| `from` | object | IG User who created the comment — contains `id` and `username` |
| `hidden` | boolean | Whether the comment is currently hidden |
| `like_count` | integer | Number of likes on the comment |
| `media` | object | The IG Media object the comment is on |
| `parent_id` | string | ID of the parent comment (present only if this is a reply) |
| `legacy_instagram_comment_id` | string | Marketing API comment ID used in v21.0 and older |

---

## Permissions

### Instagram Login

| Permission | Purpose |
|------------|---------|
| `instagram_business_basic` | Read basic account and media data |
| `instagram_business_manage_comments` | Read, hide, delete, and reply to comments |

### Facebook Login

| Permission | Purpose |
|------------|---------|
| `instagram_basic` | Read basic Instagram account data |
| `instagram_manage_comments` | Read, hide, delete, and reply to comments |
| `pages_read_engagement` | Read page and media engagement data |
| `ads_management` | Required if the user's role is granted via Business Manager (alternative: `ads_read`) |
| `ads_read` | Alternative to `ads_management` for Business Manager role-based access |

---

## Reading Comments

### Read All Comments on a Media Object

Returns top-level comments on an IG Media object. Results are returned in reverse chronological order (API v3.2 and later). Use the `replies` field to expand threaded replies inline.

```
GET /v22.0/{ig-media-id}/comments
  ?fields=id,text,timestamp,username,like_count,hidden,replies{id,text,username,timestamp}
  &access_token={token}
```

**Response**

```json
{
  "data": [
    {
      "id": "17870913679156914",
      "text": "Great post!",
      "timestamp": "2024-01-15T10:00:00+0000",
      "username": "someuser"
    }
  ]
}
```

**Pagination Notes**

| Behavior | Detail |
|----------|--------|
| Order | Reverse chronological (newest first), API v3.2+ |
| Page size | Maximum 50 comments per request |
| Scope | Top-level comments only by default |
| Replies | Include `replies` field to expand threaded replies |
| Timestamp filtering | Not supported — cannot filter by date range |

### Read a Single Comment

Retrieve full detail for a specific comment by its ID.

```
GET /v22.0/{ig-comment-id}
  ?fields=id,text,timestamp,username,from,hidden,like_count,parent_id
  &access_token={token}
```

**Response**

```json
{
  "id": "17870913679156914",
  "text": "Great post!",
  "timestamp": "2024-01-15T10:00:00+0000",
  "username": "someuser",
  "from": {
    "id": "17841400008460056",
    "username": "someuser"
  },
  "hidden": false,
  "like_count": 3,
  "parent_id": null
}
```

### Reading Limitations

| Limitation | Detail |
|------------|--------|
| Age-gated media | Comments on age-gated media are not returned |
| Restricted users | Comments from restricted IG Users are not returned unless the user has been unrestricted and approved |
| Live video | Comments are only available during an active broadcast; historical live comments are not accessible |

---

## Replying to Comments

### Reply to a Comment Directly

Creates a sub-comment (reply) on an existing comment. The reply appears threaded under the parent comment.

```
POST /v22.0/{ig-comment-id}/replies
  ?message={reply-text}
  &access_token={token}
```

**Response**

```json
{
  "id": "{ig-comment-id}"
}
```

### Reply via Mentions Endpoint (Caption or Comment @Mention)

When your account is @mentioned in a caption, reply to the media object:

```
POST /v22.0/{ig-user-id}/mentions
  ?commented_media_id={media-id}
  &message={reply-text}
  &access_token={token}
```

When your account is @mentioned in a specific comment, reply to that comment:

```
POST /v22.0/{ig-user-id}/mentions
  ?comment_id={comment-id}
  &message={reply-text}
  &access_token={token}
```

**Response**

```json
{
  "id": "{ig-comment-id}"
}
```

---

## Creating Comments

Post a new top-level comment on your own IG Media object.

```
POST /v22.0/{ig-media-id}/comments
  ?message={comment-text}
  &access_token={token}
```

**Response**

```json
{
  "id": "{ig-comment-id}"
}
```

**Note:** Creating comments is not supported on live video IG Media objects.

---

## Hiding and Unhiding Comments

The media owner can hide or unhide any comment on their media. Hidden comments remain visible to the commenter but are hidden from other users.

**Hide a comment**

```
POST /v22.0/{ig-comment-id}?hide=true&access_token={token}
```

**Unhide a comment**

```
POST /v22.0/{ig-comment-id}?hide=false&access_token={token}
```

**Response**

```json
{
  "success": true
}
```

**Limitations**

| Limitation | Detail |
|------------|--------|
| Authorization | Only the media owner can hide or unhide comments |
| Owner comments | Comments made by the media owner always display regardless of the `hide` setting |

---

## Deleting Comments

Permanently delete a comment. This action cannot be undone.

```
DELETE /v22.0/{ig-comment-id}?access_token={token}
```

**Response**

```json
{
  "success": true
}
```

**Requirements**

| Requirement | Detail |
|-------------|--------|
| Authorization | Only the comment author or the media owner can delete a comment |
| Token type | Requires a user access token from the comment creator or the media owner |

---

## Enabling and Disabling Comments on Media

Toggle comment availability on a specific IG Media object. When disabled, no new comments can be posted.

**Enable comments**

```
POST /v22.0/{ig-media-id}?comment_enabled=true&access_token={token}
```

**Disable comments**

```
POST /v22.0/{ig-media-id}?comment_enabled=false&access_token={token}
```

**Response**

```json
{
  "success": true
}
```

**Note:** Enabling or disabling comments is not supported for live video IG Media objects.

---

## Non-Organic Comments (Ads)

Comments on Instagram ads are a different comment type from organic media comments and cannot be managed through the standard IG Media Comments edge.

To manage comments on ad-associated IG Media:

1. Retrieve the ad's `effective_instagram_media_id` field via the Marketing API.
2. Use that media ID with the Marketing API's comment endpoints, not the Instagram Graph API comments edge.

| Scenario | Endpoint to Use |
|----------|-----------------|
| Organic media comments | `GET /v22.0/{ig-media-id}/comments` |
| Ad-associated media comments | Marketing API using `effective_instagram_media_id` |

---

## Mentions Handling

When your account is @mentioned in another user's caption or comment, Instagram sends a webhook notification (see [Comment Webhooks](#comment-webhooks)). You can then fetch the mentioned content using the `mentioned_comment` or `mentioned_media` fields on the IG User node.

### Check a Mentioned Comment

Retrieve the comment in which your account was @mentioned:

```
GET /v22.0/{ig-user-id}
  ?fields=mentioned_comment.comment_id({comment-id}){text,timestamp,username}
  &access_token={token}
```

**Response**

```json
{
  "mentioned_comment": {
    "text": "Hey @youraccount, check this out!",
    "timestamp": "2024-01-15T10:00:00+0000",
    "username": "anotheruser"
  },
  "id": "{ig-user-id}"
}
```

### Check a Mentioned Media (Caption Mention)

Retrieve the media whose caption @mentions your account:

```
GET /v22.0/{ig-user-id}
  ?fields=mentioned_media.media_id({media-id}){caption,media_type,timestamp}
  &access_token={token}
```

**Response**

```json
{
  "mentioned_media": {
    "caption": "Check out @youraccount's work!",
    "media_type": "IMAGE",
    "timestamp": "2024-01-15T09:30:00+0000"
  },
  "id": "{ig-user-id}"
}
```

### Available Fields for `mentioned_media`

| Field | Description |
|-------|-------------|
| `caption` | Media caption text |
| `comments` | Comments on the media |
| `comments_count` | Total number of comments |
| `id` | Media ID |
| `like_count` | Number of likes |
| `media_type` | Media type (IMAGE, VIDEO, CAROUSEL_ALBUM) |
| `media_url` | URL of the media asset |
| `owner` | IG User who owns the media |
| `timestamp` | ISO 8601 creation timestamp |
| `username` | Username of the media owner |

### Mention Limitations

| Limitation | Detail |
|------------|--------|
| Story mentions | Not supported — story @mention notifications are not available via this API |
| Private accounts | Webhooks are not sent for mentions in private account media |
| Tagged photos | Commenting on tagged photos is not supported via the mentions endpoint |

---

## Comment Webhooks

Subscribe to webhook fields to receive real-time push notifications when comment activity occurs on your account's media.

### Webhook Field Subscriptions

| Webhook Field | Triggers On |
|---------------|-------------|
| `comments` | New comments on your media |
| `mentions` | @mention of your account in a caption or comment |
| `live_comments` | Comments posted during a live video broadcast |

### Requirements

| Requirement | Detail |
|-------------|--------|
| Access level | Advanced Access required |
| Permission (Instagram Login) | `instagram_business_manage_comments` |
| Permission (Facebook Login) | `instagram_manage_comments` |
| Account visibility | Account must be public to receive comment notifications |
| App status | App must be in Live status |

### Webhook Payload Example (comments field)

```json
{
  "object": "instagram",
  "entry": [
    {
      "id": "{ig-user-id}",
      "time": 1234567890,
      "changes": [
        {
          "field": "comments",
          "value": {
            "from": {
              "id": "17841400008460056",
              "username": "commenter"
            },
            "media": {
              "id": "17870913679156914",
              "media_product_type": "FEED"
            },
            "id": "{comment-id}",
            "text": "Great post!"
          }
        }
      ]
    }
  ]
}
```

### Webhook Payload Fields

| Field | Description |
|-------|-------------|
| `object` | Always `"instagram"` for Instagram webhooks |
| `entry[].id` | The IG User ID of the account that received the notification |
| `entry[].time` | Unix timestamp of when the event was triggered |
| `changes[].field` | The subscribed field that triggered the notification (`comments`, `mentions`, `live_comments`) |
| `changes[].value.from` | Object containing `id` and `username` of the commenter |
| `changes[].value.media` | Object containing `id` and `media_product_type` of the media commented on |
| `changes[].value.id` | The comment ID |
| `changes[].value.text` | The comment text |
