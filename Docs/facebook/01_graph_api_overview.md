# Facebook Graph API — Overview & Core Concepts

Source: developers.facebook.com/docs/graph-api
Version: v22.0 (Feb 2025)

---

## Versioning

| Version | Released | Deprecated |
|---------|----------|------------|
| v22.0 | Feb 2025 | Feb 2027 |
| v21.0 | Sep 2024 | Sep 2026 |
| v20.0 | May 2024 | May 2026 |
| v19.0 | Feb 2024 | Feb 2026 |
| v18.0 | Sep 2023 | Sep 2025 |
| v17.0 | May 2023 | May 2025 |

- Two new versions per year (Feb and Sep).
- Each version supported for 2 years.
- Always specify version in URL: `/v22.0/`
- Unversioned calls default to the oldest available version — avoid.

---

## Base URLs

```
https://graph.facebook.com/v22.0/          # All API calls
https://graph-video.facebook.com/v22.0/    # Video uploads only
```

All requests require HTTPS. Pass `access_token` as a query param or `Authorization: Bearer {token}` header.

---

## Node Types

Nodes are individual objects identified by a unique ID.

| Node | ID Format | Description |
|------|-----------|-------------|
| User | Numeric or `me` | Facebook user account |
| Page | Numeric | Facebook Page |
| Post | `{user-id}_{post-id}` | Post/status update |
| Photo | Numeric | Photo object |
| Video | Numeric | Video object |
| Album | Numeric | Photo album |
| Event | Numeric | Facebook event |
| Group | Numeric | Facebook Group |
| Comment | `{object-id}_{comment-id}` | Comment on an object |
| Application | Numeric | Facebook App |
| Ad Account | `act_{ad-account-id}` | Advertising account |
| Campaign | Numeric | Ad campaign |
| Ad Set | Numeric | Ad set within campaign |
| Ad | Numeric | Individual ad |
| Ad Creative | Numeric | Creative content for an ad |
| Business | Numeric | Business Manager account |
| IG User | Numeric | Instagram professional account |
| IG Media | Numeric | Instagram post/media item |
| Custom Audience | Numeric | Targeting audience |
| Pixel | Numeric | Meta Pixel |
| Lead Ad Form | Numeric | Lead generation form |
| Catalog | Numeric | Product catalog |

### Special Nodes
```
GET /v22.0/me        # Resolves to user/page of current access token
GET /v22.0/app       # Resolves to app of current app access token
```

---

## Edge Types

Edges represent connections between nodes: `/{node-id}/{edge-name}`

### User Edges
| Edge | Description |
|------|-------------|
| `/me/accounts` | Pages managed by user |
| `/me/feed` | Posts on the user's timeline |
| `/me/posts` | Posts made by the user |
| `/me/photos` | Photos uploaded or tagged |
| `/me/videos` | Videos uploaded or tagged |
| `/me/friends` | Friends who use the app |
| `/me/likes` | Pages the user liked |
| `/me/permissions` | Permissions granted to the app |
| `/me/picture` | Profile picture |

### Page Edges
| Edge | Description |
|------|-------------|
| `/page/feed` | All posts on the page timeline |
| `/page/posts` | Posts by the page |
| `/page/published_posts` | All published posts |
| `/page/scheduled_posts` | Scheduled posts |
| `/page/photos` | Photos |
| `/page/videos` | Videos |
| `/page/events` | Events |
| `/page/insights` | Analytics metrics |
| `/page/conversations` | Messenger threads |
| `/page/leadgen_forms` | Lead generation forms |
| `/page/subscribed_apps` | Webhook subscriptions |
| `/page/roles` | Admin roles |
| `/page/ratings` | Reviews |
| `/page/albums` | Photo albums |
| `/page/live_videos` | Live broadcasts |

### Post Edges
| Edge | Description |
|------|-------------|
| `/post/comments` | Comments |
| `/post/likes` | Users who liked |
| `/post/reactions` | All reactions |
| `/post/attachments` | Attached media |
| `/post/insights` | Post analytics |
| `/post/sharedposts` | Posts that shared this |

