# Instagram API with Instagram Login

## Overview

The Instagram API with Instagram Login allows Instagram professionals (businesses and creators) to use your app to manage their Instagram presence without requiring a linked Facebook Page. This is the newer authentication path introduced by Meta.

Key characteristics:

- Base URL: `graph.instagram.com`
- Token type: Instagram User access token
- Does NOT require Facebook Page linkage
- Cannot access ads or product tagging
- Supports: messaging, media management, comment moderation, @mention identification, insights, and content publishing

This path is distinct from the Facebook Login path and uses a separate set of scopes, endpoints, and token types.

---

## Prerequisites

Before using this API:

- Your Meta app type must be set to **Business** in the Meta App Dashboard
- You must have read the Instagram Platform Overview
- You must implement the Meta login flow (Business Login for Instagram)
- You must have a webhook server implemented if subscribing to real-time events
- Advanced Access requires App Review if your app serves users other than yourself

---

## Scopes

The following permission scopes are available for this API. Always use the new scope values (see Scope Migration below).

| Scope | Description |
|-------|-------------|
| `instagram_business_basic` | Read profile, media, and basic account info |
| `instagram_business_content_publish` | Publish feed posts, reels, and stories |
| `instagram_business_manage_comments` | Read, reply, hide, and delete comments |
| `instagram_business_manage_messages` | Read and send direct messages |

---

## Scope Migration

As of **January 27, 2025**, the following scope values were deprecated. If your app was using the old values, you must migrate to the new ones immediately.

| Old Scope (deprecated Jan 27, 2025) | New Scope |
|--------------------------------------|-----------|
| `business_basic` | `instagram_business_basic` |
| `business_content_publish` | `instagram_business_content_publish` |
| `business_manage_messages` | `instagram_business_manage_messages` |
| `business_manage_comments` | `instagram_business_manage_comments` |

Always use the new `instagram_business_*` scope values in all new and existing integrations.

---

## Getting an Access Token

There are two methods to obtain an Instagram User access token.

### Method 1 — Business Login for Instagram (In-App Flow)

This is the production method for serving external users.

1. Implement the Meta login flow using Business Login for Instagram in your application.
2. The user authenticates via Instagram and grants the requested scopes.
3. You receive a short-lived token valid for **1 hour**.
4. Exchange the short-lived token for a long-lived token valid for **60 days** (see Token Exchange below).

### Method 2 — App Dashboard (Development and Testing)

This method is suitable for development, testing, and managing your own account.

1. Navigate to: **App Dashboard > Instagram > API setup with Instagram business login**
2. Click **Generate token** next to the target Instagram account.
3. Authenticate via Instagram when prompted.
4. Copy the access token displayed — this is a long-lived token valid for **60 days**.

---

## Token Exchange and Refresh

### Exchange a Short-Lived Token for a Long-Lived Token

Short-lived tokens (1 hour) obtained from the in-app login flow can be exchanged for long-lived tokens (60 days).

```
GET https://graph.instagram.com/access_token
  ?grant_type=ig_exchange_token
  &client_id={app-id}
  &client_secret={app-secret}
  &access_token={short-lived-token}
```

| Parameter | Description |
|-----------|-------------|
| `grant_type` | Must be `ig_exchange_token` |
| `client_id` | Your Meta app ID |
| `client_secret` | Your Meta app secret |
| `access_token` | The short-lived Instagram User access token |

### Refresh a Long-Lived Token

Long-lived tokens can be refreshed before they expire to extend their validity by another 60 days. The token must not be expired at the time of the refresh call.

```
GET https://graph.instagram.com/refresh_access_token
  ?grant_type=ig_refresh_token
  &access_token={long-lived-token}
```

| Parameter | Description |
|-----------|-------------|
| `grant_type` | Must be `ig_refresh_token` |
| `access_token` | A valid, non-expired long-lived Instagram User access token |

---

## Getting User Info

Use the `/me` endpoint to retrieve information about the authenticated Instagram user.

```
GET https://graph.instagram.com/v22.0/me
  ?fields=user_id,username,name,account_type,profile_picture_url,followers_count,follows_count,media_count
  &access_token={instagram-user-token}
```

### Available User Fields

