# main.py  (project root)

# ── Imports ───────────────────────────────────────────────────────────────────

from contextlib import asynccontextmanager
# asynccontextmanager: Decorator that turns an async generator function
#                      into an async context manager (for use with "async with").
# We use it to define the app's LIFESPAN — code that runs on startup and shutdown.

from fastapi import FastAPI
# FastAPI: The main application class.
# This is what ASGI servers (like uvicorn) receive and serve.

from fastapi.middleware.cors import CORSMiddleware
# CORSMiddleware: Handles Cross-Origin Resource Sharing headers.
# Allows your frontend (on a different domain) to make API requests.

import redis.asyncio as aioredis
# aioredis: Async Redis client.
# We import it as aioredis to clearly indicate it's the async version.

from fastapi_limiter import FastAPILimiter
# FastAPILimiter: Rate limiting library that uses Redis to track request counts.
# Initializing it here connects it to our Redis instance.

from app.core.config import settings
# Our Settings singleton with all environment variables.

from app.db.session import engine
# The async SQLAlchemy engine — used during startup to verify DB connectivity.

# ── Router Imports (added as each feature branch is merged) ───────────────────
from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.folders import router as folders_router
from app.api.v1.documents import router as documents_router
# from app.api.v1.search import router as search_router
# from app.api.v1.audit import router as audit_router
# NOTE: These are commented out now — they will be uncommented as each
#       feature branch is merged into development.


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = None
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=3,
            # 3 seconds timeout — fail fast, don't hang forever
        )
        await FastAPILimiter.init(redis_client)
        print("✅ Redis connected successfully.")

    except Exception as e:
        print(f"⚠️  Redis unavailable: {e}")
        if settings.APP_ENV == "production":
            # Production: Redis is MANDATORY — abort
            raise RuntimeError(f"Redis required in production: {e}")
        else:
            # Development: warn and continue without Redis
            print("⚠️  Rate limiting and logout blocklist are DISABLED.")
            redis_client = None

    print(f"✅ '{settings.APP_NAME}' started | ENV: {settings.APP_ENV}")
    yield

    # Shutdown
    if redis_client:
        await redis_client.close()
    await engine.dispose()
    print("🛑 Shutdown complete.")


# ── Application Factory ───────────────────────────────────────────────────────

def create_application() -> FastAPI:
    """
    Factory function that creates and configures the FastAPI application.

    WHY A FACTORY FUNCTION (not just `app = FastAPI()`)?
    - Testability: Tests can call create_application() to get a fresh app instance.
    - Clarity: All configuration is in one place.
    - Flexibility: Could accept config overrides for testing.
    """

    application = FastAPI(
        title=settings.APP_NAME,
        # Shown in the Swagger UI header at /docs.

        version="1.0.0",
        # API version shown in Swagger UI.

        description="""
        ## Multi-Tenant Document Intelligence API

        A secure B2B backend for uploading, organizing, and semantically
        searching enterprise documents with strict tenant isolation.

        ### Features
        - 🔐 JWT Authentication with role-based access control
        - 🏢 Multi-tenant company isolation
        - 📁 Hierarchical folder management
        - 📄 Document upload with async text extraction
        - 🔍 Keyword + semantic AI-powered search
        - 📋 Complete audit logging
        """,
        # Markdown description shown in Swagger UI.

        docs_url="/docs" if settings.DEBUG else None,
        # Only expose Swagger UI in development/debug mode.
        # In production: docs_url=None hides /docs completely.

        redoc_url="/redoc" if settings.DEBUG else None,
        # Same for ReDoc documentation.

        lifespan=lifespan,
        # Register our lifespan context manager.
        # FastAPI will call it on startup and shutdown.
    )

    # ── CORS Middleware ───────────────────────────────────────────────────────

    application.add_middleware(
        CORSMiddleware,
        # Register the CORS middleware.

        allow_origins=settings.ALLOWED_ORIGINS_LIST,
        # List of allowed frontend origins from .env.
        # PRODUCTION: ["https://your-frontend.com"] — never use ["*"].

        allow_credentials=True,
        # Allow cookies and Authorization headers to be included in requests.
        # Required for JWT Bearer token authentication.

        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        # Allowed HTTP methods. OPTIONS is needed for CORS preflight requests.

        allow_headers=["Authorization", "Content-Type", "Accept"],
        # Only allow specific headers — reduces attack surface.
    )

    # ── Register Routers ──────────────────────────────────────────────────────
    # Each router is added here as its feature branch is merged.
    # Uncomment each line when the corresponding feature branch is ready:

    application.include_router(auth_router)
    application.include_router(companies_router)
    application.include_router(folders_router)
    application.include_router(documents_router)
    # application.include_router(search_router)
    # application.include_router(audit_router)

    # ── Health Check ─────────────────────────────────────────────────────────

    @application.get("/health", tags=["Health"])
    async def health_check():
        """
        Simple health check endpoint.
        Used by Docker, Kubernetes, and load balancers to verify the app is alive.
        Returns 200 OK if the application is running.
        """
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "environment": settings.APP_ENV,
        }

    return application
    # Return the configured app instance.


# ── Create App Instance ───────────────────────────────────────────────────────

app = create_application()
# Call the factory to create the global app instance.
# uvicorn looks for this: uvicorn main:app --reload