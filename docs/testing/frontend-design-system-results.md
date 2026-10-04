# Frontend design system completion

## Scope and acceptance

Applied `apps/web/DESIGN.md` throughout ProjectPulse's nine existing workspace
views. Shared project-owned components in `src/components/ui` now provide buttons,
filled/outlined badges, cards, Field-based forms, inputs, feedback, skeletons and
Radix dialog/select wrappers. Existing navigation, state contracts, canonical
records and explicit-save audit semantics remain intact.

- High/critical risks, blocked/at-risk/overdue states and failures use red chips.
- Pending/review states, medium severity and missing delivery dates use orange.
- Active, confirmed, ready, done, completed, indexed and resolved states use green.
- Informational states use purple; inactive/unavailable states use neutral gray.
- State editor, overview, lists, review inbox, document indexing and context facts
  share one presentation map, including separate lifecycle/severity chips.
- Destructive actions use red outlined controls and red confirmation buttons.
- Document selection uses a styled browse/drop area, selected filename/size,
  change/remove controls and an explicit upload action. Keyboard browsing,
  supported formats, nonempty/5 MiB limits, pending state and failure feedback
  remain accessible. Selection alone never uploads or changes project state.
- Shell, panels, dialogs, search, forms, loading and empty states follow the shared
  palette, typography, 12px action radius and responsive conventions. The sidebar
  can scroll on shorter screens.

The repository's shadcn skill and official Button/Badge/Field/Input/Dialog docs
informed the component composition. Registry CLI calls were blocked by the managed
network policy. Source components are local adaptations using the existing Radix
foundation, not claimed as generated upstream components. Added pinned Radix Slot,
clsx and tailwind-merge dependencies support composition and class merging.

## Validation

| Check                          | Result                                                                                                                   |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `npm run build`                | Passed: standard Turbopack optimized production build                                                                    |
| `npm run lint`                 | Passed                                                                                                                   |
| `npm run typecheck`            | Passed                                                                                                                   |
| `npm run format:check`         | Passed                                                                                                                   |
| `npm test`                     | Passed: 37 tests in 5 files                                                                                              |
| `npm audit --audit-level=high` | Passed: zero vulnerabilities                                                                                             |
| `npm run test:e2e`             | Passed: all 41 tests against production Next.js, FastAPI and isolated seeded PostgreSQL                                  |
| Responsive browser review      | Passed: all 9 views at 375, 425, 768, 1024, 1280 and 1536px (54 combinations), with no horizontal overflow               |
| Keyboard/dialog review         | Passed: record dialog boundaries, Escape and focus restoration, mobile drawer, desktop help and 44px/12px button styling |
| Visual review                  | Desktop/mobile overview and redesigned document selection; refreshed feature preview images                              |
| `git diff --check`             | Passed                                                                                                                   |

The browser suite covers real uploads in all four document formats, deduplication,
provenance, deletion, all six record create/edit/delete flows, stale drafts, context
search, project isolation, keyboard navigation, loading/retry states and responsive
behavior. New cases verify rendered semantic chip colors, keyboard file browsing,
selection removal, invalid files and drag selection without automatic submission.
Two existing assertions were updated to target chips replacing plain status text.

Tests used an isolated `projectpulse_ui_test` PostgreSQL database on port 54339 in
a dedicated container, migrated and explicitly seeded for this task. Existing data
and volumes were not used or modified. No live Gemini call was made; unconfigured
indexing remains truthfully represented and covered by regression tests.

A pre-existing deeply nested glob unit case timed out once while multiple browser
checks were consuming CPU; it passed when rerun without that concurrent load.
No timeout thresholds or unrelated implementation were changed.

All work remains a Phase 2 UI refinement; no new product phase, backend behavior,
schema, identity, credential or deployment changes were introduced. The branch is
`phase/2-frontend-design-system`; merge through a pull request after its CI checks
succeed, retaining the branch for history.
