# Facebook Marketing (Ads) API

Source: developers.facebook.com/docs/marketing-api
Version: v22.0

---

## Overview

The Marketing API lets you manage and report on Facebook and Instagram advertising. The campaign hierarchy is:

```
Ad Account → Campaign → Ad Set → Ad → Ad Creative
```

All ad account endpoints use the format: `act_{ad_account_id}`

---

## Required Permissions

| Permission | Access |
|------------|--------|
| `ads_management` | Full CRUD on campaigns, ad sets, ads |
| `ads_read` | Read-only insights and reporting |
| `business_management` | Business Manager operations |
| `pages_manage_ads` | Manage page-level ads |
| `leads_retrieval` | Download lead ad form submissions |

Task permissions on Ad Account:
- `MANAGE` — account modifications, spending
- `ADVERTISE` — create and manage ads
- `ANALYZE` — view analytics
- `DRAFT` — create drafts
- `AA_ANALYZE` — Advantage+ analysis

---

## Ad Account Node

```
GET /v22.0/act_{AD_ACCOUNT_ID}?fields={fields}&access_token={token}
```

### Identity & Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | `act_{ad_account_id}` |
| `account_id` | string | Numeric account ID |
| `account_status` | int | 1=ACTIVE, 2=DISABLED, 3=UNSETTLED, 7=PENDING_RISK_REVIEW, 9=IN_GRACE_PERIOD, 100=PENDING_CLOSURE, 101=CLOSED, 201=ANY_ACTIVE, 202=ANY_CLOSED |
| `created_time` | datetime | Account creation time |
| `name` | string | Account name |
| `currency` | string | Account currency (e.g., `USD`) |

### Financial Fields

| Field | Type | Description |
|-------|------|-------------|
| `amount_spent` | string | Total spent against spend cap (in cents) |
| `balance` | string | Outstanding balance |
| `spend_cap` | string | Max spend limit (0 = unlimited) |
| `funding_source` | string | Payment method ID |
| `funding_source_details` | object | Payment method info including coupons |

### Business Information

| Field | Type | Description |
|-------|------|-------------|
| `business_name` | string | Business name |
| `business_city` | string | City |
| `business_state` | string | State |
| `business_zip` | string | Zip code |
| `business_country_code` | string | Country code |
| `business_street` | string | Street address |
| `end_advertiser` | string | Target entity (Page/App ID) |
| `media_agency` | string | Agency managing account |
| `partner` | string | Advertising partner ID |
| `owner` | string | Account owner ID |

### Operational Fields

| Field | Type | Description |
|-------|------|-------------|
| `timezone_id` | int | Timezone ID |
| `timezone_name` | string | Timezone name |
| `timezone_offset_hours_utc` | float | UTC offset |
| `age` | float | Days account has been open |
| `is_personal` | int | Whether personal use account |
| `is_prepay_account` | bool | Prepay vs postpay |
| `disable_reason` | int | Why disabled (if applicable) |
| `capabilities` | array | Account capabilities list |
| `can_create_brand_lift_study` | bool | Brand lift eligibility |
| `opportunity_score` | float | 0–100 optimization score |

### Compliance

| Field | Type | Description |
|-------|------|-------------|
| `default_dsa_payor` | string | Digital Services Act payor |
| `default_dsa_beneficiary` | string | DSA beneficiary |
| `brand_safety_content_filter_levels` | array | Content filtering settings |
| `has_page_authorized_adaccount` | bool | Political content authorization |
| `tax_id` | string | Tax ID |
| `tax_id_type` | string | Tax ID type |
| `tax_id_status` | int | Tax ID status |

### Ad Account Edges

| Edge | Description |
|------|-------------|
| `adcreatives` | Creative assets |
| `ads` | All ads in account |
| `adsets` | All ad sets |
| `campaigns` | All campaigns |
| `customaudiences` | Custom audiences |
| `customconversions` | Conversion events |
| `advideos` | Video assets |
| `connected_instagram_accounts` | Linked Instagram accounts |
| `promote_pages` | Pages promoted via account |
| `activities` | Account activity log |
| `assigned_users` | Users with access |
| `delivery_estimate` | Projected delivery metrics |
| `reachestimate` | Estimated reach |
| `insights` | Reporting and analytics |
| `saved_audiences` | Saved audience definitions |
| `pixels` | Associated Meta Pixels |

