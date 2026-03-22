# TikTok Ads API (Marketing API) — Reference

> **Base URL:** `https://business-api.tiktok.com/open_api/v1.3/`
>
> All requests require the header `Access-Token: <your_token>` and `Content-Type: application/json`.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Account Hierarchy](#account-hierarchy)
4. [Campaign Object](#campaign-object)
5. [Ad Group Object](#ad-group-object)
6. [Ad Object](#ad-object)
7. [Reporting API](#reporting-api)
8. [Custom Audiences](#custom-audiences)
9. [Lookalike Audiences](#lookalike-audiences)
10. [Sandbox Environment](#sandbox-environment)
11. [Endpoint Quick Reference](#endpoint-quick-reference)

---

## Overview

The TikTok Ads API (also called the **Marketing API** or **Business API**) enables programmatic creation and management of TikTok advertising campaigns, ad groups, ads, audiences, and reports. It follows a REST architecture with JSON request and response bodies.

- **API version:** v1.3
- **Base URL:** `https://business-api.tiktok.com/open_api/v1.3/`
- **Authentication:** OAuth 2.0 access token via TikTok Business Center
- **Rate limits:** Vary by endpoint; check `X-RateLimit-*` response headers

---

## Authentication

TikTok Ads API uses **OAuth 2.0**. The access token is passed as a custom header — not as a standard `Authorization: Bearer` header.

```http
Access-Token: <your_access_token>
Content-Type: application/json
```

### OAuth Flow (App Authorization)

| Step | Method | Endpoint |
|------|--------|----------|
| 1. Redirect user to authorize | GET | `https://business-api.tiktok.com/portal/auth?app_id=<APP_ID>&redirect_uri=<REDIRECT_URI>&state=<STATE>` |
| 2. Exchange auth code for token | POST | `https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/` |
| 3. Refresh access token | POST | `https://business-api.tiktok.com/open_api/v1.3/oauth2/refresh_token/` |

#### Token Request Body

```json
{
  "app_id": "your_app_id",
  "secret": "your_app_secret",
  "auth_code": "auth_code_from_redirect"
}
```

#### Token Response

```json
{
  "code": 0,
  "message": "OK",
  "data": {
    "access_token": "act.example_token",
    "advertiser_ids": ["123456789"],
    "scope": ["Ads Management"],
    "token_type": "Bearer",
    "expires_in": 86400
  }
}
```

> **Note:** Sandbox environments use a separate access token issued from the Business Center sandbox.

---

## Account Hierarchy

```
Business Center
  └── Advertiser Account  (advertiser_id)
        └── Campaign       (campaign_id)
              └── Ad Group  (adgroup_id)
                    └── Ad   (ad_id)
```

- **Business Center** — Top-level organization entity; manages multiple advertiser accounts, billing, and user permissions.
- **Advertiser Account** (`advertiser_id`) — The billing entity; all spend is attributed here.
- **Campaign** (`campaign_id`) — Defines the objective and top-level budget.
- **Ad Group** (`adgroup_id`) — Controls targeting, bidding, scheduling, and placement.
- **Ad** (`ad_id`) — The creative unit shown to users.

---

## Campaign Object

### Endpoints

| Action | Method | Path |
|--------|--------|------|
| Create campaign | POST | `/campaign/create/` |
| Update campaign | POST | `/campaign/update/` |
| Get campaigns | GET | `/campaign/get/` |
| Delete campaign | POST | `/campaign/delete/` |
| Update status | POST | `/campaign/status/update/` |

### Campaign Fields

| Field | Type | Description |
|-------|------|-------------|
| `campaign_id` | string | Unique campaign identifier |
| `campaign_name` | string | Campaign name (max 512 characters) |
| `advertiser_id` | string | Parent advertiser account ID |
| `objective_type` | string | Campaign objective — see [Objective Types](#objective-types) |
| `status` | string | `ENABLE`, `DISABLE`, or `DELETE` |
| `budget` | float | Campaign budget amount |
| `budget_mode` | string | `BUDGET_MODE_DAY` (daily) or `BUDGET_MODE_TOTAL` (lifetime) |
| `create_time` | string | Campaign creation timestamp (UTC) |
| `modify_time` | string | Last modification timestamp (UTC) |
| `campaign_type` | string | `REGULAR_CAMPAIGN` or `IOS14_CAMPAIGN` |
| `split_test_variable` | string | Split test variable if applicable |

### Create Campaign — Example Request

```json
POST /open_api/v1.3/campaign/create/
{
  "advertiser_id": "123456789",
  "campaign_name": "My Brand Awareness Campaign",
  "objective_type": "REACH",
  "budget_mode": "BUDGET_MODE_DAY",
  "budget": 50.00
}
```

### Objective Types

| Value | Description |
|-------|-------------|
| `VIDEO_VIEWS` | Maximize video views |
| `REACH` | Maximize unique reach |
| `APP_PROMOTION` | Drive app installs or re-engagement |
| `WEB_CONVERSIONS` | Drive conversions on a website |
| `PRODUCT_SALES` | Drive product sales via catalog |
| `LEAD_GENERATION` | Collect leads via TikTok Instant Forms |
| `COMMUNITY_INTERACTION` | Grow TikTok profile followers or engagement |
| `TRAFFIC` | Drive clicks to a URL |
| `ENGAGEMENT` | Drive engagement on content |
| `CATALOG_SALES` | Promote a product catalog |
| `RF_REACH` | Reach & Frequency buying — Reach objective |
| `RF_VIDEO_VIEW` | Reach & Frequency buying — Video Views |
| `RF_ENGAGEMENT` | Reach & Frequency buying — Engagement |
| `SHOP_PURCHASES` | Drive purchases in TikTok Shop |

---

## Ad Group Object

### Endpoints

| Action | Method | Path |
|--------|--------|------|
| Create ad group | POST | `/adgroup/create/` |
| Update ad group | POST | `/adgroup/update/` |
| Get ad groups | GET | `/adgroup/get/` |
| Delete ad group | POST | `/adgroup/delete/` |
| Update status | POST | `/adgroup/status/update/` |

### Ad Group Fields

| Field | Type | Description |
|-------|------|-------------|
| `adgroup_id` | string | Unique ad group identifier |
| `adgroup_name` | string | Ad group name |
| `campaign_id` | string | Parent campaign ID |
| `advertiser_id` | string | Parent advertiser ID |
| `status` | string | `ENABLE`, `DISABLE`, or `DELETE` |
| `budget` | float | Ad group budget |
| `budget_mode` | string | `BUDGET_MODE_DAY` or `BUDGET_MODE_TOTAL` |
| `schedule_type` | string | `SCHEDULE_FROM_NOW` or `SCHEDULE_START_END` |
| `schedule_start_time` | string | Start datetime (`YYYY-MM-DD HH:MM:SS`) |
| `schedule_end_time` | string | End datetime (`YYYY-MM-DD HH:MM:SS`) |
| `optimization_goal` | string | `CLICK`, `CONVERT`, `INSTALL`, `IN_APP_EVENT`, `SHOW`, `REACH`, etc. |
| `bid_type` | string | `BID_TYPE_CUSTOM` or `BID_TYPE_NO_BID` |
| `bid_price` | float | Bid price in account currency |
| `billing_event` | string | `OCPM`, `CPC`, `CPM`, or `CPV` |
| `placement_type` | string | `PLACEMENT_TYPE_NORMAL` or `PLACEMENT_TYPE_SEARCH` |
| `placements` | string[] | `PLACEMENT_TIKTOK`, `PLACEMENT_PANGLE`, etc. |
| `location_ids` | string[] | Geo-targeting location IDs |
| `age_groups` | string[] | `AGE_13_17`, `AGE_18_24`, `AGE_25_34`, `AGE_35_44`, `AGE_45_54`, `AGE_55_100` |
| `gender` | string | `GENDER_MALE`, `GENDER_FEMALE`, or `GENDER_UNLIMITED` |
| `languages` | string[] | BCP-47 language codes |
| `interest_category_ids` | string[] | Interest category IDs |
| `action_categories` | object[] | Behavioral targeting (hashtag, creator, video interactions) |
| `device_models` | string[] | Specific device model IDs |
| `device_price_ranges` | int[] | Device price range targeting buckets |
| `operation_systems` | string[] | `OS_ANDROID` or `OS_IOS` |
| `network_types` | string[] | `WIFI`, `CELLULAR_4G`, `CELLULAR_3G`, `CELLULAR_2G` |
| `audience_ids` | string[] | Custom audience IDs to include |
| `excluded_audience_ids` | string[] | Custom audience IDs to exclude |
| `pixel_id` | string | TikTok Pixel ID for conversion tracking |

### Create Ad Group — Example Request

```json
POST /open_api/v1.3/adgroup/create/
{
  "advertiser_id": "123456789",
  "campaign_id": "987654321",
  "adgroup_name": "US 18-34 Female",
  "placement_type": "PLACEMENT_TYPE_NORMAL",
  "placements": ["PLACEMENT_TIKTOK"],
  "location_ids": ["6252001"],
  "age_groups": ["AGE_18_24", "AGE_25_34"],
  "gender": "GENDER_FEMALE",
  "budget_mode": "BUDGET_MODE_DAY",
  "budget": 20.00,
  "schedule_type": "SCHEDULE_START_END",
  "schedule_start_time": "2026-04-01 00:00:00",
  "schedule_end_time": "2026-04-30 23:59:59",
  "billing_event": "OCPM",
  "optimization_goal": "CLICK",
  "bid_type": "BID_TYPE_CUSTOM",
  "bid_price": 0.50
}
```

---

## Ad Object

### Endpoints

| Action | Method | Path |
|--------|--------|------|
| Create ad | POST | `/ad/create/` |
| Update ad | POST | `/ad/update/` |
| Get ads | GET | `/ad/get/` |
| Delete ad | POST | `/ad/delete/` |
| Update status | POST | `/ad/status/update/` |

### Ad Fields

| Field | Type | Description |
|-------|------|-------------|
| `ad_id` | string | Unique ad identifier |
| `ad_name` | string | Ad name |
| `adgroup_id` | string | Parent ad group ID |
| `campaign_id` | string | Parent campaign ID |
| `advertiser_id` | string | Parent advertiser ID |
| `status` | string | `ENABLE`, `DISABLE`, or `DELETE` |
| `ad_format` | string | Ad format type — see [Ad Formats](#ad-formats) |
| `ad_text` | string | Ad copy/caption text |
| `landing_page_url` | string | Destination URL |
| `display_name` | string | Display name shown on the ad |
| `avatar_icon_web_uri` | string | Brand or app icon URI |
| `call_to_action` | string | CTA button: `LEARN_MORE`, `DOWNLOAD_NOW`, `SIGN_UP`, `CONTACT_US`, `SHOP_NOW`, `BOOK_NOW`, `APPLY_NOW`, `GET_QUOTE`, `SUBSCRIBE`, `WATCH_MORE` |
| `video_id` | string | TikTok video asset ID |
| `image_ids` | string[] | Image asset IDs (for image or carousel ads) |
| `music_id` | string | Background music ID |
| `tiktok_item_id` | string | Spark Ads: organic TikTok post ID to promote |
| `identity_type` | string | `CUSTOMIZED_USER` or `TT_AUTHORIZATION` (Spark Ads) |

### Ad Formats

| Format | Description |
|--------|-------------|
| `SINGLE_VIDEO` | Standard in-feed video ad |
| `SPARK_ADS` | Boost an existing organic TikTok post |
| `IMAGE` | Static image ad (Pangle network only) |
| `CAROUSEL` | Multi-image carousel ad |
| `VIDEO_SHOPPING_ADS` | Video ad with embedded product shopping |

### Create Ad (Single Video) — Example Request

```json
POST /open_api/v1.3/ad/create/
{
  "advertiser_id": "123456789",
  "adgroup_id": "111222333",
  "creatives": [
    {
      "ad_name": "Spring Sale Video Ad",
      "ad_format": "SINGLE_VIDEO",
      "ad_text": "Discover our spring collection — shop now!",
      "call_to_action": "SHOP_NOW",
      "video_id": "v09044g40000cxyz...",
      "display_name": "My Brand",
      "landing_page_url": "https://example.com/spring"
    }
  ]
}
```

### Create Ad (Spark Ads) — Example Request

```json
POST /open_api/v1.3/ad/create/
{
  "advertiser_id": "123456789",
  "adgroup_id": "111222333",
  "creatives": [
    {
      "ad_name": "Spark - Organic Post Boost",
      "ad_format": "SPARK_ADS",
      "identity_type": "TT_AUTHORIZATION",
      "tiktok_item_id": "7012345678901234567"
    }
  ]
}
```

---

## Reporting API

### Synchronous Report

**Endpoint:** `GET /open_api/v1.3/report/integrated/get/`

Returns paginated report data synchronously. Suitable for smaller date ranges and lower-cardinality queries.

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `advertiser_id` | string | Yes | Advertiser account ID |
| `report_type` | string | Yes | `BASIC`, `AUDIENCE`, `CATALOG`, or `PLAYABLE` |
| `data_level` | string | Yes | `AUCTION_ADVERTISER`, `AUCTION_CAMPAIGN`, `AUCTION_ADGROUP`, or `AUCTION_AD` |
| `dimensions` | string[] | Yes | Grouping dimensions (e.g., `["campaign_id", "stat_time_day"]`) |
| `metrics` | string[] | Yes | Metrics to return (see [Metrics](#available-reporting-metrics)) |
| `start_date` | string | Yes | Start date in `YYYY-MM-DD` format |
| `end_date` | string | Yes | End date in `YYYY-MM-DD` format |
| `filtering` | object[] | No | Filters on dimension values |
| `page` | integer | No | Page number for pagination (default: 1) |
| `page_size` | integer | No | Results per page, max 1000 (default: 20) |
| `order_field` | string | No | Field to sort by |
| `order_type` | string | No | `ASC` or `DESC` |

#### Example Request

```json
GET /open_api/v1.3/report/integrated/get/
?advertiser_id=123456789
&report_type=BASIC
&data_level=AUCTION_CAMPAIGN
&dimensions=["campaign_id","stat_time_day"]
&metrics=["impressions","clicks","spend","ctr","cpm","conversions","cost_per_conversion"]
&start_date=2026-03-01
&end_date=2026-03-21
&page=1
&page_size=100
&order_field=spend
&order_type=DESC
```

#### Example Response

```json
{
  "code": 0,
  "message": "OK",
  "data": {
    "list": [
      {
        "dimensions": {
          "campaign_id": "987654321",
          "stat_time_day": "2026-03-21"
        },
        "metrics": {
          "impressions": "45230",
          "clicks": "1234",
          "spend": "123.45",
          "ctr": "2.73",
          "cpm": "2.73",
          "conversions": "56",
          "cost_per_conversion": "2.20"
        }
      }
    ],
    "page_info": {
      "page": 1,
      "page_size": 100,
      "total_number": 1,
      "total_page": 1
    }
  }
}
```

---

### Available Reporting Dimensions

| Dimension | Description |
|-----------|-------------|
| `stat_time_day` | Date (daily breakdown) — `YYYY-MM-DD` |
| `stat_time_hour` | Hour (hourly breakdown) — `YYYY-MM-DD HH` |
| `campaign_id` | Campaign-level grouping |
| `adgroup_id` | Ad group-level grouping |
| `ad_id` | Ad-level grouping |
| `country_code` | Country (ISO 3166-1 alpha-2) |
| `gender` | Viewer gender |
| `age` | Viewer age group |
| `platform_version` | OS version of the viewer's device |
| `ac` | Network connection type |
| `language` | Viewer language |

---

### Available Reporting Metrics — Complete List

#### Delivery Metrics

| Metric | Description |
|--------|-------------|
| `impressions` | Total number of times the ad was shown |
| `reach` | Unique users who saw the ad |
| `frequency` | Average times each user saw the ad (`impressions / reach`) |
| `clicks` | Total clicks on the ad |
| `ctr` | Click-through rate (`clicks / impressions × 100`) |
| `cpm` | Cost per 1,000 impressions |
| `cpc` | Cost per click |
| `cpa` | Cost per action/conversion |
| `spend` | Total amount spent (in account currency) |
| `cost_per_1000_reached` | Cost to reach 1,000 unique users |

#### Video Metrics

| Metric | Description |
|--------|-------------|
| `video_play_actions` | Total number of video plays started |
| `video_watched_2s` | Video plays watched at least 2 seconds |
| `video_watched_6s` | Video plays watched at least 6 seconds |
| `average_video_play` | Average video play duration (seconds) |
| `average_video_play_per_user` | Average play duration per unique viewer |
| `video_views_p25` | Videos played to 25% of length |
| `video_views_p50` | Videos played to 50% of length |
| `video_views_p75` | Videos played to 75% of length |
| `video_views_p100` | Videos played to completion (100%) |
| `engaged_view` | Engaged views (≥6s watch or an interaction) |
| `engaged_view_15s` | Videos watched at least 15 seconds |

#### Engagement Metrics

| Metric | Description |
|--------|-------------|
| `likes` | Total likes on the ad |
| `comments` | Total comments on the ad |
| `shares` | Total shares of the ad |
| `follows` | Profile follows attributed to the ad |
| `profile_visits` | Profile page visits from the ad |

#### Conversion Metrics

| Metric | Description |
|--------|-------------|
| `conversions` | Total tracked conversion events |
| `cost_per_conversion` | Average cost per conversion |
| `conversion_rate` | `Conversions / clicks × 100` |
| `real_time_conversions` | Real-time conversion count (not de-duped) |
| `real_time_cost_per_conversion` | Real-time cost per conversion |
| `real_time_conversion_rate` | Real-time conversion rate |
| `result` | Primary result count (objective-dependent) |
| `cost_per_result` | Cost per primary result |
| `result_rate` | Primary result rate |

#### App Metrics

| Metric | Description |
|--------|-------------|
| `app_installs` | App install events tracked |
| `cost_per_install` | Cost per app install |
| `app_install_rate` | Install rate |

---

### Async Report Jobs

For large date ranges or high-cardinality dimensions, use the asynchronous report job flow to avoid timeouts.

#### Step 1 — Create Report Job

```http
POST /open_api/v1.3/report/task/create/
```

```json
{
  "advertiser_id": "123456789",
  "report_type": "BASIC",
  "data_level": "AUCTION_AD",
  "dimensions": ["ad_id", "stat_time_day"],
  "metrics": ["impressions", "clicks", "spend", "conversions"],
  "start_date": "2026-01-01",
  "end_date": "2026-03-21"
}
```

Response includes `task_id`.

#### Step 2 — Poll Job Status

```http
GET /open_api/v1.3/report/task/check/?advertiser_id=123456789&task_id=<task_id>
```

Status values: `RUNNING`, `COMPLETED`, `FAILED`

#### Step 3 — Download Results

```http
GET /open_api/v1.3/report/task/download/?advertiser_id=123456789&task_id=<task_id>
```

Returns a pre-signed CSV download URL valid for a limited time.

---

## Custom Audiences

Custom audiences allow targeting or exclusion of specific user sets.

### Endpoints

| Action | Method | Path |
|--------|--------|------|
| Upload audience file | POST | `/dmp/custom_audience/file/upload/` |
| Create audience | POST | `/dmp/custom_audience/create/` |
| Get audiences | GET | `/dmp/custom_audience/get/` |
| Delete audience | POST | `/dmp/custom_audience/delete/` |
| Share audience | POST | `/dmp/custom_audience/share/` |

### Audience Types

| Type | Description |
|------|-------------|
| `CUSTOMER_FILE` | Hashed email or phone number list |
| `APP_ACTIVITY` | Users based on in-app events |
| `WEBSITE_VISITOR` | Users tracked via TikTok Pixel |
| `ENGAGEMENT` | Users who engaged with your TikTok content |

> **Minimum audience size:** 1,000 matched users before the audience can be used for targeting.

### Upload Example

```json
POST /open_api/v1.3/dmp/custom_audience/file/upload/
{
  "advertiser_id": "123456789",
  "calculate_type": "HASH_EMAIL",
  "file_path": "https://your-cdn.example.com/audience.csv"
}
```

---

## Lookalike Audiences

Lookalike audiences find users similar to a source custom audience.

### Endpoints

| Action | Method | Path |
|--------|--------|------|
| Create lookalike | POST | `/dmp/lookalike/create/` |
| Get lookalikes | GET | `/dmp/lookalike/get/` |

### Similarity Levels

| Level | Description |
|-------|-------------|
| `NARROW` | Most similar to source — smallest reach |
| `BALANCED` | Balance of similarity and reach |
| `BROAD` | Widest reach with looser similarity |

### Create Lookalike Example

```json
POST /open_api/v1.3/dmp/lookalike/create/
{
  "advertiser_id": "123456789",
  "custom_audience_id": "audience_id_here",
  "lookalike_spec": {
    "similarity_type": "BALANCED",
    "location_ids": ["6252001"]
  }
}
```

---

## Sandbox Environment

TikTok provides a sandbox (test) environment for development without incurring real ad spend.

- Sandbox advertiser accounts are provisioned via the **Business Center sandbox environment**
- API calls use the **same endpoint URLs** as production
- A separate **sandbox access token** must be obtained from the sandbox Business Center
- No real budget is consumed; ad delivery is simulated
- Creative assets uploaded in sandbox do not serve to real users

---

## Endpoint Quick Reference

### Campaign Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/campaign/create/` | POST | Create a new campaign |
| `/campaign/update/` | POST | Update campaign fields |
| `/campaign/get/` | GET | Retrieve campaigns by filter |
| `/campaign/delete/` | POST | Delete campaigns |
| `/campaign/status/update/` | POST | Enable or disable campaigns |

### Ad Group Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/adgroup/create/` | POST | Create a new ad group |
| `/adgroup/update/` | POST | Update ad group fields |
| `/adgroup/get/` | GET | Retrieve ad groups by filter |
| `/adgroup/delete/` | POST | Delete ad groups |
| `/adgroup/status/update/` | POST | Enable or disable ad groups |

### Ad Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ad/create/` | POST | Create new ads |
| `/ad/update/` | POST | Update ad fields |
| `/ad/get/` | GET | Retrieve ads by filter |
| `/ad/delete/` | POST | Delete ads |
| `/ad/status/update/` | POST | Enable or disable ads |

### Reporting

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/report/integrated/get/` | GET | Synchronous report query |
| `/report/task/create/` | POST | Create async report job |
| `/report/task/check/` | GET | Poll async job status |
| `/report/task/download/` | GET | Get async report download URL |

### Audiences

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/dmp/custom_audience/file/upload/` | POST | Upload audience file |
| `/dmp/custom_audience/create/` | POST | Create custom audience |
| `/dmp/custom_audience/get/` | GET | List custom audiences |
| `/dmp/custom_audience/delete/` | POST | Delete custom audience |
| `/dmp/custom_audience/share/` | POST | Share audience across accounts |
| `/dmp/lookalike/create/` | POST | Create lookalike audience |
| `/dmp/lookalike/get/` | GET | List lookalike audiences |

### Asset Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/file/video/ad/upload/` | POST | Upload video creative asset |
| `/file/image/ad/upload/` | POST | Upload image creative asset |
| `/file/video/ad/info/` | GET | Get video asset metadata |

### OAuth

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/oauth2/access_token/` | POST | Exchange auth code for access token |
| `/oauth2/refresh_token/` | POST | Refresh an access token |
| `/oauth2/advertiser/get/` | GET | List advertiser accounts accessible by token |

---

## Standard Response Envelope

All API responses follow a common structure:

```json
{
  "code": 0,
  "message": "OK",
  "request_id": "unique_request_id",
  "data": { ... }
}
```

| Field | Description |
|-------|-------------|
| `code` | `0` indicates success; non-zero values are error codes |
| `message` | Human-readable status message |
| `request_id` | Unique identifier for the request (use when contacting support) |
| `data` | Response payload; structure varies by endpoint |

### Common Error Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `40001` | Missing required parameter |
| `40002` | Invalid parameter value |
| `40100` | Invalid or expired access token |
| `40101` | Insufficient permissions for this operation |
| `50001` | Internal server error — retry with exponential backoff |
| `50002` | Service temporarily unavailable |
