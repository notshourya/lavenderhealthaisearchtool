# Dashboard UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the dental pipeline dashboard to match lavenderhealth.ai brand — dark icon-only sidebar, warm off-white background, purple primary, pill buttons/badges, pastel bento stat cards.

**Architecture:** Pure frontend visual changes only — no API, query hooks, or data logic touched. Each task rewrites one file completely. Tasks are independent and safe to apply in order.

**Tech Stack:** React 19, Tailwind CSS v4 (`@theme {}` in CSS), Lucide React (new dep, icons only), React Router v6, Vite.

---

## File Map

| File | Change |
|---|---|
| `dashboard/package.json` | Add `lucide-react` dependency |
| `dashboard/src/index.css` | Replace all design tokens, update body bg |
| `dashboard/src/components/Layout.jsx` | Dark 64px icon sidebar with Lucide icons |
| `dashboard/src/components/Card.jsx` | Add `variant` prop, update radius/shadow |
| `dashboard/src/components/Button.jsx` | Pill radius, updated variants/sizes |
| `dashboard/src/components/StatusBadge.jsx` | Brand color mapping, pill style |
| `dashboard/src/pages/RunsPage.jsx` | Bento stat cards, redesigned run cards |
| `dashboard/src/pages/ClinicsPage.jsx` | Pill filter tabs, accent borders on cards |
| `dashboard/src/pages/ClinicDetailPage.jsx` | Refreshed layout, lavender flag section |
| `dashboard/src/pages/DraftsPage.jsx` | Pill tab filter, refreshed draft cards |
| `dashboard/src/pages/SettingsPage.jsx` | Refined form styling |

---

## Task 1: Install lucide-react + update design tokens

**Files:**
- Modify: `dashboard/package.json`
- Modify: `dashboard/src/index.css`

- [ ] **Step 1: Install lucide-react**

Run from `dashboard/` directory:
```bash
cd dashboard && npm install lucide-react
```
Expected: `added 1 package` (or similar). `lucide-react` appears in `package.json` dependencies.

- [ ] **Step 2: Replace index.css with new design tokens**

Replace the entire contents of `dashboard/src/index.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600;700;800&display=swap');
@import "tailwindcss";

@theme {
  --color-bg: #f5f4f0;
  --color-sidebar: #111118;
  --color-sidebar-hover: #1e1e2a;
  --color-primary: #7c4dbe;
  --color-primary-hover: #6a3da8;
  --color-ink: #1a2744;
  --color-muted: #6b7280;
  --color-surface: #ffffff;
  --color-subtle: #eceae4;
  --color-card-lavender: #e8dff5;
  --color-card-blue: #c5d9f0;
  --color-card-orange: #f5c4a0;
  --color-card-green: #c5e8d5;
  --color-success: #16a34a;
  --color-danger: #dc2626;
  --font-family-sans: "Open Sans", system-ui, sans-serif;
  --border-radius-card: 16px;
  --border-radius-btn: 999px;
  --shadow-card: 0 1px 4px rgba(0,0,0,0.06);
  --shadow-card-hover: 0 4px 16px rgba(124,77,190,0.12);
}

* {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: "Open Sans", system-ui, sans-serif;
  background-color: #f5f4f0;
  color: #1a2744;
}

.flag-highlight {
  background: linear-gradient(120deg, rgba(124,77,190,0.15) 0%, rgba(124,77,190,0.15) 100%);
  border-bottom: 2px solid rgba(124,77,190,0.4);
  border-radius: 2px;
}
```

- [ ] **Step 3: Verify dev server starts without errors**

```bash
cd dashboard && npm run dev
```
Expected: Vite server starts, no compilation errors. Background should now be warm off-white `#f5f4f0` when you open the browser.

- [ ] **Step 4: Commit**

```bash
git add dashboard/package.json dashboard/package-lock.json dashboard/src/index.css
git commit -m "feat(ui): install lucide-react and update design tokens to lavenderhealth brand"
```

---

## Task 2: Redesign Layout.jsx — dark icon sidebar

**Files:**
- Modify: `dashboard/src/components/Layout.jsx`

- [ ] **Step 1: Replace Layout.jsx completely**

