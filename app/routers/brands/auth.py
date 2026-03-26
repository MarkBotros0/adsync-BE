"""Brand + user authentication routes.

Endpoints:
  POST /brands/register           – create an organization + first ORG_ADMIN user
  POST /brands/login              – login; auto-issues JWT for single-brand users,
                                    returns brand list + selection token for multi-brand users
  POST /brands/select-brand       – exchange selection token + brand_id for a scoped JWT
  POST /brands/switch-brand       – re-issue JWT scoped to a different brand (authenticated)
  GET  /brands/my-brands          – list all brands the current user can access
  GET  /brands/me                 – get current user + brand
  GET  /brands/validate           – lightweight polling endpoint
  POST /brands/send-verification  – re-send OTP
  POST /brands/verify-email       – verify email with OTP
  POST /brands/logout             – soft logout
  POST /brands/force-signout      – rotate session_key, invalidate all JWTs
  POST /brands/invite             – invite a user by email (ORG_ADMIN or SUPER)
  DELETE /brands/invite/{id}      – cancel a pending invitation
  GET  /brands/invite/verify      – verify an invitation token (public)
  POST /brands/invite/accept      – accept invitation, set password, create account (public)
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

from app.config import get_settings
from app.database import get_session_local
from app.dependencies import require_user, require_org_admin
from app.models.user import UserRole
from app.models.user_brand import BrandMembershipRole
from app.repositories.brand import BrandRepository
from app.repositories.invitation import InvitationRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.organization_membership import OrganizationMembershipRepository
from app.repositories.subscription import SubscriptionRepository
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
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Repo helpers
# ──────────────────────────────────────────────

def _get_user_repo() -> UserRepository:
    return UserRepository(get_session_local()())


def _get_brand_repo() -> BrandRepository:
    return BrandRepository(get_session_local()())


def _get_org_repo() -> OrganizationRepository:
    return OrganizationRepository(get_session_local()())


def _get_org_membership_repo() -> OrganizationMembershipRepository:
    return OrganizationMembershipRepository(get_session_local()())


def _get_invite_repo() -> InvitationRepository:
    return InvitationRepository(get_session_local()())


def _get_user_brand_repo() -> UserBrandRepository:
    return UserBrandRepository(get_session_local()())


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _role_value(user) -> str:
    return user.role.value if isinstance(user.role, UserRole) else user.role


def _user_dict(user, brand, org=None) -> dict:
    role = _role_value(user)
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": role,
        "org_id": org.id if org else getattr(user, "org_id", None),
        "org_name": org.name if org else None,
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
    org_name: str
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
    role: str = UserRole.NORMAL.value   # "NORMAL" or "ORG_ADMIN"
    brand_id: int | None = None         # required for NORMAL; omitted for ORG_ADMIN


class AcceptInviteRequest(BaseModel):
    token: str
    name: str
    password: str


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    """Register a new organization and its first ORG_ADMIN user.

    No brand is created at this point — the admin creates brands from the dashboard.
    """
    user_repo = _get_user_repo()
    org_repo = _get_org_repo()
    org_membership_repo = _get_org_membership_repo()

    try:
        if user_repo.get_by_email(body.email):
            raise HTTPException(status_code=409, detail="Email already registered")

        # Resolve subscription
        subscription_id: int | None = None
        if body.subscription_name:
            sub_repo = SubscriptionRepository(org_repo.db)
            subscription = sub_repo.get_by_name(body.subscription_name)
            if subscription:
                subscription_id = subscription.id

        # Create organization
        org = org_repo.create_organization(
            name=body.org_name,
            subscription_id=subscription_id,
        )
        _ = org.subscription  # eager-load

        # Create ORG_ADMIN user
        code = generate_verification_code()
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        user = user_repo.create_user(
            email=body.email,
            hashed_password=hash_password(body.password),
            name=body.name,
            role=UserRole.NORMAL,  # role on users table is NORMAL; ORG_ADMIN comes from org membership
        )
        user_repo.set_verification_code(user, code, expires_at)

        # Link user to org as ORG_ADMIN
        org_membership_repo_2 = OrganizationMembershipRepository(org_repo.db)
        org_membership_repo_2.create_membership(user_id=user.id, org_id=org.id)

        await send_verification_email(body.email, code, type="signup")

        token = create_access_token(
            user_id=user.id,
            brand_id=0,
            org_id=org.id,
            session_key=user.session_key,
            role=UserRole.ORG_ADMIN.value,
        )

        user.brand = None
        user.role = UserRole.ORG_ADMIN  # reflect effective role in user dict
        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "user": _user_dict(user, None, org),
            "email_verified": False,
        }
    finally:
        user_repo.db.close()
        org_repo.db.close()
        org_membership_repo.db.close()


@router.post("/login", status_code=200)
async def login(body: LoginRequest):
    """Authenticate a user and issue a JWT.

    - ORG_ADMIN with no brands → JWT with brand_id=0 (redirects to create brand)
    - ORG_ADMIN with brands → JWT for first brand (or selection screen if multiple)
    - NORMAL user with one brand → JWT issued immediately
    - NORMAL user with multiple brands → selection token + brand list
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
            "org_id": "0",
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
                "org_id": 0,
                "org_name": None,
                "brand_id": 0,
                "brand": None,
                "is_active": True,
                "is_email_verified": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
        }

    user_repo = _get_user_repo()
    ub_repo = _get_user_brand_repo()
    org_membership_repo = _get_org_membership_repo()
    org_repo = _get_org_repo()

    try:
        user = user_repo.get_by_email(body.email)
        if not user or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is deactivated")

        # Check if user is an ORG_ADMIN
        org_memberships = org_membership_repo.get_orgs_for_user(user.id)

        if org_memberships:
            # ORG_ADMIN path — use the first org (most users belong to one org)
            org_membership = org_memberships[0]
            org = org_repo.get_by_id(org_membership.organization_id)
            if not org:
                raise HTTPException(status_code=500, detail="Organization not found")
            _ = org.subscription

            brands = org_repo.db.query(__import__("app.models.brand", fromlist=["BrandModel"]).BrandModel).filter(
                __import__("app.models.brand", fromlist=["BrandModel"]).BrandModel.organization_id == org.id,
                __import__("app.models.brand", fromlist=["BrandModel"]).BrandModel.deleted_at.is_(None),
                __import__("app.models.brand", fromlist=["BrandModel"]).BrandModel.is_active.is_(True),
            ).all()

            user.role = UserRole.ORG_ADMIN  # reflect effective role in user dict

            if not brands:
                # No brands yet — issue token with brand_id=0
                token = create_access_token(
                    user_id=user.id,
                    brand_id=0,
                    org_id=org.id,
                    session_key=user.session_key,
                    role=UserRole.ORG_ADMIN.value,
                )
                user.brand = None
                return {
                    "success": True,
                    "access_token": token,
                    "token_type": "bearer",
                    "user": _user_dict(user, None, org),
                    "requires_brand_creation": True,
                }

            if len(brands) == 1:
                brand = brands[0]

                token = create_access_token(
                    user_id=user.id,
                    brand_id=brand.id,
                    org_id=org.id,
                    session_key=user.session_key,
                    role=UserRole.ORG_ADMIN.value,
                )
                user.brand = brand
                return {
                    "success": True,
                    "access_token": token,
                    "token_type": "bearer",
                    "user": _user_dict(user, brand, org),
                }

            # Multiple brands — return selection token
            selection_token = _create_selection_token(user.id, user.session_key)
            return {
                "success": True,
                "requires_brand_selection": True,
                "selection_token": selection_token,
                "org_id": org.id,
                "brands": [
                    {"id": b.id, "name": b.name, "logo_url": b.logo_url, "role": UserRole.ORG_ADMIN.value}
                    for b in brands
                ],
            }

        # NORMAL user path — check brand memberships
        memberships = ub_repo.get_brands_for_user(user.id)
        if not memberships:
            raise HTTPException(status_code=403, detail="User has no active brand memberships")

        if len(memberships) == 1:
            membership = memberships[0]
            brand = membership.brand
            if not brand or not brand.is_active:
                raise HTTPException(status_code=403, detail="Brand account is deactivated")
            _ = brand.subscription

            org_id = brand.organization_id or 0
            token = create_access_token(
                user_id=user.id,
                brand_id=brand.id,
                org_id=org_id,
                session_key=user.session_key,
                role=UserRole.NORMAL.value,
            )
            user.brand = brand
            return {
                "success": True,
                "access_token": token,
                "token_type": "bearer",
                "user": _user_dict(user, brand),
            }

        # Multiple brand memberships — selection screen
        selection_token = _create_selection_token(user.id, user.session_key)
        brands_list = []
        for m in memberships:
            b = m.brand
            if b and b.is_active:
                brands_list.append({
                    "id": b.id,
                    "name": b.name,
                    "logo_url": b.logo_url,
                    "role": UserRole.NORMAL.value,
                    "org_id": b.organization_id or 0,
                })

        return {
            "success": True,
            "requires_brand_selection": True,
            "selection_token": selection_token,
            "brands": brands_list,
        }
    finally:
        user_repo.db.close()
        ub_repo.db.close()
        org_membership_repo.db.close()
        org_repo.db.close()


