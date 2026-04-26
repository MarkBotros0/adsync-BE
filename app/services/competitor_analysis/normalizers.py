"""Normalize raw Apify dataset items into compact, frontend-friendly shapes.

Each function returns ``(data, summary)`` where:
  * ``data``    — the per-actor list/dict the detail tab will render
  * ``summary`` — small dict of headline numbers used in list cards / pills
"""
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

NormalizedResult = tuple[list[dict[str, Any]] | dict[str, Any], dict[str, Any]]


def _safe_int(v: Any) -> int:
    try:
        return int(v) if v is not None else 0
    except (ValueError, TypeError):
        return 0


def _truncate(text: Any, n: int = 500) -> str | None:
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text:
        return None
    return text if len(text) <= n else text[: n - 1] + "…"


def _pick(d: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value among the given keys."""
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


def _to_iso_date(v: Any) -> str | None:
    """Coerce Apify's mixed date shapes to an ISO-8601 string (YYYY-MM-DD).

    The ``apify/facebook-ads-scraper`` actor emits ``start_date`` / ``end_date``
    as **Unix seconds** (e.g. ``1735603200``). Passing that to JS ``new Date(n)``
    interprets it as milliseconds and lands ~20 days after epoch (Jan 1970).
    Always normalize to a string here so consumers (frontend, pandas
    aggregations) get a stable type.
    """
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        ts = float(v)
        if ts > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        if s.isdigit():
            return _to_iso_date(int(s))
        return s
    return None


_TEMPLATE_TOKEN_RE = re.compile(r"\{\{[^}]+\}\}")


def _clean_ad_body(text: Any, brand_name: str | None) -> str | None:
    """Strip Mustache-style template tokens (e.g. ``{{product.brand}}``) that
    Facebook substitutes server-side at impression time. Replace with the
    competitor's brand name when known so the copy reads naturally."""
    if not isinstance(text, str):
        return None
    replacement = brand_name.strip() if isinstance(brand_name, str) and brand_name.strip() else ""
    cleaned = _TEMPLATE_TOKEN_RE.sub(replacement, text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


# ── 1. Facebook Ads ──────────────────────────────────────────────────────────

def normalize_facebook_ads(
    items: list[dict[str, Any]],
    brand_name: str | None = None,
) -> NormalizedResult:
    ads: list[dict[str, Any]] = []
    for raw in items[:60]:
        snap = raw.get("snapshot") or {}

        body_text = _pick(
            snap, "body"
        )
        if isinstance(body_text, dict):
            body_text = body_text.get("text") or body_text.get("markup")
        body_text = body_text or _pick(raw, "ad_creative_body", "body", "adCreativeBody")
        body_text = _clean_ad_body(body_text, brand_name)

        media: list[dict[str, str]] = []

        for c in (snap.get("cards") or [])[:3]:
            url = _pick(
                c,
                "video_preview_image_url", "videoPreviewImageUrl",
                "resized_image_url", "resizedImageUrl",
                "original_image_url", "originalImageUrl",
            )
            if url:
                has_video = bool(_pick(c, "video_hd_url", "videoHdUrl", "video_sd_url", "videoSdUrl"))
                media.append({"url": url, "type": "video" if has_video else "image"})

        if not media:
            for v in (snap.get("videos") or [])[:1]:
                url = _pick(
                    v,
                    "video_preview_image_url", "videoPreviewImageUrl",
                    "video_hd_url", "videoHdUrl",
                )
                if url:
                    media.append({"url": url, "type": "video"})
            for i in (snap.get("images") or [])[:2]:
                url = _pick(
                    i,
                    "resized_image_url", "resizedImageUrl",
                    "original_image_url", "originalImageUrl",
                )
                if url:
                    media.append({"url": url, "type": "image"})

        page_name = _pick(
            raw, "page_name", "pageName"
        ) or _pick(snap, "page_name", "pageName")

        page_url = _pick(raw, "page_url", "pageUrl") or _pick(snap, "page_profile_uri", "pageProfileUri")

        ad_entry = {
            "id": _pick(raw, "ad_archive_id", "adArchiveId", "id"),
            "page_name": page_name,
            "page_url": page_url,
            "body": _truncate(body_text, 600),
            "cta": _pick(snap, "cta_text", "ctaText") or _pick(raw, "cta_text", "ctaText"),
            "link_url": _pick(snap, "link_url", "linkUrl") or _pick(raw, "link_url", "linkUrl"),
            "start_date": _to_iso_date(_pick(raw, "start_date", "startDate", "start_date_string")),
            "end_date": _to_iso_date(_pick(raw, "end_date", "endDate", "end_date_string")),
            "is_active": raw.get("is_active") if raw.get("is_active") is not None else raw.get("isActive"),
            "platforms": _pick(raw, "publisher_platform", "publisherPlatform", "publisher_platforms") or [],
            "regions": _pick(raw, "regions", "eu_total_reach_breakdown") or [],
            "media": media,
        }

        # Drop ads with no usable signal: no page name AND no media AND no body.
        if not (ad_entry["page_name"] or ad_entry["media"] or ad_entry["body"]):
            continue
        ads.append(ad_entry)

    active = sum(1 for a in ads if a.get("is_active"))
    page_names = sorted({a["page_name"] for a in ads if a.get("page_name")})

    return ads, {
        "ads_total": len(ads),
        "ads_active": active,
        "pages": page_names[:5],
    }


# ── 2. Website crawler ────────────────────────────────────────────────────────

def normalize_website(items: list[dict[str, Any]]) -> NormalizedResult:
    pages: list[dict[str, Any]] = []
    for raw in items[:30]:
        if not isinstance(raw, dict):
            continue
        text = raw.get("text") or raw.get("markdown") or ""
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        title = metadata.get("title") or raw.get("title")
        description = metadata.get("description") or raw.get("description")
        pages.append({
            "url": raw.get("url"),
            "title": title if isinstance(title, str) else None,
            "description": _truncate(description, 300),
            "headings": _extract_headings(raw),
            "word_count": len(text.split()) if isinstance(text, str) else 0,
            "excerpt": _truncate(text, 600),
        })

    homepage = next((p for p in pages if p.get("url") and _is_root(p["url"])), pages[0] if pages else None)

    summary = {
        "pages_count": len(pages),
        "homepage_title": homepage.get("title") if homepage else None,
        "homepage_description": homepage.get("description") if homepage else None,
        "total_words": sum(p["word_count"] for p in pages),
    }
    return pages, summary


def _extract_headings(raw: dict[str, Any]) -> list[str]:
    """Pull the first few headings from a website-content-crawler item.

    The actor's headings field shape varies: sometimes ``metadata.headers`` is a
    dict like ``{"h1": ["..."], "h2": ["..."]}``, sometimes a list of strings,
    sometimes top-level ``h1``/``h2`` keys. Handle all three defensively.
    """
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}

    candidates: list[Any] = [
        metadata.get("headers"),
        metadata.get("headings"),
        raw.get("headings"),
        raw.get("headers"),
    ]
    out: list[str] = []
    for source in candidates:
        if isinstance(source, list):
            for item in source:
                if isinstance(item, str) and item.strip():
                    out.append(item.strip())
        elif isinstance(source, dict):
            # Walk h1, h2, ... in order.
            for key in ("h1", "h2", "h3", "h4"):
                v = source.get(key)
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and item.strip():
                            out.append(item.strip())
                elif isinstance(v, str) and v.strip():
                    out.append(v.strip())

    # Also check top-level h1/h2 fields some crawler variants emit directly.
    for key in ("h1", "h2", "h3"):
        v = raw.get(key)
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str) and item.strip():
                    out.append(item.strip())
        elif isinstance(v, str) and v.strip():
            out.append(v.strip())

    # De-dupe while preserving order; cap at 6.
    seen: set[str] = set()
    deduped: list[str] = []
    for h in out:
        if h not in seen:
            seen.add(h)
            deduped.append(h)
        if len(deduped) >= 6:
            break
    return deduped


