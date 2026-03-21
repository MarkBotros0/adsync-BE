# Facebook Business Manager API

Source: developers.facebook.com/docs/marketing-api/business-manager
Version: v22.0

---

## Overview

The Business Manager (Meta Business Suite) API allows programmatic management of business assets including ad accounts, pages, pixels, catalogs, system users, and user roles. All calls require a User Access Token or System User Access Token with the `business_management` permission.

---

## Business Node

```
GET /v22.0/{business-id}?fields={fields}&access_token={TOKEN}
```

### Business Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Business Manager ID |
| `name` | string | Business name |
| `primary_page` | object | Primary Facebook Page `{id, name}` |
| `profile_picture_url` | string | Business profile picture URL |
| `timezone_id` | int | Timezone ID |
| `created_by` | object | User who created the business `{id, name}` |
| `created_time` | datetime | Creation timestamp |
| `verification_status` | string | `not_verified`, `pending`, `verified` |
| `link` | string | Business website URL |
| `email` | string | Business contact email |
| `phone_number` | string | Business phone number |
| `street` | string | Business street address |
| `city` | string | Business city |
| `state` | string | Business state/region |
| `zip` | string | Business postal code |
| `country` | string | Business country code |

### Business Edges

| Edge | Description |
|------|-------------|
| `/owned_ad_accounts` | Ad accounts owned by this business |
| `/client_ad_accounts` | Ad accounts where business is a client/agency |
| `/owned_pages` | Pages owned by this business |
| `/client_pages` | Pages where business manages on behalf of clients |
| `/owned_pixels` | Facebook Pixels owned by this business |
| `/owned_product_catalogs` | Product catalogs owned by this business |
| `/owned_instagram_accounts` | Instagram accounts connected to this business |
| `/client_instagram_accounts` | Client Instagram accounts |
| `/system_users` | System users under this business |
| `/business_users` | Human users with access to this business |
| `/pending_users` | Users with pending invitations |
| `/agencies` | Agencies (businesses with access to this business) |
| `/clients` | Client businesses |
| `/received_audience_sharing_requests` | Audience sharing requests received |
| `/sent_audience_sharing_requests` | Audience sharing requests sent |
| `/shared_audiences` | Custom audiences shared with this business |
| `/offline_conversion_data_sets` | Offline conversion datasets |
| `/event_source_groups` | Event source groups |

---

## Ad Accounts

### List Owned Ad Accounts

```
GET /v22.0/{business-id}/owned_ad_accounts
  ?fields=id,name,account_status,currency,timezone_id,amount_spent,balance
  &access_token={TOKEN}
```

### List Client Ad Accounts

```
GET /v22.0/{business-id}/client_ad_accounts
  ?fields=id,name,account_status,currency
  &access_token={TOKEN}
```

### Account Status Values

| Value | Meaning |
|-------|---------|
| 1 | Active |
| 2 | Disabled |
| 3 | Unsettled |
| 7 | Pending Risk Review |
| 8 | Pending Settlement |
| 9 | In Grace Period |
| 100 | Pending Closure |
| 101 | Closed |
| 201 | Any Active |
| 202 | Any Closed |

### Add Existing Ad Account to Business

```
POST /v22.0/{business-id}/owned_ad_accounts
  adaccount_id={ad-account-id}
  access_token={TOKEN}
```

### Request Access to Client Ad Account

```
POST /v22.0/{business-id}/client_ad_accounts
  adaccount_id={ad-account-id}
  access_token={TOKEN}
```

---

## Pages

### List Owned Pages

```
GET /v22.0/{business-id}/owned_pages
  ?fields=id,name,category,fan_count,is_published,verification_status
  &access_token={TOKEN}
```

### Claim a Page for Your Business

```
POST /v22.0/{business-id}/owned_pages
  page_id={page-id}
  access_token={TOKEN}
```

### Assign Page Access to a User

```
POST /v22.0/{business-id}/pages
  user={user-id-or-system-user-id}
  page_id={page-id}
  tasks=ADVERTISE,ANALYZE,CREATE_CONTENT,MANAGE,MODERATE
  access_token={TOKEN}
```

### Page Task Permissions

| Task | Description |
|------|-------------|
| `ADVERTISE` | Create ads for the page |
| `ANALYZE` | View page insights |
| `CREATE_CONTENT` | Create posts and stories |
| `MANAGE` | Full admin access |
| `MODERATE` | Respond to comments and messages |
| `VIEW_MONETIZATION_INSIGHTS` | View monetization data |