### Limits
- Max 25 ad accounts per person
- Max 25 users per account
- Regular accounts: 6,000 non-archived ads, ad sets, and campaigns each
- Bulk accounts: 50,000 non-archived ads/ad sets, 10,000 campaigns

### Example
```
GET /v22.0/act_{AD_ACCOUNT_ID}
  ?fields=id,account_id,account_status,amount_spent,currency,spend_cap,timezone_name
  &access_token={TOKEN}
```

---

## Campaign Node

```
GET /v22.0/{campaign-id}?fields={fields}&access_token={token}
GET /v22.0/act_{AD_ACCOUNT_ID}/campaigns?fields={fields}&access_token={token}
```

### Campaign Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Campaign ID |
| `name` | string | Campaign name |
| `account_id` | string | Parent ad account |
| `objective` | string | Campaign objective (see below) |
| `status` | string | `ACTIVE`, `PAUSED`, `DELETED`, `ARCHIVED` |
| `configured_status` | string | Same as status |
| `effective_status` | string | Current operational status |
| `created_time` | datetime | Creation time |
| `updated_time` | datetime | Last update |
| `start_time` | datetime | Campaign start |
| `stop_time` | datetime | Campaign end |
| `daily_budget` | int64 | Daily spend limit (in cents) |
| `lifetime_budget` | int64 | Total spend limit (in cents) |
| `budget_remaining` | string | Unspent budget |
| `spend_cap` | int64 | Max spend; set to 922337203685478 to remove cap |
| `buying_type` | string | `AUCTION`, `RESERVED` |
| `bid_strategy` | string | Bid strategy |
| `promoted_object` | object | Object being promoted |
| `special_ad_categories` | array | `NONE`, `EMPLOYMENT`, `HOUSING`, `CREDIT`, `ISSUES_ELECTIONS_POLITICS` |
| `special_ad_category_country` | array | Countries for special ad category |
| `adlabels` | array | Labels |
| `issues_info` | array | Delivery blockers |
| `is_adset_budget_sharing_enabled` | bool | Advantage campaign budget |
| `can_use_spend_cap` | bool | Whether spend cap can be used |

### Campaign Objectives

| Objective | Description |
|-----------|-------------|
| `APP_INSTALLS` | Drive app installs |
| `BRAND_AWARENESS` | Increase brand awareness |
| `CONVERSIONS` | Website conversions |
| `EVENT_RESPONSES` | Event RSVPs |
| `LEAD_GENERATION` | Lead ads |
| `LINK_CLICKS` | Drive website traffic |
| `LOCAL_AWARENESS` | Reach people near a business |
| `MESSAGES` | Messenger conversations |
| `OFFER_CLAIMS` | Promote offers |
| `OUTCOME_LEADS` | Leads (new objective naming) |
| `OUTCOME_SALES` | Sales (new naming) |
| `OUTCOME_TRAFFIC` | Traffic (new naming) |
| `OUTCOME_AWARENESS` | Awareness (new naming) |
| `OUTCOME_ENGAGEMENT` | Engagement (new naming) |
| `OUTCOME_APP_PROMOTION` | App promotion (new naming) |
| `PAGE_LIKES` | Page likes |
| `POST_ENGAGEMENT` | Post engagement |
| `REACH` | Maximize reach |
| `STORE_VISITS` | In-store visits |
| `VIDEO_VIEWS` | Video views |

### Create Campaign

```
POST /v22.0/act_{AD_ACCOUNT_ID}/campaigns
  name=My Campaign
  objective=OUTCOME_TRAFFIC
  status=PAUSED
  special_ad_categories=[]
  access_token={TOKEN}
```

Required: `name`, `objective`, `special_ad_categories`

---

## Ad Set Node

```
GET /v22.0/{adset-id}?fields={fields}&access_token={token}
GET /v22.0/act_{AD_ACCOUNT_ID}/adsets?fields={fields}&access_token={token}
GET /v22.0/{campaign-id}/adsets?fields={fields}&access_token={token}
```

