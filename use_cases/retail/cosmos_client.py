"""
Cosmos DB Client for Retail Use Case.

Provides data access methods for the retail order returns flow.
Uses DefaultAzureCredential for flexible authentication.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

# Import shared configuration
from shared.cosmos_config import (
    COSMOS_ENDPOINT,
    DATABASE_NAME,
    RETAIL_CONTAINER_NAMES,
)

logger = logging.getLogger(__name__)


class RetailCosmosClient:
    """Client for accessing retail data in Cosmos DB."""

    def __init__(self):
        """Initialize the Cosmos DB client."""
        logger.info("Initializing Retail Cosmos DB client...")
        self._credential = DefaultAzureCredential(
            exclude_interactive_browser_credential=False,
            exclude_shared_token_cache_credential=False,
        )
        self._client = CosmosClient(COSMOS_ENDPOINT, credential=self._credential)
        self._database = self._client.get_database_client(DATABASE_NAME)
        self._containers = {}
        logger.info("Retail Cosmos DB client initialized")

    def _get_container(self, name: str):
        """Get a container client, caching for reuse."""
        if name not in self._containers:
            container_name = RETAIL_CONTAINER_NAMES.get(name, name)
            self._containers[name] = self._database.get_container_client(container_name)
        return self._containers[name]

    # =========================================================================
    # CUSTOMER OPERATIONS
    # =========================================================================

    def get_customer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Look up a customer by email address."""
        container = self._get_container("customers")
        query = "SELECT * FROM c WHERE c.email = @email"
        params = [{"name": "@email", "value": email}]
        
        items = list(container.query_items(query, parameters=params, enable_cross_partition_query=True))
        return items[0] if items else None

    def get_customer_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Look up a customer by name (case-insensitive partial match)."""
        container = self._get_container("customers")
        query = "SELECT * FROM c WHERE CONTAINS(LOWER(c.name), LOWER(@name))"
        params = [{"name": "@name", "value": name}]
        
        items = list(container.query_items(query, parameters=params, enable_cross_partition_query=True))
        return items[0] if items else None

    def get_customer_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Look up a customer by ID."""
        container = self._get_container("customers")
        try:
            return container.read_item(item=customer_id, partition_key=customer_id)
        except CosmosResourceNotFoundError:
            return None

    def search_customers(self, search_term: str) -> List[Dict[str, Any]]:
        """Search customers by name, email, or phone."""
        container = self._get_container("customers")
        # Handle both combined "name" field and separate "first_name"/"last_name" fields
        query = """
            SELECT * FROM c 
            WHERE CONTAINS(LOWER(c.name), LOWER(@term))
               OR CONTAINS(LOWER(c.first_name), LOWER(@term))
               OR CONTAINS(LOWER(c.last_name), LOWER(@term))
               OR CONTAINS(LOWER(c.email), LOWER(@term))
               OR CONTAINS(c.phone, @term)
        """
        params = [{"name": "@term", "value": search_term}]
        
        return list(container.query_items(query, parameters=params, enable_cross_partition_query=True))

    # =========================================================================
    # ORDER OPERATIONS
    # =========================================================================

    def get_orders_for_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all orders for a customer."""
        container = self._get_container("orders")
        query = "SELECT * FROM c WHERE c.customer_id = @customer_id ORDER BY c.order_date DESC"
        params = [{"name": "@customer_id", "value": customer_id}]
        
        return list(container.query_items(query, parameters=params, enable_cross_partition_query=True))

    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific order by ID."""
        container = self._get_container("orders")
        try:
            return container.read_item(item=order_id, partition_key=order_id)
        except CosmosResourceNotFoundError:
            return None

    def get_returnable_orders(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get orders with items that can still be returned (within return window)."""
        orders = self.get_orders_for_customer(customer_id)
        returnable = []
        
        for order in orders:
            if order.get("status") not in ["delivered", "shipped"]:
                continue
            
            returnable_items = []
            for item in order.get("items", []):
                eligibility = self.check_item_return_eligibility(order, item)
                if eligibility["eligible"]:
                    item_copy = item.copy()
                    item_copy["return_eligibility"] = eligibility
                    returnable_items.append(item_copy)
            
            if returnable_items:
                order_copy = order.copy()
                order_copy["returnable_items"] = returnable_items
                returnable.append(order_copy)
        
        return returnable

    def check_item_return_eligibility(
        self, order: Dict[str, Any], item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if an item is eligible for return."""
        try:
            # Get product details
            product = self.get_product_by_id(item.get("product_id", ""))
            if not product:
                # If product not found, assume 30-day return window
                logger.warning(f"Product {item.get('product_id')} not found, using default return window")
                return_window_days = 30
                category = "general"
            else:
                # Check if product category is returnable
                non_returnable = ["underwear", "swimwear", "earrings", "personalized"]
                category = product.get("category", "").lower()
                if category in non_returnable:
                    return {"eligible": False, "reason": f"{category.title()} items cannot be returned"}
                return_window_days = product.get("return_window_days", 30)

            # Check return window - handle various date formats
            order_date_str = order.get("order_date", "")
            try:
                # Handle ISO format with or without timezone
                if "Z" in order_date_str:
                    order_date = datetime.fromisoformat(order_date_str.replace("Z", "+00:00"))
                elif "+" in order_date_str or order_date_str.endswith("00"):
                    order_date = datetime.fromisoformat(order_date_str)
                else:
                    # No timezone - assume UTC
                    order_date = datetime.fromisoformat(order_date_str).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing order date '{order_date_str}': {e}")
                # If we can't parse the date, assume it's recent and eligible
                return {
                    "eligible": True,
                    "days_remaining": 30,
                    "deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                    "return_window_days": return_window_days,
                }

            deadline = order_date + timedelta(days=return_window_days)
            now = datetime.now(timezone.utc)
            
            # Make sure both are timezone-aware for comparison
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            
            if now > deadline:
                return {
                    "eligible": False,
                    "reason": f"Return window expired on {deadline.strftime('%Y-%m-%d')}",
                }

            days_remaining = (deadline - now).days
            return {
                "eligible": True,
                "days_remaining": max(0, days_remaining),
                "deadline": deadline.isoformat(),
                "return_window_days": return_window_days,
            }
        except Exception as e:
            logger.error(f"Error checking return eligibility: {e}")
            # On error, be permissive and allow the return
            return {
                "eligible": True,
                "days_remaining": 30,
                "deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                "return_window_days": 30,
            }

    # =========================================================================
    # PRODUCT OPERATIONS
    # =========================================================================

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a product by ID."""
        container = self._get_container("products")
        try:
            return container.read_item(item=product_id, partition_key=product_id)
        except CosmosResourceNotFoundError:
            return None

    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get all products."""
        container = self._get_container("products")
        return list(container.query_items("SELECT * FROM c", enable_cross_partition_query=True))

    # =========================================================================
    # RETURN OPERATIONS
    # =========================================================================

    def get_return_reasons(self) -> List[Dict[str, Any]]:
        """Get all return reasons."""
        container = self._get_container("return_reasons")
        return list(container.query_items("SELECT * FROM c", enable_cross_partition_query=True))

    def get_resolution_options(self) -> List[Dict[str, Any]]:
        """Get all resolution options."""
        container = self._get_container("resolution_options")
        return list(container.query_items("SELECT * FROM c", enable_cross_partition_query=True))

    def get_shipping_options(self) -> List[Dict[str, Any]]:
        """Get all return shipping options."""
        container = self._get_container("shipping_options")
        return list(container.query_items("SELECT * FROM c", enable_cross_partition_query=True))

    def get_discount_offers(self) -> List[Dict[str, Any]]:
        """Get available discount offers (for retention)."""
        container = self._get_container("discount_offers")
        return list(container.query_items("SELECT * FROM c", enable_cross_partition_query=True))

    def get_returns_for_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all returns for a customer."""
        container = self._get_container("returns")
        query = "SELECT * FROM c WHERE c.customer_id = @customer_id ORDER BY c.created_at DESC"
        params = [{"name": "@customer_id", "value": customer_id}]
        
        return list(container.query_items(query, parameters=params, enable_cross_partition_query=True))

    def create_return(self, return_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new return request."""
        container = self._get_container("returns")
        
        # Generate return ID
        import uuid
        return_id = f"RET-{uuid.uuid4().hex[:8].upper()}"
        
        return_record = {
            "id": return_id,
            "order_id": return_data["order_id"],
            "customer_id": return_data["customer_id"],
            "items": return_data["items"],
            "reason_code": return_data["reason_code"],
            "reason_details": return_data.get("reason_details", ""),
            "resolution": return_data["resolution"],
            "shipping_method": return_data.get("shipping_method", "prepaid_label"),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "refund_amount": return_data.get("refund_amount", 0),
        }
        
        container.create_item(return_record)
        return return_record

    def get_return_by_id(self, return_id: str) -> Optional[Dict[str, Any]]:
        """Get a return by ID."""
        container = self._get_container("returns")
        try:
            return container.read_item(item=return_id, partition_key=return_id)
        except CosmosResourceNotFoundError:
            return None

    # =========================================================================
    # CUSTOMER NOTES
    # =========================================================================

    def get_customer_notes(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get notes for a customer."""
        container = self._get_container("customer_notes")
        query = "SELECT * FROM c WHERE c.customer_id = @customer_id ORDER BY c.created_at DESC"
        params = [{"name": "@customer_id", "value": customer_id}]
        
        return list(container.query_items(query, parameters=params, enable_cross_partition_query=True))

    def add_customer_note(self, customer_id: str, note_type: str, content: str) -> Dict[str, Any]:
        """Add a note to a customer's record."""
        container = self._get_container("customer_notes")
        import uuid
        
        note = {
            "id": f"NOTE-{uuid.uuid4().hex[:8].upper()}",
            "customer_id": customer_id,
            "type": note_type,
            "content": content,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "created_by": "AI Assistant",
        }
        
        container.create_item(note)
        return note

    # =========================================================================
    # NLP TO SQL QUERIES
    # =========================================================================

    def execute_natural_language_query(self, query_type: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a query based on natural language intent.
        
        This is a simplified NLP2SQL implementation that maps intents to queries.
        """
        queries = {
            "find_customer": lambda p: self.search_customers(p.get("search_term", "")),
            "get_orders": lambda p: self.get_orders_for_customer(p.get("customer_id", "")),
            "get_returnable_items": lambda p: self.get_returnable_orders(p.get("customer_id", "")),
            "check_eligibility": lambda p: [self.check_item_return_eligibility(
                self.get_order_by_id(p.get("order_id", "")),
                {"product_id": p.get("product_id", "")}
            )],
            "get_return_reasons": lambda p: self.get_return_reasons(),
            "get_resolution_options": lambda p: self.get_resolution_options(),
            "get_retention_offers": lambda p: self.get_discount_offers(),
            "get_customer_history": lambda p: self.get_returns_for_customer(p.get("customer_id", "")),
        }
        
        if query_type in queries:
            return queries[query_type](params)
        else:
            raise ValueError(f"Unknown query type: {query_type}")


# Singleton instance
_client: Optional[RetailCosmosClient] = None


def get_retail_client() -> RetailCosmosClient:
    """Get the singleton Cosmos DB client instance."""
    global _client
    if _client is None:
        _client = RetailCosmosClient()
    return _client
