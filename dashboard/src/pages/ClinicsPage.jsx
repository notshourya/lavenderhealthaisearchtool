import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useClinics } from '../api/clinics'
import Card from '../components/Card'
import StatusBadge from '../components/StatusBadge'

const STATUS_OPTIONS = ['', 'scraped', 'filtered_out', 'qualified', 'enriched', 'drafted']

export default function ClinicsPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [cityFilter, setCityFilter] = useState('')
  const { data: clinics = [], isLoading } = useClinics({ status: statusFilter || undefined, city: cityFilter || undefined })
  const navigate = useNavigate()

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-ink">Clinics</h1>
        <p className="text-muted text-sm mt-0.5">{clinics.length} clinics found</p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <input
          value={cityFilter}
          onChange={e => setCityFilter(e.target.value)}
          placeholder="Filter by city…"
          className="border border-gray-200 rounded-btn px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 w-48"
        />
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="border border-gray-200 rounded-btn px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
        >
          {STATUS_OPTIONS.map(s => (
            <option key={s} value={s}>{s || 'All statuses'}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="text-muted text-sm">Loading…</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {clinics.map(clinic => (
            <Card
              key={clinic.id}
              className="cursor-pointer hover:shadow-card-hover transition-shadow duration-200"
              onClick={() => navigate(`/clinics/${clinic.id}`)}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="font-semibold text-ink text-sm leading-snug flex-1 pr-2">{clinic.name}</div>
                <StatusBadge status={clinic.status} />
              </div>
              <div className="text-xs text-muted mb-3">{clinic.city}, {clinic.state}</div>
              <div className="flex items-center gap-4 text-xs">
                <span className="text-muted">⭐ {clinic.overall_rating ?? '—'}</span>
                <span className="text-muted">{clinic.total_reviews ?? '—'} reviews</span>
                {clinic.insurance_flag_count > 0 && (
                  <span className="text-accent font-semibold">
                    🚩 {clinic.insurance_flag_count} flagged
                  </span>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
