# Facebook Webhooks, Error Codes & Rate Limits

Source: developers.facebook.com/docs/graph-api/webhooks
Version: v22.0

---

## Webhooks Overview

Webhooks allow your server to receive real-time notifications when data changes on Facebook/Meta platforms, instead of polling the API.

---

## Setup Flow

### Step 1 — Register Your Webhook in App Dashboard

App Dashboard → Your App → Add Product → Webhooks → Subscribe

Or via API:
```
POST /v22.0/{app-id}/subscriptions
  object=page
  callback_url=https://your-server.com/webhook
  verify_token=your_random_verify_token
  fields=feed,messages,mention
  access_token={APP_ACCESS_TOKEN}
```

Parameters:
| Parameter | Required | Description |
|-----------|----------|-------------|
| `object` | Yes | Type of object to subscribe to (`page`, `user`, `instagram`, `whatsapp_business_account`, etc.) |
| `callback_url` | Yes | Your HTTPS endpoint to receive events |
| `verify_token` | Yes | A string you define; used to verify ownership of the endpoint |
| `fields` | Yes | Comma-separated list of subscription fields |

### Step 2 — Handle Verification Handshake (GET)

Facebook sends a GET request to your callback URL to verify ownership:

```
GET https://your-server.com/webhook
  ?hub.mode=subscribe
  &hub.verify_token=your_random_verify_token
  &hub.challenge=RANDOM_INTEGER_STRING
```

Your server must:
1. Verify `hub.mode === 'subscribe'`
2. Verify `hub.verify_token` matches your stored token
3. Respond with HTTP 200 and the plain-text body equal to `hub.challenge`

```python
from flask import request, Response

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == YOUR_VERIFY_TOKEN:
        return Response(challenge, status=200, mimetype='text/plain')
    return Response('Forbidden', status=403)
```

### Step 3 — Handle Incoming Payloads (POST)

Facebook sends POST requests with JSON payloads when subscribed events occur.

**Always verify the payload signature before processing.**

Signature header: `X-Hub-Signature-256: sha256={HMAC_HEX}`

```python
import hmac, hashlib

def verify_signature(payload_body: bytes, signature_header: str, app_secret: str) -> bool:
    if not signature_header.startswith('sha256='):
        return False
    expected_signature = 'sha256=' + hmac.new(
        key=app_secret.encode('utf-8'),
        msg=payload_body,  # raw bytes BEFORE JSON parsing
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature_header, expected_signature)
```

**Critical:** Use `hmac.compare_digest` (timing-safe comparison) and compute HMAC on the **raw request body bytes**, not parsed JSON.

Respond to Facebook's POST with HTTP 200 within **5 seconds**. If your server does not respond within 5 seconds, Facebook marks the delivery as failed and retries.

**Reliability guarantees:**
- **At-least-once delivery**: Facebook may send the same event more than once. Always deduplicate using the message `mid` or change `post_id` to ensure idempotency.
- **No ordering guarantee**: Events may arrive out of order. Use timestamps to sequence events correctly.
- **Retry window**: Facebook retries failed deliveries for up to **5 days** with exponential backoff.

---

## Webhook Payload Structure

```json
{
  "object": "page",
  "entry": [
    {
      "id": "{page-id}",
      "time": 1458692752478,
      "changes": [
        {
          "field": "feed",
          "value": {
            "item": "post",
            "post_id": "...",
            "verb": "add",
            "message": "New post content",
            "created_time": 1458692752
          }
        }
      ],
      "messaging": [
        {
          "sender": {"id": "{sender-psid}"},
          "recipient": {"id": "{page-id}"},
          "timestamp": 1458692752478,
          "message": {
            "mid": "mid.$...",
            "text": "Hello!"
          }
        }
      ]
    }
  ]
}
```

---

## Page Webhook Subscription Fields

Subscribe at: `/{page-id}/subscribed_apps?subscribed_fields={fields}&access_token={PAGE_TOKEN}`

### Content & Feed Fields

| Field | Description |
|-------|-------------|
| `feed` | Nearly all changes to a Page's feed: posts, edits, likes, comments, shares with timestamps |
| `mention` | Page mentioned in posts or comments (includes message text, photos, videos, sender info) |
| `live_videos` | Live video status changes during streaming |
| `videos` | Video encoding status updates for published content |

### Messaging Fields

