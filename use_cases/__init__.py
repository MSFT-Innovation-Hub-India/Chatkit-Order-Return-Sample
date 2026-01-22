"""
Use Cases Package.

This package contains modular use case implementations for the ChatKit server.
Each use case is a self-contained module with its own:
- Agent and tools
- Widget builders
- Action handlers
- Store extensions (if needed)

Available use cases:
- retail: Order returns management with interactive widgets

To add new use cases, see docs/ADDING_USE_CASES.md
"""

# Re-export commonly used items from the retail use case
from use_cases.retail import (
    RetailChatKitServer,
    RetailCosmosClient,
    CosmosDBStore,
    RETAIL_TOOLS,
)

__all__ = [
    # Retail
    "RetailChatKitServer",
    "RetailCosmosClient",
    "CosmosDBStore",
    "RETAIL_TOOLS",
]

