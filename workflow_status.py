"""
Workflow Status Streaming for Tool Execution.

This module provides ChatGPT-style streaming status indicators for tool execution.
When the agent calls a tool, the UI shows real-time status like:
  🔍 Looking up customer...
  📦 Fetching your orders...
  ✅ Customer info retrieved

Uses ChatKit's Workflow API which renders as collapsible progress indicators.

This is a GENERIC framework - each domain use case provides its own tool status
messages. See use_cases/retail/tool_status.py for an example.

Usage:
    from workflow_status import create_tool_status_hooks
    from use_cases.retail.tool_status import RETAIL_TOOL_STATUS_MESSAGES
    
    hooks, tracker = create_tool_status_hooks(
        agent_context,
        tool_messages=RETAIL_TOOL_STATUS_MESSAGES
    )
"""

import logging
from typing import Any, AsyncIterator, Dict, Optional
from dataclasses import dataclass, field

from chatkit.types import Workflow, CustomTask, CustomSummary, ThreadStreamEvent
from chatkit.agents import AgentContext, stream_agent_response

from agents import RunHooks, Agent, Tool, RunResultStreaming
from agents.run_context import RunContextWrapper
from agents.stream_events import RawResponsesStreamEvent

logger = logging.getLogger(__name__)


# =============================================================================
# DEFAULT TOOL STATUS (used when no custom mapping is provided)
# =============================================================================

DEFAULT_TOOL_STATUS = (
    "Processing...",
    "Done",
    "sparkle",
)

# Valid ChatKit icons reference (for documentation):
VALID_ICONS = [
    'agent', 'analytics', 'atom', 'batch', 'bolt', 'book-open', 'book-closed', 
    'book-clock', 'bug', 'calendar', 'chart', 'check', 'check-circle', 'check-circle-filled', 
    'clock', 'compass', 'confetti', 'cube', 'desktop', 'document', 'dot', 'globe', 'keys', 
    'lab', 'images', 'info', 'lifesaver', 'lightbulb', 'mail', 'map-pin', 'maps', 'mobile', 
    'name', 'notebook', 'page-blank', 'phone', 'play', 'plus', 'profile', 'profile-card', 
    'reload', 'star', 'search', 'sparkle', 'sparkle-double', 'square-code', 'square-image', 
    'square-text', 'suitcase', 'settings-slider', 'user', 'wreath', 'write'
]


def get_tool_status(tool_name: str, tool_messages: Dict[str, tuple] = None) -> tuple:
    """Get the status messages for a tool.
    
    The OpenAI Agents SDK adds a 'tool_' prefix to function names,
    so we strip it to match our mapping.
    
    Args:
        tool_name: The tool name (may have 'tool_' prefix)
        tool_messages: Optional custom mapping of tool names to status tuples
        
    Returns:
        Tuple of (start_message, end_message, icon)
    """
    # Strip the 'tool_' prefix added by the SDK
    clean_name = tool_name
    if tool_name.startswith("tool_"):
        clean_name = tool_name[5:]  # Remove 'tool_' prefix
    
    if tool_messages:
        return tool_messages.get(clean_name, DEFAULT_TOOL_STATUS)
    return DEFAULT_TOOL_STATUS


# =============================================================================
# WORKFLOW STATUS TRACKER
# =============================================================================

