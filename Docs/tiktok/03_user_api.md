# TikTok API — User Info

## Endpoint

| | |
|-|-|
| **Method** | GET |
| **URL** | `https://open.tiktokapis.com/v2/user/info/` |
| **Auth** | Bearer access token (user OAuth token) |
| **Rate Limit** | 600 req/min (sliding window) |
| **Min Scope** | `user.info.basic` |

---

## Request

### Headers

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| Authorization | string | Yes | `Bearer {access_token}` |

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| fields | string | Yes | Comma-separated list of user fields to return |

### Example Request

```bash
curl -L -X GET 'https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,avatar_url_100,avatar_large_url,display_name,bio_description,profile_deep_link,is_verified,username,follower_count,following_count,likes_count,video_count' \
  -H 'Authorization: Bearer act.example12345Example12345Example'
```

---

## Response Fields — Complete List

| Field | Type | Required Scope | Description |
|-------|------|---------------|-------------|
| open_id | string | user.info.basic | Unique identification of the user within this application |
| union_id | string | user.info.basic | Unique identification across all apps under the same developer account |
| avatar_url | string | user.info.basic | URL to user's profile image |
| avatar_url_100 | string | user.info.basic | URL to user's profile image at 100×100 pixels |
| avatar_large_url | string | user.info.basic | URL to user's profile image at higher resolution |
| display_name | string | user.info.basic | User's display name on TikTok |
| bio_description | string | user.info.profile | User's bio description text |
| profile_deep_link | string | user.info.profile | Deep link URL to user's TikTok profile page |
| is_verified | boolean | user.info.profile | Whether TikTok has provided a verified badge |
| username | string | user.info.profile | User's unique @username on TikTok |
| follower_count | int64 | user.info.stats | Number of followers |
| following_count | int64 | user.info.stats | Number of accounts the user follows |
| likes_count | int64 | user.info.stats | Total likes across all of the user's videos |
| video_count | int64 | user.info.stats | Total number of publicly posted videos |

---

## Response Format

```json
{
  "data": {
    "user": {
      "open_id": "723f24d7-e717-40f8-a2b6-cb8464cd23b4",
      "union_id": "c9c60f44-a68e-4f5d-84dd-ce22faeb0ba1",
      "avatar_url": "https://p19-sign.tiktokcdn-us.com/...",
      "avatar_url_100": "https://p19-sign.tiktokcdn-us.com/...",
      "avatar_large_url": "https://p19-sign.tiktokcdn-us.com/...",
      "display_name": "Example User",
      "bio_description": "Hello world",
      "profile_deep_link": "https://www.tiktok.com/@example",
      "is_verified": false,
      "username": "example",
      "follower_count": 1000,
      "following_count": 500,
      "likes_count": 5000,
      "video_count": 42
    }
  },
  "error": {
    "code": "ok",
    "message": "",
    "log_id": "20220829194722CBE87ED59D524E727021"
  }
}
```

---

## Required Scopes by Field Group

| Scope | Fields Unlocked |
|-------|----------------|
| user.info.basic | open_id, union_id, avatar_url, avatar_url_100, avatar_large_url, display_name |
| user.info.profile | bio_description, profile_deep_link, is_verified, username |
| user.info.stats | follower_count, following_count, likes_count, video_count |

Minimum required scope to call the endpoint: `user.info.basic`. Fields from other scopes are only returned if the user has authorized those scopes.

---

## open_id vs union_id

| Identifier | Scope | Description |
|------------|-------|-------------|
| open_id | Per-app | Unique to the user within your specific application. The same TikTok user has a different open_id in each of your apps. |
| union_id | Cross-app | Unique to the user across all apps under the same developer account. Use this to identify the same user across multiple apps you own. |
