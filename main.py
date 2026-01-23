"""
FastAPI Application for ChatKit Retail Returns Sample.

Exposes the ChatKit endpoint for retail order returns and serves the frontend.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from chatkit.server import StreamingResult

from config import settings

# Import shared Cosmos DB configuration
from shared.cosmos_config import COSMOS_ENDPOINT, DATABASE_NAME

# Import authentication module
from auth import (
    LoginRequest,
    LoginResponse,
    hash_password,
    verify_password,
    create_session,
    get_session,
    delete_session,
    get_user_id_from_token,
    get_password_hash_for_customer,
)

# Import the retail use case ChatKit server and Cosmos DB store
from use_cases.retail import RetailChatKitServer
from use_cases.retail.cosmos_store import CosmosDBStore
from use_cases.retail.cosmos_client import get_retail_client
from azure_client import client_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Reduce Azure SDK logging verbosity
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Global instances
data_store: Optional[CosmosDBStore] = None
server: Optional[RetailChatKitServer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown."""
    global data_store, server
    
    logger.info("Starting ChatKit Retail Returns Application...")
    
    # Initialize Cosmos DB store for thread persistence
    # Uses shared configuration from shared/cosmos_config.py
    data_store = CosmosDBStore()
    logger.info(f"Cosmos DB store initialized: {COSMOS_ENDPOINT}")
    
    # Eager-load the retail Cosmos client at startup to avoid 5s delay on first request
    logger.info("Pre-initializing retail Cosmos DB client...")
    _ = get_retail_client()
    logger.info("Retail Cosmos DB client ready")
    
    # Pre-initialize the Azure OpenAI client to avoid delay on first request
    logger.info("Pre-initializing Azure OpenAI client...")
    await client_manager.get_client()
    logger.info("Azure OpenAI client ready")
    
    # Initialize ChatKit server with Cosmos DB store
    server = RetailChatKitServer(data_store)
    logger.info("Retail ChatKit server initialized")
    logger.info("All data (threads, items, retail) stored in Azure Cosmos DB")
    
    yield
    
    # Cleanup
    logger.info("Shutting down...")
    if data_store:
        await data_store.close()


