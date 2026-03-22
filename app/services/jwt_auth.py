"""JWT authentication service for brand accounts.

Every JWT embeds:
  - sub       : brand id (str)
  - session_key: per-brand nonce stored in the DB.
                 Rotating it invalidates all previously issued tokens (force sign-out).
  - exp       : expiry timestamp

Validation checks BOTH the signature/expiry AND that the session_key in the
token matches the one currently stored in the database.
"""
from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ──────────────────────────────────────────────
# Password helpers
# ──────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ──────────────────────────────────────────────
# Token helpers
# ──────────────────────────────────────────────

def create_access_token(brand_id: int, session_key: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT for a brand account."""
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=settings.jwt_access_token_expire_hours))
    payload = {
        "sub": str(brand_id),
        "session_key": session_key,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "brand_access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and verify JWT signature + expiry. Returns raw payload dict.

    Raises ``JWTError`` on failure.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_brand_id_from_token(token: str) -> int | None:
    """Return brand_id from token, or None if invalid/expired."""
    try:
        payload = decode_token(token)
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


def get_session_key_from_token(token: str) -> str | None:
    """Return the session_key embedded in the token, or None if invalid."""
    try:
        payload = decode_token(token)
        return payload.get("session_key")
    except JWTError:
        return None
