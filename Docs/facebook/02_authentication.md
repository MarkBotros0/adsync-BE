# Facebook Authentication & OAuth 2.0

Source: developers.facebook.com/docs/facebook-login
Version: v22.0

---

## OAuth 2.0 Authorization Code Flow

### Step 1 — Redirect User to Login Dialog

```
https://www.facebook.com/v22.0/dialog/oauth?
  client_id={APP_ID}
  &redirect_uri={REDIRECT_URI}
  &state={RANDOM_CSRF_TOKEN}
  &scope=email,public_profile,pages_manage_posts
  &response_type=code
```

#### Login Dialog Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `client_id` | Yes | Your App ID |
| `redirect_uri` | Yes | Must exactly match a URI registered in App Dashboard. URL-encoded. |
| `state` | Yes (strongly recommended) | Random opaque CSRF token. Validate on callback. |
| `scope` | No | Comma/space-separated permissions. Default: `public_profile` |
| `response_type` | No | `code` (default, server-side), `token` (client-side implicit, deprecated for new apps) |
| `display` | No | `page` (default), `popup`, `touch` |
| `auth_type` | No | `rerequest` (re-ask declined perms), `reauthenticate` (force re-login), `reauthorize` |
| `login_hint` | No | Pre-fill email field |

### Step 2 — Facebook Redirects to Your redirect_uri

Success:
```
https://your-app.com/callback?code=AUTH_CODE&state=YOUR_STATE_VALUE
```

Denied by user:
```
https://your-app.com/callback?error=access_denied&error_reason=user_denied&error_description=Permissions+error&state=YOUR_STATE_VALUE
```

### Step 3 — Exchange Code for Access Token

```
GET https://graph.facebook.com/v22.0/oauth/access_token
  ?client_id={APP_ID}
  &client_secret={APP_SECRET}
  &redirect_uri={REDIRECT_URI}
  &code={AUTH_CODE}
```

Response:
```json
{
  "access_token": "EAABs...",
  "token_type": "bearer",
  "expires_in": 5183944
}
```

- `code` is single-use, expires in ~10 minutes.
- `redirect_uri` must exactly match the one used in Step 1.
- **Must be done server-side** (requires app secret).

### Step 4 — Extend to Long-Lived Token

```
GET https://graph.facebook.com/v22.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id={APP_ID}
  &client_secret={APP_SECRET}
  &fb_exchange_token={SHORT_LIVED_USER_TOKEN}
```

Response:
```json
{
  "access_token": "EAABs...LONG",
  "token_type": "bearer",
  "expires_in": 5183944
}
```

- `expires_in` ≈ 5,183,944 seconds ≈ 60 days
- **Must be done server-side** (never expose app secret to client)

---

## Token Types

### User Access Token

- Represents a specific Facebook user.
- **Short-lived:** ~1–2 hours (web), auto-refreshed on mobile SDKs.
- **Long-lived:** ~60 days (converted via `fb_exchange_token`).
- Used for: reading/writing user data, managing pages the user owns.

Get user info:
```
GET /v22.0/me?fields=id,name,email&access_token={USER_TOKEN}
```

### Page Access Token

- Represents a Facebook Page. Allows acting as the page.
- **Non-expiring** when derived from a long-lived user token or system user token.
- Required for: posting as a page, reading page insights, managing messages.

Get page tokens from user token:
```
GET /v22.0/me/accounts?access_token={USER_TOKEN}
```
Response:
```json
{
  "data": [
    {
      "access_token": "EAABw...",
      "category": "Software",
      "id": "123456789",
      "name": "My Page",
      "tasks": ["MANAGE", "CREATE_CONTENT", "MODERATE", "ADVERTISE", "ANALYZE"]
    }
  ]
}
```

Get page token directly by page ID:
```
GET /v22.0/{page-id}?fields=access_token&access_token={USER_TOKEN}
```

### App Access Token

- Represents the app itself. No user context.
- **Never expires.**
- Used for: webhook verification, debugging tokens, test user management.
- Format: `{app-id}|{app-secret}` (can be used directly without endpoint call)

