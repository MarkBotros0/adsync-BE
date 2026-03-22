from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends

from app.services.auth import FacebookAuthService
from app.services.session_storage import StateStorage
from app.repositories.facebook_session import FacebookSessionRepository
from app.database import get_session_local
from app.config import get_settings
from app.dependencies import require_brand, optional_brand_id

router = APIRouter(prefix="/facebook/auth", tags=["Facebook Auth"])

settings = get_settings()

# OAuth state tokens — in-memory only (short-lived CSRF protection)
state_store = StateStorage()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_session_repo() -> FacebookSessionRepository:
    db = get_session_local()()
    return FacebookSessionRepository(db)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/login")
async def facebook_login(brand_id: int | None = Depends(optional_brand_id)):
    """Initiate Facebook OAuth. Accepts optional brand JWT to link the session."""
    if not settings.facebook_app_id or not settings.facebook_app_secret:
        raise HTTPException(
            status_code=500,
            detail="Facebook app credentials not configured",
        )

    auth_service = FacebookAuthService()
    login_data = auth_service.get_login_url()
    state_store.set(login_data["state"], brand_id=brand_id)

    return {
        "login_url": login_data["login_url"],
        "message": "Please visit the login_url to authenticate with Facebook",
    }


@router.get("/callback")
async def facebook_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """Handle Facebook OAuth callback."""
    if error:
        raise HTTPException(status_code=400, detail=f"Facebook authorization error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    if not state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    valid, brand_id = state_store.verify_and_delete(state)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    try:
        auth_service = FacebookAuthService()

        token_data = await auth_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")

        long_lived = await auth_service.get_long_lived_token(access_token)
        final_token = long_lived.get("access_token", access_token)
        expires_in = int(long_lived.get("expires_in") or 86400)

        user_info = await auth_service.get_user_info(final_token)
        user_id = user_info.get("id")
        user_name = user_info.get("name")

        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        session_id = f"fb_session_{user_id}"

        repo = _get_session_repo()
        try:
            existing = repo.get_by_session_id(session_id)
            if existing:
                existing.access_token = final_token
                existing.user_name = user_name
                existing.expires_at = expires_at
                if brand_id is not None:
                    existing.brand_id = brand_id
                repo.update(existing)
            else:
                repo.create_session(
                    session_id=session_id,
                    user_id=user_id,
                    user_name=user_name,
                    access_token=final_token,
                    expires_at=expires_at,
                    brand_id=brand_id,
                )
        finally:
            repo.db.close()

        return {
            "success": True,
            "session_id": session_id,
            "user_id": user_id,
            "user_name": user_name,
            "brand_id": brand_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.get("/session")
async def get_brand_facebook_session(brand=Depends(require_brand)):
    """Return the Facebook session linked to the authenticated brand."""
    repo = _get_session_repo()
    try:
        session = repo.get_by_brand_id(brand.id)
        if not session:
            return {"connected": False, "session_id": None, "user_name": None}
        return {
            "connected": True,
            "session_id": session.session_id,
            "user_name": session.user_name,
            "user_id": session.user_id,
        }
    finally:
        repo.db.close()


@router.delete("/disconnect")
async def disconnect_facebook(brand=Depends(require_brand)):
    """Disconnect the Facebook account linked to the authenticated brand."""
    repo = _get_session_repo()
    try:
        session = repo.get_by_brand_id(brand.id)
        if not session:
            return {"success": True, "message": "No Facebook session was connected"}
        repo.delete_session(session.session_id)
        return {"success": True, "message": "Facebook account disconnected"}
    finally:
        repo.db.close()
