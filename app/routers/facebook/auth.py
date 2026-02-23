from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from typing import Optional
from app.services.auth import FacebookAuthService
from app.services.session_storage import get_session_storage, StateStorage
from app.config import get_settings

router = APIRouter(prefix="/facebook/auth", tags=["Facebook Auth"])

settings = get_settings()
session_store = get_session_storage(settings.session_storage)
state_store = StateStorage(session_store, use_db=(settings.session_storage == "postgresql"))


@router.get("/login")
async def facebook_login():
    """Initiate Facebook OAuth login flow"""
    if not settings.facebook_app_id or not settings.facebook_app_secret:
        raise HTTPException(
            status_code=500,
            detail="Facebook app credentials not configured. Please set FACEBOOK_APP_ID and FACEBOOK_APP_SECRET in .env file"
        )
    
    auth_service = FacebookAuthService()
    login_data = auth_service.get_login_url()
    state_store.set(login_data["state"])
    
    return {
        "login_url": login_data["login_url"],
        "message": "Please visit the login_url to authenticate with Facebook"
    }


@router.get("/callback")
async def facebook_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """Handle Facebook OAuth callback"""
    if error:
        raise HTTPException(status_code=400, detail=f"Facebook authorization error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    
    if not state or not state_store.verify_and_delete(state):
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    try:
        auth_service = FacebookAuthService()
        
        token_data = await auth_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        
        long_lived_token = await auth_service.get_long_lived_token(access_token)
        final_token = long_lived_token.get("access_token", access_token)
        
        user_info = await auth_service.get_user_info(final_token)
        user_id = user_info.get("id")
        
        session_id = f"session_{user_id}"
        session_data = {
            "user_id": user_id,
            "user_name": user_info.get("name"),
            "email": user_info.get("email"),
            "access_token": final_token,
            "token_expires_in": long_lived_token.get("expires_in")
        }
        session_store.set(session_id, session_data, ttl=86400)
        
        # Return session_id as JSON for frontend to handle
        return {
            "success": True,
            "session_id": session_id,
            "user_id": user_id,
            "user_name": user_info.get("name")
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.get("/status/{session_id}")
async def check_auth_status(session_id: str):
    """Check if a session is still valid"""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    auth_service = FacebookAuthService()
    
    try:
        validation = await auth_service.validate_token(session["access_token"])
        token_data = validation.get("data", {})
        
        return {
            "valid": token_data.get("is_valid", False),
            "user_id": session["user_id"],
            "user_name": session["user_name"],
            "expires_at": token_data.get("expires_at"),
            "scopes": token_data.get("scopes", [])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token validation failed: {str(e)}")


@router.post("/logout/{session_id}")
async def logout(session_id: str):
    """Logout and invalidate session"""
    if session_store.exists(session_id):
        session_store.delete(session_id)
        return {"success": True, "message": "Successfully logged out"}
    
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/accounts")
async def get_ad_accounts(session_id: str):
    """Get all ad accounts for the authenticated user"""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    auth_service = FacebookAuthService()
    
    try:
        ad_accounts = await auth_service.get_ad_accounts(
            session["access_token"],
            session["user_id"]
        )
        
        return {
            "user_id": session["user_id"],
            "user_name": session["user_name"],
            "ad_accounts": ad_accounts.get("data", [])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch ad accounts: {str(e)}")

