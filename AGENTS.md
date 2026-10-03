# ProjectPulse working agreement

Build incrementally: Phase → Feature → Step → Tests → Documentation → Checkpoint.
Do not implement the next major phase until the user authorizes continuing.

## Branches and checkpoints

- Use `phase/<number>-<phase-name>` for each phase, starting from the current `main`.
  Phase 1 uses `phase/1-project-workspace-ui`.
- After EACH step, finish implementation, relevant tests, documentation, acceptance
  criteria and regression review. Commit and push that checkpoint to the phase's
  branch before starting the next step. Report the push and check results.
- Keep incomplete phases off `main`.
- After ALL phase steps are complete, run feature-wide E2E tests and required
  build/static checks, update the phase completion report, push the final checkpoint,
  then merge the phase branch into `main` through a pull request where possible.
- The user has authorized these checkpoint pushes and completed-phase merges;
  do not request permission again for this workflow. Respect branch protections
  and investigate failed required checks before merging. Never force-push `main`.
- Stop and report after the completed-phase merge. Keep the phase branch for history.

## Product boundaries

The product name is ProjectPulse. It is a browser-based web application built with
Next.js, FastAPI and PostgreSQL. A Windows executable/native desktop application
is outside the current hackathon scope.

Preserve existing seed identities, canonical records and local database volumes
when updating names or configuration. Never commit `.env`, credentials or build
output. AI interpretations must remain separate from confirmed project state.