---

## System Users

System users are non-human accounts that authenticate programmatically without user-based tokens. They are the recommended approach for server-to-server integrations.

### List System Users

```
GET /v22.0/{business-id}/system_users
  ?fields=id,name,role,created_time
  &access_token={TOKEN}
```

### System User Roles

| Role | Description |
|------|-------------|
| `ADMIN` | Full admin access to the business |
| `EMPLOYEE` | Limited access (must be explicitly assigned assets) |

### Create a System User

```
POST /v22.0/{business-id}/system_users
  name=My System User
  role=EMPLOYEE
  access_token={TOKEN}
```

Response: `{"id": "{system-user-id}"}`

### Generate System User Access Token

```
POST /v22.0/{business-id}/access_token
  scope=ads_management,pages_read_engagement,read_insights
  appsecret_proof={HMAC}
  set_token_expires_in_60_days=false
  access_token={ADMIN_TOKEN}
```

**Note:** System user tokens can be set to never expire (`set_token_expires_in_60_days=false`) making them ideal for long-running server integrations.

Required Fields:
| Parameter | Description |
|-----------|-------------|
| `scope` | Comma-separated list of permissions to grant |
| `appsecret_proof` | HMAC-SHA256 of the admin token signed with app secret |
| `set_token_expires_in_60_days` | `false` for non-expiring token; `true` for 60-day expiry |

### Assign Ad Account to System User

```
POST /v22.0/{ad-account-id}/assigned_users
  user={system-user-id}
  tasks=MANAGE,ADVERTISE,ANALYZE
  access_token={TOKEN}
```

### Assign Page to System User

```
POST /v22.0/{business-id}/pages
  user={system-user-id}
  page_id={page-id}
  tasks=CREATE_CONTENT,ADVERTISE,ANALYZE,MODERATE
  access_token={TOKEN}
```

### List Assets Assigned to a System User

```
GET /v22.0/{system-user-id}/assigned_ad_accounts
  ?fields=id,name,account_status
  &access_token={TOKEN}

GET /v22.0/{system-user-id}/assigned_pages
  ?fields=id,name
  &access_token={TOKEN}
```

---

## Business Users (Human Users)

### List Users in a Business

```
GET /v22.0/{business-id}/business_users
  ?fields=id,name,email,role,title,business
  &access_token={TOKEN}
```

### User Roles

| Role | Description |
|------|-------------|
| `ADMIN` | Full business admin access |
| `EMPLOYEE` | Limited access; needs explicit asset assignment |
| `FINANCE_EDITOR` | Can manage billing and payments |
| `FINANCE_ANALYST` | Read-only finance access |

### Invite a User to a Business

```
POST /v22.0/{business-id}/business_users
  email=user@example.com
  role=EMPLOYEE
  access_token={TOKEN}
```

### Remove a User from a Business

```
DELETE /v22.0/{business-id}/business_users/{user-id}
  access_token={TOKEN}
```

---

## Pixels

### List Pixels

```
GET /v22.0/{business-id}/owned_pixels
  ?fields=id,name,code,is_unavailable,last_fired_time,creation_time
  &access_token={TOKEN}
```

### Create a New Pixel

```
POST /v22.0/{business-id}/adspixels
  name=My Pixel
  access_token={TOKEN}
```

### Share Pixel with Ad Account

```
POST /v22.0/{pixel-id}/shared_accounts
  business={business-id}
  account_id={ad-account-id}
  access_token={TOKEN}
```

### Pixel Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Pixel ID |
| `name` | string | Pixel name |
| `code` | string | JavaScript pixel base code |
| `creation_time` | int | Unix timestamp of creation |
| `last_fired_time` | datetime | When pixel last received an event |
| `is_unavailable` | bool | Whether pixel is disabled/unavailable |
| `owner_business` | object | Business that owns the pixel |

---

## Product Catalogs

### List Product Catalogs

```
GET /v22.0/{business-id}/owned_product_catalogs
  ?fields=id,name,vertical,product_count
  &access_token={TOKEN}
```

### Create a Product Catalog

```
POST /v22.0/{business-id}/owned_product_catalogs
  name=My Catalog
  vertical=commerce
  access_token={TOKEN}
```

### Catalog Vertical Values

