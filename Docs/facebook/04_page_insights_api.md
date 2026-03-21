# Facebook Page Insights API

Source: developers.facebook.com/docs/graph-api/reference/page/insights
Version: v22.0

---

## Overview

The Page Insights API returns aggregated analytics about a Facebook Page and its content.

**Requirements:**
- Token type: **Page Access Token** (user access tokens return permission errors)
- Token must belong to a user with at least Analyst role on the page
- Minimum: 100+ likes for demographic breakdowns
- Data delay: 24–48 hours
- History: Up to 93 days for `day` period; up to 2 years for aggregated periods
- Max time range per query: 90 days (with `since`/`until`)

---

## Endpoint Formats

```
GET /v22.0/{page-id}/insights
GET /v22.0/{page-id}/insights/{metric}
GET /v22.0/{page-id}/insights/{metric}/{period}
GET /v22.0/{post-id}/insights
GET /v22.0/{video-id}/video_insights
```

---

## Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `metric` | string | Comma-separated metric names. Must share a compatible period. |
| `period` | string | `day`, `week`, `days_28`, `month`, `lifetime` |
| `since` | int/string | Unix timestamp or date string — start of range (inclusive) |
| `until` | int/string | Unix timestamp or date string — end of range (exclusive) |
| `date_preset` | string | `today`, `yesterday`, `last_7_days`, `last_14_days`, `last_28_days`, `last_30_days`, `last_90_days`, `this_month`, `last_month` |
| `show_description_from_api_doc` | bool | Return description field for each metric |
| `limit` | int | Results per page |
| `after` / `before` | string | Cursor pagination tokens |

**Rule:** Metrics with incompatible periods cannot be combined in one request.

---

## Response Structure

```json
{
  "data": [
    {
      "id": "{page-id}/insights/{metric}/{period}",
      "name": "page_impressions",
      "period": "day",
      "values": [
        {"value": 1234, "end_time": "2025-01-15T08:00:00+0000"},
        {"value": 1456, "end_time": "2025-01-16T08:00:00+0000"}
      ],
      "title": "Daily Total Impressions",
      "description": "The number of times any content from your Page..."
    }
  ],
  "paging": {
    "previous": "https://graph.facebook.com/...",
    "next": "https://graph.facebook.com/..."
  }
}
```

For breakdown metrics, `value` is a dictionary:
```json
{"value": {"like": 45, "love": 12, "haha": 3, "wow": 1, "sad": 0, "angry": 2}, "end_time": "..."}
```

---

## Period Values

| Period | Description |
|--------|-------------|
| `day` | Rolling 1-day window, ending midnight Pacific |
| `week` | Rolling 7-day window |
| `days_28` | Rolling 28-day window |
| `month` | Calendar month |
| `lifetime` | All time since page creation |

---

## Page-Level Metrics — Complete Reference

### Impressions

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_impressions` | day, week, days_28 | Total times any page content entered a person's screen (posts, check-ins, ads, mentions) |
| `page_impressions_unique` | day, week, days_28 | Unique people who saw page content (Reach) |
| `page_impressions_paid` | day, week, days_28 | Paid/sponsored content impressions |
| `page_impressions_paid_unique` | day, week, days_28 | Unique paid reach |
| `page_impressions_organic` | day, week, days_28 | Organic content impressions |
| `page_impressions_organic_unique` | day, week, days_28 | Unique organic reach |
| `page_impressions_viral` | day, week, days_28 | Impressions via a friend's interaction |
| `page_impressions_viral_unique` | day, week, days_28 | Unique viral reach |
| `page_impressions_nonviral` | day, week, days_28 | Non-viral impressions |
| `page_impressions_nonviral_unique` | day, week, days_28 | Unique non-viral reach |
| `page_impressions_by_story_type` | day, week, days_28 | Breakdown by story type (dict) |
| `page_impressions_by_story_type_unique` | day, week, days_28 | Unique reach by story type (dict) |
| `page_impressions_by_city_unique` | day, week, days_28 | Unique reach by city (dict) |
| `page_impressions_by_country_unique` | day, week, days_28 | Unique reach by country (dict) |
| `page_impressions_by_locale_unique` | day, week, days_28 | Unique reach by locale (dict) |
| `page_impressions_by_age_gender_unique` | day, week, days_28 | Unique reach by age and gender (dict) |
| `page_impressions_frequency_distribution` | day, week, days_28 | Frequency buckets (how many times people saw content) |
| `page_impressions_viral_frequency_distribution` | day, week, days_28 | Viral frequency distribution |

### Reach (Aggregated)

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_reach` | day, week, days_28 | Unique people who saw any page content |
| `page_organic_reach` | day, week, days_28 | Unique people who saw organic content |
| `page_paid_reach` | day, week, days_28 | Unique people who saw paid content |

