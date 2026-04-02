# Dashboard UI Redesign — Implementation Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the internal dental pipeline dashboard to match the lavenderhealth.ai brand identity — dark narrow sidebar, warm off-white background, purple primary color, pastel bento stat cards, pill buttons.

**Reference:** lavenderhealth.ai internal app (screenshot 5 from brainstorm) and marketing site color palette.

**Tech Stack:** React 18, Tailwind CSS v4 (`@import "tailwindcss"` + `@theme {}`), React Router v6, Lucide React (for icons — replaces emojis)

---

## Design Tokens

All tokens live in `dashboard/src/index.css` inside `@theme {}`. Replace existing tokens entirely.

| Token | Value | Usage |
|---|---|---|
| `--color-bg` | `#f5f4f0` | Page background (warm off-white) |
| `--color-sidebar` | `#111118` | Sidebar background |
| `--color-sidebar-hover` | `#1e1e2a` | Sidebar item hover |
| `--color-primary` | `#7c4dbe` | Buttons, active nav, links |
| `--color-primary-hover` | `#6a3da8` | Button hover state |
| `--color-ink` | `#1a2744` | All headings, primary text |
| `--color-muted` | `#6b7280` | Secondary text, labels |
| `--color-surface` | `#ffffff` | Card backgrounds |
| `--color-subtle` | `#eceae4` | Dividers, input borders |
| `--color-card-lavender` | `#e8dff5` | Stat card — qualified/purple |
| `--color-card-blue` | `#c5d9f0` | Stat card — found/blue |
| `--color-card-orange` | `#f5c4a0` | Stat card — drafted/orange |
| `--color-card-green` | `#c5e8d5` | Stat card — enriched/green |
| `--color-success` | `#16a34a` | Success states |
| `--color-danger` | `#dc2626` | Error/danger states |
| `--font-family-sans` | `"Open Sans", system-ui, sans-serif` | All text |
| `--border-radius-card` | `16px` | Cards (increased from 12px) |
| `--border-radius-btn` | `999px` | Buttons — full pill |
| `--border-radius-badge` | `999px` | Status badges — full pill |
| `--shadow-card` | `0 1px 4px rgba(0,0,0,0.06)` | Resting card shadow |
| `--shadow-card-hover` | `0 4px 16px rgba(124,77,190,0.12)` | Hover card shadow |

---

## File-by-File Changes

### `dashboard/src/index.css`
- Replace entire `@theme {}` block with new tokens above.
- Change `body` background to `var(--color-bg)`.
- Keep `flag-highlight` class for review highlighting.
- Add `.stat-card-lavender`, `.stat-card-blue`, `.stat-card-orange`, `.stat-card-green` utility classes with respective background colors and the dark navy text `#1a2744`.

### `dashboard/src/components/Layout.jsx`
Major redesign:
- **Sidebar width**: 64px (icon-only, no labels visible by default).
- **Sidebar background**: `var(--color-sidebar)` — near-black `#111118`.
- **Logo area**: Top of sidebar — lavender flower SVG mark (inline, white/purple, 32×32). No text — it's icon-only.
- **Nav items**: Each nav item is a centered 44×44px clickable square with a Lucide icon (20px). No text labels.
  - Runs → `<Activity />` icon
  - Clinics → `<Building2 />` icon
  - Drafts → `<Mail />` icon
  - Settings → `<Settings />` icon
- **Active state**: Purple background pill `bg-primary` on the icon container, white icon.
- **Inactive state**: Gray icon (`#6b7280`), hover goes to `var(--color-sidebar-hover)` with white icon.
- **Tooltip**: Native `title` attribute on each nav item for accessibility (shows label on hover).
- **Main content area**: `bg-[#f5f4f0]` background, `flex-1`, `min-h-screen`, `overflow-y-auto`.
- **Content padding**: `p-8` (32px) on all sides.

### `dashboard/src/components/Card.jsx`
- Update border-radius to `var(--border-radius-card)` (16px).
- Add `variant` prop: `"default"` (white surface) | `"lavender"` | `"blue"` | `"orange"` | `"green"`.
- Colored variants use the stat-card background colors with no shadow, `text-ink` for all text.
- Default: white background, `var(--shadow-card)`, hover → `var(--shadow-card-hover)` with transition.

### `dashboard/src/components/Button.jsx`
- **Primary**: `bg-primary` purple fill, white text, pill radius (`border-radius-btn: 999px`), hover `bg-primary-hover`.
- **Secondary**: White background, `border border-subtle`, ink text, same pill radius.
- **Danger**: `bg-danger` red fill, white text.
- **Ghost**: No background, ink text, hover gets `bg-subtle`.
- Remove the current `rounded-btn` references; use `rounded-full` for all buttons.
- Padding: `sm` → `px-3 py-1.5 text-xs`, `md` → `px-5 py-2 text-sm`, `lg` → `px-7 py-3 text-base`.

