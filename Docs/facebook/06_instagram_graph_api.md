# Instagram Graph API

Source: developers.facebook.com/docs/instagram-api
Version: v22.0

---

## Overview

The Instagram Graph API (accessed via `graph.facebook.com`) provides access to Instagram Business and Creator accounts. Requirements:

- Instagram account must be a **Business** or **Creator** account
- Instagram account must be **linked to a Facebook Page**
- Use the Facebook Page's access token to interact with the linked Instagram account
- Access Instagram account ID via the linked Facebook Page

---

## Getting the Instagram Account ID

```
GET /v22.0/{page-id}?fields=instagram_business_account&access_token={PAGE_TOKEN}
```

Response:
```json
{
  "instagram_business_account": {"id": "17841405822304914"},
  "id": "{page-id}"
}
```

---

## IG User Node

```
GET /v22.0/{ig-user-id}?fields={fields}&access_token={token}
```

### IG User Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | App-scoped Instagram User ID (IGSID) |
| `username` | string | Instagram username |
| `name` | string | Profile display name |
| `biography` | string | Bio text |
| `website` | string | Website URL |
| `profile_picture_url` | string | Profile picture URL (CDN, expires) |
| `followers_count` | int | Total followers |
| `follows_count` | int | Accounts this user follows |
| `media_count` | int | Total published media |
| `account_type` | string | `BUSINESS` or `MEDIA_CREATOR` |
| `ig_id` | int | Legacy numeric Instagram user ID |
| `has_profile_pic` | bool | Whether account has a profile picture |
| `is_published` | bool | Whether account is published |
| `legacy_instagram_user_id` | string | Instagram ID from Marketing API (v21.0 and older) |
| `shopping_product_tag_eligibility` | bool | Eligible for product tagging |

### IG User Edges

| Edge | Description | Permission |
|------|-------------|-----------|
| `media` | Published posts/media | `instagram_basic` |
| `stories` | Active stories | `instagram_basic` |
| `live_media` | Live video media | `instagram_basic` |
| `insights` | Account-level insights | `instagram_manage_insights` |
| `tags` | Media where account was tagged | `instagram_basic` |
| `mentioned_media` | Media where account was @mentioned | `instagram_manage_comments` |
| `mentioned_comment` | Comments where account was @mentioned | `instagram_manage_comments` |
| `recently_searched_hashtags` | Hashtags searched in last 7 days | `instagram_basic` |
| `business_discovery` | Data about other IG Business accounts | `instagram_basic` |
| `content_publishing_limit` | Current publishing usage | `instagram_content_publish` |
| `media_publish` | Publish an IG container | `instagram_content_publish` |
| `agencies` | Businesses that can advertise for this account | `ads_read` |
| `authorized_adaccounts` | Ad accounts authorized to advertise | `ads_read` |
| `upcoming_events` | Hosted events | `instagram_basic` |
| `collaboration_invites` | Collaboration invitations | `instagram_basic` |
| `connected_threads_user` | Connected Threads account | `instagram_basic` |

### Example
```
GET /v22.0/17841405822304914
  ?fields=biography,id,username,website,followers_count,media_count,profile_picture_url
  &access_token={TOKEN}
```

---

## IG Media Node

```
GET /v22.0/{ig-media-id}?fields={fields}&access_token={token}
```

### IG Media Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Media ID |
| `media_type` | string | `IMAGE`, `VIDEO`, `CAROUSEL_ALBUM` |
| `media_product_type` | string | `FEED`, `STORY`, `REELS`, `AD` |
| `caption` | string | Media caption (excludes album children; `@` excluded unless admin) |
| `permalink` | string | Permanent URL to media |
| `shortcode` | string | Shortcode for URL |
| `timestamp` | datetime | ISO 8601 creation time (UTC) |
| `username` | string | Creator's username |
| `owner` | object | Instagram user ID (only if app user created it) |
| `media_url` | string | URL to the media file |
| `thumbnail_url` | string | Thumbnail URL (for VIDEO type) |
| `like_count` | int | Like count (omitted if owner hid likes) |
| `comments_count` | int | Comment count (excludes album children) |
| `view_count` | int | View count for reels (paid + organic) |
| `is_shared_to_feed` | bool | For reels: whether appears in Feed and Reels tabs |
| `is_comment_enabled` | bool | Whether comments are enabled |
| `alt_text` | string | Accessibility alt text |
| `legacy_instagram_media_id` | string | Marketing API ID (v21.0 and older) |
| `boost_ads_list` | array | Active Instagram ads overview (Facebook Login only) |
| `boost_eligibility_info` | object | Boosting eligibility (Facebook Login only) |
| `copyright_check_information` | object | Copyright status and matches (Facebook Login only) |

