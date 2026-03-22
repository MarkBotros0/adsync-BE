# TikTok API — Webhooks & Error Codes

## Webhooks Overview

TikTok webhooks deliver event-driven notifications to your server when events occur on TikTok.

> "Webhook is a subscription that notifies your application via a callback URL when an event happens in TikTok."

- Payload format: HTTPS POST in JSON format
- Callback URL must be registered in the Developer Portal (during app creation or afterward)
- Callback URL must use HTTPS

### Setup

1. Register the callback URL in the Developer Portal under your app settings.
2. Implement a handler that responds with HTTP 200 immediately upon receipt.
3. Process the event asynchronously after acknowledging receipt.

### Delivery & Retry

- **At-least-once delivery**: The same event may be delivered more than once — implement idempotent event processing using event ID deduplication.
- **Retry on failure**: If HTTP 200 is not returned, TikTok retries for up to **72 hours** using exponential backoff.
- **Acknowledgement**: Must respond with HTTP 200 status code immediately.

### Payload Format

```json
{
  "event": "event_type_name",
  "create_time": 1651392000,
  "data": { ... }
}
```

### Known Event Types

TikTok webhook events vary by API product and are registered per-app. The table below describes the general model; consult the documentation for the specific API product (e.g., Content Posting API, Login Kit) for its exact event type strings.

| Event Field Value | Product | Description |
|-------------------|---------|-------------|
| (product-specific) | Content Posting API | Notifies of video publish status changes |
| (product-specific) | Login Kit | Notifies of user authorization changes |
| (product-specific) | Other API products | See per-product webhook documentation |

### Signature Verification

Verify webhook authenticity before processing any payload. TikTok includes a signature header with each request. Validate by computing an HMAC of the raw request payload using your `client_secret` and comparing the result to the signature header value.

