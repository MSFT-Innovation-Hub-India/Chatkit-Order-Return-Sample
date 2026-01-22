"""
Base ChatKit Server Implementation with Azure OpenAI.

This module provides the reusable base server that can be extended for different use cases.
It handles:
- Azure OpenAI client integration
- Agent-based response streaming
- Widget event streaming
- Common server lifecycle

To create a new use case, extend BaseChatKitServer and:
1. Define your agent with tools in your use case module
2. Override get_agent() to return your agent
3. Override action() to handle widget actions
4. Optionally override post_respond_hook() for custom widget streaming
"""

import logging
from abc import abstractmethod
from typing import Any, AsyncIterator, Optional

from chatkit.server import ChatKitServer, ThreadStreamEvent
from chatkit.store import Store, ThreadMetadata
from chatkit.types import UserMessageItem, ClientToolCallItem
from chatkit.agents import stream_agent_response, stream_widget, AgentContext, ThreadItemConverter
from chatkit.widgets import Card

from agents import Agent, Runner, RunConfig
from agents.models.openai_responses import OpenAIResponsesModel

from azure_client import client_manager
from config import settings

logger = logging.getLogger(__name__)


class BaseChatKitServer(ChatKitServer):
    """
    Base ChatKit server with Azure OpenAI integration.
    
    This class provides the common infrastructure for ChatKit-based applications:
    - Azure OpenAI model integration
    - Agent response streaming
    - Widget streaming support
    
    Extend this class and implement the abstract methods for your use case.
    """
    
    def __init__(self, data_store: Store):
        """
        Initialize the base server.
        
        Args:
            data_store: The ChatKit store for thread/message persistence
        """
        super().__init__(data_store)
        self.data_store = data_store
    
    @abstractmethod
    def get_agent(self) -> Agent:
        """
        Return the agent instance for this use case.
        
        Override this method to return your configured agent with tools.
        
        Returns:
            An Agent instance configured with appropriate tools and instructions
        """
        pass
    
    @abstractmethod
    async def action(
        self,
        thread: ThreadMetadata,
        action: Any,
        sender: Any,
        context: Any,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Handle widget actions (button clicks, form submissions, etc.)
        
        Override this method to handle actions from your widgets.
        
        Args:
            thread: The thread metadata
            action: The action object with type and payload
            sender: The widget that sent the action
            context: Request context
            
        Yields:
            ThreadStreamEvent objects (typically widget updates)
        """
        pass
    
    async def post_respond_hook(
        self,
        thread: ThreadMetadata,
        agent_context: AgentContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Hook called after the agent response is complete.
        
        Override this to stream additional events (like widgets) after the agent responds.
        The default implementation does nothing.
        
        Args:
            thread: The thread metadata
            agent_context: The agent context (may have custom attributes set by tools)
            
        Yields:
            Additional ThreadStreamEvent objects
        """
        # Default: no additional events
        return
        yield  # Make this a generator
    
    async def respond(
        self,
        thread: ThreadMetadata,
        input: UserMessageItem | ClientToolCallItem,
        context: Any,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Handle user messages and generate responses using Azure OpenAI.
        
        This method:
        1. Gets the Azure OpenAI client
        2. Creates an agent context
        3. Runs the agent with streaming
        4. Calls post_respond_hook for additional events
        
        Args:
            thread: Thread metadata
            input: User message or client tool call
            context: Request context
            
        Yields:
            ThreadStreamEvent objects
        """
        # Get Azure OpenAI client
        client = await client_manager.get_client()
        
        # Create the Azure OpenAI model wrapper using the Responses API
        # This provides proper item IDs and better streaming support
        azure_model = OpenAIResponsesModel(
            model=settings.azure_openai_deployment,
            openai_client=client,
        )
        
        # Create agent context with thread and store
        agent_context = AgentContext(
            thread=thread,
            store=self.data_store,
            request_context=context,
        )
        
        # Load full conversation history from the store
        # This is critical for the agent to have context of previous messages
        converter = ThreadItemConverter()
        
        # Load all thread items (conversation history)
        thread_items_page = await self.data_store.load_thread_items(
            thread.id,
            after=None,
            limit=100,  # Get up to 100 messages for context
            order="asc",  # Oldest first for chronological order
            context=context,
        )
        
        # Filter to only user and assistant messages (not widgets)
        # and convert to agent input format
        relevant_items = [
            item for item in thread_items_page.data
            if item.type in ("user_message", "assistant_message")
        ]
        
        # Debug: Log the conversation history being sent to the agent
        for i, item in enumerate(relevant_items):
            item_type = item.type
            # Get text preview from item content
            text_preview = ""
            if hasattr(item, 'content') and item.content:
                for c in item.content:
                    if hasattr(c, 'text'):
                        text_preview = c.text[:50] + "..." if len(c.text) > 50 else c.text
                        break
            logger.info(f"History[{i}]: {item_type} - {text_preview}")
        
        # Convert the full conversation history to agent input
        agent_input = await converter.to_agent_input(relevant_items)
        
        logger.info(f"Agent input includes {len(relevant_items)} messages from conversation history")
        
        # Get the agent for this use case
        agent = self.get_agent()
        
        # Run the agent with streaming
        result = Runner.run_streamed(
            agent,
            agent_input,
            context=agent_context,
            run_config=RunConfig(model=azure_model),
        )
        
        # Stream the agent response back to the client
        async for event in stream_agent_response(agent_context, result):
            event_type = type(event).__name__
            # Log more details about the event content
            if hasattr(event, 'item'):
                item = event.item
                item_id = getattr(item, 'id', 'unknown')
                if hasattr(item, 'content') and item.content:
                    # Log first content item for debugging
                    first_content = item.content[0] if item.content else None
                    if first_content and hasattr(first_content, 'text'):
                        text_preview = first_content.text[:50] if first_content.text else ''
                        logger.info(f"Streaming event: {event_type}, id={item_id}, text preview: {text_preview}...")
                    else:
                        logger.info(f"Streaming event: {event_type}, id={item_id}, content type: {type(first_content).__name__ if first_content else 'None'}")
                else:
                    logger.info(f"Streaming event: {event_type}, id={item_id}, item type: {type(item).__name__}")
            else:
                logger.info(f"Streaming event: {event_type}")
            yield event
        
        # Call the post-respond hook for additional events (e.g., widgets)
        async for event in self.post_respond_hook(thread, agent_context):
            logger.info(f"Post-respond hook event: {type(event).__name__}")
            yield event
    
    async def stream_widget_to_client(
        self,
        thread: ThreadMetadata,
        widget: Card,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Helper method to stream a widget to the client.
        
        Args:
            thread: The thread metadata
            widget: The widget to stream
            
        Yields:
            Widget-related ThreadStreamEvent objects
        """
        async for event in stream_widget(thread, widget):
            logger.debug(f"Streaming widget event: {event.type}")
            yield event
