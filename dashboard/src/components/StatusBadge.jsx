const STATUS_MAP = {
  pending:      { bg: 'bg-zinc-900/60', text: 'text-zinc-300', border: 'border-white/10', dot: 'bg-zinc-400' },
  running:      { bg: 'bg-blue-950/40', text: 'text-blue-300', border: 'border-blue-500/20', dot: 'bg-blue-400', pulse: true },
  completed:    { bg: 'bg-emerald-950/40', text: 'text-emerald-300', border: 'border-emerald-500/20', dot: 'bg-emerald-400' },
  failed:       { bg: 'bg-red-950/40', text: 'text-red-300', border: 'border-red-500/20', dot: 'bg-red-400' },
  scraped:      { bg: 'bg-purple-950/40', text: 'text-purple-300', border: 'border-purple-500/20', dot: 'bg-purple-400' },
  filtered_out: { bg: 'bg-zinc-950/60', text: 'text-zinc-500', border: 'border-white/5', dot: 'bg-zinc-600' },
  qualified:    { bg: 'bg-emerald-950/40', text: 'text-emerald-300', border: 'border-emerald-500/20', dot: 'bg-emerald-400' },
  enriched:     { bg: 'bg-indigo-950/40', text: 'text-indigo-300', border: 'border-indigo-500/20', dot: 'bg-indigo-400' },
  drafted:      { bg: 'bg-orange-950/40', text: 'text-orange-300', border: 'border-orange-500/20', dot: 'bg-orange-400' },
  draft:        { bg: 'bg-zinc-900/60', text: 'text-zinc-300', border: 'border-white/10', dot: 'bg-zinc-400' },
  approved:     { bg: 'bg-emerald-950/40', text: 'text-emerald-300', border: 'border-emerald-500/20', dot: 'bg-emerald-400' },
  sent:         { bg: 'bg-blue-950/40', text: 'text-blue-300', border: 'border-blue-500/20', dot: 'bg-blue-400' },
}

export default function StatusBadge({ status }) {
  const { bg, text, border, dot, pulse } = STATUS_MAP[status] || STATUS_MAP.pending
  return (
    <span className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-widest backdrop-blur-xl border shadow-lg ${bg} ${text} ${border}`}>
      <span className={`w-2 h-2 rounded-full ${dot} ${pulse ? 'animate-pulse shadow-[0_0_10px_currentColor]' : ''}`} />
      {status?.replace(/_/g, ' ')}
    </span>
  )
}