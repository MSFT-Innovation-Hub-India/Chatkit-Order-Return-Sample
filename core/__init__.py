"""
Core Framework for ChatKit Use Cases.

This module provides the extensible base classes and interfaces
that all use cases should implement. The layered architecture ensures:

1. Domain Layer - Pure business rules, no I/O
2. Data Layer - Repository pattern for data access
3. Presentation Layer - Widget composition
4. Orchestration Layer - Agent tools that wire everything together

Each use case follows this pattern for consistency and reusability.
"""

from .domain import DomainService, PolicyEngine
from .data import Repository
from .presentation import WidgetComposer, WidgetTheme
from .orchestration import UseCaseServer, ToolRegistry
from .session import SessionManager, SessionContext

__all__ = [
    # Domain
    "DomainService",
    "PolicyEngine",
    # Data
    "Repository",
    # Presentation
    "WidgetComposer",
    "WidgetTheme",
    # Orchestration
    "UseCaseServer",
    "ToolRegistry",
    # Session
    "SessionManager",
    "SessionContext",
]
