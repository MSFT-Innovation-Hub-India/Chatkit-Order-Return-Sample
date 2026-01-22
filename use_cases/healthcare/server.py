"""
Healthcare Appointment Scheduling ChatKit Server.

This demonstrates how to use the core framework to create a new use case.
Extends UseCaseServer and implements all required abstract methods.
"""

import logging
from datetime import datetime
from typing import Any, AsyncIterator, Dict

from chatkit.server import ThreadStreamEvent
from chatkit.store import Store, ThreadMetadata
from chatkit.agents import stream_widget

from agents import Agent, function_tool
from agents.run_context import RunContextWrapper

from core.orchestration import UseCaseServer
from core.presentation import WidgetComposer

from .session import AppointmentSessionContext, AppointmentFlowStep
from .presentation import AppointmentWidgetComposer

logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

HEALTHCARE_SYSTEM_PROMPT = """You are a helpful healthcare scheduling assistant for a medical clinic.

Your role is to:
1. Greet patients warmly and ask how you can help
2. Identify the patient by name, date of birth, or phone number
3. Help them schedule, reschedule, or cancel appointments
4. Show available providers and time slots
5. Confirm appointment details and provide next steps

IMPORTANT GUIDELINES:
- Always be professional and empathetic
- Respect patient privacy - don't repeat sensitive information unnecessarily
- Premium and VIP patients get priority scheduling
- Remind patients to arrive 15 minutes early
- Mention any preparation requirements (fasting, bringing documents, etc.)

CRITICAL - DO NOT LIST OPTIONS IN TEXT:
When tools return options (providers, times, dates):
- A widget will automatically appear with buttons
- Just ask a simple question like "Which provider would you prefer?"
- Don't list the options in your text response

FLOW:
1. Greet and ask for patient identification
2. Look up patient using lookup_patient tool
3. Ask what they need (new appointment, reschedule, cancel)
4. For new appointments:
   a. Show available providers
   b. Show appointment types
   c. Show available dates
   d. Show available time slots
   e. Confirm and create appointment
5. Provide confirmation with next steps

CRITICAL - ONE STEP AT A TIME:
- Only call ONE widget-triggering tool per response!
- Wait for user input between each step
- The widgets will guide the patient through the flow

Always use the available tools to get real data. Never make up appointment times or provider information.
"""


# =============================================================================
# AGENT TOOLS (placeholders - would connect to actual data layer)
# =============================================================================

@function_tool(description_override="Look up a patient by name, date of birth, or phone number.")
async def tool_lookup_patient(ctx: RunContextWrapper[Any], search_term: str) -> str:
    """Look up a patient."""
    # Placeholder - would connect to healthcare data layer
    # For demo, return mock data
    ctx.context._show_patient_widget = True
    ctx.context._patient_data = {
        "id": "PAT-001",
        "name": "John Smith",
        "tier": "premium",
        "date_of_birth": "1985-03-15",
        "phone": "(555) 123-4567",
        "insurance": "Blue Cross Blue Shield",
    }
    
    if hasattr(ctx.context, '_session_context'):
        ctx.context._session_context.set_patient("PAT-001", "John Smith", "premium")
    
    return "Found patient: John Smith (Premium member). How can I help you today? Would you like to schedule a new appointment, reschedule an existing one, or cancel an appointment?"


@function_tool(description_override="Get available healthcare providers.")
async def tool_get_providers(ctx: RunContextWrapper[Any], specialty: str = "") -> str:
    """Get available providers."""
    providers = [
        {"id": "DR-001", "name": "Dr. Sarah Johnson", "specialty": "Family Medicine", "rating": 4.9, "next_available": "Tomorrow 9 AM"},
        {"id": "DR-002", "name": "Dr. Michael Chen", "specialty": "Internal Medicine", "rating": 4.7, "next_available": "Today 2 PM"},
        {"id": "DR-003", "name": "Dr. Emily Williams", "specialty": "Family Medicine", "rating": 4.8, "next_available": "Friday 10 AM"},
    ]
    
    ctx.context._show_providers_widget = True
    ctx.context._providers_data = providers
    
    if hasattr(ctx.context, '_session_context'):
        ctx.context._session_context.set_displayed_providers(providers)
    
    return "[WIDGET WILL DISPLAY PROVIDERS - Just ask: Which provider would you prefer?]"


