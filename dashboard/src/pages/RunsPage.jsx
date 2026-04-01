import { useState, useEffect, useRef } from 'react'
import { gsap } from 'gsap'
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
    createRun.mutate({ city, state: state.toUpperCase(), max_reviews: maxReviews }, {
      onSuccess: () => { onClose(); setCity(''); setState('') },
    })
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="New City Run">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label className="block text-sm font-semibold text-ink mb-1">City</label>
          <input
            value={city}
            onChange={e => setCity(e.target.value)}
            placeholder="e.g. Houston"
            required
            className="w-full border border-gray-200 rounded-btn px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
        <div>
          <label className="block text-sm font-semibold text-ink mb-1">State</label>
          <input
            value={state}
            onChange={e => setState(e.target.value.toUpperCase())}
            placeholder="e.g. TX"
            maxLength={2}
            required
            className="w-full border border-gray-200 rounded-btn px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
        <div>
          <label className="block text-sm font-semibold text-ink mb-1">Max Reviews Per Clinic</label>
          <input
            type="number"
            value={maxReviews}
            onChange={e => setMaxReviews(Number(e.target.value))}
            min={20}
            max={500}
            className="w-full border border-gray-200 rounded-btn px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
        <div className="flex gap-2 justify-end mt-2">
          <Button variant="ghost" onClick={onClose} type="button">Cancel</Button>
          <Button type="submit" disabled={createRun.isPending}>
            {createRun.isPending ? 'Starting…' : 'Start Run'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function ProgressBar({ label, value, total, color = 'bg-primary' }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0
  return (
    <div className="flex items-center gap-2 text-xs text-muted">
      <span className="w-16 text-right">{label}</span>
      <div className="flex-1 h-1.5 bg-subtle rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8">{value}</span>
    </div>
  )
}

export default function RunsPage() {
  const { data: runs = [], isLoading } = useRuns()
  const [modalOpen, setModalOpen] = useState(false)
  const listRef = useRef(null)

  useEffect(() => {
    if (!isLoading && listRef.current) {
      gsap.fromTo(
        listRef.current.children,
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, stagger: 0.06, duration: 0.4, ease: 'power2.out' }
      )
    }
  }, [isLoading])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-ink">Pipeline Runs</h1>
          <p className="text-muted text-sm mt-0.5">Trigger and monitor city scraping runs</p>
        </div>
        <Button onClick={() => setModalOpen(true)}>+ New Run</Button>
      </div>

      {isLoading ? (
        <div className="text-muted text-sm">Loading…</div>
      ) : runs.length === 0 ? (
        <Card>
          <p className="text-muted text-center py-8">No runs yet. Start your first run above.</p>
        </Card>
      ) : (
        <div ref={listRef} className="flex flex-col gap-4">
          {runs.map(run => (
            <Card key={run.id} className="hover:shadow-card-hover transition-shadow duration-200">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="font-semibold text-ink">{run.city}, {run.state}</div>
                  <div className="text-xs text-muted mt-0.5">
                    {new Date(run.created_at).toLocaleString()} · via {run.triggered_by}
                  </div>
                </div>
                <StatusBadge status={run.status} />
              </div>
              <div className="flex flex-col gap-1.5 mt-3">
                <ProgressBar label="Found" value={run.total_clinics_found} total={run.total_clinics_found || 1} color="bg-gray-400" />
                <ProgressBar label="Qualified" value={run.total_qualified} total={run.total_clinics_found || 1} color="bg-yellow-400" />
                <ProgressBar label="Enriched" value={run.total_enriched} total={run.total_clinics_found || 1} color="bg-purple-400" />
                <ProgressBar label="Drafted" value={run.total_drafted} total={run.total_clinics_found || 1} color="bg-primary" />
              </div>
            </Card>
          ))}
        </div>
      )}

      <NewRunModal isOpen={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  )
}
