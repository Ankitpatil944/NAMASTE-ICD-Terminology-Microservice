"""
Configuration management for NAMASTE ICD Service.

Uses Pydantic Settings for environment variable management with validation.
"""

from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database configuration
    database_url: str = Field(
        default="sqlite:///./namaste.db",
        description="Database connection URL"
    )
    
    # WHO ICD-11 API configuration
    icd11_client_id: Optional[str] = Field(
        default=None,
        description="WHO ICD-11 API client ID"
    )
    icd11_client_secret: Optional[str] = Field(
        default=None,
        description="WHO ICD-11 API client secret"
    )
    
    # ABHA authentication configuration
    abha_introspection_url: Optional[str] = Field(
        default=None,
        description="ABHA token introspection endpoint URL"
    )
    
    # Application settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # API settings
    max_search_results: int = Field(
        default=100,
        description="Maximum number of search results to return"
    )
    default_search_limit: int = Field(
        default=10,
        description="Default limit for search queries"
    )
    
    # Security settings
    allowed_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings
