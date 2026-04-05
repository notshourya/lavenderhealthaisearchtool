import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Search, SlidersHorizontal } from 'lucide-react'
import { useClinics } from '../api/clinics'
import StatusBadge from '../components/StatusBadge'

const STATUS_FILTERS = [
  { value: '', label: 'All' },
  { value: 'scraped', label: 'Discovered' },
  { value: 'qualified', label: 'Affected' },
  { value: 'enriched', label: 'Enriched' },
  { value: 'drafted', label: 'Drafted' },
  { value: 'filtered_out', label: 'Filtered Out' },
]

function ClinicCard({ clinic, onClick }) {
  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      className="group flex flex-col justify-between bg-zinc-950/60 backdrop-blur-3xl border border-white/5 p-8 rounded-[32px] shadow-2xl cursor-pointer transition-all duration-500 hover:shadow-[0_20px_60px_rgba(0,0,0,0.4)] hover:-translate-y-1 hover:border-white/10"
    >
      <div className="mb-10">
        <div className="flex items-start justify-between gap-4 mb-4">
          <h3 className="font-medium text-2xl text-white tracking-tight leading-tight line-clamp-2">{clinic.name}</h3>
          <StatusBadge status={clinic.status} />
        </div>
        <div className="text-base text-zinc-500 font-medium">{clinic.city}, {clinic.state}</div>
      </div>

      <div className="grid grid-cols-3 gap-6 pt-8 border-t border-white/5">
        <div>
          <div className="text-3xl font-medium text-white tracking-tight font-mono tabular-nums">{clinic.overall_rating ?? '—'}</div>
          <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest mt-2">Rating</div>
        </div>
        <div>
          <div className="text-3xl font-medium text-white tracking-tight font-mono tabular-nums">{clinic.total_reviews ?? '—'}</div>
          <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest mt-2">Reviews</div>
        </div>
        <div>
          <div className="text-3xl font-medium text-white tracking-tight font-mono tabular-nums">{clinic.insurance_flag_count ?? 0}</div>
          <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest mt-2">Flags</div>
        </div>
      </div>
    </div>
  )
}

export default function ClinicsPage() {
  const [statusFilter, setStatusFilter] = useState('qualified')
  const [cityFilter, setCityFilter] = useState('')
  const { data: clinics = [], isLoading } = useClinics({
    status: statusFilter || undefined,
    city: cityFilter || undefined,
  })
  const navigate = useNavigate()

  return (
    <div className="w-full pb-32">
      <header className="mb-20">
        <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/10 backdrop-blur-xl px-5 py-2 text-xs font-bold uppercase tracking-widest text-zinc-300 mb-8 shadow-sm">
          <SlidersHorizontal size={14} />
          Browse Clinics
        </div>
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-10">
          <div className="w-full">
            <h1 className="text-5xl lg:text-6xl font-medium text-white tracking-tighter mb-6 leading-tight">Clinic Registry</h1>
            <p className="text-zinc-400 text-xl font-medium leading-relaxed">
              Affected clinics with discovery and filtered-out cases separated. Inspect the pipeline from start to finish.
            </p>
          </div>
          <div className="text-sm font-bold uppercase tracking-widest text-zinc-500 px-6 py-3 rounded-full border border-white/10 bg-white/5 whitespace-nowrap shadow-sm">
            {clinics.length} clinics
          </div>
        </div>

        <div className="flex flex-col md:flex-row md:items-center gap-6 mt-16 bg-zinc-950/40 backdrop-blur-2xl border border-white/5 rounded-[32px] p-4 shadow-xl">
          <div className="relative w-full md:w-[400px]">
            <Search size={20} className="absolute left-6 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              value={cityFilter}
              onChange={e => setCityFilter(e.target.value)}
              placeholder="Search by city..."
              className="w-full border border-transparent rounded-full pl-14 pr-6 py-4 text-base bg-white/5 text-white focus:outline-none focus:ring-2 focus:ring-white/20 transition-all placeholder:text-zinc-500 font-medium"
            />
          </div>

          <div className="flex gap-2 flex-wrap flex-1 justify-end">
            {STATUS_FILTERS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setStatusFilter(value)}
                className={`px-6 py-4 rounded-full text-sm font-bold transition-all duration-300 border shadow-sm ${
                  statusFilter === value
                    ? 'bg-white text-black border-white'
                    : 'bg-transparent text-zinc-400 border-transparent hover:bg-white/10 hover:text-white'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {isLoading ? (
        <div className="text-zinc-500 font-medium text-lg py-16 text-left">Loading clinics...</div>
      ) : clinics.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 bg-zinc-950/40 backdrop-blur-3xl rounded-[48px] border border-white/5 shadow-2xl">
          <Building2 size={64} strokeWidth={1.5} className="mb-10 text-white/20" />
          <p className="text-2xl font-medium text-center text-zinc-300 max-w-lg leading-relaxed">No clinics match this view. Try Discovered, Filtered Out, or All to inspect the broader dataset.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {clinics.map(clinic => (
            <ClinicCard
              key={clinic.id}
              clinic={clinic}
              onClick={() => navigate(`/clinics/${clinic.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}