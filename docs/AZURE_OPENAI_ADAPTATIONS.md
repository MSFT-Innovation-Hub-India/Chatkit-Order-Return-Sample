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

from agents import Agent, Runner, OpenAIChatCompletionsModel, RunConfig  # ← Extra imports!
from azure_client import client_manager  # ← Azure-specific!

class BaseChatKitServer(ChatKitServer):
    async def respond(self, thread, input, context):
        # AZURE-SPECIFIC: Get Azure OpenAI client
        client = await client_manager.get_client()
        
        # AZURE-SPECIFIC: Wrap in model class
        azure_model = OpenAIChatCompletionsModel(
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
| **Model reference** | `model="gpt-4.1-mini"` on Agent | `OpenAIChatCompletionsModel` wrapper |
| **Runner call** | `Runner.run_streamed(agent, input, context)` | `Runner.run_streamed(agent, input, context, run_config=RunConfig(model=...))` |
| **Extra files** | None | `azure_client.py` |
| **Extra imports** | None | `OpenAIChatCompletionsModel`, `RunConfig` |

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
│  │  azure_model = OpenAIChatCompletionsModel(                          │   │
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
- For Azure, we must explicitly create an `OpenAIChatCompletionsModel` with our Azure client
- `RunConfig(model=azure_model)` overrides the default model

**With OpenAI directly:** Remove `azure_client` import, remove `OpenAIChatCompletionsModel` wrapping, let the Runner use its default OpenAI client.

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
│  NO azure_client.py, NO OpenAIChatCompletionsModel wrapper                  │
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
| `OpenAIChatCompletionsModel` | ✅ Required | ❌ **Remove** | Only needed to inject Azure client |
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
   azure_model = OpenAIChatCompletionsModel(
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
   from agents import OpenAIChatCompletionsModel, RunConfig
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
2. **Azure-specific code in `base_server.py`** - Wraps the client in `OpenAIChatCompletionsModel` and passes to `RunConfig`
3. **Azure settings in `config.py`** - Endpoint, deployment name, API version

**With OpenAI directly**, you would:
- Delete `azure_client.py`
- Simplify `base_server.py` (remove ~15 lines of Azure wrapping)
- Use `OPENAI_API_KEY` environment variable (Agents SDK reads it automatically)
- Remove `azure-identity` from dependencies

The **ChatKitServer**, **Widgets**, **Store**, and **Agent/Tools** are all framework components that remain the same regardless of which OpenAI service you use.

---

## Features Not Implemented (Future Consideration)

### Conversation History Loading

The official ChatKit starter app includes a pattern for loading conversation history on each request, enabling multi-turn conversations with full context. **This project does not currently implement this feature.**

#### Official Starter Pattern (`chatkit/backend/app/server.py`)

```python
MAX_RECENT_ITEMS = 30

class StarterChatServer(ChatKitServer[dict[str, Any]]):
    async def respond(self, thread, item, context):
        # Load the last 30 messages from the thread
        items_page = await self.store.load_thread_items(
            thread.id,
            after=None,
            limit=MAX_RECENT_ITEMS,
            order="desc",
            context=context,
        )
        items = list(reversed(items_page.data))
        
        # Convert ALL thread items to agent input (includes history)
        agent_input = await simple_to_agent_input(items)
        
        # Agent now sees full conversation context
        result = Runner.run_streamed(agent, agent_input, context=agent_context)
```

#### This Project's Current Pattern (`base_server.py`)

```python
class BaseChatKitServer(ChatKitServer):
    async def respond(self, thread, input, context):
        # Only converts the current input (no history loading)
        converter = ThreadItemConverter()
        agent_input = await converter.to_agent_input(input)
        
        # Agent only sees the current message
        result = Runner.run_streamed(agent, agent_input, context=agent_context, ...)
```

#### Comparison

| Aspect | Official Starter | This Project |
|--------|-----------------|--------------|
| **History loading** | Loads last 30 items from store | Does not load history |
| **Agent context** | Sees full conversation | Sees only current message |
| **Multi-turn memory** | ✅ Supported (e.g., "Add that task I mentioned") | ❌ Not supported |
| **Stateless operations** | ✅ Works | ✅ Works |

#### Why It Works for the Order Returns App

The current retail use case is **stateless per request**:
- "I want to return my order" → Tool call is self-contained
- "Show my orders" → Fetches from database, no conversation context needed
- "Start return for order 12345" → Tool call is self-contained

Each operation is complete on its own without needing prior conversation context.

#### When to Implement History Loading

Consider implementing history loading for future use cases that require:

1. **Reference resolution**: "Add that task I mentioned earlier"
2. **Follow-up questions**: "What about the second one?"
3. **Contextual refinement**: "Make it shorter" (referring to previous output)
4. **Conversation continuity**: "Can you explain more?"

#### Implementation for Future Use Cases

To add conversation history support to `base_server.py`:

```python
from chatkit.agents import simple_to_agent_input  # Add import

MAX_RECENT_ITEMS = 30

async def respond(self, thread, input, context):
    # Load conversation history
    items_page = await self.data_store.load_thread_items(
        thread.id,
        after=None,
        limit=MAX_RECENT_ITEMS,
        order="desc",
        context=context,
    )
    items = list(reversed(items_page.data))
    
    # Convert with history (instead of just current input)
    agent_input = await simple_to_agent_input(items)
    
    # Rest of the method remains the same...
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

### This Project's Azure-Specific Files

| File | Purpose |
|------|---------|
| `azure_client.py` | Azure AD authentication, `AsyncAzureOpenAI` client |
| `base_server.py` | Azure model wrapping, `RunConfig` override |
| `config.py` | Azure OpenAI endpoint, deployment, API version settings |

---

*Document created: January 18, 2026*
