# Data model and migration stages

Status: Phase 0 design. See [architecture](proposed-architecture.md).

## Common conventions

IDs are UUIDs; timestamps are PostgreSQL `timestamptz` in UTC; milestone/due dates
are calendar dates. Every project entity has `project_id`, `id`, a composite unique
key `(project_id, id)`, `created_at`, and `updated_at`. Canonical objects also have
`title`, `description`, `version >= 1`, `source_kind` (`MANUAL` or `SEED` initially),
and `source_label`. Titles cannot be blank. Statuses use named check constraints
and Python enums rather than hard-to-evolve PostgreSQL enum types.

Repository operations require project ID even though UUIDs are globally unique.
Composite foreign keys enforce that referenced owners, dependencies and decisions
belong to the same project. The API later verifies actor membership as well.

## Initial schema (Step 0.3c)

| Entity | Additional fields and invariants |
| --- | --- |
| User | Display name; unique normalized email |
| Project | Name, description; no globally unique name requirement |
| ProjectMember | Project, user, primary stakeholder role; unique `(project_id, user_id)` |
| Requirement | `status` (`DRAFT`, `ACTIVE`, `COMPLETED`, `ARCHIVED`), positive integer `phase` |
| Decision | `decision_status`, `impact_area`, optional `made_by`, optional `supersedes_decision_id`, `confirmed_at` |
| Commitment | `status` (`OPEN`, `IN_PROGRESS`, `DONE`, `CANCELLED`), optional `said_by`, `owner_id`, `due_date`, `dependency_id`, `confidence` in [0,1] |
| Risk | `status` (`OPEN`, `MITIGATED`, `CLOSED`), severity (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) |
| Milestone | Date; `status` (`PLANNED`, `AT_RISK`, `COMPLETED`, `CANCELLED`) |
| Dependency | `status` (`PENDING`, `READY`, `BLOCKED`), optional owner and blocked milestone |
| OpenQuestion | `status` (`OPEN`, `RESOLVED`, `CLOSED`), optional owner |
| AuditEvent | Project, optional human actor, action, entity type/ID, structured non-secret payload, timestamp |

Membership roles initially support `PRODUCT_OWNER`, `TECH_LEAD`, `ARCHITECT`,
`DEVELOPER`, `QA`, `SECURITY`, `CLIENT`, and `PROJECT_MANAGER`. Each member has one
primary role in this foundation. Multiple role assignments can be a later migration
if governance requires them; do not claim enterprise RBAC.

Decision statuses are exactly `DISCUSSION`, `PROPOSAL`, `PROVISIONAL`,
`REVIEW_REQUIRED`, `CONFIRMED`, `SUPERSEDED`, `REJECTED`. Only confirmed decisions
are current canonical decision truth; provisional records remain visible proposals.
Confirmed/superseded decisions require a confirmation timestamp. Supersession
references stay in-project and cannot point to themselves. A future governance
service checks authority, transition legality and cycles; the database status check
alone does not implement that workflow.

Optional ownership means unresolved ownership, not a guessed owner. Commitment
speaker and owner are distinct. Future transcript IDs are added with real foreign
keys in Phase 3/5, not fabricated seed evidence. Risks gain affected-entity links
when an actual detector/workflow needs them.

Project deletion can cascade project-owned data, but user deletion is restricted
while memberships/audit references exist. Audit events are append-only through
the application repository interface; production tamper-proof audit controls are
outside the local prototype. Do not expose hard project deletion in this phase.

## Migration sequence

1. `0001_vector`: enable pgvector; owned extension rollback is explicitly tested in
   disposable databases. Refuse to commandeer an already-enabled extension.
2. `0002_canonical`: create the initial relational schema, constraints and indexes.
   Downgrade removes only these tables, in dependency order.
3. Phase 2: add documents/chunks, content hashes and embeddings with model metadata.
4. Phase 3: add meetings, participants and immutable utterances.
5. Phases 5–8: add candidate events, evidence associations, deltas, reviews and conflicts.
6. Integration phase: add connection metadata and explicitly confirmed action records.

Each migration is explicit; do not use runtime `create_all` as schema management.
Tests compare SQLAlchemy metadata with migrated schema to detect drift. New
requirements trigger small migrations rather than putting the entire MVP into
the first revision.

## Evidence and candidate relationships (later phases)

`Meeting` owns ordered `Utterance` records and participants; participant speaker
identities may be unresolved. `ProjectDocument` owns chunks with source page/section,
raw text, content hash and embedding metadata. Both remain source evidence.

`ProjectEventCandidate` records a typed interpretation, processing run, confidence,
proposed values, review status and exact evidence associations. Association rows
have project-scoped foreign keys. `ProjectDelta` records target type/ID/version,
previous and proposed values. `Conflict` links the conflicting candidate/decision
evidence and explanation. `ReviewRequest` records required roles and human outcomes.

Canonical writes link back to the applied candidate and source evidence. Candidate
application is unique and transactional with the canonical update and audit event.
Rejection changes only candidate/review records. Evidence is never silently replaced
by the model's interpretation.

## Seed baseline

Use stable UUIDs for one `Client Portal Modernization` project and its stakeholders.
Seed Phase 2 SSO, 24 November 2026 launch, PostgreSQL, pending production credentials
(John owns the commitment), pending security review, synchronous CSV export, and
three payment retries. Sarah is the product owner, John the tech lead, with QA and
architecture stakeholders for the later demo. All provenance is `SEED`.

The seed inserts missing stable IDs, commits atomically, and does not reset edited
records. A repeated run creates no duplicate project, users, memberships or objects.
No candidate, conflict or transcript is seeded as if its detector had run.
