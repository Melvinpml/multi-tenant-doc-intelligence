# alembic/env.py
# This file configures HOW Alembic connects to the database and detects changes.

# ── Imports ───────────────────────────────────────────────────────────────────

import asyncio
# asyncio: Python's async/await runtime.
# Alembic is synchronous, but our engine is async.
# asyncio.run() lets us bridge the gap.

from logging.config import fileConfig
# fileConfig: Reads the logging configuration from alembic.ini.

from sqlalchemy import pool
# pool: SQLAlchemy's connection pool module.
# NullPool is used during migrations — we don't want pooling during schema changes.

from sqlalchemy.ext.asyncio import create_async_engine
# We need to create an async engine here too, because our models use async.

from alembic import context
# context: Alembic's global context — gives access to config, metadata, etc.

# ── Import ALL models here so Alembic can detect them ─────────────────────────

from app.db.base import Base
# Base.metadata contains all table definitions.
# Alembic compares Base.metadata against the live DB to detect what changed.

# Import every model so SQLAlchemy registers them in Base.metadata:
# (These imports are added as each model file is created)
# from app.models.user import User
# from app.models.company import Company, CompanyMember
# from app.models.folder import Folder
# from app.models.document import Document
# from app.models.document_chunk import DocumentChunk
# from app.models.audit_log import AuditLog

from app.core.config import settings
# Import settings to get the database URL from .env


# ── Alembic Config ────────────────────────────────────────────────────────────

config = context.config
# config: The Alembic config object (reads from alembic.ini).

if config.config_file_name is not None:
    fileConfig(config.config_file_name)
    # Apply the logging config from alembic.ini.
    # The `if` guard prevents errors when env.py is imported without a config file.

target_metadata = Base.metadata
# target_metadata: Tells Alembic which metadata to compare against the DB.
# Base.metadata knows about ALL tables because we imported all model files above.


# ── Async Migration Runner ────────────────────────────────────────────────────

def do_run_migrations(connection):
    """
    Runs migrations synchronously given an open DB connection.
    Called from run_async_migrations() below.
    """
    context.configure(
        connection=connection,
        # The open database connection to run SQL against.

        target_metadata=target_metadata,
        # The metadata Alembic compares against to detect schema diffs.

        compare_type=True,
        # Detect column TYPE changes (e.g., VARCHAR(100) → VARCHAR(255)).
        # Without this, Alembic ignores type changes.

        compare_server_default=True,
        # Detect changes to column DEFAULT values.
    )

    with context.begin_transaction():
        # Begin a database transaction.
        # All migration SQL runs inside this transaction.
        # If any SQL fails, the entire transaction rolls back — safe.

        context.run_migrations()
        # Execute the actual migration SQL statements.


async def run_async_migrations():
    """
    Creates an async engine and runs migrations.
    We use NullPool because migrations should NOT use connection pooling —
    each migration run opens fresh connections and closes them cleanly.
    """

    async_engine = create_async_engine(
        settings.DATABASE_URL,
        # Use the async DATABASE_URL from .env.

        poolclass=pool.NullPool,
        # NullPool: Disables connection pooling.
        # For migrations, we want: connect → run SQL → disconnect.
        # A pool would keep connections open, which can cause issues
        # during schema changes (e.g., locking tables).
    )

    async with async_engine.connect() as connection:
        # Open a single async connection to the database.

        await connection.run_sync(do_run_migrations)
        # run_sync: Runs a SYNCHRONOUS function inside an ASYNC connection.
        # This is the bridge — Alembic's migration runner is sync,
        # but our connection is async. run_sync handles this translation.

    await async_engine.dispose()
    # Close the engine and all connections after migrations complete.


def run_migrations_online():
    """
    Entry point called by Alembic when running: alembic upgrade head
    'Online' means: connect to the real database and run migrations.
    """
    asyncio.run(run_async_migrations())
    # asyncio.run(): Runs the async function synchronously.
    # This is how we bridge Alembic (sync) with our async engine.


run_migrations_online()
# Call immediately when Alembic imports this file.