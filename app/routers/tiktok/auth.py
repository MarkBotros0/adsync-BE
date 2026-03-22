from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.services.tiktok.auth import TikTokAuthService
from app.services.session_storage import StateStorage
from app.services.jwt_auth import decode_token
from app.repositories.brand import BrandRepository
from app.repositories.tiktok_session import TikTokSessionRepository
from app.database import get_session_local
from app.config import get_settings

router = APIRouter(prefix="/tiktok/auth", tags=["TikTok Auth"])

settings = get_settings()

state_store = StateStorage()

_bearer = HTTPBearer(auto_error=False)
_bearer_required = HTTPBearer()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_session_repo() -> TikTokSessionRepository:
    db = get_session_local()()
    return TikTokSessionRepository(db)


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
async def tiktok_connect(brand_id: Optional[int] = Depends(_optional_brand_id)):
    """Initiate TikTok Login Kit OAuth to connect a TikTok account."""
    if not settings.tiktok_client_key or not settings.tiktok_client_secret:
        raise HTTPException(
            status_code=500,
            detail="TikTok app credentials not configured",
        )

    svc = TikTokAuthService()
    login_data = svc.get_login_url()
    state_store.set(login_data["state"], brand_id=brand_id)

    return {
        "login_url": login_data["login_url"],
        "message": "Visit login_url to connect your TikTok account",
    }


@router.get("/callback")
async def tiktok_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """Handle TikTok OAuth callback and store the session."""
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"TikTok authorization error: {error_description or error}",
        )
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    if not state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    valid, brand_id = state_store.verify_and_delete(state)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    try:
        svc = TikTokAuthService()

        # Exchange code for access + refresh tokens
        token_data = await svc.exchange_code_for_token(code)
        access_token = token_data["access_token"]
        open_id = token_data["open_id"]
        refresh_token = token_data["refresh_token"]
        expires_in = int(token_data.get("expires_in", 86400))           # 24h default
        refresh_expires_in = int(token_data.get("refresh_expires_in", 31536000))  # 365d default

        # Fetch user profile
        from app.services.tiktok.videos import TikTokVideoService
        video_svc = TikTokVideoService(access_token=access_token)
        user_info = await video_svc.fetch_user_info()
        display_name = user_info.get("display_name", "")

        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        refresh_expires_at = datetime.utcnow() + timedelta(seconds=refresh_expires_in)
        session_id = f"tt_session_{open_id}"

        repo = _get_session_repo()
        try:
            existing = repo.get_by_session_id(session_id)
            if existing:
                existing.access_token = access_token
                existing.refresh_token = refresh_token
                existing.display_name = display_name
                existing.expires_at = expires_at
                existing.refresh_expires_at = refresh_expires_at
                if brand_id is not None:
                    existing.brand_id = brand_id
                repo.update(existing)
            else:
                repo.create_session(
                    session_id=session_id,
                    open_id=open_id,
                    display_name=display_name,
                    access_token=access_token,
                    expires_at=expires_at,
                    refresh_token=refresh_token,
                    refresh_expires_at=refresh_expires_at,
                    brand_id=brand_id,
                )
        finally:
            repo.db.close()

        return {
            "success": True,
            "session_id": session_id,
            "open_id": open_id,
            "display_name": display_name,
            "brand_id": brand_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")


@router.get("/refresh")
async def tiktok_refresh_token(session_id: str):
    """Refresh the TikTok access token using the stored refresh token."""
    repo = _get_session_repo()
    try:
        session = repo.get_by_session_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.refresh_expires_at.replace(tzinfo=None) < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Refresh token expired — please reconnect TikTok")

        svc = TikTokAuthService()
        token_data = await svc.refresh_access_token(session.refresh_token)

        expires_in = int(token_data.get("expires_in", 86400))
        refresh_expires_in = int(token_data.get("refresh_expires_in", 31536000))

        session.access_token = token_data["access_token"]
        session.refresh_token = token_data["refresh_token"]
        session.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        session.refresh_expires_at = datetime.utcnow() + timedelta(seconds=refresh_expires_in)
        repo.update(session)

        return {
            "success": True,
            "session_id": session_id,
            "expires_at": session.expires_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token refresh failed: {str(e)}")
    finally:
        repo.db.close()


@router.get("/session")
async def get_tiktok_session(brand=Depends(_require_brand)):
    """Return the TikTok session connected to the authenticated brand."""
    repo = _get_session_repo()
    try:
        session = repo.get_by_brand_id(brand.id)
        if not session:
            return {"connected": False, "session_id": None, "display_name": None}
        return {
            "connected": True,
            "session_id": session.session_id,
            "open_id": session.open_id,
            "display_name": session.display_name,
        }
    finally:
        repo.db.close()


@router.delete("/disconnect")
async def disconnect_tiktok(brand=Depends(_require_brand)):
    """Disconnect the TikTok account linked to the authenticated brand."""
    repo = _get_session_repo()
    try:
        session = repo.get_by_brand_id(brand.id)
        if not session:
            return {"success": True, "message": "No TikTok account was connected"}

        # Revoke access token at TikTok
        try:
            svc = TikTokAuthService()
            await svc.revoke_token(session.access_token)
        except Exception:
            pass  # Revocation is best-effort; proceed to delete the local session

        repo.delete_session(session.session_id)
        return {"success": True, "message": "TikTok account disconnected"}
    finally:
        repo.db.close()