```jsx
import { NavLink } from 'react-router-dom'
import { Activity, Building2, Mail, Settings } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/runs',     label: 'Runs',     Icon: Activity  },
  { to: '/clinics',  label: 'Clinics',  Icon: Building2 },
  { to: '/drafts',   label: 'Drafts',   Icon: Mail      },
  { to: '/settings', label: 'Settings', Icon: Settings  },
]

function LavenderMark() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="16" r="16" fill="#7c4dbe" fillOpacity="0.2"/>
      <path d="M16 26V14" stroke="#7c4dbe" strokeWidth="1.8" strokeLinecap="round"/>
      <ellipse cx="16" cy="11" rx="2.5" ry="3.5" fill="#7c4dbe" opacity="0.9"/>
      <ellipse cx="12" cy="13" rx="2" ry="3" fill="#7c4dbe" opacity="0.6" transform="rotate(-20 12 13)"/>
      <ellipse cx="20" cy="13" rx="2" ry="3" fill="#7c4dbe" opacity="0.6" transform="rotate(20 20 13)"/>
    </svg>
  )
}

export default function Layout({ children }) {
  return (
    <div className="flex min-h-screen bg-bg">
      {/* Sidebar — 64px, dark, icon-only */}
      <aside className="w-16 bg-sidebar flex flex-col items-center py-5 gap-2 sticky top-0 h-screen shrink-0">
        {/* Logo mark */}
        <div className="mb-4">
          <LavenderMark />
        </div>

        {/* Nav items */}
        <nav className="flex flex-col items-center gap-1 w-full px-2">
          {NAV_ITEMS.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              title={label}
              className={({ isActive }) =>
                `w-10 h-10 flex items-center justify-center rounded-xl transition-all duration-150 ${
                  isActive
                    ? 'bg-primary text-white shadow-sm'
                    : 'text-muted hover:bg-sidebar-hover hover:text-white'
                }`
              }
            >
              <Icon size={20} strokeWidth={1.8} />
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-h-screen overflow-y-auto">
        <div className="max-w-6xl mx-auto px-8 py-8">
          {children}
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Verify in browser**

Open the dashboard. Expected:
- Left sidebar is dark (`#111118`), 64px wide, icon-only
- Lavender circle mark at top of sidebar
- Four nav icons (Activity, Building2, Mail, Settings) — gray when inactive, purple bg when active
- Content area is warm off-white, full width

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/Layout.jsx
git commit -m "feat(ui): dark 64px icon-only sidebar with Lucide icons and lavender mark"
```

---

## Task 3: Update base components — Card, Button, StatusBadge

**Files:**
- Modify: `dashboard/src/components/Card.jsx`
- Modify: `dashboard/src/components/Button.jsx`
- Modify: `dashboard/src/components/StatusBadge.jsx`

- [ ] **Step 1: Replace Card.jsx**

```jsx
const VARIANT_CLASSES = {
  default:  'bg-surface shadow-card hover:shadow-card-hover',
  lavender: 'bg-card-lavender',
  blue:     'bg-card-blue',
  orange:   'bg-card-orange',
  green:    'bg-card-green',
}

