"""
Orchestration Layer Base Classes.

The orchestration layer wires together all components:
- Domain services for business logic
- Repositories for data access
- Widget composers for presentation
- Session management for state

This layer also provides the ChatKit server integration.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Type

from chatkit.server import ChatKitServer, ThreadStreamEvent
from chatkit.store import Store, ThreadMetadata
from chatkit.types import UserMessageItem, ClientToolCallItem
from chatkit.agents import stream_agent_response, stream_widget, AgentContext, ThreadItemConverter

from agents import Agent, Runner, RunConfig, function_tool
from agents.models.openai_responses import OpenAIResponsesModel

from .session import SessionContext, SessionManager
from .presentation import WidgetComposer

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """
    Definition of a tool for the agent.
    
    Wraps a function with metadata for registration.
    """
    name: str
    description: str
    function: Callable
    category: str = "general"


class ToolRegistry:
    """
    Registry for agent tools.
    
    Provides a way to organize and register tools by category.
    This makes it easy to:
    - Add/remove tools for different agent configurations
    - Group related tools together
    - Document available tools
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register(
        self,
        name: str,
        description: str,
        function: Callable,
        category: str = "general",
    ):
        """
        Register a tool.
        
        Args:
            name: Unique tool name
            description: Tool description for the agent
            function: The tool function (should be decorated with @function_tool)
            category: Category for organization
        """
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            function=function,
            category=category,
        )
        
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)
    
    def get_tools(self, categories: Optional[List[str]] = None) -> List[Callable]:
        """
        Get tool functions, optionally filtered by category.
        
        Args:
            categories: Optional list of categories to include
            
        Returns:
            List of tool functions
        """
        if categories is None:
            return [t.function for t in self._tools.values()]
        
        tools = []
        for cat in categories:
            for name in self._categories.get(cat, []):
                if name in self._tools:
                    tools.append(self._tools[name].function)
        return tools
    
    def get_tool_names(self) -> List[str]:
        """Get all registered tool names."""
        return list(self._tools.keys())
    
    def get_categories(self) -> List[str]:
        """Get all categories."""
        return list(self._categories.keys())