```
GET https://graph.facebook.com/oauth/access_token
  ?client_id={APP_ID}
  &client_secret={APP_SECRET}
  &grant_type=client_credentials
```

Response:
```json
{"access_token": "{app-id}|{app-secret}", "token_type": "bearer"}
```

### System User Access Token

- For server-to-server automation (Business Manager).
- Not tied to a real user account.
- Can be set to never expire.
- Created in: Meta Business Suite → System Users → Generate Token.
- Best for: production pipelines, ad management, long-running integrations.

### Client Token

- Embedded in mobile/native apps.
- Format: `{app-id}|{client-token}`
- Found in: App Dashboard → Settings → Advanced → Client Token.

---

## Token Inspection (debug_token)

```
GET https://graph.facebook.com/debug_token
  ?input_token={TOKEN_TO_INSPECT}
  &access_token={APP_ID}|{APP_SECRET}
```

Response:
```json
{
  "data": {
    "app_id": "123456789",
    "type": "USER",
    "application": "Your App Name",
    "expires_at": 1744000000,
    "data_access_expires_at": 1744000000,
    "is_valid": true,
    "issued_at": 1739000000,
    "scopes": ["email", "public_profile", "pages_manage_posts"],
    "granular_scopes": [
      {"scope": "pages_manage_posts", "target_ids": ["123456789"]}
    ],
    "user_id": "987654321"
  }
}
```

| Field | Description |
|-------|-------------|
| `is_valid` | Whether the token is currently valid |
| `type` | `USER`, `PAGE`, `APP`, `CLIENT`, `SYSTEM_USER` |
| `expires_at` | Unix timestamp; `0` = never expires |
| `data_access_expires_at` | 90-day data access window expiry |
| `scopes` | List of granted permissions |
| `granular_scopes` | Permissions with specific targets (e.g., which page IDs) |

---

## Permissions / Scopes — Complete List

### Default (No App Review Required)
| Permission | Description |
|------------|-------------|
| `public_profile` | id, name, first_name, last_name, picture. Auto-granted. |
| `email` | User's primary email address |
| `openid` | OpenID Connect claim |

### User Data (Require App Review)
| Permission | Description |
|------------|-------------|
| `user_age_range` | Age range (e.g., `{min: 21}`) |
| `user_birthday` | Birthday |
| `user_friends` | Friends who also use the app |
| `user_gender` | Gender and pronouns |
| `user_hometown` | Hometown |
| `user_likes` | Pages liked by user |
| `user_link` | Profile URL |
| `user_location` | Current city/location |
| `user_photos` | Photos uploaded/tagged |
| `user_posts` | Posts on timeline |
| `user_videos` | Videos uploaded/tagged |
| `user_events` | Events |

### Pages Permissions (Require App Review)
| Permission | Description |
|------------|-------------|
| `pages_show_list` | List pages managed by user (`/me/accounts`) |
| `pages_read_engagement` | Page content, followers, metadata |
| `pages_read_user_content` | User-generated content on pages |
| `pages_manage_posts` | Create, edit, delete page posts |
| `pages_manage_engagement` | Reply to comments, like content |
| `pages_manage_metadata` | Subscribe to webhooks, edit settings |
| `pages_manage_ads` | Ad management on pages |
| `pages_manage_cta` | Call-to-action buttons |
| `pages_manage_instant_articles` | Instant Articles |
| `pages_messaging` | Send/receive Messenger messages |
| `pages_user_gender` | Gender of Messenger conversation users |
| `pages_user_locale` | Locale of Messenger conversation users |
| `pages_user_timezone` | Timezone of Messenger conversation users |

### Ads Permissions
| Permission | Description |
|------------|-------------|
| `ads_management` | Full ad account management |
| `ads_read` | Read-only ad data and insights |
| `business_management` | Business Manager data and settings |
| `leads_retrieval` | Download leads from Lead Ads |
| `attribution_read` | Attribution API data |
| `catalog_management` | Manage product catalogs |