export default function Card({ children, className = '', variant = 'default', onClick }) {
  return (
    <div
      onClick={onClick}
      className={`rounded-card p-6 transition-shadow duration-200 ${VARIANT_CLASSES[variant]} ${onClick ? 'cursor-pointer' : ''} ${className}`}
    >
      {children}
    </div>
  )
}
```

- [ ] **Step 2: Replace Button.jsx**

```jsx
export default function Button({ children, onClick, variant = 'primary', disabled = false, size = 'md', type = 'button' }) {
  const base = 'inline-flex items-center justify-center font-semibold rounded-btn transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50 disabled:cursor-not-allowed'

  const sizes = {
    sm: 'px-4 py-1.5 text-xs',
    md: 'px-5 py-2.5 text-sm',
    lg: 'px-7 py-3 text-base',
  }

  const variants = {
    primary:   'bg-primary text-white hover:bg-primary-hover shadow-sm',
    secondary: 'bg-surface text-ink border border-subtle hover:bg-subtle',
    danger:    'bg-danger text-white hover:opacity-90',
    ghost:     'bg-transparent text-muted hover:bg-subtle hover:text-ink',
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${sizes[size]} ${variants[variant]}`}
    >
      {children}
    </button>
  )
}
```

- [ ] **Step 3: Replace StatusBadge.jsx**

```jsx
const STATUS_MAP = {
  pending:      { bg: 'bg-card-lavender',  text: 'text-ink'     },
  running:      { bg: 'bg-card-blue',      text: 'text-ink',  pulse: true },
  completed:    { bg: 'bg-card-green',     text: 'text-ink'     },
  failed:       { bg: 'bg-red-100',        text: 'text-danger'  },
  scraped:      { bg: 'bg-subtle',         text: 'text-muted'   },
  filtered_out: { bg: 'bg-subtle',         text: 'text-muted'   },
  qualified:    { bg: 'bg-card-lavender',  text: 'text-primary' },
  enriched:     { bg: 'bg-card-blue',      text: 'text-ink'     },
  drafted:      { bg: 'bg-card-orange',    text: 'text-ink'     },
  draft:        { bg: 'bg-card-lavender',  text: 'text-primary' },
  approved:     { bg: 'bg-card-green',     text: 'text-success' },
  sent:         { bg: 'bg-card-blue',      text: 'text-ink'     },
}

export default function StatusBadge({ status }) {
  const { bg, text, pulse } = STATUS_MAP[status] || { bg: 'bg-subtle', text: 'text-muted' }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${bg} ${text}`}>
      {pulse && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
      {status?.replace(/_/g, ' ')}
    </span>
  )
}
```

- [ ] **Step 4: Verify in browser**

Open the dashboard. Expected:
- Buttons are now pill-shaped (full rounded)
- Primary button is purple (`#7c4dbe`)
- Status badges are pill-shaped with brand pastel backgrounds
- Cards have 16px radius with subtle shadow

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/Card.jsx dashboard/src/components/Button.jsx dashboard/src/components/StatusBadge.jsx
git commit -m "feat(ui): pill buttons, pastel status badges, card variant support"
```

---

## Task 4: Redesign RunsPage.jsx — bento stats + run cards

**Files:**
- Modify: `dashboard/src/pages/RunsPage.jsx`

- [ ] **Step 1: Replace RunsPage.jsx completely**

```jsx
import { useState, useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { Activity } from 'lucide-react'
import { useRuns, useCreateRun } from '../api/runs'
import Card from '../components/Card'
import Button from '../components/Button'
import Modal from '../components/Modal'
import StatusBadge from '../components/StatusBadge'

function NewRunModal({ isOpen, onClose }) {
  const [city, setCity] = useState('')
  const [state, setState] = useState('')
  const [maxReviews, setMaxReviews] = useState(200)
  const createRun = useCreateRun()

  const handleSubmit = (e) => {
    e.preventDefault()
    createRun.mutate(
      { city, state: state.toUpperCase(), max_reviews: maxReviews },
      { onSuccess: () => { onClose(); setCity(''); setState('') } }
    )
  }

  const inputCls = 'w-full border border-subtle rounded-btn px-4 py-2.5 text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-primary/30'

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="New City Run">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label className="block text-xs font-semibold text-muted mb-1 uppercase tracking-wide">City</label>
          <input value={city} onChange={e => setCity(e.target.value)} placeholder="e.g. Houston" required className={inputCls} />
        </div>
        <div>
          <label className="block text-xs font-semibold text-muted mb-1 uppercase tracking-wide">State</label>
          <input value={state} onChange={e => setState(e.target.value.toUpperCase())} placeholder="TX" maxLength={2} required className={inputCls} />
        </div>
        <div>
          <label className="block text-xs font-semibold text-muted mb-1 uppercase tracking-wide">Max Reviews Per Clinic</label>
          <input type="number" value={maxReviews} onChange={e => setMaxReviews(Number(e.target.value))} min={20} max={500} className={inputCls} />
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <Button variant="ghost" onClick={onClose} type="button">Cancel</Button>
          <Button type="submit" disabled={createRun.isPending}>
            {createRun.isPending ? 'Starting…' : 'Start Run'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function StatCard({ label, value, variant }) {
  return (
    <Card variant={variant} className="flex flex-col gap-1">
      <span className="text-3xl font-bold text-ink">{value ?? 0}</span>
      <span className="text-xs font-semibold text-muted uppercase tracking-wide">{label}</span>
    </Card>
  )
}

function RunCard({ run }) {
  const found = run.total_clinics_found || 0
  const stats = [
    { label: 'Found',     value: found,                color: 'bg-card-blue'     },
    { label: 'Qualified', value: run.total_qualified,  color: 'bg-card-lavender' },
    { label: 'Enriched',  value: run.total_enriched,   color: 'bg-card-green'    },
    { label: 'Drafted',   value: run.total_drafted,    color: 'bg-card-orange'   },
  ]

  return (
    <Card>
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="font-bold text-ink text-lg">{run.city}, {run.state}</div>
          <div className="text-xs text-muted mt-0.5">
            {new Date(run.created_at).toLocaleString()} · via {run.triggered_by}
          </div>
        </div>
        <StatusBadge status={run.status} />
      </div>

      <div className="grid grid-cols-4 gap-2">
        {stats.map(({ label, value, color }) => (
          <div key={label} className={`${color} rounded-xl px-3 py-2 text-center`}>
            <div className="text-xl font-bold text-ink">{value ?? 0}</div>
            <div className="text-xs text-muted">{label}</div>
          </div>
        ))}
      </div>
    </Card>
  )
}

export default function RunsPage() {
  const { data: runs = [], isLoading } = useRuns()
  const [modalOpen, setModalOpen] = useState(false)
  const listRef = useRef(null)

  const totals = runs.reduce(
    (acc, r) => ({
      found:     acc.found     + (r.total_clinics_found || 0),
      qualified: acc.qualified + (r.total_qualified     || 0),
      enriched:  acc.enriched  + (r.total_enriched      || 0),
      drafted:   acc.drafted   + (r.total_drafted        || 0),
    }),
    { found: 0, qualified: 0, enriched: 0, drafted: 0 }
  )

  useEffect(() => {
    if (!isLoading && listRef.current) {
      gsap.fromTo(
        listRef.current.children,
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, stagger: 0.07, duration: 0.35, ease: 'power2.out' }
      )
    }
  }, [isLoading])

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-ink">Pipeline Runs</h1>
          <p className="text-muted text-sm mt-1">Trigger and monitor city scraping runs</p>
        </div>
        <Button onClick={() => setModalOpen(true)}>+ New Run</Button>
      </div>

      {/* Bento stat cards */}
      {runs.length > 0 && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <StatCard label="Clinics Found"  value={totals.found}     variant="blue"    />
          <StatCard label="Qualified"      value={totals.qualified} variant="lavender" />
          <StatCard label="Enriched"       value={totals.enriched}  variant="green"   />
          <StatCard label="Drafted"        value={totals.drafted}   variant="orange"  />
        </div>
      )}

      {/* Run list */}
      {isLoading ? (
        <div className="text-muted text-sm">Loading…</div>
      ) : runs.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center py-12 gap-3 text-muted">
            <Activity size={36} strokeWidth={1.2} />
            <p className="text-sm">No runs yet — trigger your first city scan above</p>
          </div>
        </Card>
      ) : (
        <div ref={listRef} className="flex flex-col gap-4">
          {runs.map(run => <RunCard key={run.id} run={run} />)}
        </div>
      )}

      <NewRunModal isOpen={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  )
}
```

- [ ] **Step 2: Verify in browser**

Navigate to `/runs`. Expected:
- "Pipeline Runs" heading, bold and large
- 4 colored bento stat cards across the top (blue / lavender / green / orange)
- Each run card shows a 4-cell mini-grid (Found / Qualified / Enriched / Drafted) with pastel backgrounds
- Empty state shows Activity icon with prompt text
- "New Run" button is purple pill

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/pages/RunsPage.jsx
git commit -m "feat(ui): bento stat cards and refreshed run cards on RunsPage"
```

