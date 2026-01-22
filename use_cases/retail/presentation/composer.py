"""
Retail Widget Composer.

Transforms retail domain data into ChatKit widgets.
All widget building logic is centralized here for consistency.
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from chatkit.widgets import Card, Text, Box, Button, Row, Badge, Divider, Title, Spacer
from chatkit.actions import ActionConfig

from core.presentation import (
    WidgetComposer,
    WidgetTheme,
    WidgetAction,
    ButtonColor,
    TextFormatter,
)


class RetailWidgetTheme(WidgetTheme):
    """Custom theme for retail widgets."""
    
    def __init__(self):
        super().__init__()
        # Add retail-specific icons
        self.icons.update({
            "return": "🔄",
            "refund": "💰",
            "exchange": "🔁",
            "credit": "🎁",
            "label": "🏷️",
            "dropoff": "📮",
            "pickup": "🚛",
            "star": "⭐",
        })


class ReturnWidgetComposer(WidgetComposer):
    """
    Widget composer for the retail returns flow.
    
    Provides methods for building all widgets used in the return process.
    """
    
    def __init__(self):
        super().__init__(theme=RetailWidgetTheme())
    
    def get_widget_builders(self) -> Dict[str, Callable]:
        """Return mapping of widget names to builder methods."""
        return {
            "customer": self.compose_customer_card,
            "returnable_items": self.compose_returnable_items,
            "reasons": self.compose_reasons,
            "resolutions": self.compose_resolutions,
            "shipping": self.compose_shipping_options,
            "confirmation": self.compose_confirmation,
            "retention_offer": self.compose_retention_offer,
        }
    
    # =========================================================================
    # CUSTOMER WIDGET
    # =========================================================================
    
    def compose_customer_card(self, customer: Dict[str, Any]) -> Card:
        """
        Build a customer profile card.
        
        Args:
            customer: Customer data dictionary
            
        Returns:
            Card widget showing customer info
        """
        tier = customer.get("tier", "Standard")
        
        return self._wrap_in_card([
            self._create_header(
                title=customer.get("name", "Customer"),
                icon=self.theme.icon("customer"),
                badge=(f"{self.theme.icon('star')} {tier}", self.theme.get_tier_color(tier)),
            ),
            Divider(id=self._generate_id("div")),
            Text(
                id=self._generate_id("email"),
                value=f"{self.theme.icon('email')} {customer.get('email', '')}",
            ),
            Text(
                id=self._generate_id("phone"),
                value=f"{self.theme.icon('phone')} {customer.get('phone', 'N/A')}",
            ),
            Text(
                id=self._generate_id("member"),
                value=f"{self.theme.icon('calendar')} Member since: {customer.get('member_since', 'N/A')}",
            ),
        ], id_prefix="customer-card")
    
    # =========================================================================
    # RETURNABLE ITEMS WIDGET
    # =========================================================================
    
    def compose_returnable_items(
        self,
        orders: List[Dict[str, Any]],
        thread_id: str,
        customer_id: str = "",
    ) -> Card:
        """
        Build a widget for selecting items to return.
        
        Args:
            orders: List of orders with returnable items
            thread_id: The conversation thread ID
            customer_id: Optional customer ID for actions
            
        Returns:
            Card widget with item selection buttons
        """
        children = [
            Title(
                id=self._generate_id("title"),
                value=f"{self.theme.icon('return')} Select Item to Return",
                size="lg",
            ),
            Text(
                id=self._generate_id("subtitle"),
                value="Click on an item to start the return process",
            ),
            Divider(id=self._generate_id("div")),
        ]
        
        for order in orders:
            order_id = order.get("id", order.get("order_id", ""))
            items = order.get("items", order.get("returnable_items", []))
            
            children.append(Text(
                id=self._generate_id("order"),
                value=f"{self.theme.icon('order')} Order: {order_id}",
            ))
            
            for item in items:
                children.append(self._build_item_row(item, order_id, customer_id))
            
            children.append(Spacer(id=self._generate_id("spacer")))
        
        return self._wrap_in_card(children, id_prefix="items-card")
    
    def _build_item_row(
        self,
        item: Dict[str, Any],
        order_id: str,
        customer_id: str,
    ) -> Row:
        """Build a row for a single returnable item."""
        # Get item details
        product_id = item.get("product_id", "")
        name = item.get("name", "Unknown Item")
        price = item.get("unit_price", 0)
        quantity = item.get("quantity", 1)
        
        # Get days remaining from eligibility data
        eligibility = item.get("return_eligibility", {})
        days = item.get("days_remaining", eligibility.get("days_remaining", 30))
        
        urgency = self.theme.get_urgency(days)
        
        return Row(
            id=self._generate_id("item-row"),
            children=[
                Text(id=self._generate_id("urgency"), value=urgency),
                Box(
                    id=self._generate_id("item-box"),
                    children=[
                        Text(id=self._generate_id("name"), value=name),
                        Text(
                            id=self._generate_id("details"),
                            value=f"Qty: {quantity} • ${price:.2f} each • {days} days left",
                        ),
                    ],
                ),
                Button(
                    id=self._generate_id("select-btn"),
                    label="Return This",
                    color="primary",
                    onClickAction=ActionConfig(
                        type="select_return_item",
                        handler="server",
                        payload={
                            "order_id": order_id,
                            "product_id": product_id,
                            "name": name,
                            "unit_price": price,
                            "quantity": quantity,
                            "customer_id": customer_id,
                        },
                    ),
                ),
            ],
        )
    
    # =========================================================================
    # REASONS WIDGET
    # =========================================================================
    
    def compose_reasons(
        self,
        reasons: List[Dict[str, Any]],
        thread_id: str,
    ) -> Card:
        """
        Build a widget for selecting return reason.
        
        Args:
            reasons: List of reason options
            thread_id: The conversation thread ID
            
        Returns:
            Card widget with reason buttons
        """
        children = [
            Title(
                id=self._generate_id("title"),
                value="❓ Why are you returning this item?",
                size="lg",
            ),
            Divider(id=self._generate_id("div")),
        ]
        
        for reason in reasons:
            code = reason.get("code", "")
            label = reason.get("label", reason.get("name", code))
            description = reason.get("description", "")
            
            children.append(
                Row(
                    id=self._generate_id("reason-row"),
                    children=[
                        Box(
                            id=self._generate_id("reason-box"),
                            children=[
                                Text(id=self._generate_id("label"), value=label),
                                Text(id=self._generate_id("desc"), value=description) if description else Spacer(id=self._generate_id("spacer")),
                            ],
                        ),
                        Button(
                            id=self._generate_id("reason-btn"),
                            label="Select",
                            color="secondary",
                            onClickAction=ActionConfig(
                                type="select_reason",
                                handler="server",
                                payload={"reason_code": code, "reason_label": label},
                            ),
                        ),
                    ],
                )
            )
        
        return self._wrap_in_card(children, id_prefix="reasons-card")
    
    # =========================================================================
    # RESOLUTIONS WIDGET
    # =========================================================================
    
    def compose_resolutions(
        self,
        options: List[Dict[str, Any]],
        thread_id: str,
    ) -> Card:
        """
        Build a widget for selecting resolution type.
        
        Args:
            options: List of resolution options
            thread_id: The conversation thread ID
            
        Returns:
            Card widget with resolution buttons
        """
        children = [
            Title(
                id=self._generate_id("title"),
                value=f"{self.theme.icon('refund')} How would you like to be compensated?",
                size="lg",
            ),
            Divider(id=self._generate_id("div")),
        ]
        
        # Icon mapping for resolutions
        resolution_icons = {
            "FULL_REFUND": self.theme.icon("refund"),
            "STORE_CREDIT": self.theme.icon("credit"),
            "EXCHANGE": self.theme.icon("exchange"),
        }
        
        for option in options:
            code = option.get("code", "")
            label = option.get("label", option.get("name", code))
            description = option.get("description", "")
            icon = resolution_icons.get(code, "")
            
            # Highlight store credit bonus
            color = "warning" if code == "STORE_CREDIT" else "primary"
            
            children.append(
                Button(
                    id=self._generate_id("resolution-btn"),
                    label=f"{icon} {label}",
                    color=color,
                    onClickAction=ActionConfig(
                        type="select_resolution",
                        handler="server",
                        payload={"resolution": code, "resolution_label": label},
                    ),
                )
            )
            
            if description:
                children.append(Text(
                    id=self._generate_id("res-desc"),
                    value=f"  ↳ {description}",
                ))
        
        return self._wrap_in_card(children, id_prefix="resolution-card")
    
    # =========================================================================
    # SHIPPING OPTIONS WIDGET
    # =========================================================================
    
    def compose_shipping_options(
        self,
        options: List[Dict[str, Any]],
        thread_id: str,
    ) -> Card:
        """
        Build a widget for selecting shipping method.
        
        Args:
            options: List of shipping options
            thread_id: The conversation thread ID
            
        Returns:
            Card widget with shipping buttons
        """
        children = [
            Title(
                id=self._generate_id("title"),
                value=f"{self.theme.icon('shipping')} How would you like to return the item?",
                size="lg",
            ),
            Divider(id=self._generate_id("div")),
        ]
        
        # Icon mapping for shipping methods
        shipping_icons = {
            "PREPAID_LABEL": self.theme.icon("label"),
            "DROP_OFF": self.theme.icon("dropoff"),
            "SCHEDULE_PICKUP": self.theme.icon("pickup"),
        }
        
        for option in options:
            code = option.get("code", "")
            label = option.get("label", option.get("name", code))
            description = option.get("description", "")
            icon = shipping_icons.get(code, self.theme.icon("shipping"))
            
            children.append(
                Button(
                    id=self._generate_id("shipping-btn"),
                    label=f"{icon} {label}",
                    color="primary",
                    onClickAction=ActionConfig(
                        type="select_shipping",
                        handler="server",
                        payload={"shipping_method": code, "shipping_label": label},
                    ),
                )
            )
            
            if description:
                children.append(Text(
                    id=self._generate_id("ship-desc"),
                    value=f"  ↳ {description}",
                ))
        
        return self._wrap_in_card(children, id_prefix="shipping-card")
    
    # =========================================================================
    # CONFIRMATION WIDGET
    # =========================================================================
    
    def compose_confirmation(
        self,
        confirmation: Dict[str, Any],
        thread_id: str,
    ) -> Card:
        """
        Build a confirmation widget for a completed return.
        
        Args:
            confirmation: Return confirmation data
            thread_id: The conversation thread ID
            
        Returns:
            Card widget showing confirmation details
        """
        return_id = confirmation.get("id", "")
        status = confirmation.get("status", "pending")
        refund = confirmation.get("refund_amount", 0)
        
        return self._wrap_in_card([
            self._create_header(
                title="Return Request Confirmed!",
                icon=self.theme.icon("success"),
                badge=(status.title(), self.theme.get_status_color(status)),
            ),
            Divider(id=self._generate_id("div")),
            Text(
                id=self._generate_id("return-id"),
                value=f"Return ID: {return_id}",
            ),
            Text(
                id=self._generate_id("refund"),
                value=f"Refund Amount: {TextFormatter.currency(refund)}",
            ),
            Spacer(id=self._generate_id("spacer")),
            Text(
                id=self._generate_id("email-note"),
                value=f"{self.theme.icon('email')} A confirmation email has been sent with return instructions.",
            ),
        ], id_prefix="confirmation-card")
    
    # =========================================================================
    # RETENTION OFFER WIDGET
    # =========================================================================
    
    def compose_retention_offer(
        self,
        offers: List[Dict[str, Any]],
        thread_id: str,
    ) -> Card:
        """
        Build a widget showing retention offers.
        
        Args:
            offers: List of discount offers
            thread_id: The conversation thread ID
            
        Returns:
            Card widget with offer options
        """
        children = [
            Title(
                id=self._generate_id("title"),
                value=f"{self.theme.icon('credit')} Special Offer for You!",
                size="lg",
            ),
            Text(
                id=self._generate_id("subtitle"),
                value="Before you return, would you like to keep the item with a discount?",
            ),
            Divider(id=self._generate_id("div")),
        ]
        
        for offer in offers:
            discount = offer.get("discount_percent", offer.get("discount", 0))
            code = offer.get("code", "")
            description = offer.get("description", f"{discount}% off your purchase")
            
            children.append(
                Button(
                    id=self._generate_id("offer-btn"),
                    label=f"🎉 Accept {discount}% Discount",
                    color="success",
                    onClickAction=ActionConfig(
                        type="accept_offer",
                        handler="server",
                        payload={"offer_code": code, "discount": discount},
                    ),
                )
            )
            children.append(Text(
                id=self._generate_id("offer-desc"),
                value=description,
            ))
        
        children.append(Spacer(id=self._generate_id("spacer")))
        children.append(
            Button(
                id=self._generate_id("decline-btn"),
                label="No thanks, continue with return",
                color="secondary",
                onClickAction=ActionConfig(
                    type="decline_offers",
                    handler="server",
                    payload={},
                ),
            )
        )
        
        return self._wrap_in_card(children, id_prefix="retention-card")
