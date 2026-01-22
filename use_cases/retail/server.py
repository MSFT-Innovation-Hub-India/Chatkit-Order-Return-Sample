"""
Retail Returns ChatKit Server Implementation.

This is the ChatKit server for the retail order returns use case.
It extends BaseChatKitServer and integrates all retail-specific components.
"""

import json
import logging
from typing import Any, AsyncIterator, Optional
from datetime import datetime, timezone

from chatkit.server import ThreadStreamEvent
from chatkit.store import ThreadMetadata, Page
from chatkit.agents import stream_widget, AgentContext
from chatkit.types import (
    ThreadItemUpdatedEvent, ThreadItemReplacedEvent, ThreadItemAddedEvent,
    ThreadItemDoneEvent, InferenceOptions,
    WidgetItem, WidgetRootUpdated,
    AssistantMessageItem, AssistantMessageContent,
    UserMessageItem, UserMessageTextContent,
)
import uuid
from chatkit.widgets import Card, Text, Box, Button, Row, Badge, Divider, Title, Spacer
from chatkit.actions import ActionConfig

from agents import Agent, function_tool
from agents.run_context import RunContextWrapper

from base_server import BaseChatKitServer
from chatkit.store import Store

# Type alias for the context used by retail tools
RetailContext = AgentContext[Any]

from .tools import (
    lookup_customer,
    get_customer_orders,
    get_returnable_items,
    check_return_eligibility,
    get_return_reasons,
    get_resolution_options,
    get_shipping_options,
    get_retention_offers,
    create_return_request,
    get_customer_return_history,
    calculate_refund_amount,
)

logger = logging.getLogger(__name__)

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

RETAIL_SYSTEM_PROMPT = """You are a helpful customer service assistant for a retail company, specializing in order returns.

Your role is to:
1. Greet customers warmly and ask how you can help
2. Identify the customer by name, email, or phone number
3. Look up their orders and check return eligibility
4. Guide them through the return process step by step
5. Offer alternatives when appropriate (exchanges, store credit with bonus, retention offers)
6. Create the return request and provide confirmation

IMPORTANT GUIDELINES:
- Always be empathetic and helpful
- For "changed mind" returns, offer retention discounts before processing
- Highlight store credit bonus when presenting resolution options
- Gold and Platinum members get fee-free returns - mention this benefit
- If an item is outside the return window, apologize and offer alternatives
- For defective or damaged items, offer expedited processing

FLOW:
1. Greet and ask for customer identification
2. Look up customer using lookup_customer tool
3. Show their returnable items using get_returnable_items tool
4. Let them select items to return
5. Ask for return reason using get_return_reasons tool
6. If reason is "changed mind", offer retention discounts with get_retention_offers
7. Show resolution options using get_resolution_options tool
8. Show shipping options using get_shipping_options tool
9. Summarize and confirm using create_return_request tool
10. Provide confirmation with next steps

Always use the available tools to get real data. Never make up order numbers, prices, or customer information.

SAMPLE CUSTOMERS FOR TESTING:
- Jane Smith (jane.smith@email.com) - Gold member with recent orders
- Bob Johnson (bob.j@email.com) - Silver member  
- Alice Brown - Standard member
- Charlie Davis - Platinum member
- Eve Wilson - Standard member
"""


# =============================================================================
# AGENT TOOLS (wrapped for agents SDK)
# =============================================================================

@function_tool(description_override="Look up a customer by name, email, or phone number. Use this when the customer identifies themselves.")
async def tool_lookup_customer(ctx: RunContextWrapper["RetailContext"], search_term: str) -> str:
    """Look up a customer by name, email, or phone number."""
    result = lookup_customer(search_term)
    
    # Set context flags for widget display
    if result.get("found") and not result.get("multiple"):
        customer = result.get("customer", {})
        customer_id = customer.get("id", "")
        
        ctx.context._show_customer_widget = True
        ctx.context._customer_data = customer
        
        # Also automatically fetch returnable items for a smoother flow
        returnable_result = get_returnable_items(customer_id)
        if returnable_result.get("found"):
            orders = returnable_result.get("orders", [])
            item_count = sum(len(o.get("items", [])) for o in orders)
            ctx.context._show_returnable_items_widget = True
            ctx.context._returnable_items_data = orders
            ctx.context._current_customer_id = customer_id
            return f"Found customer: {customer['name']} ({customer['tier']} member). Customer ID: {customer_id}. They have {item_count} items eligible for return. Please select which item you'd like to return."
        else:
            return f"Found customer: {customer['name']} ({customer['tier']} member). Customer ID: {customer_id}. However, they have no items currently eligible for return."
    elif result.get("multiple"):
        return f"Found multiple customers matching '{search_term}'. Please be more specific with the email or phone number."
    else:
        return result.get("message", "Customer not found")