@dataclass
class ToolExecutionTracker:
    """Tracks tool executions for workflow status updates.
    
    This is a generic tracker that works with any domain use case.
    Pass custom tool_messages to provide domain-specific status text.
    """
    
    agent_context: Optional[AgentContext] = None
    tool_messages: Dict[str, tuple] = field(default_factory=dict)
    current_workflow_started: bool = False
    tool_count: int = 0
    tool_task_indices: Dict[str, int] = field(default_factory=dict)
    has_thinking_task: bool = False
    workflow_summary: str = "Working on it..."
    workflow_icon: str = "sparkle"
    
    async def start_workflow_if_needed(self):
        """Start a workflow if not already started.
        
        Called automatically when the first tool is executed.
        """
        if self.agent_context and not self.current_workflow_started:
            workflow = Workflow(
                type="custom",
                tasks=[],
                summary=CustomSummary(title=self.workflow_summary, icon=self.workflow_icon),
                expanded=True,
            )
            await self.agent_context.start_workflow(workflow)
            self.current_workflow_started = True
            logger.debug("Started workflow for tool execution tracking")
    
    async def add_tool_task(self, tool_name: str, is_start: bool = True):
        """Add or update a task for a tool execution."""
        if not self.agent_context:
            return
            
        start_msg, end_msg, icon = get_tool_status(tool_name, self.tool_messages)
        
        if is_start:
            # Start workflow on first tool call (lazy initialization)
            await self.start_workflow_if_needed()
            
            # Add new task for this tool
            task_index = self.tool_count
            self.tool_task_indices[tool_name] = task_index
            self.tool_count += 1
            
            task = CustomTask(
                type="custom",
                title=start_msg,
                icon=icon,
                content=None,
            )
            await self.agent_context.add_workflow_task(task)
            logger.debug(f"Added workflow task at index {task_index}: {start_msg}")
        else:
            # Update the task to show completion using tracked index
            task_index = self.tool_task_indices.get(tool_name)
            if task_index is not None:
                task = CustomTask(
                    type="custom",
                    title=f"✓ {end_msg}",
                    icon="check-circle-filled",
                    content=None,
                )
                await self.agent_context.update_workflow_task(task, task_index)
                logger.debug(f"Updated workflow task at index {task_index}: {end_msg}")
    
    async def end_workflow_if_started(self):
        """End the workflow if it was started."""
        if self.agent_context and self.current_workflow_started:
            try:
                await self.agent_context.end_workflow(expanded=False)
            except ValueError as e:
                # Workflow may have been cleared by streaming - that's OK
                logger.debug(f"Workflow already ended: {e}")
            
            self.current_workflow_started = False
            self.tool_count = 0
            self.tool_task_indices.clear()
            logger.debug("Ended workflow")


# =============================================================================
# TOOL STATUS HOOKS (implements OpenAI Agents SDK RunHooks)
# =============================================================================

class ToolStatusHooks(RunHooks):
    """
    RunHooks implementation that streams workflow status updates during tool execution.
    
    This is a generic implementation that works with any domain use case.
    The actual status messages come from the ToolExecutionTracker's tool_messages.
    
    Example:
        from workflow_status import create_tool_status_hooks
        from use_cases.retail.tool_status import RETAIL_TOOL_STATUS_MESSAGES
        
        hooks, tracker = create_tool_status_hooks(
            agent_context,
            tool_messages=RETAIL_TOOL_STATUS_MESSAGES
        )
        
        result = Runner.run_streamed(
            agent,
            input,
            context=agent_context,
            hooks=hooks,
        )
    """
    
    def __init__(self, tracker: ToolExecutionTracker):
        self.tracker = tracker
    
    async def on_tool_start(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Tool,
    ) -> None:
        """Called when a tool starts executing."""
        tool_name = tool.name
        logger.info(f"Tool starting: {tool_name}")
        
        # Add task for this tool (workflow starts automatically on first tool)
        await self.tracker.add_tool_task(tool_name, is_start=True)
    
    async def on_tool_end(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Tool,
        result: str,
    ) -> None:
        """Called when a tool finishes executing."""
        tool_name = tool.name
        logger.info(f"Tool completed: {tool_name}")
        
        # Update task to show completion
        await self.tracker.add_tool_task(tool_name, is_start=False)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_tool_status_hooks(
    agent_context: AgentContext,
    tool_messages: Dict[str, tuple] = None,
    workflow_summary: str = "Working on it...",
    workflow_icon: str = "sparkle",
) -> tuple:
    """
    Create a ToolStatusHooks instance for streaming tool execution status.
    
    This is the main entry point for using workflow status in any domain.
    
    Args:
        agent_context: The ChatKit AgentContext to stream status to
        tool_messages: Dict mapping tool names to (start_msg, end_msg, icon) tuples.
                      If not provided, uses generic "Processing..." / "Done" messages.
        workflow_summary: The header text shown while tools execute (default: "Working on it...")
        workflow_icon: The icon for the workflow header (default: "sparkle")
        
    Returns:
        A tuple of (hooks, tracker) to pass to Runner.run_streamed
        
    Example (Retail):
        from use_cases.retail.tool_status import RETAIL_TOOL_STATUS_MESSAGES
        
        hooks, tracker = create_tool_status_hooks(
            agent_context,
            tool_messages=RETAIL_TOOL_STATUS_MESSAGES
        )
    
    Example (Healthcare):
        from use_cases.healthcare.tool_status import HEALTHCARE_TOOL_STATUS_MESSAGES
        
        hooks, tracker = create_tool_status_hooks(
            agent_context,
            tool_messages=HEALTHCARE_TOOL_STATUS_MESSAGES,
            workflow_summary="Processing your request...",
            workflow_icon="lifesaver"
        )
    """
    tracker = ToolExecutionTracker(
        agent_context=agent_context,
        tool_messages=tool_messages or {},
        workflow_summary=workflow_summary,
        workflow_icon=workflow_icon,
    )
    hooks = ToolStatusHooks(tracker)
    return hooks, tracker


