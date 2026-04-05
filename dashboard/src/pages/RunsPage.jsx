import { useState, useEffect, useMemo, useRef } from 'react'
import { gsap } from 'gsap'
import { Activity, BarChart3, Database, Play, ShieldAlert, Trash2 } from 'lucide-react'
import { useRuns, useCreateRun, useDeleteRun, useRunDiagnostics, useRunPolicyResults, usePolicyReevaluation } from '../api/runs'
import Button from '../components/Button'
import Modal from '../components/Modal'

const REASON_CODE_LABELS = {
  HIGH_INSURER_COUNT: 'Frequent insurer-related complaints',
  RECENT_SPIKE: 'Recent increase in complaints',
  MULTIPLE_INDEPENDENT_REVIEWERS: 'Multiple independent reviewers',
  HIGH_COMPLAINT_RATE: 'Meaningful complaint rate',
  LIMITED_CLINIC_FAULT_EVIDENCE: 'Limited clinic-fault evidence',
  MIXED_OR_UNCLEAR_CASES: 'Some mixed or unclear cases',
  STRONG_INSURER_SIGNAL: 'Strong insurer signal',
  RECENT_COMPLAINT_CLUSTER: 'Recent complaint cluster',
  OBVIOUS_TARGET: 'Obvious target',
  SCORE_THRESHOLD: 'Met score threshold',
  INSUFFICIENT_INSURER_COMPLAINTS: 'Insufficient insurer complaints',
  INSUFFICIENT_UNIQUE_REVIEWERS: 'Insufficient unique reviewers',
  INCONSISTENT_ISSUE_PATTERN: 'Inconsistent issue pattern',
  LOW_COMPLAINT_RATE: 'Low complaint rate',
  CLINIC_FAULT_DOMINATES: 'Clinic-fault evidence dominates',
  BELOW_THRESHOLD: 'Below threshold',
}



