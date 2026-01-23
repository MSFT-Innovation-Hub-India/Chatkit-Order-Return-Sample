# Extending Workflow Status to New Domains

This guide explains how to add ChatGPT-style tool execution status indicators to new domain use cases.

## Overview

The workflow status feature provides real-time progress indicators when the agent executes tools:

```
✨ Working on it...
  ○ Looking up customer...      ← Shimmer animation while running
  ✓ Customer found              ← Checkmark when complete
  ○ Fetching orders...
  ✓ Orders retrieved
```

The framework is **generic** and can be extended to any domain (healthcare, banking, travel, etc.).

## How It Works: End-to-End Implementation

This feature uses a coordinated **frontend-backend architecture** with Server-Sent Events (SSE) for real-time updates.

### Visual Effect

The "lightning" shimmer effect you see is a **skeleton loading animation** built into ChatKit's React components. When a task is in-progress (unfilled circle ○), ChatKit renders a horizontal shimmer animation across the status text, providing visual feedback that work is happening.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  BACKEND (Python)                                                               │
│  ─────────────────                                                              │
│                                                                                 │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────────┐     │
│  │  OpenAI Agents  │───▶│  ToolStatusHooks │───▶│  AgentContext          │     │
│  │  SDK Runner     │    │  (RunHooks)      │    │  • start_workflow()     │     │
│  │                 │    │                  │    │  • add_workflow_task()  │     │
│  │  Calls tools    │    │  on_tool_start() │    │  • update_workflow_task()│    │
│  │  during agent   │    │  on_tool_end()   │    │  • end_workflow()       │     │
│  │  execution      │    │                  │    │                         │     │
│  └─────────────────┘    └──────────────────┘    └───────────┬─────────────┘     │
│                                                              │                  │
│                                                              ▼                  │
│                                              ┌───────────────────────────────┐  │
│                                              │  SSE Stream (JSON events)     │  │
│                                              │  {"type": "workflow.start"}   │  │
│                                              │  {"type": "workflow.task"}    │  │
│                                              │  {"type": "workflow.update"}  │  │
│                                              │  {"type": "workflow.end"}     │  │
│                                              └───────────────┬───────────────┘  │
└──────────────────────────────────────────────────────────────┼──────────────────┘
                                                               │
                                                               │ HTTP SSE
                                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (React)                                                               │
│  ────────────────                                                               │
│                                                                                 │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────────────┐ │
│  │  ChatKit SSE Client     │───▶│  @openai/chatkit-react Components           │ │
│  │                         │    │                                             │ │
│  │  Receives workflow      │    │  • Workflow component (collapsible header)  │ │
│  │  events from backend    │    │  • Task list with status icons              │ │
│  │                         │    │  • Shimmer animation for in-progress        │ │
│  │                         │    │  • Checkmark icons for completed            │ │
│  └─────────────────────────┘    └─────────────────────────────────────────────┘ │
│                                                                                 │
│                                              ┌─────────────────────────────────┐│
│                                              │  Visual Output:                 ││
│                                              │                                 ││
│                                              │  ✨ Working on it...            ││
│                                              │    ░░░░░░░░░░░░░░░ (shimmer)    ││
│                                              │    ○ Looking up customer...     ││
│                                              │    ✓ Customer found             ││
│                                              │                                 ││
│                                              └─────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Backend Components

| Component | File | Purpose |
|-----------|------|---------|
| `ToolStatusHooks` | `workflow_status.py` (root) | Implements `RunHooks` interface from OpenAI Agents SDK. Receives callbacks when tools start/end. |
| `ToolExecutionTracker` | `workflow_status.py` (root) | Manages workflow state, tracks task indices, calls ChatKit's workflow API. |
| `create_tool_status_hooks()` | `workflow_status.py` (root) | Factory function to create hooks with domain-specific messages. |
| Domain Messages | `use_cases/*/tool_status.py` | Maps tool names to user-friendly status text and icons. |

### Frontend Components (ChatKit React)

| Component | Package | Purpose |
|-----------|---------|---------|
| `ThreadMessages` | `@openai/chatkit-react` | Renders conversation including workflow indicators |
| Workflow UI | Built into ChatKit | Renders collapsible progress section with shimmer animation |
| SSE Handler | Built into ChatKit | Receives and processes workflow events from backend |

### Event Flow

1. **User sends message** → Backend receives request

2. **Agent starts processing** → No workflow shown yet (lazy initialization)

3. **First tool called** → Backend sends workflow events:
   ```json
   {"type": "workflow.start", "workflow": {"type": "custom", "summary": {...}, "tasks": []}}
   {"type": "workflow.task", "task": {"title": "Looking up customer...", "icon": "search"}}
   ```