### Instagram Permissions
| Permission | Description |
|------------|-------------|
| `instagram_basic` | Basic Instagram profile and media (Facebook Login) |
| `instagram_business_basic` | Basic profile info (Instagram Login) |
| `instagram_content_publish` | Publish photos/videos |
| `instagram_manage_comments` | Read/reply/delete comments |
| `instagram_manage_insights` | Account and media insights |
| `instagram_manage_messages` | Instagram Direct Messages |
| `instagram_shopping_tag_products` | Tag products in media |
| `instagram_business_manage_insights` | Insights (Instagram Login) |
| `instagram_business_manage_comments` | Comments (Instagram Login) |

### Other
| Permission | Description |
|------------|-------------|
| `read_insights` | Page/app analytics (legacy, still needed for many metrics) |
| `publish_video` | Publish videos to pages/profiles |
| `groups_access_member_info` | Member info in groups |
| `publish_to_groups` | Post to groups |
| `whatsapp_business_management` | Manage WhatsApp Business accounts |
| `whatsapp_business_messaging` | Send WhatsApp messages |

---

## Security

### State Parameter (CSRF Protection)

Always generate a cryptographically random state and validate it on callback:

```python
import secrets
state = secrets.token_hex(32)
# Store in session before redirect
session['oauth_state'] = state

# On callback, validate:
if request.args.get('state') != session['oauth_state']:
    raise Exception("CSRF attack detected")
```

### appsecret_proof

When "Require App Secret" is enabled (App Dashboard → Settings → Advanced), all server-side calls must include this HMAC:

```python
import hmac, hashlib

def make_appsecret_proof(app_secret: str, access_token: str) -> str:
    return hmac.new(
        key=app_secret.encode('utf-8'),
        msg=access_token.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
```

```
GET /v22.0/me?access_token={token}&appsecret_proof={proof}
```

### Redirect URI Validation
- All redirect URIs must be registered in App Dashboard → Facebook Login → Valid OAuth Redirect URIs.
- Facebook performs exact-match validation.
- Must use HTTPS in production.

### Token Storage
- Never store tokens in localStorage or expose in client-side code.
- Store server-side, encrypted at rest.
- Never embed app secret in mobile app binaries or public code.

### 90-Day Data Access Policy
- Even a non-expiring page token stops returning user data if the user hasn't interacted with your app in 90 days.
- Check `data_access_expires_at` in `/debug_token` response.

---

## Auth Error Codes

### OAuth Callback Errors (redirect params)
| `error` | `error_reason` | Meaning |
|---------|----------------|---------|
| `access_denied` | `user_denied` | User clicked Cancel |
| `access_denied` | `user_not_logged_in` | User not logged in |

### Graph API Auth Errors (JSON response)
| Code | Subcode | Meaning | Action |
|------|---------|---------|--------|
| 100 | 36008 | Invalid verification code format | Fix code exchange |
| 190 | 460 | Password changed | Force re-login |
| 190 | 461 | User logged out | Force re-login |
| 190 | 463 | Session expired | Refresh token |
| 190 | 464 | Session invalidated | Force re-login |
| 190 | 467 | Token expired | Re-authenticate |
| 190 | 492 | App removed by user | Force re-login |
| 2500 | — | Error authorizing application | Login dialog issue |

---

## Quick Reference Cheat Sheet

```bash
# 1. Login Dialog
https://www.facebook.com/v22.0/dialog/oauth?
  client_id=APP_ID&redirect_uri=REDIRECT_URI&state=STATE&scope=SCOPES&response_type=code

# 2. Code → User Access Token
GET https://graph.facebook.com/v22.0/oauth/access_token?
  client_id=APP_ID&client_secret=APP_SECRET&redirect_uri=REDIRECT_URI&code=AUTH_CODE

# 3. Short-lived → Long-lived User Token
GET https://graph.facebook.com/v22.0/oauth/access_token?
  grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN

# 4. Long-lived User Token → Page Tokens
GET https://graph.facebook.com/v22.0/me/accounts?
  access_token=LONG_LIVED_USER_TOKEN

# 5. App Access Token
GET https://graph.facebook.com/oauth/access_token?
  client_id=APP_ID&client_secret=APP_SECRET&grant_type=client_credentials

# 6. Inspect / Debug Token
GET https://graph.facebook.com/debug_token?
  input_token=TOKEN_TO_CHECK&access_token=APP_ID|APP_SECRET
```
