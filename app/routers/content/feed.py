"""Unified content feed — fetches from all connected platforms in a single call."""
import asyncio
import logging
import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import require_brand
from app.repositories.facebook_session import FacebookSessionRepository
from app.repositories.instagram_session import InstagramSessionRepository
from app.repositories.tiktok_session import TikTokSessionRepository
from app.database import get_session_local
from app.services.facebook.pages import PagesService
from app.services.instagram.media import InstagramMediaService
from app.services.tiktok.videos import TikTokVideoService

router = APIRouter(prefix="/content", tags=["Content Feed"])
logger = logging.getLogger(__name__)

_HASHTAG_RE = re.compile(r"#\w+")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hashtags(text: str | None) -> list[str] | None:
    if not text:
        return None
    tags = _HASHTAG_RE.findall(text)
    return tags if tags else None


def _perf(interactions: int) -> int:
    """Map raw interaction count to a 1–10 performance score."""
    return min(10, max(1, -(-interactions // 5)))  # ceiling division


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


# ── Transformers ──────────────────────────────────────────────────────────────

def _fb_to_mentions(posts: list[dict[str, Any]], page_name: str) -> list[dict[str, Any]]:
    result = []
    for p in posts:
        msg = p.get("message") or p.get("story") or ""
        if not msg:
            continue
        eng = p.get("engagement") or {}
        total = eng.get("total", 0)
        reactions = eng.get("reactions", 0)
        result.append({
            "id": p["id"],
            "platform": "facebook",
            "author": {
                "name": page_name,
                "username": f"@{page_name.lower().replace(' ', '')}",
                "followers": 0,
            },
            "content": msg,
            "url": p.get("permalink_url") or "#",
            "created_at": p.get("created_time"),
            "sentiment": "neutral",
            "reach": reactions * 10,
            "interactions": total,
            "performance": _perf(total),
            "language": "en",
            "hashtags": _hashtags(msg),
            "image_url": None,
        })
    return result


def _ig_to_mentions(items: list[dict[str, Any]], username: str) -> list[dict[str, Any]]:
    result = []
    for item in items:
        if item.get("media_product_type") == "STORY":
            continue
        cap = item.get("caption") or ""
        eng = item.get("engagement") or {}
        interactions = eng.get("likes", 0) + eng.get("comments", 0)
        views = eng.get("views", 0)
        is_reel = item.get("media_product_type") == "REELS"
        reach = views if is_reel else eng.get("likes", 0) * 10
        uname = item.get("username") or username
        result.append({
            "id": item["id"],
            "platform": "instagram",
            "author": {
                "name": uname,
                "username": f"@{uname}",
                "followers": 0,
            },
            "content": cap,
            "url": item.get("permalink") or "#",
            "created_at": item.get("timestamp"),
            "sentiment": "neutral",
            "reach": reach,
            "interactions": interactions,
            "performance": _perf(interactions),
            "language": "en",
            "hashtags": _hashtags(cap),
            "image_url": None,
        })
    return result


def _tt_to_mentions(videos: list[dict[str, Any]], display_name: str) -> list[dict[str, Any]]:
    result = []
    for v in videos:
        eng = v.get("engagement") or {}
        interactions = eng.get("likes", 0) + eng.get("comments", 0) + eng.get("shares", 0)
        content = v.get("description") or v.get("title") or ""
        ts = v.get("created_at")
        if isinstance(ts, (int, float)):
            created_at = datetime.utcfromtimestamp(ts).isoformat() + "Z"
        else:
            created_at = ts
        result.append({
            "id": v["id"],
            "platform": "tiktok",
            "author": {
                "name": display_name,
                "username": f"@{display_name}",
                "followers": 0,
            },
            "content": content,
            "url": v.get("share_url") or "#",
            "created_at": created_at,
            "sentiment": "neutral",
            "reach": eng.get("views", 0),
            "interactions": interactions,
            "performance": _perf(interactions),
            "language": "en",
            "hashtags": _hashtags(content),
            "image_url": v.get("cover_image_url") or None,
        })
    return result


# ── Per-platform fetchers ─────────────────────────────────────────────────────

async def _fetch_facebook(brand_id: int) -> list[dict[str, Any]]:
    db = get_session_local()()
    try:
        fb_session = FacebookSessionRepository(db).get_by_brand_id(brand_id)
        if not fb_session:
            return []
        user_token = fb_session.access_token
    finally:
        db.close()

    try:
        # Fetch pages list using user access token
        pages_svc = PagesService(access_token=user_token)
        pages_data = await pages_svc.fetch_pages()
        pages = pages_data.get("data", [])
        if not pages:
            return []

        # Use the first page's access token and ID
        page = pages[0]
        page_id: str = page["id"]
        page_token: str = page.get("access_token", user_token)
        page_name: str = page.get("name", "Facebook Page")

        # Fetch posts with page access token
        posts_svc = PagesService(access_token=page_token)
        raw = await posts_svc.fetch_page_posts(page_id, limit=50)
        posts_raw = raw.get("data", [])

        # Transform engagement (matches existing router logic)
        transformed = []
        for p in posts_raw:
            likes = p.get("likes", {}).get("summary", {}).get("total_count", 0)
            comments = p.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares = p.get("shares", {}).get("count", 0)
            reactions = p.get("reactions", {}).get("summary", {}).get("total_count", 0)
            transformed.append({
                "id": p.get("id"),
                "message": p.get("message", ""),
                "story": p.get("story", ""),
                "created_time": p.get("created_time"),
                "permalink_url": p.get("permalink_url"),
                "engagement": {
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                    "reactions": reactions,
                    "total": likes + comments + shares,
                },
            })
        return _fb_to_mentions(transformed, page_name)
    except Exception:
        logger.warning("Failed to fetch Facebook content for brand %d", brand_id, exc_info=True)
        return []


async def _fetch_instagram(brand_id: int) -> list[dict[str, Any]]:
    db = get_session_local()()
    try:
        ig_session = InstagramSessionRepository(db).get_by_brand_id(brand_id)
        if not ig_session:
            return []
        ig_user_id = ig_session.ig_user_id
        username = ig_session.username or ig_session.ig_user_id
        access_token = ig_session.access_token
    finally:
        db.close()

    try:
        svc = InstagramMediaService(access_token=access_token)
        raw = await svc.fetch_media(ig_user_id, limit=50)
        formatted = svc.format_media_list(raw)
        items = formatted.get("media", [])
        return _ig_to_mentions(items, username)
    except Exception:
        logger.warning("Failed to fetch Instagram content for brand %d", brand_id, exc_info=True)
        return []


async def _fetch_tiktok(brand_id: int) -> list[dict[str, Any]]:
    db = get_session_local()()
    try:
        tt_session = TikTokSessionRepository(db).get_by_brand_id(brand_id)
        if not tt_session:
            return []
        access_token = tt_session.access_token
        display_name = tt_session.display_name or tt_session.open_id
    finally:
        db.close()

    try:
        svc = TikTokVideoService(access_token=access_token)
        raw = await svc.fetch_videos(max_count=20)
        formatted = svc.format_video_list(raw)
        videos = formatted.get("videos", [])
        return _tt_to_mentions(videos, display_name)
    except Exception:
        logger.warning("Failed to fetch TikTok content for brand %d", brand_id, exc_info=True)
        return []


async def _noop() -> list[dict[str, Any]]:
    return []


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/feed")
async def get_content_feed(
    brand=Depends(require_brand),
    platforms: str | None = Query(None, description="Comma-separated platforms: facebook,instagram,tiktok"),
    date_from: str | None = Query(None, description="ISO date string, e.g. 2024-01-01"),
    date_to: str | None = Query(None, description="ISO date string, e.g. 2024-12-31"),
    sort: str = Query("recent", description="Sort order: recent | popular"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Fetch content from all connected platforms in a single authenticated call.

    - Auth: Brand JWT Bearer token. Sessions are resolved server-side by brand_id.
    - All platform fetches run in parallel.
    - Results are merged, sorted, filtered, and paginated server-side.
    - Supports optional filtering by `platforms`, `date_from`, `date_to`.
    """
    brand_id: int = brand.id

    platform_filter: set[str] | None = (
        {p.strip().lower() for p in platforms.split(",") if p.strip()}
        if platforms else None
    )

    def _want(p: str) -> bool:
        return platform_filter is None or p in platform_filter

    # Fetch all platforms in parallel
    fb_task = _fetch_facebook(brand_id) if _want("facebook") else _noop()
    ig_task = _fetch_instagram(brand_id) if _want("instagram") else _noop()
    tt_task = _fetch_tiktok(brand_id) if _want("tiktok") else _noop()

    fb_items, ig_items, tt_items = await asyncio.gather(fb_task, ig_task, tt_task)

    all_mentions: list[dict[str, Any]] = [*fb_items, *ig_items, *tt_items]
    platforms_fetched = list({m["platform"] for m in all_mentions})

    # Date filtering
    dt_from = _parse_dt(date_from)
    dt_to = _parse_dt(date_to + "T23:59:59") if date_to else None

    if dt_from or dt_to:
        filtered = []
        for m in all_mentions:
            dt = _parse_dt(m.get("created_at"))
            if dt is None:
                continue
            if dt_from and dt < dt_from:
                continue
            if dt_to and dt > dt_to:
                continue
            filtered.append(m)
        all_mentions = filtered

    # Sort
    if sort == "popular":
        all_mentions.sort(key=lambda m: m.get("interactions", 0), reverse=True)
    else:
        all_mentions.sort(
            key=lambda m: _parse_dt(m.get("created_at")) or datetime.min,
            reverse=True,
        )

    # Aggregate stats (before pagination)
    total = len(all_mentions)
    stats = {
        "total_mentions": total,
        "total_reach": sum(m.get("reach", 0) for m in all_mentions),
        "total_interactions": sum(m.get("interactions", 0) for m in all_mentions),
        "negative_count": 0,
        "positive_count": 0,
        "neutral_count": total,
        "positive_percentage": 0,
    }

    # Paginate
    offset = (page - 1) * page_size
    page_items = all_mentions[offset: offset + page_size]

    return {
        "success": True,
        "data": {
            "items": page_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (offset + page_size) < total,
            "platforms_fetched": platforms_fetched,
            "stats": stats,
        },
    }
