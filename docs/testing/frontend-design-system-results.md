# Frontend design system checkpoint

## Scope

Added `apps/web/DESIGN.md` as the project-specific frontend guide and linked it
from the repository README. Adapted the supplied Kraken reference to the existing
ProjectPulse Next.js/Tailwind/Radix architecture and compact workspace layout.

Centralized the purple/cool-gray palette, positive/warning/neutral/error colors,
font roles and elevation tokens in `globals.css`. Updated shared actions to 12px
corners with 44px targets, responsive project headings, status badges, dialog/menu
shadows, error text and favicon. Improved the state editor's narrow-screen selector.
The system font stack remains local because proprietary Kraken fonts are not
provided. Status classifications and all data/API contracts remain unchanged.

## Validation

| Check                                     | Result                                                                                                                                                      |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `npm run lint`                            | Passed                                                                                                                                                      |
| `npm run typecheck`                       | Passed                                                                                                                                                      |
| `npm run format:check`                    | Passed                                                                                                                                                      |
| `npm test`                                | Passed: 37 tests in 5 files                                                                                                                                 |
| `npm run build -- --webpack`              | Passed: optimized production build                                                                                                                          |
| `npm run build` (Turbopack)               | Environment blocked: CSS worker loopback binding returns `Operation not permitted`, including permission retry                                              |
| Browser review against production Next.js | Passed: all 9 workspace views at 375, 425, 768, 1024, 1280 and 1536px (54 combinations)                                                                     |
| Browser interaction checks                | Passed: record dialog boundaries, Escape/focus restoration, mobile drawer, desktop help dialog, 44px/12px primary button styling and no horizontal overflow |
| Visual inspection                         | Reviewed overview screenshots at 375px and 1280px                                                                                                           |
| `git diff --check`                        | Passed                                                                                                                                                      |

Browser validation used the existing synthetic `tests/fixtures/workspace.json`
with intercepted workspace API responses and an empty document library. It ran
against the webpack production build using system Chromium. The temporary review
script and screenshots live under `/tmp` and are not committed. The review did not
submit mutations. Full database-backed Playwright coverage was not run; the seeded
PostgreSQL/FastAPI test setup was not provisioned for this styling checkpoint.

## Acceptance and regression review

- Frontend guide documents the real architecture, token values, typography,
  components, responsive behavior, accessibility and agent conventions.
- Implemented shared visual rules agree with the guide and preserve existing
  navigation, business logic, record classification and explicit-save semantics.
- Existing unit/static checks and production compilation pass with the documented
  environment workaround. Mobile and desktop layouts were inspected in Chromium.
- No dependency, schema, credential, canonical record or database volume changes.

This is a Phase 2 frontend refinement; it does not start the next product phase.