# Create FastAPI app
app = FastAPI(
    title="ChatKit Retail Returns",
    description="A self-hosted ChatKit application for retail order returns with Azure OpenAI",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chatkit")
async def chatkit_endpoint(request: Request):
    """
    Main ChatKit endpoint.
    Receives ChatKit protocol requests and returns streaming responses.
    """
    if server is None:
        return Response(content='{"error": "Server not initialized"}', status_code=500)
    
    try:
        body = await request.body()
        
        # Extract user info from auth token (try header first, then cookie)
        auth_token = request.headers.get("X-Auth-Token")
        if not auth_token:
            # Fall back to cookie (set by frontend on login)
            auth_token = request.cookies.get("auth_token")
        
        user_id = None
        user_session = None
        if auth_token:
            user_session = get_session(auth_token)
            if user_session:
                user_id = user_session.get("user_id")
                logger.debug(f"Authenticated request from user: {user_id} ({user_session.get('email')})")
        
        # Build context with full user info (for agent to use)
        context = {
            "user_id": user_id,
            "user_email": user_session.get("email") if user_session else None,
            "user_first_name": user_session.get("first_name") if user_session else None,
            "user_last_name": user_session.get("last_name") if user_session else None,
            "user_membership_tier": user_session.get("membership_tier") if user_session else None,
        }
        
        # Process the request through ChatKit server with user context
        result = await server.process(body, context)
        
        if isinstance(result, StreamingResult):
            return StreamingResponse(
                result,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        return Response(content=result.json, media_type="application/json")
    
    except Exception as e:
        logger.error(f"Error processing ChatKit request: {e}", exc_info=True)
        return Response(
            content=f'{{"error": "{str(e)}"}}',
            status_code=500,
            media_type="application/json"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "use_case": "retail_returns",
        "azure_openai_configured": bool(settings.azure_openai_endpoint),
        "cosmos_db": "common-nosql-db.documents.azure.com",
    }


@app.get("/api/branding")
async def get_branding():
    """Return branding configuration for the frontend."""
    return {
        "name": os.getenv("BRAND_NAME", "Returns Assistant"),
        "tagline": os.getenv("BRAND_TAGLINE", "Quick and easy order returns"),
        "logoUrl": os.getenv("BRAND_LOGO_URL", "/static/logo.svg"),
        "primaryColor": os.getenv("BRAND_PRIMARY_COLOR", "#2563eb"),
        "faviconUrl": os.getenv("BRAND_FAVICON_URL", "/static/favicon.ico"),
        "prompts": [
            {"label": "📦 Start a return", "prompt": "Hi, I need to return an item"},
            {"label": "👤 I'm Jane Smith", "prompt": "My email is jane.smith@email.com"},
            {"label": "📋 Check my orders", "prompt": "What orders do I have that I can return?"},
            {"label": "❓ Return policy", "prompt": "What is your return policy?"},
        ],
        "howToUse": [
            "💬 Tell me you'd like to return an item",
            "👤 Identify yourself by name or email",
            "📦 Select the item you want to return",
            "📝 Choose your reason and resolution",
            "✅ Confirm and get your return label",
        ],
        "features": [
            "🔍 Look up orders from Azure Cosmos DB",
            "📦 Interactive item selection widgets",
            "💳 Multiple resolution options (refund, exchange, credit)",
            "🏷️ Automatic return label generation",
            "⭐ Loyalty tier benefits (Gold/Platinum get free returns)",
            "☁️ Azure OpenAI powered",
        ],
    }


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """
    Authenticate user with email and password.
    Returns a session token on success.
    """
    from use_cases.retail.cosmos_client import get_retail_client
    
    try:
        # Look up customer by email
        client = get_retail_client()
        customer = client.get_customer_by_email(request.email)
        
        if not customer:
            return LoginResponse(
                success=False,
                message="Invalid email or password",
            )
        
        # Get expected password hash (from demo passwords or customer doc)
        expected_hash = customer.get("password_hash") or get_password_hash_for_customer(request.email)
        
        # Verify password
        if not verify_password(request.password, expected_hash):
            return LoginResponse(
                success=False,
                message="Invalid email or password",
            )
        
        # Create session
        token = create_session(customer)
        
        # Return user info (excluding sensitive data)
        user_info = {
            "id": customer["id"],
            "email": customer["email"],
            "first_name": customer.get("first_name", ""),
            "last_name": customer.get("last_name", ""),
            "membership_tier": customer.get("membership_tier", "Basic"),
        }
        
        logger.info(f"User logged in: {customer['email']}")
        
        return LoginResponse(
            success=True,
            message="Login successful",
            token=token,
            user=user_info,
        )
        
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return LoginResponse(
            success=False,
            message="An error occurred during login",
        )


@app.post("/api/auth/logout")
async def logout(request: Request):
    """
    Log out the current user by invalidating their session.
    """
    # Get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None
    
    if token and delete_session(token):
        return {"success": True, "message": "Logged out successfully"}
    
    return {"success": True, "message": "No active session"}


@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """
    Get the current logged-in user's info.
    """
    # Get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None
    # Fall back to cookie if header is missing
    if not token:
        token = request.cookies.get("auth_token")
    
    if not token:
        return {"authenticated": False, "user": None}
    
    session = get_session(token)
    if not session:
        return {"authenticated": False, "user": None}
    
    return {
        "authenticated": True,
        "user": {
            "id": session["user_id"],
            "email": session["email"],
            "first_name": session["first_name"],
            "last_name": session["last_name"],
            "membership_tier": session["membership_tier"],
        }
    }


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """
    Serve the ChatKit frontend.
    """
    from pathlib import Path
    
    # Check for React build first
    react_build = Path("static/dist/index.html")
    if react_build.exists():
        return FileResponse(str(react_build))
    
    # Fallback to vanilla JS
    return FileResponse("static/index.html")


# Serve static files
try:
    from pathlib import Path
    react_dist = Path("static/dist")
    if react_dist.exists():
        app.mount("/assets", StaticFiles(directory="static/dist/assets"), name="assets")
        logger.info("Serving React build from static/dist")
except (RuntimeError, FileNotFoundError):
    pass

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    logger.warning("Static files directory not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
        log_level=settings.log_level.lower()
    )
