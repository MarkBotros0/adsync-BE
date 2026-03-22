"""Instagram account and profile endpoints."""
from fastapi import APIRouter, HTTPException

from app.services.instagram.account import InstagramAccountService
from app.routers.instagram.session import get_instagram_session

router = APIRouter(prefix="/instagram", tags=["Instagram"])


@router.get("/account")
async def get_instagram_account(session_id: str):
    """Get the connected Instagram account profile (session_id only)."""
    session = get_instagram_session(session_id)
    ig_user_id = session["ig_user_id"]

    svc = InstagramAccountService(access_token=session["access_token"])
    try:
        profile = await svc.fetch_profile(ig_user_id)
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "ig_user_id": ig_user_id,
                "username": session["username"],
                "profile": profile,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch account: {str(e)}")


@router.get("/accounts/{ig_user_id}/profile")
async def get_instagram_profile(ig_user_id: str, session_id: str):
    """Get the full profile for a specific Instagram account."""
    session = get_instagram_session(session_id)

    svc = InstagramAccountService(access_token=session["access_token"])
    try:
        profile = await svc.fetch_profile(ig_user_id)
        return {"success": True, "data": profile}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch profile: {str(e)}")
