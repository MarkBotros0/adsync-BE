# TikTok API — Overview

## API Products

| Product | Description | Auth Type |
|---------|-------------|-----------|
| **Login Kit** | OAuth 2.0 user authentication and identity | User OAuth token |
| **Content Posting API** | Post videos and photos to creator accounts (direct or draft) | User OAuth token (`video.publish` or `video.upload`) |
| **Display API** | Read-only access to user profiles and video metadata for display | User OAuth token |
| **Research API** | Access to TikTok public data for academic/research purposes | Client access token |
| **Data Portability API** | User data export requests (activity, posts, direct messages) | User OAuth token |
| **Commercial Content API** | Ads and advertiser data queries | Client access token |
| **Share Kit** | Video sharing functionality | User OAuth token |

---

## Base URLs

| Purpose | URL |
|---------|-----|
| All v2 API calls | `https://open.tiktokapis.com/v2/` |
| OAuth Authorization (user redirect) | `https://www.tiktok.com/v2/auth/authorize/` |
| Token Management (exchange / refresh / client creds) | `https://open.tiktokapis.com/v2/oauth/token/` |
| Token Revocation | `https://open.tiktokapis.com/v2/oauth/revoke/` |
| TikTok Ads / Marketing API | `https://business-api.tiktok.com/open_api/v1.3/` |

---

## Versioning

- Current version: **v2**
- All endpoints prefixed with `/v2/`
- v1 is deprecated

---

## Environments

| Environment | Host | Notes |
|-------------|------|-------|
| Production | `open.tiktokapis.com` | Live user data and posts |
| Sandbox | `open.tiktokapis.com` (same host) | Sandbox test users from Developer Portal; all Content Posting API posts forced to `SELF_ONLY` |

**Sandbox setup:**
1. Register app on [developers.tiktok.com](https://developers.tiktok.com)
2. Enable sandbox mode in Developer Portal app settings
3. Create sandbox test users to simulate OAuth without real TikTok accounts
4. Unaudited apps: all Content Posting API posts restricted to private (SELF_ONLY) until API audit completes

---

## Request Format

- All requests use **HTTPS**
- Request bodies: **JSON** (`Content-Type: application/json`)
- Token endpoint: **form-encoded** (`Content-Type: application/x-www-form-urlencoded`)
- Authorization header: `Bearer {access_token}`

### Example API Request

```bash
curl -X POST 'https://open.tiktokapis.com/v2/video/list/?fields=id,title,like_count' \
  -H 'Authorization: Bearer act.example12345...' \
  -H 'Content-Type: application/json' \
  -d '{"max_count": 10}'
```

---

## Response Format

All responses use a consistent envelope:

```json
{
  "data": { ... },
  "error": {
    "code": "ok",
    "message": "",
    "log_id": "20220829194722CBE87ED59D524E727021"
  }
}
```

| Field | Description |
|-------|-------------|
| data | Response payload (varies by endpoint) |
| error.code | `"ok"` on success; error string on failure |
| error.message | Human-readable description of the error |
| error.log_id | Unique request identifier — include when contacting TikTok support |

---

## Field Selection

Most endpoints accept a `fields` query parameter:
- Comma-separated list of field names
- Only requested fields are returned (reduces payload size)
- Example: `?fields=open_id,union_id,avatar_url,display_name`

---

## Pagination (Cursor-Based)

| Parameter | Location | Type | Description |
|-----------|----------|------|-------------|
| cursor | Request body | int64 | UTC Unix timestamp in milliseconds. Fetches items before this time. |
| max_count | Request body | int32 | Items per page. Default: 10, max: 20. |
| cursor | Response data | int64 | Pass as cursor in next request to get next page. |
| has_more | Response data | bool | `true` if additional pages exist. |

**Pagination flow:**
```python
cursor = None
while True:
    body = {"max_count": 20}
    if cursor:
        body["cursor"] = cursor
    response = post("/v2/video/list/", body)
    process(response["data"]["videos"])
    if not response["data"]["has_more"]:
        break
    cursor = response["data"]["cursor"]
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `GET /v2/user/info/` | 600 requests | 1-minute sliding window |
| `POST /v2/video/list/` | 600 requests | 1-minute sliding window |
| `POST /v2/video/query/` | 600 requests | 1-minute sliding window |
| `POST /v2/post/publish/video/init/` | 6 requests | Per minute per access token |
| `POST /v2/post/publish/inbox/video/init/` | 6 requests | Per minute per access token |

- Exceeded: HTTP `429`, error code `rate_limit_exceeded`
- Contact TikTok support to request higher limits for high-volume apps

---

## Rate Limit Headers

When a request is rate-limited, TikTok returns HTTP `429` with:
```json
{ "error": { "code": "rate_limit_exceeded", "message": "The API rate limit was exceeded." } }
```

---

## Sandbox Testing Notes

- All posts from unaudited clients restricted to `SELF_ONLY` (private) until API audit completes
- Sandbox test users available in Developer Portal — use to test OAuth flow without real accounts
- Client key and client secret available in app settings
- Same API endpoints used for both sandbox and production — behavior differs based on app audit status
