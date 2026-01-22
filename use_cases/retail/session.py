"""
Retail Returns Session Context.

Extends the base SessionContext with retail-specific fields
for tracking the return flow state.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from core.session import SessionContext


class ReturnFlowStep(Enum):
    """Steps in the return flow."""
    NOT_STARTED = "not_started"
    CUSTOMER_IDENTIFIED = "customer_identified"
    ITEMS_DISPLAYED = "items_displayed"
    ITEMS_SELECTED = "items_selected"
    REASON_SELECTED = "reason_selected"
    RESOLUTION_SELECTED = "resolution_selected"
    SHIPPING_SELECTED = "shipping_selected"
    RETURN_CREATED = "return_created"
    CANCELLED = "cancelled"


@dataclass
class ReturnSessionContext(SessionContext):
    """
    Session context for the retail returns flow.
    
    Tracks all the state needed throughout the return process.
    """
    
    # Order context
    displayed_orders: List[Dict[str, Any]] = field(default_factory=list)
    
    # Selected items for return
    selected_items: List[Dict[str, Any]] = field(default_factory=list)
    selected_order_id: Optional[str] = None
    
    # Return flow selections
    reason_code: Optional[str] = None
    reason_label: Optional[str] = None
    reason_details: str = ""
    
    resolution: Optional[str] = None
    resolution_label: Optional[str] = None
    
    shipping_method: Optional[str] = None
    shipping_label: Optional[str] = None
    
    # Created return
    return_id: Optional[str] = None
    return_status: Optional[str] = None
    
    # Retention offer context
    offered_discount: Optional[Dict[str, Any]] = None
    discount_accepted: bool = False
    
    # Flow tracking
    flow_step: ReturnFlowStep = ReturnFlowStep.NOT_STARTED
    
    def set_customer(self, customer_id: str, customer_name: str):
        """Set customer and update flow step."""
        super().set_customer(customer_id, customer_name)
        self.flow_step = ReturnFlowStep.CUSTOMER_IDENTIFIED
    
    def set_displayed_orders(self, orders: List[Dict[str, Any]]):
        """Set the displayed orders."""
        self.displayed_orders = orders
        self.flow_step = ReturnFlowStep.ITEMS_DISPLAYED
        self._touch()
    
    def add_selected_item(self, item: Dict[str, Any]):
        """Add an item to the selection."""
        self.selected_items.append(item)
        self.selected_order_id = item.get("order_id")
        self.flow_step = ReturnFlowStep.ITEMS_SELECTED
        self._touch()
    
    def set_reason(self, code: str, label: str = "", details: str = ""):
        """Set the return reason."""
        self.reason_code = code
        self.reason_label = label or code.replace("_", " ").title()
        self.reason_details = details
        self.flow_step = ReturnFlowStep.REASON_SELECTED
        self._touch()
    
    def set_resolution(self, code: str, label: str = ""):
        """Set the resolution option."""
        self.resolution = code
        self.resolution_label = label or code.replace("_", " ").title()
        self.flow_step = ReturnFlowStep.RESOLUTION_SELECTED
        self._touch()
    
    def set_shipping(self, method: str, label: str = ""):
        """Set the shipping method."""
        self.shipping_method = method
        self.shipping_label = label or method.replace("_", " ").title()
        self.flow_step = ReturnFlowStep.SHIPPING_SELECTED
        self._touch()
    
    def set_return_created(self, return_id: str, status: str = "pending"):
        """Mark the return as created."""
        self.return_id = return_id
        self.return_status = status
        self.flow_step = ReturnFlowStep.RETURN_CREATED
        self._touch()
    
    def is_ready_to_create_return(self) -> bool:
        """Check if all required data is present to create a return."""
        return all([
            self.customer_id,
            self.selected_items,
            self.reason_code,
            self.resolution,
            self.shipping_method,
        ])
    
    def get_all_displayed_items(self) -> List[Dict[str, Any]]:
        """Get all items from displayed orders."""
        items = []
        for order in self.displayed_orders:
            order_id = order.get("id", order.get("order_id", ""))
            for item in order.get("items", order.get("returnable_items", [])):
                item_copy = item.copy()
                item_copy["order_id"] = order_id
                items.append(item_copy)
        return items
    
    def reset_for_new_return(self):
        """Reset selection data for a new return (keep customer)."""
        self.selected_items.clear()
        self.selected_order_id = None
        self.reason_code = None
        self.reason_label = None
        self.reason_details = ""
        self.resolution = None
        self.resolution_label = None
        self.shipping_method = None
        self.shipping_label = None
        self.return_id = None
        self.return_status = None
        self.flow_step = ReturnFlowStep.CUSTOMER_IDENTIFIED
        self._touch()
    
    def to_context_string(self) -> str:
        """
        Build a detailed context summary for the agent.
        """
        parts = []
        
        # Customer info
        if self.customer_id:
            parts.append(f"Customer: {self.customer_name} (ID: {self.customer_id})")
        
        # Displayed orders with items
        if self.displayed_orders:
            parts.append("\nItems displayed for potential return:")
            for order in self.displayed_orders:
                order_id = order.get("id", order.get("order_id", "Unknown"))
                parts.append(f"  Order {order_id}:")
                items = order.get("items", order.get("returnable_items", []))
                for item in items:
                    name = item.get("name", "Unknown Item")
                    product_id = item.get("product_id", "")
                    price = item.get("unit_price", 0)
                    qty = item.get("quantity", 1)
                    days = item.get("days_remaining", item.get("return_eligibility", {}).get("days_remaining", "?"))
                    parts.append(f"    - {name} (ID: {product_id}, ${price:.2f} x {qty}, {days} days left)")
        
        # Selected items
        if self.selected_items:
            parts.append("\nItems selected for return:")
            for item in self.selected_items:
                name = item.get("name", "Unknown")
                order_id = item.get("order_id", "Unknown")
                parts.append(f"  - {name} from order {order_id}")
        
        # Flow state
        if self.reason_code:
            parts.append(f"\nReturn reason: {self.reason_label or self.reason_code}")
        if self.resolution:
            parts.append(f"Resolution: {self.resolution_label or self.resolution}")
        if self.shipping_method:
            parts.append(f"Shipping: {self.shipping_label or self.shipping_method}")
        
        # Return status
        if self.return_id:
            parts.append(f"\nReturn ID: {self.return_id} (Status: {self.return_status})")
        
        parts.append(f"\nCurrent step: {self.flow_step.value}")
        
        return "\n".join(parts) if parts else "No session context"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        base = super().to_dict()
        base.update({
            "displayed_orders": self.displayed_orders,
            "selected_items": self.selected_items,
            "selected_order_id": self.selected_order_id,
            "reason_code": self.reason_code,
            "reason_label": self.reason_label,
            "reason_details": self.reason_details,
            "resolution": self.resolution,
            "resolution_label": self.resolution_label,
            "shipping_method": self.shipping_method,
            "shipping_label": self.shipping_label,
            "return_id": self.return_id,
            "return_status": self.return_status,
            "flow_step": self.flow_step.value,
        })
        return base
