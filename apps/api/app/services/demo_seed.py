from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    AuditEvent,
    Commitment,
    Decision,
    Dependency,
    Milestone,
    OpenQuestion,
    Project,
    ProjectMember,
    Requirement,
    Risk,
    User,
)
from app.domain.demo_identity import demo_id

DEMO_PROJECT_ID = demo_id("project")
BASELINE_TIME = datetime(2026, 10, 3, tzinfo=UTC)


def _ensure[Entity: Base](
    session: Session, model: type[Entity], label: str, **values: Any
) -> Entity:
    key = demo_id(label)
    existing = session.get(model, key)
    if existing is not None:
        if getattr(existing, "project_id", DEMO_PROJECT_ID) != DEMO_PROJECT_ID:
            raise ValueError("Demo seed ID belongs to another project")
        return existing
    entity = model(id=key, **values)
    session.add(entity)
    session.flush()
    return entity


def seed_demo(session: Session) -> UUID:
    """Insert missing demo records without resetting edits; caller owns transaction."""
    _ensure(
        session,
        Project,
        "project",
        name="Client Portal Modernization",
        description="Modernize the client portal while keeping project decisions traceable.",
    )
    for label, name, role in [
        ("sarah", "Sarah", "PRODUCT_OWNER"),
        ("john", "John", "TECH_LEAD"),
        ("alex", "Alex", "ARCHITECT"),
        ("maya", "Maya", "QA"),
    ]:
        _ensure(session, User, label, display_name=name, email=f"{label}@projectpulse.demo")
        _ensure(
            session,
            ProjectMember,
            f"member-{label}",
            project_id=DEMO_PROJECT_ID,
            user_id=demo_id(label),
            role=role,
        )

    provenance = {
        "project_id": DEMO_PROJECT_ID,
        "source_kind": "SEED",
        "source_label": "Human-established demo baseline",
    }
    _ensure(
        session,
        Requirement,
        "sso",
        **provenance,
        title="Single sign-on",
        description="SSO is planned for Phase 2.",
        phase=2,
        status="ACTIVE",
    )
    _ensure(
        session,
        Milestone,
        "launch",
        **provenance,
        title="Portal launch",
        milestone_date=date(2026, 11, 24),
        status="PLANNED",
    )
    for label, title, description, impact in [
        ("database", "Database", "Use PostgreSQL.", "Architecture"),
        ("csv-export", "CSV export", "CSV export remains synchronous.", "Architecture"),
        (
            "payment-retries",
            "Payment retry",
            "Retry failed payments three times.",
            "Product behaviour",
        ),
    ]:
        _ensure(
            session,
            Decision,
            label,
            **provenance,
            title=title,
            description=description,
            decision_status="CONFIRMED",
            made_by=demo_id("john"),
            confirmed_at=BASELINE_TIME,
            impact_area=impact,
        )
    _ensure(
        session,
        Dependency,
        "security-review",
        **provenance,
        title="Security review",
        description="Security approval is pending before launch.",
        status="PENDING",
        blocked_milestone_id=demo_id("launch"),
    )
    _ensure(
        session,
        Commitment,
        "credentials",
        **provenance,
        title="Production credentials",
        description="Production access is pending; no delivery date has been agreed.",
        owner_id=demo_id("john"),
        status="OPEN",
    )
    _ensure(
        session,
        Risk,
        "security-risk",
        **provenance,
        title="Pending security approval",
        description="Launch may be blocked until security review is completed.",
        severity="HIGH",
        status="OPEN",
    )
    _ensure(
        session,
        OpenQuestion,
        "security-question",
        **provenance,
        title="Who will own the security review?",
        status="OPEN",
    )
    _ensure(
        session,
        AuditEvent,
        "seed-audit",
        project_id=DEMO_PROJECT_ID,
        action="DEMO_SEEDED",
        entity_type="project",
        entity_id=DEMO_PROJECT_ID,
        payload={"source": "seed command", "baseline_version": 1},
    )
    return DEMO_PROJECT_ID
