from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.services.instagram.auth import InstagramAuthService
from app.services.session_storage import StateStorage
from app.services.jwt_auth import decode_token
from app.repositories.brand import BrandRepository
from app.repositories.instagram_session import InstagramSessionRepository
from app.database import get_session_local
from app.config import get_settings

router = APIRouter(prefix="/instagram/auth", tags=["Instagram Auth"])

settings = get_settings()

state_store = StateStorage()

_bearer = HTTPBearer(auto_error=False)
_bearer_required = HTTPBearer()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_session_repo() -> InstagramSessionRepository:
    db = get_session_local()()
    return InstagramSessionRepository(db)


def _require_brand(credentials: HTTPAuthorizationCredentials = Depends(_bearer_required)):
    """Validate brand JWT and return the brand object."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    brand_id = int(payload.get("sub", 0))
    token_session_key = payload.get("session_key")

    db = get_session_local()()
    try:
        repo = BrandRepository(db)
        brand = repo.get_by_id(brand_id)
        if not brand or not brand.is_active:
            raise HTTPException(status_code=401, detail="Brand not found or deactivated")
        if brand.session_key != token_session_key:
            raise HTTPException(status_code=401, detail="Session invalidated — please log in again")
        return brand
    finally:
        db.close()


def _optional_brand_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[int]:
    """Extract brand_id from JWT if present; returns None otherwise."""
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        return int(payload.get("sub", 0)) or None
    except (JWTError, ValueError):
        return None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/connect")
async def instagram_connect(brand_id: Optional[int] = Depends(_optional_brand_id)):
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
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
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
async def get_instagram_session(brand=Depends(_require_brand)):
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
async def disconnect_instagram(brand=Depends(_require_brand)):
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
