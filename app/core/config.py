# app/core/config.py

# ── Imports ───────────────────────────────────────────────────────────────────

from pydantic_settings import BaseSettings, SettingsConfigDict
# BaseSettings: Special Pydantic class that reads values from environment
#               variables and .env files automatically.
# SettingsConfigDict: Lets us configure HOW BaseSettings reads the .env file.

from functools import lru_cache
# lru_cache: A decorator that memoizes (caches) the result of a function.
#            We use it so Settings() is only created ONCE, not on every request.

from typing import List
# List: Type hint for Python lists — used to type ALLOWED_ORIGINS


# ── Settings Class ────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    """
    Central configuration object.
    All values are loaded from environment variables or the .env file.
    Pydantic validates each value's type automatically.
    If a required variable is missing, the app FAILS TO START — intentional.
    """

    # ── Application ──────────────────────────────────────────────────────────

    APP_NAME: str = "Multi-Tenant Doc Intelligence API"
    # str: Python's string type.
    # Default value provided — app won't crash if this is missing from .env.

    APP_ENV: str = "development"
    # Tracks which environment we're in: "development", "staging", "production"
    # Used to toggle debug features and logging levels.

    DEBUG: bool = False
    # bool: True or False.
    # Controls FastAPI debug mode. Always False in production — never expose tracebacks.

    SECRET_KEY: str
    # No default — REQUIRED. App refuses to start if SECRET_KEY is not in .env.
    # Used as a general app secret (not the JWT secret — those are separate).


    # ── Database ─────────────────────────────────────────────────────────────

    DATABASE_URL: str
    # REQUIRED. Full async connection string.
    # Example: "postgresql+asyncpg://user:pass@localhost:5432/dbname"
    # The "+asyncpg" tells SQLAlchemy to use the async driver.

    SYNC_DATABASE_URL: str
    # REQUIRED. Same DB but sync driver for Alembic.
    # Example: "postgresql+psycopg2://user:pass@localhost:5432/dbname"


    # ── JWT ──────────────────────────────────────────────────────────────────

    JWT_SECRET_KEY: str
    # REQUIRED. The key used to SIGN and VERIFY JWT tokens.
    # If someone gets this key, they can forge tokens → keep it secret.

    JWT_ALGORITHM: str = "HS256"
    # HS256: HMAC-SHA256 — a symmetric signing algorithm.
    # Both signing and verification use the same JWT_SECRET_KEY.

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # int: Integer type.
    # Tokens expire after 30 minutes — forces re-authentication.
    # Lower = more secure but worse UX. 30 minutes is industry standard.


    # ── Redis ────────────────────────────────────────────────────────────────

    REDIS_URL: str = "redis://localhost:6379/0"
    # Connection string for Redis.
    # /0 means database 0 (Redis has 16 databases 0-15 by default).
    # Used by: Celery (task broker), fastapi-limiter (rate limiting),
    #          JWT blocklist (logout invalidation).


    # ── File Upload ──────────────────────────────────────────────────────────

    MAX_FILE_SIZE_MB: int = 50
    # Maximum file size in megabytes.
    # Used to return 413 Payload Too Large before processing begins.

    UPLOAD_DIR: str = "./uploads"
    # Directory on disk where uploaded files are stored.
    # Production note: Replace with S3 bucket path or pre-signed URL approach.

    ALLOWED_EXTENSIONS: str = "pdf,docx,txt,md"
    # Comma-separated string of allowed file extensions.
    # We keep this as a string (not List) for simple .env compatibility.

    @property
    def ALLOWED_EXTENSIONS_LIST(self) -> List[str]:
        # @property: Makes this behave like an attribute, not a method.
        # Splits the comma-separated string into a Python list.
        # Usage: settings.ALLOWED_EXTENSIONS_LIST → ["pdf", "docx", "txt", "md"]
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]
        # .split(",") → ["pdf", "docx", "txt", "md"]
        # .strip()    → removes any accidental spaces
        # .lower()    → normalizes to lowercase so "PDF" == "pdf"


    # ── AI Provider ──────────────────────────────────────────────────────────

    AI_PROVIDER_API_KEY: str
    # REQUIRED. API key for Gemini (or another AI provider).
    # Used by Celery worker to generate text embeddings.

    AI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    # Which embedding model to call on the AI provider.

    AI_EMBEDDING_DIMENSION: int = 768
    # The size of vectors produced by the embedding model.
    # Must match the VECTOR(768) column in the database schema.


    # ── CORS ─────────────────────────────────────────────────────────────────

    ALLOWED_ORIGINS: str = "http://localhost:3000"
    # Comma-separated list of allowed frontend origins.
    # PRODUCTION: Must be your exact frontend domain — never use "*".

    @property
    def ALLOWED_ORIGINS_LIST(self) -> List[str]:
        # Splits ALLOWED_ORIGINS string into a list for FastAPI's CORSMiddleware.
        # Usage: settings.ALLOWED_ORIGINS_LIST → ["http://localhost:3000"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


    # ── Pydantic Settings Configuration ──────────────────────────────────────

    model_config = SettingsConfigDict(
        env_file=".env",
        # Tells Pydantic to look for a file named ".env" in the project root.

        env_file_encoding="utf-8",
        # Encoding used to read the .env file.

        case_sensitive=False,
        # Makes variable names case-insensitive.
        # So DATABASE_URL and database_url both work.

        extra="ignore",
        # If .env has variables not defined in Settings, ignore them silently.
        # Prevents crashes from leftover variables.
    )


# ── Singleton Factory ─────────────────────────────────────────────────────────

@lru_cache()
def get_settings() -> Settings:
    """
    Returns the singleton Settings instance.

    WHY lru_cache?
      Without it: Settings() is called on every request → re-reads .env → slow.
      With it:    Settings() is called ONCE on first request → cached forever.

    HOW TO USE in other files:
      from app.core.config import get_settings
      settings = get_settings()
      print(settings.DATABASE_URL)
    """
    return Settings()


# ── Module-level shortcut ─────────────────────────────────────────────────────

settings = get_settings()
# Creates the instance at import time.
# Other modules can do: from app.core.config import settings
# This is identical to calling get_settings() — same cached object.