### Key Ad Set Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Ad Set ID |
| `name` | string | Ad set name |
| `campaign_id` | string | Parent campaign |
| `account_id` | string | Ad account |
| `status` | string | `ACTIVE`, `PAUSED`, `DELETED`, `ARCHIVED` |
| `effective_status` | string | Operational status |
| `daily_budget` | int64 | Daily limit (in cents) |
| `lifetime_budget` | int64 | Total limit (in cents) |
| `budget_remaining` | string | Remaining budget |
| `bid_amount` | int64 | Bid amount in cents |
| `bid_strategy` | string | `LOWEST_COST_WITHOUT_CAP`, `LOWEST_COST_WITH_BID_CAP`, `COST_CAP`, `LOWEST_COST_WITH_MIN_ROAS` |
| `optimization_goal` | string | What to optimize for |
| `billing_event` | string | When charged: `IMPRESSIONS`, `LINK_CLICKS`, `PAGE_LIKES`, `POST_ENGAGEMENT`, `VIDEO_VIEWS` |
| `start_time` | datetime | Start time |
| `end_time` | datetime | End time |
| `targeting` | object | Audience targeting spec |
| `promoted_object` | object | Object being promoted |
| `pacing_type` | array | `standard`, `day_parting` |
| `attribution_spec` | array | Attribution window spec |
| `destination_type` | string | `WEBSITE`, `APP`, `MESSENGER`, `INSTAGRAM_DIRECT` |

### Optimization Goals

| Goal | Description |
|------|-------------|
| `NONE` | No optimization |
| `APP_INSTALLS` | App installs |
| `AD_RECALL_LIFT` | Brand recall lift |
| `CLICKS` | Link clicks |
| `ENGAGED_USERS` | Engaged users |
| `EVENT_RESPONSES` | Event RSVPs |
| `IMPRESSIONS` | Total impressions |
| `LEAD_GENERATION` | Lead form fills |
| `QUALITY_LEAD` | High-quality leads |
| `LINK_CLICKS` | Link clicks |
| `OFFSITE_CONVERSIONS` | Website conversions |
| `PAGE_LIKES` | Page likes |
| `POST_ENGAGEMENT` | Post engagement |
| `QUALITY_CALL` | Quality calls |
| `REACH` | People reached |
| `REPLIES` | Messenger replies |
| `SOCIAL_IMPRESSIONS` | Social context impressions |
| `THRUPLAY` | Video ThruPlay views |
| `VALUE` | Purchase value |
| `VISIT_INSTAGRAM_PROFILE` | Instagram profile visits |

---

## Ad Node

```
GET /v22.0/{ad-id}?fields={fields}&access_token={token}
GET /v22.0/act_{AD_ACCOUNT_ID}/ads?fields={fields}&access_token={token}
GET /v22.0/{adset-id}/ads?fields={fields}&access_token={token}
```

### Ad Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Ad ID |
| `name` | string | Ad name |
| `account_id` | string | Ad account |
| `campaign_id` | string | Parent campaign |
| `adset_id` | string | Parent ad set |
| `adset` | object | Parent ad set object |
| `campaign` | object | Parent campaign object |
| `status` | string | `ACTIVE`, `PAUSED`, `DELETED`, `ARCHIVED` |
| `configured_status` | string | Same as status |
| `effective_status` | string | `ACTIVE`, `PAUSED`, `DELETED`, `ARCHIVED`, `WITH_ISSUES`, `IN_PROCESS`, `PENDING_REVIEW`, `DISAPPROVED`, `PREAPPROVED`, `PENDING_BILLING_INFO`, `CAMPAIGN_PAUSED`, `ADSET_PAUSED` |
| `created_time` | datetime | Creation time |
| `updated_time` | datetime | Last update |
| `creative` | object | Ad creative `{"id": "...", "name": "..."}` |
| `ad_review_feedback` | object | Review feedback if disapproved |
| `issues_info` | array | Delivery blockers |
| `recommendations` | array | Optimization suggestions |
| `bid_amount` | int64 | Bid (set via ad set) |
| `tracking_specs` | array | Conversion tracking config |
| `conversion_domain` | string | Domain where conversions occur |
| `preview_shareable_link` | string | Ad preview URL |
| `adlabels` | array | Labels |
| `source_ad_id` | string | Original ad ID if copied |
| `display_sequence` | int | Ordering within campaign |

### Create Ad

```
POST /v22.0/act_{AD_ACCOUNT_ID}/ads
  name=My Ad
  adset_id={ADSET_ID}
  creative={"creative_id": "{CREATIVE_ID}"}
  status=PAUSED
  access_token={TOKEN}
```

Note: New ads start in pending state and require Facebook review.

---

## Ad Insights (Reporting)

