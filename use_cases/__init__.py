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
- healthcare: Appointment scheduling (example skeleton for extensibility)

Architecture:
Each use case follows the layered architecture pattern defined in core/:
- domain/: Pure business logic (policies, services)
- data/: Repository pattern for data access
- presentation/: Widget composition
- session.py: Use-case-specific session context
- server.py: ChatKit server extending UseCaseServer
"""

# Re-export commonly used items from the retail use case
from use_cases.retail import (
    RetailChatKitServer,
    RetailCosmosClient,
    CosmosDBStore,
    RETAIL_TOOLS,
)

# Healthcare use case (skeleton for demonstrating extensibility)
from use_cases.healthcare import HealthcareChatKitServer

__all__ = [
    # Retail
    "RetailChatKitServer",
    "RetailCosmosClient",
    "CosmosDBStore",
    "RETAIL_TOOLS",
    # Healthcare
    "HealthcareChatKitServer",
]