function formatDigitalDuration(totalSeconds) {
  if (totalSeconds == null || Number.isNaN(totalSeconds)) return '--:--:--'
  const safe = Math.max(0, Math.floor(totalSeconds))
  const hours = Math.floor(safe / 3600)
  const minutes = Math.floor((safe % 3600) / 60)
  const seconds = safe % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function NewRunModal({ isOpen, onClose }) {
  const [city, setCity] = useState('')
  const [state, setState] = useState('')
  const [maxReviews, setMaxReviews] = useState(0)
  const createRun = useCreateRun()

  const handleSubmit = (e) => {
    e.preventDefault()
    createRun.mutate(
      { city, state: state.toUpperCase(), max_reviews: maxReviews },
      { onSuccess: () => { onClose(); setCity(''); setState('') } }
    )
  }

  const inputCls = 'w-full border border-white/10 rounded-2xl bg-black/50 px-5 py-4 text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/20 transition-all backdrop-blur-xl'

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Start Run">
      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <div>
          <label className="block text-xs font-bold text-zinc-500 mb-3 uppercase tracking-widest">City</label>
          <input value={city} onChange={e => setCity(e.target.value)} placeholder="e.g. Houston" required className={inputCls} />
        </div>
        <div>
          <label className="block text-xs font-bold text-zinc-500 mb-3 uppercase tracking-widest">State</label>
          <input value={state} onChange={e => setState(e.target.value.toUpperCase())} placeholder="TX" maxLength={2} required className={inputCls} />
        </div>
        <div>
          <label className="block text-xs font-bold text-zinc-500 mb-3 uppercase tracking-widest">Max Reviews Per Clinic</label>
          <input type="number" value={maxReviews} onChange={e => setMaxReviews(Number(e.target.value))} min={0} max={500} className={inputCls} />
          <p className="mt-3 text-xs font-medium text-zinc-500">Set to 0 for uncapped review scraping.</p>
        </div>
        <div className="flex items-center gap-4 justify-end pt-6 border-t border-white/5 mt-4">
          <Button variant="ghost" onClick={onClose} type="button">Cancel</Button>
          <Button
            type="submit"
            disabled={createRun.isPending}
            className="!bg-white !text-black !border-transparent hover:!bg-zinc-200 !px-7 !py-3 !text-sm whitespace-nowrap"
          >
            <Play size={18} fill="currentColor" />
            {createRun.isPending ? 'Starting…' : 'Start run'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function StatItem({ label, value, colorClass = "text-white" }) {
  return (
    <div className="flex flex-col justify-between p-8 rounded-[32px] bg-zinc-950/60 backdrop-blur-2xl border border-white/5 shadow-2xl">
      <span className={`text-6xl font-medium tracking-tighter ${colorClass}`}>{value ?? 0}</span>
      <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest mt-6">{label}</span>
    </div>
  )
}

// ... keeping summarizePolicyResults and others intact, updating only styling
function summarizePolicyResults(results) {
  const list = results || []
  const total = list.length
  const qualified = list.filter(result => result.is_qualified).length
  const avgFinalScore = total
    ? list.reduce((sum, result) => sum + (result.final_score || 0), 0) / total
    : 0
  const avgConfidence = total
    ? list.reduce((sum, result) => sum + (result.confidence_score || 0), 0) / total
    : 0
  const topClinic = list[0]

  return {
    total,
    qualified,
    filteredOut: Math.max(total - qualified, 0),
    qualificationRate: total ? qualified / total : 0,
    avgFinalScore,
    avgConfidence,
    topClinic,
  }
}

function PolicyComparisonCard({ profile, snapshot, isLoading, onRun, runPending, selected, onSelect }) {
  const summary = summarizePolicyResults(snapshot?.results)

  return (
    <div
      onClick={() => onSelect(profile)}
      role="button"
      tabIndex={0}
      className={`text-left rounded-[32px] border p-8 transition-all duration-300 cursor-pointer backdrop-blur-2xl shadow-xl ${
        selected
          ? 'border-white/20 bg-white/10 shadow-2xl shadow-white/5'
          : 'border-white/5 bg-zinc-950/40 hover:bg-zinc-900/60'
      }`}
    >
      <div className="flex items-start justify-between gap-4 mb-8">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Policy</div>
          <div className="mt-2 text-3xl font-medium text-white capitalize tracking-tight font-mono tabular-nums">{profile}</div>
          <div className="mt-2 text-sm text-zinc-400 font-medium">{snapshot?.policy_version || 'v1'} <span className="opacity-50 mx-2">·</span> threshold {(snapshot?.qualification_threshold ?? 0).toFixed(2)}</div>
        </div>
        <div className="rounded-full bg-white/10 px-4 py-2 text-xs font-bold uppercase tracking-widest text-white shadow-sm border border-white/5">
          {summary.qualified}/{summary.total || 0} kept
        </div>
      </div>

      {isLoading ? (
        <div className="text-sm font-medium text-zinc-500">Loading snapshot…</div>
      ) : summary.total > 0 ? (
        <div className="space-y-8">
          <div className="grid grid-cols-3 gap-6 border-t border-white/5 pt-8">
            <div>
              <div className="text-3xl font-medium text-white tracking-tight font-mono tabular-nums">{summary.total}</div>
              <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mt-2">Clinics</div>
            </div>
            <div>
              <div className="text-3xl font-medium text-white tracking-tight font-mono tabular-nums">{summary.qualified}</div>
              <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mt-2">Kept</div>
            </div>
            <div>
              <div className="text-3xl font-medium text-white tracking-tight font-mono tabular-nums">{summary.avgFinalScore.toFixed(2)}</div>
              <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mt-2">Avg Score</div>
            </div>
          </div>

          <div className="pt-2">
            <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-4">Top reasons</div>
            <div className="flex flex-wrap gap-3">
              {(snapshot?.summary?.reason_codes || []).slice(0, 3).map(reason => (
                <span key={reason.code} className="rounded-full bg-zinc-900 px-4 py-2 text-xs font-bold text-zinc-300 capitalize border border-white/5 shadow-sm">
                  {reason.label}
                  <span className="ml-2 text-zinc-500">({reason.count})</span>
                </span>
              ))}
              {(snapshot?.summary?.reason_codes || []).length === 0 && <span className="text-sm font-medium text-zinc-500">No reasons yet.</span>}
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-6 pt-6 border-t border-white/5">
          <div className="text-sm font-medium text-zinc-500">No stored snapshot yet.</div>
          <Button
            size="sm"
            variant="secondary"
            onClick={(event) => {
              event.stopPropagation()
              onRun(profile)
            }}
            disabled={runPending}
          >
            {runPending ? 'Running…' : 'Run policy'}
          </Button>
        </div>
      )}
    </div>
  )
}

function PolicyBreakdownPanel({ result }) {
  if (!result) {
    return (
      <div className="border border-white/5 rounded-[32px] p-10 bg-zinc-950/40 backdrop-blur-2xl text-zinc-500 font-medium text-left flex items-start justify-start min-h-[400px] shadow-2xl">
        Run a policy snapshot and select a clinic to inspect its scoring breakdown.
      </div>
    )
  }

  return (
    <div className="border border-white/5 rounded-[32px] p-10 bg-zinc-950/60 backdrop-blur-3xl shadow-2xl">
      <div className="flex flex-wrap items-start justify-between gap-6 border-b border-white/5 pb-8 mb-8">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-3">Clinic breakdown</div>
          <h3 className="text-4xl font-medium text-white tracking-tight leading-tight font-mono tabular-nums">{result.clinic_name}</h3>
          <div className="text-base text-zinc-400 font-medium mt-3">
            {result.policy_version} <span className="opacity-50 mx-3">·</span> {result.qualification_profile} <span className="opacity-50 mx-3">·</span> threshold {result.qualification_threshold.toFixed(2)}
          </div>
        </div>
        <div className={`rounded-full px-5 py-2 text-xs font-bold uppercase tracking-widest shadow-lg ${result.is_qualified ? 'bg-white text-black' : 'bg-zinc-900 text-zinc-300 border border-white/10'}`}>
          {result.is_qualified ? 'qualified' : 'filtered out'}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Final score</div>
          <div className="text-4xl font-medium text-white tracking-tight font-mono tabular-nums">{result.final_score.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Confidence</div>
          <div className="text-4xl font-medium text-white tracking-tight font-mono tabular-nums">{result.confidence_score.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Complaint rate</div>
          <div className="text-4xl font-medium text-white tracking-tight font-mono tabular-nums">{(result.complaint_rate * 100).toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Version</div>
          <div className="text-4xl font-medium text-white tracking-tight font-mono tabular-nums">{result.policy_version}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-10 text-base mb-10 pt-8 border-t border-white/5">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-5">Evidence</div>
          <ul className="space-y-4 text-zinc-400 font-medium">
            <li className="flex justify-between border-b border-white/5 pb-3"><span>Insurer reviews</span> <strong className="text-white">{result.insurer_fault_reviews}</strong></li>
            <li className="flex justify-between border-b border-white/5 pb-3"><span>Clinic reviews</span> <strong className="text-white">{result.clinic_fault_reviews}</strong></li>
            <li className="flex justify-between border-b border-white/5 pb-3"><span>Shared reviews</span> <strong className="text-white">{result.shared_fault_reviews}</strong></li>
            <li className="flex justify-between"><span>Unique reviewers</span> <strong className="text-white">{result.unique_insurer_reviewers}</strong></li>
          </ul>
        </div>
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-5">Scoring</div>
          <ul className="space-y-4 text-zinc-400 font-medium">
            <li className="flex justify-between border-b border-white/5 pb-3"><span>Base</span> <strong className="text-white">{result.base_score.toFixed(2)}</strong></li>
            <li className="flex justify-between border-b border-white/5 pb-3"><span>Effective signal</span> <strong className="text-white">{result.effective_insurer_signal.toFixed(2)}</strong></li>
            <li className="flex justify-between border-b border-white/5 pb-3"><span>Recency</span> <strong className="text-white">{result.recency_score.toFixed(2)}</strong></li>
            <li className="flex justify-between"><span>Uniqueness</span> <strong className="text-white">{result.reviewer_uniqueness_score.toFixed(2)}</strong></li>
          </ul>
        </div>
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-5">Policy config</div>
          <ul className="space-y-4 text-zinc-400 font-medium">
            <li className="flex justify-between border-b border-white/5 pb-3"><span>Threshold</span> <strong className="text-white">{result.policy_config?.threshold?.toFixed?.(2) ?? result.qualification_threshold.toFixed(2)}</strong></li>
            <li className="flex justify-between border-b border-white/5 pb-3"><span>Confidence</span> <strong className="text-white truncate max-w-[100px]" title={result.policy_config?.confidence_formula || 'n/a'}>{result.policy_config?.confidence_formula || 'n/a'}</strong></li>
            <li className="flex justify-between border-b border-white/5 pb-3"><span>Rate cap</span> <strong className="text-white">{result.policy_config?.normalization?.rate_cap?.toFixed?.(2) ?? 'n/a'}</strong></li>
            <li className="flex justify-between"><span>Gray zone</span> <strong className="text-white">{result.policy_config?.gray_zone?.enabled ? 'on' : 'off'}</strong></li>
          </ul>
        </div>
      </div>

      <div className="pt-8 border-t border-white/5">
        <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-4">Top signals</div>
        <div className="flex flex-wrap gap-3">
          {(result.top_signals || []).map(signal => (
            <span key={signal} className="rounded-full bg-zinc-900 px-4 py-2 text-xs font-bold text-white capitalize border border-white/10 shadow-sm">
              {signal}
            </span>
          ))}
          {(result.top_signals || []).length === 0 && <span className="text-sm font-medium text-zinc-500">No top signals.</span>}
        </div>
      </div>
    </div>
  )
}

function RunItem({ run }) {
  const isActiveRun = run.status === 'running' || run.status === 'pending'
  
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!isActiveRun) return
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [isActiveRun])

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showDiagnostics, setShowDiagnostics] = useState(false)
  const [showPolicyModal, setShowPolicyModal] = useState(false)
  const [policyProfile, setPolicyProfile] = useState('balanced')
  const [policyVersion, setPolicyVersion] = useState('v1')
  const [policyThreshold, setPolicyThreshold] = useState('0.55')
  const [selectedClinicId, setSelectedClinicId] = useState(null)
  
  const deleteRun = useDeleteRun()
  const diagnostics = useRunDiagnostics(run.id, {
    enabled: isActiveRun || showDiagnostics,
    refetchInterval: isActiveRun ? 2000 : false,
    refetchIntervalInBackground: true,
  })
  const policyRun = usePolicyReevaluation()
  const strictResults = useRunPolicyResults(run.id, 'strict', policyVersion, showPolicyModal)
  const balancedResults = useRunPolicyResults(run.id, 'balanced', policyVersion, showPolicyModal)
  const recallResults = useRunPolicyResults(run.id, 'recall', policyVersion, showPolicyModal)

  const diagnosticsData = diagnostics.data
  const found = diagnosticsData?.total_clinics ?? run.total_clinics_found ?? 0
  const qualified = diagnosticsData?.stage_counts?.qualified ?? run.total_qualified ?? 0
  const enriched = diagnosticsData?.stage_counts?.enriched ?? run.total_enriched ?? 0
  const drafted = diagnosticsData?.stage_counts?.drafted ?? run.total_drafted ?? 0
  const filteredOut = diagnosticsData?.stage_counts?.filtered_out ?? 0
  const flaggedReviews = diagnosticsData?.flagged_reviews ?? 0
  const durationSeconds = diagnosticsData?.duration_seconds

  const createdAtSecondsAgo = Math.floor((now - new Date(run.created_at).getTime()) / 1000)
  const effectiveDurationSeconds = isActiveRun
    ? (durationSeconds ?? createdAtSecondsAgo)
    : durationSeconds

  const isCompletedRun = run.status === 'completed'

  const resultsByProfile = useMemo(() => ({
    strict: strictResults,
    balanced: balancedResults,
    recall: recallResults,
  }), [strictResults, balancedResults, recallResults])

  const selectedSnapshot = resultsByProfile[policyProfile]?.data
  const selectedResults = selectedSnapshot?.results || []
  const selectedResult = selectedResults.find(result => result.clinic_id === selectedClinicId) || selectedResults[0] || null



  const handleDelete = () => {
    deleteRun.mutate(run.id, {
      onSuccess: () => setShowDeleteConfirm(false),
    })
  }

  const handleRunPolicy = (profile = policyProfile) => {
    const threshold = Number(policyThreshold)
    policyRun.mutate(
      {
        runId: run.id,
        payload: {
          qualification_profile: profile,
          qualification_threshold: Number.isFinite(threshold) ? threshold : null,
          policy_version: policyVersion,
        },
      },
      {
        onSuccess: () => {
          setPolicyProfile(profile)
          setSelectedClinicId(null)
        },
      }
    )
  }

  const digitalDurationLabel = formatDigitalDuration(effectiveDurationSeconds)

  return (
    <div className="bg-zinc-950/60 backdrop-blur-3xl border border-white/5 rounded-[40px] p-10 mb-8 relative shadow-2xl group transition-all duration-500 hover:shadow-[0_20px_60px_rgba(0,0,0,0.4)]">
      <div className="absolute top-10 right-10 text-4xl font-medium tracking-tighter tabular-nums text-white/20 group-hover:text-white/40 transition-colors">{digitalDurationLabel}</div>

      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-8 mb-12 pr-[140px]">
        <div>
          <div className="flex items-center gap-5 mb-4 flex-wrap">
            <h2 className="font-medium text-white text-5xl tracking-tight">{run.city}, {run.state}</h2>
            <span className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-widest border bg-white text-black border-white shadow-lg">
              {run.status?.replace(/_/g, ' ')}
            </span>
          </div>
          <div className="text-base text-zinc-500 font-medium">
            {new Date(run.created_at).toLocaleString()} <span className="opacity-50 mx-3">·</span> via {run.triggered_by}
          </div>
        </div>
        <div className="flex items-center gap-4 flex-wrap mt-4 lg:mt-0">
          <Button
            size="md"
            variant="secondary"
            onClick={() => setShowDiagnostics(true)}
            title="View run diagnostics"
          >
            Diagnostics
          </Button>
          <Button
            size="md"
            variant="primary"
            onClick={() => setShowPolicyModal(true)}
            title="Run and compare policy snapshots"
          >
            <BarChart3 size={18} className="mr-2 inline" />
            Policy
          </Button>
          <button
            type="button"
            onClick={() => setShowDeleteConfirm(true)}
            className="p-3 text-zinc-500 hover:text-red-400 bg-white/5 hover:bg-white/10 rounded-full transition-all ml-2"
            title="Delete this run"
          >
            <Trash2 size={20} />
          </button>
        </div>
      </div>

      {isCompletedRun && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10 bg-black/40 rounded-[32px] p-8 border border-white/5">
          <div>
            <div className="text-5xl font-medium text-white tracking-tight font-mono tabular-nums">{found}</div>
            <div className="text-xs text-zinc-500 uppercase tracking-widest mt-4 font-bold">Found</div>
          </div>
          <div>
            <div className="text-5xl font-medium text-white tracking-tight font-mono tabular-nums">{qualified}</div>
            <div className="text-xs text-zinc-500 uppercase tracking-widest mt-4 font-bold">Qualified</div>
          </div>
          <div>
            <div className="text-5xl font-medium text-white tracking-tight font-mono tabular-nums">{enriched}</div>
            <div className="text-xs text-zinc-500 uppercase tracking-widest mt-4 font-bold">Enriched</div>
          </div>
          <div>
            <div className="text-5xl font-medium text-white tracking-tight font-mono tabular-nums">{drafted}</div>
            <div className="text-xs text-zinc-500 uppercase tracking-widest mt-4 font-bold">Drafted</div>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-x-12 gap-y-6 text-base text-zinc-400 font-medium pt-8 border-t border-white/5">
        <div className="flex items-center gap-3"><Database size={20} className="text-zinc-500" /> Scraped <span className="text-white ml-2 text-lg">{diagnosticsData?.stage_counts?.scraped ?? 0}</span></div>
        <div className="flex items-center gap-3"><ShieldAlert size={20} className="text-zinc-500" /> Filtered <span className="text-white ml-2 text-lg">{filteredOut}</span></div>
        <div className="flex items-center">Flagged reviews <span className="text-white ml-3 text-lg">{flaggedReviews}</span></div>
        <div className="flex items-center">Rated clinics <span className="text-white ml-3 text-lg">{diagnosticsData?.clinics_with_rating ?? 0}</span></div>
      </div>

      {/* Skipping Modals implementation strictly to save space, but keeping them in DOM */}
      {showDeleteConfirm && (
        <Modal isOpen={showDeleteConfirm} onClose={() => setShowDeleteConfirm(false)} title="Confirm Deletion">
          <div className="flex flex-col gap-8">
            <div className="border-l-4 border-red-500 bg-red-500/10 rounded-r-2xl p-6 text-lg text-zinc-300 font-medium leading-relaxed">
              This will permanently delete <strong className="text-white">{run.city}, {run.state}</strong> and all <strong className="text-white">{found}</strong> clinic records.
              This action cannot be undone.
            </div>
            <div className="flex gap-4 justify-end mt-4">
              <Button variant="ghost" onClick={() => setShowDeleteConfirm(false)}>Cancel</Button>
              <Button
                variant="danger"
                onClick={handleDelete}
                disabled={deleteRun.isPending}
              >
                {deleteRun.isPending ? 'Deleting…' : 'Delete Run'}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {showDiagnostics && (
        <Modal isOpen={showDiagnostics} onClose={() => setShowDiagnostics(false)} title="Diagnostics" size="md">
          {diagnostics.isLoading ? (
            <div className="text-base font-medium text-zinc-500 py-12 text-left">Loading diagnostics…</div>
          ) : diagnostics.isError ? (
            <div className="text-base font-medium text-red-400 py-12 text-left">Could not load diagnostics.</div>
          ) : (
            <div className="space-y-10">
              <div className="grid grid-cols-2 gap-8">
                <div className="bg-zinc-900/50 p-6 rounded-[24px] border border-white/5">
                  <div className="text-4xl font-medium text-white tracking-tight font-mono tabular-nums">{diagnostics.data?.total_clinics ?? 0}</div>
                  <div className="text-xs text-zinc-500 uppercase tracking-widest mt-3 font-bold">Total Clinics</div>
                </div>
                <div className="bg-zinc-900/50 p-6 rounded-[24px] border border-white/5">
                  <div className="text-4xl font-medium text-white tracking-tight font-mono tabular-nums">{diagnostics.data?.flagged_reviews ?? 0}</div>
                  <div className="text-xs text-zinc-500 uppercase tracking-widest mt-3 font-bold">Flagged Reviews</div>
                </div>
                <div className="bg-zinc-900/50 p-6 rounded-[24px] border border-white/5">
                  <div className="text-4xl font-medium text-white tracking-tight font-mono tabular-nums">{diagnostics.data?.clinics_with_rating ?? 0}</div>
                  <div className="text-xs text-zinc-500 uppercase tracking-widest mt-3 font-bold">Clinics With Rating</div>
                </div>
                <div className="bg-zinc-900/50 p-6 rounded-[24px] border border-white/5">
                  <div className="text-4xl font-medium text-white tracking-tight font-mono tabular-nums">{diagnostics.data?.clinics_with_scraped_reviews ?? 0}</div>
                  <div className="text-xs text-zinc-500 uppercase tracking-widest mt-3 font-bold">Scraped Reviews</div>
                </div>
              </div>

              <div className="border-t border-white/5 pt-10">
                <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-6">Stage Counts</div>
                <div className="grid grid-cols-2 gap-6 text-lg font-medium text-zinc-300">
                  <div className="flex justify-between border-b border-white/5 pb-4 pr-6"><span>Scraped</span> <strong className="text-white">{diagnostics.data?.stage_counts?.scraped ?? 0}</strong></div>
                  <div className="flex justify-between border-b border-white/5 pb-4 pr-6"><span>Filtered Out</span> <strong className="text-white">{diagnostics.data?.stage_counts?.filtered_out ?? 0}</strong></div>
                  <div className="flex justify-between border-b border-white/5 pb-4 pr-6"><span>Qualified</span> <strong className="text-white">{diagnostics.data?.stage_counts?.qualified ?? 0}</strong></div>
                  <div className="flex justify-between border-b border-white/5 pb-4 pr-6"><span>Enriched</span> <strong className="text-white">{diagnostics.data?.stage_counts?.enriched ?? 0}</strong></div>
                  <div className="flex justify-between pb-4 pr-6"><span>Drafted</span> <strong className="text-white">{diagnostics.data?.stage_counts?.drafted ?? 0}</strong></div>
                </div>
              </div>

              <div className="text-sm text-zinc-500 pt-6 font-bold uppercase tracking-widest">
                Duration: {diagnostics.data?.duration_seconds != null ? `${diagnostics.data.duration_seconds}s` : 'n/a'}
              </div>
            </div>
          )}
        </Modal>
      )}

      {showPolicyModal && (
        <Modal isOpen={showPolicyModal} onClose={() => setShowPolicyModal(false)} title="Policy Snapshots" size="xl">
          <div className="space-y-10">
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)] items-start">
              <div className="rounded-[32px] border border-white/5 bg-white/5 p-8 shadow-2xl">
                <div className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-4">Policy snapshot</div>
                <div className="text-lg text-zinc-300 font-medium leading-relaxed max-w-3xl">
                  Re-run qualification on stored reviews only. This does not scrape again and does not call Gemini.
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-[28px] border border-white/5 bg-zinc-950/60 p-5 shadow-xl">
                  <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500 mb-3">Profiles</div>
                  <div className="text-3xl font-medium text-white tracking-tight font-mono tabular-nums">3</div>
                </div>
                <div className="rounded-[28px] border border-white/5 bg-zinc-950/60 p-5 shadow-xl">
                  <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500 mb-3">Version</div>
                  <div className="text-3xl font-medium text-white tracking-tight font-mono tabular-nums">{policyVersion}</div>
                </div>
                <div className="rounded-[28px] border border-white/5 bg-zinc-950/60 p-5 shadow-xl">
                  <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500 mb-3">Threshold</div>
                  <div className="text-3xl font-medium text-white tracking-tight font-mono tabular-nums">{Number(policyThreshold).toFixed(2)}</div>
                </div>
              </div>
            </div>

            {/* Same forms but modernized inputs */}
            <div className="grid gap-8 lg:grid-cols-[1fr_170px_260px_auto] items-end pb-10 border-b border-white/5">
              <div>
                <label className="block text-xs font-bold uppercase tracking-widest text-zinc-500 mb-4">Profile</label>
                <select
                  value={policyProfile}
                  onChange={e => {
                    setPolicyProfile(e.target.value)
                    setSelectedClinicId(null)
                  }}
                  className="w-full border border-white/10 rounded-2xl bg-black/50 px-5 py-4 text-base font-medium text-white focus:outline-none focus:ring-2 focus:ring-white/20 transition-all"
                >
                  <option value="strict">strict</option>
                  <option value="balanced">balanced</option>
                  <option value="recall">recall</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-widest text-zinc-500 mb-4">Version</label>
                <select
                  value={policyVersion}
                  onChange={e => setPolicyVersion(e.target.value)}
                  className="w-full border border-white/10 rounded-2xl bg-black/50 px-5 py-4 text-base font-medium text-white focus:outline-none focus:ring-2 focus:ring-white/20 transition-all"
                >
                  <option value="v1">v1</option>
                  <option value="v2">v2</option>
                  <option value="v3">v3</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-widest text-zinc-500 mb-4 flex justify-between">
                  <span>Threshold</span>
                  <span className="text-white">{Number(policyThreshold).toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min="0.20"
                  max="0.90"
                  step="0.01"
                  value={policyThreshold}
                  onChange={e => setPolicyThreshold(e.target.value)}
                  className="w-full accent-white h-3 bg-white/10 rounded-full appearance-none cursor-pointer"
                />
              </div>

              <Button onClick={() => handleRunPolicy()} disabled={policyRun.isPending} className="whitespace-nowrap py-4 px-8 text-base">
                {policyRun.isPending ? 'Running…' : 'Apply policy'}
              </Button>
            </div>
            
            {/* The rest is the same structural flow but uses rounded-3xl / 4xl and larger gaps where available. Leaving structural elements intact. */}
            <div className="grid gap-8 lg:grid-cols-3">
              {(['strict', 'balanced', 'recall']).map(profile => (
                <PolicyComparisonCard
                  key={profile}
                  profile={profile}
                  snapshot={resultsByProfile[profile].data}
                  isLoading={resultsByProfile[profile].isLoading}
                  onRun={handleRunPolicy}
                  runPending={policyRun.isPending}
                  selected={policyProfile === profile}
                  onSelect={(nextProfile) => {
                    setPolicyProfile(nextProfile)
                    setSelectedClinicId(null)
                  }}
                />
              ))}
            </div>
            
            <div className="border-t border-white/5 pt-12">
              <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
                <div>
                  <h3 className="text-3xl font-medium text-white tracking-tight font-mono tabular-nums">Selected Clinics</h3>
                  <div className="text-base font-medium text-zinc-500 mt-2">Click a clinic to inspect its score breakdown.</div>
                </div>
                <div className="text-sm font-bold uppercase tracking-widest text-zinc-500 bg-white/5 px-4 py-2 rounded-full border border-white/10 self-start">{selectedResults.length} clinics</div>
              </div>

              <div className="grid gap-8 2xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)] items-stretch">
                <div className="rounded-[32px] border border-white/5 bg-zinc-950/45 p-5 shadow-2xl">
                  <div className="flex items-center justify-between gap-4 px-3 pt-1 pb-5">
                    <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Clinic list</div>
                    <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">{selectedResults.length} total</div>
                  </div>
                  <div className="space-y-4 max-h-[720px] overflow-y-auto pr-2 no-scrollbar">
                  {selectedResults.map(result => (
                    <button
                      key={result.clinic_id}
                      type="button"
                      onClick={() => setSelectedClinicId(result.clinic_id)}
                      className={`w-full text-left rounded-[24px] border px-8 py-6 transition-all duration-300 backdrop-blur-xl ${
                        selectedResult?.clinic_id === result.clinic_id
                          ? 'border-white/30 bg-white/10 shadow-2xl'
                          : 'border-white/5 bg-zinc-950/40 hover:bg-zinc-900/60'
                      }`}
                    >
                      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-6">
                        <div className="min-w-0">
                          <div className="font-medium text-white text-xl truncate mb-2">#{result.rank} {result.clinic_name}</div>
                          <div className="text-base text-zinc-400 font-medium">
                            score {result.final_score.toFixed(2)} <span className="opacity-50 mx-2">·</span> conf {result.confidence_score.toFixed(2)}
                            <span className={`ml-4 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest ${result.is_qualified ? 'bg-white text-black' : 'bg-zinc-900 text-zinc-400 border border-white/10'}`}>{result.is_qualified ? 'qualified' : 'filtered out'}</span>
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                    {selectedResults.length === 0 && (
                      <div className="rounded-[28px] border border-dashed border-white/10 bg-black/30 px-6 py-14 text-zinc-500 text-left font-medium text-lg leading-relaxed">
                        No clinics in this snapshot yet. Run a policy snapshot to populate this panel.
                      </div>
                    )}
                  </div>
                </div>

                <div className="min-h-[720px]">
                  <PolicyBreakdownPanel result={selectedResult} />
                </div>
              </div>
            </div>
            
          </div>
        </Modal>
      )}
    </div>
  )
}

export default function RunsPage() {
  const { data: runs = [], isLoading } = useRuns({
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
  })
  const [modalOpen, setModalOpen] = useState(false)
  const listRef = useRef(null)

  const totals = runs.reduce(
    (acc, r) => ({
      found: acc.found + (r.total_clinics_found || 0),
      qualified: acc.qualified + (r.total_qualified || 0),
      enriched: acc.enriched + (r.total_enriched || 0),
      drafted: acc.drafted + (r.total_drafted || 0),
    }),
    { found: 0, qualified: 0, enriched: 0, drafted: 0 }
  )

  useEffect(() => {
    if (!isLoading && listRef.current) {
      gsap.fromTo(
        listRef.current.children,
        { opacity: 0, y: 30 },
        { opacity: 1, y: 0, stagger: 0.1, duration: 0.5, ease: 'power3.out' }
      )
    }
  }, [isLoading])

  return (
    <div className="w-full pb-32">
      <header className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-10 mb-20">
        <div className="w-full">
          <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/10 backdrop-blur-xl px-5 py-2 text-xs font-bold uppercase tracking-widest text-zinc-300 mb-8 shadow-sm">
            <Activity size={14} />
            Pipeline Runs
          </div>
          <h1 className="text-5xl lg:text-6xl font-medium text-white tracking-tighter mb-6 leading-tight">Operations Console</h1>
          <p className="text-zinc-400 text-xl font-medium leading-relaxed">
            Start a city run, then review progress, diagnostics, and outcomes from one place.
          </p>
        </div>
        <div className="flex items-center gap-6">
          <Button
            onClick={() => setModalOpen(true)}
            size="lg"
            className="!bg-white !text-black !border-transparent hover:!bg-zinc-200 !px-9 !py-4 !text-xl !font-semibold whitespace-nowrap !gap-3"
          >
            <Play size={30} fill="currentColor" />
            Start run
          </Button>
        </div>
      </header>

      {runs.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-10 mb-24">
          <StatItem label="Clinics Found" value={totals.found} colorClass="text-white" />
          <StatItem label="Qualified" value={totals.qualified} colorClass="text-zinc-300" />
          <StatItem label="Enriched" value={totals.enriched} colorClass="text-zinc-400" />
          <StatItem label="Drafted" value={totals.drafted} colorClass="text-zinc-500" />
        </div>
      )}

      {isLoading ? (
        <div className="text-zinc-500 font-medium text-lg py-16 text-left">Loading runs...</div>
      ) : runs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 bg-zinc-950/40 backdrop-blur-3xl rounded-[48px] border border-white/5 shadow-2xl">
          <Activity size={64} strokeWidth={1.5} className="mb-10 text-white/20" />
          <p className="text-2xl font-medium text-center text-zinc-300 max-w-lg mb-10 leading-relaxed">No runs yet. Start the first city scan and the dashboard will fill with stage-by-stage progress.</p>
          <Button variant="primary" size="lg" onClick={() => setModalOpen(true)}>Create your first run</Button>
        </div>
      ) : (
        <div ref={listRef} className="flex flex-col gap-8">
          {runs.map(run => <RunItem key={run.id} run={run} />)}
        </div>
      )}

      <NewRunModal isOpen={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  )
}