```
GET /v22.0/{object-id}/insights
  ?fields={fields}
  &level={level}
  &date_preset={preset}
  &breakdowns={breakdowns}
  &action_breakdowns={action_breakdowns}
  &access_token={TOKEN}
```

Object can be: `act_{ad_account_id}`, `{campaign-id}`, `{adset-id}`, `{ad-id}`

### Level Parameter

| Value | Description |
|-------|-------------|
| `account` | Aggregate at ad account level |
| `campaign` | Aggregate at campaign level |
| `adset` | Aggregate at ad set level |
| `ad` | Individual ad level |

### Core Insight Fields

| Field | Description |
|-------|-------------|
| `impressions` | Times ads were on screen |
| `reach` | Unique accounts that saw ads at least once |
| `clicks` | Total clicks on ads |
| `unique_clicks` | Unique people who clicked |
| `ctr` | Click-through rate (clicks / impressions × 100) |
| `unique_ctr` | Unique CTR |
| `cpm` | Cost per 1,000 impressions |
| `cpc` | Average cost per click (all clicks) |
| `cpp` | Cost per 1,000 accounts reached |
| `spend` | Total spend |
| `frequency` | Average number of times each person saw the ad |

### Conversion & Action Fields

| Field | Description |
|-------|-------------|
| `actions` | Total actions attributed: array of `{action_type, value}` |
| `action_values` | Total value of attributed conversions |
| `conversions` | Conversion events attributed to ads |
| `cost_per_action_type` | Average cost per action type |
| `cost_per_conversion` | Cost per conversion event |
| `unique_actions` | Unique action counts |
| `cost_per_unique_action_type` | Cost per unique action |
| `outbound_clicks` | Clicks taking people off Facebook |
| `outbound_clicks_ctr` | Outbound CTR |
| `website_purchase_roas` | Return on ad spend for website purchases |
| `purchase_roas` | Overall ROAS |
| `catalog_segment_value` | Catalog segment value |

### Video Fields

| Field | Description |
|-------|-------------|
| `video_p25_watched_actions` | Views reaching 25% of video |
| `video_p50_watched_actions` | Views reaching 50% |
| `video_p75_watched_actions` | Views reaching 75% |
| `video_p95_watched_actions` | Views reaching 95% |
| `video_p100_watched_actions` | Complete views (100%) |
| `video_thruplay_watched_actions` | ThruPlay views (15+ sec or full video) |
| `video_avg_time_watched_actions` | Average watch time |
| `video_play_actions` | Total video plays |
| `video_play_curve_actions` | Play retention curve |

### Reach & Delivery Fields

| Field | Description |
|-------|-------------|
| `date_start` | Start date of the data window |
| `date_stop` | End date of the data window |
| `account_id` | Ad account ID |
| `account_name` | Ad account name |
| `campaign_id` | Campaign ID |
| `campaign_name` | Campaign name |
| `adset_id` | Ad set ID |
| `adset_name` | Ad set name |
| `ad_id` | Ad ID |
| `ad_name` | Ad name |
| `objective` | Campaign objective |
| `buying_type` | `AUCTION` or `RESERVED` |
| `full_view_reach` | Unique accounts who saw the full ad |
| `full_view_impressions` | Full view impressions |
| `instant_experience_clicks_to_open` | Instant Experience opens |
| `instant_experience_clicks_to_start` | Instant Experience starts |
| `instant_experience_outbound_clicks` | Outbound clicks from Instant Experience |

### Common Action Types

| Action Type | Description |
|-------------|-------------|
| `link_click` | Clicks on ad links |
| `post_engagement` | All post engagements |
| `post_reaction` | Reactions on the post |
| `comment` | Comments on the post |
| `post` | Shares |
| `page_engagement` | All page engagements |
| `page_like` | Page likes |
| `checkin` | Check-ins |
| `rsvp` | Event RSVPs |
| `offsite_conversion.fb_pixel_purchase` | Pixel purchase event |
| `offsite_conversion.fb_pixel_lead` | Pixel lead event |
| `offsite_conversion.fb_pixel_add_to_cart` | Add to cart |
| `offsite_conversion.fb_pixel_initiate_checkout` | Begin checkout |
| `offsite_conversion.fb_pixel_view_content` | View content |
| `offsite_conversion.fb_pixel_search` | Search |
| `app_install` | App installs |
| `app_use` | App usage |
| `mobile_app_install` | Mobile app installs |
| `mobile_app_purchase` | In-app purchases |
| `lead` | Lead form submissions |
| `onsite_conversion.messaging_conversation_started_7d` | Messenger conversations |

