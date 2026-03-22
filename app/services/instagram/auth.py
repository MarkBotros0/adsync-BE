"""
Instagram Business Login OAuth service.
Uses graph.instagram.com — does NOT require a linked Facebook Page.
"""
import secrets
import httpx
from app.config import get_settings

settings = get_settings()

_IG_API_VERSION = "v22.0"
_IG_GRAPH_BASE = f"https://graph.instagram.com/{_IG_API_VERSION}"


class InstagramAuthService:
    """Handle Business Login for Instagram OAuth 2.0 flow."""

    def __init__(self):
        self.app_id = settings.instagram_app_id
        self.app_secret = settings.instagram_app_secret
        self.redirect_uri = settings.instagram_redirect_uri

    def get_login_url(self, state: str | None = None) -> dict[str, str]:
        """Build the Instagram Business Login authorization URL."""
        if not state:
            state = secrets.token_urlsafe(32)

        scopes = [
            "instagram_business_basic",
            "instagram_business_manage_comments",
            "instagram_business_manage_messages",
            "instagram_business_content_publish",
        ]

        params = "&".join([
            f"client_id={self.app_id}",
            f"redirect_uri={self.redirect_uri}",
            f"scope={','.join(scopes)}",
            "response_type=code",
            f"state={state}",
        ])

        return {
            "login_url": f"https://www.instagram.com/oauth/authorize?{params}",
            "state": state,
        }

    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for a short-lived Instagram User token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.instagram.com/oauth/access_token",
                data={
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                    "code": code,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Token exchange failed: {response.text}")
            return response.json()

    async def get_long_lived_token(self, short_lived_token: str) -> dict:
        """Exchange a short-lived token (1h) for a long-lived token (60 days)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_IG_GRAPH_BASE}/access_token",
                params={
                    "grant_type": "ig_exchange_token",
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "access_token": short_lived_token,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Long-lived token exchange failed: {response.text}")
            return response.json()

    async def get_user_info(self, access_token: str) -> dict:
        """Fetch the authenticated Instagram user's profile."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_IG_GRAPH_BASE}/me",
                params={
                    "fields": "user_id,username,name,account_type,profile_picture_url",
                    "access_token": access_token,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Failed to fetch user info: {response.text}")
            return response.json()
