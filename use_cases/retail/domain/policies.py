"""
Return Policies - Pure Business Rules.

These policies encapsulate the business rules for returns.
They have NO dependencies on databases or external services.
All data needed for evaluation is passed in as parameters.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from core.domain import (
    PolicyEngine,
    PolicyDecision,
    PolicyResult,
    Validator,
    ValidationError,
    days_between,
    parse_date,
)


# =============================================================================
# CONFIGURATION (could be loaded from config file)
# =============================================================================

# Categories that cannot be returned
NON_RETURNABLE_CATEGORIES = [
    "underwear",
    "swimwear", 
    "earrings",
    "personalized",
    "final_sale",
]

# Default return window in days
DEFAULT_RETURN_WINDOW_DAYS = 30

# Extended return window for premium tiers
TIER_RETURN_EXTENSIONS = {
    "Standard": 0,
    "Silver": 7,
    "Gold": 14,
    "Platinum": 30,
}

# Restocking fee percentages by reason
RESTOCKING_FEES = {
    "CHANGED_MIND": 0.15,  # 15% restocking fee
    "WRONG_SIZE": 0.0,
    "WRONG_COLOR": 0.0,
    "DEFECTIVE": 0.0,
    "DAMAGED": 0.0,
    "NOT_AS_DESCRIBED": 0.0,
    "ARRIVED_LATE": 0.0,
    "OTHER": 0.10,
}

# Tiers exempt from restocking fees
FEE_EXEMPT_TIERS = ["Gold", "Platinum"]


# =============================================================================
# POLICIES
# =============================================================================

class ReturnWindowPolicy(PolicyEngine):
    """
    Policy for checking if an item is within its return window.
    
    Context required:
        - order_date: ISO format date string or datetime
        - return_window_days: Optional, defaults to 30
        - customer_tier: Optional, for extended windows
    """
    
    def evaluate(self, context: Dict[str, Any]) -> PolicyDecision:
        # Parse order date
        order_date = context.get("order_date")
        if isinstance(order_date, str):
            order_date = parse_date(order_date)
        
        if order_date is None:
            return PolicyDecision(
                result=PolicyResult.APPROVED,
                reason="Unable to determine order date, allowing return",
                metadata={"fallback": True}
            )
        
        # Calculate return window
        base_window = context.get("return_window_days", DEFAULT_RETURN_WINDOW_DAYS)
        tier = context.get("customer_tier", "Standard")
        extension = TIER_RETURN_EXTENSIONS.get(tier, 0)
        total_window = base_window + extension
        
        # Calculate deadline
        deadline = order_date + timedelta(days=total_window)
        now = datetime.now(timezone.utc)
        
        if now > deadline:
            return PolicyDecision(
                result=PolicyResult.DENIED,
                reason=f"Return window expired on {deadline.strftime('%Y-%m-%d')}",
                metadata={
                    "deadline": deadline.isoformat(),
                    "days_overdue": (now - deadline).days,
                }
            )
        
        days_remaining = (deadline - now).days
        return PolicyDecision(
            result=PolicyResult.APPROVED,
            reason=f"{days_remaining} days remaining in return window",
            metadata={
                "days_remaining": days_remaining,
                "deadline": deadline.isoformat(),
                "return_window_days": total_window,
            }
        )


class CategoryPolicy(PolicyEngine):
    """
    Policy for checking if a product category allows returns.
    
    Context required:
        - category: Product category string
    """
    
    def evaluate(self, context: Dict[str, Any]) -> PolicyDecision:
        category = context.get("category", "").lower()
        
        if category in NON_RETURNABLE_CATEGORIES:
            return PolicyDecision(
                result=PolicyResult.DENIED,
                reason=f"{category.title()} items cannot be returned",
                metadata={"category": category}
            )
        
        return PolicyDecision(
            result=PolicyResult.APPROVED,
            reason="Product category is returnable",
            metadata={"category": category}
        )


class ReturnEligibilityPolicy(PolicyEngine):
    """
    Composite policy that checks all eligibility requirements.
    
    Combines:
        - Return window check
        - Category check
        - Order status check
    
    Context required:
        - order_date: ISO format date string
        - order_status: Order status string
        - category: Product category
        - return_window_days: Optional
        - customer_tier: Optional
    """
    
    def __init__(self):
        self.window_policy = ReturnWindowPolicy()
        self.category_policy = CategoryPolicy()
    
    def evaluate(self, context: Dict[str, Any]) -> PolicyDecision:
        # Check order status first
        order_status = context.get("order_status", "").lower()
        if order_status not in ["delivered", "shipped"]:
            return PolicyDecision(
                result=PolicyResult.DENIED,
                reason=f"Order status '{order_status}' is not eligible for returns. Order must be delivered or shipped.",
                metadata={"order_status": order_status}
            )
        
        # Check category
        category_decision = self.category_policy.evaluate(context)
        if category_decision.is_denied:
            return category_decision
        
        # Check return window
        window_decision = self.window_policy.evaluate(context)
        if window_decision.is_denied:
            return window_decision
        
        # All checks passed
        return PolicyDecision(
            result=PolicyResult.APPROVED,
            reason="Item is eligible for return",
            metadata={
                **window_decision.metadata,
                **category_decision.metadata,
            }
        )


class RefundPolicy(PolicyEngine):
    """
    Policy for calculating refund amount and fees.
    
    Context required:
        - items: List of items with unit_price and quantity
        - reason_code: Return reason code
        - customer_tier: Customer membership tier
    """
    
    def evaluate(self, context: Dict[str, Any]) -> PolicyDecision:
        items = context.get("items", [])
        reason_code = context.get("reason_code", "OTHER")
        tier = context.get("customer_tier", "Standard")
        
        # Calculate subtotal
        subtotal = sum(
            item.get("unit_price", 0) * item.get("quantity", 1)
            for item in items
        )
        
        # Determine restocking fee
        fee_rate = RESTOCKING_FEES.get(reason_code, 0.10)
        
        # Premium tiers are exempt from fees
        if tier in FEE_EXEMPT_TIERS:
            fee_rate = 0.0
        
        restocking_fee = subtotal * fee_rate
        refund_amount = subtotal - restocking_fee
        
        metadata = {
            "subtotal": subtotal,
            "restocking_fee": restocking_fee,
            "refund_amount": refund_amount,
            "fee_rate": fee_rate,
            "fee_waived": tier in FEE_EXEMPT_TIERS,
        }
        
        if restocking_fee > 0:
            return PolicyDecision(
                result=PolicyResult.CONDITIONAL,
                reason=f"Refund of ${refund_amount:.2f} after ${restocking_fee:.2f} restocking fee",
                conditions=[f"Customer agrees to {fee_rate*100:.0f}% restocking fee"],
                metadata=metadata,
            )
        
        return PolicyDecision(
            result=PolicyResult.APPROVED,
            reason=f"Full refund of ${refund_amount:.2f}",
            metadata=metadata,
        )


# =============================================================================
# VALIDATORS
# =============================================================================

class ReturnRequestValidator(Validator):
    """
    Validates return request data before submission.
    """
    
    REQUIRED_FIELDS = [
        "customer_id",
        "order_id",
        "items",
        "reason_code",
        "resolution",
    ]
    
    VALID_RESOLUTIONS = [
        "FULL_REFUND",
        "STORE_CREDIT",
        "EXCHANGE",
    ]
    
    VALID_SHIPPING_METHODS = [
        "PREPAID_LABEL",
        "DROP_OFF",
        "SCHEDULE_PICKUP",
    ]
    
    def validate(self, data: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if not data.get(field):
                errors.append(ValidationError(
                    field=field,
                    message=f"{field} is required",
                    code="required",
                ))
        
        # Validate items
        items = data.get("items", [])
        if not items:
            errors.append(ValidationError(
                field="items",
                message="At least one item is required",
                code="min_length",
            ))
        else:
            for i, item in enumerate(items):
                if not item.get("product_id"):
                    errors.append(ValidationError(
                        field=f"items[{i}].product_id",
                        message="Product ID is required",
                        code="required",
                    ))
        
        # Validate resolution
        resolution = data.get("resolution", "")
        if resolution and resolution not in self.VALID_RESOLUTIONS:
            errors.append(ValidationError(
                field="resolution",
                message=f"Invalid resolution. Must be one of: {', '.join(self.VALID_RESOLUTIONS)}",
                code="invalid_choice",
            ))
        
        # Validate shipping method
        shipping = data.get("shipping_method", "")
        if shipping and shipping not in self.VALID_SHIPPING_METHODS:
            errors.append(ValidationError(
                field="shipping_method",
                message=f"Invalid shipping method. Must be one of: {', '.join(self.VALID_SHIPPING_METHODS)}",
                code="invalid_choice",
            ))
        
        return errors
