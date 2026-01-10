from typing import Dict, Any
from app.services.facebook.api_client import APIClient


class PostsService(APIClient):
    """Service for Facebook Posts operations"""
    
    async def fetch_post_insights(self, post_id: str) -> Dict[str, Any]:
        """Fetch engagement data for a specific post"""
        return await self.get(
            post_id,
            params={"fields": "id,message,created_time,permalink_url,shares,likes.summary(true),comments.summary(true),reactions.summary(true)"}
        )

