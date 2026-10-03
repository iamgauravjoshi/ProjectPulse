from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.common import ProjectOwned, Timestamped, enum_check
from app.domain.statuses import StakeholderRole


class User(Timestamped, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email = lower(email) AND length(trim(email)) > 0", name="normalized_email"
        ),
        CheckConstraint("length(trim(display_name)) > 0", name="display_name_not_blank"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    display_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), unique=True)


class Project(Timestamped, Base):
    __tablename__ = "projects"
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(default="", server_default="")


class ProjectMember(ProjectOwned, Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        UniqueConstraint("project_id", "user_id"),
        enum_check("role", StakeholderRole),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(30))
