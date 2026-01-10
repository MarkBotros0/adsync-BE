"""
Application configuration module
Load environment variables and provide settings
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Vercel Deployment URL (auto-detected)
    deployed_url: str = ""
    
    # Application URL (can be overridden)
    app_url: str = ""
    
    # Facebook OAuth Configuration
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_redirect_uri: str = ""
    
    # Application Settings
    secret_key: str
    
    # Facebook API Version
    facebook_api_version: str = "v24.0"
    
    # Session Storage (memory or postgresql)
    session_storage: str
    
    # PostgreSQL Database URL
    database_url: str
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        if not self.deployed_url:
            self.deployed_url = os.getenv(
                "VERCEL_PROJECT_PRODUCTION_URL",
                os.getenv("VERCEL_URL", "localhost:8000")
            )
        
        if not self.app_url:
            self.app_url = self.base_url
        
        if not self.facebook_redirect_uri:
            self.facebook_redirect_uri = f"{self.app_url}/facebook/auth/callback"
    
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
