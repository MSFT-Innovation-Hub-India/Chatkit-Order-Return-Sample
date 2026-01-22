"""
Retail-specific tool status messages for workflow indicators.

This module defines user-friendly status messages for retail tools.
Each tool maps to (start_message, end_message, icon) tuples.
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

RETAIL_TOOL_STATUS_MESSAGES: Dict[str, tuple] = {
    # Customer operations
    "lookup_customer": (
        "Looking up customer...",
        "Customer found",
        "search",
    ),
    
    # Order operations
    "get_customer_orders": (
        "Fetching order history...",
        "Orders retrieved",
        "document",
    ),
    "get_returnable_items": (
        "Finding returnable items...",
        "Returnable items found",
        "cube",
    ),
    
    # Return flow operations
    "check_return_eligibility": (
        "Checking return eligibility...",
        "Eligibility verified",
        "check-circle",
    ),
    "get_return_reasons": (
        "Loading return reasons...",
        "Ready for selection",
        "info",
    ),
    "get_resolution_options": (
        "Fetching resolution options...",
        "Options available",
        "lightbulb",
    ),
    "get_shipping_options": (
        "Loading shipping methods...",
        "Shipping options ready",
        "suitcase",
    ),
    "get_retention_offers": (
        "Checking available offers...",
        "Offers loaded",
        "star",
    ),
    
    # Return creation
    "create_return_request": (
        "Creating return request...",
        "Return created",
        "write",
    ),
    "finalize_return_from_session": (
        "Finalizing your return...",
        "Return confirmed",
        "check-circle-filled",
    ),
    
    # Session management
    "set_user_selection": (
        "Saving your selection...",
        "Selection recorded",
        "check",
    ),
    "select_item_for_return": (
        "Selecting item...",
        "Item selected",
        "cube",
    ),
    "return_multiple_items": (
        "Processing items...",
        "Items ready for return",
        "cube",
    ),
    
    # Refund operations
    "calculate_refund_amount": (
        "Calculating refund...",
        "Refund calculated",
        "analytics",
    ),
    "get_customer_return_history": (
        "Loading return history...",
        "History retrieved",
        "clock",
    ),
}