```python
import hmac
import hashlib

def verify_webhook_signature(payload_bytes: bytes, client_secret: str, received_signature: str) -> bool:
    computed = hmac.new(
        client_secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, received_signature)
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| GET /v2/user/info/ | 600 requests | Per minute (sliding window) |
| POST /v2/video/list/ | 600 requests | Per minute (sliding window) |
| POST /v2/video/query/ | 600 requests | Per minute (sliding window) |
| POST /v2/post/publish/video/init/ | 6 requests | Per minute per access token |
| POST /v2/post/publish/inbox/video/init/ | 6 requests | Per minute per access token |
| Calculation method | 1-minute sliding window | — |
| Exceeded response | HTTP 429 | error code: `rate_limit_exceeded` |

**Increasing limits**: Contact TikTok via the support page for review and potential increases for high-volume applications.

---

## Error Response Format

All API errors use this structure:

```json
{
  "data": {},
  "error": {
    "code": "invalid_params",
    "message": "One or more fields in request is invalid.",
    "log_id": "20220829194722CBE87ED59D524E727021"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `error.code` | string | Machine-readable error identifier |
| `error.message` | string | Human-readable description |
| `error.log_id` | string | Unique request ID — include when contacting support |

---

## Error Codes — Complete Reference

### Success

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `ok` | 200 | Request succeeded |

### Authentication Errors

| Code | HTTP Status | Description | Action |
|------|-------------|-------------|--------|
| `access_token_invalid` | 401 | The access token is invalid or not found in the request. | Refresh the token using `refresh_token` and retry. |
| `scope_not_authorized` | 401 | The user did not authorize the scope required for completing this request. | Re-initiate the OAuth flow requesting the needed scope. |
| `scope_permission_missed` | 400 | Access token is valid but the requested fields require additional scopes. | Check the error message for which scope is missing; re-authorize. |

### Request Errors

| Code | HTTP Status | Description | Action |
|------|-------------|-------------|--------|
| `invalid_params` | 400 | One or more fields in request is invalid. | Review the error message for specific field details. |
| `invalid_file_upload` | 400 | The uploaded file does not meet API specifications. | Correct the file format or size and retry. |

### Content Posting Errors

| Code | HTTP Status | Description | Action |
|------|-------------|-------------|--------|
| `spam_risk_too_many_posts` | 403 | Creator has exceeded posting frequency limits. | Reduce posting frequency; retry later. |
| `spam_risk_too_many_pending_share` | 403 | Maximum 5 pending inbox shares within any 24-hour period. | Wait for existing drafts to be posted or deleted. |
| `user_banned_from_posting` | 403 | Creator account is banned from posting content. | Creator must resolve the account issue with TikTok directly. |
| `unaudited_client_can_only_post_to_private_accounts` | 403 | App has not completed API audit; all posts are forced to `SELF_ONLY`. | Complete TikTok's API audit process for public posting. |
| `url_ownership_unverified` | 403 | Domain not verified for the `PULL_FROM_URL` method. | Register and verify the domain in Developer Portal app settings. |

### Rate Limiting

| Code | HTTP Status | Description | Action |
|------|-------------|-------------|--------|
| `rate_limit_exceeded` | 429 | The API rate limit was exceeded. | Implement exponential backoff; retry after a delay. |

### Server Errors

| Code | HTTP Status | Description | Action |
|------|-------------|-------------|--------|
| `internal_error` | 500 | TikTok internal server error. | Refer to the error message; retry with backoff; contact TikTok support if the error persists. |

### Upload HTTP Status Codes (Chunk Upload)

| HTTP Status | Description | Action |
|-------------|-------------|--------|
| 201 Created | All chunks uploaded; processing begins. | Poll `/status/fetch/` for publish status. |
| 206 Partial Content | Chunk accepted; more chunks needed. | Continue uploading remaining chunks. |
| 400 Bad Request | Malformed headers or byte size mismatch. | Check `Content-Range` and `Content-Length` headers. |
| 403 Forbidden | `upload_url` has expired (valid for 1 hour only). | Re-initialize the post to obtain a new `upload_url`. |
| 416 Range Not Satisfiable | `Content-Range` does not match upload progress. | Verify byte offsets match the previously uploaded amount. |

---

## Retry Strategy

```
Attempt 1:  immediate
Attempt 2:  wait 1 second
Attempt 3:  wait 2 seconds
Attempt 4:  wait 4 seconds
Attempt N:  wait 2^(N-2) seconds (exponential backoff)
Max retries: application-defined (TikTok retries webhooks for 72 hours)
```

**Retry on:**

- HTTP 429 (rate limit) — always retry with backoff
- HTTP 5xx (server errors) — retry with backoff
- Network timeouts — retry with backoff

**Do NOT retry on:**

- HTTP 400 (bad request) — fix the request parameters
- HTTP 401 (unauthorized) — refresh the token, then retry
- HTTP 403 (forbidden) — fix permissions or the app audit issue

```python
import time
import requests

def request_with_retry(method: str, url: str, max_attempts: int = 5, **kwargs):
    for attempt in range(1, max_attempts + 1):
        response = requests.request(method, url, **kwargs)
        if response.status_code in (429,) or response.status_code >= 500:
            if attempt == max_attempts:
                response.raise_for_status()
            wait = 2 ** (attempt - 2) if attempt > 1 else 0
            time.sleep(wait)
            continue
        return response
    return response
```

---

## Sandbox vs. Production Differences

| Aspect | Sandbox | Production |
|--------|---------|------------|
| Posting | All posts forced to `SELF_ONLY` | Respects `privacy_level` setting |
| Audit required | No | Yes (for public posting via Content Posting API) |
| Test users | Available in Developer Portal | Real TikTok users |
| Rate limits | Same limits apply | Same limits apply |
| Webhooks | Deliverable to HTTPS callback | Deliverable to HTTPS callback |
| Access tokens | Test tokens via sandbox users | Real user OAuth tokens |