### Engagement

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_engaged_users` | day, week, days_28 | People who clicked any page content or engaged |
| `page_post_engagements` | day, week, days_28 | Total engagements (likes, comments, shares, clicks) on all posts |
| `page_consumptions` | day, week, days_28 | Total content clicks (links, photos, videos, other) |
| `page_consumptions_unique` | day, week, days_28 | Unique people who clicked content |
| `page_consumptions_by_consumption_type` | day, week, days_28 | Clicks by type: `link clicks`, `photo view`, `video play`, `other clicks` (dict) |
| `page_consumptions_by_consumption_type_unique` | day, week, days_28 | Unique clicks by type (dict) |
| `page_places_checkin_total` | day, week, days_28 | Total check-ins |
| `page_places_checkin_total_unique` | day, week, days_28 | Unique check-ins |
| `page_places_checkin_mobile` | day, week, days_28 | Mobile check-ins |
| `page_places_checkin_mobile_unique` | day, week, days_28 | Unique mobile check-ins |
| `page_places_checkins_by_age_gender` | day, week, days_28 | Check-ins by age/gender (dict) |
| `page_places_checkins_by_locale` | day, week, days_28 | Check-ins by locale (dict) |
| `page_places_checkins_by_country` | day, week, days_28 | Check-ins by country (dict) |

### Negative Feedback

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_negative_feedback` | day, week, days_28 | Total negative actions (hide, unlike, spam report) |
| `page_negative_feedback_unique` | day, week, days_28 | Unique people with negative actions |
| `page_negative_feedback_by_type` | day, week, days_28 | By type: `hide_clicks`, `hide_all_clicks`, `unlike_page_clicks`, `report_spam_clicks` (dict) |
| `page_negative_feedback_by_type_unique` | day, week, days_28 | Unique by type (dict) |

### Positive Feedback

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_positive_feedback_by_type` | day, week, days_28 | By type: `like`, `comment`, `link`, `answer`, `claim`, `rsvp_yes`, `rsvp_maybe`, `checkin` (dict) |
| `page_positive_feedback_by_type_unique` | day, week, days_28 | Unique positive feedback by type (dict) |

### Fans & Followers

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_fans` | lifetime | Total cumulative likes (fans) |
| `page_fan_adds` | day, week, days_28 | New likes |
| `page_fan_adds_unique` | day, week, days_28 | Unique new likes |
| `page_fan_removes` | day, week, days_28 | Unlikes |
| `page_fan_removes_unique` | day, week, days_28 | Unique unlikes |
| `page_fans_by_like_source` | lifetime | Total fans by source: `api`, `page_profile`, `search`, `page_suggestion`, `fan_badge`, `mobile`, `news_feed`, `photo`, `post_story`, `timeline`, `share`, `unknown` (dict) |
| `page_fans_by_like_source_unique` | day, week, days_28 | New likes by source (dict) |
| `page_fans_by_unlike_source_unique` | day, week, days_28 | Unlikes by source (dict) |
| `page_fan_adds_by_paid_non_paid_unique` | day, week, days_28 | New likes: paid vs organic (dict) |
| `page_fans_locale` | lifetime | Total fans by locale (dict) |
| `page_fans_city` | lifetime | Total fans by city (dict, top 45) |
| `page_fans_country` | lifetime | Total fans by country (dict, top 45) |
| `page_fans_gender_age` | lifetime | Total fans by gender and age group (dict) |
| `page_fans_online` | day | Fans online per hour (24-bucket dict) |
| `page_fans_online_per_day` | day | Fans online per day |

