from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends

from app.services.tiktok.auth import TikTokAuthService
from app.services.session_storage import StateStorage
from app.repositories.tiktok_session import TikTokSessionRepository
from app.database import get_session_local
from app.config import get_settings
from app.dependencies import require_brand, optional_brand_id

router = APIRouter(prefix="/tiktok/auth", tags=["TikTok Auth"])

settings = get_settings()

state_store = StateStorage()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_session_repo() -> TikTokSessionRepository:
    db = get_session_local()()
    return TikTokSessionRepository(db)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/connect")
async def tiktok_connect(brand_id: int | None = Depends(optional_brand_id)):
    """Initiate TikTok Login Kit OAuth to connect a TikTok account."""
    if not settings.tiktok_client_key or not settings.tiktok_client_secret:
        raise HTTPException(
            status_code=500,
            detail="TikTok app credentials not configured",
        )

    svc = TikTokAuthService()
    login_data = svc.get_login_url()
    state_store.set(login_data["state"], brand_id=brand_id, code_verifier=login_data["code_verifier"])

    return {
        "login_url": login_data["login_url"],
        "message": "Visit login_url to connect your TikTok account",
    }


@router.get("/callback")
async def tiktok_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
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

    valid, brand_id, code_verifier = state_store.verify_and_delete_pkce(state)
    if not valid or not code_verifier:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    try:
        svc = TikTokAuthService()

        # Exchange code for access + refresh tokens (PKCE required)
        token_data = await svc.exchange_code_for_token(code, code_verifier)
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
async def get_tiktok_session(brand=Depends(require_brand)):
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
async def disconnect_tiktok(brand=Depends(require_brand)):
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
