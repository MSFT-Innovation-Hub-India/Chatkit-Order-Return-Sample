"""
Healthcare Domain Services.

Services that orchestrate domain logic for complex operations.
These have NO I/O dependencies - pure calculations and transformations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .policies import APPOINTMENT_DURATIONS, AppointmentPolicy, SchedulingContext


# =============================================================================
# SERVICE RESULTS
# =============================================================================

@dataclass
class TimeSlot:
    """Represents an available time slot."""
    start_time: datetime
    end_time: datetime
    provider_id: Optional[str] = None
    provider_name: Optional[str] = None
    location: Optional[str] = None
    
    @property
    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() / 60)
    
    def to_dict(self) -> Dict:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_minutes": self.duration_minutes,
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "location": self.location,
        }


@dataclass
class AppointmentRequest:
    """Request to create an appointment."""
    patient_id: str
    patient_name: str
    provider_id: str
    provider_name: str
    appointment_type: str
    start_time: datetime
    reason: str
    notes: Optional[str] = None
    
    @property
    def end_time(self) -> datetime:
        duration = APPOINTMENT_DURATIONS.get(self.appointment_type, 30)
        return self.start_time + timedelta(minutes=duration)
    
    @property
    def duration_minutes(self) -> int:
        return APPOINTMENT_DURATIONS.get(self.appointment_type, 30)


@dataclass
class ScheduleResult:
    """Result of a scheduling operation."""
    success: bool
    slots: List[TimeSlot] = field(default_factory=list)
    message: str = ""
    next_available: Optional[datetime] = None


# =============================================================================
# DOMAIN SERVICES
# =============================================================================

class ScheduleCalculator:
    """
    Calculates available appointment slots.
    
    Pure logic - takes provider schedule and existing appointments
    as input, returns available slots.
    """
    
    def __init__(self, slot_duration_minutes: int = 30):
        self.slot_duration = slot_duration_minutes
    
    def find_available_slots(
        self,
        date: datetime,
        appointment_type: str,
        provider_schedule: Dict,
        existing_appointments: List[Dict],
    ) -> List[TimeSlot]:
        """
        Find available slots for a given date.
        
        Args:
            date: The date to check
            appointment_type: Type of appointment (determines duration)
            provider_schedule: Provider's working hours {"start": "09:00", "end": "17:00"}
            existing_appointments: List of existing appointments
            
        Returns:
            List of available TimeSlot objects
        """
        duration = APPOINTMENT_DURATIONS.get(appointment_type, 30)
        
        # Parse provider schedule
        schedule_start = self._parse_time(date, provider_schedule.get("start", "09:00"))
        schedule_end = self._parse_time(date, provider_schedule.get("end", "17:00"))
        
        # Generate all possible slots
        all_slots = self._generate_slots(schedule_start, schedule_end, duration)
        
        # Filter out slots that conflict with existing appointments
        available_slots = [
            slot for slot in all_slots
            if not self._has_conflict(slot, existing_appointments)
        ]
        
        return available_slots
    
    def _parse_time(self, date: datetime, time_str: str) -> datetime:
        """Parse a time string and combine with date."""
        hour, minute = map(int, time_str.split(":"))
        return date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    def _generate_slots(
        self,
        start: datetime,
        end: datetime,
        duration: int,
    ) -> List[TimeSlot]:
        """Generate all possible slots between start and end."""
        slots = []
        current = start
        
        while current + timedelta(minutes=duration) <= end:
            slots.append(TimeSlot(
                start_time=current,
                end_time=current + timedelta(minutes=duration),
            ))
            current += timedelta(minutes=self.slot_duration)
        
        return slots
    
    def _has_conflict(self, slot: TimeSlot, appointments: List[Dict]) -> bool:
        """Check if a slot conflicts with any existing appointment."""
        for appt in appointments:
            appt_start = appt.get("start_time")
            appt_end = appt.get("end_time")
            
            if isinstance(appt_start, str):
                appt_start = datetime.fromisoformat(appt_start)
            if isinstance(appt_end, str):
                appt_end = datetime.fromisoformat(appt_end)
            
            if appt_start and appt_end:
                # Check for overlap
                if slot.start_time < appt_end and slot.end_time > appt_start:
                    return True
        
        return False


class ConflictChecker:
    """
    Checks for appointment conflicts.
    
    Used to validate that a new appointment doesn't overlap
    with existing ones.
    """
    
    def check_patient_conflicts(
        self,
        patient_appointments: List[Dict],
        new_start: datetime,
        new_end: datetime,
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check if patient has conflicting appointments.
        
        Returns:
            Tuple of (has_conflict, conflicting_appointment)
        """
        for appt in patient_appointments:
            appt_start = appt.get("start_time")
            appt_end = appt.get("end_time")
            
            if isinstance(appt_start, str):
                appt_start = datetime.fromisoformat(appt_start)
            if isinstance(appt_end, str):
                appt_end = datetime.fromisoformat(appt_end)
            
            if appt_start and appt_end:
                if new_start < appt_end and new_end > appt_start:
                    return True, appt
        
        return False, None
    
    def check_provider_conflicts(
        self,
        provider_appointments: List[Dict],
        new_start: datetime,
        new_end: datetime,
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check if provider has conflicting appointments.
        
        Returns:
            Tuple of (has_conflict, conflicting_appointment)
        """
        # Same logic as patient conflicts
        return self.check_patient_conflicts(provider_appointments, new_start, new_end)


class AppointmentBuilder:
    """
    Builds appointment data structures.
    
    Validates and constructs appointment requests.
    """
    
    def __init__(self):
        self.policy = AppointmentPolicy()
    
    def build_request(
        self,
        patient_id: str,
        patient_name: str,
        provider_id: str,
        provider_name: str,
        appointment_type: str,
        start_time: datetime,
        reason: str,
        existing_appointments: List[Dict] = None,
        notes: Optional[str] = None,
    ) -> Tuple[Optional[AppointmentRequest], Optional[str]]:
        """
        Build and validate an appointment request.
        
        Returns:
            Tuple of (request, error_message)
            If successful, error_message is None
            If failed, request is None
        """
        # Validate with policy
        context = SchedulingContext(
            appointment_type=appointment_type,
            requested_datetime=start_time,
            current_datetime=datetime.now(),
            provider_id=provider_id,
            existing_appointments=existing_appointments or [],
        )
        
        decision = self.policy.evaluate(context)
        
        if decision.result.value != "approved":
            return None, decision.reason
        
        # Build the request
        request = AppointmentRequest(
            patient_id=patient_id,
            patient_name=patient_name,
            provider_id=provider_id,
            provider_name=provider_name,
            appointment_type=appointment_type,
            start_time=start_time,
            reason=reason,
            notes=notes,
        )
        
        return request, None
    
    def to_cosmos_document(self, request: AppointmentRequest) -> Dict:
        """
        Convert an appointment request to a Cosmos DB document.
        """
        return {
            "id": f"APPT-{request.start_time.strftime('%Y%m%d%H%M')}-{request.patient_id[:8]}",
            "type": "appointment",
            "patient_id": request.patient_id,
            "patient_name": request.patient_name,
            "provider_id": request.provider_id,
            "provider_name": request.provider_name,
            "appointment_type": request.appointment_type,
            "start_time": request.start_time.isoformat(),
            "end_time": request.end_time.isoformat(),
            "duration_minutes": request.duration_minutes,
            "reason": request.reason,
            "notes": request.notes,
            "status": "scheduled",
            "created_at": datetime.now().isoformat(),
        }