4. **Frontend receives SSE** → ChatKit renders workflow with shimmer animation

5. **Tool completes** → Backend sends update:
   ```json
   {"type": "workflow.update", "task": {"title": "✓ Customer found", "icon": "check-circle-filled"}, "index": 0}
   ```

6. **Frontend updates** → Shimmer stops, checkmark appears

7. **All tools done** → Backend ends workflow:
   ```json
   {"type": "workflow.end", "expanded": false}
   ```

8. **Frontend collapses** → Workflow section minimizes

### Key Code: Backend Hook Implementation

```python
class ToolStatusHooks(RunHooks):
    """Intercepts tool execution to stream status updates."""
    
    async def on_tool_start(self, context, agent, tool):
        # Add task with in-progress status
        task = CustomTask(
            type="custom",
            title="Looking up customer...",
            icon="search",
        )
        await self.agent_context.add_workflow_task(task)
    
    async def on_tool_end(self, context, agent, tool, result):
        # Update task to completed status
        task = CustomTask(
            type="custom", 
            title="✓ Customer found",
            icon="check-circle-filled",
        )
        await self.agent_context.update_workflow_task(task, task_index)
```

### Key Code: Integration in Server

```python
# In your domain's server.py respond() method:

from workflow_status import create_tool_status_hooks, wrap_for_hosted_tools
from use_cases.retail.tool_status import RETAIL_TOOL_STATUS_MESSAGES

# Create hooks with domain-specific messages
hooks, tracker = create_tool_status_hooks(
    agent_context,
    tool_messages=RETAIL_TOOL_STATUS_MESSAGES,
)

# Pass hooks to the agent runner
result = Runner.run_streamed(
    agent,
    agent_input,
    context=agent_context,
    hooks=hooks,  # <-- This enables the status streaming
    run_config=RunConfig(model=azure_model),
)

# Wrap result for hosted tools (file_search, web_search)
# This enables shimmer progress for server-side tools that don't trigger on_tool_start/end
wrapped_result = wrap_for_hosted_tools(result, tracker)

# Stream response (includes workflow events automatically)
async for event in stream_agent_response(agent_context, wrapped_result):
    yield event

# Clean up when done
await tracker.end_workflow_if_started()
```

### Hosted Tools (FileSearchTool, WebSearchTool)

Hosted tools like `FileSearchTool` run server-side and don't trigger the normal `on_tool_start`/`on_tool_end` hooks. The `wrap_for_hosted_tools()` function intercepts the raw stream events to detect when these tools are called:

| Event Type | Detected By |
|------------|-------------|
| `response.file_search_call.in_progress` | File search starting |
| `response.file_search_call.searching` | File search in progress |
| `response.file_search_call.completed` | File search done |
| `response.web_search_call.*` | Web search events (similar) |

Add entries to your `tool_status.py` for these hosted tools:

```python
RETAIL_TOOL_STATUS_MESSAGES = {
    # ... your function tools ...
    
    # Hosted tools (FileSearchTool, WebSearchTool)
    "file_search": (
        "Searching policy documents...",
        "Policy information found",
        "book-open",
    ),
    "web_search": (
        "Searching the web...",
        "Results found",
        "globe",
    ),
}
```

### ChatKit Workflow API

The backend uses these ChatKit `AgentContext` methods:

| Method | Purpose |
|--------|---------|
| `start_workflow(workflow)` | Initialize workflow with summary/header |
| `add_workflow_task(task)` | Add a new task (in-progress state) |
| `update_workflow_task(task, index)` | Update existing task (completed state) |
| `end_workflow(expanded=False)` | Close workflow, collapse UI |

### Why Lazy Initialization?

The workflow only starts when the **first tool is actually called**:

- **Simple text responses** (e.g., "Hello!") → No tools → No workflow shown
- **Tool-based responses** (e.g., "Look up my orders") → Tools called → Workflow appears

This avoids showing "Working on it..." for every message, only when actual work happens.

## File Structure

```
workflow_status.py              # Generic framework (at root, reusable)

use_cases/
├── retail/
│   └── tool_status.py          # RETAIL_TOOL_STATUS_MESSAGES
│
├── healthcare/
│   └── tool_status.py          # HEALTHCARE_TOOL_STATUS_MESSAGES
│
└── [your_domain]/
    └── tool_status.py          # YOUR_TOOL_STATUS_MESSAGES
```

## Step-by-Step Guide

### Step 1: Create Tool Status Messages

Create `use_cases/[your_domain]/tool_status.py`:

