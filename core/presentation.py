"""
Presentation Layer Base Classes.

The presentation layer handles widget composition and formatting.
It transforms domain objects into ChatKit widgets for display.

Key principles:
- Widgets are stateless representations
- No business logic in widgets
- Consistent theming across use cases
- Accessibility support built-in
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

from chatkit.widgets import Card, Text, Box, Button, Row, Badge, Divider, Title, Spacer
from chatkit.actions import ActionConfig


class WidgetSchemaVersion:
    """Widget schema version for backward compatibility."""
    CURRENT = "1.0"


class ButtonColor(Enum):
    """Standard button colors."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"
    INFO = "info"


class BadgeColor(Enum):
    """Standard badge colors."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"
    INFO = "info"


@dataclass
class WidgetTheme:
    """
    Theme configuration for widgets.
    
    Provides consistent styling across all widgets in a use case.
    """
    # Colors for different tiers/levels
    tier_colors: Dict[str, str] = field(default_factory=lambda: {
        "Standard": "secondary",
        "Silver": "info",
        "Gold": "warning",
        "Platinum": "primary",
    })
    
    # Status colors
    status_colors: Dict[str, str] = field(default_factory=lambda: {
        "pending": "warning",
        "approved": "success",
        "rejected": "danger",
        "processing": "info",
        "completed": "success",
        "cancelled": "secondary",
    })
    
    # Urgency indicators
    urgency_indicators: Dict[str, str] = field(default_factory=lambda: {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢",
    })
    
    # Icons for common elements
    icons: Dict[str, str] = field(default_factory=lambda: {
        "customer": "👤",
        "order": "📦",
        "return": "🔄",
        "refund": "💰",
        "shipping": "🚚",
        "email": "📧",
        "phone": "📱",
        "calendar": "🗓️",
        "warning": "⚠️",
        "success": "✅",
        "error": "❌",
        "info": "ℹ️",
    })
    
    def get_tier_color(self, tier: str) -> str:
        """Get the color for a tier level."""
        return self.tier_colors.get(tier, "secondary")
    
    def get_status_color(self, status: str) -> str:
        """Get the color for a status."""
        return self.status_colors.get(status.lower(), "secondary")
    
    def get_urgency(self, days_remaining: int) -> str:
        """Get urgency indicator based on days remaining."""
        if days_remaining <= 7:
            return self.urgency_indicators["high"]
        elif days_remaining <= 14:
            return self.urgency_indicators["medium"]
        return self.urgency_indicators["low"]
    
    def icon(self, name: str) -> str:
        """Get an icon by name."""
        return self.icons.get(name, "")


# Default theme instance
DEFAULT_THEME = WidgetTheme()


@dataclass
class WidgetAction:
    """
    Represents an action that can be triggered from a widget.
    
    Encapsulates the action configuration for buttons and interactive elements.
    """
    action_type: str
    handler: str = "server"
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_action_config(self) -> ActionConfig:
        """Convert to ChatKit ActionConfig."""
        return ActionConfig(
            type=self.action_type,
            handler=self.handler,
            payload=self.payload,
        )


class WidgetComposer(ABC):
    """
    Abstract base class for widget composers.
    
    A WidgetComposer transforms domain data into ChatKit widgets.
    Each use case should have its own composer that knows how to
    present its specific data types.
    
    Example:
        class ReturnWidgetComposer(WidgetComposer):
            def compose_customer_card(self, customer: Customer) -> Card:
                ...
            
            def compose_items_list(self, items: List[Item]) -> Card:
                ...
    """
    
    def __init__(self, theme: Optional[WidgetTheme] = None):
        """
        Initialize the composer with a theme.
        
        Args:
            theme: Optional custom theme (uses DEFAULT_THEME if not provided)
        """
        self.theme = theme or DEFAULT_THEME
        self.schema_version = WidgetSchemaVersion.CURRENT
    
    def _generate_id(self, prefix: str) -> str:
        """Generate a unique widget ID."""
        from datetime import datetime
        return f"{prefix}-{datetime.now().timestamp()}"
    
    def _create_header(
        self,
        title: str,
        icon: Optional[str] = None,
        badge: Optional[tuple] = None,  # (label, color)
    ) -> Row:
        """
        Create a standard widget header row.
        
        Args:
            title: The header title
            icon: Optional icon to prepend
            badge: Optional (label, color) tuple for a badge
            
        Returns:
            A Row widget containing the header
        """
        title_text = f"{icon} {title}" if icon else title
        children = [
            Title(id=self._generate_id("title"), value=title_text, size="lg"),
            Spacer(id=self._generate_id("spacer")),
        ]
        
        if badge:
            children.append(Badge(
                id=self._generate_id("badge"),
                label=badge[0],
                color=badge[1],
            ))
        
        return Row(id=self._generate_id("header"), children=children)
    
    def _create_info_row(self, icon: str, label: str, value: str) -> Text:
        """Create a standard info row with icon."""
        return Text(
            id=self._generate_id("info"),
            value=f"{icon} {label}: {value}" if label else f"{icon} {value}",
        )
    
    def _create_button(
        self,
        label: str,
        action: WidgetAction,
        color: Union[str, ButtonColor] = ButtonColor.PRIMARY,
        id_prefix: str = "btn",
    ) -> Button:
        """
        Create a button with an action.
        
        Args:
            label: Button label text
            action: The WidgetAction to trigger
            color: Button color
            id_prefix: Prefix for the button ID
            
        Returns:
            A Button widget
        """
        color_str = color.value if isinstance(color, ButtonColor) else color
        return Button(
            id=self._generate_id(id_prefix),
            label=label,
            color=color_str,
            onClickAction=action.to_action_config(),
        )
    
    def _wrap_in_card(self, children: List[Any], id_prefix: str = "card") -> Card:
        """Wrap a list of widgets in a Card."""
        return Card(
            id=self._generate_id(id_prefix),
            children=children,
        )
    
    @abstractmethod
    def get_widget_builders(self) -> Dict[str, Callable]:
        """
        Return a dictionary of widget builder methods.
        
        This allows the orchestration layer to call widgets by name.
        
        Returns:
            Dict mapping widget names to builder methods
        """
        pass


class TextFormatter:
    """
    Utility class for formatting text in widgets.
    
    Provides consistent formatting for common data types.
    """
    
    @staticmethod
    def currency(amount: float, currency: str = "$") -> str:
        """Format a currency amount."""
        return f"{currency}{amount:,.2f}"
    
    @staticmethod
    def date(dt: datetime, format: str = "%Y-%m-%d") -> str:
        """Format a date."""
        return dt.strftime(format)
    
    @staticmethod
    def date_relative(dt: datetime) -> str:
        """Format a date relative to now (e.g., '3 days ago')."""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        diff = now - dt
        days = diff.days
        
        if days == 0:
            return "today"
        elif days == 1:
            return "yesterday"
        elif days < 7:
            return f"{days} days ago"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            return dt.strftime("%Y-%m-%d")
    
    @staticmethod
    def truncate(text: str, max_length: int = 50) -> str:
        """Truncate text with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    @staticmethod
    def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
        """Pluralize a word based on count."""
        if count == 1:
            return f"{count} {singular}"
        return f"{count} {plural or singular + 's'}"
