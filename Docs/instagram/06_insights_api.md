# Instagram Insights API

Source: developers.facebook.com/docs/instagram-api/reference/ig-user/insights
         developers.facebook.com/docs/instagram-api/reference/ig-media/insights
Version: v22.0

---

## Overview

Instagram Insights provides analytics for Instagram professional accounts (Business and Creator). There are two levels:

1. **Account-level insights** — `GET /{ig-user-id}/insights` — metrics for the whole account over time
2. **Media-level insights** — `GET /{ig-media-id}/insights` — metrics for individual posts, reels, or stories

---

## Required Permissions

| Login Type | Permission | Scope |
|-----------|-----------|-------|
| Facebook Login | `instagram_manage_insights` | Account + media insights |
| Facebook Login | `instagram_basic` | Also required alongside insights permission |
| Facebook Login | `pages_read_engagement` | Also required |
| Facebook Login | `ads_management` or `ads_read` | If role granted via Business Manager |
| Instagram Login | `instagram_business_basic` | Account + media insights |

---

## Account-Level Insights

### Endpoint

```
GET /v22.0/{ig-user-id}/insights
  ?metric={metric1,metric2,...}
  &period={period}
  &since={unix-timestamp}
  &until={unix-timestamp}
  &breakdown={breakdown-dimension}
  &access_token={token}
```

**Host:** `graph.facebook.com` (Facebook Login) or `graph.instagram.com` (Instagram Login)

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metric` | Comma-separated list | Yes | One or more metrics (see table below) |
| `period` | Enum | Yes | Time aggregation period |
| `since` | Unix timestamp | No | Start of date range |
| `until` | Unix timestamp | No | End of date range |
| `breakdown` | Enum | No | Dimension to break results down by |
| `timeframe` | Enum | No | Used with newer metrics instead of `period` |
| `metric_type` | Enum | No | `total_value` or `time_series` |

### Period Values

| Period | Description |
|--------|-------------|
| `day` | Daily aggregation |
| `week` | 7-day rolling window |
| `days_28` | 28-day rolling window |
| `month` | Calendar month |
| `lifetime` | All time (since account creation) |

### Account Metrics (Older — period-based)

| Metric | Supported Periods | Description |
|--------|------------------|-------------|
| `impressions` | `day`, `week`, `days_28` | Total times content from account was displayed |
| `reach` | `day`, `week`, `days_28` | Unique accounts that saw content |
| `follower_count` | `day` | Net new followers gained |
| `profile_views` | `day` | Number of times profile was viewed |
| `website_clicks` | `day` | Taps on website link in profile |
| `email_contacts` | `day` | Taps on email link in profile |
| `phone_call_clicks` | `day` | Taps on call link in profile |
| `text_message_clicks` | `day` | Taps on text message link in profile |
| `get_directions_clicks` | `day` | Taps on directions link in profile |
| `online_followers` | `lifetime` | Followers online by hour (returns array of 24 values) |
| `audience_city` | `lifetime` | Top cities of followers |
| `audience_country` | `lifetime` | Top countries of followers |
| `audience_gender_age` | `lifetime` | Follower breakdown by gender and age range |
| `audience_locale` | `lifetime` | Top locales of followers |

### Account Metrics (Newer — v18+ with `metric_type` and `timeframe`)

These metrics use `metric_type=total_value` or `metric_type=time_series` and `timeframe` instead of `period`:

| Metric | Description |
|--------|-------------|
| `reach` | Unique accounts reached |
| `impressions` | Total impressions |
| `accounts_engaged` | Accounts that interacted with content |
| `total_interactions` | Total interactions (likes + comments + shares + saves + replies) |
| `likes` | Total likes |
| `comments` | Total comments |
| `shares` | Total shares |
| `saves` | Total saves |
| `replies` | Total story replies |
| `profile_views` | Profile views |
| `profile_links_taps` | Taps on links in profile |
| `website_clicks` | Website link taps |
| `email_contacts` | Email link taps |
| `phone_call_clicks` | Phone call taps |
| `text_message_clicks` | Text message taps |
| `get_directions_clicks` | Directions taps |
| `follower_count` | Followers gained and lost |

### Timeframe Values (newer metrics)

| Timeframe | Description |
|-----------|-------------|
| `last_14_days` | Previous 14 days |
| `last_30_days` | Previous 30 days |
| `last_90_days` | Previous 90 days |
| `prev_month` | Previous calendar month |
| `this_month` | Current calendar month to date |
| `this_week` | Current week to date |

### Account Breakdown Dimensions

| Breakdown | Valid Metrics | Values |
|-----------|--------------|--------|
| `follow_type` | `reach`, `impressions` | `FOLLOWER`, `NON_FOLLOWER` |
| `media_product_type` | `reach`, `impressions`, `total_interactions` | `POST`, `REEL`, `STORY` |
| `city` | Audience metrics | Top cities |
| `country` | Audience metrics | Two-letter country codes |
| `age` | Audience metrics | Age ranges: `13-17`, `18-24`, `25-34`, `35-44`, `45-54`, `55-64`, `65+` |
| `gender` | Audience metrics | `M` (male), `F` (female), `U` (unknown) |

### Example — Daily Reach for Last 30 Days

```
GET /v22.0/17841405822304914/insights
  ?metric=reach,impressions,profile_views
  &period=day
  &since=1700000000
  &until=1702592000
  &access_token={token}