### Date Presets

| Preset | Range |
|--------|-------|
| `today` | Today |
| `yesterday` | Yesterday |
| `last_3d` | Last 3 days |
| `last_7d` | Last 7 days |
| `last_14d` | Last 14 days |
| `last_28d` | Last 28 days |
| `last_30d` | Last 30 days |
| `last_90d` | Last 90 days |
| `last_month` | Previous calendar month |
| `this_month` | Current calendar month |
| `this_quarter` | Current quarter |
| `last_week_mon_sun` | Mon–Sun last week |
| `last_week_sun_sat` | Sun–Sat last week |
| `maximum` | All available data |

Custom range: use `time_range={"since": "2025-01-01", "until": "2025-01-31"}` or `since` and `until` parameters.

### Breakdown Dimensions

| Breakdown | Values |
|-----------|--------|
| `age` | `13-17`, `18-24`, `25-34`, `35-44`, `45-54`, `55-64`, `65+` |
| `gender` | `male`, `female`, `unknown` |
| `country` | ISO country code |
| `region` | Region/state |
| `dma` | Designated market area |
| `impression_device` | Device type |
| `publisher_platform` | `facebook`, `instagram`, `audience_network`, `messenger`, `whatsapp_business` |
| `platform_position` | `feed`, `right_hand_column`, `instant_article`, `marketplace`, `search`, `video_feeds`, `story`, `reels`, `instagram_explore`, `instagram_stream`, etc. |
| `device_platform` | `mobile`, `desktop` |
| `product_id` | Individual product from catalog |
| `frequency_value` | Impression frequency bucket |
| `hourly_stats_aggregated_by_advertiser_time_zone` | Hour of day |

### Action Breakdowns

| Breakdown | Description |
|-----------|-------------|
| `action_type` | Type of action taken |
| `action_target_id` | ID of target (page, app, etc.) |
| `action_destination` | Destination URL or app |
| `action_carousel_card_id` | Carousel card |
| `action_carousel_card_name` | Carousel card name |
| `action_reaction` | Reaction type |
| `action_video_sound` | Sound on/off |
| `action_video_type` | Video type (auto-play, click-to-play) |

### Attribution Windows

| Window | Description |
|--------|-------------|
| `1d_click` | Conversions within 1 day of clicking |
| `7d_click` | Within 7 days of clicking (default) |
| `28d_click` | Within 28 days of clicking |
| `1d_view` | Within 1 day of viewing |
| `7d_view` | Within 7 days of viewing |

Specify with: `action_attribution_windows=["7d_click","1d_view"]`

---

## Async Jobs (for Large Datasets)

For large reports, use async mode:

```
POST /v22.0/act_{AD_ACCOUNT_ID}/insights
  fields=impressions,clicks,spend
  level=ad
  date_preset=last_30d
  access_token={TOKEN}
```

Response:
```json
{"report_run_id": "12345678"}
```

Check status:
```
GET /v22.0/{report_run_id}?access_token={TOKEN}
```

Download results when `async_status` = `"Job Completed"`:
```
GET /v22.0/{report_run_id}/insights?access_token={TOKEN}
```

### Async Status Values
- `Job Not Started`
- `Job Started`
- `Job Running`
- `Job Completed`
- `Job Failed`
- `Job Skipped`

---

## Rate Limits (Marketing API)

| Tier | Calls per Hour |
|------|---------------|
| Development | 1,000 |
| Basic | 10,000 |
| Standard | 50,000 |
| Advanced | Custom |

BUC limits (Advanced Access):
- Ads Insights: `190,000 + 400 × active ads` per hour
- Ads Management: `100,000 + 40 × active ads` per hour

Rate limit headers:
- `X-Business-Use-Case-Usage`: includes `call_count`, `total_cputime`, `total_time`, `type`, `estimated_time_to_regain_access`
- `X-Ad-Account-Usage`: `{"acc_id_util_pct": 9.67}`

---

## Example Requests

### Get campaign performance last 30 days
```
GET /v22.0/act_{AD_ACCOUNT_ID}/insights
  ?fields=campaign_name,impressions,clicks,spend,ctr,cpm,cpc,reach,actions
  &level=campaign
  &date_preset=last_30d
  &access_token={TOKEN}
```

