"""
Facebook OAuth Authentication Service
Handles OAuth 2.0 flow for Facebook
"""
import httpx
import secrets
from typing import Optional, Dict
from app.config import get_settings

settings = get_settings()


class FacebookAuthService:
    """Handle Facebook OAuth 2.0 authentication flow"""
    
    def __init__(self):
        self.app_id = settings.facebook_app_id
        self.app_secret = settings.facebook_app_secret
        self.redirect_uri = settings.facebook_redirect_uri
        self.base_url = f"https://graph.facebook.com/{settings.facebook_api_version}"
        self.oauth_base_url = f"https://www.facebook.com/{settings.facebook_api_version}/dialog/oauth"
        
    def get_login_url(self, state: Optional[str] = None) -> Dict[str, str]:
        """
        Generate Facebook OAuth login URL
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Dictionary with login URL and state
        """
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Request permissions for ads insights and page insights
        scopes = [
            "ads_read",
            "ads_management",
            "read_insights",
            "business_management",
            "pages_show_list",
            "pages_read_engagement"
        ]
        
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": ",".join(scopes),
            "response_type": "code"
        }
        
        # Build the URL
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        login_url = f"{self.oauth_base_url}?{query_string}"
        
        return {
            "login_url": login_url,
            "state": state
        }
    
    async def exchange_code_for_token(self, code: str) -> Dict:
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code from Facebook callback
            
        Returns:
            Dictionary containing access_token and other token info
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/oauth/access_token",
                params={
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "redirect_uri": self.redirect_uri,
                    "code": code
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to exchange code: {response.text}")
            
            return response.json()
    
    async def get_long_lived_token(self, short_lived_token: str) -> Dict:
        """
        Exchange short-lived token for long-lived token
        
        Args:
            short_lived_token: Short-lived access token
            
        Returns:
            Dictionary with long-lived access token
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "fb_exchange_token": short_lived_token
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get long-lived token: {response.text}")
            
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict:
        """
        Get user information from Facebook
        
        Args:
            access_token: Valid Facebook access token
            
        Returns:
            User information dictionary
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/me",
                params={
                    "access_token": access_token,
                    "fields": "id,name,email"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get user info: {response.text}")
            
            return response.json()
    
    async def get_ad_accounts(self, access_token: str, user_id: str) -> Dict:
        """
        Get user's ad accounts
        
        Args:
            access_token: Valid Facebook access token
            user_id: Facebook user ID
            
        Returns:
            List of ad accounts
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{user_id}/adaccounts",
                params={
                    "access_token": access_token,
                    "fields": "id,name,account_id,account_status"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get ad accounts: {response.text}")
            
            return response.json()
    
    async def validate_token(self, access_token: str) -> Dict:
        """
        Validate an access token and get its metadata
        
        Args:
            access_token: Access token to validate
            
        Returns:
            Token metadata including expiry and permissions
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/debug_token",
                params={
                    "input_token": access_token,
                    "access_token": f"{self.app_id}|{self.app_secret}"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to validate token: {response.text}")
            
            return response.json()

