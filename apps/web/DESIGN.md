# ProjectPulse Frontend Design System

## 1. Visual Theme & Atmosphere

ProjectPulse is a browser-based project intelligence workspace. Meetings and
uploaded documents are evidence; human-confirmed project state is the baseline.
The interface should feel calm, trustworthy and easy to scan during daily work.

Inspired by the supplied Kraken reference, use purple for actions and navigation,
white for working surfaces, near-black for primary text and cool gray for metadata.
Keep the existing compact dashboard density rather than applying marketing-sized
headings to every record. Green indicates confirmed or completed state; amber
signals a pending review and red highlights risk, blocking or failure. Always accompany status colors with readable labels.

**Key characteristics:**

- Purple `#7132f5` for primary actions, brand identity and selected navigation.
- White panels on a very light canvas, divided by quiet borders.
- Bold display headings; compact, readable UI and record text.
- 12px button radius, 8px input radius and 6px status badge radius.
- Subtle elevation for dialogs; micro elevation for the project selector menu.
- Filled and outlined status chips share a semantic color scheme across every view.
- Canonical state, source evidence and search results remain clearly identified.

## 2. Architecture & Source of Truth

The frontend directory is `apps/web`. It uses Next.js 16 App Router, React 19,
TypeScript, Tailwind CSS v4, Radix Dialog/Select and Lucide icons.

| Location                                | Responsibility                                                                                     |
| --------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `src/app/globals.css`                   | Tailwind `@theme` tokens, base styles and shared component classes                                 |
| `src/app/layout.tsx`                    | Root document, metadata and global stylesheet loading                                              |
| `src/app/icon.svg`                      | Brand favicon; match its fill to the accent token                                                  |
| `src/components/ui/`                    | Project-owned shadcn-style Button, Badge, Card, Field, inputs, feedback and Radix overlay wrappers |
| `src/features/workspace/status.ts`      | Shared status-to-color presentation map                                                            |
| `src/lib/utils.ts`                      | `cn()` class composition with clsx and tailwind-merge                                              |
| `src/components/workspace/`             | Shell, project header/selector, panels, badges, records and feedback                               |
| `src/components/memory/`                | State editor, record dialogs, document library and context search                                  |
| `src/features/workspace/`               | Typed workspace data, navigation, presentation and attention logic                                 |
| `src/features/memory/`                  | Form validation, document/search contracts and API clients                                         |
| `src/app/api/workspace/` and `src/lib/` | Same-origin server proxies to FastAPI                                                              |
| `tests/unit/` and `tests/e2e/`          | Existing behavior, keyboard, loading and responsive coverage                                       |

Use semantic Tailwind utilities generated from `@theme`, such as `bg-accent`,
`text-muted` and `border-line`. Change a shared rule in the stylesheet or shared
component first. Keep business rules and status classification in their existing
TypeScript modules. The design system does not change API or database contracts.

## 3. Color Palette & Roles

| Role / token                   | Value                                | Usage                                                          |
| ------------------------------ | ------------------------------------ | -------------------------------------------------------------- |
| `accent`                       | `#7132f5`                            | Primary button, brand mark, focus outline, selected navigation |
| `accent-dark`                  | `#5741d8`                            | Reserved for outlined purple treatments                        |
| `accent-deep`                  | `#5b1ecf`                            | Primary button hover                                           |
| `accent-soft`                  | `rgba(133,91,251,0.16)`              | Selected navigation, avatars and informational notices         |
| `ink`                          | `#101114`                            | Primary text and overlay tint                                  |
| `muted`                        | `#686b82`                            | Descriptions, dates, labels and decorative icons               |
| `canvas`                       | `#faf9fc`                            | Workspace background                                           |
| `surface`                      | `#ffffff`                            | Panels, headers, sidebar, menus and dialogs                    |
| `surface-muted`                | `rgba(148,151,169,0.08)`             | Quiet hover and decorative backgrounds                         |
| `line`                         | `#dedee5`                            | Borders, dividers and skeletons                                |
| `success` / `success-soft`     | `#026b3f` / `rgba(20,158,97,0.16)`   | Positive status text / background                              |
| `warning` / `warning-soft`     | `#9a3412` / `#fff7ed`                | Attention status text / background                             |
| `danger`                       | `#b91c1c`                            | High risk, blocked/failed states and errors                    |
| `danger-soft` / `danger-hover` | `#fef2f2` / `#991b1b`                | Red chip/callout background / destructive button hover         |
| `neutral` / `neutral-soft`     | `#484b5e` / `rgba(104,107,130,0.12)` | Other status text / background                                 |

Use `muted` for small readable text. The reference's silver-blue `#9497a9` is used
only in the muted surface mixture; it is too light for small text on white.

## 4. Typography Rules

`font-display` and `font-ui` currently share a local system stack:
`ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`.
These separate tokens allow a future licensed display font without changing UI
components. Kraken's proprietary fonts are not bundled or requested remotely.

