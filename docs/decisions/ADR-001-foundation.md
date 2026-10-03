# ADR-001: foundation stack and local prototype scope

Date: 3 October 2026. Status: accepted for Phase 0 implementation.

## Context

The repository is empty and the product has a 10–12 working day prototype budget.
It needs trusted relational state, evidence provenance, future document retrieval
and provider independence. No existing stack, authentication or persistence must
be preserved. Model keys are not configured. Docker daemon access has been verified
for forthcoming PostgreSQL integration checks.

## Decision

Use Next.js/React/TypeScript/Tailwind for presentation, one FastAPI/Python backend,
SQLAlchemy/Alembic, and PostgreSQL with pgvector. Lock npm and uv dependencies.
Use pytest for backend contracts and real-database integration checks, Playwright
for browser flows, and explicit lint/format/type commands.

Keep AI, embedding, transcript and task-provider dependencies behind typed adapters
when their phases implement them. Keep evidence, interpretations and canonical
state separate. Only manual/seed operations and later human confirmation can write
canonical state. A future confirmation transaction must validate actor/review
authority and entity version and append audit history.

Phase 0 runs locally. A fixed server-side demo actor is only a development mechanism,
not production authentication. Bind application/database services to localhost,
store secrets on the backend, and do not deploy the unauthenticated prototype to
a public audience. Real identity and membership enforcement are required before
public access; complex enterprise administration is outside the MVP.

Initial migrations cover core canonical records and their project constraints.
Document, meeting, candidate and integration schemas arrive with their features.
The first seed is deterministic and preserves edits on repeat runs.

## Consequences

Two languages require separate toolchains but keep later document parsing simple.
API schemas are the frontend/backend boundary; generated TypeScript clients can
be introduced once business endpoints exist. No distributed infrastructure is
needed. Local identity limits hosting readiness and must remain visible in reports.
The foundation is testable without paid APIs or model calls.

## Alternatives considered

NestJS is a valid single-backend option but offers no existing-repository advantage
here. A Next.js-only backend would diverge from the preferred backend choices.
SQLite cannot validate PostgreSQL constraints/vector behavior. A dedicated vector
database, queues and microservices add avoidable hackathon setup.

Review this decision if the team commits to TypeScript-only development, public
multi-user deployment becomes required, or measured workload exceeds one backend.
