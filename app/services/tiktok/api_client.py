import httpx
from typing import Any


class TikTokAPIClient:
    """Base client for the TikTok Open API v2."""

    BASE_URL = "https://open.tiktokapis.com/v2"

    def __init__(self, access_token: str):
        self.access_token = access_token

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET request — used for user info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/{endpoint}",
                headers=self._auth_headers,
                params=params or {},
            )
            response.raise_for_status()
            data = response.json()

        error = data.get("error", {})
        if error.get("code", "ok") != "ok":
            raise Exception(f"TikTok API error [{error.get('code')}]: {error.get('message', '')}")

        return data

    async def post(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST request — used for video list/query endpoints."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/{endpoint}",
                headers={**self._auth_headers, "Content-Type": "application/json"},
                params=params or {},
                json=body or {},
            )
            response.raise_for_status()
            data = response.json()

        error = data.get("error", {})
        if error.get("code", "ok") != "ok":
            raise Exception(f"TikTok API error [{error.get('code')}]: {error.get('message', '')}")

        return data