### `dashboard/src/components/StatusBadge.jsx`
Revised color mapping using brand palette:
- `pending` → lavender bg (`#e8dff5`), ink text
- `running` → blue bg (`#c5d9f0`), ink text, with a pulsing dot indicator
- `completed` → green bg (`#c5e8d5`), ink text
- `failed` → red bg (`#fce8e8`), danger text
- `scraped` → subtle bg (`#eceae4`), muted text
- `filtered_out` → subtle bg, muted text, strikethrough style
- `qualified` → lavender bg, primary text
- `enriched` → blue bg, ink text
- `drafted` → orange bg (`#f5c4a0`), ink text
- `approved` → green bg, ink text
All badges: `rounded-full`, `px-2.5 py-0.5`, `text-xs font-semibold`.

### `dashboard/src/pages/RunsPage.jsx`
- **Page header**: Larger title (`text-3xl font-bold text-ink`), subtitle text in muted.
- **"New Run" button**: Primary purple pill button, top-right of header row.
- **Stat bento row** (new): Above the runs list, show aggregate stats across all completed runs in colored stat cards:
  - Total clinics found → blue card
  - Total qualified → lavender card
  - Total enriched → green card
  - Total drafted → orange card
  - Each card: big bold number (`text-4xl font-bold text-ink`), label below in muted.
- **Run cards**: Each run becomes a card (`variant="default"`). Replace the progress-bar component with a horizontal row of 4 mini stat chips (Found / Qualified / Enriched / Drafted), each with a small colored dot matching the card colors.
- **Status badge**: Use updated `StatusBadge`.
- **Empty state**: Centered message with an `<Activity />` icon and "No runs yet — trigger your first city scan" text.

### `dashboard/src/pages/ClinicsPage.jsx`
- **Filter bar**: Horizontal pill-toggle for status filter (replace dropdown with button group: All | Qualified | Enriched | Drafted | Filtered Out). Active pill: `bg-primary text-white`. Inactive: `bg-surface border border-subtle`.
- **City search**: Rounded input with search icon prefix.
- **Clinic cards**: Add a left accent border (4px) colored by status — purple for qualified, blue for enriched, orange for drafted, gray for others.
- **Insurance flag count**: Show as a small colored badge (lavender pill) on the card when `> 0`.
- **Rating**: Show star icon + number inline.

### `dashboard/src/pages/ClinicDetailPage.jsx`
- **Header**: Clinic name in `text-2xl font-bold text-ink`. Rating and total reviews as muted inline stats.
- **Flagged reviews section**: Title "Insurance Complaints" with a count badge in lavender.
- **Flagged review cards**: Left border accent in primary purple, card background white, LLM reasoning shown in a muted italic block below the review text.
- **Other reviews**: Collapsible section ("Show all reviews"), lighter styling.
- **Back button**: Ghost button with `<ArrowLeft />` icon.

### `dashboard/src/pages/DraftsPage.jsx`
- **Filter tabs**: Pill tab group (Draft / Approved / All) — same pill-toggle pattern as ClinicsPage filter.
- **Draft cards**: Subject line in `font-semibold text-ink`. Clinic name as muted subtitle. Approve button: primary purple pill. Edit: secondary. Export: ghost.
- **Email body preview**: Rendered in a slightly inset box (`bg-subtle rounded-xl p-4`).

### `dashboard/src/pages/SettingsPage.jsx`
- **Section headers**: `text-lg font-semibold text-ink` with a thin `border-b border-subtle` below.
- **Inputs**: `bg-surface border border-subtle rounded-xl px-4 py-2.5` — more pronounced rounded corners.
- **Save button**: Primary purple pill, full width of the form.
- **Scheduler cards**: Each scheduled job as a row card with remove button on right.

---

## Constraints
- Do NOT install any new npm packages beyond `lucide-react` (for icons).
- Do NOT change any API calls, React Query hooks, or data logic — pure visual changes only.
- Tailwind v4 syntax: use `@theme {}` in CSS, NOT `tailwind.config.js` for token changes.
- Keep all existing component prop interfaces — add props (like `variant`), never remove.
- The lavender flower SVG logo in the sidebar: use a simple inline SVG (a stylized "L" or flower shape in purple `#7c4dbe`), not an external image file.

---

## Self-Review Checklist
- [x] No TBDs or placeholders — all colors, sizes, and component specs are explicit.
- [x] Consistent use of new tokens across all components — no hardcoded old colors.
- [x] `lucide-react` is the only new dependency.
- [x] Tailwind v4 syntax confirmed — `@theme {}` not `tailwind.config.js`.
- [x] Pill radius (999px) used consistently on buttons and badges.
- [x] Sidebar is 64px icon-only — no layout breakage on any existing page.
- [x] All 5 pages and 5 components covered with explicit change descriptions.