def _is_root(url: str) -> bool:
    try:
        path = urlparse(url).path or "/"
        return path in ("/", "")
    except Exception:
        return False


# ── 3. Google Search SERP ─────────────────────────────────────────────────────

def normalize_google_search(items: list[dict[str, Any]]) -> NormalizedResult:
    organic: list[dict[str, Any]] = []
    paa: list[str] = []
    related: list[str] = []

    for page in items:
        for result in (page.get("organicResults") or [])[:10]:
            organic.append({
                "rank": result.get("position"),
                "title": result.get("title"),
                "url": result.get("url"),
                "domain": result.get("displayedUrl") or _domain(result.get("url")),
                "description": _truncate(result.get("description"), 240),
            })
        for q in (page.get("peopleAlsoAsk") or []):
            text = q.get("question") if isinstance(q, dict) else q
            if isinstance(text, str):
                paa.append(text)
        for r in (page.get("relatedQueries") or []):
            text = r.get("title") if isinstance(r, dict) else r
            if isinstance(text, str):
                related.append(text)

    organic.sort(key=lambda r: r.get("rank") or 99)

    summary = {
        "results_count": len(organic),
        "top_domain": organic[0]["domain"] if organic else None,
        "top_url": organic[0]["url"] if organic else None,
        "people_also_ask": paa[:5],
    }
    return {"organic": organic, "people_also_ask": paa[:8], "related": related[:8]}, summary