| Field | Description |
|-------|-------------|
| `messages` | Messages sent to the page |
| `messaging_postbacks` | Postback button interactions from quick replies or buttons |
| `messaging_optins` | Notification message opt-in status changes |
| `messaging_account_linking` | Account linking/unlinking events |
| `messaging_customer_information` | Customer data from commerce screens |
| `messaging_handovers` | Handover Protocol pass thread control events |
| `messaging_integrity` | Message integrity violations |
| `messaging_policy_enforcement` | Policy enforcement action notifications |
| `messaging_referrals` | Referral data (m.me links, ads) |

### Profile Update Fields

| Field | Description |
|-------|-------------|
| `name` | Page name changes |
| `picture` | Profile picture updates |
| `category` | Business category changes |
| `location` | Address/location changes |
| `phone` | Contact phone number changes |
| `email` | Email address changes |
| `website` | Website URL changes |
| `hours` | Business hours changes |

### Commerce & Leads

| Field | Description |
|-------|-------------|
| `leadgen` | Lead form submissions (includes ad ID, form ID, lead ID, timestamp) |
| `send_cart` | Shopping cart operations |
| `product_review` | Product review status changes |

### Ratings

| Field | Description |
|-------|-------------|
| `ratings` | Rating updates (includes star rating, review text, reviewer info, comment interactions) |

---

## Supported Webhook Objects

| Object | Description |
|--------|-------------|
| `user` | User profile field changes |
| `page` | Page feed, messages, profile, leads |
| `permissions` | App permission changes |
| `instagram` | Instagram mentions, comments, story changes |
| `whatsapp_business_account` | WhatsApp messages, statuses, template changes |
| `ad_account` | Ad account changes |
| `application` | App-level events |

---

## Instagram Webhook Fields

Subscribe object `instagram`:

