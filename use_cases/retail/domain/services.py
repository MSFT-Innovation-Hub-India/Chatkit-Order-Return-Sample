"""
Domain Services - Business Operations.

These services orchestrate business logic without I/O dependencies.
They use policies for decisions and work with pure data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from core.domain import DomainService

from .policies import (
    ReturnEligibilityPolicy,
    RefundPolicy,
    ReturnRequestValidator,
    RESTOCKING_FEES,
    FEE_EXEMPT_TIERS,
)


@dataclass
class RefundResult:
    """Result of a refund calculation."""
    subtotal: float
    restocking_fee: float
    refund_amount: float
    fee_rate: float
    fee_waived: bool
    store_credit_bonus: float = 0.0
    
    @property
    def total_store_credit(self) -> float:
        """Total store credit amount including bonus."""
        return self.refund_amount + self.store_credit_bonus


@dataclass
class ReturnRequest:
    """A return request ready to be persisted."""
    id: str
    customer_id: str
    order_id: str
    items: List[Dict[str, Any]]
    reason_code: str
    reason_details: str
    resolution: str
    shipping_method: str
    status: str
    refund_amount: float
    restocking_fee: float
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "order_id": self.order_id,
            "items": self.items,
            "reason_code": self.reason_code,
            "reason_details": self.reason_details,
            "resolution": self.resolution,
            "shipping_method": self.shipping_method,
            "status": self.status,
            "refund_amount": self.refund_amount,
            "restocking_fee": self.restocking_fee,
            "created_at": self.created_at.isoformat(),
        }


class RefundCalculator(DomainService):
    """
    Calculates refund amounts based on items, reason, and customer tier.
    
    This is pure business logic with no I/O.
    """
    
    # Store credit bonus percentage
    STORE_CREDIT_BONUS_RATE = 0.10  # 10% bonus for store credit
    
    def execute(
        self,
        items: List[Dict[str, Any]],
        reason_code: str,
        customer_tier: str = "Standard",
        resolution: str = "FULL_REFUND",
    ) -> RefundResult:
        """
        Calculate the refund for a return.
        
        Args:
            items: List of items with unit_price and quantity
            reason_code: The return reason code
            customer_tier: Customer membership tier
            resolution: The resolution type (FULL_REFUND, STORE_CREDIT, EXCHANGE)
            
        Returns:
            RefundResult with calculated amounts
        """
        # Calculate subtotal
        subtotal = sum(
            item.get("unit_price", 0) * item.get("quantity", 1)
            for item in items
        )
        
        # Determine restocking fee
        fee_rate = RESTOCKING_FEES.get(reason_code, 0.10)
        fee_waived = customer_tier in FEE_EXEMPT_TIERS
        
        if fee_waived:
            fee_rate = 0.0
        
        restocking_fee = subtotal * fee_rate
        refund_amount = subtotal - restocking_fee
        
        # Calculate store credit bonus
        store_credit_bonus = 0.0
        if resolution == "STORE_CREDIT":
            store_credit_bonus = refund_amount * self.STORE_CREDIT_BONUS_RATE
        
        return RefundResult(
            subtotal=subtotal,
            restocking_fee=restocking_fee,
            refund_amount=refund_amount,
            fee_rate=fee_rate,
            fee_waived=fee_waived,
            store_credit_bonus=store_credit_bonus,
        )


class ReturnRequestBuilder(DomainService):
    """
    Builds a validated return request.
    
    This service:
    1. Validates all input data
    2. Calculates refund amounts
    3. Creates a complete return request object
    """
    
    def __init__(self):
        self.validator = ReturnRequestValidator()
        self.refund_calculator = RefundCalculator()
        self.eligibility_policy = ReturnEligibilityPolicy()
    
    def execute(
        self,
        customer_id: str,
        order_id: str,
        items: List[Dict[str, Any]],
        reason_code: str,
        resolution: str,
        customer_tier: str = "Standard",
        shipping_method: str = "PREPAID_LABEL",
        reason_details: str = "",
    ) -> ReturnRequest:
        """
        Build a return request.
        
        Args:
            customer_id: Customer ID
            order_id: Order ID
            items: Items to return
            reason_code: Return reason code
            resolution: Resolution type
            customer_tier: Customer membership tier
            shipping_method: How the item will be returned
            reason_details: Additional details about the reason
            
        Returns:
            A complete ReturnRequest object
            
        Raises:
            ValueError: If validation fails
        """
        # Build the request data
        request_data = {
            "customer_id": customer_id,
            "order_id": order_id,
            "items": items,
            "reason_code": reason_code,
            "resolution": resolution,
            "shipping_method": shipping_method,
        }
        
        # Validate
        errors = self.validator.validate(request_data)
        if errors:
            error_messages = [f"{e.field}: {e.message}" for e in errors]
            raise ValueError(f"Invalid return request: {'; '.join(error_messages)}")
        
        # Calculate refund
        refund_result = self.refund_calculator.execute(
            items=items,
            reason_code=reason_code,
            customer_tier=customer_tier,
            resolution=resolution,
        )
        
        # Build the request
        return ReturnRequest(
            id=f"RET-{uuid.uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            order_id=order_id,
            items=items,
            reason_code=reason_code,
            reason_details=reason_details,
            resolution=resolution,
            shipping_method=shipping_method,
            status="pending",
            refund_amount=refund_result.refund_amount,
            restocking_fee=refund_result.restocking_fee,
            created_at=datetime.now(timezone.utc),
        )


class EligibilityChecker(DomainService):
    """
    Checks return eligibility for items.
    
    Takes product and order data and returns eligibility status.
    """
    
    def __init__(self):
        self.policy = ReturnEligibilityPolicy()
    
    def execute(
        self,
        order_date: str,
        order_status: str,
        category: str,
        return_window_days: int = 30,
        customer_tier: str = "Standard",
    ) -> Dict[str, Any]:
        """
        Check if an item is eligible for return.
        
        Returns:
            Dictionary with eligibility status and details
        """
        context = {
            "order_date": order_date,
            "order_status": order_status,
            "category": category,
            "return_window_days": return_window_days,
            "customer_tier": customer_tier,
        }
        
        decision = self.policy.evaluate(context)
        
        return {
            "eligible": decision.is_approved,
            "reason": decision.reason,
            **decision.metadata,
        }
