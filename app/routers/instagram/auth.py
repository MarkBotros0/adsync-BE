from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends

from app.services.instagram.auth import InstagramAuthService
from app.services.session_storage import StateStorage
from app.repositories.instagram_session import InstagramSessionRepository
from app.database import get_session_local
from app.config import get_settings
from app.dependencies import require_brand, optional_brand_id

router = APIRouter(prefix="/instagram/auth", tags=["Instagram Auth"])

settings = get_settings()

state_store = StateStorage()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_session_repo() -> InstagramSessionRepository:
    db = get_session_local()()
    return InstagramSessionRepository(db)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/connect")
async def instagram_connect(brand_id: int | None = Depends(optional_brand_id)):
    """Initiate Instagram Business Login to connect an Instagram account."""
    if not settings.instagram_app_id or not settings.instagram_app_secret:
        raise HTTPException(
            status_code=500,
            detail="Instagram app credentials not configured",
        )

    svc = InstagramAuthService()
    login_data = svc.get_login_url()
    state_store.set(login_data["state"], brand_id=brand_id)

    return {
        "login_url": login_data["login_url"],
        "message": "Visit login_url to connect your Instagram account",
    }


@router.get("/callback")
async def instagram_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """Handle Instagram OAuth callback and store the session."""
    if error:
        raise HTTPException(status_code=400, detail=f"Instagram authorization error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    if not state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    valid, brand_id = state_store.verify_and_delete(state)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    try:
        svc = InstagramAuthService()

        token_data = await svc.exchange_code_for_token(code)
        short_lived_token = token_data.get("access_token")

        long_lived = await svc.get_long_lived_token(short_lived_token)
        final_token = long_lived.get("access_token", short_lived_token)
        expires_in = int(long_lived.get("expires_in") or 5184000)  # 60 days default

        user_info = await svc.get_user_info(final_token)
        ig_user_id = user_info.get("user_id") or user_info.get("id")
        username = user_info.get("username", "")

        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        session_id = f"ig_session_{ig_user_id}"

        repo = _get_session_repo()
        try:
            existing = repo.get_by_session_id(session_id)
            if existing:
                existing.access_token = final_token
                existing.username = username
                existing.expires_at = expires_at
                if brand_id is not None:
                    existing.brand_id = brand_id
                repo.update(existing)
            else:
                repo.create_session(
                    session_id=session_id,
                    ig_user_id=ig_user_id,
                    username=username,
                    access_token=final_token,
                    expires_at=expires_at,
                    brand_id=brand_id,
                )
        finally:
            repo.db.close()

        return {
            "success": True,
            "session_id": session_id,
            "ig_user_id": ig_user_id,
            "username": username,
            "brand_id": brand_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")


@router.get("/session")
async def get_instagram_session(brand=Depends(require_brand)):
    """Return the Instagram session connected to the authenticated brand."""
    repo = _get_session_repo()
    try:
        session = repo.get_by_brand_id(brand.id)
        if not session:
            return {"connected": False, "session_id": None, "username": None}
        return {
            "connected": True,
            "session_id": session.session_id,
            "ig_user_id": session.ig_user_id,
            "username": session.username,
        }
    finally:
        repo.db.close()


@router.delete("/disconnect")
async def disconnect_instagram(brand=Depends(require_brand)):
    """Disconnect the Instagram account linked to the authenticated brand."""
    repo = _get_session_repo()
    try:
        session = repo.get_by_brand_id(brand.id)
        if not session:
            return {"success": True, "message": "No Instagram account was connected"}
        repo.delete_session(session.session_id)
        return {"success": True, "message": "Instagram account disconnected"}
    finally:
        repo.db.close()
