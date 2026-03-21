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

