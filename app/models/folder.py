import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.company import Company


class Folder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "folders"

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    deleted_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    company: Mapped["Company"] = relationship(
        "Company", back_populates="folders"
    )
    children: Mapped[list["Folder"]] = relationship(
        "Folder",
        back_populates="parent",
        foreign_keys="[Folder.parent_id]",
        lazy="selectin",
    )
    parent: Mapped[Optional["Folder"]] = relationship(
        "Folder",
        back_populates="children",
        foreign_keys="[Folder.parent_id]",
        remote_side="[Folder.id]",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="folder",
        lazy="noload",
    )