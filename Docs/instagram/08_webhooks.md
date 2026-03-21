# Instagram Webhooks

Instagram webhooks deliver real-time event notifications to your HTTPS endpoint when subscribed events occur on Instagram professional accounts. This document covers setup, field subscriptions, payload structures, signature validation, and reliability behavior for API version v22.0.

---

## Overview

When a subscribed event occurs on a connected Instagram professional account, Meta sends an HTTP POST request to your registered endpoint with a JSON payload describing the event. Webhooks enable real-time reactions to comments, mentions, messages, and story insights without polling the API.

---

## Requirements

| Requirement | Details |
|---|---|
| App status | Must be set to **Live** in Meta App Dashboard |
| Advanced Access | Required for comment-related fields (`comments`, `live_comments`) |
| Business verification | Mandatory |
| Account visibility | Instagram professional account must be **public** for comment notifications |
| Endpoint protocol | HTTPS with a valid TLS/SSL certificate — self-signed certificates are not accepted |
| mTLS | Optional; supported for enhanced mutual authentication security |

---

## Setup Flow

### Step 1 — Create Your Webhook Endpoint

Your server must handle two request types on the same endpoint URL.

**GET — Verification Request**

Meta sends a GET request when you register or re-verify your endpoint. The request includes three query parameters:

| Parameter | Description |
|---|---|
| `hub.mode` | Always `subscribe` |
| `hub.challenge` | A random integer Meta expects you to echo back |
| `hub.verify_token` | A string you configure; Meta sends it back for you to validate |

Your server must:
1. Confirm that `hub.verify_token` matches your configured token.
2. Return the `hub.challenge` value as a plain integer in the response body with HTTP 200.

```python
def webhook_verify(request):
    if request.args['hub.verify_token'] == MY_VERIFY_TOKEN:
        return request.args['hub.challenge']
    return 'Forbidden', 403
```

Full example verification request:

```
GET /webhook
  ?hub.mode=subscribe
  &hub.challenge=1158201444
  &hub.verify_token=meatyhamhock
```

Your server returns: `1158201444`

**POST — Event Notification**

