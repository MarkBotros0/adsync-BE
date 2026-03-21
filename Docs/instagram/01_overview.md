# Instagram Platform API — Overview

Version: v22.0
Last updated: 2026-03-21

---

## Contents

1. [API Variants](#api-variants)
2. [Versioning](#versioning)
3. [Base URLs](#base-urls)
4. [Access Levels](#access-levels)
5. [Node Types](#node-types)
6. [Field Selection](#field-selection)
7. [Pagination](#pagination)
8. [Batch Requests](#batch-requests)
9. [Rate Limits](#rate-limits)
10. [Important Notes](#important-notes)

---

## API Variants

The Instagram Platform offers two active API configurations. The choice of configuration depends on whether the Instagram account is linked to a Facebook Page.

### Instagram API with Instagram Login

Designed for Instagram professional accounts that are **not** connected to a Facebook Page. Users authenticate using their Instagram credentials.

| Property | Value |
|---|---|
| Target accounts | Instagram-only professional accounts (Business or Creator) |
| Authentication | Instagram credentials |
| Access token type | Instagram User |
| Base URL | `graph.instagram.com` |

**Required scopes:**

| Scope | Purpose |
|---|---|
| `instagram_business_basic` | Read profile and media |
| `instagram_business_content_publish` | Publish media |
| `instagram_business_manage_messages` | Read and send direct messages |
| `instagram_business_manage_comments` | Read and manage comments |

---

### Instagram API with Facebook Login for Business

Designed for Instagram professional accounts that **are** linked to a Facebook Page. Users authenticate using their Facebook credentials.

| Property | Value |
|---|---|
| Target accounts | Instagram accounts linked to Facebook Pages |
| Authentication | Facebook credentials |
| Access token type | Facebook User or Page |
| Base URL | `graph.facebook.com` |

**Required permissions:**

| Permission | Purpose |
|---|---|
| `instagram_basic` | Read profile and media |
| `instagram_content_publish` | Publish media |
| `instagram_manage_comments` | Read and manage comments |
| `instagram_manage_messages` | Read and send direct messages |
| `instagram_manage_insights` | Read account and media insights |

---

### Instagram Basic Display API — DEPRECATED

> **Warning:** Meta has retired the Instagram Basic Display API. All URLs previously associated with this API now redirect to the Instagram Platform hub. Do not use this API for any new or existing integrations.

---

## Versioning

The Instagram Platform follows the same versioning cadence as the broader Meta Graph API. Two new versions are released per year, in February and September. Each version is supported for two years after release.

| Version | Release | End of Support |
|---|---|---|
| v22.0 (current) | Feb 2025 | Feb 2027 |
| v21.0 | Sep 2024 | Sep 2026 |
| v20.0 | May 2024 | May 2026 |
| v19.0 | Feb 2024 | Feb 2026 |

The version is specified as a path segment in every API request. All examples in this documentation use **v22.0**.

---

## Base URLs

| Use case | Base URL |
|---|---|
| Facebook Login (general) | `https://graph.facebook.com/v22.0/` |
| Instagram Login (general) | `https://graph.instagram.com/v22.0/` |
| Video uploads (resumable) | `https://rupload.facebook.com/ig-api-upload/v22.0/` |

Use the base URL that corresponds to the API variant your app is using. Video and reel uploads use the dedicated resumable upload endpoint regardless of login method.

---

## Access Levels

Apps accessing the Instagram Platform are granted one of two access levels. The access level determines the scope of data the app can read and which accounts it can interact with.

| Access Level | Description | Requirements |
|---|---|---|
| Standard Access | Default level. Limited data. Suitable for testing against your own accounts. | None beyond app creation |
| Advanced Access | Required for apps that access data belonging to users other than the app owner. Unlocks full data access. | App Review + Business Verification |

Apps intended for production use with third-party Instagram accounts must complete App Review and Business Verification to obtain Advanced Access.

---

## Node Types

The Instagram Graph API models Instagram content and accounts as typed nodes. Each node type exposes a specific set of fields and edges.

| Node Type | Description |
|---|---|
| IG User | An Instagram Business or Creator account. The primary node for account-level operations. |
| IG Media | A single piece of media: photo, video, reel, carousel, or story. |
| IG Comment | A comment posted on an IG Media object. |
| IG Container | An unpublished media container created during the two-step publishing workflow. |
| IG Hashtag | An Instagram hashtag. Used to search and retrieve top or recent media for a tag. |

### The `/me` Endpoint

The `/me` endpoint is a shortcut that resolves to the Instagram professional account associated with the current access token.

```
GET https://graph.instagram.com/v22.0/me?fields=id,username&access_token=<TOKEN>
```

```
GET https://graph.facebook.com/v22.0/me?fields=id,username&access_token=<TOKEN>
```

Use the appropriate base URL for your API variant.

---

## Field Selection

By default, API responses include only a minimal set of default fields. Use the `fields` query parameter to request specific fields and traverse edges.

**Syntax:**

```
GET /v22.0/{node-id}?fields=field1,field2,nested_edge{field1,field2}
```

**Example — fetch an IG User's ID, username, and first page of media with captions:**

```
GET https://graph.facebook.com/v22.0/{ig-user-id}
  ?fields=id,username,media{id,caption,media_type}
  &access_token=<TOKEN>
```

**Example — fetch an IG Media object's timestamp and like count:**

```
GET https://graph.instagram.com/v22.0/{media-id}
  ?fields=id,timestamp,like_count
  &access_token=<TOKEN>
```

Nested edge traversal uses curly brace syntax (`edge{field1,field2}`). Multiple fields are comma-separated with no spaces.

---

## Pagination

Collections returned by edge requests are paginated. The Instagram Platform supports two pagination strategies.

### Cursor-based Pagination (Default)

Most edges return cursor-based pagination. The response includes a `paging` object with cursor values and convenience URLs.

**Response structure:**

```json
{
  "data": [ ... ],
  "paging": {
    "cursors": {
      "before": "<BEFORE_CURSOR>",
      "after": "<AFTER_CURSOR>"
    },
    "next": "https://graph.facebook.com/v22.0/...",
    "previous": "https://graph.facebook.com/v22.0/..."
  }
}
```

| Field | Description |
|---|---|
| `data` | Array of results for the current page |
| `paging.cursors.before` | Cursor pointing to the start of the current page |
| `paging.cursors.after` | Cursor pointing to the end of the current page; pass as `after` to fetch the next page |
| `paging.next` | Full URL for the next page (absent when on the last page) |
| `paging.previous` | Full URL for the previous page (absent when on the first page) |

**Fetching the next page:**

```
GET https://graph.facebook.com/v22.0/{ig-user-id}/media
  ?after=<AFTER_CURSOR>
  &access_token=<TOKEN>
```

### Time-based Pagination (User Insights Only)

The User Insights edge supports time-based pagination using Unix timestamps.

| Parameter | Description |
|---|---|
| `since` | Unix timestamp. Return results after this time. |
| `until` | Unix timestamp. Return results before this time. |

**Example:**

```
GET https://graph.facebook.com/v22.0/{ig-user-id}/insights
  ?metric=impressions,reach
  &since=1700000000
  &until=1702678400
  &access_token=<TOKEN>
```

### Page Size

Use the `limit` parameter to control the number of results per page.

```
GET https://graph.facebook.com/v22.0/{ig-user-id}/media?limit=10&access_token=<TOKEN>
```

---

## Batch Requests

Multiple API calls can be combined into a single HTTP request using the batch endpoint. This reduces network overhead when making several independent calls.

**Endpoint:**

```
POST https://graph.facebook.com/v22.0/
```

**Parameters:**

| Parameter | Description |
|---|---|
| `access_token` | A valid access token |
| `batch` | JSON array of request objects. Each object must include `method` and `relative_url`. |

**Request object fields:**

| Field | Required | Description |
|---|---|---|
| `method` | Yes | HTTP method: `GET`, `POST`, or `DELETE` |
| `relative_url` | Yes | The API path and query string, relative to the versioned base URL |
| `body` | No | For `POST` requests, a URL-encoded string of body parameters |

**Example — fetch profile and media in a single request:**

```
POST https://graph.facebook.com/v22.0/
  ?access_token=<TOKEN>
  &batch=[
    {"method":"GET","relative_url":"me?fields=id,username"},
    {"method":"GET","relative_url":"<IG_USER_ID>/media"}
  ]
```

**Constraints:**

- Maximum **50 requests** per batch call.
- Each request in the batch is subject to its own rate limit accounting.
- Responses are returned as a JSON array in the same order as the request array.

---

## Rate Limits

The Instagram Platform applies rate limits at the app and account level. Exceeding a rate limit returns an error with code `4` or `32`. Implement exponential backoff when handling these errors.

### Standard Endpoints

| Metric | Limit |
|---|---|
| API calls | 4,800 calls per 24 hours, multiplied by the number of impressions on the connected account |

The rolling 24-hour window resets continuously, not at a fixed time.

### Messaging Endpoints

| Endpoint type | Limit |
|---|---|
| Conversations | 2 calls per second per account |
| Private Replies — Live | 100 calls per second |
| Private Replies — Posts and Reels | 750 calls per hour |
| Send API — Text and links | 100 calls per second |
| Send API — Audio and video | 10 calls per second |

---

## Important Notes

The following constraints and policies apply across the Instagram Platform. Review these before designing your integration.

| Topic | Detail |
|---|---|
| Consumer accounts | The Instagram Platform cannot be used to access standard (non-professional) Instagram consumer accounts. Only Business and Creator accounts are supported. |
| Stories publishing | Publishing Stories via the API is limited to Instagram Business accounts. Creator accounts cannot publish Stories through the API. |
| Result ordering | Result ordering is not supported. The order of items returned in collections is not guaranteed and cannot be controlled via query parameters. |
| Bot disclosure | Automated messaging implementations must disclose bot status to users where required by applicable law. Check local regulations before deploying automated messaging. |
| Basic Display API | The Instagram Basic Display API has been retired by Meta. Do not use it. Existing references to that API's endpoints will redirect to the Instagram Platform hub. |
| App Review | Apps that access data for users other than the app owner must complete Meta's App Review process and obtain Advanced Access before going to production. |