@function_tool(description_override="Get all orders for a customer. Use this after identifying the customer.")
async def tool_get_customer_orders(ctx: RunContextWrapper["RetailContext"], customer_id: str) -> str:
    """Get all orders for a customer."""
    result = get_customer_orders(customer_id)
    
    if result.get("found"):
        orders = result.get("orders", [])
        ctx.context._show_orders_widget = True
        ctx.context._orders_data = orders
        return f"Found {len(orders)} orders for this customer."
    else:
        return result.get("message", "No orders found")


@function_tool(description_override="Get items that are eligible for return for a customer. Shows orders with items still within the return window.")
async def tool_get_returnable_items(ctx: RunContextWrapper["RetailContext"], customer_id: str) -> str:
    """Get items eligible for return."""
    result = get_returnable_items(customer_id)
    
    if result.get("found"):
        orders = result.get("orders", [])
        item_count = sum(len(o.get("items", [])) for o in orders)
        ctx.context._show_returnable_items_widget = True
        ctx.context._returnable_items_data = orders
        ctx.context._current_customer_id = customer_id  # Store for later use
        return f"Found {item_count} items that can be returned. Please select which item you'd like to return."
    else:
        return result.get("message", "No returnable items found")


@function_tool(description_override="Check if a specific item from an order can be returned.")
async def tool_check_return_eligibility(ctx: RunContextWrapper["RetailContext"], order_id: str, product_id: str) -> str:
    """Check return eligibility."""
    result = check_return_eligibility(order_id, product_id)
    if result.get("eligible"):
        return f"This item is eligible for return. You have {result.get('days_remaining', 0)} days remaining in the return window."
    else:
        return result.get("reason", "This item is not eligible for return.")


@function_tool(description_override="Get the list of available return reasons to present to the customer.")
async def tool_get_return_reasons(ctx: RunContextWrapper["RetailContext"]) -> str:
    """Get return reasons."""
    result = get_return_reasons()
    reasons = result.get("reasons", []) if isinstance(result, dict) else []
    if reasons:
        ctx.context._show_reasons_widget = True
        ctx.context._reasons_data = reasons
        reason_list = ", ".join([r.get("label", r.get("code", "")) for r in reasons[:5]])
        return f"Please select the reason for your return: {reason_list}"
    return "No return reasons available"


@function_tool(description_override="Get available resolution options (refund, exchange, store credit) for a return.")
async def tool_get_resolution_options(ctx: RunContextWrapper["RetailContext"]) -> str:
    """Get resolution options."""
    result = get_resolution_options()
    options = result.get("options", []) if isinstance(result, dict) else []
    if options:
        ctx.context._show_resolution_widget = True
        ctx.context._resolution_data = options
        options_list = ", ".join([r.get("label", r.get("code", "")) for r in options])
        return f"How would you like to be compensated? Options: {options_list}"
    return "No resolution options available"


@function_tool(description_override="Get available return shipping options (prepaid label, drop-off, pickup).")
async def tool_get_shipping_options(ctx: RunContextWrapper["RetailContext"]) -> str:
    """Get shipping options."""
    result = get_shipping_options()
    options = result.get("options", []) if isinstance(result, dict) else []
    if options:
        ctx.context._show_shipping_widget = True
        ctx.context._shipping_data = options
        options_list = ", ".join([r.get("label", r.get("code", "")) for r in options])
        return f"How would you like to ship the return? Options: {options_list}"
    return "No shipping options available"