### IG Media Edges

| Edge | Description |
|------|-------------|
| `children` | Album media items (for CAROUSEL_ALBUM) |
| `comments` | Comments on the media |
| `insights` | Media analytics |
| `collaborators` | Collaborators (Facebook Login only) |

### List Media for a User
```
GET /v22.0/{ig-user-id}/media
  ?fields=id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count
  &limit=25
  &access_token={TOKEN}
```

### List Stories
```
GET /v22.0/{ig-user-id}/stories
  ?fields=id,media_type,permalink,timestamp
  &access_token={TOKEN}
```

---

## IG User Insights

```
GET /v22.0/{ig-user-id}/insights
  ?metric={metrics}
  &period={period}
  &since={since}
  &until={until}
  &breakdown={breakdown}
  &metric_type=total_value
  &access_token={TOKEN}
```

### IG User Insight Metrics

| Metric | Period | Description |
|--------|--------|-------------|
| `accounts_engaged` | day | Accounts that interacted with content |
| `comments` | day | Comments on posts |
| `follows_and_unfollows` | day | New follows and unfollows |
| `follower_demographics` | (see timeframe) | Demographic breakdown of followers |
| `engaged_audience_demographics` | (see timeframe) | Demographics of engaged audience |
| `impressions` | day | Total times content was seen (deprecated v22.0+, ending Apr 21 2025) |
| `likes` | day | Likes on posts |
| `profile_links_taps` | day | Taps on links in profile |
| `reach` | day | Unique accounts that saw content |
| `replies` | day | Replies to stories |
| `reposts` | day | Reposts of content |
| `saves` | day | Saves of posts |
| `shares` | day | Shares of posts |
| `total_interactions` | day | Combined: likes + comments + shares + saves + etc. |
| `views` | day | Total views of content |

### Timeframes (for demographic metrics)
| Value | Description |
|-------|-------------|
| `last_14_days` | Previous 14 days |
| `last_30_days` | Previous 30 days |
| `last_90_days` | Previous 90 days |
| `prev_month` | Previous calendar month |
| `this_month` | Current calendar month |
| `this_week` | Current week |

### Breakdown Dimensions (User Insights)

| Breakdown | Values |
|-----------|--------|
| `contact_button_type` | `BOOK_NOW`, `CALL`, `DIRECTION`, `EMAIL`, `INSTANT_EXPERIENCE`, `TEXT`, `UNDEFINED` |
| `follow_type` | `FOLLOWER`, `NON_FOLLOWER`, `UNKNOWN` |
| `media_product_type` | `AD`, `FEED`, `REELS`, `STORY` |
| `age` | Age ranges (demographics only) |
| `city` | City name (demographics only) |
| `country` | Country code (demographics only) |
| `gender` | Gender (demographics only) |

### Required Permissions (User Insights)

**Facebook Login:**
- `instagram_basic`
- `instagram_manage_insights`
- `pages_read_engagement`

**Instagram Login:**
- `instagram_business_basic`
- `instagram_business_manage_insights`

### Example Request
```
GET /v22.0/17841405822304914/insights
  ?metric=reach,impressions,total_interactions
  &period=day
  &breakdown=media_product_type
  &metric_type=total_value
  &since=1704067200
  &access_token={TOKEN}
```

---

## IG Media Insights

```
GET /v22.0/{ig-media-id}/insights
  ?metric={metrics}
  &access_token={TOKEN}
```

### Carousel Album Metrics

| Metric | Description |
|--------|-------------|
| `impressions` | Total impressions across all carousel slides |
| `reach` | Unique accounts that saw the carousel |
| `likes` | Likes on the carousel |
| `comments` | Comments on the carousel |
| `shares` | Shares |
| `saved` | Saves/bookmarks |
| `total_interactions` | Total interactions |
| `carousel_album_impressions` | Impressions on all child items |
| `carousel_album_reach` | Unique reach across all child items |
| `carousel_album_saved` | Saves (alias) |
| `carousel_album_video_views` | Views on video children within the carousel |
| `follows` | New follows from this carousel |
| `profile_visits` | Profile visits from this carousel |

### Feed Post Metrics

| Metric | Description |
|--------|-------------|
| `comments` | Number of comments |
| `follows` | New followers from this post |
| `impressions` | Total times post was seen (deprecated for posts after Jul 2, 2024) |
| `likes` | Number of likes |
| `profile_activity` | Actions on profile after viewing post |
| `profile_visits` | Profile visits from this post |
| `reach` | Unique accounts that saw the post |
| `saved` | Times the post was saved |
| `shares` | Number of shares |
| `total_interactions` | Likes + saves + comments + shares − unlikes − unsaves |
| `views` | Total video views |

