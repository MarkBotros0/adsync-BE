"""Brand account authentication routes.

Endpoints:
  POST /brands/register        – create a new brand account
  POST /brands/login           – login, returns JWT
  GET  /brands/me              – get current brand (requires valid JWT)
  POST /brands/logout          – soft logout (client should discard token)
  POST /brands/force-signout   – rotate session_key, invalidates ALL JWTs for this brand
  GET  /brands/validate        – lightweight 5-second polling endpoint
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.services.jwt_auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    get_brand_id_from_token,
    get_session_key_from_token,
)
from app.repositories.brand import BrandRepository
from app.repositories.subscription import SubscriptionRepository
from app.database import get_session_local
from app.services.email import send_verification_email, generate_verification_code
from jose import JWTError
from datetime import datetime, timedelta

router = APIRouter(prefix="/brands", tags=["Brand Auth"])
_bearer = HTTPBearer()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _get_brand_repo():
    SessionLocal = get_session_local()
    db = SessionLocal()
    return BrandRepository(db)


def _get_sub_repo():
    SessionLocal = get_session_local()
    db = SessionLocal()
    return SubscriptionRepository(db)


def _require_brand(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    """FastAPI dependency — validates JWT and session_key, returns brand."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    brand_id = int(payload.get("sub", 0))
    token_session_key = payload.get("session_key")

    repo = _get_brand_repo()
    try:
        brand = repo.get_by_id(brand_id)
        if not brand or not brand.is_active:
            raise HTTPException(status_code=401, detail="Brand not found or deactivated")

        if brand.session_key != token_session_key:
            raise HTTPException(status_code=401, detail="Session invalidated — please log in again")

        # Trigger lazy load while the session is still open so that
        # endpoints can safely access brand.subscription after db.close().
        _ = brand.subscription

        return brand
    finally:
        repo.db.close()


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    subscription_name: Optional[str] = "free"
    logo_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    """Register a new brand account."""
    brand_repo = _get_brand_repo()
    sub_repo = _get_sub_repo()

    try:
        if brand_repo.get_by_email(body.email):
            raise HTTPException(status_code=409, detail="Email already registered")

        # Resolve subscription plan
        sub = sub_repo.get_by_name(body.subscription_name or "free")
        if not sub:
            sub = sub_repo.get_by_name("free")

        code = generate_verification_code()
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        brand = brand_repo.create_brand(
            name=body.name,
            email=body.email,
            hashed_password=hash_password(body.password),
            subscription_id=sub.id if sub else None,
            logo_url=body.logo_url,
            website=body.website,
            industry=body.industry,
        )
        brand_repo.set_verification_code(brand, code, expires_at)

        await send_verification_email(body.email, code, type="signup")

        token = create_access_token(brand.id, brand.session_key)

        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "brand": brand.to_dict(),
            "email_verified": False,
        }
    finally:
        brand_repo.db.close()
        sub_repo.db.close()


@router.post("/login")
async def login(body: LoginRequest):
    """Authenticate a brand and issue a JWT."""
    repo = _get_brand_repo()
    try:
        brand = repo.get_by_email(body.email)
        if not brand or not verify_password(body.password, brand.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not brand.is_active:
            raise HTTPException(status_code=403, detail="Brand account is deactivated")

        token = create_access_token(brand.id, brand.session_key)

        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "brand": brand.to_dict(),
        }
    finally:
        repo.db.close()


@router.get("/me")
async def get_me(brand=Depends(_require_brand)):
    """Return the authenticated brand's profile."""
    return {"success": True, "brand": brand.to_dict()}


@router.get("/validate")
async def validate_session(brand=Depends(_require_brand)):
    """Lightweight endpoint called every 5 s by the frontend to keep the session alive.

    Returns minimal data so the payload stays small.
    """
    return {
        "valid": True,
        "brand_id": brand.id,
        "brand_name": brand.name,
        "subscription": brand.subscription.name if brand.subscription else "free",
    }


@router.post("/send-verification")
async def send_verification(brand=Depends(_require_brand)):
    """Re-send a verification code to the authenticated brand's email."""
    if brand.is_email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    code = generate_verification_code()
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    repo = _get_brand_repo()
    try:
        repo.set_verification_code(brand, code, expires_at)
    finally:
        repo.db.close()

    await send_verification_email(brand.email, code, type="signup")
    return {"success": True, "message": "Verification code sent"}


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest):
    """Verify a brand's email using the 6-digit OTP code."""
    repo = _get_brand_repo()
    try:
        brand = repo.get_by_email(body.email)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")

        if brand.is_email_verified:
            return {"success": True, "message": "Email already verified"}

        if (
            brand.email_verification_code != body.code
            or brand.email_verification_expires_at is None
            or datetime.utcnow() > brand.email_verification_expires_at
        ):
            raise HTTPException(status_code=400, detail="Invalid or expired verification code")

        repo.mark_email_verified(brand)
        return {"success": True, "message": "Email verified successfully"}
    finally:
        repo.db.close()


@router.post("/logout")
async def logout(brand=Depends(_require_brand)):
    """Soft logout — instructs the client to discard its token.

    The token technically stays valid until expiry unless force-signout is used.
    """
    return {"success": True, "message": "Logged out successfully"}


@router.post("/force-signout")
async def force_signout(brand=Depends(_require_brand)):
    """Rotate the session key, immediately invalidating ALL previously issued JWTs
    for this brand (including sessions on other devices/browsers).
    """
    repo = _get_brand_repo()
    try:
        updated = repo.rotate_session_key(brand)
        # Issue a fresh token for the current caller so they aren't locked out
        new_token = create_access_token(updated.id, updated.session_key)
        return {
            "success": True,
            "message": "All other sessions have been invalidated",
            "access_token": new_token,
            "token_type": "bearer",
        }
    finally:
        repo.db.close()