---

## Task 5: Redesign ClinicsPage.jsx — pill filter tabs + accent borders

**Files:**
- Modify: `dashboard/src/pages/ClinicsPage.jsx`

- [ ] **Step 1: Replace ClinicsPage.jsx completely**

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Search } from 'lucide-react'
import { useClinics } from '../api/clinics'
import Card from '../components/Card'
import StatusBadge from '../components/StatusBadge'

const STATUS_FILTERS = [
  { value: '',            label: 'All'         },
  { value: 'qualified',   label: 'Qualified'   },
  { value: 'enriched',    label: 'Enriched'    },
  { value: 'drafted',     label: 'Drafted'     },
  { value: 'filtered_out',label: 'Filtered Out'},
]

const ACCENT_BY_STATUS = {
  qualified:    'border-l-primary',
  enriched:     'border-l-card-blue',
  drafted:      'border-l-card-orange',
  filtered_out: 'border-l-subtle',
  scraped:      'border-l-subtle',
}

export default function ClinicsPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [cityFilter, setCityFilter] = useState('')
  const { data: clinics = [], isLoading } = useClinics({
    status: statusFilter || undefined,
    city:   cityFilter   || undefined,
  })
  const navigate = useNavigate()

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-ink">Clinics</h1>
        <p className="text-muted text-sm mt-1">{clinics.length} clinics</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        {/* City search */}
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            value={cityFilter}
            onChange={e => setCityFilter(e.target.value)}
            placeholder="Search city…"
            className="border border-subtle rounded-btn pl-8 pr-4 py-2 text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-primary/30 w-44"
          />
        </div>

        {/* Status pill tabs */}
        <div className="flex gap-1.5 flex-wrap">
          {STATUS_FILTERS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setStatusFilter(value)}
              className={`px-3.5 py-1.5 rounded-btn text-xs font-semibold transition-all duration-150 ${
                statusFilter === value
                  ? 'bg-primary text-white shadow-sm'
                  : 'bg-surface text-muted border border-subtle hover:border-primary/40 hover:text-ink'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Clinic grid */}
      {isLoading ? (
        <div className="text-muted text-sm">Loading…</div>
      ) : clinics.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center py-12 gap-3 text-muted">
            <Building2 size={36} strokeWidth={1.2} />
            <p className="text-sm">No clinics match your filters</p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {clinics.map(clinic => {
            const accentClass = ACCENT_BY_STATUS[clinic.status] || 'border-l-subtle'
            return (
              <Card
                key={clinic.id}
                onClick={() => navigate(`/clinics/${clinic.id}`)}
                className={`border-l-4 ${accentClass} hover:shadow-card-hover`}
              >
                <div className="flex items-start justify-between mb-2 gap-2">
                  <div className="font-semibold text-ink text-sm leading-snug flex-1">{clinic.name}</div>
                  <StatusBadge status={clinic.status} />
                </div>
                <div className="text-xs text-muted mb-3">{clinic.city}, {clinic.state}</div>
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-xs text-muted">⭐ {clinic.overall_rating ?? '—'}</span>
                  <span className="text-xs text-muted">{clinic.total_reviews ?? '—'} reviews</span>
                  {clinic.insurance_flag_count > 0 && (
                    <span className="text-xs font-semibold bg-card-lavender text-primary px-2 py-0.5 rounded-full">
                      {clinic.insurance_flag_count} flagged
                    </span>
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify in browser**

Navigate to `/clinics`. Expected:
- Pill filter tabs row (All / Qualified / Enriched / Drafted / Filtered Out)
- Active filter tab is purple, inactive are outlined
- Clinic cards have a colored left border accent matching their status
- Flagged count shown as lavender pill badge
- Search input has a search icon prefix

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/pages/ClinicsPage.jsx
git commit -m "feat(ui): pill filter tabs and status accent borders on ClinicsPage"
```

---

## Task 6: Redesign ClinicDetailPage.jsx

**Files:**
- Modify: `dashboard/src/pages/ClinicDetailPage.jsx`

- [ ] **Step 1: Replace ClinicDetailPage.jsx completely**

```jsx
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, AlertTriangle } from 'lucide-react'
import { useClinicReviews } from '../api/clinics'
import Card from '../components/Card'
import Button from '../components/Button'

const INSURANCE_TERMS = [
  'insurance claim', 'insurance denied', 'claim rejected', 'claim not processed',
  'reimbursement', 'eob', 'explanation of benefits', 'out of pocket', 'overcharged',
  'insurance fraud', 'billed incorrectly', 'double charged', 'balance billing',
  'wrong billing code', 'failed to submit', 'billing issue',
]

function highlightInsuranceText(text) {
  let result = text
  INSURANCE_TERMS.forEach(term => {
    const regex = new RegExp(`(${term})`, 'gi')
    result = result.replace(regex, '<mark class="flag-highlight">$1</mark>')
  })
  return result
}

function StarRating({ rating }) {
  const stars = rating || 0
  return (
    <span className="text-xs">
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={i < stars ? 'text-yellow-400' : 'text-subtle'}>★</span>
      ))}
    </span>
  )
}

export default function ClinicDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: reviews = [], isLoading } = useClinicReviews(id)

  const flagged = reviews.filter(r => r.insurance_flag)
  const others  = reviews.filter(r => !r.insurance_flag)

  return (
    <div>
      {/* Back */}
      <Button variant="ghost" size="sm" onClick={() => navigate('/clinics')}>
        <ArrowLeft size={14} className="mr-1" /> Back to Clinics
      </Button>

      {/* Header */}
      <div className="mt-4 mb-8">
        <h1 className="text-3xl font-bold text-ink">Clinic Reviews</h1>
        <div className="flex gap-4 mt-1">
          {flagged.length > 0 && (
            <span className="text-xs font-semibold bg-card-lavender text-primary px-2.5 py-0.5 rounded-full">
              {flagged.length} insurance complaint{flagged.length !== 1 ? 's' : ''}
            </span>
          )}
          <span className="text-xs text-muted">{others.length} other review{others.length !== 1 ? 's' : ''}</span>
        </div>
      </div>

      {isLoading ? (
        <div className="text-muted text-sm">Loading…</div>
      ) : (
        <div className="flex flex-col gap-4">

          {/* Flagged reviews */}
          {flagged.length > 0 && (
            <>
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle size={14} className="text-primary" />
                <span className="text-xs font-bold text-primary uppercase tracking-widest">
                  Insurance Complaints
                </span>
              </div>
              {flagged.map(review => (
                <Card key={review.id} className="border-l-4 border-l-primary">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <span className="font-semibold text-sm text-ink">{review.author || 'Anonymous'}</span>
                    <StarRating rating={review.rating} />
                    {review.flag_reason && (
                      <span className="text-xs bg-card-lavender text-primary px-2 py-0.5 rounded-full font-semibold">
                        {review.flag_reason.replace(/_/g, ' ')}
                      </span>
                    )}
                  </div>
                  <p
                    className="text-sm text-ink leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: highlightInsuranceText(review.text) }}
                  />
                  {review.llm_reasoning && (
                    <p className="text-xs text-muted mt-3 italic border-t border-subtle pt-2">
                      AI analysis: {review.llm_reasoning}
                    </p>
                  )}
                </Card>
              ))}
            </>
          )}

          {/* Other reviews */}
          {others.length > 0 && (
            <>
              <div className="mt-4 mb-1">
                <span className="text-xs font-bold text-muted uppercase tracking-widest">Other Reviews</span>
              </div>
              {others.map(review => (
                <Card key={review.id}>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-semibold text-sm text-ink">{review.author || 'Anonymous'}</span>
                    <StarRating rating={review.rating} />
                  </div>
                  <p className="text-sm text-muted leading-relaxed">{review.text}</p>
                </Card>
              ))}
            </>
          )}

        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify in browser**

Click into any clinic from the Clinics page. Expected:
- Back button with arrow icon (ghost pill style)
- "Insurance Complaints" section with lavender count badge
- Flagged cards have purple left border, lavender flag_reason badge, italic AI analysis
- Star rating renders colored stars
- Other reviews section is visually quieter (muted text)

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/pages/ClinicDetailPage.jsx
git commit -m "feat(ui): refreshed ClinicDetailPage with lavender flag section and star ratings"
```

---

## Task 7: Redesign DraftsPage.jsx

**Files:**
- Modify: `dashboard/src/pages/DraftsPage.jsx`

- [ ] **Step 1: Replace DraftsPage.jsx completely**

```jsx
import { useState } from 'react'
import { Mail } from 'lucide-react'
import { useDrafts, usePatchDraft, exportDraft } from '../api/drafts'
import Card from '../components/Card'
import Button from '../components/Button'
import StatusBadge from '../components/StatusBadge'

const TABS = [
  { value: 'draft',    label: 'Draft'    },
  { value: 'approved', label: 'Approved' },
  { value: '',         label: 'All'      },
]

function DraftCard({ draft }) {
  const [editing, setEditing]         = useState(false)
  const [subject, setSubject]         = useState(draft.subject)
  const [body, setBody]               = useState(draft.body)
  const [activeVariant, setActiveVariant] = useState(0)
  const patch = usePatchDraft()

  const save    = () => patch.mutate({ id: draft.id, subject, body }, { onSuccess: () => setEditing(false) })
  const approve = () => patch.mutate({ id: draft.id, status: 'approved' })

  const inputCls = 'w-full border border-subtle rounded-xl px-4 py-2.5 text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-primary/30'

  return (
    <Card className="border-l-4 border-l-card-lavender">
      {/* Subject + status row */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1">
          {/* Variant selector */}
          {(draft.subject_variants?.length ?? 0) > 1 && (
            <div className="flex gap-1.5 mb-2 flex-wrap">
              {draft.subject_variants.map((v, i) => (
                <button
                  key={i}
                  onClick={() => { setActiveVariant(i); if (!editing) setSubject(v) }}
                  className={`text-xs px-2.5 py-1 rounded-full border font-semibold transition-colors ${
                    activeVariant === i
                      ? 'bg-primary text-white border-primary'
                      : 'border-subtle text-muted hover:border-primary/40'
                  }`}
                >
                  Subject {i + 1}
                </button>
              ))}
            </div>
          )}

          {editing ? (
            <input value={subject} onChange={e => setSubject(e.target.value)} className={`${inputCls} font-semibold mb-2`} />
          ) : (
            <div className="font-semibold text-ink text-sm mb-1">{subject}</div>
          )}
        </div>
        <StatusBadge status={draft.status} />
      </div>

      {/* Body */}
      {editing ? (
        <textarea
          value={body}
          onChange={e => setBody(e.target.value)}
          rows={8}
          className={`${inputCls} font-mono mb-3`}
        />
      ) : (
        <div
          className="text-sm text-ink leading-relaxed bg-subtle rounded-xl px-4 py-3 mb-3 prose prose-sm max-w-none"
          dangerouslySetInnerHTML={{ __html: body }}
        />
      )}

      {/* Actions */}
      <div className="flex gap-2 flex-wrap">
        {draft.status === 'draft' && (
          <Button size="sm" onClick={approve} disabled={patch.isPending}>Approve</Button>
        )}
        {editing ? (
          <>
            <Button size="sm" onClick={save} disabled={patch.isPending}>Save</Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
          </>
        ) : (
          <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>Edit</Button>
        )}
        <Button size="sm" variant="ghost" onClick={() => exportDraft(draft.id, 'pdf')}>PDF</Button>
        <Button size="sm" variant="ghost" onClick={() => exportDraft(draft.id, 'html')}>HTML</Button>
      </div>
    </Card>
  )
}

export default function DraftsPage() {
  const [tab, setTab] = useState('draft')
  const { data: drafts = [], isLoading } = useDrafts(tab || undefined)

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-ink">Email Drafts</h1>
          <p className="text-muted text-sm mt-1">{drafts.length} draft{drafts.length !== 1 ? 's' : ''}</p>
        </div>
        {/* Pill tabs */}
        <div className="flex gap-1.5">
          {TABS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setTab(value)}
              className={`px-4 py-2 rounded-btn text-sm font-semibold transition-all duration-150 ${
                tab === value
                  ? 'bg-primary text-white shadow-sm'
                  : 'bg-surface text-muted border border-subtle hover:border-primary/40 hover:text-ink'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="text-muted text-sm">Loading…</div>
      ) : drafts.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center py-12 gap-3 text-muted">
            <Mail size={36} strokeWidth={1.2} />
            <p className="text-sm">No drafts in this category</p>
          </div>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          {drafts.map(d => <DraftCard key={d.id} draft={d} />)}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify in browser**

Navigate to `/drafts`. Expected:
- Pill tab group (Draft / Approved / All) in top-right, purple active tab
- Draft cards have lavender left border accent
- Email body rendered in inset subtle-bg box
- Subject variant buttons as small pills
- All action buttons are pill-shaped

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/pages/DraftsPage.jsx
git commit -m "feat(ui): pill tabs, inset body preview, refreshed draft cards on DraftsPage"
```

---

## Task 8: Redesign SettingsPage.jsx

**Files:**
- Modify: `dashboard/src/pages/SettingsPage.jsx`

- [ ] **Step 1: Replace SettingsPage.jsx completely**

```jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings } from 'lucide-react'
import client from '../api/client'
import Card from '../components/Card'
import Button from '../components/Button'