### Get ad set breakdown by age and gender
```
GET /v22.0/act_{AD_ACCOUNT_ID}/insights
  ?fields=adset_name,impressions,clicks,spend,reach
  &level=adset
  &breakdowns=age,gender
  &date_preset=last_7d
  &access_token={TOKEN}
```

### Get ad-level platform breakdown
```
GET /v22.0/act_{AD_ACCOUNT_ID}/insights
  ?fields=ad_name,impressions,clicks,spend,ctr
  &level=ad
  &breakdowns=publisher_platform,platform_position
  &date_preset=last_14d
  &access_token={TOKEN}
```

### Get all campaigns with budget info
```
GET /v22.0/act_{AD_ACCOUNT_ID}/campaigns
  ?fields=id,name,status,objective,daily_budget,lifetime_budget,budget_remaining,spend_cap,effective_status
  &access_token={TOKEN}
```

### Get ad account overview
```
GET /v22.0/act_{AD_ACCOUNT_ID}
  ?fields=id,account_id,account_status,amount_spent,currency,spend_cap,timezone_name
  &access_token={TOKEN}
```

### Get action breakdown by type
```
GET /v22.0/act_{AD_ACCOUNT_ID}/insights
  ?fields=campaign_name,actions,cost_per_action_type,action_values
  &level=campaign
  &action_breakdowns=action_type
  &date_preset=last_30d
  &access_token={TOKEN}
```

---

## Filtering Insights

Add `filtering` as a JSON array parameter:

```
filtering=[{"field":"effective_status","operator":"IN","value":["ACTIVE","PAUSED"]}]
```

### Filter Operators

| Operator | Description |
|----------|-------------|
| `EQUAL` | Exact match |
| `NOT_EQUAL` | Not equal |
| `GREATER_THAN` | Greater than (numeric) |
| `GREATER_THAN_OR_EQUAL` | Greater than or equal |
| `LESS_THAN` | Less than |
| `LESS_THAN_OR_EQUAL` | Less than or equal |
| `IN` | Value in list |
| `NOT_IN` | Value not in list |
| `CONTAIN` | String contains |
| `NOT_CONTAIN` | String does not contain |
| `START_WITH` | String starts with |
| `END_WITH` | String ends with |
| `IN_RANGE` | Numeric range |
| `NOT_IN_RANGE` | Not in numeric range |

### Filterable Fields
- Object names: `campaign.name`, `adset.name`, `ad.name`
- IDs: `campaign_id`, `adset_id`, `ad_id`
- Status: `effective_status` → `ACTIVE`, `PAUSED`, `DELETED`, `ARCHIVED`, `ALL`
- Metrics: `spend`, `impressions`, `reach`, `clicks`, `ctr`, `cpm`, `cpc`
- Dates: `date_start`, `date_stop`

---

## Time Increment (Granularity)

| `time_increment` value | Description |
|------------------------|-------------|
| `1` | Daily breakdown |
| `7` | Weekly breakdown |
| `monthly` | Monthly aggregation |
| `all_days` | Single row for the entire range |

---

## Additional Action Types

The `actions` array supports many more action types beyond the core set:

| Action Type | Description |
|-------------|-------------|
| `onsite_conversion.post_save` | Post saves |
| `onsite_conversion.lead_grouped` | Grouped onsite leads |
| `onsite_web_lead` | Onsite web leads |
| `contact` | Contact actions |
| `find_location` | Find location clicks |
| `schedule` | Schedule actions |
| `start_trial` | Start trial |
| `submit_application` | Application submissions |
| `subscribe` | Subscriptions |
| `donate` | Donations |
| `click_to_call_call_confirm` | Call confirmations |
| `messenger_conversation_started_7d` | Messenger conversations (7-day) |
| `onsite_conversion.messaging_first_reply` | First reply in messaging |
| `onsite_conversion.messaging_conversation_started_7d` | Messaging conversations started |
| `omni_view_content` | Omni-channel view content |
| `omni_add_to_cart` | Omni-channel add to cart |
| `omni_initiated_checkout` | Omni-channel initiated checkout |
| `omni_complete_registration` | Omni-channel registration |
| `omni_purchase` | Omni-channel purchases |
| `omni_search` | Omni-channel search |
| `omni_activate_app` | Omni-channel app activation |
| `omni_app_install` | Omni-channel app installs |
| `omni_level_achieved` | Level achieved (gaming) |
| `omni_achievement_unlocked` | Achievement unlocked (gaming) |
| `omni_spent_credits` | Credits spent (gaming) |
| `offsite_conversion.fb_pixel_complete_registration` | Pixel registration events |
| `offsite_conversion.fb_pixel_add_payment_info` | Pixel payment info added |
| `offsite_conversion.fb_pixel_add_to_wishlist` | Pixel add to wishlist |
| `offsite_conversion.fb_pixel_custom` | Custom pixel events |