@function_tool(description_override="Get available discount offers to retain a customer who changed their mind.")
async def tool_get_retention_offers(ctx: RunContextWrapper["RetailContext"], customer_id: str) -> str:
    """Get retention offers."""
    result = get_retention_offers(customer_id)
    offers = result.get("offers", []) if isinstance(result, dict) else []
    if offers:
        ctx.context._show_retention_widget = True
        ctx.context._retention_data = offers
        return f"Before processing your return, we'd like to offer you a special discount if you keep the item. Would you like to see the offers?"
    return "No special offers available at this time."


@function_tool(description_override="Create a new return request after collecting all required information.")
async def tool_create_return_request(
    ctx: RunContextWrapper["RetailContext"],
    customer_id: str,
    order_id: str,
    product_id: str,
    product_name: str,
    quantity: int,
    unit_price: float,
    reason_code: str,
    resolution: str,
    shipping_method: str = "prepaid_label",
    reason_details: str = "",
) -> str:
    """Create a return request."""
    items = [{
        "product_id": product_id,
        "name": product_name,
        "quantity": quantity,
        "unit_price": unit_price,
    }]
    result = create_return_request(
        customer_id=customer_id,
        order_id=order_id,
        items=items,
        reason_code=reason_code,
        resolution=resolution,
        reason_details=reason_details,
        shipping_method=shipping_method,
    )
    
    if result.get("id"):
        ctx.context._show_confirmation_widget = True
        ctx.context._confirmation_data = result
        return f"Return request {result['id']} has been created successfully! Status: {result.get('status', 'pending')}. A confirmation email has been sent."
    return "Failed to create return request. Please try again."


@function_tool(description_override="Get the return history for a customer.")
async def tool_get_customer_return_history(ctx: RunContextWrapper["RetailContext"], customer_id: str) -> str:
    """Get customer return history."""
    result = get_customer_return_history(customer_id)
    if result:
        return f"This customer has {len(result)} previous returns."
    return "No previous return history for this customer."


@function_tool(description_override="Calculate the refund amount for items being returned.")
async def tool_calculate_refund_amount(
    ctx: RunContextWrapper["RetailContext"],
    unit_price: float,
    quantity: int = 1,
    customer_tier: str = "Standard",
    reason_code: str = "",
) -> str:
    """Calculate refund amount."""
    items = [{"unit_price": unit_price, "quantity": quantity}]
    result = calculate_refund_amount(items, customer_tier, reason_code)
    refund = result.get("refund_amount", unit_price * quantity)
    fee = result.get("restocking_fee", 0)
    if fee > 0:
        return f"Refund amount: ${refund:.2f} (after ${fee:.2f} restocking fee)"
    return f"Refund amount: ${refund:.2f}"


# =============================================================================
# AGENT CREATION
# =============================================================================

def create_retail_agent() -> Agent:
    """
    Create the retail returns agent with all tools.
    
    Returns:
        Configured Agent instance
    """
    return Agent(
        name="Retail Returns Assistant",
        instructions=RETAIL_SYSTEM_PROMPT,
        tools=[
            tool_lookup_customer,
            tool_get_customer_orders,
            tool_get_returnable_items,
            tool_check_return_eligibility,
            tool_get_return_reasons,
            tool_get_resolution_options,
            tool_get_shipping_options,
            tool_get_retention_offers,
            tool_create_return_request,
            tool_get_customer_return_history,
            tool_calculate_refund_amount,
        ],
    )


# =============================================================================
# WIDGET BUILDING
# =============================================================================

def build_customer_widget(customer: dict) -> Card:
    """Build a customer profile card widget."""
    tier = customer.get("tier", "Standard")
    tier_colors = {
        "Standard": "secondary",
        "Silver": "info",
        "Gold": "warning",
        "Platinum": "primary",
    }
    
    return Card(
        id=f"customer-card-{datetime.now().timestamp()}",
        children=[
            Row(
                id="customer-header",
                children=[
                    Title(id="customer-title", value=f"👤 {customer.get('name', 'Customer')}", size="lg"),
                    Spacer(id="spacer1"),
                    Badge(
                        id="tier-badge",
                        label=f"⭐ {tier}",
                        color=tier_colors.get(tier, "secondary"),
                    ),
                ]
            ),
            Divider(id="div1"),
            Text(id="email", value=f"📧 {customer.get('email', '')}"),
            Text(id="phone", value=f"📱 {customer.get('phone', 'N/A')}"),
            Text(id="member", value=f"🗓️ Member since: {customer.get('member_since', 'N/A')}"),
        ]
    )