| Role                           | Utility / font         | Size | Weight    | Line height | Tracking |
| ------------------------------ | ---------------------- | ---- | --------- | ----------- | -------- |
| Project title, mobile          | `page-title` / display | 28px | 700       | 1.29        | -0.5px   |
| Project title, 640px+          | `page-title` / display | 36px | 700       | 1.22        | -0.5px   |
| Dialog heading                 | UI, `text-xl`          | 20px | 600       | 28px        | normal   |
| Feedback heading               | UI, `text-lg`          | 18px | 600       | 28px        | normal   |
| Panel / memory heading / body  | UI, `text-base`        | 16px | 600 / 400 | 24px        | normal   |
| Records / navigation / buttons | UI, `text-sm`          | 14px | 400–600   | 20px        | normal   |
| Metadata / status badge        | UI, `text-[13px]`      | 13px | 400–500   | inherited   | normal   |
| Supporting caption             | UI, `text-xs`          | 12px | 400       | 16px        | normal   |

Use `leading-6` for long record descriptions. Keep one `h1` for the project title
and meaningful `h2`/`h3` levels for sections and records. Wrap long titles and source
text rather than hiding information; breadcrumb text may truncate.

## 5. Component Stylings

### Buttons

Use the shared `Button` component instead of hand-styled HTML controls.

- **Default:** purple surface, white semibold 14px text, 16px horizontal and 10px
  vertical padding, minimum 44px height, 12px radius. Hover uses `accent-deep`.
- **Outline:** white surface, near-black medium text, `line` border and the same
  minimum height/radius. Hover uses `surface-muted`.
- **Secondary:** a subtle purple surface for supporting actions.
- **Ghost:** quiet navigation/help controls; **link** for text links.
- **Destructive:** red fill for a confirmed deletion. **Destructive outline:** red
  text and border for the initial delete action.
- `size="icon"` is a 44px square. `size="sm"` reduces horizontal padding while
  retaining a 44px target. Disabled controls use 50% opacity.
- Use `asChild` to style Next.js links; set `type="submit"` on form actions.
  Icons use `data-icon="inline-start"` / `"inline-end"` and the component owns sizing.

### Status Chips

`StatusBadge` delegates to `Badge` and the presentation map in
`src/features/workspace/status.ts`. API enums and business rules remain separate.

| Tone                 | States                                                                               |
| -------------------- | ------------------------------------------------------------------------------------ |
| **Green / success**  | ACTIVE, CONFIRMED, READY, DONE, COMPLETED, MITIGATED, RESOLVED, CLOSED, INDEXED, LOW |
| **Orange / warning** | PENDING, PROVISIONAL, REVIEW_REQUIRED, MEDIUM, NO_DUE_DATE, NOT_INDEXED              |
| **Red / danger**     | HIGH, CRITICAL, BLOCKED, AT_RISK, OVERDUE, FAILED, REJECTED                          |
| **Purple / info**    | OPEN, IN_PROGRESS, PLANNED, PROPOSAL, DISCUSSION                                     |
| **Gray / neutral**   | DRAFT, ARCHIVED, SUPERSEDED, CANCELLED, UNAVAILABLE and unknown values               |

Use `variant="filled"` for the main state and `variant="outline"` for secondary
severity or provenance. Both treatments retain the same text color. Chips have
6px corners, a 1px tonal border, 8px horizontal / 2px vertical padding and 13px
medium text. `humanLabel` converts enum values to readable labels.

Risk severity and risk lifecycle are separate chips: “High” is red even when its
lifecycle is “Open”. Low severity is green to signal its level; it does not imply
resolution. Green “Active” likewise describes activity, not AI approval. Document
index statuses use the same map and label their index context.

### Document Selection

`DocumentPicker` composes `Field` and `Button` with a dashed evidence drop area,
icon, keyboard-operable “Browse files” action and a visually hidden native file
input. Show the selected filename and size with change/remove controls. Dropping
or choosing a file only selects it; `Upload document` submits explicitly.

Accept one nonempty PDF, DOCX, TXT or Markdown file up to 5 MiB. Invalid selections
show an actionable alert and disable upload. Cancelling preserves a prior selection;
success clears it and failed upload retains it. Disable selection while an upload
or index action is pending. Keep browser file security and server validation intact.

### Panels, Forms & Overlays

- Panels use a white surface, 1px `line` border, 12px corners and no large shadow.
  `Panel` provides a heading row with 20px horizontal / 16px vertical padding.
- Forms use `FieldGroup`, `Field` and `FieldLabel`. Shared inputs, textareas and
  native selects use 8px corners, 44px minimum height and a `line` border. Search
  fields use `InputGroup` with an addon icon. Labels may be visually hidden but
  must remain accessible. Use `data-invalid` on fields and `aria-invalid` on controls.
- Shared Radix `DialogContent` handles portal/overlay stacking and uses 12px
  corners, white surfaces, `shadow-subtle` and `bg-ink/30`
  backdrops. Record and document dialogs scroll within `85dvh`.
- Dialog widths leave 16px on each viewport edge; record/help dialogs cap at
  `max-w-lg` (512px), document previews at `max-w-2xl` (672px).
- Use Radix focus trapping, Escape dismissal and focus restoration. Pending saves
  retain their existing dismissal protection.