### Page Views

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_views_total` | day, week, days_28 | Total profile views |
| `page_views_logout` | day, week, days_28 | Views by logged-out users |
| `page_views_logged_in_total` | day, week, days_28 | Views by logged-in users |
| `page_views_logged_in_unique` | day, week, days_28 | Unique logged-in viewers |
| `page_views_external_referrals` | day, week, days_28 | Views from external sites (by domain, dict) |
| `page_views_by_profile_tab_total` | day, week, days_28 | Views by tab: `timeline`, `events`, `videos`, `photos`, `about`, `community` (dict) |
| `page_views_by_profile_tab_logged_in_unique` | day, week, days_28 | Unique logged-in views by tab (dict) |
| `page_views_by_internal_referer_logged_in_unique` | day, week, days_28 | Views from Facebook internal referrers (dict) |
| `page_views_by_age_gender_logged_in_unique` | day, week, days_28 | Views by age/gender of logged-in users (dict) |
| `page_views_by_country_logged_in_unique` | day, week, days_28 | Views by country (dict) |
| `page_views_by_city_logged_in_unique` | day, week, days_28 | Views by city (dict) |
| `page_views_by_locale_logged_in_unique` | day, week, days_28 | Views by locale (dict) |

### Actions on Page (CTA Clicks)

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_total_actions` | day, week, days_28 | Total action button clicks (Directions, Call, Website, etc.) |
| `page_cta_clicks_logged_in_total` | day, week, days_28 | CTA clicks by logged-in users |
| `page_cta_clicks_logged_in_unique` | day, week, days_28 | Unique logged-in CTA clicks |
| `page_cta_clicks_by_site_logged_in_unique` | day, week, days_28 | CTA clicks by platform (dict) |
| `page_cta_clicks_by_age_gender_logged_in_unique` | day, week, days_28 | CTA clicks by age/gender (dict) |
| `page_cta_clicks_by_country_logged_in_unique` | day, week, days_28 | CTA clicks by country (dict) |
| `page_cta_clicks_by_city_logged_in_unique` | day, week, days_28 | CTA clicks by city (dict) |
| `page_get_directions_clicks` | day, week, days_28 | "Get Directions" button clicks |
| `page_website_clicks` | day, week, days_28 | Website link clicks |
| `page_call_phone_clicks` | day, week, days_28 | Phone number link clicks |

### Video Metrics (Page-Level)

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_video_views` | day, week, days_28 | Total video plays ≥3 seconds |
| `page_video_views_paid` | day, week, days_28 | Paid video views |
| `page_video_views_organic` | day, week, days_28 | Organic video views |
| `page_video_views_autoplayed` | day, week, days_28 | Auto-played views |
| `page_video_views_click_to_play` | day, week, days_28 | Click-to-play views |
| `page_video_views_unique` | day, week, days_28 | Unique viewers (3+ sec) |
| `page_video_repeat_views` | day, week, days_28 | Repeat views |
| `page_video_complete_views_30s` | day, week, days_28 | Views of 30+ seconds or to completion |
| `page_video_complete_views_30s_paid` | day, week, days_28 | Paid complete views |
| `page_video_complete_views_30s_organic` | day, week, days_28 | Organic complete views |
| `page_video_complete_views_30s_autoplayed` | day, week, days_28 | Autoplay complete views |
| `page_video_complete_views_30s_click_to_play` | day, week, days_28 | Click-to-play complete views |
| `page_video_complete_views_30s_unique` | day, week, days_28 | Unique complete viewers |
| `page_video_complete_views_30s_repeat_views` | day, week, days_28 | Repeat complete views |
| `page_video_view_time` | day, week, days_28 | Total milliseconds watched |

### Posts Published (Page Content Activity)

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_posts_impressions` | day, week, days_28 | Impressions on posts published by the page |
| `page_posts_impressions_unique` | day, week, days_28 | Unique people who saw page posts |
| `page_posts_impressions_paid` | day, week, days_28 | Paid impressions on page posts |
| `page_posts_impressions_paid_unique` | day, week, days_28 | Unique paid reach for page posts |
| `page_posts_impressions_organic` | day, week, days_28 | Organic impressions on page posts |
| `page_posts_impressions_organic_unique` | day, week, days_28 | Unique organic reach |
| `page_posts_impressions_viral` | day, week, days_28 | Viral impressions on page posts |
| `page_posts_impressions_viral_unique` | day, week, days_28 | Unique viral reach |
| `page_posts_impressions_nonviral` | day, week, days_28 | Non-viral impressions |
| `page_posts_impressions_nonviral_unique` | day, week, days_28 | Unique non-viral reach |
| `page_posts_impressions_frequency_distribution` | day, week, days_28 | Frequency distribution |