```

Response:
```json
{
  "data": [
    {
      "name": "reach",
      "period": "day",
      "values": [
        {"value": 1234, "end_time": "2024-01-01T08:00:00+0000"},
        {"value": 1567, "end_time": "2024-01-02T08:00:00+0000"}
      ],
      "id": "17841405822304914/insights/reach/day"
    }
  ]
}
```

### Example — Reach with Follower/Non-Follower Breakdown

```
GET /v22.0/17841405822304914/insights
  ?metric=reach
  &metric_type=total_value
  &timeframe=last_30_days
  &breakdown=follow_type
  &access_token={token}
```

Response:
```json
{
  "data": [
    {
      "name": "reach",
      "period": "lifetime",
      "title": "Reach",
      "total_value": {
        "value": 45230,
        "breakdowns": [
          {
            "dimension_keys": ["follow_type"],
            "results": [
              {"dimension_values": ["FOLLOWER"], "value": 28000},
              {"dimension_values": ["NON_FOLLOWER"], "value": 17230}
            ]
          }
        ]
      }
    }
  ]
}
```

### Example — Audience Demographics

```
GET /v22.0/17841405822304914/insights
  ?metric=audience_gender_age
  &period=lifetime
  &access_token={token}
```

Response:
```json
{
  "data": [
    {
      "name": "audience_gender_age",
      "period": "lifetime",
      "values": [
        {
          "value": {
            "F.13-17": 12,
            "F.18-24": 234,
            "F.25-34": 445,
            "M.18-24": 189,
            "M.25-34": 398
          },
          "end_time": "2024-01-15T08:00:00+0000"
        }
      ]
    }
  ]
}
```

---

## Media-Level Insights

### Endpoint

```
GET /v22.0/{ig-media-id}/insights
  ?metric={metric1,metric2,...}
  &access_token={token}
```

**Note:** Metrics available depend on the `media_product_type` of the media object.

### Feed Post Metrics

For `media_product_type = FEED` (images, videos, carousels):

| Metric | Description |
|--------|-------------|
| `impressions` | Total times the media was displayed |
| `reach` | Unique accounts that saw the media |
| `engagement` | Likes + comments + saves + carousel swipes |
| `saved` | Unique accounts that saved the post |
| `likes` | Number of likes |
| `comments` | Number of comments |
| `shares` | Number of shares |
| `video_views` | Video views (3+ seconds) — videos only |
| `follows` | Follows attributed to this post |
| `profile_visits` | Profile visits from this post |
| `total_interactions` | Total interactions |

### Reel Metrics

For `media_product_type = REELS`:

| Metric | Description |
|--------|-------------|
| `comments` | Number of comments |
| `likes` | Number of likes |
| `plays` | Number of times reel started playing |
| `reach` | Unique accounts that saw the reel |
| `saved` | Unique accounts that saved the reel |
| `shares` | Number of shares |
| `total_interactions` | Total interactions (likes + comments + shares + saves) |

### Story Metrics

For `media_product_type = STORY`:

| Metric | Description |
|--------|-------------|
| `exits` | Times a person left the story to return to the feed |
| `impressions` | Total times the story was displayed |
| `reach` | Unique accounts that saw the story |
| `replies` | Replies sent to the story |
| `taps_forward` | Times the story was tapped to skip to the next story |
| `taps_back` | Times the story was tapped to replay the previous story |
| `follows` | Follows from this story |
| `profile_visits` | Profile visits from this story |
| `shares` | Shares of this story |
| `total_interactions` | Total interactions |
| `navigation` | Object with `taps_forward`, `taps_back`, `swipe_aways`, `exits` |

**Story metrics notes:**
- Story insights are only available **while the story is live** (within 24 hours) OR via the `story_insights` webhook after expiry
- Subscribe to `story_insights` webhook to capture metrics after stories expire

### Example — Feed Post Insights

```
GET /v22.0/17895695668004550/insights
  ?metric=impressions,reach,likes,comments,shares,saved,total_interactions
  &access_token={token}
