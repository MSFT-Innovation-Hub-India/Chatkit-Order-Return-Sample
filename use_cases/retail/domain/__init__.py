"""
Retail Returns Domain Layer.

Contains pure business logic for the retail returns use case.
No database access or I/O - just business rules.
"""

from .policies import (
    ReturnEligibilityPolicy,
    RefundPolicy,
    ReturnWindowPolicy,
)
from .services import (
    RefundCalculator,
    ReturnRequestBuilder,
)

__all__ = [
    "ReturnEligibilityPolicy",
    "RefundPolicy",
    "ReturnWindowPolicy",
    "RefundCalculator",
    "ReturnRequestBuilder",
]