---

## Ad Creative Fields

```
GET /v22.0/{creative-id}?fields={fields}&access_token={token}
GET /v22.0/act_{AD_ACCOUNT_ID}/adcreatives?fields={fields}&access_token={token}
```

| Field | Description |
|-------|-------------|
| `id` | Creative ID |
| `account_id` | Parent ad account |
| `actor_id` | Page running the ad |
| `name` | Creative name |
| `title` | Ad headline/title |
| `body` | Ad body text |
| `link_url` | Destination URL |
| `image_hash` | Hash of uploaded image |
| `image_url` | Image URL |
| `video_id` | Uploaded video ID |
| `thumbnail_url` | Video thumbnail URL |
| `thumbnail_id` | Video thumbnail ID |
| `call_to_action_type` | `SHOP_NOW`, `LEARN_MORE`, `SIGN_UP`, `BOOK_TRAVEL`, `DOWNLOAD`, `GET_OFFER`, `CONTACT_US`, `SUBSCRIBE`, `APPLY_NOW`, etc. |
| `object_story_id` | `{page_id}_{post_id}` |
| `object_story_spec` | Story spec (video/photo/link data) |
| `object_type` | `SHARE`, `PHOTO`, `VIDEO`, `STATUS`, `OFFER`, `APPLICATION` |
| `effective_object_story_id` | Effective story ID |
| `effective_instagram_media_id` | IG media ID |
| `effective_instagram_story_id` | IG story ID |
| `instagram_actor_id` | IG account used |
| `instagram_permalink_url` | IG permalink |
| `asset_feed_spec` | Dynamic creative asset feed spec |
| `template_url` | Dynamic template URL |
| `template_url_spec` | Template URL spec |
| `platform_customizations` | Platform-specific creative overrides |
| `url_tags` | URL tracking parameters appended to destination |
| `product_set_id` | Product set for Dynamic Product Ads |
| `status` | `ACTIVE`, `DELETED`, `IN_PROCESS`, `WITH_ISSUES` |

---

## Key Behavioral Notes

1. **Always specify `fields`** — the Marketing API returns no useful data by default without explicit field selection.
2. **Currency in cents** — all budget (`daily_budget`, `lifetime_budget`, `spend_cap`) and `spend` values are in the smallest currency unit (cents for USD). Divide by 100 for display.
3. **`effective_status` vs `status`** — `status` = what the advertiser set; `effective_status` = real delivery state (e.g., a paused campaign makes all child ad sets `effective_status=CAMPAIGN_PAUSED`).
4. **Timezone** — insights `date_start`/`date_stop` are in the ad account's timezone. Set on the account as `timezone_name`.
5. **Data delay** — insights data has an approximate 3-hour delay. Real-time data is not available.
6. **Historical limit** — insights data available for up to **37 months** (≈3 years). Use `date_preset=maximum` for all available data.
7. **Deleted objects still report** — deleted campaigns/ad sets/ads return insights with `effective_status=DELETED`.
8. **Learning phase** — new ad sets enter a learning phase. Exiting requires ~50 optimization events. Reflected in `learning_stage_info` field on the ad set.
9. **OUTCOME_* objectives** — as of v13.0+, new campaigns use `OUTCOME_AWARENESS`, `OUTCOME_TRAFFIC`, `OUTCOME_ENGAGEMENT`, `OUTCOME_LEADS`, `OUTCOME_APP_PROMOTION`, `OUTCOME_SALES`. Legacy objective names are deprecated.
10. **iOS / SKAdNetwork** — iOS campaigns with SKAdNetwork attribution have delayed reporting (up to 35 days for postbacks) and limited breakdown availability.
11. **Batch max 50** — batch requests accept up to 50 sub-requests per call.