### Ad Account Edges
| Edge | Description |
|------|-------------|
| `/act_{id}/campaigns` | Campaigns |
| `/act_{id}/adsets` | Ad sets |
| `/act_{id}/ads` | Ads |
| `/act_{id}/adcreatives` | Creative assets |
| `/act_{id}/insights` | Reporting |
| `/act_{id}/customaudiences` | Custom audiences |
| `/act_{id}/pixels` | Associated pixels |

---

## Making Requests

### GET — Read Data
```
GET /v22.0/{node-id}?fields=id,name&access_token={token}
```

### POST — Create / Update
```
POST /v22.0/{node-id}/{edge}
Body: field=value&access_token={token}
Returns: {"id": "..."} or {"success": true}
```

### DELETE — Remove
```
DELETE /v22.0/{node-id}?access_token={token}
Returns: {"success": true}
```

---

## Field Selection

Without `fields`, the API returns a default subset. Always specify:
```
GET /v22.0/me?fields=id,name,email,picture
```

### Nested Fields (Field Expansion)
```
GET /v22.0/me?fields=id,name,picture{url,width,height}
GET /v22.0/me?fields=posts{id,message,created_time}
GET /v22.0/me?fields=posts.limit(5){message,comments.limit(3){message,from}}
```

### Edge Filtering Inline
```
GET /v22.0/me?fields=posts.since(1680000000).until(1682592000).limit(5){message}
```

### Summary on Edges
```
GET /v22.0/{post-id}/likes?summary=true
# Returns: {"data": [...], "summary": {"total_count": 1234}}
```

### Introspection
```
GET /v22.0/{node-id}?metadata=1
# Returns all available fields, connections, types for this node
# Note: deprecated in v25.0+
```

---

## Pagination

### Cursor-Based (Most Common)
```json
{
  "data": [ ... ],
  "paging": {
    "cursors": { "before": "YWxpZmF...", "after": "MTAxNTEx..." },
    "previous": "https://graph.facebook.com/...",
    "next": "https://graph.facebook.com/..."
  }
}
```
Parameters: `limit`, `after`, `before`
- `limit`: results per page (default varies; often 25, max often 100)
- `after`: get next page
- `before`: get previous page
- If `next` is absent, you are on the last page.

### Time-Based
```json
{
  "data": [ ... ],
  "paging": {
    "previous": "https://graph.facebook.com/...?since=1364849754",
    "next": "https://graph.facebook.com/...?until=1364587774"
  }
}
```
Parameters: `since` (Unix timestamp), `until` (Unix timestamp), `limit`

### Offset-Based
Parameters: `offset`, `limit`
Warning: unreliable for frequently-changing data; prefer cursor-based.

### Best Practices
- Always follow the full `next` URL from the response rather than constructing URLs manually.
- Check for presence of `next` before fetching the next page.
- Max 100 posts per request on `/feed` edge.

---

## Batch Requests

Multiple API calls in one HTTP request. Max 50 requests per batch.

```
POST https://graph.facebook.com/v22.0/
  access_token={token}
  batch=[
    {"method":"GET","relative_url":"me"},
    {"method":"GET","relative_url":"me/friends?limit=50"},
    {"method":"POST","relative_url":"me/feed","body":"message=Hello+World"}
  ]
```

Response: Array of response objects:
```json
[
  {"code": 200, "headers": [...], "body": "{\"id\":\"123\",\"name\":\"John\"}"},
  {"code": 200, "headers": [...], "body": "{\"data\":[...]}"},
  {"code": 200, "headers": [...], "body": "{\"id\":\"post-id\"}"}
]
```

### JSONPath References Between Batch Items
```json
[
  {"method": "GET", "relative_url": "me", "name": "get-user"},
  {"method": "GET", "relative_url": "{result=get-user:$.id}/friends", "depends_on": "get-user"}
]
```

Limits:
- Max 50 requests per batch
- Each sub-request counts against rate limits
- Total timeout: ~60 seconds

---

## Rate Limits

### Application-Level (Standard Graph API)
- **Formula:** `200 × Number of Daily Active Users` per rolling 1-hour window
- Tracked per app

### Rate Limit Response Headers
| Header | Description |
|--------|-------------|
| `X-App-Usage` | `{"call_count": 28, "total_time": 25, "total_cputime": 25}` — percentages (0-100) |
| `X-Page-Usage` | Same format, for page token calls |
| `X-Ad-Account-Usage` | `{"acc_id_util_pct": 9.67}` |
| `X-Business-Use-Case-Usage` | BUC limits for Messenger, Marketing, Pages APIs |