@function_tool(description_override="Get available appointment types.")
async def tool_get_appointment_types(ctx: RunContextWrapper[Any]) -> str:
    """Get appointment types."""
    types = [
        {"code": "new_patient", "label": "New Patient Visit", "duration": 60},
        {"code": "follow_up", "label": "Follow-up Visit", "duration": 30},
        {"code": "routine_checkup", "label": "Routine Checkup", "duration": 30},
        {"code": "consultation", "label": "Consultation", "duration": 45},
    ]
    
    ctx.context._show_types_widget = True
    ctx.context._types_data = types
    
    return "[WIDGET WILL DISPLAY TYPES - Just ask: What type of appointment would you like?]"


@function_tool(description_override="Get available time slots for a provider on a date.")
async def tool_get_available_slots(ctx: RunContextWrapper[Any], provider_id: str, date: str) -> str:
    """Get available time slots."""
    # Placeholder - would call ScheduleCalculator from domain layer
    slots = [
        {"time": "9:00 AM", "start_time": f"{date}T09:00:00"},
        {"time": "10:00 AM", "start_time": f"{date}T10:00:00"},
        {"time": "11:00 AM", "start_time": f"{date}T11:00:00"},
        {"time": "2:00 PM", "start_time": f"{date}T14:00:00"},
        {"time": "3:00 PM", "start_time": f"{date}T15:00:00"},
    ]
    
    ctx.context._show_slots_widget = True
    ctx.context._slots_data = slots
    
    if hasattr(ctx.context, '_session_context'):
        ctx.context._session_context.set_displayed_slots(slots)
    
    return "[WIDGET WILL DISPLAY TIME SLOTS - Just ask: Which time works best for you?]"


@function_tool(description_override="Create an appointment after all information is collected.")
async def tool_create_appointment(
    ctx: RunContextWrapper[Any],
    patient_id: str,
    provider_id: str,
    appointment_type: str,
    start_time: str,
    reason: str,
) -> str:
    """Create an appointment."""
    # Placeholder - would call AppointmentBuilder from domain layer
    # and save via repository
    
    appointment = {
        "id": f"APPT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "patient_id": patient_id,
        "provider_id": provider_id,
        "provider_name": "Dr. Sarah Johnson",
        "appointment_type": appointment_type,
        "date": "January 23, 2026",
        "time": "9:00 AM",
        "location": "Main Clinic - Room 102",
        "status": "scheduled",
    }
    
    ctx.context._show_confirmation_widget = True
    ctx.context._confirmation_data = appointment
    
    if hasattr(ctx.context, '_session_context'):
        ctx.context._session_context.flow_step = AppointmentFlowStep.APPOINTMENT_CREATED
    
    return f"Appointment {appointment['id']} has been scheduled! A confirmation email has been sent."


# =============================================================================
# SERVER IMPLEMENTATION
# =============================================================================