```

Response:
```json
{
  "data": [
    {"name": "impressions", "period": "lifetime", "values": [{"value": 4521}], "id": "..."},
    {"name": "reach",       "period": "lifetime", "values": [{"value": 3890}], "id": "..."},
    {"name": "likes",       "period": "lifetime", "values": [{"value": 312}],  "id": "..."},
    {"name": "comments",    "period": "lifetime", "values": [{"value": 28}],   "id": "..."},
    {"name": "shares",      "period": "lifetime", "values": [{"value": 45}],   "id": "..."},
    {"name": "saved",       "period": "lifetime", "values": [{"value": 87}],   "id": "..."},
    {"name": "total_interactions", "period": "lifetime", "values": [{"value": 472}], "id": "..."}
  ]
}
```

### Example — Story Insights

```
GET /v22.0/17862253585030136/insights
  ?metric=impressions,reach,exits,taps_forward,taps_back,replies
  &access_token={token}
```

Response:
```json
{
  "data": [
    {"name": "impressions",  "period": "lifetime", "values": [{"value": 1200}], "id": "..."},
    {"name": "reach",        "period": "lifetime", "values": [{"value": 1050}], "id": "..."},
    {"name": "exits",        "period": "lifetime", "values": [{"value": 89}],   "id": "..."},
    {"name": "taps_forward", "period": "lifetime", "values": [{"value": 340}],  "id": "..."},
    {"name": "taps_back",    "period": "lifetime", "values": [{"value": 42}],   "id": "..."},
    {"name": "replies",      "period": "lifetime", "values": [{"value": 15}],   "id": "..."}
  ]
}
```

### Example — Reel Insights

```
GET /v22.0/17920238422030506/insights
  ?metric=plays,reach,likes,comments,shares,saved,total_interactions
  &access_token={token}
```

---

## Media Insights Availability by Type

| Metric | Feed Image | Feed Video | Carousel | Reel | Story |
|--------|-----------|-----------|---------|------|-------|
| `impressions` | ✓ | ✓ | ✓ | — | ✓ |
| `reach` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `likes` | ✓ | ✓ | ✓ | ✓ | — |
| `comments` | ✓ | ✓ | ✓ | ✓ | — |
| `shares` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `saved` | ✓ | ✓ | ✓ | ✓ | — |
| `video_views` | — | ✓ | — | — | — |
| `plays` | — | — | — | ✓ | — |
| `engagement` | ✓ | ✓ | ✓ | — | — |
| `total_interactions` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `profile_visits` | ✓ | ✓ | ✓ | — | ✓ |
| `follows` | ✓ | ✓ | ✓ | — | ✓ |
| `exits` | — | — | — | — | ✓ |
| `taps_forward` | — | — | — | — | ✓ |
| `taps_back` | — | — | — | — | ✓ |
| `replies` | — | — | — | — | ✓ |
| `navigation` | — | — | — | — | ✓ |

---

## Important Limitations

| Limitation | Details |
|-----------|---------|
| Story insights window | Available only while story is live (24h) or via `story_insights` webhook after expiry |
| Aggregated values | Do not include ads-driven data |
| Age-gated accounts | Data not returned for age-gated accounts |
| Minimum reach threshold | Some metrics hidden below a minimum reach threshold |
| Unavailable metrics | Requesting a metric not available for a media type returns an error |
| Lifetime period | Required for `audience_*` metrics and story metrics |
| Personal accounts | Insights not available for non-professional accounts |

---

## Insights via Webhook (story_insights)

Story insights are delivered via webhook after a story expires. Subscribe with:

```
POST /v22.0/me/subscribed_apps
  ?subscribed_fields=story_insights
  &access_token={token}
```

Webhook payload:
```json
{
  "field": "story_insights",
  "value": {
    "media_id": "17895695668004550",
    "exits": 15,
    "impressions": 1200,
    "reach": 1050,
    "replies": 3,
    "taps_forward": 340,
    "taps_back": 42
  }
}
```
