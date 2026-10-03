from enum import StrEnum


class SourceKind(StrEnum):
    MANUAL = "MANUAL"
    SEED = "SEED"


class StakeholderRole(StrEnum):
    PRODUCT_OWNER = "PRODUCT_OWNER"
    TECH_LEAD = "TECH_LEAD"
    ARCHITECT = "ARCHITECT"
    DEVELOPER = "DEVELOPER"
    QA = "QA"
    SECURITY = "SECURITY"
    CLIENT = "CLIENT"
    PROJECT_MANAGER = "PROJECT_MANAGER"


class RequirementStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class DecisionStatus(StrEnum):
    DISCUSSION = "DISCUSSION"
    PROPOSAL = "PROPOSAL"
    PROVISIONAL = "PROVISIONAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONFIRMED = "CONFIRMED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class CommitmentStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class RiskStatus(StrEnum):
    OPEN = "OPEN"
    MITIGATED = "MITIGATED"
    CLOSED = "CLOSED"


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MilestoneStatus(StrEnum):
    PLANNED = "PLANNED"
    AT_RISK = "AT_RISK"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DependencyStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    BLOCKED = "BLOCKED"


class QuestionStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