### Reactions (Page-Level)

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_actions_post_reactions_like_total` | day, week, days_28 | Like reactions on page posts |
| `page_actions_post_reactions_love_total` | day, week, days_28 | Love reactions |
| `page_actions_post_reactions_wow_total` | day, week, days_28 | Wow reactions |
| `page_actions_post_reactions_haha_total` | day, week, days_28 | Haha reactions |
| `page_actions_post_reactions_sorry_total` | day, week, days_28 | Sad reactions |
| `page_actions_post_reactions_anger_total` | day, week, days_28 | Angry reactions |
| `page_actions_post_reactions_total` | day, week, days_28 | All reactions by type (dict) |

### Messaging & Conversations

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_messages_total_messaging_connections` | day | Total people who have messaged the page |
| `page_messages_new_conversations_unique` | day | New unique conversation threads started |
| `page_messages_blocked_conversations_unique` | day | Blocked conversations |
| `page_messages_reported_conversations_unique` | day | Reported conversations |
| `page_messages_reported_conversations_by_report_type_unique` | day | Reports by type (dict) |
| `page_messages_by_response_status_unique` | day | Conversations by response status (dict) |

### Response Rate & Time

| Metric | Periods | Description |
|--------|---------|-------------|
| `page_response_rate_all` | day | % of messages page responded to |
| `page_response_rate_filtered` | day | Response rate for filtered inbox |
| `page_response_time_all` | day | Median response time in minutes (all messages) |
| `page_response_time_filtered` | day | Median response time for filtered inbox |

---

## Post-Level Insights Metrics

```
GET /v22.0/{post-id}/insights?metric={metric}&period=lifetime&access_token={PAGE_TOKEN}
```

Most post metrics use `period=lifetime`.

### Post Impressions

| Metric | Period | Description |
|--------|--------|-------------|
| `post_impressions` | lifetime | Total impressions |
| `post_impressions_unique` | lifetime | Unique people who saw it (Reach) |
| `post_impressions_paid` | lifetime | Paid impressions |
| `post_impressions_paid_unique` | lifetime | Unique paid reach |
| `post_impressions_fan` | lifetime | Impressions by page fans |
| `post_impressions_fan_unique` | lifetime | Unique fan reach |
| `post_impressions_fan_paid` | lifetime | Paid impressions among fans |
| `post_impressions_fan_paid_unique` | lifetime | Unique paid fan reach |
| `post_impressions_organic` | lifetime | Organic impressions |
| `post_impressions_organic_unique` | lifetime | Unique organic reach |
| `post_impressions_viral` | lifetime | Viral impressions |
| `post_impressions_viral_unique` | lifetime | Unique viral reach |
| `post_impressions_nonviral` | lifetime | Non-viral impressions |
| `post_impressions_nonviral_unique` | lifetime | Unique non-viral reach |
| `post_impressions_by_story_type` | lifetime | By story type (dict) |
| `post_impressions_by_story_type_unique` | lifetime | Unique by story type (dict) |

### Post Engagement

| Metric | Period | Description |
|--------|--------|-------------|
| `post_engaged_users` | lifetime | Unique people who clicked, reacted, commented, or shared |
| `post_engaged_fan` | lifetime | Fans who engaged |
| `post_clicks` | lifetime | Total clicks anywhere on the post |
| `post_clicks_unique` | lifetime | Unique people who clicked |
| `post_clicks_by_type` | lifetime | By type: `link clicks`, `photo view`, `video play`, `other clicks` (dict) |
| `post_clicks_by_type_unique` | lifetime | Unique clicks by type (dict) |
| `post_consumptions` | lifetime | Clicks on links, photos, video plays |
| `post_consumptions_unique` | lifetime | Unique content consumers |
| `post_consumptions_by_type` | lifetime | Consumptions by type (dict) |
| `post_consumptions_by_type_unique` | lifetime | Unique consumptions by type (dict) |
| `post_negative_feedback` | lifetime | Total negative actions |
| `post_negative_feedback_unique` | lifetime | Unique negative feedbackers |
| `post_negative_feedback_by_type` | lifetime | By type: `hide_clicks`, `hide_all_clicks`, `report_spam_clicks`, `unlike_page_clicks` (dict) |
| `post_negative_feedback_by_type_unique` | lifetime | Unique negative by type (dict) |

