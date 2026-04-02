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
