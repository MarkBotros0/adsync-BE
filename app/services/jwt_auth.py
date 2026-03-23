"""JWT authentication service for user accounts.

Every JWT embeds:
  - sub        : user id (str)
  - brand_id   : brand the user belongs to (str)
  - session_key: per-user nonce — rotating it invalidates all tokens (force sign-out)
  - role       : user role string
  - exp        : expiry timestamp
"""
from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(
    user_id: int,
    brand_id: int,
    session_key: str,
    role: str = "NORMAL",
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT for a user account."""
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=settings.jwt_access_token_expire_hours))
    payload = {
        "sub": str(user_id),
        "brand_id": str(brand_id),
        "session_key": session_key,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "user_access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and verify JWT. Raises ``JWTError`` on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_user_id_from_token(token: str) -> int | None:
    try:
        return int(decode_token(token)["sub"])
    except (JWTError, KeyError, ValueError):
        return None


def get_brand_id_from_token(token: str) -> int | None:
    try:
        return int(decode_token(token)["brand_id"])
    except (JWTError, KeyError, ValueError):
        return None


def get_session_key_from_token(token: str) -> str | None:
    try:
        return decode_token(token).get("session_key")
    except JWTError:
        return None
