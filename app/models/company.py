import uuid
import enum
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.folder import Folder
    # from app.models.document import Document
    from app.models.user import User


class RoleEnum(str, enum.Enum):
    owner  = "owner"
    admin  = "admin"
    member = "member"
    viewer = "viewer"


class Company(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    members: Mapped[list["CompanyMember"]] = relationship(
        "CompanyMember", back_populates="company", lazy="selectin"
    )
    folders: Mapped[list["Folder"]] = relationship(
        "Folder", back_populates="company", lazy="noload"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="company", lazy="noload"
    )


class CompanyMember(Base, TimestampMixin):
    __tablename__ = "company_members"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[RoleEnum] = mapped_column(
        SAEnum(RoleEnum, name="roleenum"), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="memberships")
    company: Mapped["Company"] = relationship("Company", back_populates="members")