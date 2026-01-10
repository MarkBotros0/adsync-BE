from typing import Dict, Any
from app.services.facebook.api_client import APIClient


class AdsService(APIClient):
    """Service for Facebook Ads operations"""
    
    async def fetch_ad_insights(self, ad_account_id: str) -> Dict[str, Any]:
        """Fetch insights for an ad account"""
        return await self.get(
            f"{ad_account_id}/insights",
            params={"fields": "clicks,impressions,spend"}
        )

