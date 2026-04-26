class FacebookAPIError(Exception):
    """Raised when Facebook API returns an error"""
    pass


class InstagramAPIError(Exception):
    """Raised when Instagram Graph API returns an error"""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class SessionNotFoundError(Exception):
    """Raised when session is not found or expired"""
    pass


class ApifyActorError(Exception):
    """Raised when an Apify actor run fails or times out."""

    def __init__(self, actor_id: str, message: str):
        self.actor_id = actor_id
        super().__init__(f"[{actor_id}] {message}")

