"""
Retail Customer Service Use Case.

This module provides the complete ChatKit implementation for 
retail order management and returns scenario.

Components:
- RetailChatKitServer: Main ChatKit server for the returns flow
- RetailCosmosClient: Cosmos DB data access
- RETAIL_TOOLS: AI function tools for the returns process
- Widgets: Rich UI components for the returns flow

Sample Data includes:
- Customers with membership tiers
- Products with return eligibility
- Orders with various statuses
- Return reasons and resolutions
- Discount/retention offers

Usage:
    from use_cases.retail import RetailChatKitServer
    
    server = RetailChatKitServer()
    # Use with FastAPI or other ASGI framework
"""

# Import the main server
from use_cases.retail.server import RetailChatKitServer

# Import Cosmos client
from use_cases.retail.cosmos_client import RetailCosmosClient, get_retail_client

# Import Cosmos DB store for ChatKit thread persistence
from use_cases.retail.cosmos_store import CosmosDBStore

# Import tools
from use_cases.retail.tools import RETAIL_TOOLS, execute_tool

__all__ = [
    # Server
    "RetailChatKitServer",
    # Cosmos client and store
    "RetailCosmosClient",
    "get_retail_client",
    "CosmosDBStore",
    # Tools
    "RETAIL_TOOLS",
    "execute_tool",
]
