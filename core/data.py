"""
Data Layer Base Classes.

The data layer provides the Repository pattern for data access.
This abstracts away the specific data store (Cosmos DB, SQL, etc.)
and provides a clean interface for the domain layer.

Key principles:
- Repositories handle CRUD operations only
- No business logic in repositories
- Return domain objects, not raw dicts (when possible)
- Support for different backends via dependency injection
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, TypeVar
from datetime import datetime, timezone

# Type variable for entity types
T = TypeVar("T")


@dataclass
class QueryOptions:
    """Options for repository queries."""
    limit: int = 100
    offset: int = 0
    order_by: Optional[str] = None
    order_desc: bool = False
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult(Generic[T]):
    """Result of a repository query with pagination info."""
    data: List[T]
    total_count: int
    has_more: bool
    next_offset: Optional[int] = None


class Repository(ABC, Generic[T]):
    """
    Abstract base class for repositories.
    
    A Repository provides data access methods for a specific entity type.
    It abstracts the underlying data store and provides a consistent interface.
    
    Type parameter T represents the entity type this repository manages.
    
    Example:
        class CustomerRepository(Repository[Customer]):
            def get_by_id(self, id: str) -> Optional[Customer]:
                doc = self._container.read_item(id, id)
                return Customer(**doc) if doc else None
    """
    
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[T]:
        """
        Get an entity by its ID.
        
        Args:
            id: The entity's unique identifier
            
        Returns:
            The entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find(self, options: Optional[QueryOptions] = None) -> QueryResult[T]:
        """
        Find entities matching the query options.
        
        Args:
            options: Query options for filtering, pagination, sorting
            
        Returns:
            QueryResult containing the matching entities
        """
        pass
    
    @abstractmethod
    def save(self, entity: T) -> T:
        """
        Save an entity (create or update).
        
        Args:
            entity: The entity to save
            
        Returns:
            The saved entity (may have updated fields like ID, timestamps)
        """
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """
        Delete an entity by ID.
        
        Args:
            id: The entity's unique identifier
            
        Returns:
            True if deleted, False if not found
        """
        pass


class ReadOnlyRepository(ABC, Generic[T]):
    """
    Abstract base class for read-only repositories.
    
    Use this for reference data that doesn't change during operation
    (e.g., return reasons, shipping options, product catalog).
    """
    
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[T]:
        """Get an entity by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[T]:
        """Get all entities."""
        pass
    
    def get_by_code(self, code: str) -> Optional[T]:
        """
        Get an entity by a code field.
        
        Default implementation searches get_all().
        Override for more efficient lookup.
        """
        for entity in self.get_all():
            if hasattr(entity, "code") and entity.code == code:
                return entity
            if isinstance(entity, dict) and entity.get("code") == code:
                return entity
        return None


class CachingRepository(ReadOnlyRepository[T]):
    """
    A repository decorator that adds caching.
    
    Use for reference data that is frequently accessed but rarely changes.
    """
    
    def __init__(self, inner: ReadOnlyRepository[T], ttl_seconds: int = 300):
        """
        Initialize with an inner repository and cache TTL.
        
        Args:
            inner: The underlying repository to cache
            ttl_seconds: How long to cache data (default 5 minutes)
        """
        self._inner = inner
        self._ttl_seconds = ttl_seconds
        self._cache: Dict[str, Any] = {}
        self._cache_time: Optional[datetime] = None
    
    def _is_cache_valid(self) -> bool:
        if self._cache_time is None:
            return False
        age = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
        return age < self._ttl_seconds
    
    def _refresh_cache(self):
        self._cache["all"] = self._inner.get_all()
        self._cache_time = datetime.now(timezone.utc)
    
    def get_all(self) -> List[T]:
        if not self._is_cache_valid():
            self._refresh_cache()
        return self._cache.get("all", [])
    
    def get_by_id(self, id: str) -> Optional[T]:
        # Use cached data if available
        for item in self.get_all():
            if hasattr(item, "id") and item.id == id:
                return item
            if isinstance(item, dict) and item.get("id") == id:
                return item
        return None
    
    def invalidate(self):
        """Invalidate the cache."""
        self._cache.clear()
        self._cache_time = None


# =============================================================================
# UNIT OF WORK PATTERN (Optional, for transactional operations)
# =============================================================================

class UnitOfWork(ABC):
    """
    Abstract base class for Unit of Work pattern.
    
    Provides transactional semantics across multiple repository operations.
    Use when you need to ensure multiple operations succeed or fail together.
    """
    
    @abstractmethod
    def __enter__(self):
        """Begin the unit of work."""
        pass
    
    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End the unit of work, committing or rolling back."""
        pass
    
    @abstractmethod
    def commit(self):
        """Commit all changes."""
        pass
    
    @abstractmethod
    def rollback(self):
        """Rollback all changes."""
        pass
