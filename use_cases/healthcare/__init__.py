"""
Healthcare Appointment Scheduling Use Case.

This use case demonstrates the extensible architecture pattern
by implementing a completely different domain: healthcare appointment scheduling.

Structure:
- domain/: Pure business logic (no I/O)
  - policies.py: AppointmentPolicy, SchedulingRules
  - services.py: ScheduleCalculator, ConflictChecker
- data/: Data access layer
  - repository.py: HealthcareRepository
- presentation/: Widget composition
  - composer.py: AppointmentWidgetComposer
- session.py: AppointmentSessionContext
- server.py: HealthcareChatKitServer
- tools.py: Agent tool functions
"""

from .server import HealthcareChatKitServer
from .session import AppointmentSessionContext, AppointmentFlowStep

__all__ = [
    "HealthcareChatKitServer",
    "AppointmentSessionContext",
    "AppointmentFlowStep",
]
