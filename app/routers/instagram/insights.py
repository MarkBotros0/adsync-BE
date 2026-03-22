"""Instagram insights and analytics endpoints."""
from fastapi import APIRouter, HTTPException

from app.services.instagram.media import InstagramMediaService
from app.services.instagram.insights import InstagramInsightsService
from app.routers.instagram.session import get_instagram_session

router = APIRouter(prefix="/instagram", tags=["Instagram"])

_VALID_PERIODS = {"day", "week", "days_28", "month"}
_VALID_MEDIA_PRODUCT_TYPES = {"FEED", "REELS", "STORY"}


# ─── Session-based endpoints (ig_user_id resolved from session) ───────────────

@router.get("/account/insights")
async def get_instagram_account_insights(
    session_id: str,
    period: str = "day",
    since: str | None = None,
    until: str | None = None,
):
    """Get time-series account insights for the connected Instagram account.

    `period`: `day`, `week`, `days_28`, or `month`.
    """
    if period not in _VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Must be one of: {', '.join(sorted(_VALID_PERIODS))}",
        )
    session = get_instagram_session(session_id)

    svc = InstagramInsightsService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_account_insights(
            session["ig_user_id"], period=period, since=since, until=until
        )
        return {"success": True, "data": svc._format_timeseries(raw)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch insights: {str(e)}")


@router.get("/account/insights/summary")
async def get_instagram_account_insights_summary(session_id: str, days: int = 30):
    """Get a comprehensive analytics summary for the connected Instagram account.

    `days`: number of days to summarize (1–90).
    """
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="days must be between 1 and 90")
    session = get_instagram_session(session_id)

    svc = InstagramInsightsService(access_token=session["access_token"])
    try:
        summary = await svc.fetch_account_summary(session["ig_user_id"], days=days)
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch insights summary: {str(e)}")


@router.get("/account/media/with-insights")
async def get_instagram_account_media_with_insights(
    session_id: str,
    limit: int = 10,
    since: str | None = None,
    until: str | None = None,
):
    """Get recent feed media with per-post insights for the connected account (max 25)."""
    limit = min(limit, 25)
    session = get_instagram_session(session_id)

    token = session["access_token"]
    ig_user_id = session["ig_user_id"]
    media_svc = InstagramMediaService(access_token=token)
    insights_svc = InstagramInsightsService(access_token=token)

    try:
        raw = await media_svc.fetch_media(ig_user_id, limit=limit, since=since, until=until)
        formatted = media_svc.format_media_list(raw)

        enriched = []
        for item in formatted["media"]:
            mpt = item.get("media_product_type") or "FEED"
            mt = item.get("media_type")
            insights = await insights_svc.fetch_media_insights(
                item["id"], media_product_type=mpt, media_type=mt
            )
            enriched.append({**item, "insights": insights.get("metrics", {})})

        return {
            "success": True,
            "data": {
                "ig_user_id": ig_user_id,
                "username": session["username"],
                "total": formatted["total"],
                "media": enriched,
                "paging": formatted["paging"],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media with insights: {str(e)}")


@router.get("/account/reels/with-insights")
async def get_instagram_account_reels_with_insights(
    session_id: str,
    limit: int = 10,
    since: str | None = None,
    until: str | None = None,
):
    """Get Reels with per-reel insights for the connected account (max 25).

    Insight metrics: plays, reach, likes, comments, shares, saved, total_interactions.
    """
    limit = min(limit, 25)
    session = get_instagram_session(session_id)

    token = session["access_token"]
    ig_user_id = session["ig_user_id"]
    media_svc = InstagramMediaService(access_token=token)
    insights_svc = InstagramInsightsService(access_token=token)

    try:
        raw = await media_svc.fetch_reels(ig_user_id, limit=limit, since=since, until=until)
        formatted = media_svc.format_media_list(raw)

        enriched = []
        for item in formatted["media"]:
            mt = item.get("media_type")
            insights = await insights_svc.fetch_media_insights(
                item["id"], media_product_type="REELS", media_type=mt
            )
            enriched.append({**item, "insights": insights.get("metrics", {})})

        return {
            "success": True,
            "data": {
                "ig_user_id": ig_user_id,
                "username": session["username"],
                "total": formatted["total"],
                "reels": enriched,
                "paging": formatted["paging"],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch reels with insights: {str(e)}")


# ─── Per-media endpoints ───────────────────────────────────────────────────────

@router.get("/media/{media_id}/insights")
async def get_media_insights(
    media_id: str,
    session_id: str,
    media_product_type: str = "FEED",
):
    """Get performance insights for a single IG Media object.

    `media_product_type`: `FEED` (default), `REELS`, or `STORY`.
    """
    if media_product_type.upper() not in _VALID_MEDIA_PRODUCT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid media_product_type. Must be one of: FEED, REELS, STORY",
        )
    session = get_instagram_session(session_id)

    svc = InstagramInsightsService(access_token=session["access_token"])
    try:
        result = await svc.fetch_media_insights(media_id, media_product_type=media_product_type)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media insights: {str(e)}")


# ─── Per-account endpoints (explicit ig_user_id) ──────────────────────────────

@router.get("/accounts/{ig_user_id}/insights")
async def get_account_insights(
    ig_user_id: str,
    session_id: str,
    period: str = "day",
    since: str | None = None,
    until: str | None = None,
):
    """Get time-series account-level insights.

    `period`: `day`, `week`, `days_28`, or `month`.
    """
    if period not in _VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Must be one of: {', '.join(sorted(_VALID_PERIODS))}",
        )
    session = get_instagram_session(session_id)

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
    session = get_instagram_session(session_id)

    svc = InstagramInsightsService(access_token=session["access_token"])
    try:
        summary = await svc.fetch_account_summary(ig_user_id, days=days)
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch insights summary: {str(e)}")


@router.get("/accounts/{ig_user_id}/insights/audience")
async def get_audience_demographics(ig_user_id: str, session_id: str):
    """Get lifetime audience demographics: gender/age, top cities, top countries."""
    session = get_instagram_session(session_id)

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
    since: str | None = None,
    until: str | None = None,
):
    """Get the most recent feed media with per-post insights included (max 25)."""
    limit = min(limit, 25)
    session = get_instagram_session(session_id)

    token = session["access_token"]
    media_svc = InstagramMediaService(access_token=token)
    insights_svc = InstagramInsightsService(access_token=token)

    try:
        raw = await media_svc.fetch_media(ig_user_id, limit=limit, since=since, until=until)
        formatted = media_svc.format_media_list(raw)

        enriched = []
        for item in formatted["media"]:
            mpt = item.get("media_product_type") or "FEED"
            mt = item.get("media_type")
            insights = await insights_svc.fetch_media_insights(
                item["id"], media_product_type=mpt, media_type=mt
            )
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
