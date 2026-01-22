# Azure OpenAI Adaptations

This document explains what customizations were made to use ChatKit with **Azure OpenAI** instead of the default **OpenAI**, and identifies which components would be unnecessary if using OpenAI directly.

---

## Reference: Official ChatKit Starter App

OpenAI provides an official starter app that demonstrates how ChatKit works with OpenAI directly:

- **Repository**: [github.com/openai/openai-chatkit-starter-app](https://github.com/openai/openai-chatkit-starter-app)
- **Documentation**: [platform.openai.com/docs/guides/chatkit](https://platform.openai.com/docs/guides/chatkit)
- **Widget Gallery**: [widgets.chatkit.studio/gallery](https://widgets.chatkit.studio/gallery)
- **Components Reference**: [widgets.chatkit.studio/components](https://widgets.chatkit.studio/components)

The official starter contains two examples:
1. **`chatkit/`** - Self-hosted ChatKit integration (what we're based on)
2. **`managed-chatkit/`** - Managed ChatKit with hosted workflows

---

## Executive Summary

ChatKit is designed to work with OpenAI directly. This project adds a custom layer to support Azure OpenAI. The key differences are:

| Aspect | With OpenAI (Default) | With Azure OpenAI (This Project) |
|--------|----------------------|----------------------------------|
| **Authentication** | API key | Azure AD / Managed Identity |
| **Client** | `AsyncOpenAI` | `AsyncAzureOpenAI` |
| **Endpoint** | `api.openai.com` | `your-resource.openai.azure.com` |
| **Model reference** | `gpt-4o` (model name) | Deployment name |
| **Custom code needed** | ❌ None | ✅ Client manager, base server |

---

## Comparison: Official Starter vs This Project

### Official OpenAI Starter (`chatkit/backend/app/server.py`)

```python
# From: github.com/openai/openai-chatkit-starter-app/chatkit/backend/app/server.py

from agents import Agent, Runner
from chatkit.agents import AgentContext, stream_agent_response

MODEL = "gpt-4.1-mini"

assistant_agent = Agent[AgentContext[dict[str, Any]]](
    model=MODEL,                              # ← Just the model name!
    name="Starter Assistant",
    instructions="You are a concise, helpful assistant...",
)

class StarterChatServer(ChatKitServer[dict[str, Any]]):
    async def respond(self, thread, item, context):
        agent_context = AgentContext(thread=thread, store=self.store, ...)
        
        # No model override needed - uses OPENAI_API_KEY automatically
        result = Runner.run_streamed(
            assistant_agent,
            agent_input,
            context=agent_context,
            # ← No run_config! Uses default OpenAI client
        )
        
        async for event in stream_agent_response(agent_context, result):
            yield event
```

**Key observation:** The official starter has **NO** client manager, **NO** model wrapper, and **NO** `RunConfig`. It just:
1. Sets `OPENAI_API_KEY` environment variable
2. Defines agent with model name (`gpt-4.1-mini`)
3. Calls `Runner.run_streamed()` directly

### This Project (`base_server.py`)

```python
# From: this project's base_server.py

from agents import Agent, Runner, RunConfig
from agents.models.openai_responses import OpenAIResponsesModel  # ← Azure-specific!
from azure_client import client_manager  # ← Azure-specific!

class BaseChatKitServer(ChatKitServer):
    async def respond(self, thread, input, context):
        # AZURE-SPECIFIC: Get Azure OpenAI client
        client = await client_manager.get_client()
        
        # AZURE-SPECIFIC: Wrap in model class
        azure_model = OpenAIResponsesModel(
            model=settings.azure_openai_deployment,  # ← Deployment name
            openai_client=client,                    # ← Azure client
        )
        
        agent_context = AgentContext(thread=thread, store=self.data_store, ...)
        
        # AZURE-SPECIFIC: Override model in RunConfig
        result = Runner.run_streamed(
            agent,
            agent_input,
            context=agent_context,
            run_config=RunConfig(model=azure_model),  # ← Required for Azure!
        )
        
        async for event in stream_agent_response(agent_context, result):
            yield event
```

### Side-by-Side Comparison

| Aspect | Official Starter (OpenAI) | This Project (Azure OpenAI) |
|--------|---------------------------|----------------------------|
| **Authentication** | `OPENAI_API_KEY` env var | `DefaultAzureCredential` |
| **Client creation** | Automatic (SDK default) | Manual (`AsyncAzureOpenAI`) |
| **Model reference** | `model="gpt-4.1-mini"` on Agent | `OpenAIResponsesModel` wrapper |
| **Runner call** | `Runner.run_streamed(agent, input, context)` | `Runner.run_streamed(agent, input, context, run_config=RunConfig(model=...))` |
| **Extra files** | None | `azure_client.py` |
| **Extra imports** | None | `OpenAIResponsesModel`, `RunConfig` |

---

## Files Created/Modified for Azure OpenAI

### 1. `azure_client.py` — **AZURE-SPECIFIC (Would be unnecessary with OpenAI)**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  azure_client.py                                      AZURE-ONLY FILE      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PURPOSE: Create and manage AsyncAzureOpenAI client with Azure AD auth     │
│                                                                             │
│  KEY AZURE-SPECIFIC CODE:                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  from openai import AsyncAzureOpenAI                                │   │
│  │  from azure.identity import DefaultAzureCredential                  │   │
│  │                                                                     │   │
│  │  # Azure AD authentication (not API key)                            │   │
│  │  credential = DefaultAzureCredential()                              │   │
│  │  token_provider = get_bearer_token_provider(                        │   │
│  │      credential,                                                    │   │
│  │      "https://cognitiveservices.azure.com/.default"                │   │
│  │  )                                                                  │   │
│  │                                                                     │   │
│  │  # Azure-specific client                                            │   │
│  │  client = AsyncAzureOpenAI(                                         │   │
│  │      azure_endpoint=endpoint,           # ← Azure resource URL      │   │
│  │      azure_ad_token_provider=token,     # ← Azure AD (not API key)  │   │
│  │      api_version="2025-01-01-preview",  # ← Azure API versioning    │   │
│  │  )                                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  WITH OPENAI DIRECTLY: This entire file would be replaced by:              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  from openai import AsyncOpenAI                                     │   │
│  │  client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Why it exists:**
- Azure OpenAI uses Azure AD tokens (Managed Identity, CLI credentials) instead of API keys
- Azure requires `azure_endpoint` (resource URL) + `api_version` parameters
- Token refresh is automatic but requires `get_bearer_token_provider`

**With OpenAI directly:** Delete this file. Use `AsyncOpenAI(api_key=...)` directly.

---

### 2. `base_server.py` — **CONTAINS AZURE-SPECIFIC MODEL WRAPPING**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  base_server.py                                       MIXED (Azure + Core) │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  AZURE-SPECIFIC SECTION (respond method, lines 140-175):                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  # Get Azure OpenAI client                                          │   │
│  │  client = await client_manager.get_client()  # ← Azure client mgr   │   │
│  │                                                                     │   │
│  │  # Create the Azure OpenAI model wrapper                            │   │
│  │  azure_model = OpenAIResponsesModel(                               │   │
│  │      model=settings.azure_openai_deployment,  # ← Deployment name   │   │
│  │      openai_client=client,                    # ← Azure client      │   │
│  │  )                                                                  │   │
│  │                                                                     │   │
│  │  # Run agent with Azure model                                       │   │
│  │  result = Runner.run_streamed(                                      │   │
│  │      agent,                                                         │   │
│  │      agent_input,                                                   │   │
│  │      context=agent_context,                                         │   │
│  │      run_config=RunConfig(model=azure_model), # ← Override model    │   │
│  │  )                                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  WITH OPENAI DIRECTLY: Replace with:                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  # No client manager needed, no model override                      │   │
│  │  result = Runner.run_streamed(                                      │   │
│  │      agent,                                                         │   │
│  │      agent_input,                                                   │   │
│  │      context=agent_context,                                         │   │
│  │      # Uses OPENAI_API_KEY env var automatically                    │   │
│  │  )                                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  The base server pattern itself IS still useful for:                       │
│  • Agent abstraction (get_agent method)                                    │
│  • Action handling                                                         │
│  • Post-respond hooks                                                      │
│  But the Azure-specific client/model code would be removed.                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Why it exists:**
- The `agents` SDK (OpenAI's Agents SDK) defaults to using `OPENAI_API_KEY`
- For Azure, we must explicitly create an `OpenAIResponsesModel` with our Azure client
- `RunConfig(model=azure_model)` overrides the default model

**With OpenAI directly:** Remove `azure_client` import, remove `OpenAIResponsesModel` wrapping, let the Runner use its default OpenAI client.

---

### 3. `config.py` — **CONTAINS AZURE-SPECIFIC SETTINGS**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  config.py                                            MIXED (Azure + App)  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  AZURE-SPECIFIC SETTINGS:                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  # Azure OpenAI Configuration                                       │   │
│  │  azure_openai_endpoint: str       # ← Azure resource URL            │   │
│  │  azure_openai_deployment: str     # ← Deployment name (not model)   │   │
│  │  azure_openai_api_version: str    # ← Azure versioning              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  WITH OPENAI DIRECTLY: Replace with:                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  openai_api_key: str              # ← Just the API key              │   │
│  │  openai_model: str = "gpt-4o"     # ← Model name                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Comparison

### With Azure OpenAI (Current)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AZURE OPENAI ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────┐                                                      │
│  │   User Request    │                                                      │
│  └─────────┬─────────┘                                                      │
│            ▼                                                                │
│  ┌───────────────────┐                                                      │
│  │   base_server.py  │  ← Custom abstraction layer                          │
│  │   respond()       │                                                      │
│  └─────────┬─────────┘                                                      │
│            ▼                                                                │
│  ┌───────────────────┐      ┌───────────────────┐                          │
│  │ azure_client.py   │ ──►  │ DefaultAzure      │  ← Azure AD auth         │
│  │ client_manager    │      │ Credential        │                          │
│  └─────────┬─────────┘      └───────────────────┘                          │
│            ▼                                                                │
│  ┌───────────────────┐                                                      │
│  │ AsyncAzureOpenAI  │  ← Azure-specific client                             │
│  │ + token provider  │                                                      │
│  └─────────┬─────────┘                                                      │
│            ▼                                                                │
│  ┌───────────────────┐                                                      │
│  │ OpenAIChat        │  ← Wrapper to use Azure client with Agents SDK       │
│  │ CompletionsModel  │                                                      │
│  └─────────┬─────────┘                                                      │
│            ▼                                                                │
│  ┌───────────────────┐                                                      │
│  │   agents.Runner   │  ← OpenAI Agents SDK                                 │
│  │   run_streamed()  │                                                      │
│  └─────────┬─────────┘                                                      │
│            ▼                                                                │
│  ┌───────────────────┐                                                      │
│  │   Azure OpenAI    │  ← your-resource.openai.azure.com                    │
│  │   (GPT-4o deploy) │                                                      │
│  └───────────────────┘                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### With OpenAI Directly (Simplified)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPENAI DIRECT ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────┐                                                      │
│  │   User Request    │                                                      │
│  └─────────┬─────────┘                                                      │
│            ▼                                                                │
│  ┌───────────────────┐                                                      │
│  │   use case server │  ← Could extend ChatKitServer directly               │
│  │   respond()       │                                                      │
│  └─────────┬─────────┘                                                      │
│            ▼                                                                │
│  ┌───────────────────┐                                                      │
│  │   agents.Runner   │  ← OpenAI Agents SDK                                 │
│  │   run_streamed()  │     Uses OPENAI_API_KEY automatically                │
│  └─────────┬─────────┘                                                      │
│            ▼                                                                │
│  ┌───────────────────┐                                                      │
│  │     OpenAI API    │  ← api.openai.com                                    │
│  │     (gpt-4o)      │                                                      │
│  └───────────────────┘                                                      │
│                                                                             │
│  NO azure_client.py, NO OpenAIResponsesModel wrapper                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Necessity Matrix

| Component | With Azure OpenAI | With OpenAI Directly | Notes |
|-----------|-------------------|---------------------|-------|
| `azure_client.py` | ✅ **Required** | ❌ **Delete** | Azure AD auth, token provider |
| `base_server.py` | ✅ Required (Azure model wrapping) | ⚠️ **Simplify** | Remove Azure client/model code, keep abstraction |
| `config.py` Azure settings | ✅ Required | ❌ **Replace** | Use `OPENAI_API_KEY` instead |
| `OpenAIResponsesModel` | ✅ Required | ❌ **Remove** | Only needed to inject Azure client |
| `RunConfig(model=...)` | ✅ Required | ❌ **Remove** | Agents SDK uses default OpenAI |
| `DefaultAzureCredential` | ✅ Required | ❌ **Remove** | Azure-specific auth |
| **ChatKitServer** | ✅ Required | ✅ Required | Core ChatKit functionality |
| **Agent/Tools** | ✅ Required | ✅ Required | Your business logic |
| **Widgets** | ✅ Required | ✅ Required | UI components |
| **Store** | ✅ Required | ✅ Required | Data persistence |

---

## Code Changes Summary

### To Convert from Azure OpenAI → OpenAI Direct

1. **Delete** `azure_client.py`

2. **Modify** `config.py`:
   ```python
   # Remove these:
   azure_openai_endpoint: str
   azure_openai_deployment: str
   azure_openai_api_version: str
   
   # Add:
   openai_model: str = "gpt-4o"
   # API key is read from OPENAI_API_KEY env var automatically
   ```

3. **Simplify** `base_server.py` respond method:
   ```python
   # BEFORE (Azure):
   client = await client_manager.get_client()
   azure_model = OpenAIResponsesModel(
       model=settings.azure_openai_deployment,
       openai_client=client,
   )
   result = Runner.run_streamed(
       agent, agent_input, context=agent_context,
       run_config=RunConfig(model=azure_model),
   )
   
   # AFTER (OpenAI Direct):
   result = Runner.run_streamed(
       agent, agent_input, context=agent_context,
       # No run_config needed - uses OPENAI_API_KEY automatically
   )
   ```

4. **Remove** imports:
   ```python
   # Remove from base_server.py:
   from agents.models.openai_responses import OpenAIResponsesModel
   from agents import RunConfig
   from azure_client import client_manager
   ```

5. **Update** `.env`:
   ```env
   # Remove:
   AZURE_OPENAI_ENDPOINT=...
   AZURE_OPENAI_DEPLOYMENT=...
   AZURE_OPENAI_API_VERSION=...
   
   # Add:
   OPENAI_API_KEY=sk-...
   ```

---

## Why Use Azure OpenAI Instead of OpenAI?

| Reason | Azure OpenAI Advantage |
|--------|----------------------|
| **Enterprise compliance** | Data stays in your Azure region |
| **Managed Identity** | No API keys to manage/rotate |
| **Private endpoints** | Keep traffic on Azure backbone |
| **Azure integration** | RBAC, logging, monitoring built-in |
| **Cost management** | Azure billing, reservations, budgets |
| **SLA guarantees** | Enterprise SLA from Microsoft |

---

## Dependencies

### Azure-Specific Python Packages

```
# These are only needed for Azure OpenAI:
azure-identity>=1.19.0     # DefaultAzureCredential
```

### Shared Packages

```
# These are needed regardless of OpenAI vs Azure:
openai>=1.93.0             # OpenAI SDK (includes AsyncAzureOpenAI)
openai-agents>=0.1.0       # Agents SDK (Runner, Agent, etc.)
openai-chatkit>=0.1.0      # ChatKit server/widgets
fastapi
uvicorn
```

---

## Summary

This project adds **three main components** to support Azure OpenAI:

1. **`azure_client.py`** - Manages Azure AD authentication and `AsyncAzureOpenAI` client
2. **Azure-specific code in `base_server.py`** - Wraps the client in `OpenAIResponsesModel` and passes to `RunConfig`
3. **Azure settings in `config.py`** - Endpoint, deployment name, API version

**With OpenAI directly**, you would:
- Delete `azure_client.py`
- Simplify `base_server.py` (remove ~15 lines of Azure wrapping)
- Use `OPENAI_API_KEY` environment variable (Agents SDK reads it automatically)
- Remove `azure-identity` from dependencies

The **ChatKitServer**, **Widgets**, **Store**, and **Agent/Tools** are all framework components that remain the same regardless of which OpenAI service you use.

---

## Conversation History Loading

The official ChatKit starter app includes a pattern for loading conversation history on each request, enabling multi-turn conversations with full context. **This project now implements this feature.**

### Current Implementation (`base_server.py`)

```python
MAX_HISTORY_ITEMS = 100

async def respond(self, thread, input, context):
    # Load full conversation history from the store
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
    relevant_items = [
        item for item in thread_items_page.data
        if item.type in ("user_message", "assistant_message")
    ]
    
    # Convert the full conversation history to agent input
    agent_input = await converter.to_agent_input(relevant_items)
    
    # Agent now sees full conversation context
    result = Runner.run_streamed(agent, agent_input, context=agent_context, ...)
```

### Comparison with Official Starter

| Aspect | Official Starter | This Project |
|--------|-----------------|--------------|
| **History loading** | Loads last 30 items from store | ✅ Loads up to 100 items |
| **Agent context** | Sees full conversation | ✅ Sees full conversation |
| **Multi-turn memory** | ✅ Supported | ✅ Supported |
| **Filtering** | All items | User & assistant messages only |

---

## Session Context for Natural Language Understanding

This project implements a **session context pattern** that enables the agent to understand natural language references like "the items above" or "return both items".

### The Session Context Structure

```python
# Stored on the server instance
self._session_context = {
    # Customer identification
    "customer_id": "CUST-1001",
    "customer_name": "Jane Smith",
    "customer_tier": "Gold",
    
    # What was shown to user (for NL reference)
    "displayed_orders": [
        {
            "order_id": "ORD-78234",
            "items": [
                {"product_id": "PROD-001", "name": "Blue Wireless Widget", ...},
            ]
        }
    ],
    
    # User's selections (updated by BOTH widget clicks AND typed input)
    "selected_items": [...],
    "reason_code": "DAMAGED",
    "resolution": "FULL_REFUND",
    "shipping_method": "SCHEDULE_PICKUP"
}
```

### Context Injection into Agent

Before each agent call, the session context is summarized and prepended to the user's message:

```python
async def respond(self, thread, input, context):
    # Build context summary
    context_summary = self._build_context_summary()
    
    # Prepend to agent input
    augmented_input = f"""
[CURRENT SESSION STATE]
{context_summary}

User message: {original_user_message}
"""
```

This allows the agent to understand references like:
- "return both items" → Agent knows which items were displayed
- "the order above" → Agent knows which order was shown
- "I want a full refund" → Agent can match to resolution options

---

## Dual-Input Architecture: Text + Widget Convergence

A key feature of this implementation is supporting **both widget button clicks AND natural language text input**, with both converging into the same processing flow.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DUAL-INPUT CONVERGENCE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐              ┌─────────────────┐                      │
│   │  Widget Click   │              │   Text Input    │                      │
│   │  [Full Refund]  │              │ "I want a full  │                      │
│   │     button      │              │    refund"      │                      │
│   └────────┬────────┘              └────────┬────────┘                      │
│            │                                │                               │
│            ▼                                ▼                               │
│   ┌─────────────────┐              ┌─────────────────┐                      │
│   │   action()      │              │   respond()     │                      │
│   │ Direct mapping  │              │  Agent + LLM    │                      │
│   │ from payload    │              │  interprets NL  │                      │
│   └────────┬────────┘              └────────┬────────┘                      │
│            │                                │                               │
│            │                                ▼                               │
│            │                       ┌─────────────────┐                      │
│            │                       │ set_user_       │                      │
│            │                       │ selection tool  │                      │
│            │                       └────────┬────────┘                      │
│            │                                │                               │
│            └────────────┬───────────────────┘                               │
│                         ▼                                                   │
│            ┌─────────────────────────┐                                      │
│            │    SESSION CONTEXT      │  ← Both paths write here!            │
│            │  resolution: FULL_REFUND│                                      │
│            └────────────┬────────────┘                                      │
│                         ▼                                                   │
│            ┌─────────────────────────┐                                      │
│            │ finalize_return_from_   │                                      │
│            │ session() - uses data   │                                      │
│            │ from session context    │                                      │
│            └─────────────────────────┘                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `action()` method | Handles widget button clicks directly (no LLM) |
| `respond()` method | Routes text input through the Agent/LLM |
| `set_user_selection` tool | Agent tool to record typed selections |
| `_session_context` | Shared state that both paths write to |
| `finalize_return_from_session` | Creates return using session data |

### Path 1: Widget Button Click

```python
async def action(self, thread, action, sender, context):
    if action_type == "select_resolution":
        resolution_code = payload.get("resolution")
        self._session_context["resolution"] = resolution_code
        # Show next widget...
```

### Path 2: Natural Language Input

```python
# Agent interprets "I want a full refund" and calls:
@function_tool
async def tool_set_user_selection(ctx, selection_type, selection_code):
    session = ctx.context._session_context
    if selection_type == "resolution":
        session["resolution"] = selection_code
        return "Recorded. Now show shipping options."
```

### Benefits

1. **User choice**: Users can click buttons OR type naturally
2. **Consistent state**: Both paths update the same session context
3. **No duplication**: `finalize_return_from_session` works for both paths
4. **Widget avoidance**: When user types selection, widget is not shown again

---

## Additional Tools for Dual-Input Support

### `set_user_selection` Tool

Records a user's typed selection (reason, resolution, or shipping):

```python
@function_tool(description="Record user's typed selection")
async def tool_set_user_selection(
    ctx: RunContextWrapper,
    selection_type: str,     # "reason", "resolution", or "shipping"
    selection_code: str,     # "FULL_REFUND", "DAMAGED", etc.
) -> str:
    session = ctx.context._session_context
    
    if selection_type == "resolution":
        session["resolution"] = selection_code
        return "Recorded resolution. Now call get_shipping_options."
    # ... similar for reason and shipping
```

### `finalize_return_from_session` Tool

Creates the return using all data collected in session:

```python
@function_tool(description="Create return from session data")
async def tool_finalize_return_from_session(ctx) -> str:
    session = ctx.context._session_context
    
    # All data comes from session - works for both input paths!
    result = create_return_request(
        customer_id=session.get("customer_id"),
        order_id=session["selected_items"][0]["order_id"],
        items=session["selected_items"],
        reason_code=session.get("reason_code"),
        resolution=session.get("resolution"),
        shipping_method=session.get("shipping_method"),
    )
    return f"Return {result['id']} created!"
```

---

## System Prompt Guidance for Dual-Input

The system prompt includes specific instructions for handling typed input:

```
HANDLING USER TYPED SELECTIONS (CRITICAL):
When the user TYPES their selection instead of clicking a button:

1. For RESOLUTION OPTIONS - If user types "full refund", "exchange", etc.:
   - Match their input to: FULL_REFUND, EXCHANGE, STORE_CREDIT, KEEP_WITH_DISCOUNT
   - Use set_user_selection tool with selection_type="resolution"
   - Then call get_shipping_options
   - DO NOT call get_resolution_options again!

CRITICAL - DO NOT LIST OPTIONS IN TEXT:
When you call get_return_reasons, get_resolution_options, or get_shipping_options:
- A widget will automatically appear showing the options
- DO NOT list the options as bullet points in your text response!
- Just ask a simple question like "How would you like to be compensated?"
```

---

## References

### Official OpenAI Resources

| Resource | URL | Description |
|----------|-----|-------------|
| **ChatKit Starter App** | [github.com/openai/openai-chatkit-starter-app](https://github.com/openai/openai-chatkit-starter-app) | Official starter templates (self-hosted + managed) |
| **ChatKit Documentation** | [platform.openai.com/docs/guides/chatkit](https://platform.openai.com/docs/guides/chatkit) | Official ChatKit guide |
| **Widget Gallery** | [widgets.chatkit.studio/gallery](https://widgets.chatkit.studio/gallery) | Visual examples of widgets |
| **Components Reference** | [widgets.chatkit.studio/components](https://widgets.chatkit.studio/components) | Widget component props and styling |
| **Icons Reference** | [widgets.chatkit.studio/icons](https://widgets.chatkit.studio/icons) | Available icons for widgets |

### Key Files in Official Starter

| File | Purpose |
|------|---------|
| `chatkit/backend/app/server.py` | Shows minimal ChatKitServer with OpenAI |
| `chatkit/backend/app/memory_store.py` | In-memory Store implementation |
| `chatkit/frontend/src/components/ChatKitPanel.tsx` | React ChatKit usage |
| `managed-chatkit/` | Alternative using hosted workflows |

### This Project's Key Files

| File | Purpose |
|------|---------|
| `azure_client.py` | Azure AD authentication, `AsyncAzureOpenAI` client |
| `base_server.py` | Azure model wrapping, conversation history, `RunConfig` override |
| `config.py` | Azure OpenAI endpoint, deployment, API version settings |
| **Core Framework (Extensibility)** | |
| `core/domain.py` | PolicyEngine, DomainService base classes (pure logic) |
| `core/data.py` | Repository pattern for data access |
| `core/presentation.py` | WidgetComposer, WidgetTheme base classes |
| `core/orchestration.py` | UseCaseServer base class extending ChatKitServer |
| `core/session.py` | SessionContext, SessionManager for state tracking |
| **Retail Use Case** | |
| `use_cases/retail/server.py` | Retail ChatKit server with dual-input handling |
| `use_cases/retail/domain/policies.py` | ReturnEligibilityPolicy, RefundPolicy |
| `use_cases/retail/presentation/composer.py` | ReturnWidgetComposer |
| `use_cases/retail/tools.py` | Business logic tools for returns processing |
| `use_cases/retail/cosmos_client.py` | Cosmos DB client for data persistence |
| **Healthcare Use Case (Example)** | |
| `use_cases/healthcare/server.py` | Example server demonstrating extensibility |
| `use_cases/healthcare/domain/policies.py` | SchedulingRules, CancellationPolicy |

---

*Document created: January 18, 2026*
*Last updated: January 22, 2026 - Added layered architecture components*
