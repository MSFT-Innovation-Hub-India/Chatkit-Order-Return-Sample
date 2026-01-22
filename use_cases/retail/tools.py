"""
AI Tools for Retail Order Returns Use Case.

These tools are registered with the Azure OpenAI model to enable
the AI assistant to perform actions in the retail returns flow.
"""

import json
import logging
from typing import Any, Dict, List

from .cosmos_client import get_retail_client

logger = logging.getLogger(__name__)


# =============================================================================
# TOOL DEFINITIONS (for OpenAI function calling)
# =============================================================================

RETAIL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_customer",
            "description": "Look up a customer by name, email, or phone number. Use this when the customer identifies themselves.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "The customer's name, email address, or phone number to search for",
                    },
                },
                "required": ["search_term"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_orders",
            "description": "Get all orders for a customer. Use this after identifying the customer to show their order history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The customer's unique ID (e.g., CUST-1001)",
                    },
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_returnable_items",
            "description": "Get items that are eligible for return for a customer. Shows orders with items still within the return window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The customer's unique ID",
                    },
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_return_eligibility",
            "description": "Check if a specific item from an order can be returned and get the return window details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID containing the item",
                    },
                    "product_id": {
                        "type": "string",
                        "description": "The product ID to check",
                    },
                },
                "required": ["order_id", "product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_return_reasons",
            "description": "Get the list of available return reasons to present to the customer.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_resolution_options",
            "description": "Get available resolution options (refund, exchange, store credit) for a return.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipping_options",
            "description": "Get available return shipping options (prepaid label, drop-off, pickup).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_retention_offers",
            "description": "Get available discount offers to retain a customer who wants to return an item. Use when customer mentions they changed their mind.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The customer's unique ID to check their tier for offers",
                    },
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_return_request",
            "description": "Create a new return request. Use this after collecting all required information from the customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The customer's unique ID",
                    },
                    "order_id": {
                        "type": "string",
                        "description": "The order ID for the return",
                    },
                    "items": {
                        "type": "array",
                        "description": "List of items to return",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "string"},
                                "quantity": {"type": "integer"},
                                "unit_price": {"type": "number"},
                            },
                        },
                    },
                    "reason_code": {
                        "type": "string",
                        "description": "The return reason code (e.g., DEFECTIVE, WRONG_SIZE)",
                    },
                    "reason_details": {
                        "type": "string",
                        "description": "Additional details about the return reason",
                    },
                    "resolution": {
                        "type": "string",
                        "enum": ["refund", "exchange", "store_credit"],
                        "description": "The chosen resolution type",
                    },
                    "shipping_method": {
                        "type": "string",
                        "enum": ["prepaid_label", "drop_off", "scheduled_pickup", "keep_item"],
                        "description": "How the customer will return the item",
                    },
                },
                "required": ["customer_id", "order_id", "items", "reason_code", "resolution"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_return_history",
            "description": "Get the return history for a customer to check patterns or previous issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The customer's unique ID",
                    },
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_refund_amount",
            "description": "Calculate the refund amount for items being returned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "Items to calculate refund for",
                        "items": {
                            "type": "object",
                            "properties": {
                                "unit_price": {"type": "number"},
                                "quantity": {"type": "integer"},
                            },
                        },
                    },
                    "customer_tier": {
                        "type": "string",
                        "enum": ["Standard", "Silver", "Gold", "Platinum"],
                        "description": "Customer's membership tier",
                    },
                    "reason_code": {
                        "type": "string",
                        "description": "The return reason code",
                    },
                },
                "required": ["items"],
            },
        },
    },
]


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

