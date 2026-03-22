"""Shared FastAPI dependency functions.

Import from here instead of duplicating auth logic across routers.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.services.jwt_auth import decode_token
from app.repositories.brand import BrandRepository
from app.database import get_session_local

# Reusable bearer extractors — import these in routers instead of creating new ones.
bearer = HTTPBearer(auto_error=False)       # optional: returns None when no token present
bearer_required = HTTPBearer()              # required: raises 403 automatically when absent


def require_brand(credentials: HTTPAuthorizationCredentials = Depends(bearer_required)):
    """Validate brand JWT and return the brand ORM object.

    Also eagerly loads brand.subscription while the DB session is open,
    so callers can access it safely after this dependency resolves.

    Raises:
        HTTPException 401: if the token is missing, invalid, expired,
                           or the session has been invalidated.
    """
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
        # Trigger lazy load while the session is still open so callers can
        # access brand.subscription after db.close().
        _ = brand.subscription
        return brand
    finally:
        db.close()


def optional_brand_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int | None:
    """Extract brand_id from JWT if a valid token is present; returns None otherwise.

    Never raises — callers treat None as "unauthenticated but allowed".
    """
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        return int(payload.get("sub", 0)) or None
    except (JWTError, ValueError):
        return None
