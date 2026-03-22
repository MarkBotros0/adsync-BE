"""
TikTok Login Kit OAuth 2.0 service.
Uses open.tiktokapis.com — access tokens expire in 24h, refresh tokens in 365d.
"""
import secrets
import httpx
from app.config import get_settings

settings = get_settings()

_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
_REVOKE_URL = "https://open.tiktokapis.com/v2/oauth/revoke/"
_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"


class TikTokAuthService:
    """Handle TikTok Login Kit OAuth 2.0 flow."""

    def __init__(self):
        self.client_key = settings.tiktok_client_key
        self.client_secret = settings.tiktok_client_secret
        self.redirect_uri = settings.tiktok_redirect_uri

    def get_login_url(self, state: str | None = None) -> dict[str, str]:
        """Build the TikTok authorization URL."""
        if not state:
            state = secrets.token_urlsafe(32)

        scopes = [
            "user.info.basic",
            "user.info.profile",
            "user.info.stats",
            "video.list",
        ]

        params = "&".join([
            f"client_key={self.client_key}",
            f"scope={','.join(scopes)}",
            f"redirect_uri={self.redirect_uri}",
            f"state={state}",
            "response_type=code",
        ])

        return {
            "login_url": f"{_AUTH_URL}?{params}",
            "state": state,
        }

    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange an authorization code for access + refresh tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": self.client_key,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Token exchange failed: {response.text}")
            data = response.json()

        # TikTok wraps token responses at the top level (not under "data")
        if "error" in data and data.get("error") not in ("", None):
            raise Exception(f"Token exchange error [{data['error']}]: {data.get('error_description', '')}")

        return data

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Obtain a new access token using the refresh token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": self.client_key,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Token refresh failed: {response.text}")
            data = response.json()

        if "error" in data and data.get("error") not in ("", None):
            raise Exception(f"Token refresh error [{data['error']}]: {data.get('error_description', '')}")

        return data

    async def revoke_token(self, access_token: str) -> None:
        """Revoke a TikTok access token on disconnect."""
        async with httpx.AsyncClient() as client:
            await client.post(
                _REVOKE_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": self.client_key,
                    "client_secret": self.client_secret,
                    "token": access_token,
                },
            )
