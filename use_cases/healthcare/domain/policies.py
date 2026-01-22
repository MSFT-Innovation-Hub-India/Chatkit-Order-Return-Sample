"""
Healthcare Domain Policies.

Pure business rules for appointment scheduling.
These classes have NO I/O dependencies - they can be unit tested in isolation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from core.domain import PolicyEngine, PolicyDecision, PolicyResult


# =============================================================================
# CONSTANTS
# =============================================================================

# Minimum hours notice required for scheduling
MIN_NOTICE_HOURS = {
    "routine": 24,
    "follow_up": 4,
    "urgent": 1,
    "emergency": 0,
}

# Maximum days in advance for booking
MAX_ADVANCE_DAYS = {
    "routine": 90,
    "follow_up": 30,
    "urgent": 7,
    "emergency": 1,
}

# Appointment durations in minutes
APPOINTMENT_DURATIONS = {
    "new_patient": 60,
    "follow_up": 30,
    "routine_checkup": 30,
    "consultation": 45,
    "procedure": 90,
    "emergency": 30,
}

# Cancellation windows (hours before appointment)
CANCELLATION_WINDOWS = {
    "free_cancellation": 24,  # No fee if cancelled 24+ hours before
    "late_cancellation": 4,   # Fee if cancelled 4-24 hours before
    "no_show": 0,             # Missed appointment - full fee
}


# =============================================================================
# POLICY ENGINES
# =============================================================================

@dataclass
class SchedulingContext:
    """Context for scheduling policy evaluation."""
    appointment_type: str
    requested_datetime: datetime
    current_datetime: datetime
    patient_type: str = "existing"  # "new" or "existing"
    provider_id: Optional[str] = None
    existing_appointments: List[Dict] = None
    
    def __post_init__(self):
        if self.existing_appointments is None:
            self.existing_appointments = []


class SchedulingRules(PolicyEngine):
    """
    Rules for when appointments can be scheduled.
    
    Evaluates:
    - Minimum notice requirements
    - Maximum advance booking limits
    - Business hours constraints
    - Provider availability
    """
    
    def get_policies(self) -> List[str]:
        return [
            "minimum_notice",
            "maximum_advance",
            "business_hours",
            "no_holidays",
        ]
    
    def evaluate(self, context: SchedulingContext) -> PolicyDecision:
        """
        Evaluate if an appointment can be scheduled at the requested time.
        """
        # Check minimum notice
        min_notice_result = self._check_minimum_notice(context)
        if min_notice_result.result == PolicyResult.DENIED:
            return min_notice_result
        
        # Check maximum advance booking
        max_advance_result = self._check_maximum_advance(context)
        if max_advance_result.result == PolicyResult.DENIED:
            return max_advance_result
        
        # Check business hours
        business_hours_result = self._check_business_hours(context)
        if business_hours_result.result == PolicyResult.DENIED:
            return business_hours_result
        
        return PolicyDecision(
            result=PolicyResult.APPROVED,
            reason="Appointment time is available",
            metadata={"policies_checked": self.get_policies()},
        )
    
    def _check_minimum_notice(self, context: SchedulingContext) -> PolicyDecision:
        """Check if appointment is scheduled with enough notice."""
        min_hours = MIN_NOTICE_HOURS.get(context.appointment_type, 24)
        min_time = context.current_datetime + timedelta(hours=min_hours)
        
        if context.requested_datetime < min_time:
            return PolicyDecision(
                result=PolicyResult.DENIED,
                reason=f"{context.appointment_type.title()} appointments require at least {min_hours} hours notice",
                metadata={"required_notice_hours": min_hours},
            )
        
        return PolicyDecision(result=PolicyResult.APPROVED, reason="Sufficient notice")
    
    def _check_maximum_advance(self, context: SchedulingContext) -> PolicyDecision:
        """Check if appointment is within the maximum advance booking window."""
        max_days = MAX_ADVANCE_DAYS.get(context.appointment_type, 90)
        max_date = context.current_datetime + timedelta(days=max_days)
        
        if context.requested_datetime > max_date:
            return PolicyDecision(
                result=PolicyResult.DENIED,
                reason=f"{context.appointment_type.title()} appointments can only be booked up to {max_days} days in advance",
                metadata={"max_advance_days": max_days},
            )
        
        return PolicyDecision(result=PolicyResult.APPROVED, reason="Within booking window")
    
    def _check_business_hours(self, context: SchedulingContext) -> PolicyDecision:
        """Check if appointment is during business hours."""
        requested = context.requested_datetime
        
        # Weekend check
        if requested.weekday() >= 5:  # Saturday = 5, Sunday = 6
            if context.appointment_type != "emergency":
                return PolicyDecision(
                    result=PolicyResult.DENIED,
                    reason="Non-emergency appointments are not available on weekends",
                )
        
        # Business hours: 8 AM to 5 PM
        if not (8 <= requested.hour < 17):
            if context.appointment_type != "emergency":
                return PolicyDecision(
                    result=PolicyResult.DENIED,
                    reason="Appointments are only available between 8 AM and 5 PM",
                )
        
        return PolicyDecision(result=PolicyResult.APPROVED, reason="Within business hours")


class AppointmentPolicy(PolicyEngine):
    """
    Overall appointment scheduling policy.
    
    Combines scheduling rules with patient-specific checks.
    """
    
    def __init__(self):
        self.scheduling_rules = SchedulingRules()
    
    def get_policies(self) -> List[str]:
        return [
            "scheduling_rules",
            "patient_eligibility",
            "no_conflicts",
        ]
    
    def evaluate(self, context: SchedulingContext) -> PolicyDecision:
        """
        Evaluate overall appointment eligibility.
        """
        # First, check scheduling rules
        scheduling_result = self.scheduling_rules.evaluate(context)
        if scheduling_result.result == PolicyResult.DENIED:
            return scheduling_result
        
        # Check for conflicts with existing appointments
        conflict_result = self._check_conflicts(context)
        if conflict_result.result == PolicyResult.DENIED:
            return conflict_result
        
        return PolicyDecision(
            result=PolicyResult.APPROVED,
            reason="Appointment can be scheduled",
            metadata={"appointment_type": context.appointment_type},
        )
    
    def _check_conflicts(self, context: SchedulingContext) -> PolicyDecision:
        """Check if the requested time conflicts with existing appointments."""
        duration = APPOINTMENT_DURATIONS.get(context.appointment_type, 30)
        requested_end = context.requested_datetime + timedelta(minutes=duration)
        
        for existing in context.existing_appointments:
            existing_start = existing.get("start_time")
            existing_end = existing.get("end_time")
            
            if existing_start and existing_end:
                # Check for overlap
                if (context.requested_datetime < existing_end and 
                    requested_end > existing_start):
                    return PolicyDecision(
                        result=PolicyResult.DENIED,
                        reason=f"Time slot conflicts with existing appointment at {existing_start}",
                        metadata={"conflicting_appointment": existing.get("id")},
                    )
        
        return PolicyDecision(result=PolicyResult.APPROVED, reason="No conflicts")


class CancellationPolicy(PolicyEngine):
    """
    Policy for appointment cancellations.
    
    Determines cancellation fees based on timing.
    """
    
    def get_policies(self) -> List[str]:
        return [
            "cancellation_window",
            "patient_history",
        ]
    
    def evaluate(self, context: Dict) -> PolicyDecision:
        """
        Evaluate cancellation request.
        
        Context should include:
        - appointment_datetime: When the appointment is scheduled
        - current_datetime: Current time
        - patient_tier: Patient's membership tier
        """
        appointment_time = context.get("appointment_datetime")
        current_time = context.get("current_datetime", datetime.now())
        patient_tier = context.get("patient_tier", "standard")
        
        if not appointment_time:
            return PolicyDecision(
                result=PolicyResult.DENIED,
                reason="No appointment time provided",
            )
        
        hours_until = (appointment_time - current_time).total_seconds() / 3600
        
        if hours_until >= CANCELLATION_WINDOWS["free_cancellation"]:
            return PolicyDecision(
                result=PolicyResult.APPROVED,
                reason="Free cancellation - more than 24 hours notice",
                metadata={"fee": 0, "fee_waived": True},
            )
        elif hours_until >= CANCELLATION_WINDOWS["late_cancellation"]:
            # Premium patients get fee waiver
            if patient_tier in ["premium", "vip"]:
                return PolicyDecision(
                    result=PolicyResult.APPROVED,
                    reason="Late cancellation fee waived for premium patient",
                    metadata={"fee": 0, "fee_waived": True, "tier_benefit": True},
                )
            return PolicyDecision(
                result=PolicyResult.APPROVED,
                reason="Late cancellation - fee applies",
                metadata={"fee": 50.00, "fee_waived": False},
            )
        else:
            return PolicyDecision(
                result=PolicyResult.APPROVED,
                reason="Very late cancellation - full fee applies",
                metadata={"fee": 100.00, "fee_waived": False},
            )