class UseCaseServer(ChatKitServer, ABC):
    """
    Abstract base class for use case servers.
    
    Extends ChatKitServer with:
    - Session management
    - Widget composer integration
    - Tool registry
    - Standard respond/action flow
    
    Each use case should extend this class and implement:
    - get_agent(): Return the configured agent
    - get_system_prompt(): Return the system prompt
    - create_session_context(): Create a use-case-specific session context
    - create_widget_composer(): Create the widget composer
    - handle_action(): Handle widget actions
    """
    
    def __init__(
        self,
        data_store: Store,
        session_context_class: Type[SessionContext] = SessionContext,
    ):
        """
        Initialize the use case server.
        
        Args:
            data_store: The ChatKit store for persistence
            session_context_class: The session context class to use
        """
        super().__init__(data_store)
        self.data_store = data_store
        self.session_manager = SessionManager(session_context_class)
        self.tool_registry = ToolRegistry()
        self._widget_composer: Optional[WidgetComposer] = None
        
        # Initialize tools and composer
        self._register_tools()
        self._widget_composer = self.create_widget_composer()
    
    @property
    def widget_composer(self) -> WidgetComposer:
        """Get the widget composer."""
        if self._widget_composer is None:
            self._widget_composer = self.create_widget_composer()
        return self._widget_composer
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Return the system prompt for this use case.
        
        The system prompt should:
        - Define the agent's role and personality
        - Specify the workflow steps
        - Include instructions for handling natural language
        """
        pass
    
    @abstractmethod
    def get_agent(self) -> Agent:
        """
        Return the configured agent for this use case.
        
        Should create an Agent with:
        - The system prompt from get_system_prompt()
        - Tools from the tool registry
        """
        pass
    
    @abstractmethod
    def create_widget_composer(self) -> WidgetComposer:
        """
        Create the widget composer for this use case.
        
        Returns:
            A WidgetComposer instance configured for this use case
        """
        pass
    
    @abstractmethod
    def _register_tools(self):
        """
        Register tools with the tool registry.
        
        Called during __init__ to set up available tools.
        """
        pass
    
    @abstractmethod
    async def handle_action(
        self,
        thread: ThreadMetadata,
        action_type: str,
        payload: Dict[str, Any],
        session: SessionContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Handle a widget action.
        
        Args:
            thread: The thread metadata
            action_type: The type of action (e.g., "select_item")
            payload: The action payload
            session: The current session context
            
        Yields:
            ThreadStreamEvent objects
        """
        pass
    
    def build_context_summary(self, session: SessionContext) -> str:
        """
        Build a context summary string for the agent.
        
        Override for use-case-specific formatting.
        
        Args:
            session: The current session context
            
        Returns:
            A string summary of the session state
        """
        return session.to_context_string()
    
    async def respond(
        self,
        thread: ThreadMetadata,
        input: UserMessageItem | ClientToolCallItem,
        context: Any,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Handle user messages with session context injection.
        
        This method:
        1. Gets or creates the session context
        2. Loads conversation history
        3. Injects session context into the agent
        4. Runs the agent with streaming
        5. Syncs session context back
        6. Calls post_respond_hook for widgets
        """
        from azure_client import client_manager
        from config import settings
        
        # Get or create session
        session = self.session_manager.get_or_create(thread.id)
        session.reset_widgets()
        
        # Get Azure OpenAI client
        client = await client_manager.get_client()
        
        # Create the Azure OpenAI model wrapper
        azure_model = OpenAIResponsesModel(
            model=settings.azure_openai_deployment,
            openai_client=client,
        )
        
        # Create agent context
        agent_context = AgentContext(
            thread=thread,
            store=self.data_store,
            request_context=context,
        )
        
        # Attach session to agent context for tools to access
        agent_context._session_context = session
        agent_context._widget_composer = self.widget_composer
        
        # Load conversation history
        converter = ThreadItemConverter()
        thread_items_page = await self.data_store.load_thread_items(
            thread.id,
            after=None,
            limit=100,
            order="asc",
            context=context,
        )
        
        relevant_items = [
            item for item in thread_items_page.data
            if item.type in ("user_message", "assistant_message")
        ]
        
        agent_input = await converter.to_agent_input(relevant_items)
        
        # Inject session context as system message
        if session.customer_id or session.displayed_items or session.selections:
            context_summary = self.build_context_summary(session)
            if context_summary:
                context_message = f"[CURRENT SESSION STATE]\n{context_summary}\n[END SESSION STATE]"
                agent_input = [{"role": "system", "content": context_message}] + agent_input
                logger.debug(f"Injected session context for thread {thread.id}")
        
        # Get and run the agent
        agent = self.get_agent()
        result = Runner.run_streamed(
            agent,
            agent_input,
            context=agent_context,
            run_config=RunConfig(model=azure_model),
        )
        
        # Stream the agent response
        async for event in stream_agent_response(agent_context, result):
            yield event
        
        # Sync session context back from agent context
        if hasattr(agent_context, '_session_context'):
            # The session object is the same reference, but this allows
            # for any additional sync logic if needed
            pass
        
        # Call post-respond hook for widgets
        async for event in self.post_respond_hook(thread, agent_context, session):
            yield event
    
    async def post_respond_hook(
        self,
        thread: ThreadMetadata,
        agent_context: AgentContext,
        session: SessionContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Hook called after the agent response for widget streaming.
        
        Override this to stream widgets based on session state.
        
        Args:
            thread: The thread metadata
            agent_context: The agent context with any flags set by tools
            session: The current session context
            
        Yields:
            Widget events
        """
        # Default: no widgets
        return
        yield
    
    async def action(
        self,
        thread: ThreadMetadata,
        action: Any,
        sender: Any,
        context: Any,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Handle widget actions.
        
        Routes to the use-case-specific handle_action method.
        """
        action_type = getattr(action, 'type', '') if action else ''
        payload = getattr(action, 'payload', {}) or {}
        
        logger.info(f"Handling action: {action_type}, payload: {payload}")
        
        # Get session
        session = self.session_manager.get_or_create(thread.id)
        
        # Delegate to use-case-specific handler
        async for event in self.handle_action(thread, action_type, payload, session):
            yield event
    
    async def stream_widget_to_client(
        self,
        thread: ThreadMetadata,
        widget: Any,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Stream a widget to the client.
        
        Helper method for streaming widgets in a consistent way.
        """
        async for event in stream_widget(thread, widget):
            yield event
