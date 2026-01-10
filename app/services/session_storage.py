from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.config import get_settings

settings = get_settings()


class MemoryStorage:
    """In-memory session storage"""
    
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
    
    def set(self, key: str, value: Dict[str, Any] = None, ttl: int = 3600) -> None:
        """Set value with TTL"""
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        self._storage[key] = {
            "data": value,
            "expires_at": expires_at
        }
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value if not expired"""
        if key not in self._storage:
            return None
        
        item = self._storage[key]
        if datetime.utcnow() > item["expires_at"]:
            del self._storage[key]
            return None
        
        return item["data"]
    
    def delete(self, key: str) -> bool:
        """Delete value"""
        if key in self._storage:
            del self._storage[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return self.get(key) is not None


class DatabaseStorage:
    """PostgreSQL session storage using repository pattern"""
    
    def __init__(self):
        pass
    
    def _get_repo(self):
        """Get repository instance"""
        from app.repositories.session import SessionRepository
        from app.database import get_session_local
        
        SessionLocal = get_session_local()
        db = SessionLocal()
        return SessionRepository(db)
    
    def set(self, key: str, value: Dict[str, Any] = None, ttl: int = 3600) -> None:
        """Set session in database"""
        repo = self._get_repo()
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        try:
            existing = repo.get_by_session_id(key)
            
            if existing:
                if value:
                    existing.user_id = value.get("user_id", existing.user_id)
                    existing.user_name = value.get("user_name", existing.user_name)
                    existing.email = value.get("email", existing.email)
                    existing.access_token = value.get("access_token", existing.access_token)
                existing.expires_at = expires_at
                existing.updated_at = datetime.utcnow()
                repo.update(existing)
            elif value:
                repo.create_session(
                    session_id=key,
                    user_id=value.get("user_id", ""),
                    user_name=value.get("user_name", ""),
                    email=value.get("email", ""),
                    access_token=value.get("access_token", ""),
                    expires_at=expires_at
                )
        finally:
            repo.db.close()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get session from database"""
        repo = self._get_repo()
        
        try:
            if not repo.is_valid(key):
                return None
            
            session = repo.get_by_session_id(key)
            if not session:
                return None
            
            return {
                "user_id": session.user_id,
                "user_name": session.user_name,
                "email": session.email,
                "access_token": session.access_token
            }
        finally:
            repo.db.close()
    
    def delete(self, key: str) -> bool:
        """Delete session from database"""
        repo = self._get_repo()
        
        try:
            return repo.delete_session(key)
        finally:
            repo.db.close()
    
    def exists(self, key: str) -> bool:
        """Check if session exists"""
        repo = self._get_repo()
        
        try:
            return repo.is_valid(key)
        finally:
            repo.db.close()


class StateStorage:
    """Simple state storage for OAuth state verification"""
    
    def __init__(self, storage, use_db: bool = False):
        self.storage = storage
    
    def set(self, state: str, ttl: int = 600) -> None:
        """Store state with 10 min TTL"""
        self.storage.set(f"state_{state}", {"valid": True}, ttl=ttl)
    
    def verify_and_delete(self, state: str) -> bool:
        """Verify state and delete it"""
        key = f"state_{state}"
        if self.storage.exists(key):
            self.storage.delete(key)
            return True
        return False


def get_session_storage(storage_type: str = "memory"):
    """Factory function for session storage"""
    if storage_type == "postgresql":
        return DatabaseStorage()
    return MemoryStorage()
