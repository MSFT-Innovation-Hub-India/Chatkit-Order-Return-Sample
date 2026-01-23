"""
Configuration module for ChatKit Order Returns App.
Loads settings from environment variables with Azure OpenAI support.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Azure OpenAI Configuration
    azure_openai_endpoint: str = Field(
        default="",
        alias="AZURE_OPENAI_ENDPOINT",
        description="Azure OpenAI endpoint URL"
    )
    azure_openai_deployment: str = Field(
        default="gpt-4o",
        alias="AZURE_OPENAI_DEPLOYMENT",
        description="Azure OpenAI deployment name"
    )
    azure_openai_api_version: str = Field(
        default="2025-03-01-preview",
        alias="AZURE_OPENAI_API_VERSION",
        description="Azure OpenAI API version (requires 2025-03-01-preview or later for Responses API)"
    )
    
    # Application Configuration
    app_host: str = Field(
        default="0.0.0.0",
        alias="APP_HOST",
        description="Host to bind the application"
    )
    app_port: int = Field(
        default=8000,
        alias="APP_PORT",
        description="Port to bind the application"
    )
    
    # Data Store Configuration
    data_store_path: str = Field(
        default="./data/chatkit.db",
        alias="DATA_STORE_PATH",
        description="Path to SQLite database file"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level"
    )
    
    # Branding Configuration
    brand_name: str = Field(
        default="Order Returns",
        alias="BRAND_NAME",
        description="Application name shown in header"
    )
    brand_tagline: str = Field(
        default="AI-Powered Returns Management",
        alias="BRAND_TAGLINE",
        description="Tagline shown in header"
    )
    brand_logo_url: str = Field(
        default="/static/logo.svg",
        alias="BRAND_LOGO_URL",
        description="URL to logo image (32x32 recommended)"
    )
    brand_primary_color: str = Field(
        default="#0078d4",
        alias="BRAND_PRIMARY_COLOR",
        description="Primary brand color (hex)"
    )
    brand_favicon_url: str = Field(
        default="/static/favicon.ico",
        alias="BRAND_FAVICON_URL",
        description="URL to favicon"
    )
    
    # Vector Store Configuration for Policy Documents
    policy_docs_vector_store_id: str = Field(
        default="",
        alias="POLICY_DOCS_VECTOR_STORE_ID",
        description="Azure OpenAI Vector Store ID for policy documents (enables RAG for policy questions)"
    )
    policy_search_max_results: int = Field(
        default=3,
        alias="POLICY_SEARCH_MAX_RESULTS",
        description="Maximum number of results to return from policy vector search"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