### Post Reactions

| Metric | Period | Description |
|--------|--------|-------------|
| `post_reactions_like_total` | lifetime | Like reactions |
| `post_reactions_love_total` | lifetime | Love reactions |
| `post_reactions_wow_total` | lifetime | Wow reactions |
| `post_reactions_haha_total` | lifetime | Haha reactions |
| `post_reactions_sorry_total` | lifetime | Sad reactions |
| `post_reactions_anger_total` | lifetime | Angry reactions |
| `post_reactions_by_type_total` | lifetime | All reactions by type: `like`, `love`, `haha`, `wow`, `sad`, `angry` (dict) |

### Post Activity

| Metric | Period | Description |
|--------|--------|-------------|
| `post_activity` | lifetime | Total activity (shares + likes + comments) |
| `post_activity_unique` | lifetime | Unique active people |
| `post_activity_by_action_type` | lifetime | By type: `like`, `comment`, `share`, `claim`, `rsvp` (dict) |
| `post_activity_by_action_type_unique` | lifetime | Unique by action type (dict) |

### Post Video Metrics

| Metric | Period | Description |
|--------|--------|-------------|
| `post_video_views` | lifetime | Views ≥3 seconds |
| `post_video_views_unique` | lifetime | Unique viewers (≥3 sec) |
| `post_video_views_paid` | lifetime | Paid views |
| `post_video_views_organic` | lifetime | Organic views |
| `post_video_views_autoplayed` | lifetime | Autoplay views |
| `post_video_views_click_to_play` | lifetime | Click-to-play views |
| `post_video_view_time` | lifetime | Total milliseconds watched |
| `post_video_avg_time_watched` | lifetime | Average watch time in milliseconds |
| `post_video_complete_views_organic` | lifetime | Organic complete views |
| `post_video_complete_views_organic_unique` | lifetime | Unique organic complete views |
| `post_video_complete_views_paid` | lifetime | Paid complete views |
| `post_video_complete_views_paid_unique` | lifetime | Unique paid complete views |
| `post_video_retention_graph` | lifetime | Retention % at each percentile of the video |
| `post_video_retention_graph_clicked_to_play` | lifetime | Retention for click-to-play viewers |
| `post_video_retention_graph_autoplayed` | lifetime | Retention for autoplay viewers |
| `post_video_views_15s` | lifetime | Views ≥15 seconds |

---

## Video-Level Insights

```
GET /v22.0/{video-id}/video_insights?metric={metric}&access_token={PAGE_TOKEN}
```

| Metric | Description |
|--------|-------------|
| `total_video_views` | Total views (≥3 sec) |
| `total_video_views_unique` | Unique viewers |
| `total_video_views_autoplayed` | Autoplay views |
| `total_video_views_clicked_to_play` | Click-to-play views |
| `total_video_views_organic` | Organic views |
| `total_video_views_organic_unique` | Unique organic viewers |
| `total_video_views_paid` | Paid views |
| `total_video_views_paid_unique` | Unique paid viewers |
| `total_video_complete_views` | Watched to end |
| `total_video_complete_views_unique` | Unique complete viewers |
| `total_video_complete_views_auto_played` | Autoplay complete views |
| `total_video_complete_views_clicked_to_play` | Click-to-play complete |
| `total_video_complete_views_organic` | Organic complete views |
| `total_video_complete_views_paid` | Paid complete views |
| `total_video_avg_time_watched` | Average watch time (ms) |
| `total_video_view_total_time` | Total watch time (ms) |
| `total_video_impressions` | Total times video was shown |
| `total_video_impressions_unique` | Unique people shown the video |
| `total_video_impressions_paid_unique` | Unique paid impressions |
| `total_video_impressions_organic_unique` | Unique organic impressions |
| `total_video_stories_by_action_type` | Stories by action: like, comment, share (dict) |
| `total_video_reactions_by_type_total` | Reactions by type (dict) |
| `total_video_negative_feedback_by_type` | Negative feedback by type (dict) |
| `total_video_retention_graph` | Retention % at each 1% interval |
| `total_video_view_time_by_age_bucket_and_gender` | Watch time by age/gender (dict) |
| `total_video_view_time_by_region_id` | Watch time by region (dict) |
| `total_video_views_15s` | Views ≥15 seconds |
| `total_video_60s_excludes_shorter_views` | Views ≥60s (for videos ≥60s long) |

---

## Example Requests

### Daily impressions and reach for last 30 days
```
GET /v22.0/{page-id}/insights
  ?metric=page_impressions,page_impressions_unique
  &period=day
  &since=2025-01-01
  &until=2025-01-31
  &access_token={PAGE_TOKEN}
```

### Lifetime fan demographics
```
GET /v22.0/{page-id}/insights
  ?metric=page_fans_gender_age,page_fans_country,page_fans_city
  &period=lifetime
  &access_token={PAGE_TOKEN}
```

### Post reactions and impressions
```
GET /v22.0/{post-id}/insights
  ?metric=post_reactions_by_type_total,post_impressions,post_engaged_users
  &period=lifetime
  &access_token={PAGE_TOKEN}
```

### Video views with date preset
```
GET /v22.0/{page-id}/insights
  ?metric=page_video_views,page_video_view_time
  &period=day
  &date_preset=last_28_days
  &access_token={PAGE_TOKEN}
```

### Messaging metrics
```
GET /v22.0/{page-id}/insights
  ?metric=page_messages_total_messaging_connections,page_messages_new_conversations_unique,page_response_rate_all,page_response_time_all
  &period=day
  &since=2025-01-01
  &until=2025-01-31
  &access_token={PAGE_TOKEN}
```

---

## Breakdown Dimensions Reference

| Breakdown | Metrics Using It |
|-----------|-----------------|
| Age + Gender | `page_impressions_by_age_gender_unique`, `page_fans_gender_age`, `page_views_by_age_gender_logged_in_unique`, `page_places_checkins_by_age_gender` |
| Country | `page_impressions_by_country_unique`, `page_fans_country`, `page_views_by_country_logged_in_unique` |
| City | `page_impressions_by_city_unique`, `page_fans_city`, `page_views_by_city_logged_in_unique` |
| Locale | `page_impressions_by_locale_unique`, `page_fans_locale`, `page_views_by_locale_logged_in_unique` |
| Story Type | `page_impressions_by_story_type`, `post_impressions_by_story_type` |
| Consumption Type | `page_consumptions_by_consumption_type`, `post_consumptions_by_type`, `post_clicks_by_type` |
| Reaction Type | `page_actions_post_reactions_total`, `post_reactions_by_type_total` |
| Like Source | `page_fans_by_like_source`, `page_fans_by_like_source_unique` |
| Action Type | `post_activity_by_action_type`, `page_positive_feedback_by_type`, `page_negative_feedback_by_type` |
| Hour (0–23) | `page_fans_online` |
| Platform/Site | `page_views_by_site_logged_in_unique`, `page_cta_clicks_by_site_logged_in_unique` |

---

## Required Permissions

| Use Case | Required |
|----------|---------|
| Impressions, reach, engagement | `pages_read_engagement`, `read_insights` |
| Fan demographics | `pages_read_engagement`, `read_insights` |
| Page views, CTA clicks | `pages_read_engagement`, `read_insights` |
| Post-level insights | `pages_read_engagement`, `read_insights`, `pages_read_user_content` |
| Messaging metrics | `pages_messaging`, `pages_read_engagement` |
| Video insights | `pages_read_engagement`, `read_insights` |

---

## Important Notes

1. **Metrics cannot mix incompatible periods** in one request — e.g., `page_fans` (lifetime) cannot be combined with `page_impressions` (day/week/days_28).
2. **Demographic breakdowns are suppressed** when the audience segment < 100 people.
3. **Data delay:** 24–48 hour lag. Current-day data is incomplete.
4. **New Pages Experience:** Some metrics may be renamed or unavailable for migrated pages.
5. **Rate limits:** 200 calls/hour per page access token. Request multiple metrics in one call when possible.
6. **`page_impressions` vs `page_posts_impressions`:** `page_impressions` = ALL surfaces (posts, ads, check-ins, profile views). `page_posts_impressions` = only page-published posts.
