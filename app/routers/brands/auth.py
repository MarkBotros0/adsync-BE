"""Brand + user authentication routes.

Endpoints:
  POST /brands/register           – create a brand + first SUPER user
  POST /brands/login              – login, returns JWT
  GET  /brands/me                 – get current user + brand
  GET  /brands/validate           – lightweight polling endpoint
  POST /brands/send-verification  – re-send OTP
  POST /brands/verify-email       – verify email with OTP
  POST /brands/logout             – soft logout
  POST /brands/force-signout      – rotate session_key, invalidate all JWTs
  POST /brands/invite             – invite a user by email (SUPER or ADMIN)
  GET  /brands/invite/verify      – verify an invitation token (public)
  POST /brands/invite/accept      – accept invitation, set password, create account (public)
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from app.services.jwt_auth import hash_password, verify_password, create_access_token
from app.repositories.brand import BrandRepository
from app.repositories.user import UserRepository
from app.repositories.invitation import InvitationRepository
from app.models.user import UserRole
from app.database import get_session_local
from app.services.email import send_verification_email, generate_verification_code, send_invitation_email
from app.dependencies import require_user, require_admin_or_super
from app.config import get_settings
from datetime import datetime, timedelta

router = APIRouter(prefix="/brands", tags=["Brand Auth"])
settings = get_settings()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _get_user_repo() -> UserRepository:
    db = get_session_local()()
    return UserRepository(db)


def _get_brand_repo() -> BrandRepository:
    db = get_session_local()()
    return BrandRepository(db)


def _get_invite_repo() -> InvitationRepository:
    db = get_session_local()()
    return InvitationRepository(db)


def _role_value(user) -> str:
    return user.role.value if isinstance(user.role, UserRole) else user.role


def _user_dict(user, brand) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": _role_value(user),
        "brand_id": brand.id,
        "brand": brand.to_dict(),
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class InviteRequest(BaseModel):
    email: EmailStr
    brand_id: int
    role: str = "NORMAL"


class AcceptInviteRequest(BaseModel):
    token: str
    name: str
    password: str


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    """Register a new brand and its first SUPER user.

    The provided name is used for both the user and as the brand's initial name
    (the brand can be renamed later).
    """
    brand_repo = _get_brand_repo()
    user_repo = _get_user_repo()

    try:
        if user_repo.get_by_email(body.email):
            raise HTTPException(status_code=409, detail="Email already registered")

        # Create brand — name defaults to the registrant's name
        brand = brand_repo.create_brand(name=body.name)
        _ = brand.subscription  # eager-load while session is open

        # Create SUPER user linked to the brand
        code = generate_verification_code()
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        user = user_repo.create_user(
            email=body.email,
            hashed_password=hash_password(body.password),
            name=body.name,
            brand_id=brand.id,
            role=UserRole.SUPER,
        )
        user_repo.set_verification_code(user, code, expires_at)

        await send_verification_email(body.email, code, type="signup")

        token = create_access_token(
            user_id=user.id,
            brand_id=brand.id,
            session_key=user.session_key,
            role=_role_value(user),
        )

        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "user": _user_dict(user, brand),
            "email_verified": False,
        }
    finally:
        brand_repo.db.close()
        user_repo.db.close()


@router.post("/login", status_code=200)
async def login(body: LoginRequest):
    """Authenticate a user and issue a JWT."""
    from app.config import get_settings
    
    settings = get_settings()
    
    # Check if this is the super user login
    super_email = settings.super_user_email
    super_password = settings.super_user_password
    
    if super_email and body.email == super_email:
        # Validate super user password
        if body.password != super_password:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Super user doesn't exist in database, create virtual user response
        from jose import jwt
        
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_access_token_expire_hours)
        payload = {
            "sub": "0",
            "brand_id": "0",
            "session_key": "super-session",
            "role": UserRole.SUPER.value,
            "email": super_email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "user_access",
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": 0,
                "email": super_email,
                "name": "Super Admin",
                "role": UserRole.SUPER.value,
                "brand_id": 0,
                "brand": None,
                "is_active": True,
                "is_email_verified": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
        }
    
    # Regular user authentication
    repo = _get_user_repo()
    try:
        user = repo.get_by_email(body.email)
        if not user or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is deactivated")

        brand = user.brand
        if not brand or not brand.is_active:
            raise HTTPException(status_code=403, detail="Brand account is deactivated")
        _ = brand.subscription

        token = create_access_token(
            user_id=user.id,
            brand_id=user.brand_id,
            session_key=user.session_key,
            role=_role_value(user),
        )

        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "user": user.to_dict(),
        }
    finally:
        repo.db.close()


@router.get("/me")
async def get_me(user=Depends(require_user)):
    return {"success": True, "user": user.to_dict()}


@router.get("/validate")
async def validate_session(user=Depends(require_user)):
    brand = user.brand
    return {
        "valid": True,
        "user_id": user.id,
        "brand_id": user.brand_id,
        "brand_name": brand.name if brand else None,
        "subscription": brand.subscription.name if brand and brand.subscription else "free",
        "role": _role_value(user),
    }


@router.post("/send-verification", status_code=200)
async def send_verification(user=Depends(require_user)):
    if user.is_email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    code = generate_verification_code()
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    repo = _get_user_repo()
    try:
        fresh_user = repo.get_by_id(user.id)
        repo.set_verification_code(fresh_user, code, expires_at)
    finally:
        repo.db.close()

    await send_verification_email(user.email, code, type="signup")
    return {"success": True, "message": "Verification code sent"}


@router.post("/verify-email", status_code=200)
async def verify_email(body: VerifyEmailRequest):
    repo = _get_user_repo()
    try:
        user = repo.get_by_email(body.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_email_verified:
            return {"success": True, "message": "Email already verified"}

        if (
            user.email_verification_code != body.code
            or user.email_verification_expires_at is None
            or datetime.utcnow() > user.email_verification_expires_at
        ):
            raise HTTPException(status_code=400, detail="Invalid or expired verification code")

        repo.mark_email_verified(user)
        return {"success": True, "message": "Email verified successfully"}
    finally:
        repo.db.close()


@router.post("/logout", status_code=200)
async def logout(user=Depends(require_user)):
    return {"success": True, "message": "Logged out successfully"}


@router.post("/force-signout", status_code=200)
async def force_signout(user=Depends(require_user)):
    repo = _get_user_repo()
    try:
        fresh_user = repo.get_by_id(user.id)
        if not fresh_user:
            raise HTTPException(status_code=404, detail="User not found")
        updated = repo.rotate_session_key(fresh_user)
        new_token = create_access_token(
            user_id=updated.id,
            brand_id=updated.brand_id,
            session_key=updated.session_key,
            role=_role_value(updated),
        )
        return {
            "success": True,
            "message": "All other sessions have been invalidated",
            "access_token": new_token,
            "token_type": "bearer",
        }
    finally:
        repo.db.close()


# ── Invitation endpoints ──────────────────────────────────────────────────────

@router.post("/invite", status_code=201)
async def invite_user(body: InviteRequest, current_user=Depends(require_admin_or_super)):
    """Invite a user by email.

    - SUPER: can invite to any brand with NORMAL, ADMIN, or SUPER roles.
    - ADMIN: can only invite to their own brand with NORMAL or ADMIN roles.
    """
    current_role = _role_value(current_user)

    # ADMIN can only invite to their own brand
    if current_role == UserRole.ADMIN.value and body.brand_id != current_user.brand_id:
        raise HTTPException(status_code=403, detail="Admins can only invite users to their own brand")

    # ADMIN cannot create SUPER users
    if current_role == UserRole.ADMIN.value and body.role == UserRole.SUPER.value:
        raise HTTPException(status_code=403, detail="Admins cannot assign the SUPER role")

    if body.role not in (UserRole.SUPER.value, UserRole.ADMIN.value, UserRole.NORMAL.value):
        raise HTTPException(status_code=422, detail="Invalid role")

    # Verify brand exists
    brand_repo = _get_brand_repo()
    try:
        brand = brand_repo.get_by_id(body.brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        brand_name = brand.name
    finally:
        brand_repo.db.close()

    # Check the email isn't already a registered user
    user_repo = _get_user_repo()
    try:
        if user_repo.get_by_email(body.email):
            raise HTTPException(status_code=409, detail="A user with this email already exists")
    finally:
        user_repo.db.close()

    invite_repo = _get_invite_repo()
    try:
        invitation = invite_repo.create_invitation(
            email=body.email,
            brand_id=body.brand_id,
            role=body.role,
            invited_by_user_id=current_user.id,
        )
        invite_url = f"{settings.app_url}/invite?token={invitation.token}"
    finally:
        invite_repo.db.close()

    await send_invitation_email(
        email=body.email,
        invite_url=invite_url,
        brand_name=brand_name,
        inviter_name=current_user.name,
    )

    return {
        "success": True,
        "message": f"Invitation sent to {body.email}",
        "invitation": invitation.to_dict(),
    }


@router.get("/invite/verify")
async def verify_invitation(token: str):
    """Verify an invitation token is valid and return its details.

    Used by the frontend to pre-fill the accept form.
    """
    repo = _get_invite_repo()
    try:
        invitation = repo.get_by_token(token)
        if not invitation or not invitation.is_valid():
            raise HTTPException(status_code=410, detail="Invitation link is invalid or has expired")

        _ = invitation.brand  # eager-load

        return {
            "valid": True,
            "email": invitation.email,
            "brand_id": invitation.brand_id,
            "brand_name": invitation.brand.name if invitation.brand else None,
            "role": invitation.role,
            "expires_at": invitation.expires_at.isoformat(),
        }
    finally:
        repo.db.close()


@router.post("/invite/accept", status_code=201)
async def accept_invitation(body: AcceptInviteRequest):
    """Accept an invitation: create a user account and return a JWT.

    No auth required — the invitation token is the credential.
    """
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    invite_repo = _get_invite_repo()
    user_repo = _get_user_repo()
    brand_repo = _get_brand_repo()

    try:
        invitation = invite_repo.get_by_token(body.token)
        if not invitation or not invitation.is_valid():
            raise HTTPException(status_code=410, detail="Invitation link is invalid or has expired")

        if user_repo.get_by_email(invitation.email):
            raise HTTPException(status_code=409, detail="An account with this email already exists")

        brand = brand_repo.get_by_id(invitation.brand_id)
        if not brand or not brand.is_active:
            raise HTTPException(status_code=404, detail="Brand not found")
        _ = brand.subscription

        # Create user
        user = user_repo.create_user(
            email=invitation.email,
            hashed_password=hash_password(body.password),
            name=body.name,
            brand_id=invitation.brand_id,
            role=UserRole(invitation.role),
        )
        user.is_email_verified = True  # email was verified via invitation link
        user_repo.db.commit()

        # Mark invitation as accepted
        invite_repo.mark_accepted(invitation)

        token = create_access_token(
            user_id=user.id,
            brand_id=brand.id,
            session_key=user.session_key,
            role=_role_value(user),
        )

        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "user": _user_dict(user, brand),
        }
    finally:
        invite_repo.db.close()
        user_repo.db.close()
        brand_repo.db.close()
