"""Instagram media, stories, reels, and tagged-media endpoints."""
from fastapi import APIRouter, HTTPException

from app.services.instagram.media import InstagramMediaService
from app.routers.instagram.session import get_instagram_session

router = APIRouter(prefix="/instagram", tags=["Instagram"])

_MAX_LIMIT = 100


# ─── Session-based endpoints (ig_user_id resolved from session) ───────────────

@router.get("/account/media")
async def get_instagram_account_media(
    session_id: str,
    limit: int = 25,
    since: str | None = None,
    until: str | None = None,
    after: str | None = None,
):
    """Get feed media for the connected Instagram account.

    Pagination: use `after` (from `paging.cursors.after`) for the next page.
    Use `since` / `until` (Unix timestamps) for time-range filtering.
    """
    limit = min(limit, _MAX_LIMIT)
    session = get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_media(
            session["ig_user_id"], limit=limit, since=since, until=until, after=after
        )
        formatted = svc.format_media_list(raw)
        return {
            "success": True,
            "data": {
                "ig_user_id": session["ig_user_id"],
                "username": session["username"],
                **formatted,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media: {str(e)}")


@router.get("/account/stories")
async def get_instagram_account_stories(session_id: str):
    """Get currently active stories for the connected Instagram account."""
    session = get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_stories(session["ig_user_id"])
        stories = raw.get("data", [])
        return {
            "success": True,
            "data": {
                "ig_user_id": session["ig_user_id"],
                "username": session["username"],
                "total": len(stories),
                "stories": stories,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch stories: {str(e)}")


@router.get("/account/reels")
async def get_instagram_account_reels(
    session_id: str,
    limit: int = 25,
    since: str | None = None,
    until: str | None = None,
    after: str | None = None,
):
    """Get Reels for the connected Instagram account (no feed images or stories).

    Pagination: use `after` (from `paging.cursors.after`) for the next page.
    """
    limit = min(limit, _MAX_LIMIT)
    session = get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_reels(
            session["ig_user_id"], limit=limit, since=since, until=until, after=after
        )
        formatted = svc.format_media_list(raw)
        return {
            "success": True,
            "data": {
                "ig_user_id": session["ig_user_id"],
                "username": session["username"],
                **formatted,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch reels: {str(e)}")


@router.get("/account/tags")
async def get_instagram_account_tagged_media(
    session_id: str,
    limit: int = 25,
    after: str | None = None,
):
    """Get media where the connected account has been tagged by other users.

    Requires instagram_business_manage_comments permission.
    """
    limit = min(limit, _MAX_LIMIT)
    session = get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_tagged_media(session["ig_user_id"], limit=limit, after=after)
        formatted = svc.format_media_list(raw)
        return {
            "success": True,
            "data": {
                "ig_user_id": session["ig_user_id"],
                "username": session["username"],
                **formatted,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch tagged media: {str(e)}")


# ─── Per-account endpoints (explicit ig_user_id) ──────────────────────────────

@router.get("/accounts/{ig_user_id}/media")
async def get_instagram_media(
    ig_user_id: str,
    session_id: str,
    limit: int = 25,
    since: str | None = None,
    until: str | None = None,
    after: str | None = None,
):
    """Get feed media for a specific Instagram account.

    Pagination: use `after` (from `paging.cursors.after`) for the next page.
    """
    limit = min(limit, _MAX_LIMIT)
    session = get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_media(ig_user_id, limit=limit, since=since, until=until, after=after)
        return {"success": True, "data": svc.format_media_list(raw)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media: {str(e)}")


@router.get("/accounts/{ig_user_id}/stories")
async def get_instagram_stories(ig_user_id: str, session_id: str):
    """Get currently active stories (24-hour window only)."""
    session = get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_stories(ig_user_id)
        stories = raw.get("data", [])
        return {"success": True, "data": {"total": len(stories), "stories": stories}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch stories: {str(e)}")


@router.get("/accounts/{ig_user_id}/reels")
async def get_instagram_reels(
    ig_user_id: str,
    session_id: str,
    limit: int = 25,
    since: str | None = None,
    until: str | None = None,
    after: str | None = None,
):
    """Get Reels for a specific Instagram account using the dedicated /reels edge.

    Pagination: use `after` (from `paging.cursors.after`) for the next page.
    """
    limit = min(limit, _MAX_LIMIT)
    session = get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_reels(ig_user_id, limit=limit, since=since, until=until, after=after)
        return {"success": True, "data": svc.format_media_list(raw)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch reels: {str(e)}")


@router.get("/accounts/{ig_user_id}/tags")
async def get_tagged_media(
    ig_user_id: str,
    session_id: str,
    limit: int = 25,
    after: str | None = None,
):
    """Get IG Media where the account has been tagged by other users.

    Requires instagram_business_manage_comments permission.
    """
    limit = min(limit, _MAX_LIMIT)
    session = get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        raw = await svc.fetch_tagged_media(ig_user_id, limit=limit, after=after)
        return {"success": True, "data": svc.format_media_list(raw)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch tagged media: {str(e)}")


# ─── Per-media-object endpoints ────────────────────────────────────────────────

@router.get("/media/{media_id}")
async def get_single_media(media_id: str, session_id: str):
    """Get metadata for a single IG Media object."""
    session = get_instagram_session(session_id)

    svc = InstagramMediaService(access_token=session["access_token"])
    try:
        media = await svc.fetch_single_media(media_id)
        return {"success": True, "data": media}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media: {str(e)}")


@router.get("/media/{media_id}/comments")
async def get_media_comments(media_id: str, session_id: str, limit: int = 50):
    """Get top-level comments on an IG Media object (max 50 per request)."""
    session = get_instagram_session(session_id)

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
    session = get_instagram_session(session_id)

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
