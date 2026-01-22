"""
Healthcare-specific tool status messages for workflow indicators.

This module defines user-friendly status messages for healthcare tools.
Each tool maps to (start_message, end_message, icon) tuples.

This is an EXAMPLE showing how to extend the workflow status framework
for a new domain. Copy this pattern for other use cases.
"""

from typing import Dict

# Valid ChatKit icons reference:
# 'agent', 'analytics', 'atom', 'batch', 'bolt', 'book-open', 'book-closed', 
# 'book-clock', 'bug', 'calendar', 'chart', 'check', 'check-circle', 'check-circle-filled', 
# 'clock', 'compass', 'confetti', 'cube', 'desktop', 'document', 'dot', 'globe', 'keys', 
# 'lab', 'images', 'info', 'lifesaver', 'lightbulb', 'mail', 'map-pin', 'maps', 'mobile', 
# 'name', 'notebook', 'page-blank', 'phone', 'play', 'plus', 'profile', 'profile-card', 
# 'reload', 'star', 'search', 'sparkle', 'sparkle-double', 'square-code', 'square-image', 
# 'square-text', 'suitcase', 'settings-slider', 'user', 'wreath', 'write'

HEALTHCARE_TOOL_STATUS_MESSAGES: Dict[str, tuple] = {
    # Patient operations
    "lookup_patient": (
        "Looking up patient record...",
        "Patient found",
        "search",
    ),
    "get_patient_history": (
        "Loading medical history...",
        "History retrieved",
        "document",
    ),
    
    # Appointment operations
    "get_available_slots": (
        "Checking available appointments...",
        "Slots found",
        "calendar",
    ),
    "book_appointment": (
        "Booking your appointment...",
        "Appointment confirmed",
        "check-circle-filled",
    ),
    "cancel_appointment": (
        "Cancelling appointment...",
        "Appointment cancelled",
        "check",
    ),
    "reschedule_appointment": (
        "Rescheduling appointment...",
        "Appointment rescheduled",
        "calendar",
    ),
    
    # Provider operations
    "find_providers": (
        "Searching for providers...",
        "Providers found",
        "user",
    ),
    "get_provider_schedule": (
        "Loading provider schedule...",
        "Schedule loaded",
        "calendar",
    ),
    
    # Prescription operations
    "get_prescriptions": (
        "Loading prescriptions...",
        "Prescriptions retrieved",
        "document",
    ),
    "request_refill": (
        "Requesting prescription refill...",
        "Refill requested",
        "write",
    ),
    
    # Insurance operations
    "verify_insurance": (
        "Verifying insurance coverage...",
        "Coverage verified",
        "check-circle",
    ),
    "get_coverage_details": (
        "Loading coverage details...",
        "Coverage loaded",
        "info",
    ),
}


# Example usage in healthcare server:
#
# from core.workflow_status import create_tool_status_hooks
# from use_cases.healthcare.tool_status import HEALTHCARE_TOOL_STATUS_MESSAGES
#
# hooks, tracker = create_tool_status_hooks(
#     agent_context,
#     tool_messages=HEALTHCARE_TOOL_STATUS_MESSAGES,
#     workflow_summary="Processing your request...",
#     workflow_icon="lifesaver"
# )
