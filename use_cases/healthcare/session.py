"""
Healthcare Session Context.

Extends the core SessionContext with appointment-specific state tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from core.session import SessionContext


class AppointmentFlowStep(Enum):
    """Steps in the appointment scheduling flow."""
    NOT_STARTED = "not_started"
    PATIENT_IDENTIFIED = "patient_identified"
    PROVIDER_SELECTED = "provider_selected"
    APPOINTMENT_TYPE_SELECTED = "appointment_type_selected"
    DATE_SELECTED = "date_selected"
    TIME_SELECTED = "time_selected"
    REASON_PROVIDED = "reason_provided"
    CONFIRMED = "confirmed"
    APPOINTMENT_CREATED = "appointment_created"


@dataclass
class AppointmentSessionContext(SessionContext):
    """
    Session context for healthcare appointment scheduling.
    
    Tracks the patient's progress through the scheduling flow.
    """
    
    # Patient information
    patient_id: str = ""
    patient_name: str = ""
    patient_tier: str = "standard"
    
    # Provider selection
    provider_id: str = ""
    provider_name: str = ""
    specialty: str = ""
    
    # Appointment details
    appointment_type: str = ""
    selected_date: Optional[datetime] = None
    selected_time: Optional[datetime] = None
    reason: str = ""
    notes: str = ""
    
    # Flow tracking
    flow_step: AppointmentFlowStep = AppointmentFlowStep.NOT_STARTED
    
    # Displayed data for natural language references
    displayed_providers: List[Dict] = field(default_factory=list)
    displayed_slots: List[Dict] = field(default_factory=list)
    existing_appointments: List[Dict] = field(default_factory=list)
    
    def set_patient(self, patient_id: str, name: str, tier: str = "standard"):
        """Set the current patient."""
        self.patient_id = patient_id
        self.patient_name = name
        self.patient_tier = tier
        self.customer_id = patient_id  # Also set base class field
        self.flow_step = AppointmentFlowStep.PATIENT_IDENTIFIED
    
    def set_provider(self, provider_id: str, name: str, specialty: str = ""):
        """Set the selected provider."""
        self.provider_id = provider_id
        self.provider_name = name
        self.specialty = specialty
        self.flow_step = AppointmentFlowStep.PROVIDER_SELECTED
    
    def set_appointment_type(self, appointment_type: str):
        """Set the appointment type."""
        self.appointment_type = appointment_type
        self.flow_step = AppointmentFlowStep.APPOINTMENT_TYPE_SELECTED
    
    def set_date(self, date: datetime):
        """Set the selected date."""
        self.selected_date = date
        self.flow_step = AppointmentFlowStep.DATE_SELECTED
    
    def set_time(self, time: datetime):
        """Set the selected time slot."""
        self.selected_time = time
        self.flow_step = AppointmentFlowStep.TIME_SELECTED
    
    def set_reason(self, reason: str, notes: str = ""):
        """Set the appointment reason and notes."""
        self.reason = reason
        self.notes = notes
        self.flow_step = AppointmentFlowStep.REASON_PROVIDED
    
    def set_displayed_providers(self, providers: List[Dict]):
        """Store providers shown to the user for natural language reference."""
        self.displayed_providers = providers
    
    def set_displayed_slots(self, slots: List[Dict]):
        """Store time slots shown to the user for natural language reference."""
        self.displayed_slots = slots
    
    def is_ready_to_create_appointment(self) -> bool:
        """Check if all required information has been collected."""
        return all([
            self.patient_id,
            self.provider_id,
            self.appointment_type,
            self.selected_time,
            self.reason,
        ])
    
    def get_missing_info(self) -> List[str]:
        """Get list of missing required information."""
        missing = []
        if not self.patient_id:
            missing.append("patient identification")
        if not self.provider_id:
            missing.append("provider selection")
        if not self.appointment_type:
            missing.append("appointment type")
        if not self.selected_time:
            missing.append("appointment time")
        if not self.reason:
            missing.append("reason for visit")
        return missing
    
    def to_context_string(self) -> str:
        """
        Convert session state to a string for agent context injection.
        """
        parts = []
        
        if self.patient_id:
            parts.append(f"Patient: {self.patient_name} (ID: {self.patient_id}, Tier: {self.patient_tier})")
        
        if self.provider_id:
            specialty_str = f" - {self.specialty}" if self.specialty else ""
            parts.append(f"Selected provider: {self.provider_name}{specialty_str}")
        
        if self.appointment_type:
            parts.append(f"Appointment type: {self.appointment_type}")
        
        if self.selected_date:
            parts.append(f"Selected date: {self.selected_date.strftime('%A, %B %d, %Y')}")
        
        if self.selected_time:
            parts.append(f"Selected time: {self.selected_time.strftime('%I:%M %p')}")
        
        if self.reason:
            parts.append(f"Reason for visit: {self.reason}")
        
        if self.displayed_providers:
            parts.append("\nProviders shown to patient:")
            for p in self.displayed_providers:
                parts.append(f"  - {p.get('name', 'Unknown')} ({p.get('specialty', 'General')})")
        
        if self.displayed_slots:
            parts.append("\nAvailable time slots shown:")
            for slot in self.displayed_slots[:5]:  # Limit to 5 for brevity
                parts.append(f"  - {slot.get('start_time', 'Unknown')}")
        
        if self.existing_appointments:
            parts.append("\nPatient's upcoming appointments:")
            for appt in self.existing_appointments:
                parts.append(f"  - {appt.get('start_time', 'Unknown')} with {appt.get('provider_name', 'Unknown')}")
        
        parts.append(f"\nCurrent step: {self.flow_step.value}")
        
        if not self.is_ready_to_create_appointment():
            missing = self.get_missing_info()
            parts.append(f"Still needed: {', '.join(missing)}")
        
        return "\n".join(parts)
    
    def reset_for_new_appointment(self):
        """Reset session for scheduling another appointment."""
        self.provider_id = ""
        self.provider_name = ""
        self.specialty = ""
        self.appointment_type = ""
        self.selected_date = None
        self.selected_time = None
        self.reason = ""
        self.notes = ""
        self.flow_step = AppointmentFlowStep.PATIENT_IDENTIFIED
        self.displayed_providers = []
        self.displayed_slots = []
        self.reset_widgets()
