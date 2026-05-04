# app/db/session.py

# ── Imports ───────────────────────────────────────────────────────────────────

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    # AsyncSession: The async version of SQLAlchemy's Session.
    # All database queries (.execute(), .commit(), .rollback()) are awaited.

    async_sessionmaker,
    # async_sessionmaker: Factory that creates AsyncSession instances.
    # Think of it like a "session template" — configured once, reused forever.

    create_async_engine,
    # create_async_engine: Creates the async database connection engine.
    # The engine manages the CONNECTION POOL — a set of reusable DB connections.
)

from app.core.config import settings
# Import our Settings singleton to get DATABASE_URL.


# ── Async Engine ──────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    # The connection string — tells SQLAlchemy WHERE the database is
    # and WHICH driver to use (asyncpg for PostgreSQL).

    echo=settings.DEBUG,
    # echo=True: Prints every SQL query to the console.
    # We only enable this in DEBUG mode (development).
    # NEVER enable in production — floods logs with SQL statements.

    pool_size=10,
    # CONNECTION POOL EXPLAINED:
    # Instead of opening a new DB connection per request (slow),
    # SQLAlchemy maintains a pool of REUSABLE connections.
    # pool_size=10 means: keep 10 connections open and ready at all times.

    max_overflow=20,
    # If all 10 pool connections are busy, allow up to 20 EXTRA connections.
    # Total max connections = pool_size + max_overflow = 30.
    # After the overflow connections are done, they are CLOSED (not returned to pool).

    pool_pre_ping=True,
    # Before using a connection from the pool, send a quick "ping" to PostgreSQL.
    # If the connection dropped (e.g., DB restarted), SQLAlchemy replaces it.
    # Without this, you get "connection closed" errors after DB restarts.

    pool_recycle=3600,
    # Recycle (replace) connections after 3600 seconds (1 hour).
    # Prevents issues with PostgreSQL's idle connection timeout.
)
# RESULT: `engine` is the single async engine used by the entire application.
# One engine per application — created once at startup.


# ── Session Factory ───────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    # Bind this session factory to our engine.
    # All sessions created by this factory will use the same connection pool.

    class_=AsyncSession,
    # The CLASS to instantiate — AsyncSession (not the default sync Session).

    expire_on_commit=False,
    # CRITICAL SETTING. Explained:
    # Default (expire_on_commit=True): After session.commit(), SQLAlchemy marks
    #   ALL objects as "expired". The next time you access any attribute,
    #   SQLAlchemy issues a new SELECT query to refresh the data.
    # With expire_on_commit=False: Objects keep their values after commit.
    #   This is essential for async code — we can't accidentally trigger
    #   a lazy-load query after the session is already closed.

    autocommit=False,
    # We control commits manually with: await session.commit()
    # autocommit=True would commit after every statement — dangerous.

    autoflush=False,
    # We control flushes (sending pending changes to DB) manually.
    # autoflush=True can cause unexpected DB writes mid-operation.
)
# RESULT: AsyncSessionLocal is a callable.
# async with AsyncSessionLocal() as session: → creates a session
# Sessions are like "units of work" — you group queries, then commit or rollback.