def build_returnable_items_widget(orders: list, thread_id: str, customer_id: str = "") -> Card:
    """Build a widget for selecting items to return."""
    children = [
        Title(id="items-title", value="🔄 Select Item to Return", size="lg"),
        Text(id="items-subtitle", value="Click on an item to start the return process"),
        Divider(id="div1"),
    ]
    
    for order in orders:
        order_id = order.get("id", "")
        children.append(Text(id=f"order-{order_id}", value=f"📦 Order: {order_id}"))
        
        for item in order.get("items", []):
            days = item.get("days_remaining", 30)
            urgency = "🟢" if days > 14 else "🟡" if days > 7 else "🔴"
            product_id = item.get("product_id", "")
            name = item.get("name", "Item")
            price = item.get("unit_price", 0)
            quantity = item.get("quantity", 1)
            
            children.append(
                Row(
                    id=f"item-row-{product_id}",
                    children=[
                        Text(id=f"urgency-{product_id}", value=urgency),
                        Box(
                            id=f"item-box-{product_id}",
                            children=[
                                Text(id=f"item-name-{product_id}", value=name),
                                Text(id=f"item-details-{product_id}", value=f"${price:.2f} • {days} days left"),
                            ]
                        ),
                        Button(
                            id=f"select-{product_id}",
                            label="Return This",
                            color="primary",
                            onClickAction=ActionConfig(
                                type="select_return_item",
                                handler="server",
                                payload={
                                    "order_id": order_id,
                                    "product_id": product_id,
                                    "name": name,
                                    "unit_price": price,
                                    "quantity": quantity,
                                    "customer_id": customer_id,
                                },
                            ),
                        ),
                    ]
                )
            )
        children.append(Spacer(id=f"spacer-{order_id}"))
    
    return Card(id=f"returnable-items-{thread_id}", children=children)


def build_reasons_widget(reasons: list, thread_id: str) -> Card:
    """Build a widget for selecting return reason."""
    icons = {
        "DEFECTIVE": "🔧",
        "DAMAGED": "📦",
        "WRONG_ITEM": "❌",
        "WRONG_SIZE": "📏",
        "NOT_AS_DESCRIBED": "📝",
        "CHANGED_MIND": "💭",
        "OTHER": "❓",
    }
    
    children = [
        Title(id="reasons-title", value="❓ Why are you returning?", size="lg"),
        Divider(id="div1"),
    ]
    
    for reason in reasons:
        code = reason.get("code", "")
        label = reason.get("label", code)
        icon = icons.get(code, "📋")
        
        children.append(
            Button(
                id=f"reason-{code}",
                label=f"{icon} {label}",
                color="secondary",
                onClickAction=ActionConfig(
                    type="select_reason",
                    handler="server",
                    payload={"reason_code": code, "reason_label": label},
                ),
            )
        )
        children.append(Spacer(id=f"spacer-{code}"))
    
    return Card(id=f"reasons-{thread_id}", children=children)


def build_resolution_widget(options: list, thread_id: str) -> Card:
    """Build a widget for selecting resolution."""
    icons = {
        "refund": "💰",
        "exchange": "🔄",
        "store_credit": "🎁",
    }
    
    children = [
        Title(id="resolution-title", value="💳 How would you like to be compensated?", size="lg"),
        Divider(id="div1"),
    ]
    
    for opt in options:
        code = opt.get("code", "")
        label = opt.get("label", code)
        desc = opt.get("description", "")
        icon = icons.get(code, "✓")
        
        children.append(
            Row(
                id=f"opt-row-{code}",
                children=[
                    Text(id=f"opt-icon-{code}", value=icon),
                    Box(
                        id=f"opt-box-{code}",
                        children=[
                            Text(id=f"opt-label-{code}", value=label),
                            Text(id=f"opt-desc-{code}", value=desc),
                        ]
                    ),
                    Button(
                        id=f"select-{code}",
                        label="Select",
                        color="primary",
                        onClickAction=ActionConfig(
                            type="select_resolution",
                            handler="server",
                            payload={"resolution": code},
                        ),
                    ),
                ]
            )
        )
        children.append(Spacer(id=f"spacer-{code}"))
    
    return Card(id=f"resolution-{thread_id}", children=children)


