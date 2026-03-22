from typing import Any
from app.services.instagram.api_client import InstagramAPIClient


class InstagramAccountService(InstagramAPIClient):
    """Service for Instagram account profile data via Instagram Login."""

    async def fetch_profile(self, ig_user_id: str) -> dict[str, Any]:
        """Fetch full profile for an Instagram user."""
        return await self.get(
            ig_user_id,
            params={
                "fields": (
                    "id,username,name,biography,profile_picture_url,"
                    "website,followers_count,follows_count,media_count"
                )
            },
        )
