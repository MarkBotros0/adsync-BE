from typing import Dict, Any
from app.services.facebook.api_client import APIClient
from app.utils.exceptions import FacebookAPIError


class PagesService(APIClient):
    """Service for Facebook Pages operations"""
    
    async def fetch_pages(self) -> Dict[str, Any]:
        """Fetch all pages the user manages"""
        return await self.get(
            "me/accounts",
            params={"fields": "id,name,access_token,category,followers_count,fan_count"}
        )
    
    async def fetch_page_posts(self, page_id: str, limit: int = 25) -> Dict[str, Any]:
        """Fetch posts from a specific page"""
        try:
            return await self.get(
                f"{page_id}/posts",
                params={
                    "fields": "id,message,created_time,permalink_url,story",
                    "limit": limit
                }
            )
        except FacebookAPIError as e:
            if "10" in str(e):
                return await self.get(
                    f"{page_id}/feed",
                    params={
                        "fields": "id,message,created_time,permalink_url,story",
                        "limit": limit
                    }
                )
            raise