| Field | Description |
|-------|-------------|
| `comments` | Comments on owned media |
| `live_comments` | Live video comments |
| `live_likes` | Live video likes |
| `live_reactions` | Live video reactions |
| `live_mention` | Mentions in live videos |
| `mentions` | @mentions in other media or comments |
| `messages` | Direct messages |
| `messaging_seen` | Message seen events |
| `story_insights` | Story performance metrics (fires when story's 24h window expires; delivers final metrics) |
| `standby` | Handover protocol standby channel events |

### `story_insights` Webhook Payload

Fires automatically when a Story expires; useful for capturing analytics without polling.

```json
{
  "object": "instagram",
  "entry": [{
    "id": "{ig-user-id}",
    "time": 1234567890,
    "changes": [{
      "field": "story_insights",
      "value": {
        "media_id": "17854360229135492",
        "impressions": 100,
        "reach": 80,
        "taps_forward": 40,
        "taps_back": 5,
        "exits": 15,
        "replies": 3
      }
    }]
  }]
}
```

---

## Rate Limits — Complete Reference

### Application-Level Rate Limits (Graph API)

**Standard:**
- `200 × Daily Active Users` calls per rolling 1-hour window, per app
- Tracked per app across all users

**Headers:**
```
X-App-Usage: {"call_count": 28, "total_time": 25, "total_cputime": 25}
```
- Values are percentages (0–100)
- Throttling begins when any value approaches 100

### Page-Level Rate Limits

- `4,800 × Number of Engaged Users` per 24 hours
- Applies to calls made with page access tokens
- **Header:** `X-Page-Usage: {"call_count": 12, "total_time": 8, "total_cputime": 10}`

### Marketing API Rate Limits

| Tier | Calls/Hour |
|------|-----------|
| Development | 1,000 |
| Basic | 10,000 |
| Standard | 50,000 |
| Advanced | Custom |

**Header:** `X-Ad-Account-Usage: {"acc_id_util_pct": 9.67}`

### Business Use Case (BUC) Rate Limits

| API | Limit (Advanced Access) |
|-----|------------------------|
| Ads Insights | `190,000 + 400 × active ads` per hour |
| Ads Management | `100,000 + 40 × active ads` per hour |
| Custom Audience | `190,000 + 40 × active custom audiences` per hour |
| Pages API | `4,800 × engaged users` per 24 hours |
| Messenger | `200 × engaged users` per 24 hours |

**Header:**
```
X-Business-Use-Case-Usage: {
  "{business-id}": [{
    "call_count": 50,
    "total_cputime": 45,
    "total_time": 55,
    "type": "messenger",
    "estimated_time_to_regain_access": 5
  }]
}
```

### Rate Limit Error Codes

| Code | Description |
|------|-------------|
| 4 | App-level rate limit exceeded |
| 17 | User-level rate limit exceeded |
| 32 | Page-level rate limit exceeded |
| 613 | Custom (BUC) rate limit breached |
| 80001 | Ads insights rate limit |
| 80002 | Ads management rate limit |
| 80003 | Custom audience rate limit |
| 80004 | Messages rate limit |
| 80005 | BUC general rate limit |

### Backoff Strategy

```python
import time

def api_call_with_backoff(fn, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = fn()
            # Check rate limit headers
            usage = response.headers.get('X-App-Usage')
            if usage:
                import json
                usage_data = json.loads(usage)
                if any(v > 80 for v in usage_data.values()):
                    time.sleep(60)  # back off proactively
            return response
        except RateLimitException as e:
            wait_time = (2 ** attempt) + random.uniform(0, 1)  # exponential backoff with jitter
            time.sleep(wait_time)
    raise Exception("Max retries exceeded")
```

Rules:
- **Stop immediately** when rate limited — more calls increase the backoff window
- Use `estimated_time_to_regain_access` from BUC header to know when to retry
- Use exponential backoff with jitter (random delay)
- Monitor headers proactively and slow down before hitting 100%

---

## Error Codes — Complete Reference

### Error Response Format

```json
{
  "error": {
    "message": "Human-readable description",
    "type": "OAuthException",
    "code": 190,
    "error_subcode": 463,
    "error_user_title": "Session Expired",
    "error_user_msg": "Please log in again to continue.",
    "fbtrace_id": "AbCdEfGhIjKlMnOp"
  }
}
```

| Field | Description |
|-------|-------------|
| `message` | Human-readable error message |
| `type` | Error category (see types below) |
| `code` | Primary error code |
| `error_subcode` | More specific sub-code |
| `error_user_title` | Title for end-user display |
| `error_user_msg` | Message for end-user display |
| `fbtrace_id` | Trace ID for Facebook support |

### Error Types

| Type | Description |
|------|-------------|
| `OAuthException` | OAuth/authentication/permission related |
| `GraphMethodException` | Invalid method or endpoint |
| `GraphInvalidID` | Invalid object ID |
| `GraphBatchException` | Batch request error |
| `GraphThrottledException` | Rate limit exceeded |
| `GraphRequestException` | General request error |

### All Primary Error Codes

| Code | Type | Description | Recommended Action |
|------|------|-------------|-------------------|
| 1 | GraphMethodException | API unknown error | Retry with exponential backoff |
| 2 | GraphMethodException | API service error (temp) | Retry with exponential backoff |
| 3 | GraphMethodException | API method doesn't exist | Check endpoint |
| 4 | OAuthException | App call limit reached | Back off; monitor X-App-Usage |
| 10 | OAuthException | App does not have permission | Check app permissions in dashboard |
| 17 | OAuthException | User call limit reached | Back off; monitor X-App-Usage |
| 32 | OAuthException | Page-level rate limit | Back off; use page token |
| 33 | OAuthException | Temporary data access | Retry later |
| 100 | GraphMethodException | Invalid parameter | Fix request parameters |
| 102 | OAuthException | Session key invalid (legacy) | Force re-authentication |
| 104 | OAuthException | Incorrect signature | Fix appsecret_proof |
| 190 | OAuthException | Invalid OAuth access token | See error_subcode (table below) |
| 200 | OAuthException | Permission denied (general) | Request required permission |
| 210 | OAuthException | User not visible | User's privacy settings block access |
| 220 | OAuthException | Album not accessible | Check album permissions |
| 240 | OAuthException | Desktop apps cannot call this function | Use server-side flow |
| 273 | OAuthException | Feature requires app review | Submit for App Review |
| 290 | OAuthException | App not installed | User needs to authorize app |
| 368 | OAuthException | Temporarily blocked (policy violation) | Review content policies |
| 459 | OAuthException | User must confirm security checkpoint | User must complete security check |
| 460 | OAuthException | Incorrect user | Token doesn't match user |
| 463 | OAuthException | Session expired | Refresh or reacquire token |
| 467 | OAuthException | Invalid/malformed access token | Reacquire token |
| 506 | OAuthException | Duplicate post | Post content is a duplicate |
| 551 | OAuthException | User unavailable | User profile not accessible |
| 613 | OAuthException | Rate limit breached | Implement backoff |
| 1609005 | OAuthException | Link blocked | URL has been blocked |
| 2500 | OAuthException | Error authorizing application | Login dialog error |

### Error Code 190 Subcodes (Token Issues)

| Subcode | Description | Action |
|---------|-------------|--------|
| 460 | Password was changed | Force user re-login |
| 461 | User has logged out | Force user re-login |
| 462 | User needs to re-login for security | Force user re-login |
| 463 | Session expired | Refresh long-lived token or re-auth |
| 464 | Session invalidated | Force user re-login |
| 467 | Access token has expired | Use token refresh or re-auth |
| 492 | User removed app from their account | Force user re-login |

### Error Code 200 Subcodes (Permission Issues)

| Subcode | Description |
|---------|-------------|
| 200 | Application does not have permission to read |
| 201 | Application does not have permission to write |
| 210 | Application does not have permission to access this user's data |
| 215 | Facebook application not set up |
| 220 | Application does not have permission to read insights |
| 230 | Application does not have permission to use this endpoint |
| 240 | Application does not have permission for this operation |

### HTTP Status Code Reference

| HTTP Status | Graph API Meaning |
|-------------|------------------|
| 200 | Success |
| 400 | Bad request (malformed/invalid params) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not found (object doesn't exist or not accessible) |
| 405 | Method not allowed |
| 429 | Rate limited / Too Many Requests |
| 500 | Internal Server Error (Meta-side) |
| 503 | Service Unavailable |

### Error Handling Strategy

```python
def handle_fb_error(error: dict):
    code = error.get('code')
    subcode = error.get('error_subcode')
    error_type = error.get('type')

    # Rate limiting — back off
    if code in [4, 17, 32, 613] or code in range(80001, 80015):
        implement_exponential_backoff()

    # Transient server errors — retry
    elif code in [1, 2]:
        implement_exponential_backoff()

    # Token expired or invalid — reauth
    elif code == 190:
        if subcode in [460, 461, 462, 464, 492]:
            trigger_relogin_flow()
        elif subcode in [463, 467]:
            try_token_refresh()
        else:
            trigger_relogin_flow()

    # Missing permissions — ask user
    elif code in range(200, 300) or code == 10:
        request_missing_permissions()

    # Bad request — fix code
    elif code == 100:
        log_and_fix_request_parameters()

    # Policy violation — review
    elif code == 368:
        log_policy_violation()

    else:
        log_unknown_error(error)
```

---

## Business Manager API

### Get Business Info
```
GET /v22.0/{business-id}?fields=id,name,primary_page,profile_picture_url&access_token={TOKEN}
```

### List Ad Accounts Under a Business
```
GET /v22.0/{business-id}/owned_ad_accounts?fields=id,name,account_status,currency&access_token={TOKEN}
GET /v22.0/{business-id}/client_ad_accounts?fields=id,name,account_status&access_token={TOKEN}
```

### List Pages Under a Business
```
GET /v22.0/{business-id}/owned_pages?fields=id,name,category,fan_count&access_token={TOKEN}
```

### List System Users
```
GET /v22.0/{business-id}/system_users?fields=id,name,role&access_token={TOKEN}
```

### Assign Ad Account to System User
```
POST /v22.0/{ad-account-id}/assigned_users
  user={system-user-id}
  tasks=MANAGE,ADVERTISE,ANALYZE
  access_token={TOKEN}
```

### Required Permission
- `business_management`

---

## Webhook Retry & Reliability

- Facebook retries failed webhook deliveries with exponential backoff for up to **5 days**.
- Your server must respond with HTTP 200 within **5 seconds** or the delivery is considered failed.
- If your server consistently fails to respond, Facebook may disable the subscription.
- Use async processing: accept the webhook, return 200 immediately, then process in the background.

```python
from flask import request, jsonify
import threading

@app.route('/webhook', methods=['POST'])
def receive_webhook():
    # Verify signature first
    if not verify_signature(request.data, request.headers.get('X-Hub-Signature-256'), APP_SECRET):
        return jsonify({'error': 'Invalid signature'}), 403

    payload = request.json

    # Process asynchronously
    thread = threading.Thread(target=process_webhook, args=(payload,))
    thread.start()

    return jsonify({'status': 'received'}), 200
```

### Deduplication
Facebook may deliver the same event more than once. Track event IDs to avoid duplicate processing:

```python
processed_event_ids = set()

def process_webhook(payload):
    for entry in payload.get('entry', []):
        entry_id = f"{entry['id']}_{entry['time']}"
        if entry_id in processed_event_ids:
            return  # already processed
        processed_event_ids.add(entry_id)
        # ... process entry ...
```