def lookup_customer(search_term: str) -> Dict[str, Any]:
    """Look up a customer by name, email, or phone."""
    try:
        logger.info(f"Looking up customer with term: {search_term}")
        client = get_retail_client()
        customers = client.search_customers(search_term)
        logger.info(f"Found {len(customers)} customers")
        
        if not customers:
            return {"found": False, "message": f"No customer found matching '{search_term}'"}
        
        if len(customers) == 1:
            customer = customers[0]
            # Handle both "name" and "first_name"/"last_name" formats
            if "name" in customer:
                customer_name = customer["name"]
            else:
                first = customer.get("first_name", "")
                last = customer.get("last_name", "")
                customer_name = f"{first} {last}".strip()
            
            result = {
                "found": True,
                "customer": {
                    "id": customer["id"],
                    "name": customer_name,
                    "email": customer.get("email", ""),
                    "phone": customer.get("phone", ""),
                    "tier": customer.get("membership_tier", "Standard"),
                    "member_since": customer.get("member_since", ""),
                },
            }
            logger.info(f"Returning customer: {result}")
            return result
        else:
            # Multiple customers found
            customer_list = []
            for c in customers:
                if "name" in c:
                    cname = c["name"]
                else:
                    cname = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
                customer_list.append({"id": c["id"], "name": cname, "email": c.get("email", "")})
            
            return {
                "found": True,
                "multiple": True,
                "customers": customer_list,
            }
    except Exception as e:
        logger.error(f"Error in lookup_customer: {e}")
        return {"found": False, "error": str(e)}


def get_customer_orders(customer_id: str) -> Dict[str, Any]:
    """Get all orders for a customer."""
    client = get_retail_client()
    orders = client.get_orders_for_customer(customer_id)
    
    if not orders:
        return {"found": False, "message": "No orders found for this customer"}
    
    return {
        "found": True,
        "orders": [
            {
                "id": o["id"],
                "order_date": o["order_date"],
                "status": o["status"],
                "total": o.get("total", 0),
                "items": [
                    {
                        "product_id": item["product_id"],
                        "name": item["name"],
                        "quantity": item["quantity"],
                        "unit_price": item["unit_price"],
                    }
                    for item in o.get("items", [])
                ],
            }
            for o in orders
        ],
    }


def get_returnable_items(customer_id: str) -> Dict[str, Any]:
    """Get items eligible for return."""
    try:
        logger.info(f"Getting returnable items for customer: {customer_id}")
        client = get_retail_client()
        orders = client.get_returnable_orders(customer_id)
        logger.info(f"Found {len(orders)} returnable orders")
        
        if not orders:
            return {"found": False, "message": "No returnable items found. Items may be outside the return window."}
        
        result_orders = []
        for o in orders:
            order_items = []
            for item in o.get("returnable_items", []):
                try:
                    eligibility = item.get("return_eligibility", {})
                    order_items.append({
                        "product_id": item.get("product_id", ""),
                        "name": item.get("name", "Unknown Item"),
                        "quantity": item.get("quantity", 1),
                        "unit_price": item.get("unit_price", 0),
                        "days_remaining": eligibility.get("days_remaining", 30),
                        "deadline": eligibility.get("deadline", ""),
                    })
                except Exception as e:
                    logger.warning(f"Error processing item: {e}")
                    continue
            
            if order_items:
                result_orders.append({
                    "id": o.get("id", ""),
                    "order_date": o.get("order_date", ""),
                    "items": order_items,
                })
        
        logger.info(f"Returning {len(result_orders)} orders with returnable items")
        return {
            "found": True,
            "orders": result_orders,
        }
    except Exception as e:
        logger.error(f"Error in get_returnable_items: {e}")
        return {"found": False, "error": str(e)}


def check_return_eligibility(order_id: str, product_id: str) -> Dict[str, Any]:
    """Check if a specific item can be returned."""
    client = get_retail_client()
    order = client.get_order_by_id(order_id)
    
    if not order:
        return {"eligible": False, "reason": "Order not found"}
    
    item = next((i for i in order.get("items", []) if i["product_id"] == product_id), None)
    if not item:
        return {"eligible": False, "reason": "Item not found in order"}
    
    return client.check_item_return_eligibility(order, item)


def get_return_reasons() -> Dict[str, Any]:
    """Get available return reasons."""
    client = get_retail_client()
    reasons = client.get_return_reasons()
    
    return {
        "reasons": [
            {
                "code": r["code"],
                "label": r["label"],
                "description": r.get("description", ""),
                "requires_details": r.get("requires_details", False),
            }
            for r in reasons
        ]
    }


def get_resolution_options() -> Dict[str, Any]:
    """Get available resolution options."""
    client = get_retail_client()
    options = client.get_resolution_options()
    
    return {
        "options": [
            {
                "code": o["code"],
                "label": o["label"],
                "description": o.get("description", ""),
                "processing_time": o.get("processing_time", ""),
            }
            for o in options
        ]
    }