class HealthcareChatKitServer(UseCaseServer):
    """
    ChatKit server for healthcare appointment scheduling.
    
    Demonstrates how to create a new use case by extending UseCaseServer.
    """
    
    def __init__(self, data_store: Store):
        """Initialize the healthcare server."""
        super().__init__(data_store, session_context_class=AppointmentSessionContext)
        self._agent = None
    
    def get_system_prompt(self) -> str:
        """Return the system prompt for healthcare scheduling."""
        return HEALTHCARE_SYSTEM_PROMPT
    
    def get_agent(self) -> Agent:
        """Return the healthcare scheduling agent."""
        if self._agent is None:
            self._agent = Agent(
                name="Healthcare Scheduling Assistant",
                instructions=self.get_system_prompt(),
                tools=[
                    tool_lookup_patient,
                    tool_get_providers,
                    tool_get_appointment_types,
                    tool_get_available_slots,
                    tool_create_appointment,
                ],
            )
        return self._agent
    
    def create_widget_composer(self) -> WidgetComposer:
        """Create the healthcare widget composer."""
        return AppointmentWidgetComposer()
    
    def _register_tools(self):
        """Register tools with the tool registry."""
        self.tool_registry.register(
            name="lookup_patient",
            description="Look up a patient",
            function=tool_lookup_patient,
            category="patient",
        )
        self.tool_registry.register(
            name="get_providers",
            description="Get available providers",
            function=tool_get_providers,
            category="scheduling",
        )
        self.tool_registry.register(
            name="get_appointment_types",
            description="Get appointment types",
            function=tool_get_appointment_types,
            category="scheduling",
        )
        self.tool_registry.register(
            name="get_available_slots",
            description="Get available time slots",
            function=tool_get_available_slots,
            category="scheduling",
        )
        self.tool_registry.register(
            name="create_appointment",
            description="Create an appointment",
            function=tool_create_appointment,
            category="scheduling",
        )
    
    async def handle_action(
        self,
        thread: ThreadMetadata,
        action_type: str,
        payload: Dict[str, Any],
        session: AppointmentSessionContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle widget actions."""
        logger.info(f"Handling healthcare action: {action_type}, payload: {payload}")
        
        if action_type == "select_provider":
            session.set_provider(
                provider_id=payload.get("provider_id", ""),
                name=payload.get("name", ""),
                specialty=payload.get("specialty", ""),
            )
            # Show appointment types
            types = [
                {"code": "new_patient", "label": "New Patient Visit", "duration": 60},
                {"code": "follow_up", "label": "Follow-up Visit", "duration": 30},
                {"code": "routine_checkup", "label": "Routine Checkup", "duration": 30},
            ]
            widget = self.widget_composer.compose("appointment_types", types, thread.id)
            async for event in stream_widget(thread, widget):
                yield event
        
        elif action_type == "select_appointment_type":
            session.set_appointment_type(payload.get("appointment_type", ""))
            # Show time slots (simplified - would show date picker first in full impl)
            slots = [
                {"time": "9:00 AM", "start_time": "2026-01-23T09:00:00"},
                {"time": "10:00 AM", "start_time": "2026-01-23T10:00:00"},
                {"time": "2:00 PM", "start_time": "2026-01-23T14:00:00"},
            ]
            widget = self.widget_composer.compose("time_slots", slots, thread.id)
            async for event in stream_widget(thread, widget):
                yield event
        
        elif action_type == "select_time":
            session.set_time(datetime.fromisoformat(payload.get("start_time", "")))
            # Show confirmation
            confirmation = {
                "id": f"APPT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "provider_name": session.provider_name,
                "date": "January 23, 2026",
                "time": payload.get("time", ""),
                "appointment_type": session.appointment_type,
                "location": "Main Clinic - Room 102",
            }
            widget = self.widget_composer.compose("confirmation", confirmation, thread.id)
            async for event in stream_widget(thread, widget):
                yield event
        
        elif action_type == "cancel_appointment":
            # Handle cancellation
            logger.info(f"Cancelling appointment: {payload.get('appointment_id')}")
            # Would call CancellationPolicy and update database
    
    async def post_respond_hook(
        self,
        thread: ThreadMetadata,
        agent_context: Any,
        session: AppointmentSessionContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Stream widgets after agent response."""
        thread_id = thread.id
        
        # Patient widget
        if getattr(agent_context, '_show_patient_widget', False):
            patient_data = getattr(agent_context, '_patient_data', {})
            if patient_data:
                widget = self.widget_composer.compose("patient_card", patient_data, thread_id)
                async for event in stream_widget(thread, widget):
                    yield event
        
        # Providers widget
        if getattr(agent_context, '_show_providers_widget', False):
            providers_data = getattr(agent_context, '_providers_data', [])
            if providers_data:
                widget = self.widget_composer.compose("providers", providers_data, thread_id)
                async for event in stream_widget(thread, widget):
                    yield event
        
        # Appointment types widget
        if getattr(agent_context, '_show_types_widget', False):
            types_data = getattr(agent_context, '_types_data', [])
            if types_data:
                widget = self.widget_composer.compose("appointment_types", types_data, thread_id)
                async for event in stream_widget(thread, widget):
                    yield event
        
        # Time slots widget
        if getattr(agent_context, '_show_slots_widget', False):
            slots_data = getattr(agent_context, '_slots_data', [])
            if slots_data:
                widget = self.widget_composer.compose("time_slots", slots_data, thread_id)
                async for event in stream_widget(thread, widget):
                    yield event
        
        # Confirmation widget
        if getattr(agent_context, '_show_confirmation_widget', False):
            confirmation_data = getattr(agent_context, '_confirmation_data', {})
            if confirmation_data:
                widget = self.widget_composer.compose("confirmation", confirmation_data, thread_id)
                async for event in stream_widget(thread, widget):
                    yield event
