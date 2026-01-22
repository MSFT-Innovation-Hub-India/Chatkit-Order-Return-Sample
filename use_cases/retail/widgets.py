"""
ChatKit Widgets for Retail Order Returns Use Case.

Generates rich UI components for the returns flow including:
- Customer profile cards
- Order summaries
- Return item selection
- Reason selection
- Resolution options
- Return confirmation
"""

from typing import Any, Dict, List, Optional


def create_customer_card(customer: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a customer profile card widget.
    
    Shows customer info with their membership tier badge.
    """
    tier = customer.get("tier", "Standard")
    tier_colors = {
        "Standard": "#6B7280",  # Gray
        "Silver": "#9CA3AF",    # Silver
        "Gold": "#F59E0B",      # Gold
        "Platinum": "#8B5CF6",  # Purple
    }
    
    return {
        "type": "card",
        "title": f"👤 {customer.get('name', 'Customer')}",
        "content": {
            "type": "customer_profile",
            "data": {
                "id": customer.get("id", ""),
                "name": customer.get("name", ""),
                "email": customer.get("email", ""),
                "phone": customer.get("phone", ""),
                "tier": tier,
                "tier_color": tier_colors.get(tier, "#6B7280"),
                "member_since": customer.get("member_since", ""),
            },
        },
        "metadata": {"customer_id": customer.get("id", "")},
    }


def create_customer_selection_widget(customers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a widget for selecting from multiple matching customers.
    """
    return {
        "type": "selection",
        "title": "🔍 Multiple Customers Found",
        "description": "Please select the correct customer:",
        "options": [
            {
                "id": c.get("id", ""),
                "label": c.get("name", ""),
                "sublabel": c.get("email", ""),
                "action": {
                    "type": "select_customer",
                    "customer_id": c.get("id", ""),
                },
            }
            for c in customers
        ],
    }


def create_orders_list_widget(orders: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a widget showing customer's orders.
    """
    return {
        "type": "list",
        "title": "📦 Your Orders",
        "items": [
            {
                "id": order.get("id", ""),
                "title": f"Order {order.get('id', '')}",
                "subtitle": f"{order.get('order_date', '')[:10]} • {order.get('status', '').title()}",
                "details": [
                    f"{item.get('name', '')} (x{item.get('quantity', 1)})"
                    for item in order.get("items", [])
                ],
                "total": f"${order.get('total', 0):.2f}",
                "status": order.get("status", ""),
            }
            for order in orders
        ],
    }


def create_returnable_items_widget(orders: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a widget for selecting items to return.
    
    Shows items with their return eligibility and days remaining.
    """
    items = []
    for order in orders:
        for item in order.get("items", []):
            days = item.get("days_remaining", 0)
            urgency = "🟢" if days > 14 else "🟡" if days > 7 else "🔴"
            
            items.append({
                "id": f"{order.get('id', '')}|{item.get('product_id', '')}",
                "order_id": order.get("id", ""),
                "product_id": item.get("product_id", ""),
                "name": item.get("name", ""),
                "quantity": item.get("quantity", 1),
                "unit_price": item.get("unit_price", 0),
                "days_remaining": days,
                "urgency_indicator": urgency,
                "deadline": item.get("deadline", ""),
                "action": {
                    "type": "select_return_item",
                    "order_id": order.get("id", ""),
                    "product_id": item.get("product_id", ""),
                    "name": item.get("name", ""),
                    "unit_price": item.get("unit_price", 0),
                },
            })
    
    return {
        "type": "item_selector",
        "title": "🔄 Select Items to Return",
        "description": "Choose the items you'd like to return. Items are listed with their return deadline.",
        "items": items,
        "allow_multiple": True,
    }


def create_return_reasons_widget(reasons: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a widget for selecting return reason.
    """
    # Group reasons by category
    icons = {
        "DEFECTIVE": "🔧",
        "DAMAGED": "📦",
        "WRONG_ITEM": "❌",
        "WRONG_SIZE": "📏",
        "NOT_AS_DESCRIBED": "📝",
        "CHANGED_MIND": "💭",
        "OTHER": "❓",
    }
    
    return {
        "type": "option_selector",
        "title": "❓ Reason for Return",
        "description": "Please select the reason for your return:",
        "options": [
            {
                "code": r.get("code", ""),
                "label": r.get("label", ""),
                "description": r.get("description", ""),
                "icon": icons.get(r.get("code", ""), "📋"),
                "requires_details": r.get("requires_details", False),
                "action": {
                    "type": "select_reason",
                    "reason_code": r.get("code", ""),
                    "requires_details": r.get("requires_details", False),
                },
            }
            for r in reasons
        ],
    }


def create_resolution_options_widget(
    options: List[Dict[str, Any]],
    refund_amount: float,
    customer_tier: str = "Standard",
) -> Dict[str, Any]:
    """
    Create a widget for selecting return resolution.
    """
    icons = {
        "refund": "💰",
        "exchange": "🔄",
        "store_credit": "🎁",
        "keep_item": "📦",
    }
    
    # Add bonus for store credit
    store_credit_bonus = 0.10 if customer_tier in ["Gold", "Platinum"] else 0.05
    
    enhanced_options = []
    for opt in options:
        option = {
            "code": opt.get("code", ""),
            "label": opt.get("label", ""),
            "description": opt.get("description", ""),
            "processing_time": opt.get("processing_time", ""),
            "icon": icons.get(opt.get("code", ""), "✓"),
            "action": {
                "type": "select_resolution",
                "resolution": opt.get("code", ""),
            },
        }
        
        # Add amounts for refund and store credit
        if opt.get("code") == "refund":
            option["amount"] = refund_amount
            option["amount_display"] = f"${refund_amount:.2f}"
        elif opt.get("code") == "store_credit":
            bonus_amount = refund_amount * (1 + store_credit_bonus)
            option["amount"] = bonus_amount
            option["amount_display"] = f"${bonus_amount:.2f}"
            option["bonus"] = f"+{int(store_credit_bonus * 100)}% bonus"
        
        enhanced_options.append(option)
    
    return {
        "type": "resolution_selector",
        "title": "💳 Choose Your Resolution",
        "description": "How would you like to resolve this return?",
        "options": enhanced_options,
        "highlight": "store_credit",  # Recommend store credit
    }


def create_shipping_options_widget(options: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a widget for selecting return shipping method.
    """
    icons = {
        "prepaid_label": "📧",
        "drop_off": "🏪",
        "scheduled_pickup": "🚚",
        "keep_item": "🏠",
    }
    
    return {
        "type": "shipping_selector",
        "title": "📬 Return Shipping Method",
        "description": "How would you like to return the item?",
        "options": [
            {
                "code": opt.get("code", ""),
                "label": opt.get("label", ""),
                "description": opt.get("description", ""),
                "cost": opt.get("cost", 0),
                "cost_display": "Free" if opt.get("cost", 0) == 0 else f"${opt.get('cost', 0):.2f}",
                "icon": icons.get(opt.get("code", ""), "📦"),
                "action": {
                    "type": "select_shipping",
                    "shipping_method": opt.get("code", ""),
                },
            }
            for opt in options
        ],
    }


def create_retention_offer_widget(
    offers: List[Dict[str, Any]],
    customer_tier: str,
    item_name: str,
) -> Dict[str, Any]:
    """
    Create a widget showing retention offers for customers who changed their mind.
    """
    return {
        "type": "offer_card",
        "title": "🎁 Special Offer Just for You!",
        "description": f"We'd love for you to keep your {item_name}. As a {customer_tier} member, here are some exclusive offers:",
        "offers": [
            {
                "code": offer.get("code", ""),
                "label": offer.get("label", ""),
                "description": offer.get("description", ""),
                "discount": f"{offer.get('discount_percent', 0)}% off",
                "action": {
                    "type": "accept_offer",
                    "offer_code": offer.get("code", ""),
                },
            }
            for offer in offers
        ],
        "decline_action": {
            "type": "decline_offers",
            "label": "No thanks, continue with return",
        },
    }


def create_return_summary_widget(
    return_data: Dict[str, Any],
    customer: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a summary widget before final confirmation.
    """
    items = return_data.get("items", [])
    total = sum(item.get("unit_price", 0) * item.get("quantity", 1) for item in items)
    
    return {
        "type": "summary_card",
        "title": "📋 Return Summary",
        "sections": [
            {
                "title": "Customer",
                "content": customer.get("name", ""),
            },
            {
                "title": "Order",
                "content": return_data.get("order_id", ""),
            },
            {
                "title": "Items",
                "items": [
                    f"{item.get('name', '')} (x{item.get('quantity', 1)}) - ${item.get('unit_price', 0):.2f}"
                    for item in items
                ],
            },
            {
                "title": "Reason",
                "content": return_data.get("reason_label", return_data.get("reason_code", "")),
            },
            {
                "title": "Resolution",
                "content": return_data.get("resolution", "").replace("_", " ").title(),
            },
            {
                "title": "Shipping",
                "content": return_data.get("shipping_method", "").replace("_", " ").title(),
            },
        ],
        "total": {
            "label": "Refund Amount",
            "amount": f"${return_data.get('refund_amount', total):.2f}",
        },
        "actions": [
            {
                "type": "confirm_return",
                "label": "✅ Confirm Return",
                "style": "primary",
            },
            {
                "type": "cancel_return",
                "label": "Cancel",
                "style": "secondary",
            },
        ],
    }


def create_return_confirmation_widget(
    return_result: Dict[str, Any],
    shipping_method: str = "prepaid_label",
) -> Dict[str, Any]:
    """
    Create a confirmation widget after return is created.
    """
    return_id = return_result.get("return_id", "")
    refund_amount = return_result.get("refund_amount", 0)
    
    # Different next steps based on shipping method
    next_steps = {
        "prepaid_label": [
            "📧 A prepaid shipping label has been sent to your email",
            "📦 Pack the item securely in its original packaging if possible",
            "🏪 Drop off at any UPS or FedEx location",
            "⏱️ Refund will be processed within 3-5 business days after we receive the item",
        ],
        "drop_off": [
            "🏪 Visit any of our partner locations to drop off your return",
            "📱 Show this return ID at the counter",
            "⏱️ Refund will be processed within 3-5 business days",
        ],
        "scheduled_pickup": [
            "🚚 A pickup has been scheduled for the next business day",
            "📦 Have the item ready and packaged",
            "⏱️ Refund will be processed within 3-5 business days after pickup",
        ],
        "keep_item": [
            "🎁 You can keep the item!",
            "💰 Your refund will be processed within 1-2 business days",
            "🙏 Thank you for your patience with this issue",
        ],
    }
    
    return {
        "type": "confirmation_card",
        "title": "✅ Return Created Successfully!",
        "return_id": return_id,
        "status": "Pending",
        "refund_amount": f"${refund_amount:.2f}",
        "next_steps": next_steps.get(shipping_method, next_steps["prepaid_label"]),
        "tracking": {
            "enabled": shipping_method != "keep_item",
            "message": "You'll receive tracking updates via email",
        },
        "actions": [
            {
                "type": "view_return_status",
                "label": "📍 Track Return Status",
                "return_id": return_id,
            },
            {
                "type": "contact_support",
                "label": "💬 Contact Support",
            },
        ],
    }


def create_error_widget(message: str, suggestions: List[str] = None) -> Dict[str, Any]:
    """
    Create an error widget with helpful suggestions.
    """
    return {
        "type": "error_card",
        "title": "⚠️ Unable to Process",
        "message": message,
        "suggestions": suggestions or [
            "Try searching with a different term",
            "Contact customer support for assistance",
        ],
        "actions": [
            {
                "type": "retry",
                "label": "🔄 Try Again",
            },
            {
                "type": "contact_support",
                "label": "💬 Get Help",
            },
        ],
    }


def create_return_history_widget(returns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a widget showing customer's return history.
    """
    status_colors = {
        "pending": "#F59E0B",    # Yellow
        "approved": "#10B981",   # Green
        "completed": "#6B7280",  # Gray
        "rejected": "#EF4444",   # Red
    }
    
    return {
        "type": "history_list",
        "title": "📜 Return History",
        "items": [
            {
                "id": r.get("id", ""),
                "order_id": r.get("order_id", ""),
                "status": r.get("status", "pending"),
                "status_color": status_colors.get(r.get("status", "pending"), "#6B7280"),
                "reason": r.get("reason", ""),
                "created_at": r.get("created_at", "")[:10] if r.get("created_at") else "",
                "refund_amount": f"${r.get('refund_amount', 0):.2f}",
            }
            for r in returns
        ],
        "summary": {
            "total_returns": len(returns),
            "message": f"You have made {len(returns)} return(s) in the past",
        },
    }


# =============================================================================
# WIDGET SERIALIZATION FOR CHATKIT
# =============================================================================

def serialize_widget_for_chatkit(widget: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a widget for ChatKit's UI data format.
    
    ChatKit expects widgets in a specific format for rendering.
    """
    return {
        "widget": widget.get("type", "card"),
        "data": widget,
    }


def create_action_buttons(actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create action buttons that trigger onClickAction in ChatKit.
    """
    return {
        "type": "action_buttons",
        "buttons": [
            {
                "id": action.get("type", "action"),
                "label": action.get("label", "Action"),
                "style": action.get("style", "primary"),
                "action": action,
            }
            for action in actions
        ],
    }
