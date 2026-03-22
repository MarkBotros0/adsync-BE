"""Shared Instagram session helper for Instagram content routers."""
from datetime import datetime
from fastapi import HTTPException

from app.repositories.instagram_session import InstagramSessionRepository
from app.database import get_session_local


def get_instagram_session(session_id: str) -> dict[str, str]:
    """Look up a valid Instagram session by ID, or raise 401."""
    db = get_session_local()()
    try:
        repo = InstagramSessionRepository(db)
        session = repo.get_by_session_id(session_id)
        if not session or session.expires_at.replace(tzinfo=None) < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Invalid or expired Instagram session")
        return {
            "ig_user_id": session.ig_user_id,
            "username": session.username,
            "access_token": session.access_token,
        }
    finally:
        db.close()