# =============================================================================
# STREAMING WITH HOSTED TOOL STATUS (FILE_SEARCH, WEB_SEARCH)
# =============================================================================

class HostedToolStreamWrapper:
    """
    Wraps a RunResultStreaming to detect hosted tool events (file_search, web_search).
    
    Hosted tools like FileSearchTool run server-side and don't trigger local 
    on_tool_start/on_tool_end hooks. This wrapper intercepts the raw stream events
    to detect when these tools are called and updates the workflow status accordingly.
    
    The wrapper is transparent - it yields all original events while also triggering
    workflow status updates for hosted tools.
    """
    
    def __init__(self, result: RunResultStreaming, tracker: ToolExecutionTracker):
        self._result = result
        self._tracker = tracker
        self._active_hosted_tools: Dict[str, bool] = {}
    
    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped result."""
        return getattr(self._result, name)
    
    async def stream_events(self):
        """
        Wrap stream_events to detect hosted tool events.
        
        Yields all original events while also triggering workflow status for:
        - response.file_search_call.in_progress / .searching / .completed
        - response.web_search_call.in_progress / .searching / .completed
        """
        async for event in self._result.stream_events():
            # Check for hosted tool events in raw responses
            if isinstance(event, RawResponsesStreamEvent):
                raw_event = event.data
                event_type = getattr(raw_event, 'type', '')
                
                # File search events
                if event_type in ('response.file_search_call.in_progress', 
                                  'response.file_search_call.searching'):
                    if 'file_search' not in self._active_hosted_tools:
                        self._active_hosted_tools['file_search'] = True
                        await self._tracker.add_tool_task("file_search", is_start=True)
                        logger.info(f"File search started (event: {event_type})")
                        
                elif event_type == 'response.file_search_call.completed':
                    if 'file_search' in self._active_hosted_tools:
                        await self._tracker.add_tool_task("file_search", is_start=False)
                        del self._active_hosted_tools['file_search']
                        logger.info("File search completed")
                
                # Web search events (for future use)
                elif event_type in ('response.web_search_call.in_progress',
                                    'response.web_search_call.searching'):
                    if 'web_search' not in self._active_hosted_tools:
                        self._active_hosted_tools['web_search'] = True
                        await self._tracker.add_tool_task("web_search", is_start=True)
                        logger.info(f"Web search started (event: {event_type})")
                        
                elif event_type == 'response.web_search_call.completed':
                    if 'web_search' in self._active_hosted_tools:
                        await self._tracker.add_tool_task("web_search", is_start=False)
                        del self._active_hosted_tools['web_search']
                        logger.info("Web search completed")
            
            # Always yield the original event
            yield event


def wrap_for_hosted_tools(
    result: RunResultStreaming, 
    tracker: ToolExecutionTracker
) -> HostedToolStreamWrapper:
    """
    Wrap a RunResultStreaming to detect hosted tool events for workflow status.
    
    Use this to wrap the result from Runner.run_streamed before passing to
    stream_agent_response. This enables shimmer progress indicators for hosted
    tools like FileSearchTool and WebSearchTool.
    
    Args:
        result: The streaming result from Runner.run_streamed
        tracker: The ToolExecutionTracker for workflow status
        
    Returns:
        A wrapped result that can be passed to stream_agent_response
        
    Usage:
        result = Runner.run_streamed(agent, input, hooks=hooks)
        wrapped_result = wrap_for_hosted_tools(result, tracker)
        
        async for event in stream_agent_response(agent_context, wrapped_result):
            yield event
    """
    return HostedToolStreamWrapper(result, tracker)