Meta sends event data as a JSON POST body. Always validate the `X-Hub-Signature-256` header before processing the payload (see [X-Hub-Signature-256 Validation](#x-hub-signature-256-validation)).

```
POST /webhook
X-Hub-Signature-256: sha256={HMAC-SHA256(app_secret, raw_request_body)}
Content-Type: application/json

{ ... }
```

---

### Step 2 — Configure in App Dashboard

1. Open **Meta App Dashboard > Webhooks > Instagram**.
2. Click **Edit** and enter your endpoint URL and Verify Token.
3. Click **Verify and Save** — Meta will immediately send the GET verification request.

---

### Step 3 — Subscribe to Fields

After your endpoint is registered, subscribe the desired fields for a specific Instagram account using its User Access Token:

```
POST /v22.0/me/subscribed_apps
  ?subscribed_fields=comments,mentions,story_insights
  &access_token={user-access-token}
```

Provide a comma-separated list of field names. See [Webhook Fields](#webhook-fields) for all available options.

---

### Step 4 — Enable Account Notifications

Subscribing via the endpoint in Step 3 activates notifications for the account associated with the provided access token. No additional step is required — the subscription and account enablement are performed in the same API call.

---

### Step 5 — Test

Use the **Test** button in **Meta App Dashboard > Webhooks > Instagram** to send a sample payload to your endpoint. Verify that your server receives, validates, and processes the test notification correctly before going live.

---

## Webhook Fields

| Field | Description | Permission Required |
|---|---|---|
| `comments` | New comment posted on the app user's media | Advanced Access; `instagram_business_manage_comments` or `instagram_manage_comments` |
| `live_comments` | Comments posted during a live broadcast | Advanced Access |
| `mentions` | Account @mentioned in a media caption or comment | `instagram_business_basic` or `instagram_basic` |
| `messages` | Direct messages received by the account | `instagram_business_manage_messages` or `instagram_manage_messages` |
| `message_reactions` | Reactions added to direct messages | Messaging permissions |
| `messaging_handover` | Handover protocol notifications between apps | Messaging permissions |
| `messaging_optins` | User opt-in notifications | Messaging permissions |
| `messaging_postbacks` | Postback notifications from message buttons | Messaging permissions |
| `story_insights` | Story metrics delivered after the story expires (24 h) | `instagram_business_basic` or `instagram_basic` |

---

## X-Hub-Signature-256 Validation

Every POST notification includes an `X-Hub-Signature-256` header. The value is an HMAC-SHA256 signature of the raw request body, keyed with your app secret.

Header format:

```
X-Hub-Signature-256: sha256={signature}
```

**Always validate this header before processing any payload.** Reject requests where the signature does not match.

```python
import hmac
import hashlib

def validate_signature(request_body, signature_header, app_secret):
    expected = hmac.new(
        app_secret.encode('utf-8'),
        request_body,
        hashlib.sha256
    ).hexdigest()
    received = signature_header.replace('sha256=', '')
    return hmac.compare_digest(expected, received)
```

Notes:
- `request_body` must be the **raw bytes** of the request body, not a parsed object.
- Use `hmac.compare_digest` (or equivalent constant-time comparison) to prevent timing attacks.
- If validation fails, return HTTP 403 and do not process the payload.

---

## Payload Examples

All webhook notifications share a common envelope structure. The `entry` array may contain multiple entries, and each entry may contain multiple `changes`.

**Envelope:**

```json
{
  "object": "instagram",
  "entry": [
    {
      "id": "{ig-user-id}",
      "time": 1234567890,
      "changes": [
        {
          "field": "{field-name}",
          "value": { }
        }
      ]
    }
  ]
}
```

---

### comments

Sent when a new comment is posted on the subscribed account's media.

```json
{
  "field": "comments",
  "value": {
    "from": {
      "id": "17841405822304914",
      "username": "commenter_username"
    },
    "media": {
      "id": "17895695668004550",
      "media_product_type": "FEED"
    },
    "id": "17870913679156914",
    "text": "Great post!"
  }
}
```

---

### mentions — caption mention

Sent when the subscribed account is @mentioned in a media caption. `comment_id` is `null` for caption mentions.

```json
{
  "field": "mentions",
  "value": {
    "media_id": "17873440459141021",
    "comment_id": null
  }
}
```

---

### mentions — comment mention

Sent when the subscribed account is @mentioned in a comment. `media_id` is `null` for comment mentions.

```json
{
  "field": "mentions",
  "value": {
    "media_id": null,
    "comment_id": "17858893269000001"
  }
}
```

---

### messages

Sent when the subscribed account receives a direct message.

```json
{
  "field": "messages",
  "value": {
    "sender": { "id": "..." },
    "recipient": { "id": "..." },
    "timestamp": 1234567890,
    "message": {
      "mid": "...",
      "text": "Hello!"
    }
  }
}
```

---

### story_insights

Sent after a story expires (approximately 24 hours after posting) with aggregated metrics for the story. See [Story Insights Notes](#story-insights-notes).

```json
{
  "field": "story_insights",
  "value": {
    "media_id": "17895695668004550",
    "exits": 15,
    "impressions": 120,
    "reach": 110,
    "replies": 3,
    "taps_forward": 20,
    "taps_back": 5
  }
}
```

---

## Story Insights Notes

- Story insights are **only available after a story expires** (after the 24-hour story window closes). The webhook is not sent while the story is active.
- Subscribe to the `story_insights` field to receive these notifications automatically.
- The payload includes exit counts, impression and reach totals, replies, and forward/back tap counts.
- Because the data is only delivered once (post-expiry), **save the payload immediately** upon receipt — webhooks do not store data and the notification will not be re-sent unless Meta retries a failed delivery.

---

## Retry and Reliability

| Behavior | Detail |
|---|---|
| Retry window | Meta retries failed deliveries for up to **36 hours** |
| Data storage | Webhooks do **not** store data — save payloads immediately on receipt |
| Live video comments | `live_comments` notifications are only sent during an active broadcast |
| Private accounts | Webhook notifications are **not** sent for mentions on private account media |

To ensure reliable delivery:
- Respond with HTTP 200 as quickly as possible. Offload any heavy processing to a background job.
- Implement idempotent payload handling — retries may deliver the same event more than once.
- Log all received payloads before processing so you can replay them if your processing logic fails.

---

## Unsubscribing

To remove a field subscription for an account, send a DELETE request with the fields to remove:

```
DELETE /v22.0/me/subscribed_apps
  ?subscribed_fields=comments
  &access_token={user-access-token}
```

To remove multiple fields at once, provide a comma-separated list:

```
DELETE /v22.0/me/subscribed_apps
  ?subscribed_fields=comments,mentions,story_insights
  &access_token={user-access-token}
```

A successful response returns `{ "success": true }`. The account will no longer receive webhook notifications for the removed fields.
