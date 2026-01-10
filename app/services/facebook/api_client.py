import httpx
from typing import Dict, Any
from app.config import get_settings
from app.utils.exceptions import FacebookAPIError

settings = get_settings()


class APIClient:
    """Base client for Facebook Graph API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = f"https://graph.facebook.com/{settings.facebook_api_version}"
    
    async def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make GET request to Facebook API"""
        if params is None:
            params = {}
        
        params["access_token"] = self.access_token
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                raise FacebookAPIError(f"{data['error'].get('message', 'Unknown error')}")
            
            return data

