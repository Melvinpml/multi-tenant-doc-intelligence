# app/db/base.py

# ── Imports ───────────────────────────────────────────────────────────────────

import uuid
# uuid: Python's built-in UUID library.
# UUIDs are better than integers for IDs in multi-tenant systems:
#   - Cannot be guessed (unlike sequential integers 1, 2, 3...)
#   - Globally unique across all tables and databases
#   - Safe to expose in URLs — no information leakage

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
# DeclarativeBase: The base class ALL ORM models inherit from.
#                  SQLAlchemy uses it to track all your table definitions.
# Mapped:          Type annotation wrapper — tells SQLAlchemy a field IS a column.
# mapped_column:   The actual column definition with constraints (PK, nullable, etc.)

from sqlalchemy import DateTime, func
# DateTime: Column type for timestamp fields.
# func:     Access to SQL functions — func.now() calls PostgreSQL's NOW() function.

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
# UUID:     PostgreSQL-specific UUID column type.
#           Stores UUIDs natively in PostgreSQL as 16-byte binary (efficient).
#           We alias it PG_UUID to avoid confusion with Python's uuid.UUID.


# ── Declarative Base ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    The parent class for ALL database models in this project.

    Every model (User, Company, Document, etc.) will:
        class User(Base):
            __tablename__ = "users"
            ...

    SQLAlchemy scans all subclasses of Base to know which tables exist.
    Alembic uses Base.metadata to detect schema changes and auto-generate migrations.
    """
    pass
    # No fields here — Base is just a registry.
    # Actual shared columns (id, created_at) are defined in TimestampMixin below.


# ── Mixin: Shared Columns ─────────────────────────────────────────────────────

class UUIDPrimaryKeyMixin:
    """
    Mixin that adds a UUID primary key to any model.

    WHAT IS A MIXIN?
    A mixin is a class you inherit from to add reusable fields/methods.
    It is NOT a database table itself — it just contributes columns.

    USAGE:
        class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
            __tablename__ = "users"
            # Automatically gets: id, created_at, updated_at
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        # PG_UUID(as_uuid=True): Store as PostgreSQL UUID type.
        #                        as_uuid=True means Python gets a uuid.UUID object
        #                        (not a plain string).

        primary_key=True,
        # Marks this column as the PRIMARY KEY — enforces uniqueness + creates index.

        default=uuid.uuid4,
        # uuid.uuid4: Python function that generates a random UUID.
        # default=uuid.uuid4 (NOT uuid.uuid4()) means:
        #   - uuid.uuid4   → SQLAlchemy calls this function each time a row is created
        #   - uuid.uuid4() → Would generate ONE uuid at class definition time (wrong!)
    )


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at columns to any model.
    These timestamps are set automatically by the database — no manual work needed.
    """

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        # timezone=True: Stores timestamp WITH timezone (TIMESTAMPTZ in PostgreSQL).
        # Always use timezone-aware timestamps — avoids DST bugs.

        server_default=func.now(),
        # server_default: The DEFAULT value is set by the DATABASE SERVER, not Python.
        # func.now(): Calls PostgreSQL's NOW() function → current timestamp.
        # This runs even if Python doesn't set the value explicitly.

        nullable=False,
        # Cannot be NULL — every row must have a creation time.
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        # Set to NOW() on first insert.

        onupdate=func.now(),
        # onupdate: Automatically calls func.now() whenever this ROW is UPDATED.
        # You never need to manually set updated_at — SQLAlchemy handles it.

        nullable=False,
    )