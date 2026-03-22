from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.services.tiktok.videos import TikTokVideoService
from app.repositories.tiktok_session import TikTokSessionRepository
from app.database import get_session_local

router = APIRouter(prefix="/tiktok", tags=["TikTok"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_tiktok_session(session_id: str) -> dict:
    """Look up a valid TikTok session by ID, or raise 401.

    TikTok access tokens expire every 24h but the refresh token lasts 365d.
    We check the refresh_expires_at so that the session stays valid as long as
    the client can call /tiktok/auth/refresh to obtain a new access token.
    """
    db = get_session_local()()
    try:
        repo = TikTokSessionRepository(db)
        session = repo.get_by_session_id(session_id)
        if not session or session.refresh_expires_at.replace(tzinfo=None) < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Invalid or expired TikTok session")
        return {
            "open_id": session.open_id,
            "display_name": session.display_name,
            "access_token": session.access_token,
            "access_token_expired": session.expires_at.replace(tzinfo=None) < datetime.utcnow(),
        }
    finally:
        db.close()


# ─── Account endpoints ────────────────────────────────────────────────────────

@router.get("/account")
async def get_tiktok_account(session_id: str):
    """
    Get the connected TikTok account profile.
    Mirrors GET /instagram/account — only session_id needed.
    """
    session = _get_tiktok_session(session_id)

    svc = TikTokVideoService(access_token=session["access_token"])
    try:
        user_info = await svc.fetch_user_info()
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "open_id": session["open_id"],
                "display_name": session["display_name"],
                "profile": user_info,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch account: {str(e)}")


@router.get("/account/videos")
async def get_tiktok_account_videos(
    session_id: str,
    max_count: int = 20,
    cursor: int | None = None,
):
    """
    Get the connected TikTok account's public videos (newest first).
    Mirrors GET /instagram/account/media — only session_id needed.

    Pagination:
    - Use `cursor` (from `paging.cursor`) for the next page when `paging.has_more` is true.
    - `cursor` is a UTC Unix timestamp in milliseconds.
    """
    if max_count > 20:
        max_count = 20
    session = _get_tiktok_session(session_id)

    svc = TikTokVideoService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_videos(max_count=max_count, cursor=cursor)
        formatted = svc.format_video_list(raw)
        return {
            "success": True,
            "data": {
                "open_id": session["open_id"],
                "display_name": session["display_name"],
                **formatted,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch videos: {str(e)}")


# ─── Per-account endpoints (by explicit open_id) ──────────────────────────────

@router.get("/accounts/{open_id}/videos")
async def get_tiktok_videos(
    open_id: str,
    session_id: str,
    max_count: int = 20,
    cursor: int | None = None,
):
    """
    Get public videos for a specific TikTok account.
    Mirrors GET /instagram/accounts/{ig_user_id}/media.

    Pagination:
    - Use `cursor` (from `paging.cursor`) for the next page when `paging.has_more` is true.
    """
    if max_count > 20:
        max_count = 20
    session = _get_tiktok_session(session_id)

    svc = TikTokVideoService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_videos(max_count=max_count, cursor=cursor)
        return {"success": True, "data": svc.format_video_list(raw)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch videos: {str(e)}")


# ─── Per-video endpoints ──────────────────────────────────────────────────────

@router.get("/videos/query")
async def query_tiktok_videos(session_id: str, video_ids: str):
    """
    Fetch specific TikTok videos by ID (max 20 per request).
    Mirrors GET /instagram/media/{media_id}.

    Pass `video_ids` as a comma-separated string: `?video_ids=id1,id2,id3`
    """
    ids = [v.strip() for v in video_ids.split(",") if v.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="video_ids must not be empty")
    if len(ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 video IDs per request")

    session = _get_tiktok_session(session_id)

    svc = TikTokVideoService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_videos_by_ids(ids)
        videos = raw.get("videos", [])
        formatted = svc.format_video_list({"videos": videos})
        return {
            "success": True,
            "data": {
                "open_id": session["open_id"],
                "requested_ids": ids,
                **formatted,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to query videos: {str(e)}")
