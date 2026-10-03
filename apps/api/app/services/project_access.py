from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project, ProjectMember
from app.domain.demo_identity import demo_id
from app.domain.errors import ProjectNotFound

# Local prototype identity; never accept an actor ID supplied by the browser.
LOCAL_DEMO_ACTOR_ID = demo_id("sarah")


def require_project_access(session: Session, project_id: UUID) -> None:
    if (
        session.scalar(
            select(Project.id)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(Project.id == project_id, ProjectMember.user_id == LOCAL_DEMO_ACTOR_ID)
        )
        is None
    ):
        raise ProjectNotFound
