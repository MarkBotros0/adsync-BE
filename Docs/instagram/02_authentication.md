# Instagram API Authentication

Version: v22.0

---

## Auth Paths Overview

The Instagram Graph API supports two distinct authentication paths. The correct path depends on whether your app requires Facebook Page linkage and whether you need access to ads or product tagging.

| | Path A: Facebook Login for Business | Path B: Instagram Login (Business Login) |
|---|---|---|
| User authenticates with | Facebook credentials | Instagram credentials |
| Token type | Facebook User Access Token or Page Access Token | Instagram User Access Token |
| Base URL | `graph.facebook.com` | `graph.instagram.com` |
| Requires Facebook Page linkage | Yes | No |
| Ads and product tagging | Supported | Not supported |
| Permission namespace | `instagram_*` | `instagram_business_*` |

Choose Path A if your integration touches ads, product catalogs, or Page-level operations. Choose Path B for standalone Instagram Business or Creator accounts that are not linked to a Facebook Page.

---

## OAuth Flow

Both paths follow the same high-level OAuth 2.0 authorization code flow.

1. App user clicks an embed URL constructed by your app.
2. An authorization window opens showing the requested permissions.
3. User reviews and grants the permissions.
4. App receives an authorization code valid for **1 hour**.
5. App exchanges the authorization code for a short-lived access token.
   - Business Login for Instagram: short-lived token is valid for **1 hour**.
   - Facebook Login: short-lived token is valid for approximately **1 hour**.
6. App exchanges the short-lived token for a long-lived token valid for **60 days**.

The authorization code is single-use. Codes that are not exchanged within their validity window must be discarded and the flow restarted.

---

## Token Types

| Token Type | Validity | Use Case |
|---|---|---|
| Short-lived User (Business Login) | 1 hour | Initial token from Instagram Business Login flow |
| Short-lived User (Facebook Login) | ~1 hour | Initial token from Facebook OAuth flow |
| Long-lived User | 60 days | Obtained by exchanging a short-lived token; refreshable before expiry |
| Page Access Token | Does not expire | Linked to a Facebook Page; use for Page-linked operations |
| System User Token | Does not expire | Server-to-server calls; requires Business Manager |
| App Access Token | Does not expire | App-level API calls; never expose to clients |

Long-lived tokens and Page Access Tokens are appropriate for server-side integrations. App Access Tokens must never be sent to client applications.

---

## Long-lived Token Exchange

### Path A — Facebook Login

Exchange a short-lived Facebook User Access Token for a long-lived token using the `fb_exchange_token` grant type.

```
GET https://graph.facebook.com/v22.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id={app-id}
  &client_secret={app-secret}
  &fb_exchange_token={short-lived-token}
```

### Path B — Instagram Login

The initial code exchange is performed against the Instagram authorization endpoint:

```
GET https://api.instagram.com/oauth/access_token
```

The resulting short-lived Instagram User Access Token is then exchanged for a long-lived token via the Instagram Graph API base URL:

```
GET https://graph.instagram.com/v22.0/access_token
  ?grant_type=ig_exchange_token
  &client_id={app-id}
  &client_secret={app-secret}
  &access_token={short-lived-instagram-token}
```

---

## Token Refresh

Long-lived User Access Tokens can be refreshed before they expire. Refreshing a token resets its validity to a new 60-day window from the time of the refresh.

**Constraints:**
- The token must be at least **24 hours old** before it can be refreshed.
- The token must not already be expired. Expired tokens cannot be refreshed; the full OAuth flow must be restarted.

### Path A — Facebook Login

```
GET https://graph.facebook.com/v22.0/oauth/access_token
  ?grant_type=ig_refresh_token
  &access_token={long-lived-token}
```

### Path B — Instagram Login

```
GET https://graph.instagram.com/v22.0/refresh_access_token
  ?grant_type=ig_refresh_token
  &access_token={long-lived-instagram-token}
```

---

## Inspecting Tokens — debug_token

Use the `debug_token` endpoint to inspect any access token and verify its validity, scopes, and expiry.

```
GET https://graph.facebook.com/v22.0/debug_token
  ?input_token={token-to-inspect}
  &access_token={app-access-token}
```

The `access_token` parameter must be an App Access Token, constructed as `{app-id}|{app-secret}`.

**Response fields:**

| Field | Description |
|---|---|
| `app_id` | The app ID the token was issued for |
| `type` | Token type: `USER`, `PAGE`, `APP` |
| `application` | App display name |
| `expires_at` | Unix timestamp of expiry; `0` for non-expiring tokens |
| `is_valid` | Boolean; `false` if the token is invalid or expired |
| `issued_at` | Unix timestamp when the token was issued |
| `metadata` | Additional metadata if present |
| `scopes` | Array of granted permissions or scopes |
| `user_id` | The user ID associated with the token |