### Reels Metrics

| Metric | Description |
|--------|-------------|
| `clips_replays_count` | Replay count (deprecated v22.0+) |
| `comments` | Number of comments |
| `ig_reels_aggregated_all_plays_count` | Total plays on Instagram + Facebook (deprecated) |
| `ig_reels_avg_watch_time` | Average playback duration in milliseconds |
| `ig_reels_video_view_total_time` | Total cumulative watch time in milliseconds |
| `likes` | Number of likes |
| `plays` | Initial video plays (deprecated v22.0+) |
| `reach` | Unique viewers |
| `saved` | Times saved |
| `shares` | Number of shares |
| `total_interactions` | Combined engagement |
| `views` | Total reel views |

### Stories Metrics

| Metric | Description |
|--------|-------------|
| `impressions` | Total times the story was seen (deprecated for stories after Jul 2, 2024) |
| `reach` | Unique viewers |
| `taps_forward` | Taps to see the next story |
| `taps_back` | Taps to see the previous story |
| `exits` | Times someone exited the story viewer |
| `swipe_aways` | Swipes away from the story |
| `navigation` | Total navigations: taps_forward + taps_back + exits + swipe_aways |
| `replies` | Replies (returns 0 for creators in Europe/Japan) |
| `shares` | Shares of the story |
| `follows` | New followers from story |
| `profile_visits` | Profile visits from story |
| `profile_activity` | Profile actions after viewing |
| `link_clicks` | Clicks on the link sticker (v17+) |
| `sticker_taps_hashtag` | Taps on hashtag stickers |
| `sticker_taps_mention` | Taps on @mention stickers |
| `sticker_taps_location` | Taps on location stickers |
| `sticker_taps_other` | Taps on other interactive stickers |
| `total_interactions` | Combined engagement |

**Derived metric (not native):** Completion rate = `(impressions - exits) / impressions`

Story metrics are only available while the story is live or up to **30 days** after it expires.

### Required Permissions (Media Insights)

**Facebook Login:**
- `instagram_basic`
- `instagram_manage_insights`
- `pages_read_engagement`

**Instagram Login:**
- `instagram_business_basic`
- `instagram_business_manage_insights`

---

## Content Publishing API

Publishing Instagram content requires two steps: create a container, then publish it.

### Step 1: Create Media Container

**Photo post:**
```
POST /v22.0/{ig-user-id}/media
  image_url=https://example.com/image.jpg
  caption=My caption #hashtag
  access_token={TOKEN}
```

**Video/Reel post:**
```
POST /v22.0/{ig-user-id}/media
  media_type=REELS
  video_url=https://example.com/video.mp4
  caption=My reel caption
  share_to_feed=true
  access_token={TOKEN}
```

**Carousel post (Step 1a — create individual items):**
```
POST /v22.0/{ig-user-id}/media
  image_url=https://example.com/image1.jpg
  is_carousel_item=true
  access_token={TOKEN}
```
Repeat for each item (up to 10).

**Carousel post (Step 1b — create carousel container):**
```
POST /v22.0/{ig-user-id}/media
  media_type=CAROUSEL
  children={item_id_1},{item_id_2},{item_id_3}
  caption=Carousel caption
  access_token={TOKEN}
```

Returns: `{"id": "{container-id}"}`

### Step 2: Check Container Status

```
GET /v22.0/{container-id}?fields=status_code&access_token={TOKEN}
```

`status_code` values: `EXPIRED`, `ERROR`, `FINISHED`, `IN_PROGRESS`, `PUBLISHED`

Wait until `FINISHED` before publishing.

### Step 3: Publish Container

```
POST /v22.0/{ig-user-id}/media_publish
  creation_id={container-id}
  access_token={TOKEN}
```

Returns: `{"id": "{ig-media-id}"}`

### Publishing Limits

Check current usage:
```
GET /v22.0/{ig-user-id}/content_publishing_limit
  ?fields=config,quota_usage
  &access_token={TOKEN}
```

| Limit | Value |
|-------|-------|
| Feed posts + Reels per 24h | 25 |
| Stories per 24h | 100 |

### Supported Media Specifications

**Images:**
- Format: JPEG or PNG
- Min width: 320px, Max width: 1440px
- Aspect ratios: 4:5 (portrait), 1:1 (square), 1.91:1 (landscape)
- Max file size: 8MB

