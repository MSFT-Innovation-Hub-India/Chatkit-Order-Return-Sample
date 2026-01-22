"""
Shared modules for the Order Returns application.

This package contains shared configuration and utilities used across the application.
"""

from shared.cosmos_config import (
    COSMOS_ENDPOINT,
    DATABASE_NAME,
    RETAIL_CONTAINERS,
    CHATKIT_CONTAINERS,
)

__all__ = [
    "COSMOS_ENDPOINT",
    "DATABASE_NAME",
    "RETAIL_CONTAINERS",
    "CHATKIT_CONTAINERS",
]
