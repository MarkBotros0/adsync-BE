from typing import Any
from datetime import datetime, timedelta

_DEFAULT_TTL = 600  # 10 minutes (OAuth round-trip)


class MemoryStorage:
    """In-memory key/value store with TTL. Used only for short-lived OAuth state tokens."""

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}

    def set(self, key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
        self._store[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
        }

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if not entry:
            return None
        if datetime.utcnow() > entry["expires_at"]:
            del self._store[key]
            return None
        return entry["value"]

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


class StateStorage:
    """Short-lived OAuth state storage (CSRF protection). Always backed by MemoryStorage."""

    def __init__(self):
        self._mem = MemoryStorage()

    def set(self, state: str, brand_id: int | None = None, code_verifier: str | None = None) -> None:
        """Store state with 10-minute TTL. Optionally store a PKCE code_verifier."""
        self._mem.set(state, {"brand_id": brand_id, "code_verifier": code_verifier})

    def verify_and_delete(self, state: str):
        """Verify state and delete it. Returns (is_valid, brand_id)."""
        data = self._mem.get(state)
        if data is None:
            return False, None
        self._mem.delete(state)
        return True, data.get("brand_id")

    def verify_and_delete_pkce(self, state: str):
        """Verify state and delete it. Returns (is_valid, brand_id, code_verifier)."""
        data = self._mem.get(state)
        if data is None:
            return False, None, None
        self._mem.delete(state)
        return True, data.get("brand_id"), data.get("code_verifier")
