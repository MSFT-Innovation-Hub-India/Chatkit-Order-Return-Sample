"""
Cosmos DB Data Population Script for Order Returns Application.

Populates sample retail data into Azure Cosmos DB using DefaultAzureCredential.

Usage:
    python scripts/populate_cosmosdb.py

Environment:
    COSMOS_ENDPOINT - Override the default Cosmos DB endpoint
    COSMOS_DATABASE - Override the default database name

Containers Required:
    
    RETAIL DATA CONTAINERS (populated with sample data):
    - Retail_Products        (partition: /id)
    - Retail_Customers       (partition: /id)
    - Retail_Orders          (partition: /id)
    - Retail_ReturnReasons   (partition: /code)
    - Retail_ResolutionOptions (partition: /code)
    - Retail_ShippingOptions (partition: /code)
    - Retail_DiscountOffers  (partition: /code)
    - Retail_Returns         (partition: /id)
    - Retail_CustomerNotes   (partition: /customer_id)
    - Retail_DemoScenarios   (partition: /name)
    
    CHATKIT CONTAINERS (created empty, populated at runtime):
    - ChatKit_Threads        (partition: /id) - Conversation thread metadata
    - ChatKit_Items          (partition: /thread_id) - Messages and widgets
    - ChatKit_Feedback       (partition: /thread_id) - User feedback (thumbs up/down)
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceExistsError, CosmosHttpResponseError
from azure.identity import AzureCliCredential

# Import configuration from shared module
from shared.cosmos_config import (
    COSMOS_ENDPOINT,
    DATABASE_NAME,
    RETAIL_CONTAINERS,
    CHATKIT_CONTAINERS,
)

# Import sample data
from data.sample.retail_data import (
    PRODUCTS,
    CUSTOMERS,
    ORDERS,
    RETURN_REASONS,
    RESOLUTION_OPTIONS,
    RETURN_SHIPPING_OPTIONS,
    DISCOUNT_OFFERS,
    EXISTING_RETURNS,
    CUSTOMER_NOTES,
    DEMO_SCENARIOS,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# DATA PREPARATION
# =============================================================================

def prepare_products() -> List[Dict[str, Any]]:
    """Prepare products for Cosmos DB (ensure 'id' field exists)."""
    items = []
    for p in PRODUCTS:
        item = p.copy()
        item["id"] = p["id"]
        items.append(item)
    return items


def prepare_customers() -> List[Dict[str, Any]]:
    """Prepare customers for Cosmos DB."""
    items = []
    for c in CUSTOMERS:
        item = c.copy()
        item["id"] = c["id"]
        items.append(item)
    return items


def prepare_orders() -> List[Dict[str, Any]]:
    """Prepare orders for Cosmos DB."""
    items = []
    for o in ORDERS:
        item = o.copy()
        item["id"] = o["id"]
        items.append(item)
    return items


def prepare_return_reasons() -> List[Dict[str, Any]]:
    """Prepare return reasons for Cosmos DB."""
    items = []
    for r in RETURN_REASONS:
        item = r.copy()
        item["id"] = r["code"]
        items.append(item)
    return items


def prepare_resolution_options() -> List[Dict[str, Any]]:
    """Prepare resolution options for Cosmos DB."""
    items = []
    for r in RESOLUTION_OPTIONS:
        item = r.copy()
        item["id"] = r["code"]
        items.append(item)
    return items


def prepare_shipping_options() -> List[Dict[str, Any]]:
    """Prepare shipping options for Cosmos DB."""
    items = []
    for s in RETURN_SHIPPING_OPTIONS:
        item = s.copy()
        item["id"] = s["code"]
        items.append(item)
    return items


def prepare_discount_offers() -> List[Dict[str, Any]]:
    """Prepare discount offers for Cosmos DB."""
    items = []
    for d in DISCOUNT_OFFERS:
        item = d.copy()
        item["id"] = d["code"]
        items.append(item)
    return items


def prepare_returns() -> List[Dict[str, Any]]:
    """Prepare existing returns for Cosmos DB."""
    items = []
    for r in EXISTING_RETURNS:
        item = r.copy()
        item["id"] = r["id"]
        items.append(item)
    return items


def prepare_customer_notes() -> List[Dict[str, Any]]:
    """Prepare customer notes for Cosmos DB."""
    items = []
    for i, n in enumerate(CUSTOMER_NOTES):
        item = n.copy()
        item["id"] = f"{n['customer_id']}-note-{i+1}"
        items.append(item)
    return items


def prepare_demo_scenarios() -> List[Dict[str, Any]]:
    """Prepare demo scenarios for Cosmos DB."""
    items = []
    for s in DEMO_SCENARIOS:
        item = s.copy()
        item["id"] = s["name"].lower().replace(" ", "-").replace("---", "-")
        items.append(item)
    return items


# =============================================================================
# COSMOS DB OPERATIONS
# =============================================================================

def upsert_items(container, items: List[Dict[str, Any]]) -> int:
    """Upsert items into a container."""
    count = 0
    for item in items:
        try:
            container.upsert_item(item)
            count += 1
        except Exception as e:
            logger.error(f"Failed to upsert item {item.get('id')}: {e}")
    return count


def main():
    """Main function to populate Cosmos DB with retail sample data."""
    logger.info("=" * 60)
    logger.info("Order Returns - Cosmos DB Population Script")
    logger.info("=" * 60)
    logger.info(f"Endpoint: {COSMOS_ENDPOINT}")
    logger.info(f"Database: {DATABASE_NAME}")
    logger.info("Authentication: AzureCliCredential")
    logger.info("=" * 60)

    # Create credential and client using Azure CLI credential
    logger.info("\nAuthenticating with Azure CLI...")
    credential = AzureCliCredential()
    
    client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
    
    # Get database
    logger.info(f"Connecting to database '{DATABASE_NAME}'...")
    try:
        database = client.get_database_client(DATABASE_NAME)
        database.read()
        logger.info(f"Database '{DATABASE_NAME}' found")
    except CosmosHttpResponseError as e:
        logger.error(f"Database '{DATABASE_NAME}' not found or access denied: {e}")
        logger.error("Please create the database first or check RBAC permissions")
        return

    # Data to populate
    data_sets = [
        ("products", prepare_products()),
        ("customers", prepare_customers()),
        ("orders", prepare_orders()),
        ("return_reasons", prepare_return_reasons()),
        ("resolution_options", prepare_resolution_options()),
        ("shipping_options", prepare_shipping_options()),
        ("discount_offers", prepare_discount_offers()),
        ("returns", prepare_returns()),
        ("customer_notes", prepare_customer_notes()),
        ("demo_scenarios", prepare_demo_scenarios()),
    ]

    # Container info - Retail (populated with sample data)
    logger.info("\n--- Retail Data Containers (pre-created via Azure CLI) ---")
    for key, (container_name, partition_key) in RETAIL_CONTAINERS.items():
        logger.info(f"  {container_name} (partition: {partition_key})")
    
    # Container info - ChatKit (created empty, populated at runtime)
    logger.info("\n--- ChatKit Containers (no sample data, populated at runtime) ---")
    chatkit_partition_keys = {
        "threads": "/id",
        "items": "/thread_id", 
        "feedback": "/thread_id",
    }
    for key, container_name in CHATKIT_CONTAINERS.items():
        pk = chatkit_partition_keys.get(key, "/id")
        logger.info(f"  {container_name} (partition: {pk})")

    logger.info("\n--- Populating Retail Data ---")
    total_items = 0
    for key, items in data_sets:
        container_name, _ = RETAIL_CONTAINERS[key]
        container = database.get_container_client(container_name)
        count = upsert_items(container, items)
        logger.info(f"  {container_name}: {count} items")
        total_items += count

    logger.info("\n" + "=" * 60)
    logger.info(f"COMPLETE: {total_items} total items populated across {len(RETAIL_CONTAINERS)} retail containers")
    logger.info(f"ChatKit containers ({len(CHATKIT_CONTAINERS)}) are created empty and populated at runtime")
    logger.info("=" * 60)
    
    # Print Azure CLI commands for creating all containers
    logger.info("\n--- Azure CLI Commands to Create All Containers ---")
    logger.info("# If containers don't exist, run these commands:")
    logger.info("")
    logger.info("# Retail containers:")
    for key, (container_name, partition_key) in RETAIL_CONTAINERS.items():
        logger.info(f'az cosmosdb sql container create --account-name "common-nosql-db" --database-name "{DATABASE_NAME}" --name "{container_name}" --partition-key-path "{partition_key}" --resource-group "common-svc-rg"')
    logger.info("")
    logger.info("# ChatKit containers:")
    for key, container_name in CHATKIT_CONTAINERS.items():
        pk = chatkit_partition_keys.get(key, "/id")
        logger.info(f'az cosmosdb sql container create --account-name "common-nosql-db" --database-name "{DATABASE_NAME}" --name "{container_name}" --partition-key-path "{pk}" --resource-group "common-svc-rg"')


if __name__ == "__main__":
    main()