def _domain(url: Any) -> str | None:
    if not isinstance(url, str):
        return None
    try:
        return urlparse(url).netloc or None
    except Exception:
        return None


# ── 4. Instagram ──────────────────────────────────────────────────────────────

def normalize_instagram(items: list[dict[str, Any]]) -> NormalizedResult:
    profiles: list[dict[str, Any]] = []
    posts: list[dict[str, Any]] = []

    for raw in items:
        if raw.get("type") == "user" or "username" in raw and "followersCount" in raw:
            profiles.append({
                "username": raw.get("username"),
                "full_name": raw.get("fullName") or raw.get("full_name"),
                "biography": _truncate(raw.get("biography"), 280),
                "followers": _safe_int(raw.get("followersCount") or raw.get("followers_count")),
                "follows": _safe_int(raw.get("followsCount") or raw.get("follows_count")),
                "posts_count": _safe_int(raw.get("postsCount") or raw.get("posts_count")),
                "is_verified": raw.get("verified") or raw.get("is_verified") or False,
                "profile_pic_url": raw.get("profilePicUrl") or raw.get("profile_pic_url"),
                "external_url": raw.get("externalUrl") or raw.get("external_url"),
            })
            for post in (raw.get("latestPosts") or raw.get("posts") or [])[:12]:
                posts.append(_normalize_ig_post(post, raw.get("username")))
        elif "shortCode" in raw or "url" in raw and raw.get("type") in ("Image", "Video", "Sidecar"):
            posts.append(_normalize_ig_post(raw, raw.get("ownerUsername")))

    profiles.sort(key=lambda p: p.get("followers") or 0, reverse=True)
    top = profiles[0] if profiles else None

    summary = {
        "top_username": top.get("username") if top else None,
        "followers": top.get("followers") if top else 0,
        "posts_count": top.get("posts_count") if top else 0,
        "matches": len(profiles),
    }
    return {"profiles": profiles, "posts": posts[:30]}, summary


def _normalize_ig_post(p: dict[str, Any], owner_username: str | None) -> dict[str, Any]:
    return {
        "id": p.get("id") or p.get("shortCode"),
        "shortcode": p.get("shortCode"),
        "url": p.get("url"),
        "type": p.get("type"),
        "caption": _truncate(p.get("caption"), 400),
        "likes": _safe_int(p.get("likesCount") or p.get("likes_count")),
        "comments": _safe_int(p.get("commentsCount") or p.get("comments_count")),
        "video_views": _safe_int(p.get("videoViewCount") or p.get("video_view_count")),
        "timestamp": p.get("timestamp"),
        "display_url": p.get("displayUrl") or p.get("display_url"),
        "owner_username": owner_username or p.get("ownerUsername"),
    }


# ── 5. TikTok ─────────────────────────────────────────────────────────────────

