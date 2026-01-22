"""
Azure OpenAI Client Manager.
Provides async Azure OpenAI client with DefaultAzureCredential for managed identity support.
"""

import logging
from typing import Optional
from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from config import settings

logger = logging.getLogger(__name__)


class AzureOpenAIClientManager:
    """
    Singleton manager for AsyncAzureOpenAI client.
    Uses Azure DefaultAzureCredential for secure authentication with:
    - Managed Identity (Azure-hosted environments)
    - Azure CLI credentials (local development)
    - Environment variables
    """
    
    _instance = None
    _client: Optional[AsyncAzureOpenAI] = None
    _credential: Optional[DefaultAzureCredential] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_client(self) -> AsyncAzureOpenAI:
        """Get or create the AsyncAzureOpenAI client."""
        if self._client is None:
            logger.info("Initializing AsyncAzureOpenAI client with DefaultAzureCredential...")
            
            # Create credential for Azure AD authentication
            self._credential = DefaultAzureCredential()
            
            # Create token provider for automatic token refresh
            token_provider = get_bearer_token_provider(
                self._credential,
                "https://cognitiveservices.azure.com/.default"
            )
            
            # Normalize endpoint URL
            azure_endpoint = settings.azure_openai_endpoint
            if azure_endpoint.endswith("/openai/v1"):
                azure_endpoint = azure_endpoint.replace("/openai/v1", "")
            elif azure_endpoint.endswith("/openai/v1/"):
                azure_endpoint = azure_endpoint.replace("/openai/v1/", "")
            if azure_endpoint.endswith("/"):
                azure_endpoint = azure_endpoint[:-1]
            
            self._client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=settings.azure_openai_api_version,
            )
            
            logger.info(f"AsyncAzureOpenAI client initialized: {azure_endpoint}")
        
        return self._client
    
    async def close(self):
        """Close the client connection."""
        if self._client:
            await self._client.close()
            self._client = None


# Global client manager instance
client_manager = AzureOpenAIClientManager()
