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
