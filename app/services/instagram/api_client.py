import httpx
from typing import Dict, Any


class InstagramAPIClient:
    """Base client for the Instagram Graph API (graph.instagram.com)."""

    BASE_URL = "https://graph.instagram.com/v22.0"

    def __init__(self, access_token: str):
        self.access_token = access_token

    async def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        if params is None:
            params = {}
        params["access_token"] = self.access_token

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}/{endpoint}", params=params)
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            raise Exception(data["error"].get("message", "Instagram API error"))

        return data
