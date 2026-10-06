"""Explicit model registration for Alembic and repository consumers."""

from app.db.audit import AuditEvent
from app.db.chunks import DocumentChunk
from app.db.decisions import Decision
from app.db.deltas import DeltaComparisonRun, ProjectDelta
from app.db.documents import Document
from app.db.events import (
    EventCandidateEvidence,
    EventExtraction,
    ExtractedSegment,
    ProjectEventCandidate,
)
from app.db.identity import Project, ProjectMember, User
from app.db.meetings import Meeting, MeetingParticipant, Utterance
from app.db.relevance import RelevanceAnalysis, UtteranceRelevance
from app.db.state import Milestone, Requirement, Risk
from app.db.work import Commitment, Dependency, OpenQuestion

__all__ = [
    "DeltaComparisonRun",
    "ProjectDelta",
    "EventCandidateEvidence",
    "EventExtraction",
    "ExtractedSegment",
    "ProjectEventCandidate",
    "AuditEvent",
    "RelevanceAnalysis",
    "UtteranceRelevance",
    "Meeting",
    "MeetingParticipant",
    "Utterance",
    "Document",
    "DocumentChunk",
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
