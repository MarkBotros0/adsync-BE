from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException

from app.services.instagram.account import InstagramAccountService
from app.services.instagram.media import InstagramMediaService
from app.services.instagram.insights import InstagramInsightsService
from app.repositories.instagram_session import InstagramSessionRepository
from app.database import get_session_local

router = APIRouter(prefix="/instagram", tags=["Instagram"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_instagram_session(session_id: str) -> dict:
    """Look up a valid Instagram session by ID, or raise 401."""
    db = get_session_local()()
    try:
        repo = InstagramSessionRepository(db)
        session = repo.get_by_session_id(session_id)
        if not session or session.expires_at.replace(tzinfo=None) < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Invalid or expired Instagram session")
        return {
            "ig_user_id": session.ig_user_id,
            "username": session.username,
            "access_token": session.access_token,
        }
    finally:
        db.close()


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/accounts/{ig_user_id}/profile")
async def get_instagram_profile(ig_user_id: str, session_id: str):
    """Get the full profile for an Instagram account."""
    session = _get_instagram_session(session_id)

    svc = InstagramAccountService(access_token=session["access_token"])
    try:
        profile = await svc.fetch_profile(ig_user_id)
        return {"success": True, "data": profile}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch profile: {str(e)}")


@router.get("/accounts/{ig_user_id}/media")
async def get_instagram_media(
    ig_user_id: str,
    session_id: str,
    limit: int = 25,
    since: Optional[str] = None,
    until: Optional[str] = None,
    after: Optional[str] = None,
):
    """
    Get feed media (images, videos, reels, carousels) with engagement counts.

    Pagination:
    - Use `after` (from `paging.cursors.after`) for the next page.
    - Use `since` / `until` (Unix timestamps) for time-range filtering.
    """
    if limit > 100:
        limit = 100
    session = _get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_media(ig_user_id, limit=limit, since=since, until=until, after=after)
        return {"success": True, "data": svc.format_media_list(raw)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media: {str(e)}")


@router.get("/accounts/{ig_user_id}/stories")
async def get_instagram_stories(ig_user_id: str, session_id: str):
    """Get currently active stories (24-hour window only)."""
    session = _get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_stories(ig_user_id)
        stories = raw.get("data", [])
        return {"success": True, "data": {"total": len(stories), "stories": stories}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch stories: {str(e)}")


@router.get("/media/{media_id}")
async def get_single_media(media_id: str, session_id: str):
    """Get metadata for a single IG Media object."""
    session = _get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        media = await svc.fetch_single_media(media_id)
        return {"success": True, "data": media}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media: {str(e)}")


@router.get("/media/{media_id}/comments")
async def get_media_comments(media_id: str, session_id: str, limit: int = 50):
    """Get top-level comments on an IG Media object (max 50 per request)."""
    session = _get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_media_comments(media_id, limit=limit)
        comments = raw.get("data", [])
        return {
            "success": True,
            "data": {
                "media_id": media_id,
                "total": len(comments),
                "comments": comments,
                "paging": raw.get("paging", {}),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch comments: {str(e)}")


@router.get("/media/{media_id}/children")
async def get_carousel_children(media_id: str, session_id: str):
    """Get child items for a CAROUSEL_ALBUM post."""
    session = _get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_carousel_children(media_id)
        children = raw.get("data", [])
        return {
            "success": True,
            "data": {"media_id": media_id, "total": len(children), "children": children},
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch carousel children: {str(e)}")


@router.get("/media/{media_id}/insights")
async def get_media_insights(
    media_id: str,
    session_id: str,
    media_product_type: str = "FEED",
):
    """
    Get performance insights for a single IG Media object.
    `media_product_type`: `FEED` (default), `REELS`, or `STORY`.
    """
    valid_types = {"FEED", "REELS", "STORY"}
    if media_product_type.upper() not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid media_product_type. Must be one of: FEED, REELS, STORY",
        )
    session = _get_instagram_session(session_id)

    svc = InstagramInsightsService(access_token=session["access_token"])
    try:
        result = await svc.fetch_media_insights(media_id, media_product_type=media_product_type)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media insights: {str(e)}")


@router.get("/accounts/{ig_user_id}/insights")
async def get_account_insights(
    ig_user_id: str,
    session_id: str,
    period: str = "day",
    since: Optional[str] = None,
    until: Optional[str] = None,
):
    """
    Get time-series account-level insights.
    `period`: `day`, `week`, `days_28`, or `month`.
    """
    valid_periods = {"day", "week", "days_28", "month"}
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Must be one of: {', '.join(sorted(valid_periods))}",
        )
    session = _get_instagram_session(session_id)

    svc = InstagramInsightsService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_account_insights(ig_user_id, period=period, since=since, until=until)
        return {"success": True, "data": svc._format_timeseries(raw)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch account insights: {str(e)}")


@router.get("/accounts/{ig_user_id}/insights/summary")
async def get_account_insights_summary(ig_user_id: str, session_id: str, days: int = 30):
    """Get a comprehensive analytics summary for the last N days (1–90)."""
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="days must be between 1 and 90")
    session = _get_instagram_session(session_id)

    svc = InstagramInsightsService(access_token=session["access_token"])
    try:
        summary = await svc.fetch_account_summary(ig_user_id, days=days)
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch insights summary: {str(e)}")


@router.get("/accounts/{ig_user_id}/insights/audience")
async def get_audience_demographics(ig_user_id: str, session_id: str):
    """Get lifetime audience demographics: gender/age, top cities, top countries."""
    session = _get_instagram_session(session_id)

    svc = InstagramInsightsService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_audience_demographics(ig_user_id)
        return {"success": True, "data": svc._format_demographics(raw)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch demographics: {str(e)}")


@router.get("/accounts/{ig_user_id}/media/with-insights")
async def get_media_with_insights(
    ig_user_id: str,
    session_id: str,
    limit: int = 10,
    since: Optional[str] = None,
    until: Optional[str] = None,
):
    """Get the most recent feed media with per-post insights included (max 25)."""
    limit = min(limit, 25)
    session = _get_instagram_session(session_id)

    token = session["access_token"]
    media_svc = InstagramMediaService(access_token=token)
    insights_svc = InstagramInsightsService(access_token=token)

    try:
        raw = await media_svc.fetch_media(ig_user_id, limit=limit, since=since, until=until)
        formatted = media_svc.format_media_list(raw)

        enriched = []
        for item in formatted["media"]:
            mpt = item.get("media_product_type") or "FEED"
            insights = await insights_svc.fetch_media_insights(item["id"], media_product_type=mpt)
            enriched.append({**item, "insights": insights.get("metrics", {})})

        return {
            "success": True,
            "data": {
                "total": formatted["total"],
                "media": enriched,
                "paging": formatted["paging"],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media with insights: {str(e)}")