const inputCls = 'w-full border border-subtle rounded-xl px-4 py-2.5 text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-primary/30'

function SectionHeader({ children }) {
  return (
    <div className="pb-3 mb-4 border-b border-subtle">
      <h2 className="text-base font-bold text-ink">{children}</h2>
    </div>
  )
}

function Field({ label, name, type = 'text', placeholder, value, onChange }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-muted mb-1.5 uppercase tracking-wide">{label}</label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className={inputCls}
      />
    </div>
  )
}

function SchedulerConfig() {
  const [city, setCity] = useState('')
  const [state, setState] = useState('')
  const [cron, setCron] = useState('0 9 * * 1')
  const qc = useQueryClient()

  const { data: schedules = [] } = useQuery({
    queryKey: ['schedules'],
    queryFn: () => client.get('/settings/schedules').then(r => r.data),
  })

  const addSchedule = useMutation({
    mutationFn: data => client.post('/settings/schedules', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['schedules'] }); setCity(''); setState('') },
  })

  const removeSchedule = useMutation({
    mutationFn: jobId => client.delete(`/settings/schedules/${jobId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  })

  return (
    <Card>
      <SectionHeader>Scheduled Runs</SectionHeader>
      <div className="flex flex-col gap-3 mb-4">
        <div className="flex gap-2">
          <input value={city} onChange={e => setCity(e.target.value)} placeholder="City" className={`${inputCls} flex-1`} />
          <input value={state} onChange={e => setState(e.target.value.toUpperCase())} placeholder="ST" maxLength={2} className={`${inputCls} w-16`} />
        </div>
        <div>
          <label className="block text-xs font-semibold text-muted mb-1.5 uppercase tracking-wide">Cron Expression</label>
          <input value={cron} onChange={e => setCron(e.target.value)} placeholder="0 9 * * 1" className={inputCls} />
          <p className="text-xs text-muted mt-1.5">
            e.g. every Monday 9am: <code className="bg-subtle px-1 py-0.5 rounded text-xs">0 9 * * 1</code>
          </p>
        </div>
        <Button size="sm" onClick={() => addSchedule.mutate({ city, state, cron })} disabled={!city || !state}>
          Add Schedule
        </Button>
      </div>

      {schedules.length > 0 && (
        <div className="flex flex-col gap-2">
          {schedules.map(s => (
            <div key={s.job_id} className="flex items-center justify-between bg-subtle rounded-xl px-4 py-2.5">
              <div>
                <span className="font-semibold text-sm text-ink">{s.job_id}</span>
                <span className="text-xs text-muted ml-2">next: {s.next_run || '—'}</span>
              </div>
              <Button size="sm" variant="ghost" onClick={() => removeSchedule.mutate(s.job_id)}>Remove</Button>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

export default function SettingsPage() {
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => client.get('/settings').then(r => r.data),
  })

  const [form, setForm] = useState({
    apollo_api_key:      '',
    gemini_api_key:      '',
    proxy_url:           '',
    max_reviews_default: 200,
  })

  const save = useMutation({ mutationFn: data => client.put('/settings', data) })

  const set = name => e => setForm(f => ({ ...f, [name]: e.target.value }))

  if (isLoading) return <div className="text-muted text-sm">Loading…</div>

  const ph = name => settings?.[name] ? '(set — enter new value to update)' : 'Not set'

  return (
    <div>
      <div className="flex items-center gap-3 mb-8">
        <Settings size={24} className="text-primary" />
        <h1 className="text-3xl font-bold text-ink">Settings</h1>
      </div>

      <div className="flex flex-col gap-6 max-w-lg">
        <Card>
          <SectionHeader>API Keys</SectionHeader>
          <div className="flex flex-col gap-4">
            <Field label="Apollo API Key"  name="apollo_api_key" type="password" placeholder={ph('apollo_api_key')} value={form.apollo_api_key} onChange={set('apollo_api_key')} />
            <Field label="Gemini API Key"  name="gemini_api_key" type="password" placeholder={ph('gemini_api_key')} value={form.gemini_api_key} onChange={set('gemini_api_key')} />
          </div>
        </Card>

        <Card>
          <SectionHeader>Scraper Config</SectionHeader>
          <div className="flex flex-col gap-4">
            <Field label="Proxy URL (optional)" name="proxy_url" placeholder="http://proxy:8080" value={form.proxy_url} onChange={set('proxy_url')} />
            <div>
              <label className="block text-xs font-semibold text-muted mb-1.5 uppercase tracking-wide">Max Reviews Default</label>
              <input
                type="number"
                value={form.max_reviews_default}
                onChange={e => setForm(f => ({ ...f, max_reviews_default: Number(e.target.value) }))}
                min={20}
                max={500}
                className={inputCls}
              />
            </div>
          </div>
        </Card>

        <div className="flex items-center gap-3">
          <Button onClick={() => save.mutate(form)} disabled={save.isPending}>
            {save.isPending ? 'Saving…' : 'Save Settings'}
          </Button>
          {save.isSuccess && (
            <span className="text-success text-sm font-semibold">Saved ✓</span>
          )}
        </div>

        <SchedulerConfig />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify in browser**

Navigate to `/settings`. Expected:
- Settings icon + large bold heading
- Section headers with bottom border separator
- Labels in small uppercase tracking style
- Inputs have larger rounded corners (`rounded-xl`)
- Save button is purple pill, full-width of form area
- Scheduler section matches the card style

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/pages/SettingsPage.jsx
git commit -m "feat(ui): refined form styling, section headers, and uppercase labels on SettingsPage"
```

---

## Final verification

- [ ] **Run the full dev build and do a visual pass of every page**

```bash
cd dashboard && npm run dev
```

Visit each route and verify:
- `/runs` — dark sidebar, warm bg, bento cards, purple buttons, pill badges
- `/clinics` — pill filter tabs, accent borders on cards, search icon in input
- `/clinics/:id` — back button with arrow, lavender complaint badges, star ratings
- `/drafts` — pill tabs, inset body box, lavender left border on cards
- `/settings` — settings icon in header, section separators, xl input radius

- [ ] **Run the production build to confirm no Tailwind/Vite errors**

```bash
cd dashboard && npm run build
```
Expected: build succeeds with no errors.

- [ ] **Final commit**

```bash
git add -A
git commit -m "feat(ui): complete dashboard redesign matching lavenderhealth.ai brand identity"
```
