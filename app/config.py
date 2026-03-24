"""
Application configuration module
Load environment variables and provide settings
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # Vercel Deployment URL (auto-detected)
    deployed_url: str = ""

    # Application URL (can be overridden)
    app_url: str = ""

    # Facebook OAuth Configuration
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_redirect_uri: str = ""

    # Instagram OAuth Configuration (Business Login for Instagram)
    instagram_app_id: str = ""
    instagram_app_secret: str = ""
    instagram_redirect_uri: str = ""

    # TikTok OAuth Configuration (Login Kit)
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = ""

    # Application Settings
    secret_key: str

    # Facebook API Version
    facebook_api_version: str = "v25.0"

    # Session Storage (memory or postgresql)
    session_storage: str

    # PostgreSQL Database URL
    database_url: str

    # JWT Configuration for brand accounts
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_hours: int = 24

    # Gmail SMTP (shared with Refs Project)
    gmail_user: str = ""
    gmail_app_password: str = ""
    
    # Super User Credentials
    super_user_email: str = ""
    super_user_password: str = ""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not self.jwt_secret:
            self.jwt_secret = self.secret_key

        if not self.deployed_url:
            self.deployed_url = os.getenv(
                "VERCEL_PROJECT_PRODUCTION_URL",
                os.getenv("VERCEL_URL", "localhost:8000")
            )
        
        if not self.app_url:
            self.app_url = self.base_url
        
        if not self.facebook_redirect_uri:
            self.facebook_redirect_uri = f"{self.app_url}/facebook/auth/callback"

        if not self.instagram_redirect_uri:
            self.instagram_redirect_uri = f"{self.app_url}/instagram/auth/callback"

        if not self.tiktok_redirect_uri:
            self.tiktok_redirect_uri = f"{self.app_url}/tiktok/auth/callback"
    
    @property
    def base_url(self) -> str:
        """Construct proper base URL with protocol"""
        url = self.deployed_url or "localhost:8000"
        
        if "localhost" in url:
            return f"http://{url}"
        return f"https://{url}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
