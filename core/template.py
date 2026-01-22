"""
Use Case Template.

This module provides a template for creating new use cases.
Copy this folder structure and implement the required classes.

Directory Structure:
    use_cases/
        your_use_case/
            __init__.py          # Exports the server class
            domain/
                __init__.py
                policies.py      # Business rules (PolicyEngine subclasses)
                services.py      # Domain services (calculations, validations)
            data/
                __init__.py
                repositories.py  # Data access (Repository subclasses)
                cosmos_client.py # Cosmos DB specific implementation
            presentation/
                __init__.py
                widgets.py       # Widget composer (WidgetComposer subclass)
                formatters.py    # Text formatting utilities
            orchestration/
                __init__.py
                tools.py         # Agent tools (decorated with @function_tool)
                prompts.py       # System prompts
            server.py            # Main server class (UseCaseServer subclass)
            session.py           # Session context (SessionContext subclass)

Implementation Steps:
    1. Define domain policies and services (no I/O)
    2. Create repositories for data access
    3. Build widget composer for presentation
    4. Create agent tools that wire everything together
    5. Implement the server class

See use_cases/retail/ for a complete example.
"""

# This file serves as documentation - see individual layer modules for base classes