def normalize_tiktok(items: list[dict[str, Any]]) -> NormalizedResult:
    videos: list[dict[str, Any]] = []
    authors: dict[str, dict[str, Any]] = {}

    for raw in items[:50]:
        author_info = raw.get("authorMeta") or {}
        author_name = author_info.get("name") or author_info.get("nickName") or raw.get("author")
        if author_name and author_name not in authors:
            authors[author_name] = {
                "username": author_name,
                "nickname": author_info.get("nickName"),
                "followers": _safe_int(author_info.get("fans")),
                "following": _safe_int(author_info.get("following")),
                "hearts": _safe_int(author_info.get("heart") or author_info.get("heartCount")),
                "video_count": _safe_int(author_info.get("video")),
                "verified": author_info.get("verified") or False,
                "avatar": author_info.get("avatar"),
                "signature": _truncate(author_info.get("signature"), 240),
            }

        videos.append({
            "id": raw.get("id"),
            "url": raw.get("webVideoUrl") or raw.get("url"),
            "description": _truncate(raw.get("text") or raw.get("description"), 400),
            "create_time": raw.get("createTimeISO") or raw.get("createTime"),
            "duration": _safe_int(raw.get("videoMeta", {}).get("duration") if isinstance(raw.get("videoMeta"), dict) else 0),
            "cover": (raw.get("videoMeta") or {}).get("coverUrl") if isinstance(raw.get("videoMeta"), dict) else raw.get("covers", [None])[0] if raw.get("covers") else None,
            "plays": _safe_int(raw.get("playCount")),
            "likes": _safe_int(raw.get("diggCount")),
            "comments": _safe_int(raw.get("commentCount")),
            "shares": _safe_int(raw.get("shareCount")),
            "author": author_name,
            "music_name": (raw.get("musicMeta") or {}).get("musicName") if isinstance(raw.get("musicMeta"), dict) else None,
            "hashtags": [h.get("name") for h in (raw.get("hashtags") or []) if isinstance(h, dict) and h.get("name")][:8],
        })

    author_list = sorted(authors.values(), key=lambda a: a.get("followers") or 0, reverse=True)
    top = author_list[0] if author_list else None

    summary = {
        "top_username": top.get("username") if top else None,
        "followers": top.get("followers") if top else 0,
        "videos_count": len(videos),
        "total_plays": sum(v.get("plays") or 0 for v in videos),
    }
    return {"authors": author_list, "videos": videos}, summary


# ── 6. Google Places ──────────────────────────────────────────────────────────

def normalize_google_places(items: list[dict[str, Any]]) -> NormalizedResult:
    places: list[dict[str, Any]] = []
    for raw in items[:15]:
        loc = raw.get("location") or {}
        reviews_raw = raw.get("reviews") or []
        reviews: list[dict[str, Any]] = []
        for r in reviews_raw[:6]:
            reviews.append({
                "name": r.get("name"),
                "rating": _safe_int(r.get("stars") or r.get("rating")),
                "text": _truncate(r.get("text") or r.get("textTranslated"), 360),
                "published_at": r.get("publishedAtDate") or r.get("publishedAt"),
            })

        places.append({
            "id": raw.get("placeId") or raw.get("place_id") or raw.get("cid"),
            "name": raw.get("title") or raw.get("name"),
            "category": raw.get("categoryName") or (raw.get("categories") or [None])[0],
            "address": raw.get("address"),
            "city": raw.get("city"),
            "country": raw.get("countryCode") or raw.get("country"),
            "phone": raw.get("phone"),
            "website": raw.get("website"),
            "rating": float(raw.get("totalScore") or 0) if raw.get("totalScore") is not None else None,
            "reviews_count": _safe_int(raw.get("reviewsCount")),
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "url": raw.get("url"),
            "image_url": raw.get("imageUrl") or (raw.get("imageUrls") or [None])[0],
            "reviews": reviews,
        })

    ratings = [p["rating"] for p in places if isinstance(p.get("rating"), (int, float))]
    summary = {
        "places_count": len(places),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "total_reviews": sum(p.get("reviews_count") or 0 for p in places),
    }
    return places, summary


def extract_top_url_from_serp(serp_data: dict[str, Any]) -> str | None:
    """Extract the top organic URL from a normalized SERP payload (used to feed website crawler)."""
    organic = serp_data.get("organic") if isinstance(serp_data, dict) else None
    if not isinstance(organic, list):
        return None
    for r in organic:
        url = r.get("url")
        if isinstance(url, str) and url.startswith("http"):
            return url
    return None