def build_shipping_widget(options: list, thread_id: str) -> Card:
    """Build a widget for selecting shipping method."""
    icons = {
        "prepaid_label": "📬",
        "drop_off": "🏪",
        "pickup": "🚚",
    }
    
    children = [
        Title(id="shipping-title", value="📦 How will you return the item?", size="lg"),
        Divider(id="div1"),
    ]
    
    for opt in options:
        code = opt.get("code", "")
        label = opt.get("label", code)
        cost = opt.get("cost", 0)
        icon = icons.get(code, "📦")
        cost_text = "Free" if cost == 0 else f"${cost:.2f}"
        
        children.append(
            Row(
                id=f"ship-row-{code}",
                children=[
                    Text(id=f"ship-icon-{code}", value=icon),
                    Box(
                        id=f"ship-box-{code}",
                        children=[
                            Text(id=f"ship-label-{code}", value=label),
                            Text(id=f"ship-cost-{code}", value=cost_text),
                        ]
                    ),
                    Button(
                        id=f"select-ship-{code}",
                        label="Select",
                        color="primary",
                        onClickAction=ActionConfig(
                            type="select_shipping",
                            handler="server",
                            payload={"shipping_method": code},
                        ),
                    ),
                ]
            )
        )
        children.append(Spacer(id=f"spacer-{code}"))
    
    return Card(id=f"shipping-{thread_id}", children=children)


def build_confirmation_widget(confirmation: dict, thread_id: str) -> Card:
    """Build a return confirmation widget."""
    return Card(
        id=f"confirmation-{thread_id}",
        children=[
            Row(
                id="confirm-header",
                children=[
                    Title(id="confirm-title", value="✅ Return Request Confirmed!", size="lg"),
                    Badge(id="status-badge", label=confirmation.get("status", "pending").title(), color="info"),
                ]
            ),
            Divider(id="div1"),
            Text(id="return-id", value=f"Return ID: {confirmation.get('id', 'N/A')}"),
            Text(id="next-steps", value="📧 A confirmation email has been sent with your return label."),
            Spacer(id="spacer1"),
            Text(id="instructions", value="📋 Next Steps:"),
            Text(id="step1", value="1. Print your return label"),
            Text(id="step2", value="2. Pack the item securely"),
            Text(id="step3", value="3. Drop off at any shipping location"),
        ]
    )


# =============================================================================
# SERVER IMPLEMENTATION
# =============================================================================

