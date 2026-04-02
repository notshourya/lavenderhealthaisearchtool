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