When any value approaches 100, throttling begins.

### Business Use Case (BUC) Rate Limits
| API | Limit (Advanced Access) |
|-----|------------------------|
| Ads Insights | `190,000 + 400 × active ads` per hour |
| Ads Management | `100,000 + 40 × active ads` per hour |
| Pages API | `4,800 × engaged users` per 24 hours |
| Messenger | `200 × engaged users` per 24 hours |

### Rate Limit Error Codes
| Code | Meaning |
|------|---------|
| 4 | App rate limit exceeded |
| 17 | User rate limit exceeded |
| 32 | Page-level throttling |
| 613 | Custom rate limit breached |
| 80001–80014 | BUC rate limits |

### Backoff Strategy
- Stop making calls immediately when rate limited — additional calls increase the backoff window.
- Check `estimated_time_to_regain_access` in `X-Business-Use-Case-Usage` header.
- Use exponential backoff with jitter for retryable errors (codes 1, 2, 4, 17, 32).

---

## Error Codes

### Error Response Format
```json
{
  "error": {
    "message": "Human-readable error message",
    "type": "OAuthException",
    "code": 190,
    "error_subcode": 460,
    "error_user_title": "Session Expired",
    "error_user_msg": "Please log in again.",
    "fbtrace_id": "AbCdEfGhIj"
  }
}
```

### Error Types
| Type | Description |
|------|-------------|
| `OAuthException` | OAuth/token related |
| `GraphMethodException` | Invalid method or endpoint |
| `GraphInvalidID` | Invalid object ID |
| `GraphThrottledException` | Rate limit exceeded |

### Primary Error Codes
| Code | Type | Description | Action |
|------|------|-------------|--------|
| 1 | GraphMethodException | API unknown | Retry with backoff |
| 2 | GraphMethodException | API service error | Retry with backoff |
| 4 | OAuthException | App call limit reached | Back off |
| 10 | OAuthException | App lacks permission | Check app permissions |
| 17 | OAuthException | User call limit reached | Back off |
| 32 | OAuthException | Page-level throttle | Back off |
| 100 | GraphMethodException | Invalid parameter | Fix request |
| 104 | OAuthException | Incorrect appsecret_proof | Fix HMAC |
| 190 | OAuthException | Invalid access token | Refresh/reacquire |
| 200–299 | OAuthException | Permission errors | Request permission |
| 368 | OAuthException | Temporarily blocked | Review policies |
| 613 | OAuthException | Rate limit | Back off |

### Error 190 Subcodes (Token Issues)
| Subcode | Description | Action |
|---------|-------------|--------|
| 460 | Password changed | Force re-login |
| 461 | User logged out | Force re-login |
| 463 | Session expired | Refresh token |
| 464 | Session invalidated | Force re-login |
| 467 | Token expired | Re-authenticate |
| 492 | App removed by user | Force re-login |

### HTTP Status Codes
| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Bad request / invalid params |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not found |
| 429 | Rate limited |
| 500 | Facebook-side error |

---

## appsecret_proof

When "Require App Secret" is enabled in App Settings → Advanced, all server-side calls must include `appsecret_proof`.

```python
import hmac, hashlib
appsecret_proof = hmac.new(
    key=app_secret.encode('utf-8'),
    msg=access_token.encode('utf-8'),
    digestmod=hashlib.sha256
).hexdigest()
```

```
GET /v22.0/me?access_token={token}&appsecret_proof={proof}
```

---

## Search

```
GET /v22.0/search?type={type}&q={query}&fields={fields}&access_token={token}
```

| `type` | Searches for |
|--------|-------------|
| `page` | Facebook Pages |
| `event` | Public events |
| `group` | Public groups |
| `place` | Locations/places |
| `user` | Users (very restricted) |

Place search with location:
```
GET /v22.0/search?type=place&q=coffee&center=37.76,-122.427&distance=1000
```

---

## Checking Granted Permissions

```
GET /v22.0/me/permissions?access_token={token}
```
```json
{
  "data": [
    {"permission": "email", "status": "granted"},
    {"permission": "user_birthday", "status": "declined"}
  ]
}
```

Revoke a permission:
```
DELETE /v22.0/me/permissions/{permission-name}?access_token={token}
```
