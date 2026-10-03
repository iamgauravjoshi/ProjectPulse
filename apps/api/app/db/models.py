"""Explicit model registration for Alembic and repository consumers."""

from app.db.audit import AuditEvent
from app.db.decisions import Decision
from app.db.documents import Document
from app.db.identity import Project, ProjectMember, User
from app.db.state import Milestone, Requirement, Risk
from app.db.work import Commitment, Dependency, OpenQuestion

__all__ = [
    "AuditEvent",
    "Document",
    "Decision",
    "Project",
    "ProjectMember",
    "User",
    "Milestone",
    "Requirement",
    "Risk",
    "Commitment",
    "Dependency",
    "OpenQuestion",
]
