"""
Azure Cosmos DB Configuration.

Centralized configuration for all Cosmos DB settings used across the application.
This ensures consistency between the application, scripts, and data population tools.

Environment Variables (optional overrides):
    COSMOS_ENDPOINT - Override the default Cosmos DB endpoint
    COSMOS_DATABASE - Override the default database name
"""

import os

# =============================================================================
# COSMOS DB CONNECTION
# =============================================================================

COSMOS_ENDPOINT = os.getenv(
    "COSMOS_ENDPOINT",
    "https://common-nosql-db.documents.azure.com:443/"
)

DATABASE_NAME = os.getenv(
    "COSMOS_DATABASE",
    "db001"
)

# =============================================================================
# RETAIL DATA CONTAINERS
# =============================================================================

# Container names for retail order returns data
# Format: logical_name -> (container_name, partition_key_path)
RETAIL_CONTAINERS = {
    "products": ("Retail_Products", "/id"),
    "customers": ("Retail_Customers", "/id"),
    "orders": ("Retail_Orders", "/id"),
    "return_reasons": ("Retail_ReturnReasons", "/code"),
    "resolution_options": ("Retail_ResolutionOptions", "/code"),
    "shipping_options": ("Retail_ShippingOptions", "/code"),
    "discount_offers": ("Retail_DiscountOffers", "/code"),
    "returns": ("Retail_Returns", "/id"),
    "customer_notes": ("Retail_CustomerNotes", "/customer_id"),
    "demo_scenarios": ("Retail_DemoScenarios", "/name"),
}

# Simple container name lookup (without partition key)
RETAIL_CONTAINER_NAMES = {
    key: name for key, (name, _) in RETAIL_CONTAINERS.items()
}

# =============================================================================
# CHATKIT THREAD STORAGE CONTAINERS
# =============================================================================

# Container names for ChatKit thread/conversation storage
CHATKIT_CONTAINERS = {
    "threads": "ChatKit_Threads",
    "items": "ChatKit_Items",
    "feedback": "ChatKit_Feedback",  # User feedback on assistant responses
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_retail_container_name(logical_name: str) -> str:
    """Get the actual container name for a logical retail container name."""
    if logical_name in RETAIL_CONTAINER_NAMES:
        return RETAIL_CONTAINER_NAMES[logical_name]
    return logical_name


def get_retail_container_config(logical_name: str) -> tuple:
    """Get (container_name, partition_key_path) for a retail container."""
    if logical_name in RETAIL_CONTAINERS:
        return RETAIL_CONTAINERS[logical_name]
    raise ValueError(f"Unknown retail container: {logical_name}")
