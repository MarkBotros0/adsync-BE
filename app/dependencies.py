"""Shared FastAPI dependency functions."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.services.jwt_auth import decode_token
from app.repositories.brand import BrandRepository
from app.repositories.user import UserRepository
from app.repositories.user_brand import UserBrandRepository
from app.models.user import UserRole
from app.database import get_session_local

bearer = HTTPBearer(auto_error=False)
bearer_required = HTTPBearer()


def _validate_user_and_brand(token: str):
    """Decode JWT, validate user session + brand membership. Returns (user, brand).

    For non-SUPER users the user's in-memory .role is overwritten with the
    brand-specific role from UserBrandModel so that require_admin_or_super
    works correctly without any changes.
    """
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = int(payload.get("sub", 0))
    brand_id = int(payload.get("brand_id", 0))
    token_session_key = payload.get("session_key")
    role = payload.get("role")

    # Super user bypass - doesn't exist in database
    if user_id == 0 and role == UserRole.SUPER.value:
        from app.models.user import UserModel
        # Create a virtual super user object
        class VirtualBrand:
            id = 0
            name = "Super Admin"
            is_active = True
            subscription = None

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
        return virtual_user, VirtualBrand()

    db = get_session_local()()
    try:
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or deactivated")
        if user.session_key != token_session_key:
            raise HTTPException(status_code=401, detail="Session invalidated — please log in again")

        brand_repo = BrandRepository(db)
        brand = brand_repo.get_by_id(brand_id)
        if not brand or not brand.is_active:
            raise HTTPException(status_code=401, detail="Brand not found or deactivated")

        _ = brand.subscription

        # SUPER users bypass brand membership checks
        user_role = user.role.value if isinstance(user.role, UserRole) else user.role
        if user_role != UserRole.SUPER.value:
            ub_repo = UserBrandRepository(db)
            membership = ub_repo.get_membership(user_id, brand_id)
            if not membership:
                raise HTTPException(status_code=401, detail="Access to this brand is not permitted")
            # Overwrite the in-memory role with the brand-specific role so that
            # require_admin_or_super sees the correct value for this brand context.
            user.role = membership.role  # type: ignore[assignment]

        user.brand = brand
        return user, brand
    finally:
        db.close()


def require_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_required)):
    """Validate JWT and return the authenticated user (with brand + subscription eager-loaded)."""
    user, _ = _validate_user_and_brand(credentials.credentials)
    return user


def require_brand(credentials: HTTPAuthorizationCredentials = Depends(bearer_required)):
    """Validate JWT and return the authenticated user's brand.

    Used by platform routers (Facebook, Instagram, TikTok).
    """
    _, brand = _validate_user_and_brand(credentials.credentials)
    return brand


def require_super(credentials: HTTPAuthorizationCredentials = Depends(bearer_required)):
    """Validate JWT and ensure user has SUPER role."""
    user, _ = _validate_user_and_brand(credentials.credentials)
    role = user.role.value if isinstance(user.role, UserRole) else user.role
    if role != UserRole.SUPER.value:
        raise HTTPException(status_code=403, detail="Super-user access required")
    return user


def require_admin_or_super(credentials: HTTPAuthorizationCredentials = Depends(bearer_required)):
    """Validate JWT and ensure user has ADMIN or SUPER role."""
    user, _ = _validate_user_and_brand(credentials.credentials)
    role = user.role.value if isinstance(user.role, UserRole) else user.role
    if role not in (UserRole.ADMIN.value, UserRole.SUPER.value):
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
