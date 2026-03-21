# Facebook Pages API

Source: developers.facebook.com/docs/graph-api/reference/page
Version: v22.0

---

## Overview

The Page node represents a Facebook Page. Access requires either:
- A **User Access Token** with `pages_read_engagement` (for pages the user manages)
- A **Page Access Token** (for full page operations)
- **Page Public Content Access** feature (for reading public pages you don't own)

---

## Page Node Fields

```
GET /v22.0/{page-id}?fields={fields}&access_token={token}
```

### Identity
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Page ID |
| `name` | string | Page name |
| `username` | string | Page alias/vanity URL |
| `link` | string | Facebook Page URL |
| `permalink_url` | string | Permanent URL |

### Description & Info
| Field | Type | Description |
|-------|------|-------------|
| `about` | string | Short description (100 char limit) |
| `description` | string | Long description |
| `category` | string | Primary Page category |
| `category_list` | array | All categories |
| `website` | string | Website URL |
| `phone` | string | Contact phone number |
| `emails` | array | Email addresses |
| `founded` | string | Founded date |
| `company_overview` | string | Company overview |
| `mission` | string | Page mission statement |

### Audience Metrics
| Field | Type | Description |
|-------|------|-------------|
| `fan_count` | int | Number of people who liked the page |
| `followers_count` | int | Number of followers |
| `talking_about_count` | int | People discussing the page recently |
| `checkins` | int | Total check-ins |
| `rating_count` | int | Number of ratings |
| `overall_star_rating` | float | Average star rating (1–5) |

### Location & Business
| Field | Type | Description |
|-------|------|-------------|
| `location` | object | `city`, `state`, `zip`, `country`, `street`, `latitude`, `longitude` |
| `hours` | object | Operating hours (keyed by `mon_1_open`, `mon_1_close`, etc.) |
| `parking` | object | Parking availability |
| `price_range` | string | `$`, `$$`, `$$$`, `$$$$` |
| `temporary_status` | string | `OPEN`, `CLOSED`, `DIFFERENTLY_OPEN` |
| `is_permanently_closed` | bool | Whether closed permanently |

### Verification & Status
| Field | Type | Description |
|-------|------|-------------|
| `is_verified` | bool | Whether page is verified |
| `verification_status` | string | `blue_verified`, `gray_verified`, `not_verified` |
| `is_published` | bool | Whether the page is publicly visible |
| `has_transitioned_to_new_page_experience` | bool | New Pages Experience |
| `is_owned` | bool | Whether the token owner manages this page |

### Media
| Field | Type | Description |
|-------|------|-------------|
| `cover` | object | Cover photo: `id`, `source`, `offset_x`, `offset_y` |
| `picture` | object | Profile picture: `url`, `width`, `height`, `is_silhouette` |

---

## Page Edges (Connections)

| Edge | Description | Required Permission |
|------|-------------|---------------------|
| `/feed` | All posts on timeline (by page and others) | `pages_read_engagement` |
| `/posts` | Posts made by the page | `pages_read_engagement` |
| `/published_posts` | All published posts | `pages_read_engagement` |
| `/scheduled_posts` | Posts scheduled to publish | `pages_manage_posts` |
| `/photos` | Photos | `pages_read_engagement` |
| `/videos` | Videos | `pages_read_engagement` |
| `/albums` | Photo albums | `pages_read_engagement` |
| `/live_videos` | Live video broadcasts | `pages_read_engagement` |
| `/events` | Events hosted by page | `pages_read_engagement` |
| `/insights` | Analytics metrics | `read_insights` |
| `/conversations` | Messenger conversation threads | `pages_messaging` |
| `/messages` | Messenger messages | `pages_messaging` |
| `/leadgen_forms` | Lead generation forms | `leads_retrieval` |
| `/subscribed_apps` | Apps subscribed to webhooks | `pages_manage_metadata` |
| `/roles` | Page admin roles | `pages_manage_metadata` |
| `/assigned_users` | Users assigned to page | `pages_manage_metadata` |
| `/ratings` | User ratings and reviews | `pages_read_user_content` |
| `/tabs` | Custom page tabs | `pages_manage_metadata` |
| `/call_to_actions` | CTA buttons | `pages_manage_cta` |
| `/likes` | Pages liked by this page | `pages_read_engagement` |
| `/locations` | Child/branch pages | `pages_read_engagement` |
| `/global_brand_children` | Brand hierarchy pages | `pages_read_engagement` |
| `/blocked` | Blocked users | `pages_manage_engagement` |
| `/commerce_orders` | Shop orders | `commerce_manage_orders` |
| `/product_catalogs` | Linked product catalogs | `catalog_management` |

---

## Reading the Feed

```
GET /v22.0/{page-id}/feed
  ?fields=id,message,created_time,permalink_url,full_picture,attachments,shares,story
  &limit=25
  &access_token={PAGE_ACCESS_TOKEN}
```

### Feed Parameters
| Parameter | Description |
|-----------|-------------|
| `limit` | Results per page (max 100) |
| `fields` | Comma-separated field list |
| `since` | Unix timestamp — posts after this time |
| `until` | Unix timestamp — posts before this time |
| `after` | Cursor for next page |
| `before` | Cursor for previous page |

### Feed Fields Available
| Field | Description |
|-------|-------------|
| `id` | Post ID in format `{page-id}_{post-id}` |
| `message` | Text content |
| `story` | Auto-generated activity description |
| `created_time` | ISO 8601 creation timestamp |
| `updated_time` | ISO 8601 last update |
| `permalink_url` | Permanent URL to the post |
| `full_picture` | Image URL (max 720px wide) |
| `attachments` | Attached media (photos, videos, links) |
| `shares` | `{count: N}` share count |
| `is_published` | Publication status |
| `is_hidden` | Whether hidden |
| `status_type` | `added_photos`, `added_video`, `mobile_status_update`, `shared_story`, etc. |
| `from` | Author object (id, name) |
| `place` | Tagged location |
| `privacy` | Privacy settings object |
| `call_to_action` | CTA object |
| `is_popular` | Popularity flag |
| `targeting` | Targeting restrictions |
| `feed_targeting` | News feed audience controls |

### Feed Response Structure
```json
{
  "data": [
    {
      "id": "123456789_987654321",
      "message": "Post content here",
      "created_time": "2025-01-15T10:00:00+0000",
      "permalink_url": "https://www.facebook.com/permalink/..."
    }
  ],
  "paging": {
    "cursors": {"before": "...", "after": "..."},
    "next": "https://graph.facebook.com/..."
  }
}
```

Limitations:
- Max 100 posts per request.
- Returns ~600 ranked posts per year.
- Expired posts become inaccessible.

### Required Permissions for Reading Feed
- `pages_read_engagement`
- `pages_read_user_content`
- Page must have `CREATE_CONTENT`, `MANAGE`, or `MODERATE` task capability

---

## Reading Posts (`/posts` vs `/published_posts`)

```
GET /v22.0/{page-id}/posts?fields=id,message,created_time,permalink_url&limit=25&access_token={token}
GET /v22.0/{page-id}/published_posts?fields=id,message,created_time&limit=25&access_token={token}
```

- `/posts` — posts published by the page itself (not visitor posts)
- `/published_posts` — all published posts, including those created via API
- `/feed` — posts by the page AND by visitors to the page

---

## Post Node Fields

```
GET /v22.0/{post-id}?fields={fields}&access_token={token}
```

### Core Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Post ID |
| `message` | string | Text content |
| `story` | string | Auto-generated activity description |
| `created_time` | datetime | Publication timestamp |
| `updated_time` | datetime | Last modification |
| `permalink_url` | string | Permanent URL |
| `from` | object | Author `{id, name}` |

### Media
| Field | Type | Description |
|-------|------|-------------|
| `full_picture` | string | Image URL (max 720px) |
| `object_id` | string | Uploaded photo/video ID |
| `source` | string | Flash/video file URL |
| `icon` | string | Post type icon link |
| `height`, `width` | int | Dimensions |

### Engagement
| Field | Type | Description |
|-------|------|-------------|
| `shares` | object | `{"count": N}` |
| `likes` | edge | Likes edge (use `likes.summary(true)` for count) |
| `comments` | edge | Comments edge |
| `reactions` | edge | Reactions edge |

### Status & Visibility
| Field | Type | Description |
|-------|------|-------------|
| `is_published` | bool | Publication status |
| `is_hidden` | bool | Whether hidden |
| `is_popular` | bool | Popularity flag |
| `is_expired` | bool | Whether expired |
| `status_type` | string | Type of status update |
| `privacy` | object | Privacy settings |

### Scheduling & Targeting
| Field | Type | Description |
|-------|------|-------------|
| `scheduled_publish_time` | datetime | Scheduled publish time |
| `backdated_time` | datetime | Backdated timestamp |
| `targeting` | object | Demographic restrictions |
| `feed_targeting` | object | News feed audience controls |
| `timeline_visibility` | string | Timeline display |

### Ads & Promotion
| Field | Type | Description |
|-------|------|-------------|
| `is_eligible_for_promotion` | bool | Can be boosted |
| `promotable_id` | string | ID for promotion |
| `allowed_advertising_objectives` | array | Ad objective restrictions |
| `is_inline_created` | bool | Created as ad |

### Administrative
| Field | Type | Description |
|-------|------|-------------|
| `admin_creator` | object | Multi-admin page creator |
| `application` | object | App that published the post |
| `call_to_action` | object | Mobile app CTA |
| `place` | object | Associated location |
| `message_tags` | array | Mentioned profiles |
| `story_tags` | array | Tagged items |
| `parent_id` | string | Parent post ID |
| `child_attachments` | array | Multi-link share objects |

### Post Edges
| Edge | Description |
|------|-------------|
| `comments` | Comments on the post |
| `likes` | Users who liked |
| `reactions` | All reaction types |
| `attachments` | Media attachments |
| `insights` | Post-level analytics |
| `sharedposts` | Posts that shared this post |
| `sponsor_tags` | Tagged sponsor pages |

---

## Publishing Posts

```
POST /v22.0/{page-id}/feed
  access_token={PAGE_ACCESS_TOKEN}
```

### Required (at least one of)
| Parameter | Description |
|-----------|-------------|
| `message` | Text content |
| `link` | URL to attach |

### Optional Publishing Fields
| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | string | Post text |
| `link` | string | URL to attach |
| `published` | bool | `true` (default) = publish immediately |
| `scheduled_publish_time` | int | Unix timestamp (10 min to 75 days in future). Requires `published=false` |
| `backdated_time` | int | Unix timestamp to backdate post |
| `place` | string | Location page ID |
| `tags` | string | CSV of tagged user IDs |
| `call_to_action` | object | `{"type": "SIGN_UP", "value": {"link": "https://..."}}` |
| `feed_targeting` | object | Audience targeting by age, location, interests |
| `targeting` | object | Visibility restrictions |
| `child_attachments` | array | Multiple links (2–5 objects; 2–10 with multi_share_optimized) |
| `multi_share_optimized` | bool | Let Facebook optimize multi-link order |

### Publishing Required Permissions
- Page access token with `CREATE_CONTENT` task capability
- `pages_manage_posts`
- `pages_read_engagement`
- `pages_show_list`

### Response
```json
{"id": "{page-id}_{post-id}"}
```

---

## Publishing Photos

```
POST /v22.0/{page-id}/photos
  url=https://example.com/image.jpg
  caption=My photo caption
  access_token={PAGE_ACCESS_TOKEN}
```

Or upload directly:
```
POST /v22.0/{page-id}/photos
  source=@/path/to/image.jpg
  caption=Caption text
  access_token={PAGE_ACCESS_TOKEN}
```

---

## Publishing Videos

```
POST https://graph-video.facebook.com/v22.0/{page-id}/videos
  file_url=https://example.com/video.mp4
  description=Video description
  title=Video Title
  access_token={PAGE_ACCESS_TOKEN}
```

---

## Error Codes

| Code | Meaning |
|------|---------|
| 100 | Invalid parameter |
| 190 | Invalid access token |
| 200 | Permission denied |
| 210 | User not visible |
| 368 | Content flagged as abusive |
| 80001 | Rate limit exceeded |
| 551 | User unavailable |

---

## Permissions Summary

| Operation | Required Permission(s) |
|-----------|----------------------|
| Read page basic info | None (public pages) or `pages_read_engagement` |
| Read page feed / posts | `pages_read_engagement`, `pages_read_user_content` |
| Read page insights | `read_insights`, `pages_read_engagement` |
| Publish posts | `pages_manage_posts`, `pages_show_list` |
| Reply to comments | `pages_manage_engagement` |
| Read messages | `pages_messaging` |
| Webhook subscriptions | `pages_manage_metadata` |
| Lead forms | `leads_retrieval` |
