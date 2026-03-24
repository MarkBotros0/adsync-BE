"""Brand + user authentication routes.

Endpoints:
  POST /brands/register           – create a brand + first SUPER user
  POST /brands/login              – login; auto-issues JWT for single-brand users,
                                    returns brand list + selection token for multi-brand users
  POST /brands/select-brand       – exchange selection token + brand_id for a scoped JWT
  POST /brands/switch-brand       – re-issue JWT scoped to a different brand (authenticated)
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
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

from app.config import get_settings
from app.database import get_session_local
from app.dependencies import require_user, require_admin_or_super
from app.models.user import UserRole
from app.models.user_brand import BrandMembershipRole
from app.repositories.brand import BrandRepository
from app.repositories.invitation import InvitationRepository
from app.repositories.user import UserRepository
from app.repositories.user_brand import UserBrandRepository
from app.services.email import (
    generate_verification_code,
    send_invitation_email,
    send_verification_email,
)
from app.services.jwt_auth import create_access_token, hash_password, verify_password

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


def _get_user_brand_repo() -> UserBrandRepository:
    db = get_session_local()()
    return UserBrandRepository(db)


def _role_value(user) -> str:
    return user.role.value if isinstance(user.role, UserRole) else user.role


def _membership_role_value(membership) -> str:
    return (
        membership.role.value
        if isinstance(membership.role, BrandMembershipRole)
        else membership.role
    )


def _user_dict(user, brand) -> dict:
    role = _role_value(user)
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": role,
        "brand_id": brand.id if brand else None,
        "brand": brand.to_dict() if brand else None,
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def _create_selection_token(user_id: int, session_key: str) -> str:
    """Issue a short-lived (5-min) token used only for the select-brand step."""
    expire = datetime.utcnow() + timedelta(minutes=5)
    payload = {
        "sub": str(user_id),
        "session_key": session_key,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "brand_selection",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_selection_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "brand_selection":
        raise JWTError("Not a brand selection token")
    return payload


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    subscription_name: str | None = "free"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SelectBrandRequest(BaseModel):
    selection_token: str
    brand_id: int


class SwitchBrandRequest(BaseModel):
    brand_id: int


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
    """Register a new brand and its first SUPER user."""
    from app.repositories.subscription import SubscriptionRepository

    brand_repo = _get_brand_repo()
    user_repo = _get_user_repo()
    ub_repo = _get_user_brand_repo()

    try:
        if user_repo.get_by_email(body.email):
            raise HTTPException(status_code=409, detail="Email already registered")

        # Resolve subscription by name (defaults to free)
        subscription_id: int | None = None
        if body.subscription_name:
            sub_repo = SubscriptionRepository(brand_repo.db)
            subscription = sub_repo.get_by_name(body.subscription_name)
            if subscription:
                subscription_id = subscription.id

        # Create brand — name defaults to the registrant's name
        brand = brand_repo.create_brand(name=body.name, subscription_id=subscription_id)
        _ = brand.subscription  # eager-load while session is open

        # Create SUPER user (global role)
        code = generate_verification_code()
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        user = user_repo.create_user(
            email=body.email,
            hashed_password=hash_password(body.password),
            name=body.name,
            role=UserRole.SUPER,
        )
        user_repo.set_verification_code(user, code, expires_at)

        # Link the SUPER user to the new brand as ADMIN
        ub_repo.create_membership(
            user_id=user.id,
            brand_id=brand.id,
            role=BrandMembershipRole.ADMIN,
        )

        await send_verification_email(body.email, code, type="signup")

        token = create_access_token(
            user_id=user.id,
            brand_id=brand.id,
            session_key=user.session_key,
            role=_role_value(user),
        )

        user.brand = brand
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
        ub_repo.db.close()


@router.post("/login", status_code=200)
async def login(body: LoginRequest):
    """Authenticate a user and issue a JWT.

    - Single-brand users → JWT issued immediately.
    - Multi-brand users  → returns a selection token + brand list; call
      POST /brands/select-brand to get a scoped JWT.
    - Config-level SUPER → JWT issued immediately (unchanged).
    """
    from app.config import get_settings as _gs
    _settings = _gs()

    # Config-level super user (not in DB)
    super_email = _settings.super_user_email
    super_password = _settings.super_user_password

    if super_email and body.email == super_email:
        if body.password != super_password:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        expire = datetime.utcnow() + timedelta(hours=_settings.jwt_access_token_expire_hours)
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
        token = jwt.encode(payload, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)

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
    user_repo = _get_user_repo()
    ub_repo = _get_user_brand_repo()
    try:
        user = user_repo.get_by_email(body.email)
        if not user or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is deactivated")

        memberships = ub_repo.get_brands_for_user(user.id)

        # SUPER users without memberships still get a scoped token (brand_id=0)
        user_role_val = _role_value(user)
        if not memberships and user_role_val != UserRole.SUPER.value:
            raise HTTPException(status_code=403, detail="User has no active brand memberships")

        # Single membership → issue JWT immediately
        if len(memberships) == 1:
            membership = memberships[0]
            brand = membership.brand
            if not brand or not brand.is_active:
                raise HTTPException(status_code=403, detail="Brand account is deactivated")
            _ = brand.subscription if hasattr(brand, "subscription") else None

            effective_role = (
                user_role_val if user_role_val == UserRole.SUPER.value
                else _membership_role_value(membership)
            )

            token = create_access_token(
                user_id=user.id,
                brand_id=brand.id,
                session_key=user.session_key,
                role=effective_role,
            )
            user.brand = brand
            user.role = effective_role  # type: ignore[assignment]
            return {
                "success": True,
                "access_token": token,
                "token_type": "bearer",
                "user": _user_dict(user, brand),
            }

        # Multiple memberships → return brand list + selection token
        selection_token = _create_selection_token(user.id, user.session_key)
        brands = []
        for m in memberships:
            b = m.brand
            if b and b.is_active:
                brands.append({
                    "id": b.id,
                    "name": b.name,
                    "logo_url": b.logo_url if hasattr(b, "logo_url") else None,
                    "role": _membership_role_value(m),
                })

        return {
            "success": True,
            "requires_brand_selection": True,
            "selection_token": selection_token,
            "brands": brands,
        }
    finally:
        user_repo.db.close()
        ub_repo.db.close()


@router.post("/select-brand", status_code=200)
async def select_brand(body: SelectBrandRequest):
    """Exchange a brand selection token + brand_id for a scoped JWT.

    Called after login when a user belongs to multiple brands.
    """
    try:
        payload = _decode_selection_token(body.selection_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired selection token")

    user_id = int(payload.get("sub", 0))
    token_session_key = payload.get("session_key")

    user_repo = _get_user_repo()
    ub_repo = _get_user_brand_repo()
    brand_repo = _get_brand_repo()
    try:
        user = user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or deactivated")
        if user.session_key != token_session_key:
            raise HTTPException(status_code=401, detail="Session invalidated — please log in again")

        brand = brand_repo.get_by_id(body.brand_id)
        if not brand or not brand.is_active:
            raise HTTPException(status_code=404, detail="Brand not found")
        _ = brand.subscription

        user_role_val = _role_value(user)
        if user_role_val != UserRole.SUPER.value:
            membership = ub_repo.get_membership(user_id, body.brand_id)
            if not membership:
                raise HTTPException(status_code=403, detail="You are not a member of this brand")
            effective_role = _membership_role_value(membership)
        else:
            effective_role = UserRole.SUPER.value

        token = create_access_token(
            user_id=user.id,
            brand_id=brand.id,
            session_key=user.session_key,
            role=effective_role,
        )
        user.brand = brand
        user.role = effective_role  # type: ignore[assignment]
        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "user": _user_dict(user, brand),
        }
    finally:
        user_repo.db.close()
        ub_repo.db.close()
        brand_repo.db.close()


@router.post("/switch-brand", status_code=200)
async def switch_brand(body: SwitchBrandRequest, current_user=Depends(require_user)):
    """Re-issue a JWT scoped to a different brand.

    Allows authenticated users to switch brand context. All subsequent requests
    will be filtered to the newly selected brand.
    """
    ub_repo = _get_user_brand_repo()
    brand_repo = _get_brand_repo()
    try:
        brand = brand_repo.get_by_id(body.brand_id)
        if not brand or not brand.is_active:
            raise HTTPException(status_code=404, detail="Brand not found")
        _ = brand.subscription

        user_role_val = _role_value(current_user)
        if user_role_val != UserRole.SUPER.value:
            membership = ub_repo.get_membership(current_user.id, body.brand_id)
            if not membership:
                raise HTTPException(status_code=403, detail="You are not a member of this brand")
            effective_role = _membership_role_value(membership)
        else:
            effective_role = UserRole.SUPER.value

        token = create_access_token(
            user_id=current_user.id,
            brand_id=brand.id,
            session_key=current_user.session_key,
            role=effective_role,
        )
        current_user.brand = brand
        current_user.role = effective_role  # type: ignore[assignment]
        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "user": _user_dict(current_user, brand),
        }
    finally:
        ub_repo.db.close()
        brand_repo.db.close()


@router.get("/me")
async def get_me(user=Depends(require_user)):
    return {"success": True, "user": user.to_dict()}


@router.get("/validate")
async def validate_session(user=Depends(require_user)):
    brand = user.brand
    return {
        "valid": True,
        "user_id": user.id,
        "brand_id": brand.id if brand else None,
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
    brand_repo = _get_brand_repo()
    try:
        fresh_user = repo.get_by_id(user.id)
        if not fresh_user:
            raise HTTPException(status_code=404, detail="User not found")
        updated = repo.rotate_session_key(fresh_user)

        brand = user.brand
        brand_id = brand.id if brand else 0
        new_token = create_access_token(
            user_id=updated.id,
            brand_id=brand_id,
            session_key=updated.session_key,
            role=_role_value(user),
        )
        return {
            "success": True,
            "message": "All other sessions have been invalidated",
            "access_token": new_token,
            "token_type": "bearer",
        }
    finally:
        repo.db.close()
        brand_repo.db.close()


# ── Invitation endpoints ──────────────────────────────────────────────────────

@router.post("/invite", status_code=201)
async def invite_user(body: InviteRequest, current_user=Depends(require_admin_or_super)):
    """Invite a user by email.

    - SUPER: can invite to any brand with NORMAL, ADMIN, or SUPER roles.
    - ADMIN: can only invite to their own brand with NORMAL or ADMIN roles.
    """
    current_role = _role_value(current_user)

    # ADMIN can only invite to their own brand
    current_brand = current_user.brand
    if current_role == UserRole.ADMIN.value and body.brand_id != (current_brand.id if current_brand else None):
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
        existing_user = user_repo.get_by_email(body.email)
        if existing_user:
            # If user exists, check if they already have a membership in this brand
            ub_repo = _get_user_brand_repo()
            try:
                if ub_repo.get_membership(existing_user.id, body.brand_id):
                    raise HTTPException(
                        status_code=409,
                        detail="This user is already a member of this brand",
                    )
                # User exists but has no membership → add them directly
                membership_role = BrandMembershipRole.ADMIN if body.role == UserRole.ADMIN.value else BrandMembershipRole.NORMAL
                ub_repo.create_membership(
                    user_id=existing_user.id,
                    brand_id=body.brand_id,
                    role=membership_role,
                )
                return {
                    "success": True,
                    "message": f"{existing_user.email} has been added to the brand",
                    "invitation": None,
                }
            finally:
                ub_repo.db.close()
    finally:
        user_repo.db.close()

    invite_repo = _get_invite_repo()
    try:
        # Prevent duplicate pending invitation for the same email+brand
        if invite_repo.get_pending_by_email_and_brand(body.email, body.brand_id):
            raise HTTPException(
                status_code=409,
                detail="A pending invitation for this email already exists for this brand",
            )

        # For super user (id=0), pass None since they don't exist in DB
        inviter_id = None if current_user.id == 0 else current_user.id

        invitation = invite_repo.create_invitation(
            email=body.email,
            brand_id=body.brand_id,
            role=body.role,
            invited_by_user_id=inviter_id,
        )
        _ = invitation.brand  # Eager load before closing session
        invite_url = f"{settings.app_url}/invite?token={invitation.token}"
        invitation_dict = invitation.to_dict()
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
        "invitation": invitation_dict,
    }


@router.delete("/invite/{invitation_id}", status_code=200)
async def delete_invitation(invitation_id: int, current_user=Depends(require_admin_or_super)):
    """Soft-delete a pending invitation.

    SUPER can delete any invitation. ADMIN can only delete invitations for their own brand.
    """
    invite_repo = _get_invite_repo()
    try:
        invitation = invite_repo.get(invitation_id)
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")

        current_role = _role_value(current_user)
        current_brand = current_user.brand
        if current_role == UserRole.ADMIN.value and invitation.brand_id != (current_brand.id if current_brand else None):
            raise HTTPException(status_code=403, detail="Access denied to this invitation")

        invite_repo.soft_delete(invitation_id)
        return {"success": True, "message": "Invitation deleted"}
    finally:
        invite_repo.db.close()


@router.get("/invite/verify")
async def verify_invitation(token: str):
    """Verify an invitation token is valid and return its details."""
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
    ub_repo = _get_user_brand_repo()

    try:
        invitation = invite_repo.get_by_token(body.token)
        if not invitation or not invitation.is_valid():
            raise HTTPException(status_code=410, detail="Invitation link is invalid or has expired")

        brand = brand_repo.get_by_id(invitation.brand_id)
        if not brand or not brand.is_active:
            raise HTTPException(status_code=404, detail="Brand not found")
        _ = brand.subscription

        existing_user = user_repo.get_by_email(invitation.email)
        if existing_user:
            # User already exists — just add the membership
            if ub_repo.get_membership(existing_user.id, invitation.brand_id):
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email already belongs to this brand",
                )
            membership_role = (
                BrandMembershipRole.ADMIN
                if invitation.role == UserRole.ADMIN.value
                else BrandMembershipRole.NORMAL
            )
            ub_repo.create_membership(
                user_id=existing_user.id,
                brand_id=invitation.brand_id,
                role=membership_role,
            )
            invite_repo.mark_accepted(invitation)
            invite_repo.soft_delete(invitation.id)

            effective_role = _role_value(existing_user) if _role_value(existing_user) == UserRole.SUPER.value else membership_role.value
            token = create_access_token(
                user_id=existing_user.id,
                brand_id=brand.id,
                session_key=existing_user.session_key,
                role=effective_role,
            )
            existing_user.brand = brand
            existing_user.role = effective_role  # type: ignore[assignment]
            return {
                "success": True,
                "access_token": token,
                "token_type": "bearer",
                "user": _user_dict(existing_user, brand),
            }

        # Create new user
        user = user_repo.create_user(
            email=invitation.email,
            hashed_password=hash_password(body.password),
            name=body.name,
            role=UserRole.NORMAL,
        )
        user.is_email_verified = True  # email was verified via invitation link
        user_repo.db.commit()

        # Create brand membership
        membership_role = (
            BrandMembershipRole.ADMIN
            if invitation.role == UserRole.ADMIN.value
            else BrandMembershipRole.NORMAL
        )
        ub_repo.create_membership(
            user_id=user.id,
            brand_id=invitation.brand_id,
            role=membership_role,
        )

        # Mark invitation as accepted and remove it
        invite_repo.mark_accepted(invitation)
        invite_repo.soft_delete(invitation.id)

        token = create_access_token(
            user_id=user.id,
            brand_id=brand.id,
            session_key=user.session_key,
            role=membership_role.value,
        )

        user.brand = brand
        user.role = membership_role.value  # type: ignore[assignment]
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
        ub_repo.db.close()
