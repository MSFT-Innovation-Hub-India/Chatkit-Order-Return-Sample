# Dual-Input Architecture: Text + Widget

A key feature of this ChatKit implementation is supporting **both widget button clicks AND natural language text input**, with both converging into the same processing flow.

## Overview

This architecture enables users to interact with the assistant in two ways:

| Input Mode | How It Works | Response Time |
|------------|--------------|---------------|
| **Widget Click** | Direct action execution—no LLM call needed | ⚡ Immediate |
| **Text Input** | Agent interprets intent via LLM, then executes | 🔄 Slightly longer |

Both modes converge to the **same application state**, ensuring a consistent experience regardless of how the user interacts.

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INPUT                                      │
│                                                                         │
│   ┌─────────────────┐              ┌─────────────────┐                  │
│   │  Widget Click   │              │   Text Input    │                  │
│   │  [Full Refund]  │              │ "I want a full  │                  │
│   │     button      │              │    refund"      │                  │
│   └────────┬────────┘              └────────┬────────┘                  │
│            │                                │                           │
│            ▼                                ▼                           │
│   ┌─────────────────┐              ┌─────────────────┐                  │
│   │   action()      │              │   Agent/LLM     │                  │
│   │ Direct mapping  │              │  Interprets NL  │                  │
│   │ from payload    │              │  + uses tools   │                  │
│   └────────┬────────┘              └────────┬────────┘                  │
│            │                                │                           │
│            └────────────┬───────────────────┘                           │
│                         ▼                                               │
│            ┌─────────────────────────┐                                  │
│            │    SESSION CONTEXT      │                                  │
│            │  (Unified State Store)  │                                  │
│            │                         │                                  │
│            │  resolution: FULL_REFUND│  ← Both paths update this!       │
│            └────────────┬────────────┘                                  │
│                         ▼                                               │
│            ┌─────────────────────────┐                                  │
│            │   Next Step / Finalize  │                                  │
│            └─────────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Components

| Component | Purpose |
|-----------|---------|
| **`action()` method** | Handles widget button clicks directly (no LLM) |
| **`respond()` method** | Routes text input through the Agent/LLM |
| **`set_user_selection` tool** | Agent tool to record typed selections |
| **Session Context** | Shared state that both paths write to |
| **`finalize_return_from_session`** | Creates return using session data |

## Widget-Driven Flow (Fast Path)

When a user clicks a widget button (e.g., selects a return reason):

1. The click triggers a **direct tool call**—bypassing the LLM entirely
2. The session state is updated immediately
3. The **next widget in the workflow** is automatically presented

This creates a fast, guided experience where each action seamlessly leads to the next step.

### Example: Widget Button Click

```
User clicks [Full Refund] button
  → action() receives {type: "select_resolution", payload: {resolution: "FULL_REFUND"}}
  → Stores in session: resolution = "FULL_REFUND"
  → Shows shipping widget
```

## Text Input Flow (LLM Path)

When a user types instead of clicking (e.g., "I want a full refund"):

1. The text is sent to the **Agent/LLM** for interpretation
2. The Agent identifies intent and calls the appropriate tool
3. The session state converges to the **same state** as the widget path
4. The next widget is presented

### Example: Natural Language Input

```
User types: "I would like a full refund please"
  → respond() sends to Agent with session context
  → Agent recognizes intent, calls set_user_selection(type="resolution", code="FULL_REFUND")
  → Stores in session: resolution = "FULL_REFUND"  
  → Agent calls get_shipping_options
  → Shows shipping widget
```

## State Convergence

Both paths result in the **same outcome**! The key insight is:

- **Widget clicks** update session state directly via `action()` method
- **Text input** updates session state via Agent tools (e.g., `set_user_selection`)
- Both paths write to the **same `SessionContext`** object
- The next step in the workflow is determined by session state, not input method

## Performance Considerations

| Path | Latency | When to Use |
|------|---------|-------------|
| **Widget Click** | ~50-100ms | User wants quick, guided interaction |
| **Text Input** | ~500-2000ms | User prefers natural language or complex requests |

> 💡 **Performance Note**: Widget clicks are faster since they skip the LLM inference step, but both paths result in identical outcomes.

## Implementation Details

### The `action()` Method

The `action()` method in `RetailChatKitServer` handles widget button clicks:

```python
async def action(self, thread, action, sender, context):
    action_type = action.get("type")
    payload = action.get("payload", {})
    
    if action_type == "select_resolution":
        # Direct state update - no LLM needed
        session = self._get_session(thread.id)
        session.resolution = payload.get("resolution")
        
        # Show next widget
        await self._show_shipping_widget(thread)
```

### The `set_user_selection` Tool

The Agent uses this tool to record selections from text input:

```python
@function_tool
def set_user_selection(type: str, code: str) -> str:
    """Record user's selection from natural language input."""
    session = get_current_session()
    
    if type == "resolution":
        session.resolution = code
        return f"Recorded resolution: {code}"
    # ... handle other selection types
```

### Session Context

Both paths write to the same session object:

```python
class ReturnSessionContext:
    customer_id: str
    displayed_orders: list
    selected_items: list
    reason_code: str
    resolution: str        # ← Both paths update this!
    shipping_method: str
```

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall system architecture
- [DIAGRAMS.md](DIAGRAMS.md) - Sequence diagrams showing dual-input flow
- [use_cases/retail/server.py](../use_cases/retail/server.py) - Implementation details
