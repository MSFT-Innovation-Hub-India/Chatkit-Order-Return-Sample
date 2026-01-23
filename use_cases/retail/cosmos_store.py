"""
Azure Cosmos DB-based data store for ChatKit.
Implements the Store interface required by ChatKit server.
Uses the same Cosmos DB account as the retail data for unified storage.
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Any

from azure.identity import DefaultAzureCredential, AzureCliCredential
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from chatkit.store import Store, ThreadMetadata, ThreadItem, Page, Attachment
from chatkit.types import ActiveStatus
from pydantic import TypeAdapter

# Import shared configuration
from shared.cosmos_config import (
    COSMOS_ENDPOINT,
    DATABASE_NAME,
    CHATKIT_CONTAINERS,
)

logger = logging.getLogger(__name__)

# Create a TypeAdapter for parsing thread items from JSON
_thread_item_adapter = TypeAdapter(ThreadItem)


class CosmosDBStore(Store):
    """
    Azure Cosmos DB-based persistent store for ChatKit threads and messages.
    Production-ready store that uses the same Cosmos DB as retail data.
    """
    
    def __init__(
        self,
        endpoint: str = COSMOS_ENDPOINT,
        database_name: str = DATABASE_NAME,
        threads_container: str = CHATKIT_CONTAINERS["threads"],
        items_container: str = CHATKIT_CONTAINERS["items"],
    ):
        """
        Initialize the Cosmos DB store.
        
        Args:
            endpoint: Cosmos DB endpoint URL
            database_name: Database name
            threads_container: Container name for threads
            items_container: Container name for thread items
        """
        self.endpoint = endpoint
        self.database_name = database_name
        self.threads_container_name = threads_container
        self.items_container_name = items_container
        
        # Initialize Cosmos DB client with DefaultAzureCredential
        # This supports multiple auth methods with fallback
        logger.info("Initializing Cosmos DB connection...")
        self._credential = DefaultAzureCredential(
            exclude_interactive_browser_credential=False,
            exclude_shared_token_cache_credential=False,
        )
        self._client = CosmosClient(endpoint, credential=self._credential)
        self._database = self._client.get_database_client(database_name)
        logger.info(f"Connected to Cosmos DB: {database_name}")
        
        # Container clients (will be created if needed)
        self._threads_container = None
        self._items_container = None
        self._initialized = False
    
    def _ensure_containers(self):
        """Ensure containers exist (lazy initialization)."""
        if self._initialized:
            return
        
        try:
            # Try to get existing containers
            self._threads_container = self._database.get_container_client(
                self.threads_container_name
            )
            self._items_container = self._database.get_container_client(
                self.items_container_name
            )
            
            # Verify they exist by reading their properties
            self._threads_container.read()
            self._items_container.read()
            
        except CosmosResourceNotFoundError:
            # Containers don't exist - they should be created via Azure CLI
            # since this account has data plane container creation disabled
            raise RuntimeError(
                f"ChatKit containers not found in Cosmos DB. "
                f"Please create '{self.threads_container_name}' and '{self.items_container_name}' "
                f"containers using Azure CLI or Azure Portal."
            )
        
        self._initialized = True
    
    async def close(self):
        """Close the Cosmos DB connection."""
        # Cosmos DB sync client doesn't need explicit close
        pass
    
    # ----- Store interface implementation -----
    
    def _get_user_id_from_context(self, context: Any) -> Optional[str]:
        """Extract user_id from request context if available."""
        if context is None:
            return None
        
        # Try to get user_id from various context structures
        if hasattr(context, 'user_id'):
            return context.user_id
        if isinstance(context, dict):
            return context.get('user_id')
        if hasattr(context, 'state') and isinstance(context.state, dict):
            return context.state.get('user_id')
        
        return None
    
    async def load_thread(self, thread_id: str, context: Any) -> ThreadMetadata:
        """Load a thread's metadata by id."""
        self._ensure_containers()
        
        try:
            item = self._threads_container.read_item(
                item=thread_id,
                partition_key=thread_id,
            )
            
            # Optional: Verify ownership if user_id is in context
            user_id = self._get_user_id_from_context(context)
            if user_id and item.get("owner_id") and item["owner_id"] != user_id:
                logger.warning(f"User {user_id} attempted to access thread {thread_id} owned by {item.get('owner_id')}")
                # For now, allow access but log it. In strict mode, raise an error.
            
            created_at = datetime.fromisoformat(item.get("created_at", datetime.now(timezone.utc).isoformat()))
            
            return ThreadMetadata(
                id=item["id"],
                title=item.get("title", "New Chat"),
                status=ActiveStatus(),
                created_at=created_at,
            )
            
        except CosmosResourceNotFoundError:
            # Thread doesn't exist, create it
            return await self._create_thread(thread_id, context)
    
    async def _create_thread(self, thread_id: str, context: Any) -> ThreadMetadata:
        """Create a new thread with optional owner association."""
        self._ensure_containers()
        
        now = datetime.now(timezone.utc)
        user_id = self._get_user_id_from_context(context)
        
        logger.info(f"_create_thread called with thread_id={thread_id}, user_id={user_id}, context type={type(context)}")
        
        thread_doc = {
            "id": thread_id,
            "title": "New Chat",
            "status": "active",
            "owner_id": user_id,  # Associate thread with user (None if anonymous)
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        self._threads_container.upsert_item(thread_doc)
        logger.info(f"Created thread {thread_id} for user {user_id or 'anonymous'}")
        
        return ThreadMetadata(
            id=thread_id,
            title="New Chat",
            status=ActiveStatus(),
            created_at=now,
        )
    
    async def save_thread(self, thread: ThreadMetadata, context: Any) -> None:
        """Persist thread metadata."""
        self._ensure_containers()
        
        now = datetime.now(timezone.utc).isoformat()
        status_str = thread.status.type if thread.status else "active"
        user_id = self._get_user_id_from_context(context)
        
        # Try to preserve created_at and owner_id from existing document
        existing_owner_id = None
        try:
            existing = self._threads_container.read_item(
                item=thread.id,
                partition_key=thread.id,
            )
            created_at = existing.get("created_at", now)
            existing_owner_id = existing.get("owner_id")
        except CosmosResourceNotFoundError:
            created_at = now
            # New thread - set owner from context
            logger.info(f"save_thread creating new thread {thread.id} for user {user_id or 'anonymous'}")
        
        thread_doc = {
            "id": thread.id,
            "title": thread.title,
            "status": status_str,
            "owner_id": existing_owner_id if existing_owner_id else user_id,  # Preserve existing or set from context
            "created_at": created_at,
            "updated_at": now,
        }
        
        self._threads_container.upsert_item(thread_doc)
    
    async def load_thread_items(
        self,
        thread_id: str,
        after: str | None,
        limit: int,
        order: str,
        context: Any,
    ) -> Page[ThreadItem]:
        """Load a page of thread items with pagination."""
        self._ensure_containers()
        
        order_dir = "DESC" if order == "desc" else "ASC"
        
        # Build query
        if after:
            query = f"""
                SELECT * FROM c 
                WHERE c.thread_id = @thread_id AND c.id > @after
                ORDER BY c.created_at {order_dir}
            """
            params = [
                {"name": "@thread_id", "value": thread_id},
                {"name": "@after", "value": after},
            ]
        else:
            query = f"""
                SELECT * FROM c 
                WHERE c.thread_id = @thread_id
                ORDER BY c.created_at {order_dir}
            """
            params = [{"name": "@thread_id", "value": thread_id}]
        
        # Execute query with limit + 1 to check for more
        results = list(self._items_container.query_items(
            query=query,
            parameters=params,
            max_item_count=limit + 1,
            enable_cross_partition_query=True,
        ))
        
        items = []
        has_more = len(results) > limit
        last_id = None
        
        for i, row in enumerate(results):
            if i >= limit:
                break
            
            # Parse the item data
            item_data = row.get("data", row)
            if isinstance(item_data, str):
                item_data = json.loads(item_data)
            
            item = _thread_item_adapter.validate_python(item_data)
            items.append(item)
            last_id = row["id"]
        
        return Page(data=items, has_more=has_more, after=last_id if has_more else None)
    
    async def add_thread_item(
        self, thread_id: str, item: ThreadItem, context: Any
    ) -> None:
        """Persist a newly created thread item."""
        await self.save_item(thread_id, item, context)
    
    async def save_item(
        self, thread_id: str, item: ThreadItem, context: Any
    ) -> None:
        """Upsert a thread item by id."""
        self._ensure_containers()
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Serialize item to JSON
        if hasattr(item, 'model_dump'):
            item_data = item.model_dump(mode='json')
        else:
            item_data = dict(item)
        
        item_id = item_data.get('id', f"item_{uuid.uuid4().hex[:12]}")
        
        # Store with thread_id for querying
        doc = {
            "id": item_id,
            "thread_id": thread_id,
            "data": item_data,
            "created_at": now,
        }
        
        self._items_container.upsert_item(doc)
    
    async def load_item(
        self, thread_id: str, item_id: str, context: Any
    ) -> ThreadItem:
        """Load a thread item by id."""
        self._ensure_containers()
        
        try:
            # Query by both id and thread_id
            query = "SELECT * FROM c WHERE c.id = @id AND c.thread_id = @thread_id"
            params = [
                {"name": "@id", "value": item_id},
                {"name": "@thread_id", "value": thread_id},
            ]
            
            results = list(self._items_container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            ))
            
            if results:
                item_data = results[0].get("data", results[0])
                if isinstance(item_data, str):
                    item_data = json.loads(item_data)
                return _thread_item_adapter.validate_python(item_data)
            
            raise KeyError(f"Item {item_id} not found in thread {thread_id}")
            
        except CosmosResourceNotFoundError:
            raise KeyError(f"Item {item_id} not found in thread {thread_id}")
    
    async def delete_thread(self, thread_id: str, context: Any) -> None:
        """Delete a thread and its items."""
        self._ensure_containers()
        
        # Delete all items for this thread
        query = "SELECT c.id FROM c WHERE c.thread_id = @thread_id"
        params = [{"name": "@thread_id", "value": thread_id}]
        
        items = list(self._items_container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        ))
        
        for item in items:
            try:
                self._items_container.delete_item(
                    item=item["id"],
                    partition_key=thread_id,
                )
            except CosmosResourceNotFoundError:
                pass
        
        # Delete the thread
        try:
            self._threads_container.delete_item(
                item=thread_id,
                partition_key=thread_id,
            )
        except CosmosResourceNotFoundError:
            pass
    
    async def delete_thread_item(
        self, thread_id: str, item_id: str, context: Any
    ) -> None:
        """Delete a thread item by id."""
        self._ensure_containers()
        
        try:
            self._items_container.delete_item(
                item=item_id,
                partition_key=thread_id,
            )
        except CosmosResourceNotFoundError:
            pass
    
    async def load_threads(
        self,
        limit: int,
        after: str | None,
        order: str,
        context: Any,
    ) -> Page[ThreadMetadata]:
        """Load a page of threads with pagination, filtered by owner if authenticated."""
        self._ensure_containers()
        
        order_dir = "DESC" if order == "desc" else "ASC"
        user_id = self._get_user_id_from_context(context)
        
        logger.info(f"load_threads called with user_id={user_id}, context type={type(context)}, context={context}")
        
        # Build query - filter by owner if user is authenticated
        params = []
        
        if user_id:
            # Authenticated user: show only their threads
            if after:
                query = f"""
                    SELECT * FROM c 
                    WHERE c.owner_id = @owner_id AND c.id > @after
                    ORDER BY c.updated_at {order_dir}
                """
                params = [
                    {"name": "@owner_id", "value": user_id},
                    {"name": "@after", "value": after},
                ]
            else:
                query = f"""
                    SELECT * FROM c 
                    WHERE c.owner_id = @owner_id
                    ORDER BY c.updated_at {order_dir}
                """
                params = [{"name": "@owner_id", "value": user_id}]
        else:
            # Anonymous user: show only anonymous threads (no owner_id)
            if after:
                query = f"""
                    SELECT * FROM c 
                    WHERE (NOT IS_DEFINED(c.owner_id) OR c.owner_id = null) AND c.id > @after
                    ORDER BY c.updated_at {order_dir}
                """
                params = [{"name": "@after", "value": after}]
            else:
                query = f"""
                    SELECT * FROM c 
                    WHERE NOT IS_DEFINED(c.owner_id) OR c.owner_id = null
                    ORDER BY c.updated_at {order_dir}
                """
                params = []
        
        results = list(self._threads_container.query_items(
            query=query,
            parameters=params,
            max_item_count=limit + 1,
            enable_cross_partition_query=True,
        ))
        
        logger.info(f"load_threads query returned {len(results)} results for user_id={user_id}")
        
        threads = []
        has_more = len(results) > limit
        last_id = None
        
        for i, row in enumerate(results):
            if i >= limit:
                break
            
            created_at = datetime.fromisoformat(row.get("created_at", datetime.now(timezone.utc).isoformat()))
            
            threads.append(ThreadMetadata(
                id=row["id"],
                title=row.get("title", "New Chat"),
                status=ActiveStatus(),
                created_at=created_at,
            ))
            last_id = row["id"]
        
        return Page(data=threads, has_more=has_more, after=last_id if has_more else None)
    
    async def load_attachments(
        self,
        thread_id: str,
        attachment_ids: list[str],
        context: Any,
    ) -> list[Attachment]:
        """Load attachments by IDs. Not implemented for this use case."""
        return []
    
    async def load_attachment(
        self,
        thread_id: str,
        attachment_id: str,
        context: Any,
    ) -> Attachment:
        """Load a single attachment by ID. Not implemented for this use case."""
        raise KeyError(f"Attachment {attachment_id} not found")
    
    async def save_attachment(
        self,
        thread_id: str,
        attachment: Attachment,
        context: Any,
    ) -> None:
        """Save an attachment. Not implemented for this use case."""
        pass
    
    async def delete_attachment(
        self,
        thread_id: str,
        attachment_id: str,
        context: Any,
    ) -> None:
        """Delete an attachment. Not implemented for this use case."""
        pass

    # =========================================================================
    # FEEDBACK STORAGE
    # =========================================================================
    
    def _ensure_feedback_container(self):
        """Ensure the feedback container exists (lazy initialization)."""
        if hasattr(self, '_feedback_container') and self._feedback_container:
            return
        
        feedback_container_name = CHATKIT_CONTAINERS.get("feedback", "ChatKit_Feedback")
        try:
            self._feedback_container = self._database.get_container_client(feedback_container_name)
            self._feedback_container.read()
        except CosmosResourceNotFoundError:
            logger.warning(
                f"Feedback container '{feedback_container_name}' not found. "
                f"Feedback will not be persisted until container is created."
            )
            self._feedback_container = None
    
    async def save_feedback(
        self,
        thread_id: str,
        item_ids: list[str],
        kind: str,
        user_id: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> dict:
        """
        Save user feedback for assistant responses.
        
        Args:
            thread_id: The conversation thread ID
            item_ids: List of message item IDs the feedback applies to
            kind: "positive" or "negative"
            user_id: Optional user ID who gave the feedback
            comment: Optional comment explaining the feedback
            
        Returns:
            The saved feedback document
        """
        self._ensure_feedback_container()
        
        if not self._feedback_container:
            logger.warning("Feedback container not available - feedback not saved")
            return {}
        
        now = datetime.now(timezone.utc)
        feedback_id = str(uuid.uuid4())
        
        feedback_doc = {
            "id": feedback_id,
            "thread_id": thread_id,
            "item_ids": item_ids,
            "kind": kind,
            "user_id": user_id,
            "comment": comment,
            "created_at": now.isoformat(),
        }
        
        self._feedback_container.upsert_item(feedback_doc)
        logger.info(f"Saved {kind} feedback for thread {thread_id}, items {item_ids}")
        
        return feedback_doc
    
    async def get_feedback_for_thread(self, thread_id: str) -> list[dict]:
        """Get all feedback for a specific thread."""
        self._ensure_feedback_container()
        
        if not self._feedback_container:
            return []
        
        query = "SELECT * FROM c WHERE c.thread_id = @thread_id ORDER BY c.created_at DESC"
        items = list(self._feedback_container.query_items(
            query=query,
            parameters=[{"name": "@thread_id", "value": thread_id}],
            enable_cross_partition_query=True,
        ))
        
        return items
