# TikTok API — Authentication

## OAuth 2.0 Flow (Login Kit)

### Step 1: Create Anti-Forgery State Token
Generate a random alphanumeric string and store it server-side. Validate it on callback to prevent CSRF attacks.

### Step 2: Redirect User to Authorization Page

```
GET https://www.tiktok.com/v2/auth/authorize/
  ?client_key={client_key}
  &scope={comma_separated_scopes}
  &redirect_uri={redirect_uri}
  &state={state_token}
  &response_type=code
  &disable_auto_auth=0
```

**Authorization Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| client_key | string | Yes | App identification key from Developer Portal |
| scope | string | Yes | Comma-separated permission scopes (e.g. `user.info.basic,video.list`) |
| redirect_uri | string | Yes | Registered callback URI. Must start with `https://`, no query params, no fragments, max 512 chars |
| state | string | Yes | CSRF protection token — must be validated on callback |
| response_type | string | Yes | Always `"code"` |
| disable_auto_auth | int | No | `0` = skip login page if session valid; `1` = always show login page |

**Redirect URI Constraints**
- Max 10 URIs registered per app
- Must begin with `https://`
- Must be static (no query parameters)
- Cannot include fragments (`#`)
- Max 512 characters each

### Step 3: Handle Authorization Response

TikTok redirects to `redirect_uri` with:

| Parameter | Description |
|-----------|-------------|
| code | Authorization code — exchange for tokens (URL-decode before use, single-use) |
| scopes | Comma-separated list of granted scopes |
| state | Must match the original state token |
| error | Error code if user denied |
| error_description | Human-readable error description |

### Step 4: Exchange Authorization Code for Tokens

```
POST https://open.tiktokapis.com/v2/oauth/token/
Content-Type: application/x-www-form-urlencoded

client_key={client_key}
&client_secret={client_secret}
&code={authorization_code_url_decoded}
&grant_type=authorization_code
&redirect_uri={redirect_uri}
```

**Response**

```json
{
  "access_token": "act.example12345Example12345Example",
  "expires_in": 86400,
  "open_id": "723f24d7-e717-40f8-a2b6-cb8464cd23b4",
  "refresh_token": "rft.example12345Example12345Example",
  "refresh_expires_in": 31536000,
  "scope": "user.info.basic,video.list",
  "token_type": "Bearer"
}
```

| Field | Type | Description |
|-------|------|-------------|
| access_token | string | Bearer token for API calls. Prefix: `act.` |
| expires_in | int64 | Seconds until access token expires (86400 = 24 hours) |
| open_id | string | User's unique ID in this application |
| refresh_token | string | Token to obtain new access tokens. Prefix: `rft.` |
| refresh_expires_in | int64 | Seconds until refresh token expires (31536000 = 365 days) |
| scope | string | Comma-separated list of authorized scopes |
| token_type | string | Always `"Bearer"` |

---

## PKCE Flow (Mobile / Desktop Apps)

Used for apps that cannot securely store a `client_secret`. Add these steps:

1. Generate `code_verifier`: random string, 43–128 characters, using unreserved URI characters (`A-Z a-z 0-9 - . _ ~`)
2. Compute `code_challenge`: `BASE64URL(SHA256(code_verifier))`
3. Add to authorization request:
   - `code_challenge={code_challenge}`
   - `code_challenge_method=S256`
4. Add to token exchange request:
   - `code_verifier={code_verifier}`

---

## Token Types

| Token Type | Prefix | Validity | Use Case |
|------------|--------|----------|----------|
| access_token | `act.` | 24 hours (86400s) | Bearer token for all API calls |
| refresh_token | `rft.` | 365 days (31536000s) | Obtain new access tokens without re-auth |
| client_access_token | `clt.` | 2 hours (7200s) | Server-to-server: Research API, Commercial Content API |

---

## Token Refresh

```
POST https://open.tiktokapis.com/v2/oauth/token/
Content-Type: application/x-www-form-urlencoded

client_key={client_key}
&client_secret={client_secret}
&grant_type=refresh_token
&refresh_token={refresh_token}
```

Returns a new `access_token` and a new `refresh_token` (the refresh token value may change — always store the latest).

---

## Token Revocation

```
POST https://open.tiktokapis.com/v2/oauth/revoke/
Content-Type: application/x-www-form-urlencoded

client_key={client_key}
&client_secret={client_secret}
&token={access_token}
```

Response: empty body on success.

---

## Client Credentials Flow (Server-to-Server)

For Research API and Commercial Content API — no user authorization required.

```
POST https://open.tiktokapis.com/v2/oauth/token/
Content-Type: application/x-www-form-urlencoded

client_key={client_key}
&client_secret={client_secret}
&grant_type=client_credentials
```

**Response**

```json
{
  "access_token": "clt.example12345Example12345Example",
  "expires_in": 7200,
  "token_type": "Bearer"
}
```

---

## Scopes / Permissions List

| Scope | Description |
|-------|-------------|
| user.info.basic | Read open_id, union_id, avatar_url, avatar_url_100, avatar_large_url, display_name |
| user.info.profile | Read bio_description, profile_deep_link, is_verified, username |
| user.info.stats | Read follower_count, following_count, likes_count, video_count |
| video.list | Read a user's public videos on TikTok |
| video.publish | Directly post content to a user's TikTok profile (requires API audit) |
| video.upload | Share content to creator's Inbox as a draft |
| research.adlib.basic | Access to public commercial data for research purposes |
| research.data.basic | Access to TikTok public data for research purposes |
| research.data.u18eu | Access data from European users under 18 for research |
| research.data.vra | Access to provisioned data for vetted researchers |
| portability.activity.ongoing | Make recurring requests for user activity data |
| portability.activity.single | Make one-time requests for user activity data |
| portability.directmessages.ongoing | Make recurring requests for direct message data |
| portability.directmessages.single | Make one-time requests for direct message data |
| portability.postsandprofile.ongoing | Make recurring requests for posts and profile data |
| portability.postsandprofile.single | Make one-time requests for posts and profile data |
| portability.all.ongoing | Make recurring requests for all available user data |
| portability.all.single | Make one-time requests for all available user data |
| local.product.manage | Create and manage product listings |
| local.shop.manage | Create and manage local shops |
| local.voucher.manage | Validate and redeem vouchers |

---

## Security Best Practices

- Store `client_secret` server-side only — never expose in client-side code or mobile apps
- Validate `state` parameter on every OAuth callback before proceeding
- Use PKCE for mobile/desktop apps instead of client_secret
- Revoke tokens when users disconnect your app
- Authorization codes are single-use and short-lived — URL-decode before submitting

---

## Sandbox Credentials

- Obtain `client_key` and `client_secret` from app settings in Developer Portal
- Create sandbox test users in Developer Portal to simulate OAuth without real TikTok accounts
- Sandbox posts are always `SELF_ONLY` (private) regardless of `privacy_level` setting in request
