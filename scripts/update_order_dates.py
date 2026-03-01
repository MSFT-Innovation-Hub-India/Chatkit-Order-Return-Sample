"""
Update order dates in Cosmos DB to be recent (within return window).

This makes sample orders eligible for returns by setting order_date
to recent dates and status to 'delivered'.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from shared.cosmos_config import COSMOS_ENDPOINT, DATABASE_NAME, RETAIL_CONTAINER_NAMES


def main():
    credential = DefaultAzureCredential(
        exclude_interactive_browser_credential=False,
        exclude_shared_token_cache_credential=False,
    )
    client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
    database = client.get_database_client(DATABASE_NAME)
    container = database.get_container_client(RETAIL_CONTAINER_NAMES["orders"])

    # Query all orders
    orders = list(container.query_items(
        "SELECT * FROM c",
        enable_cross_partition_query=True,
    ))

    now = datetime.now(timezone.utc)
    print(f"Found {len(orders)} orders. Updating dates...")

    for i, order in enumerate(orders):
        # Spread orders across the last 1-10 days
        days_ago = (i % 10) + 1
        new_date = (now - timedelta(days=days_ago)).isoformat()

        order["order_date"] = new_date
        # Ensure status allows returns
        if order.get("status") not in ("delivered", "shipped"):
            order["status"] = "delivered"

        container.upsert_item(order)
        print(f"  Updated {order['id']}: order_date={new_date}, status={order['status']}")

    print("Done! All orders are now within the 30-day return window.")


if __name__ == "__main__":
    main()
