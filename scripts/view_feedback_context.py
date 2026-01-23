#!/usr/bin/env python3
"""
View conversation context for feedback.

Usage:
    python scripts/view_feedback_context.py <thread_id>
    
Example:
    python scripts/view_feedback_context.py thr_8dad4b9b
"""

import sys
import json
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

# Configuration
COSMOS_ENDPOINT = "https://common-nosql-db.documents.azure.com:443/"
DATABASE_NAME = "db001"


def get_conversation_for_thread(thread_id: str):
    """Get the full conversation context for a thread."""
    credential = DefaultAzureCredential()
    client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
    db = client.get_database_client(DATABASE_NAME)
    
    # Get thread metadata
    threads_container = db.get_container_client("ChatKit_Threads")
    threads = list(threads_container.query_items(
        query=f"SELECT * FROM c WHERE c.id = '{thread_id}'",
        enable_cross_partition_query=True
    ))
    
    print("=" * 60)
    print("THREAD METADATA")
    print("=" * 60)
    if threads:
        print(json.dumps(threads[0], indent=2, default=str))
    else:
        print(f"Thread {thread_id} not found")
        return
    
    # Get all items in the thread
    items_container = db.get_container_client("ChatKit_Items")
    items = list(items_container.query_items(
        query=f"SELECT * FROM c WHERE c.thread_id = '{thread_id}' ORDER BY c._ts",
        enable_cross_partition_query=True
    ))
    
    # Get feedback for this thread (fetch early so we can mark items)
    feedback_container = db.get_container_client("ChatKit_Feedback")
    feedback = list(feedback_container.query_items(
        query=f"SELECT * FROM c WHERE c.thread_id = '{thread_id}' ORDER BY c.created_at DESC",
        enable_cross_partition_query=True
    ))
    
    print("\n" + "=" * 60)
    print(f"CONVERSATION ({len(items)} items)")
    print("=" * 60)
    
    for item in items:
        item_id = item.get("id", "?")
        
        # Items are wrapped in a 'data' field
        data = item.get("data", item)
        item_type = data.get("type", "unknown")
        content = data.get("content", [])
        
        # Mark feedback items
        feedback_marker = ""
        for fb in feedback:
            if item_id in fb.get("item_ids", []):
                feedback_marker = f" ⭐ [{fb.get('kind', '?').upper()} FEEDBACK]"
                break
        
        print(f"\n[{item_id}]{feedback_marker}")
        
        if item_type == "user_message":
            for c in content:
                if isinstance(c, dict):
                    text = c.get("text", "")
                    if text:
                        print(f"  👤 USER: {text}")
        
        elif item_type == "assistant_message":
            for c in content:
                if isinstance(c, dict):
                    text = c.get("text", "")
                    if text:
                        # Truncate long messages
                        if len(text) > 400:
                            text = text[:400] + "..."
                        print(f"  🤖 ASSISTANT: {text}")
        
        elif item_type == "widget":
            widget = data.get("widget", {})
            widget_type = widget.get("type", "unknown")
            print(f"  📦 WIDGET: {widget_type}")
        
        elif item_type == "workflow":
            workflow = data.get("workflow", {})
            summary = workflow.get("summary", {}).get("title", "Processing...")
            tasks = workflow.get("tasks", [])
            print(f"  ⚙️ WORKFLOW: {summary}")
            for task in tasks:
                print(f"     - {task.get('title', '?')}")
        
        else:
            print(f"  TYPE: {item_type}")
    
    # Show feedback summary
    if feedback:
        print("\n" + "=" * 60)
        print(f"FEEDBACK ({len(feedback)} entries)")
        print("=" * 60)
        for fb in feedback:
            print(f"\n  Kind: {fb.get('kind')}")
            print(f"  Item IDs: {fb.get('item_ids')}")
            print(f"  User: {fb.get('user_id')}")
            print(f"  Comment: {fb.get('comment')}")
            print(f"  Created: {fb.get('created_at')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/view_feedback_context.py <thread_id>")
        print("Example: python scripts/view_feedback_context.py thr_8dad4b9b")
        sys.exit(1)
    
    thread_id = sys.argv[1]
    get_conversation_for_thread(thread_id)
