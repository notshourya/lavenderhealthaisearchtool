import { useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useClinicDetail } from '../api/clinics'
import Button from '../components/Button'

function highlightInsuranceText(text) {
  const terms = [
    'insurance claim', 'insurance denied', 'claim rejected', 'claim denied',
    'reimbursement', 'out of pocket', 'overcharged', 'billed incorrectly',
    'double charged', 'billing issue', 'coverage denied', 'prior authorization',
  ]
  let result = text
  terms.forEach(term => {
    const regex = new RegExp(`(${term})`, 'gi')
    result = result.replace(regex, '<mark class="bg-indigo-500/30 text-indigo-200 px-1.5 py-0.5 rounded">$1</mark>')
  })
  return result
}

function Rating({ rating }) {
  return (
    <span className="text-white text-base tracking-widest">
      {'★'.repeat(rating || 0)}{'☆'.repeat(5 - (rating || 0))}
    </span>
  )
}

function formatReviewDate(value) {
  if (!value) return 'Unknown date'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unknown date'
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

function labelize(value) {
  if (!value) return 'Unknown'
  return value.replaceAll('_', ' ')
}

function ReviewChip({ children, tone = 'neutral' }) {
  const tones = {
    neutral: 'bg-white/5 text-zinc-400 border border-white/10 shadow-sm',
    strong: 'bg-white text-black border border-white shadow-lg',
    medium: 'bg-white/10 text-white border border-white/20 shadow-md',
    light: 'bg-transparent text-zinc-300 border border-white/20 shadow-sm',
  }

  return (
    <span className={`rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-widest transition-all ${tones[tone]}`}>
      {children}
    </span>
  )
}

function ContactCard({ contact }) {
  return (
    <div className="rounded-[32px] border border-white/5 bg-zinc-950/40 backdrop-blur-2xl p-8 shadow-xl hover:shadow-[0_10px_40px_rgba(0,0,0,0.3)] hover:-translate-y-1 transition-all duration-300">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <div className="font-medium text-white text-2xl tracking-tight">{contact.first_name || contact.last_name ? `${contact.first_name || ''} ${contact.last_name || ''}`.trim() : 'Apollo contact'}</div>
          <div className="text-sm font-bold uppercase tracking-widest text-zinc-500 mt-2">{contact.title || 'No title provided'}</div>
        </div>
        <ReviewChip tone="strong">{Math.round((contact.confidence_score || 0) * 100)}% Match</ReviewChip>
      </div>
      <div className="text-base font-medium text-zinc-300 break-all bg-black/30 p-4 rounded-2xl border border-white/5 inline-block">{contact.email}</div>
    </div>
  )
}

function ReviewRecord({ review }) {
  const tone =
    review.fault_party === 'insurer'
      ? 'strong'
      : review.fault_party === 'clinic'
        ? 'medium'
        : review.fault_party === 'shared'
          ? 'light'
          : 'neutral'

  return (
    <div className="bg-zinc-950/60 backdrop-blur-3xl border border-white/5 p-10 rounded-[40px] shadow-2xl mb-8 group transition-all duration-500 hover:shadow-[0_20px_60px_rgba(0,0,0,0.4)]">
      <div className="space-y-8">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 mb-4">
          <div className="flex items-center gap-5 flex-wrap">
            <span className="font-medium text-2xl text-white tracking-tight">{review.author || 'Anonymous'}</span>
            <Rating rating={review.rating} />
            <span className="text-sm text-zinc-500 font-bold uppercase tracking-widest ml-2">{formatReviewDate(review.date)}</span>
          </div>
          <div className="flex flex-wrap gap-3">
            <ReviewChip tone={tone}>{labelize(review.fault_party)}</ReviewChip>
            {review.issue_category && <ReviewChip tone="medium">{labelize(review.issue_category)}</ReviewChip>}
            {review.flag_reason && <ReviewChip tone="light">{review.flag_reason}</ReviewChip>}
            {typeof review.classification_confidence === 'number' && (
              <ReviewChip tone="neutral">{Math.round(review.classification_confidence * 100)}% conf.</ReviewChip>
            )}
          </div>
        </div>

        <div
          className="text-lg text-zinc-300 leading-relaxed prose prose-invert prose-lg max-w-none bg-black/30 border border-white/5 rounded-[32px] p-8 shadow-inner"
          dangerouslySetInnerHTML={{ __html: highlightInsuranceText(review.text) }}
        />

        {review.keyword_matches?.length > 0 && (
          <div className="pt-4">
            <div className="text-xs uppercase tracking-widest text-zinc-500 mb-4 font-bold">Matched Keywords</div>
            <div className="flex flex-wrap gap-3">
              {review.keyword_matches.map(keyword => (
                <ReviewChip key={keyword} tone="medium">{keyword}</ReviewChip>
              ))}
            </div>
          </div>
        )}

        {review.llm_reasoning && (
          <div className="rounded-[24px] border border-white/10 bg-white/5 p-8 mt-6 backdrop-blur-md">
            <div className="text-xs uppercase tracking-widest text-zinc-400 mb-4 font-bold">AI Reasoning</div>
            <p className="text-base text-zinc-300 italic leading-relaxed">{review.llm_reasoning}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ClinicDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data, isLoading } = useClinicDetail(id)
  const [filter, setFilter] = useState('insurer')

  const clinic = data?.clinic
  const diagnostics = data?.diagnostics
  const contacts = data?.contacts ?? []
  
  const reviews = useMemo(() => data?.reviews ?? [], [data?.reviews])

  const reviewGroups = useMemo(() => {
    const insurer = reviews.filter(review => review.fault_party === 'insurer' || review.insurance_flag)
    const clinicFault = reviews.filter(review => review.fault_party === 'clinic')
    const shared = reviews.filter(review => review.fault_party === 'shared')
    const other = reviews.filter(
      review => review.fault_party !== 'insurer' && review.fault_party !== 'clinic' && review.fault_party !== 'shared' && !review.insurance_flag
    )
    return { insurer, clinicFault, shared, other }
  }, [reviews])

  const visibleReviews =
    filter === 'insurer'
      ? reviewGroups.insurer
      : filter === 'clinic'
        ? reviewGroups.clinicFault
        : filter === 'shared'
          ? reviewGroups.shared
          : filter === 'other'
            ? reviewGroups.other
            : reviews

  if (isLoading) {
    return <div className="text-zinc-500 font-medium text-lg py-16 text-left">Loading clinic data...</div>
  }

  return (
    <div className="w-full pb-32">
      <div className="mb-16">
        <Button variant="secondary" size="md" onClick={() => navigate('/clinics')}>← Back to Clinics</Button>
      </div>

      <header className="mb-20">
        <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/10 backdrop-blur-xl px-5 py-2 text-xs font-bold uppercase tracking-widest text-zinc-300 mb-8 shadow-sm">
          Evidence Inspector
        </div>
        <h1 className="text-5xl lg:text-7xl font-medium text-white tracking-tighter mb-6 leading-tight">{clinic?.name || 'Clinic reviews'}</h1>
        <p className="text-zinc-400 text-xl font-medium w-full max-w-[1600px] leading-relaxed mb-10">
          Full review evidence for manual inspection before outreach. Review affected cases, pattern strength, and available contacts.
        </p>
        
        <div className="flex flex-wrap gap-4">
          <span className="rounded-full bg-white px-6 py-3 text-sm font-bold uppercase tracking-widest text-black shadow-lg">{reviewGroups.insurer.length} affected</span>
          <span className="rounded-full bg-zinc-900 border border-white/10 px-6 py-3 text-sm font-bold uppercase tracking-widest text-zinc-300 shadow-sm">{reviewGroups.clinicFault.length} clinic fault</span>
          <span className="rounded-full bg-zinc-900 border border-white/10 px-6 py-3 text-sm font-bold uppercase tracking-widest text-zinc-300 shadow-sm">{reviewGroups.shared.length} shared</span>
          <span className="rounded-full bg-zinc-900 border border-white/10 px-6 py-3 text-sm font-bold uppercase tracking-widest text-zinc-300 shadow-sm">{reviewGroups.other.length} other</span>
        </div>
      </header>

      {diagnostics && (
        <section className="mb-24 border-t border-white/5 pt-16">
          <h2 className="text-4xl font-medium text-white tracking-tight mb-12 font-mono tabular-nums">Diagnostics & Patterns</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8">
            <div className="bg-zinc-950/60 backdrop-blur-2xl border border-white/5 p-8 rounded-[32px] shadow-2xl">
              <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-8">Pattern Strength</div>
              <ul className="space-y-5 text-base text-zinc-400 font-medium">
                <li className="flex justify-between border-b border-white/5 pb-4 pr-2"><span>Insurer fault</span> <span className="text-white font-medium text-xl font-mono tabular-nums">{diagnostics.insurer_fault_reviews}</span></li>
                <li className="flex justify-between border-b border-white/5 pb-4 pr-2"><span>Unique reviewers</span> <span className="text-white font-medium text-xl font-mono tabular-nums">{diagnostics.unique_insurer_reviewers}</span></li>
                <li className="flex justify-between pb-2 pr-2"><span>Complaint rate</span> <span className="text-white font-medium text-xl font-mono tabular-nums">{(diagnostics.complaint_rate * 100).toFixed(1)}%</span></li>
              </ul>
            </div>

            <div className="bg-zinc-950/60 backdrop-blur-2xl border border-white/5 p-8 rounded-[32px] shadow-2xl">
              <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-8">Issue Consistency</div>
              <ul className="space-y-5 text-base text-zinc-400 font-medium">
                <li className="flex justify-between items-center border-b border-white/5 pb-4 pr-2"><span>Top issue</span> <span className="text-white font-medium text-lg text-right ml-4 truncate max-w-[140px] font-mono tabular-nums" title={labelize(diagnostics.dominant_issue_category)}>{labelize(diagnostics.dominant_issue_category)}</span></li>
                <li className="flex justify-between border-b border-white/5 pb-4 pr-2"><span>Issue repeats</span> <span className="text-white font-medium text-xl font-mono tabular-nums">{diagnostics.dominant_issue_category_reviews}</span></li>
                <li className="flex justify-between pb-2 pr-2"><span>Shared reviews</span> <span className="text-white font-medium text-xl font-mono tabular-nums">{diagnostics.shared_fault_reviews}</span></li>
              </ul>
            </div>

            <div className="bg-zinc-950/60 backdrop-blur-2xl border border-white/5 p-8 rounded-[32px] shadow-2xl">
              <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-8">Recency</div>
              <ul className="space-y-5 text-base text-zinc-400 font-medium">
                <li className="flex justify-between border-b border-white/5 pb-4 pr-2"><span>Recent issues</span> <span className="text-white font-medium text-xl font-mono tabular-nums">{diagnostics.recent_insurer_fault_reviews}</span></li>
                <li className="flex justify-between border-b border-white/5 pb-4 pr-2"><span>Peak cluster</span> <span className="text-white font-medium text-xl font-mono tabular-nums">{diagnostics.recent_month_cluster_peak}</span></li>
                <li className="flex justify-between pb-2 pr-2"><span>Total reviews</span> <span className="text-white font-medium text-xl font-mono tabular-nums">{diagnostics.total_reviews_known}</span></li>
              </ul>
            </div>

            <div className="bg-zinc-950/60 backdrop-blur-2xl border border-white/5 p-8 rounded-[32px] shadow-2xl">
              <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-8">Guardrails</div>
              <ul className="space-y-5 text-base text-zinc-400 font-medium">
                <li className="flex justify-between border-b border-white/5 pb-4 pr-2"><span>Clinic fault</span> <span className="text-white font-medium text-xl font-mono tabular-nums">{diagnostics.clinic_fault_reviews}</span></li>
                <li className="flex justify-between border-b border-white/5 pb-4 pr-2"><span>Min confirmed</span> <span className="text-white font-medium text-xl font-mono tabular-nums">{diagnostics.min_confirmed_required}</span></li>
                <li className="flex justify-between pb-2 pr-2"><span>Min rate</span> <span className="text-white font-medium text-xl font-mono tabular-nums">{(diagnostics.min_complaint_rate_required * 100).toFixed(1)}%</span></li>
              </ul>
            </div>
          </div>
        </section>
      )}

      <section className="mb-24 border-t border-white/5 pt-16">
        <div className="flex items-center justify-between gap-6 mb-12">
          <div>
            <h2 className="text-4xl font-medium text-white tracking-tight font-mono tabular-nums">Outreach Contacts</h2>
            <div className="text-base text-zinc-500 mt-2 font-medium">Apollo enrichment</div>
          </div>
          <div className="text-sm font-bold uppercase tracking-widest text-zinc-400 bg-white/5 border border-white/10 px-6 py-3 rounded-full shadow-sm">{contacts.length} found</div>
        </div>

        {contacts.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {contacts.map(contact => (
              <ContactCard key={contact.id || contact.email} contact={contact} />
            ))}
          </div>
        ) : (
          <div className="text-zinc-500 py-16 font-medium text-xl border border-white/5 rounded-[40px] bg-zinc-950/40 text-left shadow-xl backdrop-blur-xl">No Apollo contacts found for this clinic yet.</div>
        )}
      </section>

      <section className="border-t border-white/5 pt-16">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-10 mb-14">
          <div>
            <h2 className="text-4xl font-medium text-white tracking-tight font-mono tabular-nums">Review Feed</h2>
            <div className="text-base text-zinc-500 mt-2 font-medium">Read the raw evidence.</div>
          </div>
          
          <div className="flex flex-wrap gap-3 bg-zinc-950/40 backdrop-blur-2xl border border-white/5 p-2 rounded-full shadow-lg">
            {[
              ['insurer', `Affected (${reviewGroups.insurer.length})`],
              ['all', `All (${reviews.length})`],
              ['clinic', `Clinic Fault (${reviewGroups.clinicFault.length})`],
              ['shared', `Shared (${reviewGroups.shared.length})`],
              ['other', `Other (${reviewGroups.other.length})`],
            ].map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setFilter(key)}
                className={`rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest transition-all duration-300 ${
                  filter === key
                    ? 'bg-white text-black shadow-md'
                    : 'bg-transparent text-zinc-500 hover:bg-white/10 hover:text-white'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-6">
          {visibleReviews.length > 0 ? (
            visibleReviews.map(review => <ReviewRecord key={review.id} review={review} />)
          ) : (
            <div className="text-zinc-500 py-32 text-2xl font-medium text-center flex items-center justify-center border border-white/5 rounded-[48px] bg-zinc-950/40 shadow-2xl backdrop-blur-2xl">No reviews in this category.</div>
          )}
        </div>
      </section>
    </div>
  )
}