```python
"""
[Your Domain]-specific tool status messages for workflow indicators.

Each tool maps to (start_message, end_message, icon) tuples.
"""

from typing import Dict

YOUR_DOMAIN_TOOL_STATUS_MESSAGES: Dict[str, tuple] = {
    # Format: "tool_function_name": ("In-progress message", "Completed message", "icon")
    
    "your_tool_name": (
        "Doing something...",    # Shown while tool runs
        "Something done",        # Shown when tool completes
        "sparkle",               # ChatKit icon name
    ),
    
    "another_tool": (
        "Processing data...",
        "Data processed",
        "document",
    ),
}
```

### Step 2: Integrate in Your Server

In your domain's `server.py`, add the workflow status hooks:

```python
from workflow_status import create_tool_status_hooks, wrap_for_hosted_tools
from use_cases.your_domain.tool_status import YOUR_DOMAIN_TOOL_STATUS_MESSAGES

async def respond(self, thread, agent_context):
    # ... your existing code ...
    
    # Create workflow status hooks
    hooks, tracker = create_tool_status_hooks(
        agent_context,
        tool_messages=YOUR_DOMAIN_TOOL_STATUS_MESSAGES,
        workflow_summary="Processing your request...",  # Optional: custom header
        workflow_icon="sparkle",                        # Optional: custom icon
    )
    
    # Run the agent with hooks
    result = Runner.run_streamed(
        agent,
        agent_input,
        context=agent_context,
        hooks=hooks,  # <-- Pass the hooks here
        run_config=RunConfig(model=azure_model),
    )
    
    # Wrap for hosted tools (file_search, web_search) if using them
    wrapped_result = wrap_for_hosted_tools(result, tracker)
    
    # Stream the response
    async for event in stream_agent_response(agent_context, wrapped_result):
        yield event
    
    # Clean up workflow when done
    await tracker.end_workflow_if_started()
```

## Available Icons

ChatKit supports these icons for status indicators:

| Category | Icons |
|----------|-------|
| **Actions** | `check`, `check-circle`, `check-circle-filled`, `play`, `plus`, `reload`, `write` |
| **Objects** | `calendar`, `cube`, `desktop`, `document`, `globe`, `mail`, `mobile`, `notebook`, `phone`, `suitcase` |
| **People** | `agent`, `profile`, `profile-card`, `user` |
| **Symbols** | `analytics`, `atom`, `bolt`, `bug`, `chart`, `clock`, `compass`, `info`, `lightbulb`, `sparkle`, `sparkle-double`, `star` |
| **Other** | `book-open`, `book-closed`, `images`, `lab`, `lifesaver`, `map-pin`, `maps`, `search`, `settings-slider`, `wreath` |

## Configuration Options

The `create_tool_status_hooks` function accepts these parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_context` | `AgentContext` | Required | The ChatKit agent context |
| `tool_messages` | `Dict[str, tuple]` | `{}` | Tool name → (start, end, icon) mapping |
| `workflow_summary` | `str` | `"Working on it..."` | Header text shown during execution |
| `workflow_icon` | `str` | `"sparkle"` | Icon for the workflow header |

## Example: Healthcare Domain

```python
# use_cases/healthcare/tool_status.py

HEALTHCARE_TOOL_STATUS_MESSAGES = {
    "lookup_patient": (
        "Looking up patient record...",
        "Patient found",
        "search",
    ),
    "get_available_slots": (
        "Checking available appointments...",
        "Slots found",
        "calendar",
    ),
    "book_appointment": (
        "Booking your appointment...",
        "Appointment confirmed",
        "check-circle-filled",
    ),
    "verify_insurance": (
        "Verifying insurance coverage...",
        "Coverage verified",
        "check-circle",
    ),
}
```

Usage in healthcare server:

```python
hooks, tracker = create_tool_status_hooks(
    agent_context,
    tool_messages=HEALTHCARE_TOOL_STATUS_MESSAGES,
    workflow_summary="Processing your healthcare request...",
    workflow_icon="lifesaver"
)
```

## How It Works

1. **Workflow starts** when the first tool is called (lazy initialization)
2. **Each tool** gets a status task showing "in-progress" message
3. **When tool completes**, status updates to show "completed" with checkmark
4. **Workflow ends** when streaming is done (collapses automatically)

This provides transparency without showing unnecessary indicators for simple text responses.

## Fallback Behavior

If a tool is not in your `tool_messages` mapping, it falls back to:
- Start: `"Processing..."`
- End: `"Done"`
- Icon: `"sparkle"`

This ensures all tools show some status, even if not explicitly mapped.