class RetailChatKitServer(BaseChatKitServer):
    """
    ChatKit server for retail order returns.
    
    This server:
    - Uses the retail agent with order/return tools
    - Connects to Cosmos DB for real data
    - Renders interactive widgets for the returns flow
    - Handles widget actions for selections and confirmations
    """
    
    def __init__(self, data_store: Store):
        """
        Initialize the retail server.
        
        Args:
            data_store: Store instance for thread persistence (CosmosDBStore recommended)
        """
        super().__init__(data_store)
        self._agent = None
        self._session_context = {}
    
    def get_agent(self) -> Agent:
        """Return the retail returns agent."""
        if self._agent is None:
            self._agent = create_retail_agent()
        return self._agent
    
    async def action(
        self,
        thread: ThreadMetadata,
        action: Any,
        sender: Any,
        context: Any,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Handle widget actions (button clicks, selections, etc.)
        """
        # Action is a Pydantic model with .type and .payload attributes
        action_type = getattr(action, 'type', '') if action else ''
        payload = getattr(action, 'payload', {}) or {}
        
        logger.info(f"Handling retail action: {action_type}, payload: {payload}")
        
        # Convert action to user message for the agent
        action_messages = {
            "select_customer": f"I am customer {payload.get('customer_id', '')}",
            "select_return_item": f"I want to return {payload.get('name', 'this item')} from order {payload.get('order_id', '')}",
            "select_reason": f"The reason for my return is: {payload.get('reason_code', '')}",
            "select_resolution": f"I would like a {payload.get('resolution', 'refund')}",
            "select_shipping": f"I will use {payload.get('shipping_method', 'prepaid_label').replace('_', ' ')}",
            "accept_offer": "I'll accept the discount offer and keep the item",
            "decline_offers": "No thanks, I want to continue with the return",
            "confirm_return": "Yes, please confirm and process my return",
            "cancel_return": "I want to cancel this return request",
        }
        
        # Store context from action
        if action_type == "select_customer":
            self._session_context["customer_id"] = payload.get("customer_id")
            self._session_context["customer_name"] = payload.get("name", "")
        
        elif action_type == "select_return_item":
            self._session_context["customer_id"] = payload.get("customer_id", "")
            self._session_context["selected_order_id"] = payload.get("order_id")
            self._session_context["selected_product_id"] = payload.get("product_id")
            self._session_context["selected_item_name"] = payload.get("name")
            self._session_context["unit_price"] = payload.get("unit_price", 0)
            self._session_context["quantity"] = payload.get("quantity", 1)
        
        elif action_type == "select_reason":
            self._session_context["reason_code"] = payload.get("reason_code")
            self._session_context["reason_details"] = payload.get("reason_details", "")
        
        elif action_type == "select_resolution":
            self._session_context["resolution"] = payload.get("resolution")
        
        elif action_type == "select_shipping":
            self._session_context["shipping_method"] = payload.get("shipping_method")
        
        # Generate a text response acknowledging the action
        message_text = action_messages.get(action_type, f"You selected: {action_type}")
        
        logger.info(f"Action processed: {message_text}")
        
        # Emit a user message to show the selection in the thread
        # This makes the user's choices visible in the conversation
        user_message_item = UserMessageItem(
            id=f"user-selection-{uuid.uuid4().hex[:8]}",
            thread_id=thread.id,
            created_at=datetime.now(timezone.utc),
            content=[UserMessageTextContent(type="input_text", text=message_text)],
            attachments=[],
            inference_options=InferenceOptions(),
        )
        yield ThreadItemDoneEvent(item=user_message_item)
        
        # Stream the next appropriate widget based on action type
        if action_type == "select_return_item":
            # After selecting item, show reasons widget
            result = get_return_reasons()
            reasons = result.get("reasons", []) if isinstance(result, dict) else []
            if reasons:
                widget = build_reasons_widget(reasons, thread.id)
                async for event in stream_widget(thread, widget):
                    yield event
        
        elif action_type == "select_reason":
            # After selecting reason, show resolution options
            result = get_resolution_options()
            options = result.get("options", []) if isinstance(result, dict) else []
            if options:
                widget = build_resolution_widget(options, thread.id)
                async for event in stream_widget(thread, widget):
                    yield event
        
        elif action_type == "select_resolution":
            # After selecting resolution, show shipping options
            result = get_shipping_options()
            shipping = result.get("options", []) if isinstance(result, dict) else []
            if shipping:
                widget = build_shipping_widget(shipping, thread.id)
                async for event in stream_widget(thread, widget):
                    yield event
        
        elif action_type == "select_shipping":
            # After selecting shipping, actually create the return in Cosmos DB
            try:
                # Gather all context for the return
                customer_id = self._session_context.get("customer_id", "")
                order_id = self._session_context.get("selected_order_id", "")
                product_id = self._session_context.get("selected_product_id", "")
                item_name = self._session_context.get("selected_item_name", "")
                unit_price = self._session_context.get("unit_price", 0)
                quantity = self._session_context.get("quantity", 1)
                reason_code = self._session_context.get("reason_code", "OTHER")
                reason_details = self._session_context.get("reason_details", "")
                resolution = self._session_context.get("resolution", "refund")
                shipping_method = self._session_context.get("shipping_method", "prepaid_label")
                
                # Build items list for the return
                items = [{
                    "product_id": product_id,
                    "name": item_name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                }]
                
                # Create the return request in Cosmos DB
                result = create_return_request(
                    customer_id=customer_id,
                    order_id=order_id,
                    items=items,
                    reason_code=reason_code,
                    reason_details=reason_details,
                    resolution=resolution,
                    shipping_method=shipping_method,
                )
                
                logger.info(f"Return created successfully: {result}")
                
                confirmation = {
                    "id": result.get("return_id", f"RET-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                    "status": result.get("status", "pending"),
                    "refund_amount": result.get("refund_amount", 0),
                }
            except Exception as e:
                logger.error(f"Error creating return: {e}")
                # Fallback to display-only confirmation if save fails
                confirmation = {
                    "id": f"RET-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "status": "pending",
                    "error": str(e),
                }
            
            widget = build_confirmation_widget(confirmation, thread.id)
            async for event in stream_widget(thread, widget):
                yield event
    
    async def post_respond_hook(
        self,
        thread: ThreadMetadata,
        agent_context: Any,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Stream widgets after agent response based on context flags.
        
        Tools set flags like _show_customer_widget, _show_returnable_items_widget, etc.
        to trigger widget display.
        """
        thread_id = thread.id
        
        # Check for customer widget
        if getattr(agent_context, '_show_customer_widget', False):
            customer_data = getattr(agent_context, '_customer_data', {})
            if customer_data:
                widget = build_customer_widget(customer_data)
                logger.info(f"Streaming customer widget for {customer_data.get('name')}")
                async for event in stream_widget(thread, widget):
                    yield event
        
        # Check for returnable items widget
        if getattr(agent_context, '_show_returnable_items_widget', False):
            items_data = getattr(agent_context, '_returnable_items_data', [])
            customer_id = getattr(agent_context, '_current_customer_id', '')
            if items_data:
                widget = build_returnable_items_widget(items_data, thread_id, customer_id)
                logger.info(f"Streaming returnable items widget with {len(items_data)} orders")
                async for event in stream_widget(thread, widget):
                    yield event
        
        # Check for reasons widget
        if getattr(agent_context, '_show_reasons_widget', False):
            reasons_data = getattr(agent_context, '_reasons_data', [])
            if reasons_data:
                widget = build_reasons_widget(reasons_data, thread_id)
                logger.info(f"Streaming reasons widget with {len(reasons_data)} options")
                async for event in stream_widget(thread, widget):
                    yield event
        
        # Check for resolution widget
        if getattr(agent_context, '_show_resolution_widget', False):
            resolution_data = getattr(agent_context, '_resolution_data', [])
            if resolution_data:
                widget = build_resolution_widget(resolution_data, thread_id)
                logger.info(f"Streaming resolution widget with {len(resolution_data)} options")
                async for event in stream_widget(thread, widget):
                    yield event
        
        # Check for shipping widget
        if getattr(agent_context, '_show_shipping_widget', False):
            shipping_data = getattr(agent_context, '_shipping_data', [])
            if shipping_data:
                widget = build_shipping_widget(shipping_data, thread_id)
                logger.info(f"Streaming shipping widget with {len(shipping_data)} options")
                async for event in stream_widget(thread, widget):
                    yield event
        
        # Check for confirmation widget
        if getattr(agent_context, '_show_confirmation_widget', False):
            confirmation_data = getattr(agent_context, '_confirmation_data', {})
            if confirmation_data:
                widget = build_confirmation_widget(confirmation_data, thread_id)
                logger.info(f"Streaming confirmation widget for return {confirmation_data.get('id')}")
                async for event in stream_widget(thread, widget):
                    yield event

    async def _collapse_old_widgets(
        self,
        thread: ThreadMetadata,
        context: Any,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Replace old widgets with summaries to keep UI clean.
        """
        try:
            items_page: Page = await self.data_store.load_thread_items(
                thread_id=thread.id,
            )
            
            for item in items_page.items:
                if isinstance(item, WidgetItem):
                    widget_data = item.widget.data if hasattr(item, "widget") else {}
                    widget_type = widget_data.get("type", "")
                    
                    if widget_type in ["item_selector", "option_selector", "resolution_selector"]:
                        # Replace with a text summary
                        summary_text = f"[Previous selection widget - {widget_type}]"
                        yield ThreadItemReplacedEvent(
                            item=AssistantMessageItem(
                                id=item.id,
                                content=[AssistantMessageContent(
                                    type="text",
                                    text=summary_text,
                                )],
                            )
                        )
        except Exception as e:
            logger.warning(f"Error collapsing old widgets: {e}")