**Videos (Feed):**
- Format: MP4 or MOV, H.264 codec, AAC audio
- Max duration: 60 seconds
- Recommended bitrate: 3500 kbps
- Aspect ratios: 4:5 to 1.91:1

**Reels:**
- Format: MP4, H.264, AAC audio
- Duration: 3 seconds to 90 seconds
- Recommended resolution: 1080×1920 (9:16)
- Max file size: 1GB

**Stories:**
- Images: JPEG/PNG, recommended 1080×1920
- Videos: MP4, up to 60 seconds

### Required Permission
- `instagram_content_publish`

---

## Comments API

### List Comments
```
GET /v22.0/{ig-media-id}/comments
  ?fields=id,text,timestamp,username,from
  &access_token={TOKEN}
```

### Reply to a Comment
```
POST /v22.0/{ig-comment-id}/replies
  message=@username Thank you!
  access_token={TOKEN}
```

### Reply to a Post (Top-Level Comment)
```
POST /v22.0/{ig-media-id}/comments
  message=Great post!
  access_token={TOKEN}
```

### Hide / Show a Comment
```
POST /v22.0/{ig-comment-id}
  hide=true
  access_token={TOKEN}
```

### Delete a Comment
```
DELETE /v22.0/{ig-comment-id}?access_token={TOKEN}
```

### Required Permission
- `instagram_manage_comments` (Facebook Login) or `instagram_business_manage_comments` (Instagram Login)

---

## Hashtag Search API

### Step 1: Find Hashtag ID
```
GET /v22.0/ig_hashtag_search
  ?user_id={ig-user-id}
  &q=coke
  &access_token={TOKEN}
```

Returns: `{"data": [{"id": "17873440459141021"}]}`

### Step 2: Get Top/Recent Media for Hashtag
```
GET /v22.0/{hashtag-id}/top_media
  ?user_id={ig-user-id}
  &fields=id,caption,permalink,media_type
  &access_token={TOKEN}

GET /v22.0/{hashtag-id}/recent_media
  ?user_id={ig-user-id}
  &fields=id,caption,permalink
  &access_token={TOKEN}
```

Limits:
- Can query max 30 unique hashtags per user per 7 days
- `recently_searched_hashtags` edge shows what you've searched

---

## Mentions API

### Get Mentioned Media
```
GET /v22.0/{ig-user-id}/mentioned_media
  ?fields=caption,media_url,timestamp
  &media_id={media-id-where-mentioned}
  &access_token={TOKEN}
```

### Get Mentioned Comment
```
GET /v22.0/{ig-user-id}/mentioned_comment
  ?fields=text,timestamp
  &comment_id={comment-id-where-mentioned}
  &access_token={TOKEN}
```

---

## Business Discovery API

Look up another Instagram Business account by username:
```
GET /v22.0/{ig-user-id}
  ?fields=business_discovery.fields(username,followers_count,media_count,biography)
  &access_token={TOKEN}
```

Note: The target account must be a Business or Creator account.

---

## Rate Limits

Instagram Graph API calls are subject to:
- Standard Graph API rate limits (200 calls/hour per app per user)
- `X-Business-Use-Case-Usage` header for business-tier calls

Specific limits:
- Hashtag search: 30 unique hashtags per user per 7 days
- Content publishing: 50 posts per 24 hours

---

## Permissions Summary

| Operation | Facebook Login Permission | Instagram Login Permission |
|-----------|--------------------------|--------------------------|
| Read profile & media | `instagram_basic` + `pages_read_engagement` | `instagram_business_basic` |
| Read insights | `instagram_manage_insights` + `pages_read_engagement` | `instagram_business_manage_insights` |
| Manage comments | `instagram_manage_comments` + `pages_read_engagement` | `instagram_business_manage_comments` |
| Publish content | `instagram_content_publish` | `instagram_business_content_publish` |
| Read messages | `instagram_manage_messages` | `instagram_business_manage_messages` |
| Tag products | `instagram_shopping_tag_products` | `instagram_shopping_tag_products` |
| List ad accounts | `ads_read` | — |

---

## Notes

- **Story insights:** Only available for 24 hours while the story is live.
- **Data delay:** Media insights can be delayed up to 48 hours.
- **Data retention:** Insights data retained for up to 2 years.
- **Album children:** Insights are unavailable for individual items within a CAROUSEL_ALBUM.
- **`impressions` deprecation:** Metric deprecated for media created after July 2, 2024 and for account-level insights in v22.0+ (ending April 21, 2025). Use `views` or `reach` instead.
- **Europe/Japan:** Story `replies` metric returns 0 for creators in these regions.