def get_shipping_options() -> Dict[str, Any]:
    """Get available return shipping options."""
    client = get_retail_client()
    options = client.get_shipping_options()
    
    return {
        "options": [
            {
                "code": o["code"],
                "label": o["label"],
                "description": o.get("description", ""),
                "cost": o.get("cost", 0),
            }
            for o in options
        ]
    }


def get_retention_offers(customer_id: str) -> Dict[str, Any]:
    """Get discount offers for customer retention."""
    client = get_retail_client()
    customer = client.get_customer_by_id(customer_id)
    offers = client.get_discount_offers()
    
    tier = customer.get("membership_tier", "Standard") if customer else "Standard"
    
    # Filter offers based on customer tier
    tier_priority = {"Standard": 1, "Silver": 2, "Gold": 3, "Platinum": 4}
    customer_priority = tier_priority.get(tier, 1)
    
    applicable_offers = []
    for offer in offers:
        min_tier = offer.get("min_tier", "Standard")
        if tier_priority.get(min_tier, 1) <= customer_priority:
            applicable_offers.append({
                "code": offer["code"],
                "label": offer["label"],
                "description": offer.get("description", ""),
                "discount_percent": offer.get("discount_percent", 0),
            })
    
    return {"offers": applicable_offers, "customer_tier": tier}


def create_return_request(
    customer_id: str,
    order_id: str,
    items: List[Dict[str, Any]],
    reason_code: str,
    resolution: str,
    reason_details: str = "",
    shipping_method: str = "prepaid_label",
) -> Dict[str, Any]:
    """Create a new return request."""
    client = get_retail_client()
    
    # Calculate refund amount
    refund_amount = sum(item.get("unit_price", 0) * item.get("quantity", 1) for item in items)
    
    return_data = {
        "customer_id": customer_id,
        "order_id": order_id,
        "items": items,
        "reason_code": reason_code,
        "reason_details": reason_details,
        "resolution": resolution,
        "shipping_method": shipping_method,
        "refund_amount": refund_amount,
    }
    
    result = client.create_return(return_data)
    
    return {
        "success": True,
        "return_id": result["id"],
        "status": result["status"],
        "refund_amount": result["refund_amount"],
        "message": f"Return request {result['id']} created successfully",
    }


def get_customer_return_history(customer_id: str) -> Dict[str, Any]:
    """Get return history for a customer."""
    client = get_retail_client()
    returns = client.get_returns_for_customer(customer_id)
    
    return {
        "returns": [
            {
                "id": r["id"],
                "order_id": r["order_id"],
                "status": r["status"],
                "reason": r.get("reason_code", ""),
                "created_at": r.get("created_at", ""),
                "refund_amount": r.get("refund_amount", 0),
            }
            for r in returns
        ],
        "total_returns": len(returns),
    }


def calculate_refund_amount(
    items: List[Dict[str, Any]],
    customer_tier: str = "Standard",
    reason_code: str = "",
) -> Dict[str, Any]:
    """Calculate the refund amount."""
    subtotal = sum(item.get("unit_price", 0) * item.get("quantity", 1) for item in items)
    
    # Apply restocking fee for certain reasons (unless premium tier)
    restocking_fee = 0
    if reason_code == "CHANGED_MIND" and customer_tier not in ["Gold", "Platinum"]:
        restocking_fee = subtotal * 0.15  # 15% restocking fee
    
    refund_amount = subtotal - restocking_fee
    
    return {
        "subtotal": subtotal,
        "restocking_fee": restocking_fee,
        "refund_amount": refund_amount,
        "note": "Gold and Platinum members are exempt from restocking fees" if restocking_fee > 0 else "",
    }


# =============================================================================
# TOOL EXECUTION
# =============================================================================

TOOL_FUNCTIONS = {
    "lookup_customer": lookup_customer,
    "get_customer_orders": get_customer_orders,
    "get_returnable_items": get_returnable_items,
    "check_return_eligibility": check_return_eligibility,
    "get_return_reasons": get_return_reasons,
    "get_resolution_options": get_resolution_options,
    "get_shipping_options": get_shipping_options,
    "get_retention_offers": get_retention_offers,
    "create_return_request": create_return_request,
    "get_customer_return_history": get_customer_return_history,
    "calculate_refund_amount": calculate_refund_amount,
}


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute a tool and return the result as JSON string."""
    if tool_name not in TOOL_FUNCTIONS:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    
    try:
        result = TOOL_FUNCTIONS[tool_name](**arguments)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return json.dumps({"error": str(e)})