---

## appsecret_proof

When the **Require App Secret** setting is enabled in the App Dashboard, all server-side API calls must include an `appsecret_proof` parameter. This prevents token theft by verifying the request originates from a party that holds the app secret.

**Generating the proof:**

```
appsecret_proof = HMAC-SHA256(key=app_secret, message=access_token)
```

The result must be hex-encoded and appended to every API request:

```
GET https://graph.facebook.com/v22.0/me
  ?access_token={access-token}
  &appsecret_proof={hmac-sha256-hex-digest}
```

**Example — Python:**

```python
import hashlib
import hmac

def generate_appsecret_proof(app_secret: str, access_token: str) -> str:
    return hmac.new(
        app_secret.encode("utf-8"),
        access_token.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
```

Note: `appsecret_proof` is tied to the specific access token it was generated with. A new proof must be computed whenever the access token changes.

---

## Permissions — Facebook Login (Path A)

These permissions are requested during the Facebook OAuth flow. Most Instagram Graph API operations require `instagram_basic` plus one or more of the feature-specific permissions below. `pages_read_engagement` is required alongside most Instagram permissions because the Instagram account must be linked to a Page.

| Permission | Description |
|---|---|
| `instagram_basic` | Read profile data and media |
| `instagram_content_publish` | Publish media to the Instagram account |
| `instagram_manage_comments` | Read, delete, and hide comments |
| `instagram_manage_insights` | Read account and media insights |
| `instagram_manage_messages` | Read and send direct messages |
| `pages_read_engagement` | Required alongside most Instagram permissions |
| `pages_show_list` | Read the list of Pages managed by the user |
| `ads_management` | Required when the user role was granted via Business Manager |
| `ads_read` | Read-only alternative to `ads_management` |
| `business_management` | Business Manager operations |
| `catalog_management` | Access product catalogs |
| `instagram_shopping_tag_products` | Tag products in posts |

Permissions must be approved via App Review before they can be requested from users outside your development team.

---

## Scopes — Instagram Login (Path B)

These scopes are requested during the Instagram Business Login flow. They do not require a linked Facebook Page.

| Scope | Description | Replaces |
|---|---|---|
| `instagram_business_basic` | Read profile and media | `business_basic` |
| `instagram_business_content_publish` | Publish media | `business_content_publish` |
| `instagram_business_manage_comments` | Read, delete, and hide comments | `business_manage_comments` |
| `instagram_business_manage_messages` | Read and send direct messages | `business_manage_messages` |

**Deprecation notice:** The old scope values (`business_basic`, `business_content_publish`, `business_manage_messages`, `business_manage_comments`) were deprecated on **January 27, 2025**. All integrations must use the `instagram_business_*` prefixed values.

Ads, product tagging, and catalog management are not available through the Instagram Login path.

---

## Getting Page Access Tokens

For Path A integrations, a Page Access Token is required for operations tied to a specific Facebook Page. Retrieve the Page Access Token by calling the `me/accounts` edge with a valid User Access Token.

```
GET https://graph.facebook.com/v22.0/me/accounts
  ?access_token={user-access-token}
```

The response returns an array of Pages the user administers. Each entry includes the Page's `access_token`, `id`, `name`, and the `tasks` the user can perform on that Page.

```json
{
  "data": [
    {
      "access_token": "EAABs...",
      "category": "Media",
      "category_list": [{ "id": "2256", "name": "Media" }],
      "name": "Example Page",
      "id": "123456789",
      "tasks": ["ANALYZE", "ADVERTISE", "MODERATE", "CREATE_CONTENT"]
    }
  ]
}
```

Page Access Tokens do not expire. Store them securely alongside the associated Page ID.

---

## System Users

System Users are non-human accounts created in Meta Business Manager. They are used for server-to-server integrations where a human user token is not appropriate.

**Key characteristics:**

- System User tokens do not expire.
- Created and managed via Meta Business Manager (business.facebook.com > Users > System Users).
- Must be assigned to the relevant assets (Pages, Ad Accounts, Instagram accounts) with appropriate roles.
- Tokens are generated once in Business Manager and stored by your application; there is no OAuth flow for System Users.
- Require the `business_management` permission for programmatic access.

System User tokens are the preferred credential type for long-running production integrations because they are not tied to any individual employee's account and do not require periodic re-authorization.

To generate a System User token:
1. Navigate to Business Manager > Users > System Users.
2. Select the System User.
3. Click **Generate New Token**.
4. Select the app and the permissions the token should carry.
5. Copy and store the token securely; it is only shown once.
