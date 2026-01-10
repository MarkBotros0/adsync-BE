"""
Application configuration module
Load environment variables and provide settings
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application Settings (required)
    app_url: str
    
    # Facebook OAuth Configuration
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_redirect_uri: str = ""
    
    # Application Settings
    secret_key: str = "dev-secret-key-change-in-production"
    
    # Facebook API Version
    facebook_api_version: str = "v24.0"
    
    # Session Storage (memory, redis, or postgresql)
    session_storage: str = "postgresql"
    
    # PostgreSQL Database URL
    database_url: str = "postgresql://postgres:password@localhost:5432/adsync_db"
    
    # Redis Configuration (optional, only if using redis)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-generate redirect URI if not provided
        if not self.facebook_redirect_uri:
            self.facebook_redirect_uri = f"{self.app_url}/facebook/auth/callback"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
