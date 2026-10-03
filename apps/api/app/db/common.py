from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Constraint

from app.domain.statuses import SourceKind


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProjectOwned(Timestamped):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )


class CanonicalRecord(ProjectOwned):
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(default="", server_default="")
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    source_kind: Mapped[str] = mapped_column(
        String(20), default=SourceKind.MANUAL, server_default=SourceKind.MANUAL.value
    )
    source_label: Mapped[str] = mapped_column(default="", server_default="")


def enum_check(column: str, enum_type: type[StrEnum]) -> CheckConstraint:
    values = ", ".join(repr(item.value) for item in enum_type)
    return CheckConstraint(f"{column} IN ({values})", name=f"{column}_values")


def canonical_constraints(*extra: Constraint) -> tuple[Constraint, ...]:
    return (
        UniqueConstraint("project_id", "id"),
        CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        CheckConstraint("version >= 1", name="version_positive"),
        enum_check("source_kind", SourceKind),
        *extra,
    )
