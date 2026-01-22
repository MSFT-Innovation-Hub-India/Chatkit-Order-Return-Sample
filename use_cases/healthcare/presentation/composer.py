"""
Healthcare Widget Composer.

Builds ChatKit widgets for the appointment scheduling flow.
Extends the core WidgetComposer base class.
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from chatkit.widgets import Card, Text, Box, Button, Row, Badge, Divider, Title, Spacer
from chatkit.actions import ActionConfig

from core.presentation import WidgetComposer, WidgetTheme


class AppointmentWidgetComposer(WidgetComposer):
    """
    Composes widgets for healthcare appointment scheduling.
    
    Provides methods to build:
    - Patient profile cards
    - Provider selection widgets
    - Date picker widgets
    - Time slot selection widgets
    - Appointment type selection
    - Confirmation widgets
    """
    
    def get_widget_builders(self) -> Dict[str, Callable]:
        """Return the mapping of widget types to builder methods."""
        return {
            "patient_card": self.compose_patient_card,
            "providers": self.compose_provider_list,
            "appointment_types": self.compose_appointment_types,
            "date_picker": self.compose_date_picker,
            "time_slots": self.compose_time_slots,
            "confirmation": self.compose_confirmation,
            "upcoming_appointments": self.compose_upcoming_appointments,
        }
    
    def compose_patient_card(self, patient: Dict, thread_id: str) -> Card:
        """
        Build a patient profile card.
        
        Args:
            patient: Patient data with id, name, tier, etc.
            thread_id: Current thread ID
            
        Returns:
            Card widget displaying patient info
        """
        tier = patient.get("tier", "standard")
        tier_colors = {
            "standard": "secondary",
            "premium": "info",
            "vip": "primary",
        }
        
        return Card(
            id=f"patient-card-{datetime.now().timestamp()}",
            children=[
                Row(
                    id="patient-header",
                    children=[
                        Title(id="patient-title", value=f"🏥 {patient.get('name', 'Patient')}", size="lg"),
                        Spacer(id="spacer1"),
                        Badge(
                            id="tier-badge",
                            label=tier.title(),
                            color=tier_colors.get(tier, "secondary"),
                        ),
                    ]
                ),
                Divider(id="div1"),
                Text(id="dob", value=f"📅 DOB: {patient.get('date_of_birth', 'N/A')}"),
                Text(id="phone", value=f"📱 {patient.get('phone', 'N/A')}"),
                Text(id="insurance", value=f"🏦 Insurance: {patient.get('insurance', 'N/A')}"),
            ]
        )
    
    def compose_provider_list(self, providers: List[Dict], thread_id: str) -> Card:
        """
        Build a provider selection widget.
        
        Args:
            providers: List of provider data
            thread_id: Current thread ID
            
        Returns:
            Card widget with provider options
        """
        children = [
            Title(id="providers-title", value="👨‍⚕️ Select a Provider", size="lg"),
            Text(id="providers-subtitle", value="Choose your healthcare provider"),
            Divider(id="div1"),
        ]
        
        for provider in providers:
            provider_id = provider.get("id", "")
            name = provider.get("name", "Provider")
            specialty = provider.get("specialty", "General Practice")
            rating = provider.get("rating", 4.5)
            next_available = provider.get("next_available", "Tomorrow")
            
            children.append(
                Row(
                    id=f"provider-row-{provider_id}",
                    children=[
                        Box(
                            id=f"provider-info-{provider_id}",
                            children=[
                                Text(id=f"provider-name-{provider_id}", value=f"👨‍⚕️ {name}"),
                                Text(id=f"provider-specialty-{provider_id}", value=f"📋 {specialty}"),
                                Text(id=f"provider-rating-{provider_id}", value=f"⭐ {rating}/5 • Next: {next_available}"),
                            ]
                        ),
                        Button(
                            id=f"select-provider-{provider_id}",
                            label="Select",
                            color="primary",
                            onClickAction=ActionConfig(
                                type="select_provider",
                                handler="server",
                                payload={
                                    "provider_id": provider_id,
                                    "name": name,
                                    "specialty": specialty,
                                },
                            ),
                        ),
                    ]
                )
            )
            children.append(Spacer(id=f"spacer-{provider_id}"))
        
        return Card(id=f"providers-{thread_id}", children=children)
    
    def compose_appointment_types(self, types: List[Dict], thread_id: str) -> Card:
        """
        Build an appointment type selection widget.
        
        Args:
            types: List of appointment type options
            thread_id: Current thread ID
            
        Returns:
            Card widget with type options
        """
        icons = {
            "new_patient": "🆕",
            "follow_up": "🔄",
            "routine_checkup": "✅",
            "consultation": "💬",
            "procedure": "🏥",
            "emergency": "🚨",
        }
        
        children = [
            Title(id="types-title", value="📋 Select Appointment Type", size="lg"),
            Divider(id="div1"),
        ]
        
        for apt_type in types:
            code = apt_type.get("code", "")
            label = apt_type.get("label", code)
            duration = apt_type.get("duration", 30)
            icon = icons.get(code, "📅")
            
            children.append(
                Row(
                    id=f"type-row-{code}",
                    children=[
                        Text(id=f"type-icon-{code}", value=icon),
                        Box(
                            id=f"type-info-{code}",
                            children=[
                                Text(id=f"type-label-{code}", value=label),
                                Text(id=f"type-duration-{code}", value=f"Duration: {duration} minutes"),
                            ]
                        ),
                        Button(
                            id=f"select-type-{code}",
                            label="Select",
                            color="primary",
                            onClickAction=ActionConfig(
                                type="select_appointment_type",
                                handler="server",
                                payload={"appointment_type": code, "label": label},
                            ),
                        ),
                    ]
                )
            )
            children.append(Spacer(id=f"spacer-{code}"))
        
        return Card(id=f"appointment-types-{thread_id}", children=children)
    
    def compose_date_picker(self, available_dates: List[Dict], thread_id: str) -> Card:
        """
        Build a date selection widget.
        
        Args:
            available_dates: List of available dates
            thread_id: Current thread ID
            
        Returns:
            Card widget with date options
        """
        children = [
            Title(id="dates-title", value="📅 Select a Date", size="lg"),
            Text(id="dates-subtitle", value="Available appointment dates"),
            Divider(id="div1"),
        ]
        
        for date_info in available_dates:
            date_str = date_info.get("date", "")
            day_name = date_info.get("day_name", "")
            slots_available = date_info.get("slots_available", 0)
            
            children.append(
                Row(
                    id=f"date-row-{date_str}",
                    children=[
                        Box(
                            id=f"date-info-{date_str}",
                            children=[
                                Text(id=f"date-day-{date_str}", value=f"📆 {day_name}"),
                                Text(id=f"date-full-{date_str}", value=date_str),
                                Text(id=f"date-slots-{date_str}", value=f"{slots_available} slots available"),
                            ]
                        ),
                        Button(
                            id=f"select-date-{date_str}",
                            label="Select",
                            color="primary",
                            onClickAction=ActionConfig(
                                type="select_date",
                                handler="server",
                                payload={"date": date_str},
                            ),
                        ),
                    ]
                )
            )
            children.append(Spacer(id=f"spacer-{date_str}"))
        
        return Card(id=f"dates-{thread_id}", children=children)
    
    def compose_time_slots(self, slots: List[Dict], thread_id: str) -> Card:
        """
        Build a time slot selection widget.
        
        Args:
            slots: List of available time slots
            thread_id: Current thread ID
            
        Returns:
            Card widget with time options
        """
        children = [
            Title(id="slots-title", value="🕐 Select a Time", size="lg"),
            Text(id="slots-subtitle", value="Available appointment times"),
            Divider(id="div1"),
        ]
        
        # Group slots into rows of 3 for better layout
        for i, slot in enumerate(slots):
            time_str = slot.get("time", "")
            start_time = slot.get("start_time", time_str)
            
            children.append(
                Button(
                    id=f"select-time-{i}",
                    label=f"🕐 {time_str}",
                    color="secondary",
                    onClickAction=ActionConfig(
                        type="select_time",
                        handler="server",
                        payload={"time": time_str, "start_time": start_time},
                    ),
                )
            )
        
        return Card(id=f"time-slots-{thread_id}", children=children)
    
    def compose_confirmation(self, appointment: Dict, thread_id: str) -> Card:
        """
        Build an appointment confirmation widget.
        
        Args:
            appointment: Created appointment data
            thread_id: Current thread ID
            
        Returns:
            Card widget with confirmation details
        """
        return Card(
            id=f"confirmation-{thread_id}",
            children=[
                Row(
                    id="confirm-header",
                    children=[
                        Title(id="confirm-title", value="✅ Appointment Confirmed!", size="lg"),
                        Badge(id="status-badge", label="Scheduled", color="info"),
                    ]
                ),
                Divider(id="div1"),
                Text(id="appt-id", value=f"Appointment ID: {appointment.get('id', 'N/A')}"),
                Spacer(id="spacer1"),
                Text(id="provider", value=f"👨‍⚕️ Provider: {appointment.get('provider_name', 'N/A')}"),
                Text(id="datetime", value=f"📅 {appointment.get('date', 'N/A')} at {appointment.get('time', 'N/A')}"),
                Text(id="type", value=f"📋 Type: {appointment.get('appointment_type', 'N/A')}"),
                Text(id="location", value=f"📍 Location: {appointment.get('location', 'Main Office')}"),
                Spacer(id="spacer2"),
                Divider(id="div2"),
                Text(id="reminder", value="📧 A confirmation email has been sent."),
                Text(id="instructions", value="📝 Please arrive 15 minutes early with your ID and insurance card."),
            ]
        )
    
    def compose_upcoming_appointments(self, appointments: List[Dict], thread_id: str) -> Card:
        """
        Build a widget showing upcoming appointments.
        
        Args:
            appointments: List of upcoming appointments
            thread_id: Current thread ID
            
        Returns:
            Card widget with appointment list
        """
        children = [
            Title(id="upcoming-title", value="📅 Your Upcoming Appointments", size="lg"),
            Divider(id="div1"),
        ]
        
        if not appointments:
            children.append(Text(id="no-appts", value="No upcoming appointments."))
        else:
            for appt in appointments:
                appt_id = appt.get("id", "")
                children.append(
                    Row(
                        id=f"appt-row-{appt_id}",
                        children=[
                            Box(
                                id=f"appt-info-{appt_id}",
                                children=[
                                    Text(id=f"appt-provider-{appt_id}", value=f"👨‍⚕️ {appt.get('provider_name', 'N/A')}"),
                                    Text(id=f"appt-datetime-{appt_id}", value=f"📅 {appt.get('date', 'N/A')} at {appt.get('time', 'N/A')}"),
                                    Text(id=f"appt-type-{appt_id}", value=f"📋 {appt.get('appointment_type', 'N/A')}"),
                                ]
                            ),
                            Button(
                                id=f"cancel-appt-{appt_id}",
                                label="Cancel",
                                color="danger",
                                onClickAction=ActionConfig(
                                    type="cancel_appointment",
                                    handler="server",
                                    payload={"appointment_id": appt_id},
                                ),
                            ),
                        ]
                    )
                )
                children.append(Spacer(id=f"spacer-{appt_id}"))
        
        return Card(id=f"upcoming-{thread_id}", children=children)