@router.post("/select-brand", status_code=200)
async def select_brand(body: SelectBrandRequest):
    """Exchange a brand selection token + brand_id for a scoped JWT."""
    try:
        payload = _decode_selection_token(body.selection_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired selection token")

    user_id = int(payload.get("sub", 0))
    token_session_key = payload.get("session_key")

    user_repo = _get_user_repo()
    ub_repo = _get_user_brand_repo()
    brand_repo = _get_brand_repo()
    org_membership_repo = _get_org_membership_repo()

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

        org_id = brand.organization_id or 0

        # Determine role
        is_org_admin = org_membership_repo.get_membership(user_id, org_id) is not None
        if is_org_admin:
            effective_role = UserRole.ORG_ADMIN.value
        else:
            membership = ub_repo.get_membership(user_id, body.brand_id)
            if not membership:
                raise HTTPException(status_code=403, detail="You are not a member of this brand")
            effective_role = UserRole.NORMAL.value

        token = create_access_token(
            user_id=user.id,
            brand_id=brand.id,
            org_id=org_id,
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
        org_membership_repo.db.close()


@router.post("/switch-brand", status_code=200)
async def switch_brand(body: SwitchBrandRequest, current_user=Depends(require_user)):
    """Re-issue a JWT scoped to a different brand."""
    ub_repo = _get_user_brand_repo()
    brand_repo = _get_brand_repo()
    org_membership_repo = _get_org_membership_repo()

    try:
        brand = brand_repo.get_by_id(body.brand_id)
        if not brand or not brand.is_active:
            raise HTTPException(status_code=404, detail="Brand not found")
        _ = brand.subscription

        user_role = _role_value(current_user)
        org_id = brand.organization_id or getattr(current_user, "org_id", 0)

        if user_role == UserRole.SUPER.value:
            effective_role = UserRole.SUPER.value
        elif org_membership_repo.get_membership(current_user.id, org_id):
            effective_role = UserRole.ORG_ADMIN.value
        else:
            membership = ub_repo.get_membership(current_user.id, body.brand_id)
            if not membership:
                raise HTTPException(status_code=403, detail="You are not a member of this brand")
            effective_role = UserRole.NORMAL.value

        token = create_access_token(
            user_id=current_user.id,
            brand_id=brand.id,
            org_id=org_id,
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
        org_membership_repo.db.close()


@router.get("/my-brands", status_code=200)
async def my_brands(current_user=Depends(require_user)):
    """Return all brands the authenticated user can access.

    ORG_ADMIN → all brands in their org.
    NORMAL → only brands they have a user_brands row for.
    SUPER → all brands across all orgs.
    """
    user_role = _role_value(current_user)
    org_id = getattr(current_user, "org_id", 0)

    brand_repo = _get_brand_repo()
    try:
        if user_role == UserRole.SUPER.value:
            brands = brand_repo.get_all_brands()
            for b in brands:
                _ = b.subscription
            return {
                "success": True,
                "brands": [
                    {"id": b.id, "name": b.name, "logo_url": b.logo_url, "role": UserRole.SUPER.value}
                    for b in brands
                ],
            }

        if user_role == UserRole.ORG_ADMIN.value:
            brands = brand_repo.get_brands_for_org(org_id)
            for b in brands:
                _ = b.subscription
            return {
                "success": True,
                "brands": [
                    {"id": b.id, "name": b.name, "logo_url": b.logo_url, "role": UserRole.ORG_ADMIN.value}
                    for b in brands
                ],
            }

        # NORMAL — only their brand memberships
        ub_repo = _get_user_brand_repo()
        try:
            memberships = ub_repo.get_brands_for_user(current_user.id)
            brands_list = []
            for m in memberships:
                b = m.brand
                if b and b.is_active and b.deleted_at is None:
                    brands_list.append({
                        "id": b.id,
                        "name": b.name,
                        "logo_url": b.logo_url,
                        "role": UserRole.NORMAL.value,
                    })
            return {"success": True, "brands": brands_list}
        finally:
            ub_repo.db.close()
    finally:
        brand_repo.db.close()


@router.get("/me")
async def get_me(user=Depends(require_user)):
    return {"success": True, "user": user.to_dict()}


@router.get("/validate")
async def validate_session(user=Depends(require_user)):
    brand = user.brand
    org_id = getattr(user, "org_id", 0)
    return {
        "valid": True,
        "user_id": user.id,
        "org_id": org_id,
        "brand_id": brand.id if brand else None,
        "brand_name": brand.name if brand else None,
        "subscription": (
            brand.organization.subscription.name
            if brand and brand.organization and brand.organization.subscription
            else "free"
        ),
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
    if user.id == 0:
        # Config-level SUPER user is not in the DB — nothing to invalidate
        return {"success": True, "message": "Logged out successfully"}

    repo = _get_user_repo()
    try:
        fresh_user = repo.get_by_id(user.id)
        if fresh_user:
            repo.rotate_session_key(fresh_user)
    finally:
        repo.db.close()

    return {"success": True, "message": "Logged out successfully"}


@router.post("/force-signout", status_code=200)
async def force_signout(user=Depends(require_user)):
    repo = _get_user_repo()
    try:
        fresh_user = repo.get_by_id(user.id)
        if not fresh_user:
            raise HTTPException(status_code=404, detail="User not found")
        updated = repo.rotate_session_key(fresh_user)

        brand = user.brand
        brand_id = brand.id if brand else 0
        org_id = getattr(user, "org_id", 0)
        new_token = create_access_token(
            user_id=updated.id,
            brand_id=brand_id,
            org_id=org_id,
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


# ── Invitation endpoints ──────────────────────────────────────────────────────

@router.post("/invite", status_code=201)
async def invite_user(body: InviteRequest, current_user=Depends(require_org_admin)):
    """Invite a user by email. ORG_ADMIN and SUPER only.

    - role=NORMAL  → brand-scoped invite; brand_id required.
    - role=ORG_ADMIN → org-level invite; brand_id ignored; user gets access to all brands.
    """
    current_role = _role_value(current_user)
    org_id = getattr(current_user, "org_id", 0)
    inviting_org_admin = body.role == UserRole.ORG_ADMIN.value

    inviter_id = None if current_user.id == 0 else current_user.id

    # ── ORG_ADMIN invite path ─────────────────────────────────────────────────
    if inviting_org_admin:
        org_repo = _get_org_repo()
        try:
            org = org_repo.get(org_id)
            if not org:
                raise HTTPException(status_code=404, detail="Organization not found")
            org_name = org.name
        finally:
            org_repo.db.close()

        # If the user already exists, add them to the org directly
        user_repo = _get_user_repo()
        try:
            existing_user = user_repo.get_by_email(body.email)
            if existing_user:
                om_repo = _get_org_membership_repo()
                try:
                    if om_repo.get_membership(existing_user.id, org_id):
                        raise HTTPException(status_code=409, detail="User is already an admin of this organization")
                    om_repo.create_membership(user_id=existing_user.id, org_id=org_id)
                    return {
                        "success": True,
                        "message": f"{existing_user.email} has been added as an org admin",
                        "invitation": None,
                    }
                finally:
                    om_repo.db.close()
        finally:
            user_repo.db.close()

        invite_repo = _get_invite_repo()
        try:
            if invite_repo.get_pending_by_email_and_org(body.email, org_id):
                raise HTTPException(status_code=409, detail="A pending invitation already exists for this email")

            invitation = invite_repo.create_invitation(
                email=body.email,
                role=UserRole.ORG_ADMIN.value,
                invited_by_user_id=inviter_id,
                organization_id=org_id,
            )
            _ = invitation.organization
            invite_url = f"{settings.app_url}/invite?token={invitation.token}"
            invitation_dict = invitation.to_dict()
        finally:
            invite_repo.db.close()

        await send_invitation_email(
            email=body.email,
            invite_url=invite_url,
            org_name=org_name,
            inviter_name=current_user.name,
            role=UserRole.ORG_ADMIN.value,
        )

        return {
            "success": True,
            "message": f"Invitation sent to {body.email}",
            "invitation": invitation_dict,
        }

    # ── NORMAL (brand-scoped) invite path ─────────────────────────────────────
    if not body.brand_id:
        raise HTTPException(status_code=422, detail="brand_id is required when inviting a member")

    brand_repo = _get_brand_repo()
    try:
        brand = brand_repo.get_by_id(body.brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        if current_role == UserRole.ORG_ADMIN.value and brand.organization_id != org_id:
            raise HTTPException(status_code=403, detail="Brand does not belong to your organization")
        brand_name = brand.name
    finally:
        brand_repo.db.close()

    user_repo = _get_user_repo()
    try:
        existing_user = user_repo.get_by_email(body.email)
        if existing_user:
            ub_repo = _get_user_brand_repo()
            try:
                if ub_repo.get_membership(existing_user.id, body.brand_id):
                    raise HTTPException(status_code=409, detail="User is already a member of this brand")
                ub_repo.create_membership(
                    user_id=existing_user.id,
                    brand_id=body.brand_id,
                    role=BrandMembershipRole.NORMAL,
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
        if invite_repo.get_pending_by_email_and_brand(body.email, body.brand_id):
            raise HTTPException(status_code=409, detail="A pending invitation already exists for this email")

        invitation = invite_repo.create_invitation(
            email=body.email,
            role=UserRole.NORMAL.value,
            invited_by_user_id=inviter_id,
            brand_id=body.brand_id,
        )
        _ = invitation.brand
        invite_url = f"{settings.app_url}/invite?token={invitation.token}"
        invitation_dict = invitation.to_dict()
    finally:
        invite_repo.db.close()

    await send_invitation_email(
        email=body.email,
        invite_url=invite_url,
        org_name=brand_name,
        inviter_name=current_user.name,
        role=UserRole.NORMAL.value,
    )

    return {
        "success": True,
        "message": f"Invitation sent to {body.email}",
        "invitation": invitation_dict,
    }


@router.delete("/invite/{invitation_id}", status_code=200)
async def delete_invitation(invitation_id: int, current_user=Depends(require_org_admin)):
    """Cancel a pending invitation."""
    org_id = getattr(current_user, "org_id", 0)
    current_role = _role_value(current_user)

    invite_repo = _get_invite_repo()
    brand_repo = _get_brand_repo()
    try:
        invitation = invite_repo.get(invitation_id)
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")

        # ORG_ADMIN can only delete invitations for their own org
        if current_role == UserRole.ORG_ADMIN.value:
            if invitation.organization_id and invitation.organization_id != org_id:
                raise HTTPException(status_code=403, detail="Access denied to this invitation")
            if invitation.brand_id:
                brand = brand_repo.get_by_id(invitation.brand_id)
                if not brand or brand.organization_id != org_id:
                    raise HTTPException(status_code=403, detail="Access denied to this invitation")

        invite_repo.soft_delete(invitation_id)
        return {"success": True, "message": "Invitation deleted"}
    finally:
        invite_repo.db.close()
        brand_repo.db.close()


@router.get("/invite/verify")
async def verify_invitation(token: str):
    """Verify an invitation token is valid and return its details."""
    repo = _get_invite_repo()
    try:
        invitation = repo.get_by_token(token)
        if not invitation or not invitation.is_valid():
            raise HTTPException(status_code=410, detail="Invitation link is invalid or has expired")
        _ = invitation.brand
        _ = invitation.organization
        return {
            "valid": True,
            "email": invitation.email,
            "brand_id": invitation.brand_id,
            "brand_name": invitation.brand.name if invitation.brand else None,
            "organization_id": invitation.organization_id,
            "org_name": invitation.organization.name if invitation.organization else None,
            "role": invitation.role,
            "expires_at": invitation.expires_at.isoformat(),
        }
    finally:
        repo.db.close()


@router.post("/invite/accept", status_code=201)
async def accept_invitation(body: AcceptInviteRequest):
    """Accept an invitation: create a user account (if new) and return a JWT."""
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    invite_repo = _get_invite_repo()
    user_repo = _get_user_repo()
    org_repo = _get_org_repo()
    brand_repo = _get_brand_repo()
    ub_repo = _get_user_brand_repo()
    om_repo = _get_org_membership_repo()

    try:
        invitation = invite_repo.get_by_token(body.token)
        if not invitation or not invitation.is_valid():
            raise HTTPException(status_code=410, detail="Invitation link is invalid or has expired")

        is_org_admin_invite = invitation.role == UserRole.ORG_ADMIN

        # ── ORG_ADMIN invite ──────────────────────────────────────────────────
        if is_org_admin_invite:
            org_id = invitation.organization_id or 0
            org = org_repo.get(org_id)
            if not org:
                raise HTTPException(status_code=404, detail="Organization not found")

            existing_user = user_repo.get_by_email(invitation.email)
            if existing_user:
                if om_repo.get_membership(existing_user.id, org_id):
                    raise HTTPException(status_code=409, detail="Account is already an admin of this organization")
                om_repo.create_membership(user_id=existing_user.id, org_id=org_id)
                invite_repo.mark_accepted(invitation)
                invite_repo.soft_delete(invitation.id)

                jwt_token = create_access_token(
                    user_id=existing_user.id,
                    brand_id=None,
                    org_id=org_id,
                    session_key=existing_user.session_key,
                    role=UserRole.ORG_ADMIN.value,
                )
                existing_user.brand = None
                return {
                    "success": True,
                    "access_token": jwt_token,
                    "token_type": "bearer",
                    "user": _user_dict(existing_user, None),
                    "requires_brand_creation": False,
                }

            # New user
            new_user = user_repo.create_user(
                email=invitation.email,
                hashed_password=hash_password(body.password),
                name=body.name,
                role=UserRole.NORMAL,
            )
            new_user.is_email_verified = True
            user_repo.db.commit()

            om_repo.create_membership(user_id=new_user.id, org_id=org_id)
            invite_repo.mark_accepted(invitation)
            invite_repo.soft_delete(invitation.id)

            jwt_token = create_access_token(
                user_id=new_user.id,
                brand_id=None,
                org_id=org_id,
                session_key=new_user.session_key,
                role=UserRole.ORG_ADMIN.value,
            )
            new_user.brand = None
            return {
                "success": True,
                "access_token": jwt_token,
                "token_type": "bearer",
                "user": _user_dict(new_user, None),
                "requires_brand_creation": False,
            }

        # ── NORMAL (brand-scoped) invite ──────────────────────────────────────
        brand = brand_repo.get_by_id(invitation.brand_id)
        if not brand or not brand.is_active:
            raise HTTPException(status_code=404, detail="Brand not found")
        _ = brand.subscription

        org_id = brand.organization_id or 0

        existing_user = user_repo.get_by_email(invitation.email)
        if existing_user:
            if ub_repo.get_membership(existing_user.id, invitation.brand_id):
                raise HTTPException(status_code=409, detail="Account already belongs to this brand")
            ub_repo.create_membership(
                user_id=existing_user.id,
                brand_id=invitation.brand_id,
                role=BrandMembershipRole.NORMAL,
            )
            invite_repo.mark_accepted(invitation)
            invite_repo.soft_delete(invitation.id)

            jwt_token = create_access_token(
                user_id=existing_user.id,
                brand_id=brand.id,
                org_id=org_id,
                session_key=existing_user.session_key,
                role=UserRole.NORMAL.value,
            )
            existing_user.brand = brand
            return {
                "success": True,
                "access_token": jwt_token,
                "token_type": "bearer",
                "user": _user_dict(existing_user, brand),
            }

        # New user
        user = user_repo.create_user(
            email=invitation.email,
            hashed_password=hash_password(body.password),
            name=body.name,
            role=UserRole.NORMAL,
        )
        user.is_email_verified = True
        user_repo.db.commit()

        ub_repo.create_membership(
            user_id=user.id,
            brand_id=invitation.brand_id,
            role=BrandMembershipRole.NORMAL,
        )
        invite_repo.mark_accepted(invitation)
        invite_repo.soft_delete(invitation.id)

        jwt_token = create_access_token(
            user_id=user.id,
            brand_id=brand.id,
            org_id=org_id,
            session_key=user.session_key,
            role=UserRole.NORMAL.value,
        )
        user.brand = brand
        return {
            "success": True,
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": _user_dict(user, brand),
        }
    finally:
        invite_repo.db.close()
        user_repo.db.close()
        org_repo.db.close()
        brand_repo.db.close()
        ub_repo.db.close()
        om_repo.db.close()
