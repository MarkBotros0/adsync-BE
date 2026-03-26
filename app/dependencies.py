"""Shared FastAPI dependency functions."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.services.jwt_auth import decode_token
from app.repositories.brand import BrandRepository
from app.repositories.user import UserRepository
from app.repositories.user_brand import UserBrandRepository
from app.repositories.organization_membership import OrganizationMembershipRepository
from app.models.user import UserRole
from app.database import get_session_local

bearer = HTTPBearer(auto_error=False)
bearer_required = HTTPBearer()


def _validate_user_and_brand(token: str):
    """Decode JWT, validate user session + brand access. Returns (user, brand).

    Access is granted if:
      - user.role == SUPER (app-wide)
      - user has an OrganizationMembershipModel row for the brand's org (ORG_ADMIN)
      - user has a UserBrandModel row for the brand (NORMAL)
    """
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = int(payload.get("sub", 0))
    _raw_brand_id = payload.get("brand_id")
    brand_id = int(_raw_brand_id) if _raw_brand_id not in (None, "None", "") else 0
    org_id = int(payload.get("org_id", 0))
    token_session_key = payload.get("session_key")
    role = payload.get("role")

    # Config-level SUPER user (not in DB)
    if user_id == 0 and role == UserRole.SUPER.value:
        from app.models.user import UserModel

        class VirtualBrand:
            id = 0
            name = "Super Admin"
            is_active = True
            subscription = None
            organization_id = 0

        virtual_user = UserModel(
            id=0,
            email=payload.get("email", "super@adsync.com"),
            name="Super Admin",
            role=UserRole.SUPER,
            session_key=token_session_key,
            is_active=True,
            is_email_verified=True,
        )
        virtual_user.brand = VirtualBrand()
        virtual_user.org_id = 0
        return virtual_user, VirtualBrand()

    db = get_session_local()()
    try:
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or deactivated")
        if user.session_key != token_session_key:
            raise HTTPException(status_code=401, detail="Session invalidated — please log in again")

        user_role = user.role.value if isinstance(user.role, UserRole) else user.role

        # SUPER bypasses everything
        if user_role == UserRole.SUPER.value:
            user.brand = None
            user.org_id = org_id
            return user, None

        # Load the requested brand (brand_id=0 means no active brand yet — allowed for ORG_ADMIN)
        brand = None
        if brand_id:
            brand_repo = BrandRepository(db)
            brand = brand_repo.get_by_id(brand_id)
            if not brand or not brand.is_active:
                raise HTTPException(status_code=401, detail="Brand not found or deactivated")
            if brand.organization:
                _ = brand.organization.subscription

        # Determine access: ORG_ADMIN via org membership, or NORMAL via brand membership
        if brand:
            brand_org_id = brand.organization_id or org_id
            org_repo = OrganizationMembershipRepository(db)
            is_org_admin = org_repo.get_membership(user_id, brand_org_id) is not None

            if not is_org_admin:
                ub_repo = UserBrandRepository(db)
                membership = ub_repo.get_membership(user_id, brand_id)
                if not membership:
                    raise HTTPException(status_code=403, detail="Access to this brand is not permitted")
                user.role = UserRole.NORMAL  # type: ignore[assignment]
            else:
                user.role = UserRole.ORG_ADMIN  # type: ignore[assignment]
        else:
            # No brand context — verify at least the user has org membership
            org_repo = OrganizationMembershipRepository(db)
            is_org_admin = org_repo.get_membership(user_id, org_id) is not None
            if not is_org_admin:
                raise HTTPException(status_code=403, detail="No organization access")
            user.role = UserRole.ORG_ADMIN  # type: ignore[assignment]

        user.brand = brand
        user.org_id = org_id
        return user, brand
    finally:
        db.close()


def require_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_required)):
    """Validate JWT and return the authenticated user."""
    user, _ = _validate_user_and_brand(credentials.credentials)
    return user


def require_brand(credentials: HTTPAuthorizationCredentials = Depends(bearer_required)):
    """Validate JWT and return the authenticated user's brand."""
    _, brand = _validate_user_and_brand(credentials.credentials)
    return brand


def require_super(credentials: HTTPAuthorizationCredentials = Depends(bearer_required)):
    """Validate JWT and ensure user has SUPER role."""
    user, _ = _validate_user_and_brand(credentials.credentials)
    role = user.role.value if isinstance(user.role, UserRole) else user.role
    if role != UserRole.SUPER.value:
        raise HTTPException(status_code=403, detail="Super-user access required")
    return user


def require_org_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_required)):
    """Validate JWT and ensure user is an ORG_ADMIN or SUPER."""
    user, _ = _validate_user_and_brand(credentials.credentials)
    role = user.role.value if isinstance(user.role, UserRole) else user.role
    if role not in (UserRole.ORG_ADMIN.value, UserRole.SUPER.value):
        raise HTTPException(status_code=403, detail="Organization admin access required")
    return user


def require_admin_or_super(credentials: HTTPAuthorizationCredentials = Depends(bearer_required)):
    """Validate JWT and ensure user has ORG_ADMIN, legacy ADMIN, or SUPER role."""
    user, _ = _validate_user_and_brand(credentials.credentials)
    role = user.role.value if isinstance(user.role, UserRole) else user.role
    if role not in (UserRole.ORG_ADMIN.value, UserRole.ADMIN.value, UserRole.SUPER.value):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def optional_brand_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int | None:
    """Extract brand_id from JWT if present and valid; None otherwise. Never raises."""
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        return int(payload.get("brand_id", 0)) or None
    except (JWTError, ValueError):
        return None


def optional_org_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int | None:
    """Extract org_id from JWT if present and valid; None otherwise. Never raises."""
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        return int(payload.get("org_id", 0)) or None
    except (JWTError, ValueError):
        return None