| Value | Use Case |
|-------|----------|
| `commerce` | General e-commerce products |
| `destinations` | Travel destinations |
| `flights` | Flight offers |
| `home_listings` | Real estate |
| `hotels` | Hotel rooms |
| `vehicles` | Automotive |
| `jobs` | Job listings |
| `local` | Local products |

---

## Instagram Accounts

### List Connected Instagram Accounts

```
GET /v22.0/{business-id}/owned_instagram_accounts
  ?fields=id,name,username,profile_picture_url,followers_count,biography
  &access_token={TOKEN}
```

### Connect Instagram Account to Business

This is typically done through the Meta Business Suite UI, but can also be initiated via:

```
POST /v22.0/{business-id}/instagram_accounts
  instagram_account={ig-user-id}
  access_token={TOKEN}
```

---

## Agencies & Client Relationships

### List Agencies (Businesses with access to YOUR business)

```
GET /v22.0/{business-id}/agencies
  ?fields=id,name,link
  &access_token={TOKEN}
```

### List Clients (Businesses YOUR business manages)

```
GET /v22.0/{business-id}/clients
  ?fields=id,name
  &access_token={TOKEN}
```

### Remove Agency Access

```
DELETE /v22.0/{business-id}/agencies
  business={agency-business-id}
  access_token={TOKEN}
```

---

## Custom Audience Sharing

### Share Custom Audience with Another Business

```
POST /v22.0/{custom-audience-id}/shared_account_ids
  adaccounts=[{target-ad-account-id}]
  access_token={TOKEN}
```

### List Shared Audiences

```
GET /v22.0/{business-id}/shared_audiences
  ?fields=id,name,approximate_count,subtype
  &access_token={TOKEN}
```

---

## Business Verification

### Check Verification Status

```
GET /v22.0/{business-id}?fields=verification_status&access_token={TOKEN}
```

| Status | Meaning |
|--------|---------|
| `not_verified` | Business has not started verification |
| `pending` | Verification is in progress |
| `verified` | Business is verified |

**Note:** Advanced access to many APIs requires verified business status. Verification is done through the Meta Business Suite UI (Business Settings → Business Info → Business Verification).

---

## Permissions Required

| Operation | Permission(s) |
|-----------|--------------|
| Read business info | `business_management` |
| List owned/client ad accounts | `business_management` |
| List owned/client pages | `business_management` |
| Create system users | `business_management` |
| Generate system user tokens | `business_management` |
| Assign assets to users | `business_management` |
| Manage pixels | `business_management` |
| Manage product catalogs | `business_management`, `catalog_management` |
| Invite business users | `business_management` |

---

## Common Workflow: Setting Up Server-to-Server Integration

1. **Create a System User** in your Business Manager
2. **Generate a non-expiring token** for the System User
3. **Assign ad accounts and pages** the System User needs access to
4. **Use the System User token** in all server-side API calls

```python
# Example: Full setup verification
import requests

BUSINESS_ID = "your_business_id"
SYSTEM_USER_TOKEN = "your_system_user_token"

# Verify system user has access to ad accounts
r = requests.get(
    f"https://graph.facebook.com/v22.0/{BUSINESS_ID}/owned_ad_accounts",
    params={
        "fields": "id,name,account_status,currency",
        "access_token": SYSTEM_USER_TOKEN
    }
)
ad_accounts = r.json().get("data", [])
print(f"System user has access to {len(ad_accounts)} ad accounts")
```

---

## Pagination

Business Manager API endpoints return paginated results using cursor-based pagination:

```json
{
  "data": [...],
  "paging": {
    "cursors": {
      "before": "before_cursor",
      "after": "after_cursor"
    },
    "next": "https://graph.facebook.com/..."
  }
}
```

Use `after` cursor in subsequent requests to iterate through all results:

```
GET /v22.0/{business-id}/owned_ad_accounts?after={cursor}&access_token={TOKEN}
```

---

## Error Codes Specific to Business Manager

| Code | Description | Action |
|------|-------------|--------|
| 100 | Invalid parameter (e.g., unknown ad account ID) | Fix request |
| 200 | Permission denied | Ensure token has `business_management` |
| 273 | Feature requires app review | Submit `business_management` for app review |
| 3918 | Business not found | Verify business ID |
| 3919 | Ad account not found or not accessible | Verify ad account ID and access |
| 3920 | Page not found or not accessible | Verify page ID and access |
| 36007 | Cannot add ad account: already at max limit | Request limit increase via Business Support |
