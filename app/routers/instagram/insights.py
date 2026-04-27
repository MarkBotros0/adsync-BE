"""Instagram insights and analytics endpoints.

Two auth styles coexist:
- Legacy session_id-style endpoints (kept for backwards compatibility with the FE).
- New ``/instagram/v2/...`` endpoints under the same router that resolve the IG session
  from the brand JWT (``require_brand``) — these are the ones the analytics dashboard
  rebuild calls.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_session_local
from app.dependencies import require_brand
from app.repositories.instagram_session import InstagramSessionRepository
from app.services.instagram.media import InstagramMediaService
from app.services.instagram.insights import InstagramInsightsService
from app.routers.instagram.session import get_instagram_session

router = APIRouter(prefix="/instagram", tags=["Instagram"])


def _resolve_ig_session_for_brand(brand_id: int) -> tuple[str, str, str]:
    """Return ``(ig_user_id, username, access_token)`` for the brand's IG session, or 404."""
    db = get_session_local()()
    try:
        sess = InstagramSessionRepository(db).get_by_brand_id(brand_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Instagram not connected for this brand")
        return sess.ig_user_id, (sess.username or sess.ig_user_id), sess.access_token
    finally:
        db.close()

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


# ─── New brand-JWT endpoints (drive the analytics dashboard rebuild) ──────────

@router.get("/v2/engagement-totals")
async def get_engagement_totals_v2(
    brand=Depends(require_brand),
    days: int = Query(30, ge=1, le=90),
) -> dict[str, Any]:
    """Headline engagement totals for the brand's IG account over the last N days.

    Includes the action-tap fields (profile links, phone, text, directions) so the
    KPI tiles can show "what did people do after they reached the profile?".
    """
    ig_user_id, username, token = _resolve_ig_session_for_brand(brand.id)
    svc = InstagramInsightsService(access_token=token)
    totals = await svc.fetch_engagement_totals(ig_user_id, days=days)
    return {"success": True, "data": {"ig_user_id": ig_user_id, "username": username, "totals": totals}}


@router.get("/v2/reach-by-follow-type")
async def get_reach_by_follow_type_v2(
    brand=Depends(require_brand),
    days: int = Query(30, ge=1, le=90),
) -> dict[str, Any]:
    """Reach split between FOLLOWER and NON_FOLLOWER for the donut chart."""
    ig_user_id, _, token = _resolve_ig_session_for_brand(brand.id)
    svc = InstagramInsightsService(access_token=token)
    return {"success": True, "data": await svc.fetch_reach_by_follow_type(ig_user_id, days=days)}


@router.get("/v2/reach-by-media-product-type")
async def get_reach_by_media_product_type_v2(
    brand=Depends(require_brand),
    days: int = Query(30, ge=1, le=90),
) -> dict[str, Any]:
    """Reach split by POST / REEL / STORY — drives the 'best content type' card."""
    ig_user_id, _, token = _resolve_ig_session_for_brand(brand.id)
    svc = InstagramInsightsService(access_token=token)
    return {"success": True, "data": await svc.fetch_reach_by_media_product_type(ig_user_id, days=days)}


@router.get("/v2/stories")
async def list_stories_v2(
    brand=Depends(require_brand),
    limit: int = Query(25, ge=1, le=50),
) -> dict[str, Any]:
    """Active stories (24h window) for the Stories filter on /content."""
    ig_user_id, username, token = _resolve_ig_session_for_brand(brand.id)
    svc = InstagramInsightsService(access_token=token)
    items = await svc.fetch_stories(ig_user_id, limit=limit)
    return {"success": True, "data": {"ig_user_id": ig_user_id, "username": username, "stories": items}}


@router.get("/v2/stories/{story_id}/insights")
async def get_story_insights_v2(
    story_id: str,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    """Per-story metrics (taps_forward, taps_back, exits, replies, reach)."""
    _, _, token = _resolve_ig_session_for_brand(brand.id)
    svc = InstagramInsightsService(access_token=token)
    return {"success": True, "data": await svc.fetch_story_insights(story_id)}


@router.get("/v2/audience")
async def get_audience_v2(brand=Depends(require_brand)) -> dict[str, Any]:
    """Lifetime audience demographics — gender/age, top cities/countries, online_followers."""
    ig_user_id, _, token = _resolve_ig_session_for_brand(brand.id)
    svc = InstagramInsightsService(access_token=token)
    raw = await svc.fetch_audience_demographics(ig_user_id)
    return {"success": True, "data": svc._format_demographics(raw)}
