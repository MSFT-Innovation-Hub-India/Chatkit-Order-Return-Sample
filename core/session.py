"""
Session Management for Use Cases.

Provides session context tracking across conversation turns.
This enables:
- Tracking what has been shown to the user
- Understanding natural language references ("the items above")
- Maintaining state across the return flow
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FlowStep(Enum):
    """Generic flow steps that can be extended by use cases."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class SessionContext:
    """
    Base session context that tracks conversation state.
    
    Each use case should extend this with use-case-specific fields.
    The session context is:
    - Scoped to a single conversation thread
    - Reset when a new conversation starts
    - Used to inject context into agent prompts
    """
    # Identity
    thread_id: str = ""
    
    # Customer context
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    
    # What has been displayed
    displayed_items: List[Dict[str, Any]] = field(default_factory=list)
    
    # Current flow state
    current_step: str = "not_started"
    
    # User selections (generic key-value store)
    selections: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Widget display flags
    pending_widgets: List[str] = field(default_factory=list)
    shown_widgets: List[str] = field(default_factory=list)
    
    def set_customer(self, customer_id: str, customer_name: str):
        """Set the current customer."""
        self.customer_id = customer_id
        self.customer_name = customer_name
        self._touch()
    
    def set_selection(self, key: str, value: Any):
        """Set a selection value."""
        self.selections[key] = value
        self._touch()
    
    def get_selection(self, key: str, default: Any = None) -> Any:
        """Get a selection value."""
        return self.selections.get(key, default)
    
    def add_displayed_items(self, items: List[Dict[str, Any]]):
        """Add items that have been displayed to the user."""
        self.displayed_items.extend(items)
        self._touch()
    
    def clear_displayed_items(self):
        """Clear displayed items."""
        self.displayed_items.clear()
        self._touch()
    
    def queue_widget(self, widget_name: str):
        """Queue a widget to be shown."""
        if widget_name not in self.pending_widgets:
            self.pending_widgets.append(widget_name)
    
    def mark_widget_shown(self, widget_name: str):
        """Mark a widget as shown."""
        if widget_name in self.pending_widgets:
            self.pending_widgets.remove(widget_name)
        if widget_name not in self.shown_widgets:
            self.shown_widgets.append(widget_name)
    
    def reset_widgets(self):
        """Reset widget tracking for a new turn."""
        self.pending_widgets.clear()
    
    def _touch(self):
        """Update the timestamp."""
        self.updated_at = datetime.now(timezone.utc)
    
    def to_context_string(self) -> str:
        """
        Convert session context to a string for agent injection.
        
        Override in subclasses for use-case-specific formatting.
        """
        parts = []
        
        if self.customer_id:
            parts.append(f"Customer: {self.customer_name} (ID: {self.customer_id})")
        
        if self.displayed_items:
            parts.append(f"Items displayed: {len(self.displayed_items)} items")
        
        if self.selections:
            parts.append(f"Selections: {self.selections}")
        
        parts.append(f"Current step: {self.current_step}")
        
        return "\n".join(parts) if parts else "No session context"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "thread_id": self.thread_id,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "displayed_items": self.displayed_items,
            "current_step": self.current_step,
            "selections": self.selections,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionContext":
        """Create from dictionary."""
        context = cls(
            thread_id=data.get("thread_id", ""),
            customer_id=data.get("customer_id"),
            customer_name=data.get("customer_name"),
            displayed_items=data.get("displayed_items", []),
            current_step=data.get("current_step", "not_started"),
            selections=data.get("selections", {}),
        )
        return context


class SessionManager:
    """
    Manages session contexts across threads.
    
    This is a simple in-memory manager. For production, extend
    this to persist sessions to a database.
    """
    
    def __init__(self, context_class: type = SessionContext):
        """
        Initialize the session manager.
        
        Args:
            context_class: The SessionContext class to use (can be a subclass)
        """
        self._sessions: Dict[str, SessionContext] = {}
        self._context_class = context_class
    
    def get_or_create(self, thread_id: str) -> SessionContext:
        """
        Get an existing session or create a new one.
        
        Args:
            thread_id: The thread ID to get/create session for
            
        Returns:
            The session context for this thread
        """
        if thread_id not in self._sessions:
            session = self._context_class()
            session.thread_id = thread_id
            self._sessions[thread_id] = session
            logger.debug(f"Created new session for thread {thread_id}")
        return self._sessions[thread_id]
    
    def get(self, thread_id: str) -> Optional[SessionContext]:
        """
        Get an existing session.
        
        Args:
            thread_id: The thread ID
            
        Returns:
            The session context if it exists, None otherwise
        """
        return self._sessions.get(thread_id)
    
    def update(self, thread_id: str, updates: Dict[str, Any]):
        """
        Update a session with new values.
        
        Args:
            thread_id: The thread ID
            updates: Dictionary of updates to apply
        """
        session = self.get_or_create(thread_id)
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
        session._touch()
    
    def clear(self, thread_id: str):
        """
        Clear a session.
        
        Args:
            thread_id: The thread ID to clear
        """
        if thread_id in self._sessions:
            del self._sessions[thread_id]
            logger.debug(f"Cleared session for thread {thread_id}")
    
    def clear_all(self):
        """Clear all sessions."""
        self._sessions.clear()
        logger.debug("Cleared all sessions")
