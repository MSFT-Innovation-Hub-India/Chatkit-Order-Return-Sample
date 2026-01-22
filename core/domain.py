"""
Domain Layer Base Classes.

The domain layer contains pure business logic with no external dependencies.
This makes business rules:
- Easy to test (no mocking needed)
- Reusable across different interfaces
- Clear and self-documenting

Example Usage:
    class ReturnPolicyEngine(PolicyEngine):
        def evaluate(self, context: dict) -> PolicyResult:
            # Pure business logic here
            ...
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum


class PolicyResult(Enum):
    """Result of a policy evaluation."""
    APPROVED = "approved"
    DENIED = "denied"
    REQUIRES_REVIEW = "requires_review"
    CONDITIONAL = "conditional"


@dataclass
class PolicyDecision:
    """
    The outcome of a policy evaluation.
    
    Attributes:
        result: The policy decision result
        reason: Human-readable explanation
        conditions: Any conditions that must be met (for CONDITIONAL results)
        metadata: Additional context for the decision
    """
    result: PolicyResult
    reason: str
    conditions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_approved(self) -> bool:
        return self.result == PolicyResult.APPROVED
    
    @property
    def is_denied(self) -> bool:
        return self.result == PolicyResult.DENIED


@dataclass
class DomainEvent:
    """
    Base class for domain events.
    
    Domain events represent something that happened in the business domain.
    They can be used for:
    - Audit logging
    - Triggering side effects
    - Event sourcing
    """
    event_type: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = field(default_factory=dict)


class PolicyEngine(ABC):
    """
    Abstract base class for policy engines.
    
    A PolicyEngine encapsulates a set of business rules that can be
    evaluated against a context to produce a decision.
    
    Example:
        class ReturnEligibilityPolicy(PolicyEngine):
            def evaluate(self, context: dict) -> PolicyDecision:
                days_since_purchase = context.get("days_since_purchase", 0)
                if days_since_purchase > 30:
                    return PolicyDecision(
                        result=PolicyResult.DENIED,
                        reason="Return window has expired"
                    )
                return PolicyDecision(
                    result=PolicyResult.APPROVED,
                    reason="Item is eligible for return"
                )
    """
    
    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> PolicyDecision:
        """
        Evaluate the policy against the given context.
        
        Args:
            context: Dictionary containing all data needed for evaluation
            
        Returns:
            PolicyDecision with the result and explanation
        """
        pass
    
    def explain(self, context: Dict[str, Any]) -> str:
        """
        Provide a human-readable explanation of how the policy would be applied.
        
        Default implementation returns the reason from evaluate().
        Override for more detailed explanations.
        """
        decision = self.evaluate(context)
        return decision.reason


class DomainService(ABC):
    """
    Abstract base class for domain services.
    
    Domain services contain business logic that doesn't belong to a single entity.
    They orchestrate multiple policies and entities to perform complex operations.
    
    Key principles:
    - No I/O operations (database, network, file)
    - All dependencies passed as parameters
    - Return domain objects, not DTOs
    
    Example:
        class RefundCalculator(DomainService):
            def calculate(self, items: List[Item], tier: str) -> RefundResult:
                subtotal = sum(item.price * item.quantity for item in items)
                fee = self._calculate_restocking_fee(tier, subtotal)
                return RefundResult(amount=subtotal - fee, fee=fee)
    """
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        Execute the domain service operation.
        
        Implementation should contain pure business logic only.
        """
        pass


@dataclass
class ValidationError:
    """A validation error with field and message."""
    field: str
    message: str
    code: str = "invalid"


class Validator(ABC):
    """
    Abstract base class for validators.
    
    Validators check that data meets business requirements before processing.
    """
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> List[ValidationError]:
        """
        Validate the data and return any errors.
        
        Args:
            data: The data to validate
            
        Returns:
            List of ValidationError objects (empty if valid)
        """
        pass
    
    def is_valid(self, data: Dict[str, Any]) -> bool:
        """Check if data is valid."""
        return len(self.validate(data)) == 0


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def days_between(date1: datetime, date2: datetime) -> int:
    """Calculate the number of days between two dates."""
    if date1.tzinfo is None:
        date1 = date1.replace(tzinfo=timezone.utc)
    if date2.tzinfo is None:
        date2 = date2.replace(tzinfo=timezone.utc)
    return abs((date2 - date1).days)


def parse_date(date_string: str) -> Optional[datetime]:
    """Parse an ISO format date string safely."""
    if not date_string:
        return None
    try:
        if "Z" in date_string:
            return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        elif "+" in date_string:
            return datetime.fromisoformat(date_string)
        else:
            return datetime.fromisoformat(date_string).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