| Field | Description |
|-------|-------------|
| `id` | App-scoped user ID |
| `user_id` | The Instagram user ID |
| `username` | The Instagram username |
| `name` | The account display name |
| `account_type` | Account type: `BUSINESS` or `CREATOR` |
| `profile_picture_url` | URL of the profile picture |
| `followers_count` | Number of followers |
| `follows_count` | Number of accounts the user follows |
| `media_count` | Total number of media objects on the account |

### Example Response

```json
{
  "user_id": "17841400000000000",
  "username": "examplebusiness",
  "name": "Example Business",
  "account_type": "BUSINESS",
  "profile_picture_url": "https://example.com/pic.jpg",
  "followers_count": 12400,
  "follows_count": 310,
  "media_count": 204,
  "id": "123456789"
}
```

---

## Accessing Media

Retrieve a list of media objects published by the authenticated user.

```
GET https://graph.instagram.com/v22.0/{ig-user-id}/media
  ?fields=id,caption,media_type,timestamp,permalink
  &access_token={instagram-user-token}
```

| Parameter | Description |
|-----------|-------------|
| `{ig-user-id}` | The Instagram user ID (from the `user_id` field) |
| `fields` | Comma-separated list of media fields to return |
| `access_token` | A valid Instagram User access token |

The response returns an array of IG Media object IDs along with pagination cursors for iterating through results.

### Common Media Fields

| Field | Description |
|-------|-------------|
| `id` | Media object ID |
| `caption` | Caption text |
| `media_type` | `IMAGE`, `VIDEO`, or `CAROUSEL_ALBUM` |
| `timestamp` | ISO 8601 publish timestamp |
| `permalink` | Permanent URL to the post on Instagram |
| `thumbnail_url` | Thumbnail URL (video only) |
| `media_url` | URL of the media asset |

---

## Webhooks with Instagram Login

To receive real-time notifications, subscribe using an Instagram User access token. This is distinct from Facebook-based webhook subscriptions.

```
POST https://graph.instagram.com/v22.0/me/subscribed_apps
  ?subscribed_fields=comments,mentions,story_insights,messages
  &access_token={instagram-user-token}
```

| Parameter | Description |
|-----------|-------------|
| `subscribed_fields` | Comma-separated list of event types to subscribe to |
| `access_token` | A valid Instagram User access token |

### Available Subscribed Fields

| Field | Description |
|-------|-------------|
| `comments` | Notifications when users comment on your media |
| `mentions` | Notifications when your account is @mentioned |
| `story_insights` | Insights data when a story expires |
| `messages` | Incoming direct messages |

---

## Key Differences vs. Facebook Login Path

The Instagram API is also accessible via Facebook Login (using `graph.facebook.com`). The table below summarizes the differences between the two authentication paths.

| Feature | Instagram Login | Facebook Login |
|---------|----------------|----------------|
| Base URL | `graph.instagram.com` | `graph.facebook.com` |
| Token type | Instagram User token | Facebook User or Page token |
| Facebook Page required | No | Yes |
| Ads access | No | Yes |
| Product tagging | No | Yes |
| Permission scopes | `instagram_business_*` | `instagram_basic`, `instagram_content_publish`, etc. |
| Token validity (short-lived) | 1 hour | ~1 hour |
| Token validity (long-lived) | 60 days | 60 days |
| `/me` endpoint | `graph.instagram.com/me` | `graph.facebook.com/me` |
| Hashtag search | Available | Available |
| Business discovery | Available | Available |
| Messaging | Yes | Yes |

Use the Instagram Login path when your users do not have or do not want to connect a Facebook Page. Use the Facebook Login path when your integration requires ads access, product tagging, or Facebook Page-level operations.

---

## App Review Requirements

### Standard Access (Own Accounts Only)

No App Review is required when your app is only used to manage your own Instagram accounts. This applies during development and testing.

### Advanced Access (External Users)

If your app serves users other than yourself, you must obtain Advanced Access for each permission scope through Meta's App Review process.

| Requirement | Details |
|-------------|---------|
| Business verification | Your business must be verified with Meta |
| App Review approval | Required for each permission scope used |
| Scopes requiring review | `instagram_business_manage_comments`, `instagram_business_content_publish`, `instagram_business_manage_messages` |

To submit for App Review, navigate to **App Dashboard > App Review > Permissions and Features** and request the relevant scopes. Each scope submission requires a screencast, sample data, and a written description of how the permission is used.
