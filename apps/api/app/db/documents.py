from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.common import ProjectOwned


class Document(ProjectOwned, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        UniqueConstraint("project_id", "content_hash"),
        ForeignKeyConstraint(
            ["project_id", "uploaded_by"], ["project_members.project_id", "project_members.user_id"]
        ),
        CheckConstraint("byte_size > 0 AND byte_size <= 5242880", name="byte_size_bounds"),
    )
    filename: Mapped[str] = mapped_column(String(240))
    content_hash: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int]
    format: Mapped[str] = mapped_column(String(10))
    raw_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    segments: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    uploaded_by: Mapped[UUID]
