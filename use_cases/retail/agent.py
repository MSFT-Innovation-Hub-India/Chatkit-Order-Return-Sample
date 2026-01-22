"""
Retail Order Returns Agent with ChatKit + Azure OpenAI.

This agent handles the complete order returns flow with:
- Natural language understanding
- Cosmos DB data access
- Rich ChatKit widgets for UI
- Action handling for user interactions
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai import AsyncAzureOpenAI
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from chatkit import (
    ChatContext,
    ContentPart,
    UIData,
    Widget,
)

from .tools import RETAIL_TOOLS, execute_tool
from .widgets import (
    create_customer_card,
    create_customer_selection_widget,
    create_orders_list_widget,
    create_returnable_items_widget,
    create_return_reasons_widget,
    create_resolution_options_widget,
    create_shipping_options_widget,
    create_retention_offer_widget,
    create_return_summary_widget,
    create_return_confirmation_widget,
    create_error_widget,
    create_return_history_widget,
)

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_OPENAI_ENDPOINT = "https://common-aoai.openai.azure.com/"
AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
AZURE_OPENAI_API_VERSION = "2024-10-21"

SYSTEM_PROMPT = """You are a helpful customer service assistant for a retail company, specializing in order returns.

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
When presenting options, use clear formatting and be concise.
"""


class RetailReturnsAgent:
    """Agent for handling retail order returns with ChatKit."""

    def __init__(self):
        """Initialize the agent."""
        self._credential = None
        self._client = None
        self._session_context: Dict[str, Any] = {}

    async def _ensure_client(self) -> AsyncAzureOpenAI:
        """Ensure the Azure OpenAI client is initialized."""
        if self._client is None:
            self._credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                self._credential,
                "https://cognitiveservices.azure.com/.default"
            )
            self._client = AsyncAzureOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                azure_ad_token_provider=token_provider,
                api_version=AZURE_OPENAI_API_VERSION,
            )
        return self._client

    async def close(self):
        """Close the agent and clean up resources."""
        if self._credential:
            await self._credential.close()
        if self._client:
            await self._client.close()

    def _update_session_context(self, key: str, value: Any):
        """Update session context with conversation state."""
        self._session_context[key] = value

    def _get_session_context(self, key: str, default: Any = None) -> Any:
        """Get value from session context."""
        return self._session_context.get(key, default)

    async def _process_tool_calls(
        self,
        tool_calls: List[Any],
        messages: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process tool calls and return tool results and widgets.
        """
        widgets = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            logger.info(f"Executing tool call: {function_name} with args: {arguments}")
            
            # Execute the tool
            result_str = execute_tool(function_name, arguments)
            result = json.loads(result_str)
            
            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str,
            })
            
            # Generate widgets based on tool results
            widget = self._create_widget_for_tool_result(function_name, result, arguments)
            if widget:
                widgets.append(widget)
            
            # Update session context based on tool
            self._update_context_from_tool(function_name, result, arguments)
        
        return messages, widgets

    def _create_widget_for_tool_result(
        self,
        function_name: str,
        result: Dict[str, Any],
        arguments: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Create appropriate widget based on tool result."""
        
        if function_name == "lookup_customer":
            if result.get("found"):
                if result.get("multiple"):
                    return create_customer_selection_widget(result["customers"])
                else:
                    return create_customer_card(result["customer"])
            else:
                return create_error_widget(
                    result.get("message", "Customer not found"),
                    ["Try with full name or email", "Check for typos"]
                )
        
        elif function_name == "get_customer_orders":
            if result.get("found"):
                return create_orders_list_widget(result["orders"])
            return None
        
        elif function_name == "get_returnable_items":
            if result.get("found"):
                return create_returnable_items_widget(result["orders"])
            else:
                return create_error_widget(
                    result.get("message", "No returnable items found"),
                    ["Items may be outside the 30-day return window",
                     "Contact support for special circumstances"]
                )
        
        elif function_name == "get_return_reasons":
            return create_return_reasons_widget(result.get("reasons", []))
        
        elif function_name == "get_resolution_options":
            customer = self._get_session_context("customer", {})
            refund_amount = self._get_session_context("refund_amount", 0)
            return create_resolution_options_widget(
                result.get("options", []),
                refund_amount,
                customer.get("tier", "Standard"),
            )
        
        elif function_name == "get_shipping_options":
            return create_shipping_options_widget(result.get("options", []))
        
        elif function_name == "get_retention_offers":
            item_name = self._get_session_context("selected_item_name", "item")
            if result.get("offers"):
                return create_retention_offer_widget(
                    result["offers"],
                    result.get("customer_tier", "Standard"),
                    item_name,
                )
            return None
        
        elif function_name == "create_return_request":
            if result.get("success"):
                shipping_method = self._get_session_context("shipping_method", "prepaid_label")
                return create_return_confirmation_widget(result, shipping_method)
            else:
                return create_error_widget(
                    result.get("error", "Failed to create return"),
                    ["Please try again", "Contact support if issue persists"]
                )
        
        elif function_name == "get_customer_return_history":
            return create_return_history_widget(result.get("returns", []))
        
        return None

    def _update_context_from_tool(
        self,
        function_name: str,
        result: Dict[str, Any],
        arguments: Dict[str, Any],
    ):
        """Update session context based on tool execution."""
        
        if function_name == "lookup_customer" and result.get("found") and not result.get("multiple"):
            self._update_session_context("customer", result["customer"])
            self._update_session_context("customer_id", result["customer"]["id"])
        
        elif function_name == "get_returnable_items" and result.get("found"):
            self._update_session_context("returnable_orders", result["orders"])
        
        elif function_name == "calculate_refund_amount":
            self._update_session_context("refund_amount", result.get("refund_amount", 0))

    async def process_message(
        self,
        message: str,
        conversation_history: List[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message and generate streaming response with widgets.
        
        Yields chunks containing text and/or widgets.
        """
        client = await self._ensure_client()
        
        # Build messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": message})
        
        # Initial completion with tools
        response = await client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            tools=RETAIL_TOOLS,
            tool_choice="auto",
            stream=False,  # First call non-streaming to handle tool calls
        )
        
        assistant_message = response.choices[0].message
        collected_widgets = []
        
        # Process tool calls if any
        while assistant_message.tool_calls:
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            messages, widgets = await self._process_tool_calls(
                assistant_message.tool_calls,
                messages,
            )
            collected_widgets.extend(widgets)
            
            # Get next response
            response = await client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                tools=RETAIL_TOOLS,
                tool_choice="auto",
                stream=False,
            )
            assistant_message = response.choices[0].message
        
        # Yield widgets first
        for widget in collected_widgets:
            yield {"type": "widget", "data": widget}
        
        # Stream the final text response
        if assistant_message.content:
            # Re-create streaming response for the final message
            stream = await client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {"type": "text", "content": chunk.choices[0].delta.content}

    async def handle_action(
        self,
        action: Dict[str, Any],
        conversation_history: List[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle a user action from a widget (e.g., button click, selection).
        
        Converts the action into a natural language message and processes it.
        """
        action_type = action.get("type", "")
        
        # Convert actions to natural language for the AI
        action_messages = {
            "select_customer": f"I'm selecting customer {action.get('customer_id', '')}",
            "select_return_item": f"I want to return the {action.get('name', 'item')} from order {action.get('order_id', '')}",
            "select_reason": f"The reason for my return is: {action.get('reason_code', '')}",
            "select_resolution": f"I'd like a {action.get('resolution', 'refund')} for my return",
            "select_shipping": f"I'll use {action.get('shipping_method', 'prepaid_label').replace('_', ' ')} to return the item",
            "accept_offer": f"Yes, I'll accept the {action.get('offer_code', '')} offer and keep the item",
            "decline_offers": "No thanks, I'd still like to proceed with the return",
            "confirm_return": "Yes, please confirm and process my return",
            "cancel_return": "I'd like to cancel this return request",
            "retry": "Let's try again",
            "contact_support": "I need to speak with a human support agent",
        }
        
        # Update context based on action
        if action_type == "select_return_item":
            self._update_session_context("selected_order_id", action.get("order_id"))
            self._update_session_context("selected_product_id", action.get("product_id"))
            self._update_session_context("selected_item_name", action.get("name"))
            self._update_session_context("refund_amount", action.get("unit_price", 0))
        
        elif action_type == "select_resolution":
            self._update_session_context("resolution", action.get("resolution"))
        
        elif action_type == "select_shipping":
            self._update_session_context("shipping_method", action.get("shipping_method"))
        
        message = action_messages.get(action_type, f"Action: {action_type}")
        
        async for chunk in self.process_message(message, conversation_history):
            yield chunk


# =============================================================================
# CHATKIT INTEGRATION
# =============================================================================

class RetailChatHandler:
    """
    ChatKit-compatible handler for the retail returns flow.
    
    Integrates with ChatKit's streaming protocol.
    """

    def __init__(self):
        """Initialize the handler."""
        self.agent = RetailReturnsAgent()

    async def close(self):
        """Close the handler."""
        await self.agent.close()

    async def handle_chat(
        self,
        context: ChatContext,
    ) -> AsyncGenerator[ContentPart, None]:
        """
        Handle a chat request from ChatKit.
        
        Yields ContentPart objects for streaming response.
        """
        # Get the last user message
        last_message = context.messages[-1] if context.messages else None
        if not last_message or last_message.role != "user":
            return
        
        user_content = last_message.content
        if isinstance(user_content, list):
            # Extract text from content parts
            user_text = " ".join(
                part.text for part in user_content 
                if hasattr(part, "text")
            )
        else:
            user_text = str(user_content)
        
        # Convert previous messages to format for agent
        conversation_history = []
        for msg in context.messages[:-1]:  # Exclude last message
            content = msg.content
            if isinstance(content, list):
                content = " ".join(
                    part.text for part in content 
                    if hasattr(part, "text")
                )
            conversation_history.append({
                "role": msg.role,
                "content": str(content),
            })
        
        # Process message and stream response
        async for chunk in self.agent.process_message(user_text, conversation_history):
            if chunk["type"] == "text":
                yield ContentPart(text=chunk["content"])
            elif chunk["type"] == "widget":
                # Yield widget as UI data
                yield ContentPart(
                    ui=UIData(
                        widget=Widget(
                            type=chunk["data"].get("type", "card"),
                            data=chunk["data"],
                        )
                    )
                )

    async def handle_action(
        self,
        action: Dict[str, Any],
        context: ChatContext,
    ) -> AsyncGenerator[ContentPart, None]:
        """
        Handle an action from a widget click.
        """
        conversation_history = []
        for msg in context.messages:
            content = msg.content
            if isinstance(content, list):
                content = " ".join(
                    part.text for part in content 
                    if hasattr(part, "text")
                )
            conversation_history.append({
                "role": msg.role,
                "content": str(content),
            })
        
        async for chunk in self.agent.handle_action(action, conversation_history):
            if chunk["type"] == "text":
                yield ContentPart(text=chunk["content"])
            elif chunk["type"] == "widget":
                yield ContentPart(
                    ui=UIData(
                        widget=Widget(
                            type=chunk["data"].get("type", "card"),
                            data=chunk["data"],
                        )
                    )
                )


# Singleton instance
_handler: Optional[RetailChatHandler] = None


def get_retail_handler() -> RetailChatHandler:
    """Get the singleton retail chat handler."""
    global _handler
    if _handler is None:
        _handler = RetailChatHandler()
    return _handler
