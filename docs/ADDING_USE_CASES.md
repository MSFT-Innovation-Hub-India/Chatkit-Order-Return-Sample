# Adding New Use Cases

This guide shows how to create a new domain use case (e.g., healthcare, banking, travel) by following the retail example.

## Quick Start

Copy the retail structure and adapt:

```
use_cases/
├── retail/              # Reference implementation
│   ├── __init__.py
│   ├── server.py        # ChatKit server (main logic)
│   ├── tools.py         # Agent function tools
│   ├── tool_status.py   # Status messages for workflow
│   ├── widgets.py       # Widget builders
│   ├── cosmos_client.py # Data access
│   └── cosmos_store.py  # Thread storage
│
└── your_domain/         # Your new use case
    ├── __init__.py
    ├── server.py        # Copy and adapt from retail
    ├── tools.py         # Define your domain tools
    ├── tool_status.py   # Status messages for your tools
    └── ...
```

## Step-by-Step Guide

### 1. Create Folder Structure

```bash
mkdir -p use_cases/healthcare
```

### 2. Define Your Tools (`tools.py`)

```python
from agents import function_tool

@function_tool
def lookup_patient(email: str) -> str:
    """Look up a patient by email."""
    # Your implementation
    return json.dumps({"found": True, "patient": {...}})

@function_tool  
def book_appointment(patient_id: str, date: str, provider: str) -> str:
    """Book an appointment for a patient."""
    # Your implementation
    return json.dumps({"success": True, "appointment_id": "APT-123"})
```

### 3. Add Tool Status Messages (`tool_status.py`)

```python
HEALTHCARE_TOOL_STATUS_MESSAGES = {
    "lookup_patient": (
        "Looking up patient record...",
        "Patient found",
        "search",
    ),
    "book_appointment": (
        "Booking appointment...",
        "Appointment confirmed",
        "calendar",
    ),
}
```

### 4. Create Your Server (`server.py`)

The simplest approach - copy retail/server.py and modify:

```python
from chatkit.server import ChatKitServer
from agents import Agent

class HealthcareChatKitServer(ChatKitServer):
    
    def get_agent(self):
        return Agent(
            name="Healthcare Assistant",
            instructions="You help patients schedule appointments...",
            tools=[
                lookup_patient,
                book_appointment,
                # ... your tools
            ],
        )
    
    async def respond(self, thread, agent_context):
        # Use workflow status hooks
        from workflow_status import create_tool_status_hooks
        from use_cases.healthcare.tool_status import HEALTHCARE_TOOL_STATUS_MESSAGES
        
        hooks, tracker = create_tool_status_hooks(
            agent_context,
            tool_messages=HEALTHCARE_TOOL_STATUS_MESSAGES,
        )
        
        # Run agent with hooks
        result = Runner.run_streamed(
            self.get_agent(),
            agent_input,
            context=agent_context,
            hooks=hooks,
        )
        
        async for event in stream_agent_response(agent_context, result):
            yield event
        
        await tracker.end_workflow_if_started()
```

### 5. Register in `main.py`

```python
# In main.py, switch or add your server:
from use_cases.healthcare import HealthcareChatKitServer

chatkit_server = HealthcareChatKitServer(store=cosmos_store)
```

## What's Reusable from `core/`

| Module | Purpose | How to Use |
|--------|---------|------------|
| `workflow_status.py` | ChatGPT-style progress indicators | Pass your domain's tool_status messages |

## Key Patterns from Retail

### 1. Agent with Tools
```python
agent = Agent(
    name="Your Assistant",
    instructions="...",
    tools=[tool1, tool2, tool3],
)
```

### 2. Widget Actions
```python
Button(
    label="Select",
    onClickAction=ActionConfig(
        type="your_action_type",
        handler="server",
        payload={"key": "value"},
    ),
)
```

### 3. Action Handling
```python
async def action(self, thread, action, sender):
    if action.type == "your_action_type":
        # Handle the widget click
        yield from self.handle_your_action(action.payload)
```

## Example Domains

| Domain | Tools | Widgets |
|--------|-------|---------|
| **Healthcare** | lookup_patient, book_appointment, cancel_appointment | Patient card, appointment slots, confirmation |
| **Banking** | get_account, transfer_funds, dispute_transaction | Account summary, transaction list, dispute form |
| **Travel** | search_flights, book_hotel, modify_reservation | Flight options, hotel cards, itinerary |
| **HR** | lookup_employee, submit_request, check_status | Employee card, request form, status tracker |

## Tips

1. **Start simple** - Get basic chat working before adding widgets
2. **Copy retail patterns** - Don't reinvent; adapt what works
3. **Use tool_status.py** - Makes your tools feel responsive
4. **Test with text first** - Ensure agent logic works before widget polish