- Lucide icons generally use 14–24px sizes outside shared controls. Hide decorative icons from assistive
  technology; label icon-only controls. Circular avatars are allowed.

## 6. Layout, Spacing & Elevation

Use Tailwind's existing 4px spacing scale. Common values are 4, 8, 12, 16, 20, 24,
28 and 32px. Keep 1px borders and small icon/avatar offsets where necessary.

The desktop shell has a fixed 240px sidebar and 72px top header. Workspace
content uses 20px mobile / 32px desktop padding. Statistics are two columns on
mobile and four from `sm`; overview content expands using its existing `xl` grid.

| Radius               | Usage                                              |
| -------------------- | -------------------------------------------------- |
| 6px (`rounded-md`)   | Badges, skeletons and menu options                 |
| 8px (`rounded-lg`)   | Inputs, navigation rows and small decorative tiles |
| 12px (`rounded-xl`)  | Buttons, panels and dialogs                        |
| 50% (`rounded-full`) | Avatars only                                       |

| Elevation token | Value                           | Usage         |
| --------------- | ------------------------------- | ------------- |
| `shadow-subtle` | `0 4px 24px rgba(0,0,0,0.03)`   | Dialogs       |
| `shadow-micro`  | `0 1px 4px rgba(16,24,40,0.04)` | Selector menu |

## 7. Responsive Behavior

Use the existing Tailwind defaults: `sm` 640px, `md` 768px, `lg` 1024px, `xl`
1280px and `2xl` 1536px. 375px and 425px are verification widths, not extra CSS
breakpoints.

Below 1024px, replace the fixed sidebar with the existing Radix navigation drawer.
Stack filters and project-header actions when space is limited. The state editor
record-type selector uses a full-width mobile row and an inline desktop layout.
Keep dialogs, long descriptions and toolbar actions within the viewport.

## 8. Accessibility & Product Guardrails

- Preserve the skip link and the 2px accent `:focus-visible` outline with 3px offset.
- Use a 44px target for shared action/icon buttons. Retain keyboard-operable Radix
  navigation and selects; never remove focus styles without an equivalent.
- Respect reduced motion; shared `Skeleton` uses `motion-reduce:animate-none`.
- Provide loading, empty and retry states. Announce mutation failures with
  `role="alert"` and successful changes through the existing status region.
- Pair every status color with text. Use readable muted text, not opacity to hide
  essential descriptions. Verify contrast for any new color pair.
- Keep search results and source documents distinct from confirmed state. Only an
  explicit human save changes canonical records; display audit/version context.

## 9. Do's and Don'ts

**Do:** reuse theme tokens, shared `Button`, `Panel`, `StatusBadge`, Field controls,
Radix wrappers and Lucide icons. Use `cn()` for conditional classes, `gap-*` for
stacks, shared `Alert`/`Empty`/`Skeleton` for feedback and `Separator` for dividers. Preserve compact record density and predictable spacing. Extend
this document when adding a new shared pattern.

**Don't:** add unrelated purples, pill buttons, heavy panel shadows, unlicensed
brand fonts or page-specific raw semantic colors. Extend the project-owned shadcn-style components in `src/components/ui` rather
than adding a competing component library. Do not imply AI interpretations
are confirmed state or add unsupported actions to the interface.

## 10. Agent Prompt Guide & Validation

Example prompts:

> Add a workspace panel using `Panel`, white surfaces and `border-line`. Use
> compact 14px record text, `text-muted` metadata and `StatusBadge` for state.

> Add a record action using `Button` with its default variant. Preserve the Radix dialog's keyboard
> behavior, mobile scrolling, pending state and explicit-save audit semantics.

> Add a workspace view in the existing features/components structure. Reuse
> semantic Tailwind tokens and navigation helpers; verify 375px and desktop layouts.

Run from `apps/web`: `npm run build`, `npm run lint`, `npm run typecheck`,
`npm run format:check` and `npm test`. Use the existing Playwright suite for
navigation, focus restoration, dialogs and desktop/mobile checks; its full setup
requires the seeded local PostgreSQL database and FastAPI dependencies. Do not
change canonical records or database volumes to validate cosmetic changes.

## 11. shadcn/ui Guidance

The UI follows the repository's [shadcn skill](../../.agents/skills/shadcn/SKILL.md):
semantic color variants, composable controls, Field-based forms and accessible
Radix overlays. Components are project-owned adaptations using the existing
Radix packages, not CLI-generated upstream files. The managed environment blocks
the registry host, so CLI registry installation was unavailable. Documentation
was read through the Firecrawl connector:

- [Button](https://ui.shadcn.com/docs/components/radix/button)
- [Badge](https://ui.shadcn.com/docs/components/radix/badge)
- [Field](https://ui.shadcn.com/docs/components/radix/field)
- [Input](https://ui.shadcn.com/docs/components/radix/input)
- [Dialog](https://ui.shadcn.com/docs/components/radix/dialog)

Retain ProjectPulse's 12px button radius and local fonts when applying future
shadcn presets. Review generated changes before replacing these local components.
